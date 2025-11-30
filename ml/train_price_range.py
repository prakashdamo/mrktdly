#!/usr/bin/env python3
"""
Price Range Predictor
Predicts upper and lower price bounds for next 5 days using ML
"""
import boto3
import pandas as pd
import numpy as np
import pickle
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from datetime import datetime
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')
price_table = dynamodb.Table('mrktdly-price-history')

def calculate_future_range(ticker, date, days=5):
    """Calculate actual high and low over next N days"""
    try:
        # Get next N+3 days (account for weekends)
        start_date = pd.to_datetime(date)
        end_date = start_date + pd.Timedelta(days=days+3)
        
        response = price_table.query(
            KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            ),
            Limit=days+3
        )
        
        prices = response.get('Items', [])
        if len(prices) < 2:
            return None, None
        
        # Skip first day (current), get next N days
        future_prices = prices[1:days+1]
        if len(future_prices) < 2:
            return None, None
        
        highs = [float(p['high']) for p in future_prices]
        lows = [float(p['low']) for p in future_prices]
        
        return max(highs), min(lows)
        
    except Exception as e:
        print(f"Error calculating range for {ticker} on {date}: {e}")
        return None, None

def load_and_label_data():
    """Load features and calculate future price ranges"""
    print("Loading features from DynamoDB...")
    features_table = dynamodb.Table('mrktdly-features')
    
    response = features_table.scan()
    items = response['Items']
    while 'LastEvaluatedKey' in response:
        response = features_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    print(f"Loaded {len(items)} records")
    
    df = pd.DataFrame(items)
    df['date'] = pd.to_datetime(df['date'])
    
    # Calculate future ranges (this will take a while)
    print("Calculating future price ranges...")
    ranges = []
    for idx, row in df.iterrows():
        if idx % 1000 == 0:
            print(f"Processed {idx}/{len(df)}")
        
        future_high, future_low = calculate_future_range(
            row['ticker'], 
            row['date']
        )
        
        if future_high and future_low:
            current_price = float(row.get('price', 0))
            if current_price > 0:
                ranges.append({
                    'ticker': row['ticker'],
                    'date': row['date'],
                    'future_high': future_high,
                    'future_low': future_low,
                    'future_high_pct': ((future_high - current_price) / current_price) * 100,
                    'future_low_pct': ((future_low - current_price) / current_price) * 100
                })
    
    ranges_df = pd.DataFrame(ranges)
    df = df.merge(ranges_df, on=['ticker', 'date'], how='inner')
    
    print(f"Records with ranges: {len(df)}")
    return df

def train_models(df):
    """Train two models: one for upper bound, one for lower bound"""
    print("\nPreparing training data...")
    
    # Features
    feature_cols = ['ma_5', 'ma_10', 'ma_20', 'ma_50', 'ma_200', 'rsi', 'macd', 'macd_signal',
                    'bb_upper', 'bb_middle', 'bb_lower', 'atr', 'vol_ratio', 'return_1d',
                    'return_5d', 'return_20d', 'volatility', 'pct_from_high', 'pct_from_low']
    
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=feature_cols + ['future_high_pct', 'future_low_pct'])
    
    X = df[feature_cols]
    y_high = df['future_high_pct']
    y_low = df['future_low_pct']
    
    print(f"Training samples: {len(X)}")
    print(f"Avg future high: +{y_high.mean():.2f}%")
    print(f"Avg future low: {y_low.mean():.2f}%")
    
    # Split
    X_train, X_test, y_high_train, y_high_test, y_low_train, y_low_test = train_test_split(
        X, y_high, y_low, test_size=0.2, random_state=42
    )
    
    # Train upper bound model
    print("\nTraining upper bound model...")
    model_high = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    model_high.fit(X_train, y_high_train)
    
    # Train lower bound model
    print("Training lower bound model...")
    model_low = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    model_low.fit(X_train, y_low_train)
    
    # Evaluate
    y_high_pred = model_high.predict(X_test)
    y_low_pred = model_low.predict(X_test)
    
    mae_high = mean_absolute_error(y_high_test, y_high_pred)
    mae_low = mean_absolute_error(y_low_test, y_low_pred)
    r2_high = r2_score(y_high_test, y_high_pred)
    r2_low = r2_score(y_low_test, y_low_pred)
    
    print(f"\n{'='*60}")
    print(f"MODEL PERFORMANCE")
    print(f"{'='*60}")
    print(f"Upper Bound Model:")
    print(f"  MAE: ±{mae_high:.2f}%")
    print(f"  R²: {r2_high:.3f}")
    print(f"\nLower Bound Model:")
    print(f"  MAE: ±{mae_low:.2f}%")
    print(f"  R²: {r2_low:.3f}")
    
    # Test on sample
    print(f"\n{'='*60}")
    print(f"SAMPLE PREDICTIONS")
    print(f"{'='*60}")
    for i in range(5):
        print(f"Predicted: +{y_high_pred[i]:.1f}% / {y_low_pred[i]:.1f}%  "
              f"Actual: +{y_high_test.iloc[i]:.1f}% / {y_low_test.iloc[i]:.1f}%")
    
    return model_high, model_low, feature_cols

def save_models(model_high, model_low, feature_cols):
    """Save models to S3"""
    print(f"\n{'='*60}")
    print(f"SAVING MODELS")
    print(f"{'='*60}")
    
    model_data = {
        'model_high': model_high,
        'model_low': model_low,
        'feature_cols': feature_cols,
        'trained_date': datetime.now().isoformat(),
        'model_type': 'price_range_predictor'
    }
    
    with open('/tmp/price_range_models.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    s3.upload_file('/tmp/price_range_models.pkl', 'mrktdly-models', 'price_range_models.pkl')
    print("✓ Models saved to s3://mrktdly-models/price_range_models.pkl")

def main():
    print("="*60)
    print("PRICE RANGE PREDICTOR TRAINING")
    print("="*60)
    
    # Load and label (this takes time)
    df = load_and_label_data()
    
    # Train
    model_high, model_low, feature_cols = train_models(df)
    
    # Save
    save_models(model_high, model_low, feature_cols)
    
    print(f"\n{'='*60}")
    print("TRAINING COMPLETE")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

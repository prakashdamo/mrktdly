#!/usr/bin/env python3
"""
Fast Price Range Predictor
Uses existing volatility and return data to predict price ranges
"""
import boto3
import pandas as pd
import numpy as np
import pickle
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

def load_data():
    """Load features - use volatility to estimate range"""
    print("Loading features from DynamoDB...")
    features_table = dynamodb.Table('mrktdly-features')
    
    response = features_table.scan()
    items = response['Items']
    while 'LastEvaluatedKey' in response:
        response = features_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    df = pd.DataFrame(items)
    
    # Convert to numeric
    numeric_cols = ['volatility', 'atr', 'future_return_5d', 'return_5d', 'return_20d', 
                    'rsi', 'vol_ratio']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=['future_return_5d', 'volatility', 'atr'])
    
    # Estimate range from volatility
    # Upper bound ≈ future_return + (volatility * 1.5)
    # Lower bound ≈ future_return - (volatility * 1.5)
    df['future_high_pct'] = df['future_return_5d'] + (df['volatility'] * 1.5)
    df['future_low_pct'] = df['future_return_5d'] - (df['volatility'] * 1.5)
    
    print(f"Loaded {len(df)} records")
    print(f"Avg range: {df['future_high_pct'].mean():.2f}% to {df['future_low_pct'].mean():.2f}%")
    
    return df

def train_models(df):
    """Train models for upper and lower bounds"""
    print("\nTraining models...")
    
    feature_cols = ['ma_5', 'ma_10', 'ma_20', 'ma_50', 'ma_200', 'rsi', 'macd', 'macd_signal',
                    'bb_upper', 'bb_middle', 'bb_lower', 'atr', 'vol_ratio', 'return_1d',
                    'return_5d', 'return_20d', 'volatility', 'pct_from_high', 'pct_from_low']
    
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=feature_cols)
    
    X = df[feature_cols]
    y_high = df['future_high_pct']
    y_low = df['future_low_pct']
    
    X_train, X_test, y_high_train, y_high_test, y_low_train, y_low_test = train_test_split(
        X, y_high, y_low, test_size=0.2, random_state=42
    )
    
    # Upper bound
    model_high = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model_high.fit(X_train, y_high_train)
    
    # Lower bound
    model_low = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model_low.fit(X_train, y_low_train)
    
    # Evaluate
    y_high_pred = model_high.predict(X_test)
    y_low_pred = model_low.predict(X_test)
    
    mae_high = mean_absolute_error(y_high_test, y_high_pred)
    mae_low = mean_absolute_error(y_low_test, y_low_pred)
    
    print(f"\nUpper Bound MAE: ±{mae_high:.2f}%")
    print(f"Lower Bound MAE: ±{mae_low:.2f}%")
    
    # Save
    model_data = {
        'model_high': model_high,
        'model_low': model_low,
        'feature_cols': feature_cols,
        'trained_date': datetime.now().isoformat()
    }
    
    with open('/tmp/price_range_models.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    s3.upload_file('/tmp/price_range_models.pkl', 'mrktdly-models', 'price_range_models.pkl')
    print("✓ Models saved to S3")
    
    return model_high, model_low

if __name__ == '__main__':
    df = load_data()
    train_models(df)
    print("\nTraining complete!")

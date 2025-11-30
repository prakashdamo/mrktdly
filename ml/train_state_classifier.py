#!/usr/bin/env python3
"""
Market State Classifier
Classifies stocks into actionable states: Oversold Bounce, Breakout, Trending Up, etc.
"""
import boto3
import pandas as pd
import numpy as np
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

def define_state(row):
    """Define market state based on technicals and future outcome"""
    rsi = float(row.get('rsi', 50))
    return_20d = float(row.get('return_20d', 0))
    return_5d = float(row.get('return_5d', 0))
    vol_ratio = float(row.get('vol_ratio', 1))
    above_ma20 = row.get('above_ma20', False)
    above_ma50 = row.get('above_ma50', False)
    above_ma200 = row.get('above_ma200', False)
    volatility = float(row.get('volatility', 0))
    pct_from_high = float(row.get('pct_from_high', 0))
    pct_from_low = float(row.get('pct_from_low', 0))
    future_return = float(row.get('future_return_5d', 0))
    
    # State 1: Oversold Bounce (RSI < 30, down big, then bounces)
    if rsi < 30 and return_20d < -15 and future_return > 3:
        return 'oversold_bounce'
    
    # State 2: Breakout (new highs, volume surge, continues up)
    if pct_from_high > 95 and vol_ratio > 1.5 and future_return > 5:
        return 'breakout'
    
    # State 3: Trending Up (above all MAs, consistent gains)
    if above_ma20 and above_ma50 and above_ma200 and return_20d > 5 and future_return > 2:
        return 'trending_up'
    
    # State 4: Consolidation (tight range, low volatility, then moves)
    if volatility < 2 and abs(return_5d) < 2 and abs(future_return) > 3:
        return 'consolidation'
    
    # State 5: Reversal (momentum shift from down to up)
    if return_20d < -10 and return_5d > 3 and rsi > 40 and future_return > 3:
        return 'reversal'
    
    # State 6: Overbought (RSI > 70, extended, pulls back)
    if rsi > 70 and return_20d > 15 and future_return < 0:
        return 'overbought'
    
    # State 7: Trending Down (below MAs, consistent losses)
    if not above_ma20 and not above_ma50 and return_20d < -5 and future_return < -2:
        return 'trending_down'
    
    # State 8: Choppy (no clear pattern, mixed signals)
    return 'choppy'

def load_and_label_data():
    """Load features and assign state labels"""
    print("Loading features from DynamoDB...")
    features_table = dynamodb.Table('mrktdly-features')
    
    response = features_table.scan()
    items = response['Items']
    while 'LastEvaluatedKey' in response:
        response = features_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    print(f"Loaded {len(items)} records")
    
    df = pd.DataFrame(items)
    
    # Convert to numeric
    numeric_cols = ['rsi', 'return_20d', 'return_5d', 'vol_ratio', 'volatility', 
                    'pct_from_high', 'pct_from_low', 'future_return_5d']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Convert boolean
    bool_cols = ['above_ma20', 'above_ma50', 'above_ma200']
    for col in bool_cols:
        df[col] = df[col].astype(str).str.lower() == 'true'
    
    # Assign states
    print("Assigning market states...")
    df['state'] = df.apply(define_state, axis=1)
    
    # Remove rows without future returns
    df = df[df['future_return_5d'].notna()]
    
    print(f"\nState distribution:")
    print(df['state'].value_counts())
    print(f"\nTotal labeled: {len(df)}")
    
    return df

def train_model(df):
    """Train state classifier"""
    print("\nPreparing training data...")
    
    # Features
    feature_cols = ['ma_5', 'ma_10', 'ma_20', 'ma_50', 'ma_200', 'rsi', 'macd', 'macd_signal',
                    'bb_upper', 'bb_middle', 'bb_lower', 'atr', 'vol_ratio', 'return_1d',
                    'return_5d', 'return_20d', 'volatility', 'pct_from_high', 'pct_from_low']
    
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=feature_cols + ['state'])
    
    X = df[feature_cols]
    y = df['state']
    
    print(f"Training samples: {len(X)}")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train
    print("\nTraining RandomForest classifier...")
    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=15,
        min_samples_split=10,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\n{'='*60}")
    print(f"MODEL PERFORMANCE")
    print(f"{'='*60}")
    print(f"Overall Accuracy: {accuracy*100:.1f}%\n")
    print(classification_report(y_test, y_pred))
    
    print(f"\n{'='*60}")
    print(f"CONFUSION MATRIX")
    print(f"{'='*60}")
    print(confusion_matrix(y_test, y_pred))
    
    # Feature importance
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\n{'='*60}")
    print(f"TOP 10 FEATURES")
    print(f"{'='*60}")
    for _, row in importances.head(10).iterrows():
        print(f"{row['feature']:20s} {row['importance']*100:5.1f}%")
    
    return model, feature_cols

def save_model(model, feature_cols):
    """Save model to S3"""
    print(f"\n{'='*60}")
    print(f"SAVING MODEL")
    print(f"{'='*60}")
    
    model_data = {
        'model': model,
        'feature_cols': feature_cols,
        'trained_date': datetime.now().isoformat(),
        'model_type': 'state_classifier'
    }
    
    with open('/tmp/state_classifier.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    s3.upload_file('/tmp/state_classifier.pkl', 'mrktdly-models', 'state_classifier.pkl')
    print("✓ Model saved to s3://mrktdly-models/state_classifier.pkl")

def main():
    print("="*60)
    print("MARKET STATE CLASSIFIER TRAINING")
    print("="*60)
    
    # Load and label
    df = load_and_label_data()
    
    # Train
    model, feature_cols = train_model(df)
    
    # Save
    save_model(model, feature_cols)
    
    print(f"\n{'='*60}")
    print("TRAINING COMPLETE")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("1. Deploy Lambda function to use this model")
    print("2. Test with: aws lambda invoke --function-name mrktdly-state-classifier")
    print("3. Integrate into daily email")

if __name__ == '__main__':
    main()

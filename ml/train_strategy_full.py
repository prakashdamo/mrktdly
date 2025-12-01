#!/usr/bin/env python3
"""Train Strategy Optimizer with full 32k dataset"""
import boto3
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import pickle
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_table = dynamodb.Table('mrktdly-price-history')
features_table = dynamodb.Table('mrktdly-features')

def get_all_features():
    """Get all features from DynamoDB"""
    print("Loading features from DynamoDB...")
    
    features = []
    response = features_table.scan()
    features.extend(response['Items'])
    
    while 'LastEvaluatedKey' in response:
        response = features_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        features.extend(response['Items'])
        print(f"  Loaded {len(features)} records...")
    
    return features

def get_price_history(ticker, start_date, end_date):
    """Get price history for backtesting"""
    response = price_table.query(
        KeyConditionExpression='ticker = :t AND #d BETWEEN :start AND :end',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={':t': ticker, ':start': start_date, ':end': end_date}
    )
    return sorted(response['Items'], key=lambda x: x['date'])

def test_strategy(history, entry_idx, target, stop, hold):
    """Test a strategy on historical data"""
    if entry_idx >= len(history):
        return 0
    
    entry = float(history[entry_idx]['close'])
    target_price = entry * (1 + target/100)
    stop_price = entry * (1 - stop/100)
    
    for i in range(entry_idx + 1, min(entry_idx + hold + 1, len(history))):
        high = float(history[i]['high'])
        low = float(history[i]['low'])
        
        if high >= target_price:
            return target
        if low <= stop_price:
            return -stop
    
    if entry_idx + hold < len(history):
        close = float(history[entry_idx + hold]['close'])
        return (close - entry) / entry * 100
    return 0

def find_optimal_params(ticker, date, features):
    """Find best strategy params by backtesting"""
    # Get 60 days of history before this date for backtesting
    start_date = (pd.to_datetime(date) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    end_date = date
    
    history = get_price_history(ticker, start_date, end_date)
    if len(history) < 30:
        return None
    
    entry_idx = len(history) - 1
    
    best_expectancy = -999
    best_params = (5, 3, 10)
    
    for target in [3, 4, 5, 6, 7, 8]:
        for stop in [2, 3, 4, 5]:
            for hold in [5, 10, 15, 20]:
                results = []
                for i in range(max(0, entry_idx - 20), entry_idx):
                    ret = test_strategy(history, i, target, stop, hold)
                    results.append(ret)
                
                if len(results) >= 10:
                    wins = [r for r in results if r > 0]
                    wr = len(wins) / len(results)
                    avg_win = np.mean(wins) if wins else 0
                    avg_loss = np.mean([r for r in results if r <= 0]) if any(r <= 0 for r in results) else 0
                    exp = wr * avg_win + (1-wr) * avg_loss
                    
                    if exp > best_expectancy:
                        best_expectancy = exp
                        best_params = (target, stop, hold)
    
    return best_params

def build_training_data():
    """Build training dataset from all features"""
    print("\nBuilding training data...")
    
    all_features = get_all_features()
    print(f"Total features loaded: {len(all_features)}")
    
    # Sample 10k for faster training (or use all 32k)
    sample_size = min(10000, len(all_features))
    sampled = np.random.choice(all_features, sample_size, replace=False)
    
    print(f"Using {sample_size} samples for training...")
    
    data = []
    for i, feat in enumerate(sampled):
        if i % 500 == 0:
            print(f"  Processing {i}/{sample_size}...")
        
        optimal = find_optimal_params(feat['ticker'], feat['date'], feat)
        if optimal:
            data.append({
                'rsi': float(feat.get('rsi', 50)),
                'volatility': float(feat.get('volatility', 0)),
                'return_5d': float(feat.get('return_5d', 0)),
                'return_20d': float(feat.get('return_20d', 0)),
                'vol_ratio': float(feat.get('vol_ratio', 1)),
                'above_ma20': 1 if feat.get('above_ma20') else 0,
                'above_ma50': 1 if feat.get('above_ma50') else 0,
                'pct_from_high': float(feat.get('pct_from_high', 0)),
                'optimal_target': optimal[0],
                'optimal_stop': optimal[1],
                'optimal_hold': optimal[2]
            })
    
    return pd.DataFrame(data)

def train_model():
    """Train the strategy optimizer"""
    print("="*60)
    print("TRAINING STRATEGY OPTIMIZER WITH FULL DATASET")
    print("="*60)
    
    df = build_training_data()
    print(f"\nTraining samples: {len(df)}")
    
    if len(df) < 100:
        print("Not enough data!")
        return
    
    feature_cols = ['rsi', 'volatility', 'return_5d', 'return_20d', 'vol_ratio',
                    'above_ma20', 'above_ma50', 'pct_from_high']
    
    X = df[feature_cols]
    
    models = {}
    
    for param in ['optimal_target', 'optimal_stop', 'optimal_hold']:
        print(f"\nTraining {param} predictor...")
        y = df[param]
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"  MAE: {mae:.2f} | R²: {r2:.3f}")
        models[param] = model
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'strategy_optimizer_full_{timestamp}.pkl'
    
    with open(filename, 'wb') as f:
        pickle.dump({'models': models, 'features': feature_cols, 'samples': len(df)}, f)
    
    print(f"\n{'='*60}")
    print(f"✅ Model saved to {filename}")
    print(f"Training samples: {len(df)}")
    print(f"Model size: {os.path.getsize(filename) / 1024 / 1024:.1f} MB")
    print("="*60)

if __name__ == '__main__':
    import os
    train_model()

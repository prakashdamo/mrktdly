#!/usr/bin/env python3
"""Optimized training - cache price data, reduce queries"""
import boto3
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import pickle
from datetime import datetime
import time

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_table = dynamodb.Table('mrktdly-price-history')
features_table = dynamodb.Table('mrktdly-features')

# Cache for price data
PRICE_CACHE = {}

def get_all_features():
    """Get all features"""
    print("Loading features...")
    features = []
    response = features_table.scan()
    features.extend(response['Items'])
    
    while 'LastEvaluatedKey' in response:
        response = features_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        features.extend(response['Items'])
    
    print(f"Loaded {len(features)} features")
    return features

def load_all_price_data():
    """Load ALL price data once (batch operation)"""
    print("Loading all price data (one-time batch)...")
    
    prices = {}
    response = price_table.scan()
    
    for item in response['Items']:
        ticker = item['ticker']
        if ticker not in prices:
            prices[ticker] = []
        prices[ticker].append(item)
    
    while 'LastEvaluatedKey' in response:
        time.sleep(0.1)  # Rate limiting
        response = price_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        for item in response['Items']:
            ticker = item['ticker']
            if ticker not in prices:
                prices[ticker] = []
            prices[ticker].append(item)
    
    # Sort by date
    for ticker in prices:
        prices[ticker] = sorted(prices[ticker], key=lambda x: x['date'])
    
    print(f"Loaded {sum(len(v) for v in prices.values())} price records for {len(prices)} tickers")
    return prices

def find_optimal_simple(ticker_prices, date):
    """Simplified optimal parameter finding using cached data"""
    # Find index of this date
    dates = [p['date'] for p in ticker_prices]
    if date not in dates:
        return None
    
    idx = dates.index(date)
    if idx < 30:  # Need history
        return None
    
    # Quick backtest on last 10 trades only (not 20)
    results = {(5,3,10): [], (6,4,15): [], (7,5,20): []}
    
    for i in range(max(0, idx-10), idx):
        entry = float(ticker_prices[i]['close'])
        
        for (target, stop, hold) in results.keys():
            target_price = entry * (1 + target/100)
            stop_price = entry * (1 - stop/100)
            
            for j in range(i+1, min(i+hold+1, len(ticker_prices))):
                high = float(ticker_prices[j]['high'])
                low = float(ticker_prices[j]['low'])
                
                if high >= target_price:
                    results[(target,stop,hold)].append(target)
                    break
                if low <= stop_price:
                    results[(target,stop,hold)].append(-stop)
                    break
    
    # Pick best
    best = (5, 3, 10)
    best_exp = -999
    
    for params, rets in results.items():
        if len(rets) >= 5:
            wins = [r for r in rets if r > 0]
            wr = len(wins) / len(rets)
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean([r for r in rets if r <= 0]) if any(r <= 0 for r in rets) else 0
            exp = wr * avg_win + (1-wr) * avg_loss
            
            if exp > best_exp:
                best_exp = exp
                best = params
    
    return best

def build_training_data(all_features, all_prices):
    """Build training data using cached prices"""
    print("\nBuilding training data...")
    
    # Use 5k samples for speed
    sample_size = min(5000, len(all_features))
    sampled = np.random.choice(all_features, sample_size, replace=False)
    
    data = []
    for i, feat in enumerate(sampled):
        if i % 500 == 0:
            print(f"  {i}/{sample_size}...")
        
        ticker = feat['ticker']
        if ticker not in all_prices:
            continue
        
        optimal = find_optimal_simple(all_prices[ticker], feat['date'])
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

def train():
    print("="*60)
    print("OPTIMIZED STRATEGY OPTIMIZER TRAINING")
    print("="*60)
    
    # Load everything once
    all_features = get_all_features()
    all_prices = load_all_price_data()
    
    # Build training data
    df = build_training_data(all_features, all_prices)
    print(f"\nFinal training samples: {len(df)}")
    
    if len(df) < 100:
        print("Not enough data!")
        return
    
    feature_cols = ['rsi', 'volatility', 'return_5d', 'return_20d', 'vol_ratio',
                    'above_ma20', 'above_ma50', 'pct_from_high']
    
    X = df[feature_cols]
    models = {}
    
    print("\nTraining models...")
    for param in ['optimal_target', 'optimal_stop', 'optimal_hold']:
        y = df[param]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"  {param}: MAE={mae:.2f}, R²={r2:.3f}")
        models[param] = model
    
    # Save
    filename = 'strategy_optimizer_optimized.pkl'
    with open(filename, 'wb') as f:
        pickle.dump({'models': models, 'features': feature_cols, 'samples': len(df)}, f)
    
    import os
    print(f"\n{'='*60}")
    print(f"✅ Model saved: {filename}")
    print(f"   Samples: {len(df)}")
    print(f"   Size: {os.path.getsize(filename)/1024/1024:.1f} MB")
    print("="*60)

if __name__ == '__main__':
    train()

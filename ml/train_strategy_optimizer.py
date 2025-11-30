#!/usr/bin/env python3
"""Train ML model to predict optimal trading strategy parameters"""
import boto3
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import pickle
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_table = dynamodb.Table('mrktdly-price-history')
features_table = dynamodb.Table('mrktdly-features')

def get_all_tickers():
    """Get all tickers with price data"""
    response = price_table.scan(ProjectionExpression='ticker')
    tickers = set(item['ticker'] for item in response['Items'])
    
    while 'LastEvaluatedKey' in response:
        response = price_table.scan(
            ProjectionExpression='ticker',
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        tickers.update(item['ticker'] for item in response['Items'])
    
    # Filter out futures/ETFs (contain = or are indices)
    stocks = [t for t in tickers if '=' not in t and t not in ['SPY', 'QQQ', 'DIA', 'IWM', 'VOO', 'VTI', 'GLD', 'SLV', 'USO']]
    return sorted(stocks)

TICKERS = get_all_tickers()

def get_all_features(ticker):
    """Batch get all features for a ticker"""
    try:
        response = features_table.query(
            KeyConditionExpression='ticker = :t',
            ExpressionAttributeValues={':t': ticker}
        )
        return {item['date']: item for item in response['Items']}
    except:
        return {}

def test_strategy(ticker, start_idx, history, target, stop, hold):
    """Test a strategy and return result"""
    entry = float(history[start_idx]['close'])
    target_price = entry * (1 + target/100)
    stop_price = entry * (1 - stop/100)
    
    for i in range(start_idx+1, min(start_idx+hold+1, len(history))):
        high = float(history[i]['high'])
        low = float(history[i]['low'])
        
        if high >= target_price:
            return target, i - start_idx
        if low <= stop_price:
            return -stop, i - start_idx
    
    if start_idx + hold < len(history):
        close = float(history[start_idx + hold]['close'])
        return (close - entry) / entry * 100, hold
    return 0, hold

def find_optimal_params(ticker, start_idx, history):
    """Find best strategy params for this setup"""
    best_expectancy = -999
    best_params = None
    
    for target in [3, 4, 5, 6, 7, 8]:
        for stop in [2, 3, 4, 5]:
            for hold in [5, 10, 15, 20]:
                results = []
                for i in range(max(0, start_idx-20), start_idx):
                    ret, days = test_strategy(ticker, i, history, target, stop, hold)
                    results.append(ret)
                
                if len(results) >= 10:
                    wins = [r for r in results if r > 0]
                    losses = [r for r in results if r <= 0]
                    wr = len(wins) / len(results)
                    avg_win = np.mean(wins) if wins else 0
                    avg_loss = np.mean(losses) if losses else 0
                    exp = wr * avg_win + (1-wr) * avg_loss
                    
                    if exp > best_expectancy:
                        best_expectancy = exp
                        best_params = (target, stop, hold)
    
    return best_params if best_params else (5, 3, 10)

def build_training_data():
    """Build training dataset"""
    print("Building training data...")
    data = []
    
    for ticker in TICKERS:
        print(f"Processing {ticker}...")
        
        # Batch read price history
        response = price_table.query(
            KeyConditionExpression='ticker = :t',
            ExpressionAttributeValues={':t': ticker},
            ScanIndexForward=True
        )
        history = sorted(response['Items'], key=lambda x: x['date'])
        
        if len(history) < 100:
            continue
        
        # Batch read all features for this ticker
        features_map = get_all_features(ticker)
        
        for i in range(60, len(history) - 30):
            date = history[i]['date']
            features = features_map.get(date)
            
            if not features:
                continue
            
            optimal = find_optimal_params(ticker, i, history)
            
            data.append({
                'ticker': ticker,
                'date': date,
                'rsi': float(features.get('rsi', 50)),
                'volatility': float(features.get('volatility', 0)),
                'return_5d': float(features.get('return_5d', 0)),
                'return_20d': float(features.get('return_20d', 0)),
                'vol_ratio': float(features.get('vol_ratio', 1)),
                'above_ma20': 1 if features.get('above_ma20') else 0,
                'above_ma50': 1 if features.get('above_ma50') else 0,
                'pct_from_high': float(features.get('pct_from_high', 0)),
                'optimal_target': optimal[0],
                'optimal_stop': optimal[1],
                'optimal_hold': optimal[2]
            })
    
    return pd.DataFrame(data)

def train_model():
    """Train the strategy optimizer"""
    print("Training Strategy Optimizer Model\n")
    
    df = build_training_data()
    print(f"Training samples: {len(df)}\n")
    
    if len(df) < 100:
        print("Not enough data!")
        return
    
    feature_cols = ['rsi', 'volatility', 'return_5d', 'return_20d', 'vol_ratio',
                    'above_ma20', 'above_ma50', 'pct_from_high']
    
    X = df[feature_cols]
    
    # Train 3 models: target, stop, hold
    models = {}
    
    for param in ['optimal_target', 'optimal_stop', 'optimal_hold']:
        print(f"Training {param} predictor...")
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
    with open('strategy_optimizer.pkl', 'wb') as f:
        pickle.dump({'models': models, 'features': feature_cols}, f)
    
    print(f"\n✅ Model saved to strategy_optimizer.pkl")

if __name__ == '__main__':
    train_model()

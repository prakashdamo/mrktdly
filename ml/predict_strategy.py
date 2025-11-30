#!/usr/bin/env python3
"""Predict optimal strategy for a ticker using ML model"""
import boto3
import pickle
import sys

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
features_table = dynamodb.Table('mrktdly-features')

def predict_strategy(ticker):
    """Predict optimal strategy parameters"""
    
    # Load model
    with open('strategy_optimizer.pkl', 'rb') as f:
        data = pickle.load(f)
    
    models = data['models']
    feature_cols = data['features']
    
    # Get latest features
    response = features_table.query(
        KeyConditionExpression='ticker = :t',
        ExpressionAttributeValues={':t': ticker},
        ScanIndexForward=False,
        Limit=1
    )
    
    if not response['Items']:
        print(f"No features found for {ticker}")
        return
    
    features = response['Items'][0]
    
    # Prepare input
    X = [[
        float(features.get('rsi', 50)),
        float(features.get('volatility', 0)),
        float(features.get('return_5d', 0)),
        float(features.get('return_20d', 0)),
        float(features.get('vol_ratio', 1)),
        1 if features.get('above_ma20') else 0,
        1 if features.get('above_ma50') else 0,
        float(features.get('pct_from_high', 0))
    ]]
    
    # Predict
    target = models['optimal_target'].predict(X)[0]
    stop = models['optimal_stop'].predict(X)[0]
    hold = models['optimal_hold'].predict(X)[0]
    
    print(f"\n🎯 PREDICTED OPTIMAL STRATEGY FOR {ticker}")
    print(f"{'='*50}")
    print(f"Target:  +{target:.1f}%")
    print(f"Stop:    -{stop:.1f}%")
    print(f"Hold:    {int(hold)} days")
    print(f"\nCurrent Conditions:")
    print(f"  RSI: {float(features.get('rsi', 50)):.1f}")
    print(f"  Volatility: {float(features.get('volatility', 0)):.1f}%")
    print(f"  20d Return: {float(features.get('return_20d', 0)):+.1f}%")
    print(f"  Above MA20: {'Yes' if features.get('above_ma20') else 'No'}")

if __name__ == '__main__':
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'
    predict_strategy(ticker)

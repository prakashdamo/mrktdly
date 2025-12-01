#!/usr/bin/env python3
"""Backtest ML Strategy Optimizer models (old vs new)"""
import boto3
import pickle
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_table = dynamodb.Table('mrktdly-price-history')
feature_table = dynamodb.Table('mrktdly-features')

def load_models():
    """Load both strategy optimizer models"""
    with open('ml/strategy_optimizer.pkl', 'rb') as f:
        old_model = pickle.load(f)
    with open('ml/strategy_optimizer_optimized.pkl', 'rb') as f:
        new_model = pickle.load(f)
    return old_model, new_model

def get_all_features(ticker):
    """Get all features for a ticker"""
    response = feature_table.query(
        KeyConditionExpression='ticker = :t',
        ExpressionAttributeValues={':t': ticker}
    )
    return sorted(response['Items'], key=lambda x: x['date'])

def get_price_history(ticker):
    """Get all price history for ticker"""
    response = price_table.query(
        KeyConditionExpression='ticker = :t',
        ExpressionAttributeValues={':t': ticker}
    )
    return sorted(response['Items'], key=lambda x: x['date'])

def test_trade(history, entry_date, target_pct, stop_pct, hold_days):
    """Test a single trade starting from entry_date"""
    entry_idx = next((i for i, p in enumerate(history) if p['date'] == entry_date), None)
    if entry_idx is None or entry_idx + hold_days >= len(history):
        return None
    
    entry = float(history[entry_idx]['close'])
    target = entry * (1 + target_pct/100)
    stop = entry * (1 - stop_pct/100)
    
    for i in range(entry_idx+1, min(entry_idx+hold_days+1, len(history))):
        high = float(history[i]['high'])
        low = float(history[i]['low'])
        
        if high >= target:
            return target_pct, 'win'
        if low <= stop:
            return -stop_pct, 'loss'
    
    exit_idx = min(entry_idx+hold_days, len(history)-1)
    close = float(history[exit_idx]['close'])
    ret = (close - entry) / entry * 100
    return ret, 'win' if ret > 0 else 'loss'

def backtest_model(model, name, tickers):
    """Backtest a strategy optimizer model"""
    print(f"\n{'='*60}")
    print(f"BACKTESTING: {name}")
    print(f"{'='*60}\n")
    
    all_trades = []
    
    for ticker in tickers:
        features = get_all_features(ticker)
        history = get_price_history(ticker)
        
        if not features or len(history) < 30:
            continue
        
        # Test each feature date
        for feat in features[:50]:  # Test up to 50 per ticker
            # Use only features the model was trained on
            try:
                X = np.array([[float(feat[k]) for k in model['features']]])
            except (ValueError, KeyError):
                continue
            
            # Get ML predictions
            target_pct = max(3, min(10, float(model['models']['optimal_target'].predict(X)[0])))
            stop_pct = max(2, min(5, float(model['models']['optimal_stop'].predict(X)[0])))
            hold_days = max(5, min(20, int(model['models']['optimal_hold'].predict(X)[0])))
            
            # Test trade
            result = test_trade(history, feat['date'], target_pct, stop_pct, hold_days)
            if result:
                ret, outcome = result
                all_trades.append({
                    'ticker': ticker,
                    'date': feat['date'],
                    'return': ret,
                    'outcome': outcome,
                    'target': target_pct,
                    'stop': stop_pct,
                    'hold': hold_days
                })
    
    # Calculate metrics
    if not all_trades:
        print(f"No valid trades (tested {len(tickers)} tickers)\n")
        return None
    
    wins = [t for t in all_trades if t['outcome'] == 'win']
    losses = [t for t in all_trades if t['outcome'] == 'loss']
    
    total = len(all_trades)
    win_rate = len(wins) / total * 100
    avg_return = sum(t['return'] for t in all_trades) / total
    avg_win = sum(t['return'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['return'] for t in losses) / len(losses) if losses else 0
    expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)
    
    print(f"Trades: {total}")
    print(f"Win Rate: {win_rate:.1f}% ({len(wins)}/{total})")
    print(f"Avg Return: {avg_return:+.2f}%")
    print(f"Avg Win: {avg_win:+.2f}%")
    print(f"Avg Loss: {avg_loss:+.2f}%")
    print(f"Expectancy: {expectancy:+.2f}% per trade")
    
    return {
        'trades': total,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'expectancy': expectancy,
        'all_trades': all_trades
    }

def main():
    print("\n🔬 ML STRATEGY OPTIMIZER BACKTEST")
    
    old_model, new_model = load_models()
    
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'JPM', 'BAC', 'JNJ', 'UNH', 'XOM', 'CVX']
    
    old_results = backtest_model(old_model, "OLD MODEL (20 tickers)", test_tickers)
    new_results = backtest_model(new_model, "NEW MODEL (124 tickers)", test_tickers)
    
    if old_results and new_results:
        print(f"\n{'='*60}")
        print("COMPARISON")
        print(f"{'='*60}\n")
        
        print(f"{'Metric':<20} {'Old Model':<15} {'New Model':<15} {'Change'}")
        print("-"*60)
        print(f"{'Trades':<20} {old_results['trades']:<15} {new_results['trades']:<15}")
        print(f"{'Win Rate':<20} {old_results['win_rate']:<14.1f}% {new_results['win_rate']:<14.1f}% {new_results['win_rate']-old_results['win_rate']:+.1f}%")
        print(f"{'Avg Return':<20} {old_results['avg_return']:<14.2f}% {new_results['avg_return']:<14.2f}% {new_results['avg_return']-old_results['avg_return']:+.2f}%")
        print(f"{'Expectancy':<20} {old_results['expectancy']:<14.2f}% {new_results['expectancy']:<14.2f}% {new_results['expectancy']-old_results['expectancy']:+.2f}%")
        
        improvement = ((new_results['expectancy'] - old_results['expectancy']) / abs(old_results['expectancy']) * 100) if old_results['expectancy'] != 0 else 0
        print(f"\n{'Expectancy Improvement:':<20} {improvement:+.1f}%")
        
        if new_results['expectancy'] > old_results['expectancy']:
            print("\n✅ NEW MODEL PERFORMS BETTER - Safe to deploy")
        else:
            print("\n⚠️  OLD MODEL PERFORMS BETTER - Keep current model")

if __name__ == '__main__':
    main()

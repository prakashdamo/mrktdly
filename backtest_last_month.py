#!/usr/bin/env python3
"""Backtest model performance for last month"""
import boto3
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
signals_table = dynamodb.Table('mrktdly-signal-performance')
price_table = dynamodb.Table('mrktdly-price-history')

def get_last_month_signals():
    """Get all signals from last month"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    response = signals_table.scan()
    signals = [s for s in response['Items'] 
               if start_date.strftime('%Y-%m-%d') <= s['signal_date'] <= end_date.strftime('%Y-%m-%d')]
    return signals

def evaluate_signal(signal):
    """Check if signal hit target or stop"""
    ticker = signal['ticker']
    signal_date = signal['signal_date']
    entry = float(signal['entry'])
    target = float(signal['target'])
    stop = float(signal['stop_loss'])
    
    # Get price data after signal
    response = price_table.query(
        KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').gte(signal_date),
        Limit=20
    )
    
    for item in response['Items']:
        high = float(item['high'])
        low = float(item['low'])
        
        if high >= target:
            return 'WIN', ((target - entry) / entry * 100), (datetime.strptime(item['date'], '%Y-%m-%d') - datetime.strptime(signal_date, '%Y-%m-%d')).days
        if low <= stop:
            return 'LOSS', ((stop - entry) / entry * 100), (datetime.strptime(item['date'], '%Y-%m-%d') - datetime.strptime(signal_date, '%Y-%m-%d')).days
    
    return 'OPEN', 0, 0

def main():
    signals = get_last_month_signals()
    
    wins = []
    losses = []
    open_trades = []
    
    for signal in signals:
        outcome, return_pct, days = evaluate_signal(signal)
        
        if outcome == 'WIN':
            wins.append((signal['ticker'], return_pct, days))
        elif outcome == 'LOSS':
            losses.append((signal['ticker'], return_pct, days))
        else:
            open_trades.append(signal['ticker'])
    
    total = len(wins) + len(losses)
    win_rate = len(wins) / total * 100 if total > 0 else 0
    avg_win = sum(r for _, r, _ in wins) / len(wins) if wins else 0
    avg_loss = sum(r for _, r, _ in losses) / len(losses) if losses else 0
    expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)
    
    print(f"\n{'='*60}")
    print(f"LAST MONTH BACKTEST RESULTS")
    print(f"{'='*60}")
    print(f"Total Signals: {len(signals)}")
    print(f"Closed: {total} | Open: {len(open_trades)}")
    print(f"Win Rate: {win_rate:.1f}% ({len(wins)}/{total})")
    print(f"Avg Win: +{avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%")
    print(f"Expectancy: {expectancy:.2f}%")
    print(f"Risk:Reward: {abs(avg_win/avg_loss):.2f}:1" if avg_loss != 0 else "N/A")
    
    if wins:
        print(f"\nWINNERS ({len(wins)}):")
        for ticker, ret, days in sorted(wins, key=lambda x: x[1], reverse=True):
            print(f"  {ticker}: +{ret:.2f}% in {days} days")
    
    if losses:
        print(f"\nLOSSES ({len(losses)}):")
        for ticker, ret, days in sorted(losses, key=lambda x: x[1]):
            print(f"  {ticker}: {ret:.2f}% in {days} days")
    
    if open_trades:
        print(f"\nOPEN ({len(open_trades)}): {', '.join(open_trades)}")

if __name__ == '__main__':
    main()

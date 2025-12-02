#!/usr/bin/env python3
"""Find optimal trading strategy for a specific ticker"""
import boto3
import sys
from datetime import datetime, timedelta
from collections import defaultdict

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_table = dynamodb.Table('mrktdly-price-history')

def get_price_history(ticker, days=180):
    """Get historical price data"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    response = price_table.query(
        KeyConditionExpression='ticker = :t AND #d BETWEEN :start AND :end',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={
            ':t': ticker,
            ':start': start_date.strftime('%Y-%m-%d'),
            ':end': end_date.strftime('%Y-%m-%d')
        }
    )
    return sorted(response['Items'], key=lambda x: x['date'])

def test_strategy(history, target_pct, stop_pct, hold_days):
    """Backtest a specific strategy"""
    wins = []
    losses = []
    
    for i in range(len(history) - hold_days):
        entry = float(history[i]['close'])
        target = entry * (1 + target_pct/100)
        stop = entry * (1 - stop_pct/100)
        
        for j in range(i+1, min(i+hold_days+1, len(history))):
            high = float(history[j]['high'])
            low = float(history[j]['low'])
            
            if high >= target:
                wins.append(target_pct)
                break
            if low <= stop:
                losses.append(-stop_pct)
                break
        else:
            close = float(history[min(i+hold_days, len(history)-1)]['close'])
            ret = (close - entry) / entry * 100
            if ret > 0:
                wins.append(ret)
            else:
                losses.append(ret)
    
    total = len(wins) + len(losses)
    if total == 0:
        return None
    
    win_rate = len(wins) / total * 100
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)
    
    return {
        'target': target_pct,
        'stop': stop_pct,
        'hold_days': hold_days,
        'trades': total,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy,
        'wins': len(wins),
        'losses': len(losses)
    }

def optimize_strategy(ticker):
    """Find best strategy parameters"""
    print(f"🔍 Optimizing strategy for {ticker}...\n")
    
    history = get_price_history(ticker)
    if len(history) < 60:
        print(f"Not enough data for {ticker}")
        return
    
    print(f"Analyzing {len(history)} days of price data\n")
    
    # Test different parameter combinations
    targets = [3, 4, 5, 6, 7, 8]
    stops = [2, 3, 4, 5]
    hold_periods = [5, 7, 10, 15, 20]
    
    results = []
    
    for target in targets:
        for stop in stops:
            for hold in hold_periods:
                result = test_strategy(history, target, stop, hold)
                if result and result['trades'] >= 10:
                    results.append(result)
    
    # Sort by expectancy
    results.sort(key=lambda x: x['expectancy'], reverse=True)
    
    print(f"📊 TOP 10 STRATEGIES (by expectancy):\n")
    print(f"{'Target':<8} {'Stop':<6} {'Hold':<6} {'Trades':<8} {'Win Rate':<10} {'Expectancy':<12} {'R:R'}")
    print("="*75)
    
    for r in results[:10]:
        rr = abs(r['avg_win'] / r['avg_loss']) if r['avg_loss'] != 0 else 0
        print(f"{r['target']:>5}%   {r['stop']:>3}%   {r['hold_days']:>3}d   "
              f"{r['trades']:>5}     {r['win_rate']:>5.1f}%     "
              f"{r['expectancy']:>+6.2f}%      {rr:.2f}:1")
    
    # Best strategy
    best = results[0]
    print(f"\n🏆 OPTIMAL STRATEGY FOR {ticker}:")
    print(f"  Target: +{best['target']}%")
    print(f"  Stop Loss: -{best['stop']}%")
    print(f"  Holding Period: {best['hold_days']} days")
    print(f"  Win Rate: {best['win_rate']:.1f}% ({best['wins']}/{best['trades']})")
    print(f"  Expectancy: {best['expectancy']:+.2f}% per trade")
    print(f"  Risk:Reward: {abs(best['avg_win']/best['avg_loss']):.2f}:1")
    
    # Compare to current strategy (5% target, 3% stop, 10 days)
    current = test_strategy(history, 5, 3, 10)
    if current:
        improvement = ((best['expectancy'] - current['expectancy']) / abs(current['expectancy']) * 100) if current['expectancy'] != 0 else 0
        print(f"\n📈 vs Current Strategy (5% target, 3% stop, 10 days):")
        print(f"  Current Expectancy: {current['expectancy']:+.2f}%")
        print(f"  Improvement: {improvement:+.1f}%")

if __name__ == '__main__':
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'
    optimize_strategy(ticker)

"""
Backtest swing patterns to measure historical performance
"""
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key
import sys
sys.path.append('lambda/swing_scanner')
from handler import (
    detect_consolidation_breakout,
    detect_bull_flag,
    detect_ascending_triangle,
    detect_momentum_alignment,
    detect_volume_breakout
)

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_history_table = dynamodb.Table('mrktdly-price-history')

TICKERS = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'PLTR', 'SMCI']

def backtest_pattern(ticker, test_date, days_forward=30):
    """Test if a signal on test_date would have been profitable"""
    
    # Get historical data
    end_date = datetime.strptime(test_date, '%Y-%m-%d')
    start_date = end_date - timedelta(days=120)
    future_date = end_date + timedelta(days=days_forward + 10)
    
    response = price_history_table.query(
        KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(
            start_date.strftime('%Y-%m-%d'),
            future_date.strftime('%Y-%m-%d')
        ),
        ScanIndexForward=True
    )
    
    all_history = response['Items']
    if len(all_history) < 60:
        return None
    
    # Find index of test_date
    test_idx = None
    for i, item in enumerate(all_history):
        if item['date'] == test_date:
            test_idx = i
            break
    
    if test_idx is None or test_idx < 60:
        return None
    
    # Get history up to test date
    history = all_history[:test_idx + 1][-60:]
    
    # Try each pattern
    signal = None
    pattern_name = None
    
    for detector, name in [
        (detect_consolidation_breakout, 'consolidation_breakout'),
        (detect_bull_flag, 'bull_flag'),
        (detect_ascending_triangle, 'ascending_triangle'),
        (detect_momentum_alignment, 'momentum_alignment'),
        (detect_volume_breakout, 'volume_breakout')
    ]:
        try:
            sig = detector(ticker, history, test_date)
            if sig:
                signal = sig
                pattern_name = name
                break
        except:
            continue
    
    if not signal:
        return None
    
    # Get future prices
    future_history = all_history[test_idx + 1:test_idx + days_forward + 1]
    if len(future_history) < 5:
        return None
    
    entry = float(signal['entry'])
    target = float(signal['target'])
    support = float(signal['support'])
    
    # Track what happened
    max_gain = 0
    max_loss = 0
    hit_target = False
    hit_stop = False
    days_to_target = None
    days_to_stop = None
    
    for i, day in enumerate(future_history):
        high = float(day['high'])
        low = float(day['low'])
        
        gain_pct = ((high - entry) / entry) * 100
        loss_pct = ((low - entry) / entry) * 100
        
        max_gain = max(max_gain, gain_pct)
        max_loss = min(max_loss, loss_pct)
        
        # Check if hit target
        if high >= target and not hit_target:
            hit_target = True
            days_to_target = i + 1
        
        # Check if hit stop
        if low <= support and not hit_stop:
            hit_stop = True
            days_to_stop = i + 1
    
    final_close = float(future_history[-1]['close'])
    final_return = ((final_close - entry) / entry) * 100
    
    return {
        'ticker': ticker,
        'date': test_date,
        'pattern': pattern_name,
        'entry': entry,
        'target': target,
        'support': support,
        'rr': float(signal['risk_reward']),
        'hit_target': hit_target,
        'hit_stop': hit_stop,
        'days_to_target': days_to_target,
        'days_to_stop': days_to_stop,
        'max_gain': max_gain,
        'max_loss': max_loss,
        'final_return': final_return
    }

def run_backtest():
    """Run backtest across multiple dates and tickers"""
    
    # Test dates: every 2 weeks for last 6 months
    test_dates = []
    start = datetime(2025, 6, 1)
    end = datetime(2025, 11, 29)
    current = start
    
    while current <= end:
        test_dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=14)
    
    print(f"Backtesting {len(TICKERS)} tickers across {len(test_dates)} dates...")
    print()
    
    results = []
    signals_found = 0
    
    for test_date in test_dates:
        for ticker in TICKERS:
            result = backtest_pattern(ticker, test_date)
            if result:
                results.append(result)
                signals_found += 1
    
    if not results:
        print("No signals found in backtest period")
        return
    
    # Analyze results by pattern
    patterns = {}
    for r in results:
        pattern = r['pattern']
        if pattern not in patterns:
            patterns[pattern] = []
        patterns[pattern].append(r)
    
    print(f"Found {signals_found} signals across {len(test_dates)} test dates\n")
    print("=" * 80)
    
    for pattern, trades in patterns.items():
        print(f"\n{pattern.upper().replace('_', ' ')}")
        print("-" * 80)
        print(f"Total signals: {len(trades)}")
        
        winners = [t for t in trades if t['hit_target']]
        losers = [t for t in trades if t['hit_stop']]
        
        win_rate = (len(winners) / len(trades)) * 100 if trades else 0
        
        avg_gain = sum(t['max_gain'] for t in trades) / len(trades)
        avg_loss = sum(t['max_loss'] for t in trades) / len(trades)
        avg_final = sum(t['final_return'] for t in trades) / len(trades)
        
        print(f"Win rate (hit target): {win_rate:.1f}%")
        print(f"Stop hit rate: {(len(losers) / len(trades)) * 100:.1f}%")
        print(f"Avg max gain: {avg_gain:.1f}%")
        print(f"Avg max loss: {avg_loss:.1f}%")
        print(f"Avg 30-day return: {avg_final:.1f}%")
        
        if winners:
            avg_days_to_target = sum(t['days_to_target'] for t in winners) / len(winners)
            print(f"Avg days to target: {avg_days_to_target:.1f}")
        
        # Show best trades
        print(f"\nTop 3 trades:")
        sorted_trades = sorted(trades, key=lambda x: x['final_return'], reverse=True)[:3]
        for t in sorted_trades:
            print(f"  {t['ticker']} on {t['date']}: {t['final_return']:.1f}% return (max: {t['max_gain']:.1f}%)")
    
    print("\n" + "=" * 80)
    print(f"\nOVERALL STATS")
    print("-" * 80)
    all_winners = [t for t in results if t['hit_target']]
    all_losers = [t for t in results if t['hit_stop']]
    
    print(f"Total signals: {len(results)}")
    print(f"Overall win rate: {(len(all_winners) / len(results)) * 100:.1f}%")
    print(f"Overall stop rate: {(len(all_losers) / len(results)) * 100:.1f}%")
    print(f"Avg 30-day return: {sum(t['final_return'] for t in results) / len(results):.1f}%")

if __name__ == '__main__':
    run_backtest()

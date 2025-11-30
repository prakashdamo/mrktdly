"""
Backtest last 3 months - show all signals that would have triggered
"""
import boto3
from datetime import datetime, timedelta
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

TICKERS = [
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'AVGO', 'ORCL', 'ADBE',
    'TSM', 'ASML', 'QCOM', 'AMD', 'INTC', 'PLTR', 'SNOW', 'CRWD', 'PANW', 'NOW',
    'JPM', 'BAC', 'V', 'MA', 'COIN', 'UNH', 'LLY', 'ABBV', 'WMT', 'COST',
    'XOM', 'CVX', 'BA', 'CAT', 'GE', 'TSLA', 'RIVN', 'MSTR', 'GME', 'SMCI', 'IONQ', 'RKLB'
]

def scan_date(test_date):
    """Scan all tickers for signals on a specific date"""
    signals = []
    
    for ticker in TICKERS:
        try:
            # Get history
            end_date = datetime.strptime(test_date, '%Y-%m-%d')
            start_date = end_date - timedelta(days=120)
            future_date = end_date + timedelta(days=35)
            
            response = price_history_table.query(
                KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(
                    start_date.strftime('%Y-%m-%d'),
                    future_date.strftime('%Y-%m-%d')
                ),
                ScanIndexForward=True
            )
            
            all_history = response['Items']
            if len(all_history) < 60:
                continue
            
            # Find test date
            test_idx = None
            for i, item in enumerate(all_history):
                if item['date'] == test_date:
                    test_idx = i
                    break
            
            if test_idx is None or test_idx < 60:
                continue
            
            history = all_history[:test_idx + 1][-60:]
            future = all_history[test_idx + 1:test_idx + 31]
            
            # Try each pattern
            for detector, name in [
                (detect_momentum_alignment, 'momentum_alignment'),
                (detect_volume_breakout, 'volume_breakout'),
                (detect_consolidation_breakout, 'consolidation_breakout'),
                (detect_bull_flag, 'bull_flag'),
                (detect_ascending_triangle, 'ascending_triangle')
            ]:
                try:
                    signal = detector(ticker, history, test_date)
                    if signal:
                        # Calculate outcome
                        entry = float(signal['entry'])
                        target = float(signal['target'])
                        support = float(signal['support'])
                        
                        outcome = analyze_outcome(entry, target, support, future)
                        
                        signals.append({
                            'date': test_date,
                            'ticker': ticker,
                            'pattern': name,
                            'entry': entry,
                            'target': target,
                            'support': support,
                            'rr': float(signal['risk_reward']),
                            'outcome': outcome
                        })
                        break
                except:
                    continue
        except:
            continue
    
    return signals

def analyze_outcome(entry, target, support, future):
    """Analyze what happened after signal"""
    if not future:
        return {'status': 'no_data', 'return': 0, 'max_gain': 0, 'max_loss': 0}
    
    max_gain = 0
    max_loss = 0
    hit_target = False
    hit_stop = False
    days_to_target = None
    days_to_stop = None
    
    for i, day in enumerate(future):
        high = float(day['high'])
        low = float(day['low'])
        
        gain = ((high - entry) / entry) * 100
        loss = ((low - entry) / entry) * 100
        
        max_gain = max(max_gain, gain)
        max_loss = min(max_loss, loss)
        
        if high >= target and not hit_target:
            hit_target = True
            days_to_target = i + 1
        
        if low <= support and not hit_stop:
            hit_stop = True
            days_to_stop = i + 1
    
    final_close = float(future[-1]['close'])
    final_return = ((final_close - entry) / entry) * 100
    
    if hit_target:
        status = 'winner'
    elif hit_stop:
        status = 'loser'
    else:
        status = 'open'
    
    return {
        'status': status,
        'return': final_return,
        'max_gain': max_gain,
        'max_loss': max_loss,
        'days_to_target': days_to_target,
        'days_to_stop': days_to_stop
    }

# Scan last 3 months (every week)
print("🔍 BACKTESTING LAST 3 MONTHS")
print("=" * 80)
print()

start_date = datetime(2025, 9, 1)
end_date = datetime(2025, 11, 29)
current = start_date

all_signals = []
dates_scanned = 0

while current <= end_date:
    date_str = current.strftime('%Y-%m-%d')
    print(f"Scanning {date_str}...", end=' ')
    
    signals = scan_date(date_str)
    all_signals.extend(signals)
    dates_scanned += 1
    
    print(f"Found {len(signals)} signals")
    
    current += timedelta(days=7)  # Weekly

print()
print("=" * 80)
print(f"RESULTS: Found {len(all_signals)} signals across {dates_scanned} dates")
print("=" * 80)
print()

if not all_signals:
    print("No signals found in 3-month period")
else:
    # Group by pattern
    by_pattern = {}
    for sig in all_signals:
        pattern = sig['pattern']
        if pattern not in by_pattern:
            by_pattern[pattern] = []
        by_pattern[pattern].append(sig)
    
    # Show all signals
    for pattern, sigs in by_pattern.items():
        print(f"\n{pattern.upper().replace('_', ' ')}: {len(sigs)} signals")
        print("-" * 80)
        
        winners = [s for s in sigs if s['outcome']['status'] == 'winner']
        losers = [s for s in sigs if s['outcome']['status'] == 'loser']
        
        for sig in sigs:
            outcome = sig['outcome']
            status_icon = '✅' if outcome['status'] == 'winner' else '❌' if outcome['status'] == 'loser' else '🔄'
            
            print(f"{status_icon} {sig['date']} - {sig['ticker']}: ${sig['entry']:.2f} → ${sig['target']:.2f}")
            print(f"   R/R: {sig['rr']:.1f}:1 | Return: {outcome['return']:+.1f}% | Max: +{outcome['max_gain']:.1f}%")
            
            if outcome['days_to_target']:
                print(f"   Hit target in {outcome['days_to_target']} days")
            elif outcome['days_to_stop']:
                print(f"   Stopped out in {outcome['days_to_stop']} days")
            print()
        
        if sigs:
            win_rate = (len(winners) / len(sigs)) * 100
            avg_return = sum(s['outcome']['return'] for s in sigs) / len(sigs)
            print(f"Win Rate: {win_rate:.1f}% | Avg Return: {avg_return:+.1f}%")
    
    # Overall stats
    print("\n" + "=" * 80)
    print("OVERALL PERFORMANCE")
    print("=" * 80)
    
    total_winners = sum(1 for s in all_signals if s['outcome']['status'] == 'winner')
    total_losers = sum(1 for s in all_signals if s['outcome']['status'] == 'loser')
    
    print(f"Total signals: {len(all_signals)}")
    print(f"Winners: {total_winners} ({(total_winners/len(all_signals)*100):.1f}%)")
    print(f"Losers: {total_losers} ({(total_losers/len(all_signals)*100):.1f}%)")
    print(f"Avg return: {sum(s['outcome']['return'] for s in all_signals) / len(all_signals):+.1f}%")

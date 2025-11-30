"""
Backtest full year 2025 to identify algorithm improvements
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
    'XOM', 'CVX', 'BA', 'CAT', 'GE', 'RIVN', 'MSTR', 'GME', 'SMCI', 'IONQ', 'RKLB'
]

def scan_date(test_date):
    """Scan all tickers for signals on a specific date"""
    signals = []
    
    for ticker in TICKERS:
        try:
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
            
            test_idx = None
            for i, item in enumerate(all_history):
                if item['date'] == test_date:
                    test_idx = i
                    break
            
            if test_idx is None or test_idx < 60:
                continue
            
            history = all_history[:test_idx + 1][-60:]
            future = all_history[test_idx + 1:test_idx + 31]
            
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

# Scan full year 2025 (every 5 days)
print("🔍 BACKTESTING FULL YEAR 2025")
print("=" * 80)
print()

start_date = datetime(2025, 1, 5)
end_date = datetime(2025, 11, 29)
current = start_date

all_signals = []
dates_scanned = 0

while current <= end_date:
    date_str = current.strftime('%Y-%m-%d')
    print(f"Scanning {date_str}...", end=' ', flush=True)
    
    signals = scan_date(date_str)
    all_signals.extend(signals)
    dates_scanned += 1
    
    print(f"{len(signals)} signals")
    
    current += timedelta(days=5)

print()
print("=" * 80)
print(f"RESULTS: Found {len(all_signals)} signals across {dates_scanned} dates")
print("=" * 80)
print()

if not all_signals:
    print("No signals found")
else:
    # Analyze by pattern
    by_pattern = {}
    for sig in all_signals:
        pattern = sig['pattern']
        if pattern not in by_pattern:
            by_pattern[pattern] = []
        by_pattern[pattern].append(sig)
    
    # Pattern performance
    for pattern, sigs in sorted(by_pattern.items()):
        winners = [s for s in sigs if s['outcome']['status'] == 'winner']
        losers = [s for s in sigs if s['outcome']['status'] == 'loser']
        
        win_rate = (len(winners) / len(sigs)) * 100 if sigs else 0
        avg_return = sum(s['outcome']['return'] for s in sigs) / len(sigs)
        avg_max_gain = sum(s['outcome']['max_gain'] for s in sigs) / len(sigs)
        
        print(f"{pattern.upper().replace('_', ' ')}")
        print(f"  Signals: {len(sigs)}")
        print(f"  Win rate: {win_rate:.1f}%")
        print(f"  Avg return: {avg_return:+.1f}%")
        print(f"  Avg max gain: {avg_max_gain:.1f}%")
        print()
    
    # Overall stats
    print("=" * 80)
    print("OVERALL PERFORMANCE")
    print("=" * 80)
    
    total_winners = [s for s in all_signals if s['outcome']['status'] == 'winner']
    total_losers = [s for s in all_signals if s['outcome']['status'] == 'loser']
    
    print(f"Total signals: {len(all_signals)}")
    print(f"Winners: {len(total_winners)} ({(len(total_winners)/len(all_signals)*100):.1f}%)")
    print(f"Losers: {len(total_losers)} ({(len(total_losers)/len(all_signals)*100):.1f}%)")
    print(f"Avg return: {sum(s['outcome']['return'] for s in all_signals) / len(all_signals):+.1f}%")
    print(f"Avg max gain: {sum(s['outcome']['max_gain'] for s in all_signals) / len(all_signals):.1f}%")
    
    # Recommendations
    print()
    print("=" * 80)
    print("ALGORITHM RECOMMENDATIONS")
    print("=" * 80)
    
    win_rate = (len(total_winners) / len(all_signals)) * 100
    avg_return = sum(s['outcome']['return'] for s in all_signals) / len(all_signals)
    
    if win_rate < 30:
        print("❌ Win rate too low (<30%)")
        print("   → Tighten entry criteria")
        print("   → Add trend filters")
        print("   → Require stronger momentum")
    elif win_rate < 50:
        print("⚠️  Win rate below target (30-50%)")
        print("   → Consider adding filters:")
        print("     - Volume confirmation")
        print("     - Market regime filter (bull/bear)")
        print("     - Sector strength")
    else:
        print("✅ Win rate acceptable (>50%)")
    
    if avg_return < 0:
        print("❌ Negative average return")
        print("   → Widen stops or tighten targets")
        print("   → Add exit rules (trailing stops)")
    elif avg_return < 2:
        print("⚠️  Low average return (<2%)")
        print("   → Optimize R/R ratios")
        print("   → Consider position sizing")
    else:
        print("✅ Positive average return")
    
    # Pattern-specific recommendations
    print()
    print("PATTERN-SPECIFIC:")
    for pattern, sigs in sorted(by_pattern.items()):
        winners = [s for s in sigs if s['outcome']['status'] == 'winner']
        wr = (len(winners) / len(sigs)) * 100 if sigs else 0
        ar = sum(s['outcome']['return'] for s in sigs) / len(sigs)
        
        if wr < 20 or ar < -2:
            print(f"❌ {pattern}: Disable or rework (WR: {wr:.1f}%, Avg: {ar:+.1f}%)")
        elif wr < 40 or ar < 1:
            print(f"⚠️  {pattern}: Needs improvement (WR: {wr:.1f}%, Avg: {ar:+.1f}%)")
        else:
            print(f"✅ {pattern}: Keep as-is (WR: {wr:.1f}%, Avg: {ar:+.1f}%)")

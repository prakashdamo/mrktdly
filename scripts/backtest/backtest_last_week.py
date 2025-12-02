"""
Backtest what signals looked like on Nov 22 and what happened
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

TICKERS = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'PLTR', 'SMCI', 'IONQ', 'RKLB']

def scan_and_backtest(test_date):
    """Scan for signals on test_date and see what happened"""
    
    print(f"Scanning for signals on {test_date}...")
    print("=" * 80)
    
    signals = []
    
    for ticker in TICKERS:
        # Get history up to test date
        end_date = datetime.strptime(test_date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=120)
        future_date = end_date + timedelta(days=10)
        
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
        
        # Find test date index
        test_idx = None
        for i, item in enumerate(all_history):
            if item['date'] == test_date:
                test_idx = i
                break
        
        if test_idx is None or test_idx < 60:
            continue
        
        history = all_history[:test_idx + 1][-60:]
        
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
                    # Get next 5 days
                    future = all_history[test_idx + 1:test_idx + 6]
                    signals.append((signal, future))
                    break
            except Exception as e:
                continue
    
    if not signals:
        print("No signals found\n")
        return
    
    print(f"\nFound {len(signals)} signals:\n")
    
    for signal, future in signals:
        ticker = signal['ticker']
        pattern = signal['pattern']
        entry = float(signal['entry'])
        target = float(signal['target'])
        support = float(signal['support'])
        rr = float(signal['risk_reward'])
        
        print(f"{ticker} - {pattern.replace('_', ' ').title()}")
        print(f"  Entry: ${entry:.2f} | Target: ${target:.2f} | Stop: ${support:.2f} | R/R: {rr:.1f}:1")
        
        if not future:
            print(f"  Result: No data yet (weekend)\n")
            continue
        
        # Check what happened
        max_gain = 0
        max_loss = 0
        hit_target = False
        hit_stop = False
        
        for day in future:
            high = float(day['high'])
            low = float(day['low'])
            
            gain = ((high - entry) / entry) * 100
            loss = ((low - entry) / entry) * 100
            
            max_gain = max(max_gain, gain)
            max_loss = min(max_loss, loss)
            
            if high >= target:
                hit_target = True
            if low <= support:
                hit_stop = True
        
        latest_close = float(future[-1]['close'])
        current_return = ((latest_close - entry) / entry) * 100
        
        if hit_target:
            print(f"  Result: ✅ HIT TARGET (+{max_gain:.1f}% max)")
        elif hit_stop:
            print(f"  Result: ❌ HIT STOP ({max_loss:.1f}% max loss)")
        else:
            print(f"  Result: 🔄 Open - Currently {current_return:+.1f}% (max: +{max_gain:.1f}%)")
        print()

# Test multiple dates
test_dates = ['2025-11-22', '2025-11-20', '2025-11-18']

for date in test_dates:
    scan_and_backtest(date)
    print()

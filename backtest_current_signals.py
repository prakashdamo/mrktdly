"""
Backtest current AAPL and MCD signals
"""
import boto3
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_history_table = dynamodb.Table('mrktdly-price-history')

def backtest_signal(ticker, entry_date, entry_price, target, stop):
    """See what happened after entry"""
    
    end_date = datetime.strptime(entry_date, '%Y-%m-%d')
    start_date = end_date - timedelta(days=5)
    future_date = end_date + timedelta(days=35)
    
    response = price_history_table.query(
        KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(
            start_date.strftime('%Y-%m-%d'),
            future_date.strftime('%Y-%m-%d')
        ),
        ScanIndexForward=True
    )
    
    history = response['Items']
    
    # Find entry index
    entry_idx = None
    for i, item in enumerate(history):
        if item['date'] == entry_date:
            entry_idx = i
            break
    
    if entry_idx is None:
        return None
    
    # Look at next 30 days
    future = history[entry_idx + 1:]
    
    if not future:
        print(f"{ticker}: No future data available")
        return
    
    print(f"\n{ticker} - Entry on {entry_date} at ${entry_price:.2f}")
    print(f"Target: ${target:.2f} (+{((target - entry_price) / entry_price * 100):.1f}%)")
    print(f"Stop: ${stop:.2f} ({((stop - entry_price) / entry_price * 100):.1f}%)")
    print("-" * 60)
    
    max_gain = 0
    max_loss = 0
    hit_target = False
    hit_stop = False
    
    for i, day in enumerate(future[:30]):
        date = day['date']
        high = float(day['high'])
        low = float(day['low'])
        close = float(day['close'])
        
        gain = ((high - entry_price) / entry_price) * 100
        loss = ((low - entry_price) / entry_price) * 100
        close_return = ((close - entry_price) / entry_price) * 100
        
        max_gain = max(max_gain, gain)
        max_loss = min(max_loss, loss)
        
        if high >= target and not hit_target:
            hit_target = True
            print(f"✅ Day {i+1} ({date}): HIT TARGET at ${high:.2f} (+{gain:.1f}%)")
        
        if low <= stop and not hit_stop:
            hit_stop = True
            print(f"❌ Day {i+1} ({date}): HIT STOP at ${low:.2f} ({loss:.1f}%)")
        
        if i == len(future[:30]) - 1:
            print(f"\nDay {i+1} ({date}): Close ${close:.2f} ({close_return:+.1f}%)")
    
    print(f"\nMax gain reached: +{max_gain:.1f}%")
    print(f"Max loss reached: {max_loss:.1f}%")
    
    if hit_target:
        print(f"Result: ✅ TARGET HIT")
    elif hit_stop:
        print(f"Result: ❌ STOPPED OUT")
    else:
        final_close = float(future[min(29, len(future)-1)]['close'])
        final_return = ((final_close - entry_price) / entry_price) * 100
        print(f"Result: 🔄 STILL OPEN ({final_return:+.1f}%)")

# Current signals from scanner
print("=" * 60)
print("BACKTESTING CURRENT SIGNALS")
print("=" * 60)

# AAPL momentum signal
backtest_signal(
    ticker='AAPL',
    entry_date='2025-11-29',
    entry_price=278.85,
    target=306.74,
    stop=264.32
)

# MCD momentum signal
backtest_signal(
    ticker='MCD',
    entry_date='2025-11-29',
    entry_price=311.82,
    target=343.00,
    stop=294.44
)

print("\n" + "=" * 60)

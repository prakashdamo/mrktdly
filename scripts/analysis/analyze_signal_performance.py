import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
signals_table = dynamodb.Table('mrktdly-signal-performance')
price_table = dynamodb.Table('mrktdly-price-history')

def get_current_price(ticker):
    try:
        response = price_table.query(
            KeyConditionExpression='ticker = :ticker',
            ExpressionAttributeValues={':ticker': ticker},
            ScanIndexForward=False,
            Limit=1
        )
        if response['Items']:
            return float(response['Items'][0]['close'])
    except:
        pass
    return None

def get_signals_this_week():
    # Get signals from Nov 25 onwards (this week)
    response = signals_table.scan()
    signals = response['Items']
    
    # Filter for this week
    week_start = '2025-11-25'
    this_week = [s for s in signals if s.get('signal_date', '') >= week_start]
    
    return this_week

signals = get_signals_this_week()

print("=" * 120)
print("SIGNAL PERFORMANCE ANALYSIS - THIS WEEK")
print("=" * 120)
print(f"Analysis Date: December 2, 2025")
print(f"Signals from: November 25 onwards")
print("=" * 120)

open_signals = [s for s in signals if s.get('status') == 'OPEN']
closed_signals = [s for s in signals if s.get('status') in ['EXPIRED', 'STOPPED', 'TARGET_HIT']]

print(f"\nTotal Signals: {len(signals)}")
print(f"Open Signals: {len(open_signals)}")
print(f"Closed Signals: {len(closed_signals)}")

# Analyze open signals
print("\n" + "=" * 120)
print("OPEN SIGNALS - CURRENT STATUS")
print("=" * 120)
print(f"{'Ticker':<8} {'Entry':<10} {'Current':<10} {'Target':<10} {'Stop':<10} {'P/L %':<10} {'Status':<15} {'Days':<6}")
print("-" * 120)

for signal in sorted(open_signals, key=lambda x: x.get('signal_date', '')):
    ticker = signal.get('ticker')
    entry = float(signal.get('entry', 0))
    target = float(signal.get('target', 0))
    stop = float(signal.get('stop_loss', 0))
    signal_date = signal.get('signal_date', '')
    
    current_price = get_current_price(ticker)
    
    if current_price:
        pl_pct = ((current_price - entry) / entry) * 100
        
        # Determine status
        if current_price >= target:
            status = "🎯 TARGET HIT"
        elif current_price <= stop:
            status = "🛑 STOPPED OUT"
        elif pl_pct > 0:
            status = "✅ WINNING"
        else:
            status = "⚠️ LOSING"
        
        # Calculate days held
        try:
            signal_dt = datetime.strptime(signal_date, '%Y-%m-%d')
            days_held = (datetime.now() - signal_dt).days
        except:
            days_held = 0
        
        print(f"{ticker:<8} ${entry:<9.2f} ${current_price:<9.2f} ${target:<9.2f} ${stop:<9.2f} {pl_pct:>9.2f}% {status:<15} {days_held:<6}")
    else:
        print(f"{ticker:<8} ${entry:<9.2f} {'N/A':<10} ${target:<9.2f} ${stop:<9.2f} {'N/A':<10} {'NO DATA':<15} {'N/A':<6}")

# Analyze closed signals
if closed_signals:
    print("\n" + "=" * 120)
    print("CLOSED SIGNALS - FINAL RESULTS")
    print("=" * 120)
    print(f"{'Ticker':<8} {'Entry':<10} {'Exit':<10} {'Return %':<10} {'Outcome':<15} {'Days':<6} {'Date':<12}")
    print("-" * 120)
    
    for signal in sorted(closed_signals, key=lambda x: x.get('signal_date', '')):
        ticker = signal.get('ticker')
        entry = float(signal.get('entry', 0))
        return_pct = float(signal.get('return_pct', 0))
        outcome = signal.get('outcome', 'UNKNOWN')
        days_held = int(signal.get('days_held', 0))
        signal_date = signal.get('signal_date', '')
        
        # Calculate exit price
        exit_price = entry * (1 + return_pct / 100)
        
        print(f"{ticker:<8} ${entry:<9.2f} ${exit_price:<9.2f} {return_pct:>9.2f}% {outcome:<15} {days_held:<6} {signal_date:<12}")

# Summary statistics
print("\n" + "=" * 120)
print("SUMMARY STATISTICS")
print("=" * 120)

# Open signals stats
winning_open = 0
losing_open = 0
total_pl_open = 0

for signal in open_signals:
    ticker = signal.get('ticker')
    entry = float(signal.get('entry', 0))
    current_price = get_current_price(ticker)
    
    if current_price:
        pl_pct = ((current_price - entry) / entry) * 100
        total_pl_open += pl_pct
        if pl_pct > 0:
            winning_open += 1
        else:
            losing_open += 1

# Closed signals stats
total_return_closed = sum(float(s.get('return_pct', 0)) for s in closed_signals)
winning_closed = sum(1 for s in closed_signals if float(s.get('return_pct', 0)) > 0)
losing_closed = len(closed_signals) - winning_closed

print(f"\nOPEN SIGNALS:")
print(f"  Total: {len(open_signals)}")
print(f"  Currently Winning: {winning_open}")
print(f"  Currently Losing: {losing_open}")
if len(open_signals) > 0:
    print(f"  Average P/L: {total_pl_open / len(open_signals):.2f}%")
    print(f"  Win Rate: {winning_open / len(open_signals) * 100:.1f}%")

print(f"\nCLOSED SIGNALS:")
print(f"  Total: {len(closed_signals)}")
print(f"  Winners: {winning_closed}")
print(f"  Losers: {losing_closed}")
if len(closed_signals) > 0:
    print(f"  Average Return: {total_return_closed / len(closed_signals):.2f}%")
    print(f"  Win Rate: {winning_closed / len(closed_signals) * 100:.1f}%")

print(f"\nOVERALL:")
total_signals = len(open_signals) + len(closed_signals)
total_winning = winning_open + winning_closed
print(f"  Total Signals: {total_signals}")
print(f"  Currently/Finally Winning: {total_winning}")
print(f"  Overall Win Rate: {total_winning / total_signals * 100:.1f}%")

# Best and worst performers
print("\n" + "=" * 120)
print("BEST & WORST PERFORMERS")
print("=" * 120)

all_performance = []

for signal in open_signals:
    ticker = signal.get('ticker')
    entry = float(signal.get('entry', 0))
    current_price = get_current_price(ticker)
    if current_price:
        pl_pct = ((current_price - entry) / entry) * 100
        all_performance.append((ticker, pl_pct, 'OPEN'))

for signal in closed_signals:
    ticker = signal.get('ticker')
    return_pct = float(signal.get('return_pct', 0))
    all_performance.append((ticker, return_pct, 'CLOSED'))

all_performance.sort(key=lambda x: x[1], reverse=True)

print("\nTOP 3 PERFORMERS:")
for i, (ticker, pct, status) in enumerate(all_performance[:3], 1):
    print(f"  {i}. {ticker}: {pct:+.2f}% ({status})")

print("\nWORST 3 PERFORMERS:")
for i, (ticker, pct, status) in enumerate(all_performance[-3:], 1):
    print(f"  {i}. {ticker}: {pct:+.2f}% ({status})")

print("\n" + "=" * 120)

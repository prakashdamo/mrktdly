import boto3
from datetime import datetime
from collections import defaultdict

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

def get_signal_pattern(ticker, signal_date, entry):
    """Analyze what pattern/rule generated this signal"""
    try:
        # Get price history before signal
        response = price_table.query(
            KeyConditionExpression='ticker = :ticker AND #d < :date',
            ExpressionAttributeNames={'#d': 'date'},
            ExpressionAttributeValues={':ticker': ticker, ':date': signal_date},
            ScanIndexForward=False,
            Limit=50
        )
        
        if len(response['Items']) < 20:
            return None
        
        prices = sorted(response['Items'], key=lambda x: x['date'])
        closes = [float(p['close']) for p in prices]
        volumes = [float(p['volume']) for p in prices]
        
        # Calculate indicators
        sma20 = sum(closes[-20:]) / 20
        sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma20
        
        # RSI
        gains = [max(closes[i] - closes[i-1], 0) for i in range(-14, 0)]
        losses = [max(closes[i-1] - closes[i], 0) for i in range(-14, 0)]
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        # Volume
        vol_recent = sum(volumes[-5:]) / 5
        vol_older = sum(volumes[-20:-5]) / 15
        vol_surge = ((vol_recent - vol_older) / vol_older * 100) if vol_older > 0 else 0
        
        # Price action
        last_close = closes[-1]
        prev_close = closes[-2]
        daily_change = ((last_close - prev_close) / prev_close * 100)
        
        # Distance from entry
        entry_vs_sma20 = ((entry - sma20) / sma20 * 100)
        
        return {
            'sma20': sma20,
            'sma50': sma50,
            'rsi': rsi,
            'vol_surge': vol_surge,
            'daily_change': daily_change,
            'entry_vs_sma20': entry_vs_sma20,
            'above_sma20': entry > sma20,
            'above_sma50': entry > sma50
        }
    except Exception as e:
        return None

# Get all open signals
response = signals_table.scan()
signals = [s for s in response['Items'] if s.get('status') == 'OPEN']

failing_signals = []
winning_signals = []

for signal in signals:
    ticker = signal.get('ticker')
    entry = float(signal.get('entry', 0))
    current_price = get_current_price(ticker)
    
    if current_price:
        pl_pct = ((current_price - entry) / entry) * 100
        signal_date = signal.get('signal_date', '')
        
        pattern = get_signal_pattern(ticker, signal_date, entry)
        
        signal_info = {
            'ticker': ticker,
            'entry': entry,
            'current': current_price,
            'pl_pct': pl_pct,
            'signal_date': signal_date,
            'source': signal.get('source', 'Unknown'),
            'pattern': pattern
        }
        
        if pl_pct < 0:
            failing_signals.append(signal_info)
        else:
            winning_signals.append(signal_info)

print("=" * 120)
print("FAILING SIGNALS ANALYSIS")
print("=" * 120)
print(f"Total Failing: {len(failing_signals)} out of {len(signals)} open signals")
print("=" * 120)

# Analyze patterns in failing signals
failing_with_pattern = [s for s in failing_signals if s['pattern']]
winning_with_pattern = [s for s in winning_signals if s['pattern']]

print(f"\nSignals with pattern data: {len(failing_with_pattern)} failing, {len(winning_with_pattern)} winning")

if failing_with_pattern:
    # Calculate averages
    avg_rsi_fail = sum(s['pattern']['rsi'] for s in failing_with_pattern) / len(failing_with_pattern)
    avg_rsi_win = sum(s['pattern']['rsi'] for s in winning_with_pattern) / len(winning_with_pattern) if winning_with_pattern else 0
    
    avg_vol_fail = sum(s['pattern']['vol_surge'] for s in failing_with_pattern) / len(failing_with_pattern)
    avg_vol_win = sum(s['pattern']['vol_surge'] for s in winning_with_pattern) / len(winning_with_pattern) if winning_with_pattern else 0
    
    above_sma20_fail = sum(1 for s in failing_with_pattern if s['pattern']['above_sma20'])
    above_sma20_win = sum(1 for s in winning_with_pattern if s['pattern']['above_sma20'])
    
    above_sma50_fail = sum(1 for s in failing_with_pattern if s['pattern']['above_sma50'])
    above_sma50_win = sum(1 for s in winning_with_pattern if s['pattern']['above_sma50'])
    
    print("\n" + "=" * 120)
    print("PATTERN COMPARISON: FAILING vs WINNING")
    print("=" * 120)
    print(f"{'Metric':<30} {'Failing Signals':<25} {'Winning Signals':<25} {'Difference':<20}")
    print("-" * 120)
    print(f"{'Average RSI at Entry':<30} {avg_rsi_fail:<24.1f} {avg_rsi_win:<24.1f} {avg_rsi_fail - avg_rsi_win:<20.1f}")
    print(f"{'Average Volume Surge':<30} {avg_vol_fail:<24.1f}% {avg_vol_win:<24.1f}% {avg_vol_fail - avg_vol_win:<20.1f}%")
    print(f"{'Above SMA20 at Entry':<30} {above_sma20_fail}/{len(failing_with_pattern)} ({above_sma20_fail/len(failing_with_pattern)*100:.1f}%) {above_sma20_win}/{len(winning_with_pattern)} ({above_sma20_win/len(winning_with_pattern)*100:.1f}%) ")
    print(f"{'Above SMA50 at Entry':<30} {above_sma50_fail}/{len(failing_with_pattern)} ({above_sma50_fail/len(failing_with_pattern)*100:.1f}%) {above_sma50_win}/{len(winning_with_pattern)} ({above_sma50_win/len(winning_with_pattern)*100:.1f}%) ")

# Group by source
by_source_fail = defaultdict(list)
by_source_win = defaultdict(list)

for s in failing_signals:
    by_source_fail[s['source']].append(s['pl_pct'])

for s in winning_signals:
    by_source_win[s['source']].append(s['pl_pct'])

print("\n" + "=" * 120)
print("PERFORMANCE BY SOURCE")
print("=" * 120)
print(f"{'Source':<15} {'Failing':<15} {'Winning':<15} {'Fail Rate':<15} {'Avg Loss':<15}")
print("-" * 120)

for source in set(list(by_source_fail.keys()) + list(by_source_win.keys())):
    fail_count = len(by_source_fail[source])
    win_count = len(by_source_win[source])
    total = fail_count + win_count
    fail_rate = (fail_count / total * 100) if total > 0 else 0
    avg_loss = sum(by_source_fail[source]) / fail_count if fail_count > 0 else 0
    
    print(f"{source:<15} {fail_count:<15} {win_count:<15} {fail_rate:<14.1f}% {avg_loss:<14.2f}%")

# Show worst performers
print("\n" + "=" * 120)
print("WORST 10 PERFORMERS")
print("=" * 120)
print(f"{'Ticker':<8} {'Entry':<10} {'Current':<10} {'P/L %':<10} {'Source':<12} {'RSI':<8} {'Vol Surge':<12} {'Above MA20':<12}")
print("-" * 120)

failing_signals.sort(key=lambda x: x['pl_pct'])
for s in failing_signals[:10]:
    pattern = s['pattern']
    if pattern:
        print(f"{s['ticker']:<8} ${s['entry']:<9.2f} ${s['current']:<9.2f} {s['pl_pct']:>9.2f}% {s['source']:<12} {pattern['rsi']:<7.1f} {pattern['vol_surge']:>11.1f}% {str(pattern['above_sma20']):<12}")
    else:
        print(f"{s['ticker']:<8} ${s['entry']:<9.2f} ${s['current']:<9.2f} {s['pl_pct']:>9.2f}% {s['source']:<12} {'N/A':<7} {'N/A':<12} {'N/A':<12}")

print("\n" + "=" * 120)
print("KEY FINDINGS")
print("=" * 120)

if failing_with_pattern and winning_with_pattern:
    findings = []
    
    if avg_rsi_fail > 60:
        findings.append(f"• Failing signals had overbought RSI ({avg_rsi_fail:.1f}) - entering too late")
    elif avg_rsi_fail < 40:
        findings.append(f"• Failing signals had oversold RSI ({avg_rsi_fail:.1f}) - catching falling knives")
    
    if avg_vol_fail < 0:
        findings.append(f"• Failing signals had declining volume ({avg_vol_fail:.1f}%) - weak conviction")
    
    if above_sma20_fail / len(failing_with_pattern) < 0.5:
        findings.append(f"• Only {above_sma20_fail/len(failing_with_pattern)*100:.0f}% of failing signals were above SMA20 - weak trend")
    
    if above_sma50_fail / len(failing_with_pattern) < 0.5:
        findings.append(f"• Only {above_sma50_fail/len(failing_with_pattern)*100:.0f}% of failing signals were above SMA50 - downtrend")
    
    for finding in findings:
        print(finding)

print("\n" + "=" * 120)

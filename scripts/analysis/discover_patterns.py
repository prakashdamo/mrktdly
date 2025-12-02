"""
Analyze 5 years of price data to discover patterns with best win rates
"""
import boto3
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from collections import defaultdict

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_history_table = dynamodb.Table('mrktdly-price-history')

TICKERS = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'PLTR']

def analyze_pattern(ticker, start_date, end_date):
    """Analyze various patterns for a ticker"""
    
    response = price_history_table.query(
        KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(
            start_date, end_date
        ),
        ScanIndexForward=True
    )
    
    history = response['Items']
    if len(history) < 100:
        return []
    
    patterns_found = []
    
    # Test each day as potential entry
    for i in range(60, len(history) - 30):
        entry_date = history[i]['date']
        entry_price = float(history[i]['close'])
        
        # Get context
        past_60 = history[i-60:i+1]
        future_30 = history[i+1:i+31]
        
        if len(future_30) < 20:
            continue
        
        # Calculate indicators
        closes = [float(d['close']) for d in past_60]
        volumes = [float(d['volume']) for d in past_60]
        highs = [float(d['high']) for d in past_60]
        lows = [float(d['low']) for d in past_60]
        
        ma_20 = sum(closes[-20:]) / 20
        ma_50 = sum(closes[-50:]) / 50
        avg_vol = sum(volumes[-20:]) / 20
        
        # Calculate outcome
        max_gain = max((float(d['high']) - entry_price) / entry_price * 100 for d in future_30)
        max_loss = min((float(d['low']) - entry_price) / entry_price * 100 for d in future_30)
        final_return = (float(future_30[-1]['close']) - entry_price) / entry_price * 100
        
        # Pattern 1: New 20-day high with volume
        if entry_price >= max(closes[-20:-1]) and volumes[-1] > avg_vol * 1.5:
            patterns_found.append({
                'pattern': '20d_high_volume',
                'ticker': ticker,
                'date': entry_date,
                'entry': entry_price,
                'max_gain': max_gain,
                'max_loss': max_loss,
                'return': final_return,
                'winner': max_gain >= 10
            })
        
        # Pattern 2: Pullback to 20 MA with RSI < 40
        rsi = calculate_simple_rsi(closes, 14)
        if rsi and 30 < rsi < 40 and abs(entry_price - ma_20) / ma_20 < 0.02:
            patterns_found.append({
                'pattern': 'ma20_pullback_rsi',
                'ticker': ticker,
                'date': entry_date,
                'entry': entry_price,
                'max_gain': max_gain,
                'max_loss': max_loss,
                'return': final_return,
                'winner': max_gain >= 8
            })
        
        # Pattern 3: 3 consecutive higher lows
        if len(lows) >= 15:
            recent_lows = [lows[-15], lows[-10], lows[-5], lows[-1]]
            if all(recent_lows[i] < recent_lows[i+1] for i in range(len(recent_lows)-1)):
                patterns_found.append({
                    'pattern': 'higher_lows_3x',
                    'ticker': ticker,
                    'date': entry_date,
                    'entry': entry_price,
                    'max_gain': max_gain,
                    'max_loss': max_loss,
                    'return': final_return,
                    'winner': max_gain >= 10
                })
        
        # Pattern 4: Gap up that holds
        if i > 0:
            prev_close = float(history[i-1]['close'])
            gap_pct = (entry_price - prev_close) / prev_close * 100
            if gap_pct > 2 and volumes[-1] > avg_vol * 2:
                patterns_found.append({
                    'pattern': 'gap_up_hold',
                    'ticker': ticker,
                    'date': entry_date,
                    'entry': entry_price,
                    'max_gain': max_gain,
                    'max_loss': max_loss,
                    'return': final_return,
                    'winner': max_gain >= 8
                })
        
        # Pattern 5: Tight range breakout (Bollinger squeeze)
        if len(closes) >= 20:
            recent_range = (max(highs[-20:]) - min(lows[-20:])) / min(lows[-20:])
            if recent_range < 0.05 and entry_price > max(highs[-20:-1]):
                patterns_found.append({
                    'pattern': 'tight_range_breakout',
                    'ticker': ticker,
                    'date': entry_date,
                    'entry': entry_price,
                    'max_gain': max_gain,
                    'max_loss': max_loss,
                    'return': final_return,
                    'winner': max_gain >= 10
                })
        
        # Pattern 6: Strong up day after down streak
        if len(closes) >= 5:
            last_5_changes = [(closes[j] - closes[j-1]) / closes[j-1] for j in range(-5, 0)]
            down_days = sum(1 for c in last_5_changes[:-1] if c < 0)
            today_change = (entry_price - closes[-2]) / closes[-2] * 100
            
            if down_days >= 3 and today_change > 2 and volumes[-1] > avg_vol * 1.5:
                patterns_found.append({
                    'pattern': 'reversal_after_decline',
                    'ticker': ticker,
                    'date': entry_date,
                    'entry': entry_price,
                    'max_gain': max_gain,
                    'max_loss': max_loss,
                    'return': final_return,
                    'winner': max_gain >= 8
                })
        
        # Pattern 7: 50-day MA bounce
        if abs(entry_price - ma_50) / ma_50 < 0.02 and entry_price > ma_50:
            patterns_found.append({
                'pattern': 'ma50_bounce',
                'ticker': ticker,
                'date': entry_date,
                'entry': entry_price,
                'max_gain': max_gain,
                'max_loss': max_loss,
                'return': final_return,
                'winner': max_gain >= 8
            })
    
    return patterns_found

def calculate_simple_rsi(prices, period=14):
    """Simple RSI calculation"""
    if len(prices) < period + 1:
        return None
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Analyze patterns
print("🔍 DISCOVERING WINNING PATTERNS FROM 5 YEARS OF DATA")
print("=" * 80)
print()

all_patterns = []

for ticker in TICKERS:
    print(f"Analyzing {ticker}...", flush=True)
    
    # Analyze 2021-2025
    patterns = analyze_pattern(ticker, '2021-01-01', '2025-11-29')
    all_patterns.extend(patterns)
    
    print(f"  Found {len(patterns)} pattern instances")

print()
print("=" * 80)
print(f"TOTAL PATTERN INSTANCES: {len(all_patterns)}")
print("=" * 80)
print()

# Analyze by pattern type
by_pattern = defaultdict(list)
for p in all_patterns:
    by_pattern[p['pattern']].append(p)

# Rank patterns by win rate
pattern_stats = []

for pattern_name, instances in by_pattern.items():
    winners = [p for p in instances if p['winner']]
    win_rate = (len(winners) / len(instances)) * 100 if instances else 0
    avg_return = sum(p['return'] for p in instances) / len(instances)
    avg_max_gain = sum(p['max_gain'] for p in instances) / len(instances)
    avg_max_loss = sum(p['max_loss'] for p in instances) / len(instances)
    
    pattern_stats.append({
        'pattern': pattern_name,
        'count': len(instances),
        'win_rate': win_rate,
        'avg_return': avg_return,
        'avg_max_gain': avg_max_gain,
        'avg_max_loss': avg_max_loss
    })

# Sort by win rate
pattern_stats.sort(key=lambda x: x['win_rate'], reverse=True)

print("PATTERN PERFORMANCE (Sorted by Win Rate)")
print("=" * 80)
print()

for stat in pattern_stats:
    print(f"{stat['pattern'].upper().replace('_', ' ')}")
    print(f"  Instances: {stat['count']}")
    print(f"  Win Rate: {stat['win_rate']:.1f}%")
    print(f"  Avg Return: {stat['avg_return']:+.1f}%")
    print(f"  Avg Max Gain: {stat['avg_max_gain']:.1f}%")
    print(f"  Avg Max Loss: {stat['avg_max_loss']:.1f}%")
    
    if stat['win_rate'] >= 40:
        print(f"  ✅ IMPLEMENT THIS - High win rate!")
    elif stat['win_rate'] >= 30:
        print(f"  ⚠️  Consider implementing")
    else:
        print(f"  ❌ Skip - Low win rate")
    print()

print("=" * 80)
print("TOP 3 PATTERNS TO IMPLEMENT:")
print("=" * 80)

for i, stat in enumerate(pattern_stats[:3], 1):
    print(f"{i}. {stat['pattern'].replace('_', ' ').title()}")
    print(f"   Win Rate: {stat['win_rate']:.1f}% | Avg Return: {stat['avg_return']:+.1f}%")
    print()

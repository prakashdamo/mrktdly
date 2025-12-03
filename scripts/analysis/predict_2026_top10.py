import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def get_prices(ticker, start_date, end_date):
    try:
        response = table.query(
            KeyConditionExpression='ticker = :ticker AND #d BETWEEN :start AND :end',
            ExpressionAttributeNames={'#d': 'date'},
            ExpressionAttributeValues={':ticker': ticker, ':start': start_date, ':end': end_date}
        )
        return sorted(response['Items'], key=lambda x: x['date'])
    except:
        return []

def calculate_technical_score(prices):
    if len(prices) < 200:
        return None
    
    closes = [float(p['close']) for p in prices]
    volumes = [float(p['volume']) for p in prices]
    
    # Current price
    current = closes[-1]
    
    # Moving averages
    sma20 = sum(closes[-20:]) / 20
    sma50 = sum(closes[-50:]) / 50
    sma200 = sum(closes[-200:]) / 200
    
    # RSI
    gains = [max(closes[i] - closes[i-1], 0) for i in range(-14, 0)]
    losses = [max(closes[i-1] - closes[i], 0) for i in range(-14, 0)]
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - (100 / (1 + rs))
    
    # Momentum
    mom_1m = ((closes[-1] - closes[-21]) / closes[-21] * 100) if len(closes) > 21 else 0
    mom_3m = ((closes[-1] - closes[-63]) / closes[-63] * 100) if len(closes) > 63 else 0
    mom_6m = ((closes[-1] - closes[-126]) / closes[-126] * 100) if len(closes) > 126 else 0
    
    # Volume trend
    vol_recent = sum(volumes[-20:]) / 20
    vol_older = sum(volumes[-40:-20]) / 20
    vol_trend = ((vol_recent - vol_older) / vol_older * 100) if vol_older > 0 else 0
    
    # Price position (distance from 52-week high)
    high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
    price_position = (current / high_52w) * 100
    
    # Scoring
    score = 0
    
    # Moving averages (30 points)
    if current > sma20:
        score += 10
    if current > sma50:
        score += 10
    if current > sma200:
        score += 10
    
    # RSI (20 points)
    if 40 <= rsi <= 60:
        score += 20
    elif 30 <= rsi < 40 or 60 < rsi <= 70:
        score += 10
    
    # Momentum (25 points)
    if mom_1m > 0:
        score += 8
    if mom_3m > 5:
        score += 8
    if mom_6m > 10:
        score += 9
    
    # Volume trend (15 points)
    if vol_trend > 10:
        score += 15
    elif vol_trend > 0:
        score += 8
    
    # Price position (10 points)
    if price_position > 90:
        score += 10
    elif price_position > 80:
        score += 5
    
    return {
        'score': score,
        'current': current,
        'sma20': sma20,
        'sma50': sma50,
        'sma200': sma200,
        'rsi': rsi,
        'mom_1m': mom_1m,
        'mom_3m': mom_3m,
        'mom_6m': mom_6m,
        'vol_trend': vol_trend,
        'price_position': price_position
    }

# Expanded ticker list
tickers = [
    'SPY', 'QQQ', 'IWM',
    'PLTR', 'GOOGL', 'TSLA', 'NVDA', 'HIMS', 'AAPL', 'MSFT', 'AMZN', 'META',
    'HOOD', 'SOFI', 'COIN', 'RKLB', 'IONQ',
    'SHOP', 'SQ', 'PYPL', 'ADBE', 'CRM',
    'AMD', 'INTC', 'QCOM', 'AVGO',
    'NFLX', 'DIS', 'SPOT',
    'BA', 'CAT', 'GE',
    'JPM', 'BAC', 'GS', 'V', 'MA',
    'XOM', 'CVX', 'COP',
    'JNJ', 'UNH', 'PFE', 'ABBV',
    'WMT', 'TGT', 'COST', 'HD', 'LOW',
    'XLK', 'XLV', 'XLF', 'XLE', 'XLY', 'XLP'
]

print("=" * 120)
print("2026 PORTFOLIO PREDICTION - TECHNICAL ANALYSIS")
print("=" * 120)
print("Analyzing technical indicators for all available stocks...")
print("=" * 120)

results = []

for ticker in tickers:
    prices = get_prices(ticker, '2024-01-01', '2025-12-02')
    if len(prices) >= 200:
        analysis = calculate_technical_score(prices)
        if analysis:
            results.append({
                'ticker': ticker,
                **analysis
            })

# Sort by score
results.sort(key=lambda x: x['score'], reverse=True)

print(f"\n{'Rank':<6} {'Ticker':<8} {'Score':<8} {'RSI':<8} {'1M Mom':<10} {'3M Mom':<10} {'6M Mom':<10} {'Vol Trend':<12} {'Price Pos':<10}")
print("-" * 120)

for i, r in enumerate(results[:20], 1):
    print(f"{i:<6} {r['ticker']:<8} {r['score']:<8} {r['rsi']:<7.1f} {r['mom_1m']:>9.1f}% {r['mom_3m']:>9.1f}% {r['mom_6m']:>9.1f}% {r['vol_trend']:>11.1f}% {r['price_position']:>9.1f}%")

print("\n" + "=" * 120)
print("TOP 10 PICKS FOR 2026 (Based on Technical Strength)")
print("=" * 120)

top10 = results[:10]

for i, r in enumerate(top10, 1):
    print(f"\n{i}. {r['ticker']} - Score: {r['score']}/100")
    print(f"   Current: ${r['current']:.2f}")
    print(f"   Above SMA20: {'✓' if r['current'] > r['sma20'] else '✗'}")
    print(f"   Above SMA50: {'✓' if r['current'] > r['sma50'] else '✗'}")
    print(f"   Above SMA200: {'✓' if r['current'] > r['sma200'] else '✗'}")
    print(f"   RSI: {r['rsi']:.1f} ({'Neutral' if 40 <= r['rsi'] <= 60 else 'Oversold' if r['rsi'] < 40 else 'Overbought'})")
    print(f"   Momentum: 1M {r['mom_1m']:+.1f}%, 3M {r['mom_3m']:+.1f}%, 6M {r['mom_6m']:+.1f}%")
    print(f"   Volume Trend: {r['vol_trend']:+.1f}%")
    print(f"   Price Position: {r['price_position']:.1f}% of 52-week high")

print("\n" + "=" * 120)
print("SCORING METHODOLOGY")
print("=" * 120)
print("Moving Averages (30 pts): Above SMA20/50/200")
print("RSI (20 pts): Neutral range preferred (40-60)")
print("Momentum (25 pts): Positive 1M/3M/6M returns")
print("Volume Trend (15 pts): Increasing volume")
print("Price Position (10 pts): Near 52-week high")
print("=" * 120)

print("\n" + "=" * 120)
print("DISCLAIMER")
print("=" * 120)
print("This is technical analysis only. Not investment advice.")
print("Based on historical price data through December 2, 2025.")
print("Does not consider fundamentals, valuation, or market conditions.")
print("Past technical strength does not guarantee future performance.")
print("=" * 120)

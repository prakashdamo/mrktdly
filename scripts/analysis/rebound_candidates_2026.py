import boto3

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

def calculate_rebound_score(prices):
    if len(prices) < 200:
        return None
    
    closes = [float(p['close']) for p in prices]
    volumes = [float(p['volume']) for p in prices]
    
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
    
    # Distance from highs
    high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
    high_3m = max(closes[-63:]) if len(closes) >= 63 else max(closes)
    distance_from_high = ((current - high_52w) / high_52w * 100)
    distance_from_3m_high = ((current - high_3m) / high_3m * 100)
    
    # Volume trend
    vol_recent = sum(volumes[-20:]) / 20
    vol_older = sum(volumes[-40:-20]) / 20
    vol_trend = ((vol_recent - vol_older) / vol_older * 100) if vol_older > 0 else 0
    
    # Rebound scoring (looking for oversold with strength)
    score = 0
    
    # RSI oversold (30 points) - key for rebound
    if rsi < 30:
        score += 30
    elif rsi < 35:
        score += 25
    elif rsi < 40:
        score += 20
    elif rsi < 45:
        score += 10
    
    # Still above long-term MA (20 points) - shows underlying strength
    if current > sma200:
        score += 20
    elif current > sma200 * 0.95:
        score += 10
    
    # Recent pullback (25 points) - down from highs
    if distance_from_high < -20:
        score += 25
    elif distance_from_high < -15:
        score += 20
    elif distance_from_high < -10:
        score += 15
    elif distance_from_high < -5:
        score += 10
    
    # But strong 6M momentum (15 points) - was strong before pullback
    if mom_6m > 20:
        score += 15
    elif mom_6m > 10:
        score += 10
    elif mom_6m > 0:
        score += 5
    
    # Volume increasing (10 points) - buying interest
    if vol_trend > 10:
        score += 10
    elif vol_trend > 0:
        score += 5
    
    return {
        'score': score,
        'current': current,
        'rsi': rsi,
        'mom_1m': mom_1m,
        'mom_3m': mom_3m,
        'mom_6m': mom_6m,
        'distance_from_high': distance_from_high,
        'distance_from_3m_high': distance_from_3m_high,
        'above_sma200': current > sma200,
        'vol_trend': vol_trend
    }

tickers = [
    'PLTR', 'GOOGL', 'TSLA', 'NVDA', 'HIMS', 'AAPL', 'MSFT', 'AMZN', 'META',
    'HOOD', 'SOFI', 'COIN', 'RKLB', 'IONQ',
    'SHOP', 'SQ', 'PYPL', 'ADBE', 'CRM',
    'AMD', 'INTC', 'QCOM', 'AVGO', 'MU',
    'NFLX', 'DIS', 'SPOT',
    'BA', 'CAT', 'GE', 'DE',
    'JPM', 'BAC', 'GS', 'V', 'MA', 'C', 'WFC',
    'XOM', 'CVX', 'COP',
    'JNJ', 'UNH', 'PFE', 'ABBV', 'LLY',
    'WMT', 'TGT', 'COST', 'HD', 'LOW',
    'UBER', 'LYFT', 'DASH', 'ABNB'
]

print("=" * 120)
print("2026 REBOUND CANDIDATES - TECHNICAL ANALYSIS")
print("=" * 120)
print("Looking for: Oversold stocks with underlying strength")
print("Criteria: Low RSI + Down from highs + Above 200-day MA + Strong 6M momentum")
print("=" * 120)

results = []

for ticker in tickers:
    prices = get_prices(ticker, '2024-01-01', '2025-12-02')
    if len(prices) >= 200:
        analysis = calculate_rebound_score(prices)
        if analysis:
            results.append({
                'ticker': ticker,
                **analysis
            })

results.sort(key=lambda x: x['score'], reverse=True)

print(f"\n{'Rank':<6} {'Ticker':<8} {'Score':<8} {'RSI':<8} {'From High':<12} {'6M Mom':<10} {'Above 200MA':<12} {'Vol Trend':<12}")
print("-" * 120)

for i, r in enumerate(results[:20], 1):
    above_200 = '✓' if r['above_sma200'] else '✗'
    print(f"{i:<6} {r['ticker']:<8} {r['score']:<8} {r['rsi']:<7.1f} {r['distance_from_high']:>11.1f}% {r['mom_6m']:>9.1f}% {above_200:<12} {r['vol_trend']:>11.1f}%")

print("\n" + "=" * 120)
print("TOP 10 REBOUND CANDIDATES FOR 2026")
print("=" * 120)

top10 = results[:10]

for i, r in enumerate(top10, 1):
    print(f"\n{i}. {r['ticker']} - Rebound Score: {r['score']}/100")
    print(f"   Current Price: ${r['current']:.2f}")
    print(f"   RSI: {r['rsi']:.1f} ({'Oversold' if r['rsi'] < 30 else 'Low' if r['rsi'] < 40 else 'Neutral'})")
    print(f"   Distance from 52-week high: {r['distance_from_high']:.1f}%")
    print(f"   Distance from 3-month high: {r['distance_from_3m_high']:.1f}%")
    print(f"   6-month momentum: {r['mom_6m']:+.1f}%")
    print(f"   Above 200-day MA: {'Yes' if r['above_sma200'] else 'No'}")
    print(f"   Volume trend: {r['vol_trend']:+.1f}%")
    print(f"   Why: ", end='')
    
    reasons = []
    if r['rsi'] < 30:
        reasons.append("Deeply oversold")
    elif r['rsi'] < 40:
        reasons.append("Oversold")
    
    if r['distance_from_high'] < -20:
        reasons.append(f"Down {abs(r['distance_from_high']):.0f}% from highs")
    elif r['distance_from_high'] < -10:
        reasons.append(f"Pulled back {abs(r['distance_from_high']):.0f}%")
    
    if r['mom_6m'] > 20:
        reasons.append("Strong 6M momentum before pullback")
    elif r['mom_6m'] > 0:
        reasons.append("Positive 6M momentum")
    
    if r['above_sma200']:
        reasons.append("Still above 200-day MA")
    
    if r['vol_trend'] > 10:
        reasons.append("Volume increasing")
    
    print(", ".join(reasons))

print("\n" + "=" * 120)
print("SCORING METHODOLOGY")
print("=" * 120)
print("RSI Oversold (30 pts): RSI < 30 = 30pts, < 35 = 25pts, < 40 = 20pts")
print("Above 200-day MA (20 pts): Shows underlying strength despite pullback")
print("Distance from High (25 pts): Down 20%+ = 25pts, 15%+ = 20pts, 10%+ = 15pts")
print("6-Month Momentum (15 pts): Was strong before pullback (20%+ = 15pts)")
print("Volume Trend (10 pts): Increasing volume suggests buying interest")
print("=" * 120)

print("\n" + "=" * 120)
print("KEY CHARACTERISTICS")
print("=" * 120)

avg_rsi = sum(r['rsi'] for r in top10) / len(top10)
avg_pullback = sum(r['distance_from_high'] for r in top10) / len(top10)
avg_6m_mom = sum(r['mom_6m'] for r in top10) / len(top10)
above_200_count = sum(1 for r in top10 if r['above_sma200'])

print(f"Average RSI: {avg_rsi:.1f} (oversold territory)")
print(f"Average pullback from high: {avg_pullback:.1f}%")
print(f"Average 6-month momentum: {avg_6m_mom:+.1f}%")
print(f"Above 200-day MA: {above_200_count}/10")
print("=" * 120)

print("\n" + "=" * 120)
print("DISCLAIMER")
print("=" * 120)
print("These stocks are oversold, not guaranteed to rebound.")
print("Oversold can become more oversold.")
print("Some may be falling for fundamental reasons (bad earnings, business issues).")
print("This is technical analysis only - does not consider fundamentals.")
print("Past pullbacks don't guarantee future rebounds.")
print("Do your own research. Not investment advice.")
print("=" * 120)

#!/usr/bin/env python3
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def get_stock_data(ticker, days=252):
    """Get recent stock data"""
    response = table.query(
        KeyConditionExpression='ticker = :ticker',
        ExpressionAttributeValues={':ticker': ticker},
        ScanIndexForward=False,
        Limit=days
    )
    
    data = []
    for item in response['Items']:
        data.append({
            'date': item['date'],
            'open': float(item['open']),
            'high': float(item['high']),
            'low': float(item['low']),
            'close': float(item['close']),
            'volume': int(item['volume'])
        })
    
    return sorted(data, key=lambda x: x['date'])

def calculate_technicals(data):
    """Calculate comprehensive technical indicators"""
    if len(data) < 200:
        return None
    
    current = data[-1]
    
    # Price metrics
    price_change_1m = ((current['close'] - data[-21]['close']) / data[-21]['close']) * 100
    price_change_3m = ((current['close'] - data[-63]['close']) / data[-63]['close']) * 100
    price_change_6m = ((current['close'] - data[-126]['close']) / data[-126]['close']) * 100
    price_change_1y = ((current['close'] - data[-252]['close']) / data[-252]['close']) * 100
    
    # Moving averages
    sma20 = sum([d['close'] for d in data[-20:]]) / 20
    sma50 = sum([d['close'] for d in data[-50:]]) / 50
    sma200 = sum([d['close'] for d in data[-200:]]) / 200
    
    # RSI
    gains = sum([max(data[i]['close'] - data[i-1]['close'], 0) for i in range(-14, 0)])
    losses = sum([max(data[i-1]['close'] - data[i]['close'], 0) for i in range(-14, 0)])
    rs = gains / losses if losses > 0 else 100
    rsi = 100 - (100 / (1 + rs))
    
    # Volatility (standard deviation of returns)
    returns = [(data[i]['close'] - data[i-1]['close']) / data[i-1]['close'] for i in range(-20, 0)]
    avg_return = sum(returns) / len(returns)
    variance = sum([(r - avg_return) ** 2 for r in returns]) / len(returns)
    volatility = (variance ** 0.5) * 100
    
    # Volume trend
    avg_volume_recent = sum([d['volume'] for d in data[-20:]]) / 20
    avg_volume_older = sum([d['volume'] for d in data[-40:-20]]) / 20
    volume_trend = ((avg_volume_recent - avg_volume_older) / avg_volume_older) * 100
    
    # Trend strength
    above_sma20 = current['close'] > sma20
    above_sma50 = current['close'] > sma50
    above_sma200 = current['close'] > sma200
    golden_cross = sma50 > sma200
    
    # Support/Resistance
    recent_high = max([d['high'] for d in data[-60:]])
    recent_low = min([d['low'] for d in data[-60:]])
    distance_from_high = ((current['close'] - recent_high) / recent_high) * 100
    distance_from_low = ((current['close'] - recent_low) / recent_low) * 100
    
    return {
        'current_price': current['close'],
        'price_change_1m': price_change_1m,
        'price_change_3m': price_change_3m,
        'price_change_6m': price_change_6m,
        'price_change_1y': price_change_1y,
        'sma20': sma20,
        'sma50': sma50,
        'sma200': sma200,
        'rsi': rsi,
        'volatility': volatility,
        'volume_trend': volume_trend,
        'above_sma20': above_sma20,
        'above_sma50': above_sma50,
        'above_sma200': above_sma200,
        'golden_cross': golden_cross,
        'distance_from_high': distance_from_high,
        'distance_from_low': distance_from_low,
        'recent_high': recent_high,
        'recent_low': recent_low
    }

def score_stock(ticker, technicals):
    """Score stock based on technical indicators for 2026 potential"""
    if not technicals:
        return 0, {}
    
    score = 0
    reasons = []
    
    # Momentum scoring (40 points)
    if technicals['price_change_3m'] > 20:
        score += 15
        reasons.append(f"Strong 3M momentum (+{technicals['price_change_3m']:.1f}%)")
    elif technicals['price_change_3m'] > 10:
        score += 10
        reasons.append(f"Good 3M momentum (+{technicals['price_change_3m']:.1f}%)")
    elif technicals['price_change_3m'] > 0:
        score += 5
        reasons.append(f"Positive 3M momentum (+{technicals['price_change_3m']:.1f}%)")
    
    if technicals['price_change_1y'] > 50:
        score += 15
        reasons.append(f"Exceptional 1Y performance (+{technicals['price_change_1y']:.1f}%)")
    elif technicals['price_change_1y'] > 20:
        score += 10
        reasons.append(f"Strong 1Y performance (+{technicals['price_change_1y']:.1f}%)")
    
    if technicals['price_change_1m'] > 5:
        score += 10
        reasons.append(f"Recent strength (+{technicals['price_change_1m']:.1f}% 1M)")
    
    # Trend scoring (30 points)
    if technicals['above_sma200']:
        score += 10
        reasons.append("Above 200-day MA (long-term uptrend)")
    
    if technicals['above_sma50']:
        score += 10
        reasons.append("Above 50-day MA (medium-term uptrend)")
    
    if technicals['golden_cross']:
        score += 10
        reasons.append("Golden cross (50 MA > 200 MA)")
    
    # RSI scoring (15 points)
    if 40 < technicals['rsi'] < 70:
        score += 15
        reasons.append(f"Healthy RSI ({technicals['rsi']:.1f}) - room to run")
    elif 30 < technicals['rsi'] <= 40:
        score += 10
        reasons.append(f"Oversold RSI ({technicals['rsi']:.1f}) - potential bounce")
    elif technicals['rsi'] >= 70:
        score += 5
        reasons.append(f"Overbought RSI ({technicals['rsi']:.1f}) - strong but risky")
    
    # Volume scoring (10 points)
    if technicals['volume_trend'] > 20:
        score += 10
        reasons.append(f"Surging volume (+{technicals['volume_trend']:.1f}%)")
    elif technicals['volume_trend'] > 0:
        score += 5
        reasons.append(f"Increasing volume (+{technicals['volume_trend']:.1f}%)")
    
    # Position scoring (5 points)
    if technicals['distance_from_high'] > -10:
        score += 5
        reasons.append(f"Near 52-week high ({technicals['distance_from_high']:.1f}%)")
    elif technicals['distance_from_low'] > 30:
        score += 3
        reasons.append(f"Well above 52-week low (+{technicals['distance_from_low']:.1f}%)")
    
    return score, reasons

def main():
    tickers = ['PLTR', 'HIMS', 'BB', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
               'COIN', 'MSTR', 'HOOD', 'SOFI', 'RKLB', 'IONQ', 'SMCI', 'ARM']
    
    print("=" * 120)
    print("2026 PORTFOLIO PREDICTION - TECHNICAL ANALYSIS")
    print("Analyzing current technicals to predict best performers for 2026")
    print("=" * 120)
    
    results = []
    
    for ticker in tickers:
        try:
            data = get_stock_data(ticker, 252)
            if len(data) < 200:
                continue
            
            technicals = calculate_technicals(data)
            if not technicals:
                continue
            
            score, reasons = score_stock(ticker, technicals)
            
            results.append({
                'ticker': ticker,
                'score': score,
                'reasons': reasons,
                'technicals': technicals
            })
            
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n" + "=" * 120)
    print("STOCK RANKINGS FOR 2026 POTENTIAL")
    print("=" * 120)
    print(f"{'Rank':<6} {'Ticker':<8} {'Score':<8} {'Price':<10} {'1M':<8} {'3M':<8} {'1Y':<10} {'RSI':<8} {'Trend':<15}")
    print("-" * 120)
    
    for i, r in enumerate(results, 1):
        t = r['technicals']
        trend = "🟢 Strong" if r['score'] >= 70 else "🟡 Moderate" if r['score'] >= 50 else "⚪ Weak"
        print(f"{i:<6} {r['ticker']:<8} {r['score']:<8} ${t['current_price']:<9.2f} {t['price_change_1m']:>+6.1f}% {t['price_change_3m']:>+6.1f}% {t['price_change_1y']:>+8.1f}% {t['rsi']:>6.1f} {trend:<15}")
    
    # Top picks
    top5 = results[:5]
    top3 = results[:3]
    
    print("\n" + "=" * 120)
    print("🏆 TOP 5 PICKS FOR 2026")
    print("=" * 120)
    
    for i, r in enumerate(top5, 1):
        print(f"\n{i}. {r['ticker']} (Score: {r['score']}/100)")
        print(f"   Current Price: ${r['technicals']['current_price']:.2f}")
        print(f"   Key Strengths:")
        for reason in r['reasons'][:5]:
            print(f"   • {reason}")
    
    print("\n" + "=" * 120)
    print("💼 RECOMMENDED 2026 PORTFOLIOS")
    print("=" * 120)
    
    print("\n🚀 AGGRESSIVE (High Risk/High Reward):")
    print(f"   Top 1: 100% {top3[0]['ticker']}")
    print(f"   Expected: High volatility, potential for 50%+ returns")
    
    print("\n⚖️  BALANCED (Moderate Risk):")
    print(f"   Top 3: {top3[0]['ticker']} (40%), {top3[1]['ticker']} (35%), {top3[2]['ticker']} (25%)")
    print(f"   Expected: Diversified growth, 30-50% target")
    
    print("\n🛡️  CONSERVATIVE (Lower Risk):")
    print(f"   Top 5: Equal weight 20% each")
    print(f"   Stocks: {', '.join([r['ticker'] for r in top5])}")
    print(f"   Expected: Stable growth, 20-35% target")
    
    print("\n" + "=" * 120)
    print("📊 TECHNICAL SUMMARY")
    print("=" * 120)
    
    avg_score = sum([r['score'] for r in results]) / len(results)
    strong_stocks = len([r for r in results if r['score'] >= 70])
    
    print(f"• Stocks analyzed: {len(results)}")
    print(f"• Average technical score: {avg_score:.1f}/100")
    print(f"• Strong buy signals: {strong_stocks} stocks")
    print(f"• Market sentiment: {'🟢 Bullish' if avg_score > 60 else '🟡 Neutral' if avg_score > 40 else '🔴 Bearish'}")
    
    print("\n" + "=" * 120)
    print("⚠️  DISCLAIMER")
    print("=" * 120)
    print("This is a technical analysis based on historical data and current trends.")
    print("Past performance does not guarantee future results. Always do your own research.")
    print("Consider your risk tolerance and investment goals before investing.")
    print("=" * 120)

if __name__ == '__main__':
    main()

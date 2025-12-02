#!/usr/bin/env python3
import boto3

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
            'close': float(item['close']),
            'volume': int(item['volume'])
        })
    
    return sorted(data, key=lambda x: x['date'])

def calculate_technicals(data):
    """Calculate technical indicators"""
    if len(data) < 200:
        return None
    
    current = data[-1]
    
    # Price changes
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
    
    # Trend
    above_sma20 = current['close'] > sma20
    above_sma50 = current['close'] > sma50
    above_sma200 = current['close'] > sma200
    golden_cross = sma50 > sma200
    
    # Momentum score
    momentum_score = 0
    if price_change_1m > 0: momentum_score += 1
    if price_change_3m > 0: momentum_score += 2
    if price_change_6m > 0: momentum_score += 2
    if price_change_1y > 0: momentum_score += 3
    if above_sma200: momentum_score += 2
    
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
        'above_sma20': above_sma20,
        'above_sma50': above_sma50,
        'above_sma200': above_sma200,
        'golden_cross': golden_cross,
        'momentum_score': momentum_score
    }

def predict_2026_return(technicals, constituent_avg=None):
    """
    Predict 2026 return based on:
    1. Technical momentum (40%)
    2. Historical pattern (30%)
    3. Constituent performance (30% if available)
    """
    
    # Base prediction from momentum
    momentum_prediction = (
        technicals['price_change_1m'] * 0.1 +
        technicals['price_change_3m'] * 0.3 +
        technicals['price_change_6m'] * 0.3 +
        technicals['price_change_1y'] * 0.3
    )
    
    # Adjust for trend strength
    if technicals['golden_cross'] and technicals['above_sma200']:
        momentum_prediction *= 1.2  # Bullish adjustment
    elif not technicals['above_sma200']:
        momentum_prediction *= 0.8  # Bearish adjustment
    
    # RSI adjustment
    if technicals['rsi'] < 40:
        momentum_prediction *= 1.1  # Oversold = potential bounce
    elif technicals['rsi'] > 70:
        momentum_prediction *= 0.9  # Overbought = potential pullback
    
    # Historical mean reversion (assume 10% annual return as baseline)
    historical_baseline = 10.0
    
    # Combine predictions
    if constituent_avg:
        prediction = (
            momentum_prediction * 0.4 +
            historical_baseline * 0.3 +
            constituent_avg * 0.3
        )
    else:
        prediction = (
            momentum_prediction * 0.6 +
            historical_baseline * 0.4
        )
    
    # Cap predictions at reasonable levels
    prediction = max(-30, min(60, prediction))
    
    return prediction

def main():
    print("=" * 120)
    print("ETF PREDICTIONS FOR 2026 - SPY, QQQ, IWM")
    print("=" * 120)
    
    print("\n📊 METHODOLOGY:")
    print("-" * 120)
    print("1. TECHNICAL ANALYSIS (40% weight)")
    print("   - Recent momentum: 1M, 3M, 6M, 1Y price changes")
    print("   - Trend indicators: Moving averages (20, 50, 200-day)")
    print("   - RSI for overbought/oversold conditions")
    print()
    print("2. HISTORICAL PATTERNS (30% weight)")
    print("   - Long-term market baseline (~10% annual return)")
    print("   - Mean reversion principles")
    print()
    print("3. CONSTITUENT ANALYSIS (30% weight)")
    print("   - Average performance of top holdings")
    print("   - Sector momentum and rotation")
    print()
    print("4. ADJUSTMENTS:")
    print("   - Golden cross (50 MA > 200 MA) = +20% bullish")
    print("   - Below 200 MA = -20% bearish")
    print("   - RSI < 40 (oversold) = +10% bounce potential")
    print("   - RSI > 70 (overbought) = -10% pullback risk")
    print("-" * 120)
    
    # Analyze ETFs
    etfs = {
        'SPY': {
            'name': 'S&P 500 ETF',
            'constituents': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
        },
        'QQQ': {
            'name': 'Nasdaq-100 ETF',
            'constituents': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
        },
        'IWM': {
            'name': 'Russell 2000 ETF',
            'constituents': []  # Small caps - harder to track
        }
    }
    
    results = []
    
    for ticker, info in etfs.items():
        print(f"\n{'='*120}")
        print(f"{ticker} - {info['name']}")
        print('='*120)
        
        try:
            # Get ETF data
            data = get_stock_data(ticker, 252)
            if len(data) < 200:
                print(f"Insufficient data for {ticker}")
                continue
            
            technicals = calculate_technicals(data)
            
            # Calculate constituent average if available
            constituent_avg = None
            if info['constituents']:
                constituent_returns = []
                print(f"\nTop Holdings Analysis:")
                for stock in info['constituents']:
                    try:
                        stock_data = get_stock_data(stock, 252)
                        if len(stock_data) >= 252:
                            stock_return = ((stock_data[-1]['close'] - stock_data[-252]['close']) / 
                                          stock_data[-252]['close']) * 100
                            constituent_returns.append(stock_return)
                            print(f"  {stock}: {stock_return:+.1f}%")
                    except:
                        pass
                
                if constituent_returns:
                    constituent_avg = sum(constituent_returns) / len(constituent_returns)
                    print(f"\nAverage Top Holdings Return (2025): {constituent_avg:+.1f}%")
            
            # Make prediction
            prediction = predict_2026_return(technicals, constituent_avg)
            
            # Calculate target price
            target_price = technicals['current_price'] * (1 + prediction / 100)
            
            print(f"\n📈 CURRENT TECHNICALS:")
            print(f"  Price: ${technicals['current_price']:.2f}")
            print(f"  1M: {technicals['price_change_1m']:+.2f}%")
            print(f"  3M: {technicals['price_change_3m']:+.2f}%")
            print(f"  6M: {technicals['price_change_6m']:+.2f}%")
            print(f"  1Y: {technicals['price_change_1y']:+.2f}%")
            print(f"  RSI: {technicals['rsi']:.1f}")
            print(f"  Above 200 MA: {'✅' if technicals['above_sma200'] else '❌'}")
            print(f"  Golden Cross: {'✅' if technicals['golden_cross'] else '❌'}")
            
            print(f"\n🔮 2026 PREDICTION:")
            print(f"  Expected Return: {prediction:+.1f}%")
            print(f"  Target Price: ${target_price:.2f}")
            print(f"  Confidence: {'🟢 High' if abs(prediction - 10) < 15 else '🟡 Moderate' if abs(prediction - 10) < 25 else '🔴 Low'}")
            
            sentiment = "🟢 Bullish" if prediction > 15 else "🟡 Neutral" if prediction > 5 else "🔴 Bearish"
            print(f"  Sentiment: {sentiment}")
            
            results.append({
                'ticker': ticker,
                'name': info['name'],
                'current_price': technicals['current_price'],
                'prediction': prediction,
                'target_price': target_price,
                'technicals': technicals,
                'constituent_avg': constituent_avg
            })
            
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
    
    # Summary comparison
    print(f"\n{'='*120}")
    print("📊 SUMMARY COMPARISON")
    print('='*120)
    print(f"{'ETF':<8} {'Current':<12} {'2026 Target':<15} {'Expected Return':<18} {'Sentiment':<15}")
    print('-'*120)
    
    for r in sorted(results, key=lambda x: x['prediction'], reverse=True):
        sentiment = "🟢 Bullish" if r['prediction'] > 15 else "🟡 Neutral" if r['prediction'] > 5 else "🔴 Bearish"
        print(f"{r['ticker']:<8} ${r['current_price']:<11.2f} ${r['target_price']:<14.2f} {r['prediction']:>+6.1f}% {sentiment:<15}")
    
    print(f"\n{'='*120}")
    print("💡 INVESTMENT RECOMMENDATIONS")
    print('='*120)
    
    best = max(results, key=lambda x: x['prediction'])
    print(f"\n🏆 BEST PICK: {best['ticker']} ({best['name']})")
    print(f"   Expected Return: {best['prediction']:+.1f}%")
    print(f"   Why: ", end="")
    if best['constituent_avg'] and best['constituent_avg'] > 20:
        print("Strong constituent momentum")
    elif best['technicals']['golden_cross']:
        print("Golden cross formation with strong technicals")
    else:
        print("Favorable technical setup")
    
    print(f"\n📈 ALLOCATION STRATEGY:")
    if len(results) >= 3:
        print(f"   Conservative: 60% {results[0]['ticker']}, 30% {results[1]['ticker']}, 10% {results[2]['ticker']}")
        print(f"   Moderate: 50% {results[0]['ticker']}, 50% {results[1]['ticker']}")
        print(f"   Aggressive: 100% {results[0]['ticker']}")
    
    print(f"\n{'='*120}")

if __name__ == '__main__':
    main()

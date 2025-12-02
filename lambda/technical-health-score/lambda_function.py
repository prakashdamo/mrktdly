import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_table = dynamodb.Table('mrktdly-price-history')
score_table = dynamodb.Table('mrktdly-technical-scores')

def lambda_handler(event, context):
    """
    Calculate technical health score for a ticker
    Score: 0-100 based on multiple technical indicators
    """
    
    # Get ticker from event
    ticker = event.get('ticker')
    if not ticker:
        return {'statusCode': 400, 'body': json.dumps({'error': 'ticker required'})}
    
    try:
        # Get recent price data
        data = get_price_data(ticker, 252)
        
        if len(data) < 50:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Insufficient data'})}
        
        # Calculate score
        score_data = calculate_health_score(data)
        
        # Save to DynamoDB
        save_score(ticker, score_data)
        
        return {
            'statusCode': 200,
            'body': json.dumps(score_data, default=str)
        }
        
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def get_price_data(ticker, days=252):
    """Fetch recent price data"""
    response = price_table.query(
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

def calculate_health_score(data):
    """Calculate 0-100 health score"""
    
    current = data[-1]
    score = 0
    components = {}
    signals = []
    
    # 1. Moving Average Position (30 points)
    sma20 = sum([d['close'] for d in data[-20:]]) / 20
    sma50 = sum([d['close'] for d in data[-50:]]) / 50
    sma200 = sum([d['close'] for d in data[-200:]]) / 200
    
    ma_score = 0
    if current['close'] > sma200:
        ma_score += 10
        signals.append("Above 200-day MA (bullish)")
    else:
        signals.append("Below 200-day MA (bearish)")
    
    if current['close'] > sma50:
        ma_score += 10
        signals.append("Above 50-day MA")
    else:
        signals.append("Below 50-day MA")
    
    if current['close'] > sma20:
        ma_score += 5
        signals.append("Above 20-day MA")
    
    if sma50 > sma200:
        ma_score += 5
        signals.append("Golden cross (50>200)")
    
    score += ma_score
    components['moving_averages'] = ma_score
    
    # 2. RSI (20 points)
    gains = sum([max(data[i]['close'] - data[i-1]['close'], 0) for i in range(-14, 0)])
    losses = sum([max(data[i-1]['close'] - data[i]['close'], 0) for i in range(-14, 0)])
    rs = gains / losses if losses > 0 else 100
    rsi = 100 - (100 / (1 + rs))
    
    rsi_score = 0
    if 40 < rsi < 70:
        rsi_score = 20
        signals.append(f"Healthy RSI ({rsi:.1f})")
    elif 30 < rsi <= 40:
        rsi_score = 15
        signals.append(f"Oversold RSI ({rsi:.1f}) - bounce potential")
    elif rsi >= 70:
        rsi_score = 10
        signals.append(f"Overbought RSI ({rsi:.1f})")
    else:
        rsi_score = 5
        signals.append(f"Very oversold RSI ({rsi:.1f})")
    
    score += rsi_score
    components['rsi'] = rsi_score
    
    # 3. Momentum (25 points)
    momentum_1m = ((current['close'] - data[-21]['close']) / data[-21]['close']) * 100
    momentum_3m = ((current['close'] - data[-63]['close']) / data[-63]['close']) * 100
    momentum_6m = ((current['close'] - data[-126]['close']) / data[-126]['close']) * 100
    
    momentum_score = 0
    if momentum_1m > 5:
        momentum_score += 8
        signals.append(f"Strong 1M momentum (+{momentum_1m:.1f}%)")
    elif momentum_1m > 0:
        momentum_score += 5
    
    if momentum_3m > 10:
        momentum_score += 10
        signals.append(f"Strong 3M momentum (+{momentum_3m:.1f}%)")
    elif momentum_3m > 0:
        momentum_score += 5
    
    if momentum_6m > 0:
        momentum_score += 7
    
    score += momentum_score
    components['momentum'] = momentum_score
    
    # 4. Volume Trend (15 points)
    avg_volume_recent = sum([d['volume'] for d in data[-20:]]) / 20
    avg_volume_older = sum([d['volume'] for d in data[-40:-20]]) / 20
    volume_trend = ((avg_volume_recent - avg_volume_older) / avg_volume_older) * 100
    
    volume_score = 0
    if volume_trend > 20:
        volume_score = 15
        signals.append(f"Surging volume (+{volume_trend:.1f}%)")
    elif volume_trend > 0:
        volume_score = 10
        signals.append(f"Increasing volume (+{volume_trend:.1f}%)")
    elif volume_trend > -20:
        volume_score = 5
    
    score += volume_score
    components['volume'] = volume_score
    
    # 5. Distance from High (10 points)
    recent_high = max([d['close'] for d in data[-60:]])
    distance_from_high = ((current['close'] - recent_high) / recent_high) * 100
    
    high_score = 0
    if distance_from_high > -5:
        high_score = 10
        signals.append(f"Near 60-day high ({distance_from_high:.1f}%)")
    elif distance_from_high > -10:
        high_score = 7
    elif distance_from_high > -15:
        high_score = 4
    
    score += high_score
    components['price_position'] = high_score
    
    # Determine rating
    if score >= 80:
        rating = "Excellent"
        emoji = "🟢"
    elif score >= 60:
        rating = "Good"
        emoji = "🟡"
    elif score >= 40:
        rating = "Fair"
        emoji = "🟠"
    else:
        rating = "Weak"
        emoji = "🔴"
    
    return {
        'ticker': data[-1].get('ticker', 'UNKNOWN'),
        'score': score,
        'rating': rating,
        'emoji': emoji,
        'components': components,
        'signals': signals[:5],  # Top 5 signals
        'technicals': {
            'price': current['close'],
            'sma20': round(sma20, 2),
            'sma50': round(sma50, 2),
            'sma200': round(sma200, 2),
            'rsi': round(rsi, 1),
            'momentum_1m': round(momentum_1m, 2),
            'momentum_3m': round(momentum_3m, 2),
            'volume_trend': round(volume_trend, 2),
            'distance_from_high': round(distance_from_high, 2)
        },
        'timestamp': datetime.now().isoformat()
    }

def save_score(ticker, score_data):
    """Save score to DynamoDB"""
    try:
        score_table.put_item(
            Item={
                'ticker': ticker,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'timestamp': datetime.now().isoformat(),
                'score': Decimal(str(score_data['score'])),
                'rating': score_data['rating'],
                'components': {k: Decimal(str(v)) for k, v in score_data['components'].items()},
                'signals': score_data['signals'],
                'technicals': {k: Decimal(str(v)) for k, v in score_data['technicals'].items()}
            }
        )
    except Exception as e:
        print(f"Error saving score: {e}")

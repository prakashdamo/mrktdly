import json
import boto3
from decimal import Decimal
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')
cache_table = dynamodb.Table('mrktdly-ticker-cache')
price_history_table = dynamodb.Table('mrktdly-price-history')
projections_table = dynamodb.Table('mrktdly-projections')

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """Analyze a single ticker in depth"""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        body = json.loads(event.get('body', '{}'))
        ticker = body.get('ticker', '').upper().strip()
        
        if not ticker:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Ticker symbol required'})
            }
        
        # Check cache first (5 minute TTL)
        cached = get_cached_analysis(ticker)
        if cached:
            print(f'Cache hit for {ticker}')
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(cached, default=decimal_to_float)
            }
        
        # Fetch detailed data for ticker
        ticker_data = fetch_ticker_data(ticker)
        
        if not ticker_data:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': f'Unable to fetch data for {ticker}'})
            }
        
        if ticker_data.get('error'):
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': ticker_data['error']})
            }
        
        if ticker_data.get('price', 0) == 0:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': f'No price data available for {ticker}'})
            }
        
        # Get comprehensive model analysis
        comprehensive = get_comprehensive_analysis(ticker)
        
        # Generate AI analysis (with comprehensive data as context)
        try:
            analysis = generate_ticker_analysis(ticker, ticker_data, comprehensive)
        except Exception as e:
            print(f'Error generating analysis: {e}')
            # Fall back to analysis without comprehensive data
            analysis = generate_ticker_analysis(ticker, ticker_data, None)
        
        # Get projection if available
        projection = get_projection(ticker)
        
        result = {
            'ticker': ticker,
            'data': ticker_data,
            'comprehensive': comprehensive,
            'analysis': analysis,
            'projection': projection
        }
        
        # Cache the result
        cache_analysis(ticker, result)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result, default=decimal_to_float)
        }
        
    except Exception as e:
        print(f'Error: {e}')
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def get_cached_analysis(ticker):
    """Get cached analysis if less than 2 hours old"""
    try:
        response = cache_table.get_item(Key={'ticker': ticker})
        if 'Item' in response:
            item = response['Item']
            cached_time = datetime.fromisoformat(item['timestamp'])
            if datetime.utcnow() - cached_time < timedelta(hours=2):
                return {
                    'ticker': item['ticker'],
                    'data': item['data'],
                    'analysis': item['analysis']
                }
    except Exception as e:
        print(f'Cache read error: {e}')
    return None

def cache_analysis(ticker, result):
    """Cache analysis result"""
    try:
        # Convert floats to Decimals for DynamoDB
        def convert_to_decimal(obj):
            if isinstance(obj, dict):
                return {k: convert_to_decimal(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_decimal(item) for item in obj]
            elif isinstance(obj, float):
                return Decimal(str(obj))
            return obj
        
        cache_table.put_item(Item={
            'ticker': ticker,
            'data': convert_to_decimal(result['data']),
            'analysis': result['analysis'],  # Already strings
            'timestamp': datetime.utcnow().isoformat(),
            'ttl': int((datetime.utcnow() + timedelta(hours=2)).timestamp())  # 2 hour cache
        })
    except Exception as e:
        print(f'Cache write error: {e}')

def get_projection(ticker):
    """Get latest projection for ticker"""
    try:
        response = projections_table.query(
            KeyConditionExpression=Key('ticker').eq(ticker),
            ScanIndexForward=False,
            Limit=1
        )
        if response['Items']:
            proj = response['Items'][0]
            return {
                'current_price': float(proj['current_price']),
                'volatility': float(proj['volatility']),
                'drift': float(proj['drift']),
                'projections': [
                    {
                        'day': int(p['day']),
                        'p10': float(p['p10']),
                        'p25': float(p['p25']),
                        'p50': float(p['p50']),
                        'p75': float(p['p75']),
                        'p90': float(p['p90'])
                    } for p in proj['projections']
                ]
            }
    except Exception as e:
        print(f'Error fetching projection: {e}')
    return None

def get_comprehensive_analysis(ticker):
    """Get comprehensive analysis from ticker-analysis-v2 Lambda"""
    try:
        response = lambda_client.invoke(
            FunctionName='mrktdly-ticker-analysis-v2',
            InvocationType='RequestResponse',
            Payload=json.dumps({'ticker': ticker})
        )
        
        result = json.loads(response['Payload'].read())
        if result.get('statusCode') == 200:
            body_str = result['body']
            if isinstance(body_str, str):
                return json.loads(body_str)
            return body_str
    except Exception as e:
        print(f'Error getting comprehensive analysis: {e}')
    
    return None

def fetch_ticker_data(symbol):
    """Fetch comprehensive data for a single ticker from DynamoDB"""
    try:
        # Get last 90 days of price history from DynamoDB
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        response = price_history_table.query(
            KeyConditionExpression=Key('ticker').eq(symbol) & Key('date').between(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            ),
            ScanIndexForward=True
        )
        
        history = response['Items']
        
        if not history:
            return {'error': f'No data found for {symbol}'}
        
        # Extract data
        closes = [float(d['close']) for d in history]
        highs = [float(d['high']) for d in history]
        lows = [float(d['low']) for d in history]
        volumes = [float(d['volume']) for d in history]
        
        current_price = closes[-1]
        prev_close = closes[-2] if len(closes) > 1 else current_price
        
        # Calculate moving averages
        ma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
        ma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current_price
        
        # 52-week high/low
        high_52w = max(highs)
        low_52w = min(lows)
        
        # Calculate Fibonacci retracement levels from 30-day swing
        swing_high = max(highs[-30:]) if len(highs) >= 30 else max(highs)
        swing_low = min(lows[-30:]) if len(lows) >= 30 else min(lows)
        fib_levels = calculate_fibonacci(swing_high, swing_low)
        
        # Calculate price distribution for heatmap
        price_distribution = calculate_price_distribution(history, high_52w, low_52w)
        
        # Determine trend
        trend = determine_trend(closes, ma_20, ma_50, current_price)
        
        return {
            'price': round(current_price, 2),
            'prev_close': round(prev_close, 2),
            'change': round(current_price - prev_close, 2),
            'change_percent': round((current_price - prev_close) / prev_close * 100, 2),
            'high': round(highs[-1], 2),
            'low': round(lows[-1], 2),
            'volume': int(volumes[-1]),
            'avg_volume': int(sum(volumes[-20:]) / 20) if len(volumes) >= 20 else int(volumes[-1]),
            'high_52w': round(high_52w, 2),
            'low_52w': round(low_52w, 2),
            'ma_20': round(ma_20, 2),
            'ma_50': round(ma_50, 2),
            'high_5d': round(max(highs[-5:]), 2),
            'low_5d': round(min(lows[-5:]), 2),
            'fibonacci': fib_levels,
            'price_distribution': price_distribution,
            'historical_30d': [round(p, 2) for p in closes[-60:]],
            'trend': trend
            }
    except Exception as e:
        print(f'Error fetching {symbol}: {e}')
        return None

def calculate_fibonacci(high, low):
    """Calculate Fibonacci retracement levels"""
    diff = high - low
    return {
        'level_0': round(high, 2),
        'level_236': round(high - (diff * 0.236), 2),
        'level_382': round(high - (diff * 0.382), 2),
        'level_500': round(high - (diff * 0.500), 2),
        'level_618': round(high - (diff * 0.618), 2),
        'level_786': round(high - (diff * 0.786), 2),
        'level_100': round(low, 2),
        'swing_high': round(high, 2),
        'swing_low': round(low, 2)
    }

def calculate_price_distribution(history, high_52w, low_52w):
    """Calculate price distribution for heatmap visualization"""
    # Safety check
    if high_52w <= low_52w or len(history) < 10:
        return None
    
    # Create 20 price buckets from 52w low to high
    num_buckets = 20
    bucket_size = (high_52w - low_52w) / num_buckets
    buckets = [0] * num_buckets
    
    # Count days in each price bucket
    for day in history:
        close = float(day['close'])
        bucket_idx = int((close - low_52w) / bucket_size)
        if 0 <= bucket_idx < num_buckets:
            buckets[bucket_idx] += 1
    
    # Create price levels and counts
    price_levels = []
    for i in range(num_buckets):
        price = low_52w + (i + 0.5) * bucket_size
        price_levels.append({
            'price': round(price, 2),
            'count': buckets[i]
        })
    
    return {
        'levels': price_levels,
        'max_count': max(buckets) if buckets else 1
    }

def determine_trend(closes, ma_20, ma_50, current_price):
    """Determine current trend based on price action and MAs"""
    if len(closes) < 20:
        return {'direction': 'Insufficient Data', 'strength': 'N/A', 'description': 'Need more data'}
    
    # Price vs MAs
    above_ma20 = current_price > ma_20
    above_ma50 = current_price > ma_50
    ma20_above_ma50 = ma_20 > ma_50
    
    # Recent momentum (last 5 vs previous 5 days)
    recent_avg = sum(closes[-5:]) / 5
    prev_avg = sum(closes[-10:-5]) / 5
    momentum = 'Increasing' if recent_avg > prev_avg else 'Decreasing'
    
    # Determine trend
    if above_ma20 and above_ma50 and ma20_above_ma50:
        direction = 'Strong Uptrend'
        strength = 'Strong'
        description = 'Price above both MAs, bullish alignment'
    elif above_ma20 and above_ma50:
        direction = 'Uptrend'
        strength = 'Moderate'
        description = 'Price above MAs, watch for MA crossover'
    elif not above_ma20 and not above_ma50 and not ma20_above_ma50:
        direction = 'Strong Downtrend'
        strength = 'Strong'
        description = 'Price below both MAs, bearish alignment'
    elif not above_ma20 and not above_ma50:
        direction = 'Downtrend'
        strength = 'Moderate'
        description = 'Price below MAs, watch for support'
    else:
        direction = 'Sideways'
        strength = 'Weak'
        description = 'Mixed signals, consolidating'
    
    return {
        'direction': direction,
        'strength': strength,
        'momentum': momentum,
        'description': description
    }


def generate_ticker_analysis(ticker, data, comprehensive=None):
    """Generate comprehensive analysis using Bedrock"""
    
    # Add comprehensive model data to prompt if available
    model_insights = ""
    if comprehensive and isinstance(comprehensive, dict):
        state = comprehensive.get('market_state', {}) or {}
        levels = comprehensive.get('price_levels', {}) or {}
        rec = comprehensive.get('recommendation', {}) or {}
        
        model_insights = f"""

ML MODEL ANALYSIS:
- Market State: {state.get('state', 'Unknown')} ({state.get('confidence', 0)*100:.0f}% confidence)
- Action: {state.get('action', 'UNKNOWN')} ({state.get('conviction', 'unknown')} conviction)
- Support: ${levels.get('support', 'N/A')}
- Resistance: ${levels.get('resistance', 'N/A')}
- Expected 5-day range: ${levels.get('expected_range', {}).get('lower', 'N/A')}-${levels.get('expected_range', {}).get('upper', 'N/A')}
- Recommendation: {rec.get('action', 'UNKNOWN')} (conviction score: {rec.get('conviction_score', 0)})
- Entry: ${rec.get('entry_exit', {}).get('entry', 'N/A')} | Stop: ${rec.get('entry_exit', {}).get('stop_loss', 'N/A')} | Target: ${rec.get('entry_exit', {}).get('target', 'N/A')}
- Risk/Reward: {rec.get('entry_exit', {}).get('risk_reward', 'N/A')}:1
"""
    # Calculate trend explicitly
    price = data['price']
    ma_20 = data['ma_20']
    ma_50 = data['ma_50']
    
    trend_vs_ma20 = "ABOVE" if price > ma_20 else "BELOW"
    trend_vs_ma50 = "ABOVE" if price > ma_50 else "BELOW"
    trend_direction = "bullish" if price > ma_20 and price > ma_50 else "bearish" if price < ma_20 and price < ma_50 else "mixed"
    
    prompt = f"""You are a senior equity analyst with 20+ years of experience. Analyze {ticker} using this data:

Current Price: ${price} (prev ${data['prev_close']}, {data['change_percent']:+.2f}%)
{model_insights}

Price Ranges:
- Today: ${data['low']} - ${data['high']}
- 5-day: ${data['low_5d']} - ${data['high_5d']}
- 52-week: ${data['low_52w']} - ${data['high_52w']}

CRITICAL - 52-Week Range:
- 52-week HIGH: ${data['high_52w']} (resistance)
- 52-week LOW: ${data['low_52w']} (support)
- Current price ${price} is {"near high" if abs(price - data['high_52w']) < 10 else "near low" if abs(price - data['low_52w']) < 10 else "mid-range"}

Moving Averages:
- 20-day MA: ${ma_20}
- 50-day MA: ${ma_50}

Price vs MAs:
- Price ${price} is {trend_vs_ma20} 20-day MA ${ma_20} ({"bullish" if trend_vs_ma20 == "ABOVE" else "bearish"})
- Price ${price} is {trend_vs_ma50} 50-day MA ${ma_50} ({"bullish" if trend_vs_ma50 == "ABOVE" else "bearish"})
- Overall trend: {trend_direction}

Volume:
- Current: {data['volume']:,}
- Average: {data['avg_volume']:,}
- Status: {"Above average" if data['volume'] > data['avg_volume'] else "Below average"}

Provide JSON with:

1. price_action: 2-3 sentences on current position, momentum, and key level proximity
   Example: "{ticker} at ${price}, {"up" if data['change_percent'] > 0 else "down"} {abs(data['change_percent']):.2f}% from ${data['prev_close']}. Trading {"near" if abs(price - data['high_52w']) < 10 else "below"} 52w high of ${data['high_52w']}. Price is {trend_vs_ma20} 20d MA (${ma_20}) and {trend_vs_ma50} 50d MA (${ma_50}), indicating {trend_direction} trend."

2. technical_analysis: 5 bullet points covering:
   - Price vs MAs: "Price ${price} is {trend_vs_ma20} 20d MA ${ma_20} and {trend_vs_ma50} 50d MA ${ma_50} - {trend_direction} trend"
   - 52-week range: "52w range ${data['low_52w']}-${data['high_52w']}. Current ${price} is [calculate position in range]"
   - Support/resistance: Use 52w low ${data['low_52w']} as major support, 52w high ${data['high_52w']} as major resistance
   - Volume analysis: Current {data['volume']:,} vs avg {data['avg_volume']:,} ({"above" if data['volume'] > data['avg_volume'] else "below"} average)
   - Momentum assessment based on actual price movement and trend
   CRITICAL: 52w low is ${data['low_52w']}, NOT ${data['low_5d']}. 52w high is ${data['high_52w']}, NOT ${data['high_5d']}.

3. key_levels: 3-4 specific prices with technical reasoning
   Format: {{"level": "285.50", "note": "52w high - major resistance, multiple rejections here. Break above targets $295-300."}}
   Focus on: 52w high/low, MAs, recent swing points, breakout levels. NOT just "round numbers".

4. trading_considerations: 3-4 actionable points
   - Breakout/breakdown levels to watch (near-term: 5d high/low, MAs)
   - Stop loss zones: MUST be 3-10% from current price, based on recent support (5d low, nearby MA, recent swing low)
     Example for {ticker} at ${price}: Stop loss at ${price * 0.95:.2f} (5% below) or ${data['low_5d']} (5d low)
     DO NOT use 52w low for stop loss - too wide!
   - Price targets: Near-term (5-10% moves) and medium-term based on technical levels
   - Time frame: Short-term (days-weeks) or medium-term (weeks-months)
   Be specific with prices. Stop losses should be practical and tight.

5. risk_assessment: 2-3 current risks
   - Technical risks (overbought, support breaks, etc)
   - Volatility considerations based on recent range
   - Market context risks
   Be specific to current price action.

Rules:
- Use ONLY the exact numbers provided above
- VERIFY: If price < MA, say BELOW. If price > MA, say ABOVE
- Be specific and actionable
- This is educational content only

Return ONLY valid JSON: {{"price_action": "", "technical_analysis": [], "key_levels": [{{"level": "", "note": ""}}], "trading_considerations": [], "risk_assessment": []}}"""

    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 2500,
                'messages': [{
                    'role': 'user',
                    'content': prompt
                }]
            })
        )
        
        result = json.loads(response['body'].read())
        analysis_text = result['content'][0]['text']
        
        # Extract JSON
        start = analysis_text.find('{')
        end = analysis_text.rfind('}') + 1
        if start != -1 and end > 0:
            return json.loads(analysis_text[start:end])
        
        return {'error': 'Unable to parse analysis'}
        
    except Exception as e:
        print(f'Bedrock error: {e}')
        return {
            'price_action': f'{ticker} is currently trading at ${data["price"]}, {"up" if data["change"] > 0 else "down"} {abs(data["change_percent"])}% from previous close.',
            'technical_analysis': [
                f'Price is {"above" if data["price"] > data["ma_20"] else "below"} 20-day MA (${data["ma_20"]})',
                f'52-week range: ${data["low_52w"]} - ${data["high_52w"]}',
                f'Volume: {data["volume"]:,} vs avg {data["avg_volume"]:,}'
            ],
            'key_levels': [
                {'level': str(data['high_52w']), 'note': '52-week high - major resistance'},
                {'level': str(data['low_52w']), 'note': '52-week low - major support'}
            ],
            'trading_considerations': ['Monitor price action at key levels', 'Watch volume for confirmation'],
            'risk_assessment': ['Market volatility', 'Technical levels may not hold']
        }

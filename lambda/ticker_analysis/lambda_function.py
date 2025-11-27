import json
import boto3
import urllib.request
from decimal import Decimal
from datetime import datetime, timedelta

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')
cache_table = dynamodb.Table('mrktdly-ticker-cache')

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
        
        if not ticker_data or ticker_data['price'] == 0:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': f'Unable to fetch data for {ticker}'})
            }
        
        # Generate analysis
        analysis = generate_ticker_analysis(ticker, ticker_data)
        
        result = {
            'ticker': ticker,
            'data': ticker_data,
            'analysis': analysis
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
    """Get cached analysis if less than 5 minutes old"""
    try:
        response = cache_table.get_item(Key={'ticker': ticker})
        if 'Item' in response:
            item = response['Item']
            cached_time = datetime.fromisoformat(item['timestamp'])
            if datetime.utcnow() - cached_time < timedelta(minutes=5):
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
        cache_table.put_item(Item={
            'ticker': ticker,
            'data': result['data'],
            'analysis': result['analysis'],
            'timestamp': datetime.utcnow().isoformat(),
            'ttl': int((datetime.utcnow() + timedelta(minutes=5)).timestamp())
        })
    except Exception as e:
        print(f'Cache write error: {e}')

def fetch_ticker_data(symbol):
    """Fetch comprehensive data for a single ticker"""
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=3mo'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read())
            quote = result['chart']['result'][0]
            meta = quote['meta']
            
            closes = [c for c in quote['indicators']['quote'][0].get('close', []) if c]
            highs = [h for h in quote['indicators']['quote'][0].get('high', []) if h]
            lows = [l for l in quote['indicators']['quote'][0].get('low', []) if l]
            volumes = [v for v in quote['indicators']['quote'][0].get('volume', []) if v]
            
            current_price = closes[-1]
            prev_close = closes[-2] if len(closes) > 1 else current_price
            
            # Calculate moving averages
            ma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
            ma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current_price
            
            # Get 52-week high/low from metadata (actual values from Yahoo)
            high_52w = meta.get('fiftyTwoWeekHigh', max(highs))
            low_52w = meta.get('fiftyTwoWeekLow', min(lows))
            
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
                'low_5d': round(min(lows[-5:]), 2)
            }
    except Exception as e:
        print(f'Error fetching {symbol}: {e}')
        return None

def generate_ticker_analysis(ticker, data):
    """Generate comprehensive analysis using Bedrock"""
    
    # Calculate trend explicitly
    price = data['price']
    ma_20 = data['ma_20']
    ma_50 = data['ma_50']
    
    trend_vs_ma20 = "ABOVE" if price > ma_20 else "BELOW"
    trend_vs_ma50 = "ABOVE" if price > ma_50 else "BELOW"
    trend_direction = "bullish" if price > ma_20 and price > ma_50 else "bearish" if price < ma_20 and price < ma_50 else "mixed"
    
    prompt = f"""You are a senior equity analyst with 20+ years of experience. Analyze {ticker} using this data:

Current Price: ${price} (prev ${data['prev_close']}, {data['change_percent']:+.2f}%)

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

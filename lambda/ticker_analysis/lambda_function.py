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
    
    prompt = f"""You are a senior equity analyst with 20+ years of experience in technical and fundamental analysis. Provide a comprehensive analysis of {ticker}.

Current Data (ALL values are ACTUAL data from Yahoo Finance API - use these exact numbers):
{json.dumps(data, indent=2)}

CRITICAL: Use the EXACT numbers provided above. Do NOT make up or estimate any values.
- 52-week high: ${data['high_52w']} (actual from API)
- 52-week low: ${data['low_52w']} (actual from API)  
- Current price: ${data['price']}
- 20-day MA: ${data['ma_20']}
- 50-day MA: ${data['ma_50']}
- Today's high: ${data['high']}, low: ${data['low']}
- Volume: {data['volume']:,} vs avg {data['avg_volume']:,}

Provide a detailed analysis with these sections:

1. **Price Action Summary** (2-3 sentences): Current price context, recent momentum, position relative to key levels.

2. **Technical Analysis** (4-5 bullet points): 
   - Support and resistance levels (use actual data: 52w high/low, 5d high/low, moving averages)
   - Trend analysis (price vs MA20, MA50)
   - Volume analysis (current vs average)
   - Key technical patterns or setups
   - Momentum indicators

3. **Key Levels to Watch** (3-4 specific price levels):
   - Each with price and reasoning
   - Include both support and resistance
   - Use actual data points (52w high/low, MAs, recent swing points)

4. **Trading Considerations** (3-4 points):
   - What to watch for (breakouts, breakdowns, volume confirmation)
   - Risk levels (stop loss considerations)
   - Potential targets
   - Time frame considerations

5. **Risk Assessment** (2-3 points):
   - Key risks specific to current price action
   - Volatility considerations
   - Market context

Use ACTUAL numbers from the data provided. Be specific and actionable. This is educational content only.

Return ONLY valid JSON with keys: price_action, technical_analysis (array), key_levels (array of objects with level/note), trading_considerations (array), risk_assessment (array)"""

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

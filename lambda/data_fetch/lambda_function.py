import json
import os
import boto3
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('mrktdly-data')
price_history_table = dynamodb.Table('mrktdly-price-history')

def is_market_open():
    """Check if market is open (skip weekends and major holidays)"""
    from datetime import datetime
    import pytz
    
    # Get current time in ET
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    
    # Skip weekends (Saturday=5, Sunday=6)
    if now_et.weekday() >= 5:
        return False
    
    # Major market holidays (approximate dates, market closed)
    holidays_2025 = [
        (1, 1),   # New Year's Day
        (1, 20),  # MLK Day
        (2, 17),  # Presidents Day
        (4, 18),  # Good Friday
        (5, 26),  # Memorial Day
        (6, 19),  # Juneteenth
        (7, 4),   # Independence Day
        (9, 1),   # Labor Day
        (11, 27), # Thanksgiving
        (12, 25), # Christmas
    ]
    
    current_date = (now_et.month, now_et.day)
    if current_date in holidays_2025:
        return False
    
    return True

def lambda_handler(event, context):
    """Fetches market data at 7:00 AM ET"""
    
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Check if market is open by testing SPY
    if not is_market_open():
        print(f"Market closed on {date_key}, skipping data fetch")
        return {'statusCode': 200, 'body': json.dumps('Market closed')}
    
    # Fetch market data (using free Yahoo Finance API)
    market_data = fetch_market_data()
    
    # Fetch news
    news = fetch_news()
    
    # Store in DynamoDB
    table.put_item(Item={
        'pk': f'DATA#{date_key}',
        'sk': 'MARKET',
        'date': date_key,
        'market_data': market_data,
        'news': news,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    # Store price history for each ticker
    store_price_history(market_data, date_key)
    
    # Trigger unusual-activity lambda
    lambda_client = boto3.client('lambda')
    lambda_client.invoke(
        FunctionName='mrktdly-unusual-activity',
        InvocationType='Event'
    )
    
    return {'statusCode': 200, 'body': json.dumps('Data fetched')}

def fetch_market_data():
    """Fetch key market data from Yahoo Finance"""
    # Core indices and ETFs
    symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO']
    futures = ['ES=F', 'NQ=F', 'YM=F', 'RTY=F', 'CL=F', 'GC=F', 'SI=F', 'NG=F']
    
    # Mega cap tech (Magnificent 7 + key tech)
    mega_tech = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'AVGO', 'ORCL', 'ADBE', 'CRM', 'NFLX', 'AMD', 'INTC', 'CSCO', 'IBM', 'UBER', 'SHOP']
    
    # Semiconductors
    semis = ['TSM', 'ASML', 'QCOM', 'TXN', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'ARM', 'MCHP', 'ON']
    
    # AI/Cloud/Software
    ai_cloud = ['PLTR', 'SNOW', 'DDOG', 'NET', 'CRWD', 'ZS', 'PANW', 'WDAY', 'NOW', 'TEAM', 'MDB', 'HUBS', 'AI', 'SOUN']
    
    # Financials
    financials = ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL', 'SQ', 'COIN', 'HOOD', 'NU', 'SOFI']
    
    # Healthcare/Biotech
    healthcare = ['UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'BMY', 'AMGN', 'GILD', 'VRTX', 'REGN', 'MRNA', 'BNTX']
    
    # Consumer/Retail
    consumer = ['AMZN', 'WMT', 'COST', 'HD', 'TGT', 'LOW', 'NKE', 'SBUX', 'MCD', 'DIS', 'BKNG', 'ABNB', 'BABA', 'PDD']
    
    # Energy
    energy = ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL']
    
    # Industrials/Aerospace
    industrials = ['BA', 'CAT', 'GE', 'RTX', 'LMT', 'HON', 'UPS', 'UNP', 'DE', 'MMM', 'NOC', 'GD']
    
    # EV/Auto
    ev_auto = ['TSLA', 'F', 'GM', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI']
    
    # Crypto-related
    crypto = ['COIN', 'MSTR', 'RIOT', 'MARA', 'CLSK', 'HOOD']
    
    # Meme/High volatility
    meme = ['GME', 'AMC', 'BB', 'BBBY', 'APE', 'SNAP']
    
    # Small cap leaders
    small_caps = ['RKLB', 'IONQ', 'SMCI', 'APP', 'CVNA', 'UPST', 'SOFI', 'AFRM', 'NBIS', 'HIMS']
    
    # Telecom/Communication
    telecom = ['T', 'VZ', 'TMUS']
    
    # Media/Entertainment
    media = ['DIS', 'NFLX', 'WBD']
    
    # Commodities/ETFs
    commodities = ['GLD', 'SLV', 'USO']
    
    # REITs
    reits = ['O', 'SPG', 'PLD']
    
    # Combine and deduplicate
    all_tickers = list(set(
        symbols + futures + mega_tech + semis + ai_cloud + financials + 
        healthcare + consumer + energy + industrials + ev_auto + crypto + 
        meme + small_caps + telecom + media + commodities + reits
    ))
    
    data = {}
    
    # Fetch all tickers
    for symbol in all_tickers:
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d'
            if not url.startswith('https://'):
                raise ValueError('Only HTTPS URLs are allowed')
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                result = json.loads(response.read())
                quote = result['chart']['result'][0]
                meta = quote['meta']
                
                # Get historical closes and other data
                closes = quote['indicators']['quote'][0].get('close', [])
                highs = quote['indicators']['quote'][0].get('high', [])
                lows = quote['indicators']['quote'][0].get('low', [])
                volumes = quote['indicators']['quote'][0].get('volume', [])
                
                # Filter out None values and get last two valid closes
                valid_closes = [c for c in closes if c is not None and c > 0]
                valid_highs = [h for h in highs if h is not None and h > 0]
                valid_lows = [l for l in lows if l is not None and l > 0]
                valid_volumes = [v for v in volumes if v is not None and v > 0]
                
                if len(valid_closes) >= 2:
                    current_price = valid_closes[-1]  # Most recent close
                    prev_close = valid_closes[-2]     # Previous day close
                elif len(valid_closes) == 1:
                    current_price = valid_closes[-1]
                    prev_close = meta.get('previousClose', valid_closes[-1])
                else:
                    current_price = meta.get('regularMarketPrice', 0)
                    prev_close = meta.get('previousClose', current_price)
                
                # Get high/low/volume for today
                today_high = valid_highs[-1] if valid_highs else current_price
                today_low = valid_lows[-1] if valid_lows else current_price
                today_volume = valid_volumes[-1] if valid_volumes else 0
                avg_volume = sum(valid_volumes[-10:]) / len(valid_volumes[-10:]) if len(valid_volumes) >= 10 else today_volume
                
                # Calculate 5-day high/low
                high_5d = max(valid_highs[-5:]) if len(valid_highs) >= 5 else today_high
                low_5d = min(valid_lows[-5:]) if len(valid_lows) >= 5 else today_low
                
                change = round(current_price - prev_close, 2)
                change_pct = round((change / prev_close) * 100, 2) if prev_close > 0 else 0
                
                data[symbol] = {
                    'price': Decimal(str(round(current_price, 2))),
                    'change': Decimal(str(change)),
                    'change_percent': Decimal(str(change_pct)),
                    'high': Decimal(str(round(today_high, 2))),
                    'low': Decimal(str(round(today_low, 2))),
                    'volume': int(today_volume),
                    'avg_volume': int(avg_volume),
                    'high_5d': Decimal(str(round(high_5d, 2))),
                    'low_5d': Decimal(str(round(low_5d, 2))),
                    'prev_close': Decimal(str(round(prev_close, 2)))
                }
                print(f'{symbol}: ${current_price:.2f} (prev: ${prev_close:.2f}, change: {change_pct:.2f}%)')
        except Exception as e:
            print(f'Error fetching {symbol}: {e}')
            data[symbol] = {
                'price': Decimal('0'), 'change': Decimal('0'), 'change_percent': Decimal('0'),
                'high': Decimal('0'), 'low': Decimal('0'), 'volume': 0, 'avg_volume': 0,
                'high_5d': Decimal('0'), 'low_5d': Decimal('0'), 'prev_close': Decimal('0')
            }
    
    print(f'Successfully fetched {len([v for v in data.values() if v["price"] > 0])} out of {len(all_tickers)} tickers')
    return data

def fetch_news():
    """Fetch top 5 finance news from Yahoo Finance"""
    try:
        url = 'https://finance.yahoo.com/news/'
        if not url.startswith('https://'):
            raise ValueError('Only HTTPS URLs are allowed')
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
            html = response.read().decode('utf-8')
            
        # Simple parsing for news items
        news_items = []
        import re
        
        # Look for news article patterns in Yahoo Finance
        pattern = r'<h3[^>]*><a[^>]*href="([^"]*)"[^>]*>([^<]+)</a></h3>'
        matches = re.findall(pattern, html)
        
        for url, title in matches[:5]:
            if url.startswith('/'):
                url = f'https://finance.yahoo.com{url}'
            news_items.append({'title': title, 'url': url})
        
        print(f'Fetched {len(news_items)} news items')
        return news_items if news_items else get_fallback_news()
        
    except Exception as e:
        print(f'Error fetching news: {e}')
        return get_fallback_news()

def get_fallback_news():
    """Fallback news if fetch fails"""
    return [
        {'title': 'Market Update: Check Yahoo Finance for latest news', 'url': 'https://finance.yahoo.com'},
        {'title': 'Economic Calendar: Monitor key data releases', 'url': 'https://finance.yahoo.com/calendar'},
        {'title': 'Earnings Reports: Track company earnings', 'url': 'https://finance.yahoo.com/calendar/earnings'},
        {'title': 'Market Analysis: Review technical indicators', 'url': 'https://finance.yahoo.com'},
        {'title': 'Trading Education: Continue learning market fundamentals', 'url': 'https://finance.yahoo.com'}
    ]

def store_price_history(market_data, date_key):
    """Store daily price data for each ticker in price history table"""
    stored_count = 0
    
    for ticker, data in market_data.items():
        try:
            # Skip if no valid price data
            if data['price'] == 0:
                continue
            
            # Calculate open from previous close + change
            open_price = float(data['prev_close'])
            close_price = float(data['price'])
            high_price = float(data['high'])
            low_price = float(data['low'])
            volume = int(data['volume'])
            
            price_history_table.put_item(Item={
                'ticker': ticker,
                'date': date_key,
                'open': Decimal(str(round(open_price, 2))),
                'high': Decimal(str(round(high_price, 2))),
                'low': Decimal(str(round(low_price, 2))),
                'close': Decimal(str(round(close_price, 2))),
                'volume': volume,
                'adj_close': Decimal(str(round(close_price, 2))),  # Same as close for now
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            stored_count += 1
            
        except Exception as e:
            print(f'Error storing price history for {ticker}: {e}')
    
    print(f'Stored price history for {stored_count} tickers on {date_key}')
    return stored_count

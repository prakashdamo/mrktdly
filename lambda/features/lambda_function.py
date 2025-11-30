import json
import boto3
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')
price_history_table = dynamodb.Table('mrktdly-price-history')
features_table = dynamodb.Table('mrktdly-features')

def lambda_handler(event, context):
    """Calculate technical features for all tickers"""
    
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Use hardcoded ticker list (same as data-fetch)
    tickers = [
        'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO',
        'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'AVGO', 'ORCL', 'ADBE', 'CRM', 'NFLX', 'AMD', 'INTC',
        'TSM', 'ASML', 'QCOM', 'TXN', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'ARM', 'MCHP', 'ON',
        'PLTR', 'SNOW', 'DDOG', 'NET', 'CRWD', 'ZS', 'PANW', 'WDAY', 'NOW', 'TEAM', 'MDB', 'HUBS',
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL', 'COIN', 'HOOD',
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'BMY', 'AMGN', 'GILD', 'VRTX', 'REGN',
        'WMT', 'COST', 'HD', 'TGT', 'LOW', 'NKE', 'SBUX', 'MCD', 'DIS', 'BKNG', 'ABNB',
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL',
        'BA', 'CAT', 'GE', 'RTX', 'LMT', 'HON', 'UPS', 'UNP', 'DE', 'MMM',
        'F', 'GM', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI',
        'MSTR', 'RIOT', 'MARA', 'CLSK',
        'GME', 'AMC',
        'RKLB', 'IONQ', 'SMCI', 'APP', 'CVNA', 'UPST', 'SOFI', 'AFRM'
    ]
    
    print(f'Processing {len(tickers)} tickers for {date_key}')
    
    features_calculated = 0
    for ticker in tickers:  # Process all tickers
        try:
            features = calculate_features(ticker, date_key)
            if features:
                store_features(ticker, date_key, features)
                features_calculated += 1
                if features_calculated % 10 == 0:
                    print(f'Progress: {features_calculated}/{len(tickers)}')
        except Exception as e:
            print(f'✗ {ticker}: {e}')
    
    print(f'Calculated features for {features_calculated} tickers')
    return {'statusCode': 200, 'body': json.dumps(f'Processed {features_calculated} tickers')}

def calculate_features(ticker, date_key):
    """Calculate technical indicators for a ticker"""
    
    # Get 260 days of history (1 year)
    end_date = date_key
    start_date = (datetime.strptime(date_key, '%Y-%m-%d') - timedelta(days=400)).strftime('%Y-%m-%d')
    
    response = price_history_table.query(
        KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(start_date, end_date),
        Limit=260,
        ScanIndexForward=False
    )
    
    history = response.get('Items', [])
    if len(history) < 50:
        return None
    
    # Sort by date descending (most recent first)
    history.sort(key=lambda x: x['date'], reverse=True)
    
    # Extract data
    closes = [float(h['close']) for h in history]
    highs = [float(h['high']) for h in history]
    lows = [float(h['low']) for h in history]
    volumes = [int(h.get('volume', 0)) for h in history]
    
    current_price = closes[0]
    
    # Moving Averages
    ma_5 = sum(closes[:5]) / 5 if len(closes) >= 5 else current_price
    ma_10 = sum(closes[:10]) / 10 if len(closes) >= 10 else current_price
    ma_20 = sum(closes[:20]) / 20 if len(closes) >= 20 else current_price
    ma_50 = sum(closes[:50]) / 50 if len(closes) >= 50 else current_price
    ma_200 = sum(closes[:200]) / 200 if len(closes) >= 200 else current_price
    
    # RSI (14-day)
    rsi = calculate_rsi(closes[:15]) if len(closes) >= 15 else 50
    
    # MACD
    macd, signal, histogram = calculate_macd(closes[:35]) if len(closes) >= 35 else (0, 0, 0)
    
    # Bollinger Bands (20-day, 2 std)
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes[:20]) if len(closes) >= 20 else (current_price, current_price, current_price)
    
    # Volume indicators
    vol_20 = sum(volumes[:20]) / 20 if len(volumes) >= 20 else volumes[0]
    vol_ratio = volumes[0] / vol_20 if vol_20 > 0 else 1
    
    # Price momentum
    return_1d = (closes[0] - closes[1]) / closes[1] * 100 if len(closes) > 1 else 0
    return_5d = (closes[0] - closes[5]) / closes[5] * 100 if len(closes) > 5 else 0
    return_20d = (closes[0] - closes[20]) / closes[20] * 100 if len(closes) > 20 else 0
    
    # Volatility (20-day std)
    volatility = calculate_std(closes[:20]) if len(closes) >= 20 else 0
    
    # Price position
    high_52w = max(closes[:252]) if len(closes) >= 252 else current_price
    low_52w = min(closes[:252]) if len(closes) >= 252 else current_price
    pct_from_high = (current_price - high_52w) / high_52w * 100 if high_52w > 0 else 0
    pct_from_low = (current_price - low_52w) / low_52w * 100 if low_52w > 0 else 0
    
    # Trend indicators
    above_ma20 = 1 if current_price > ma_20 else 0
    above_ma50 = 1 if current_price > ma_50 else 0
    above_ma200 = 1 if current_price > ma_200 else 0
    ma_alignment = 1 if ma_20 > ma_50 > ma_200 else 0
    
    # Average True Range (ATR)
    atr = calculate_atr(highs[:15], lows[:15], closes[:15]) if len(closes) >= 15 else 0
    
    return {
        'price': str(current_price),
        'ma_5': str(round(ma_5, 2)),
        'ma_10': str(round(ma_10, 2)),
        'ma_20': str(round(ma_20, 2)),
        'ma_50': str(round(ma_50, 2)),
        'ma_200': str(round(ma_200, 2)),
        'rsi': str(round(rsi, 2)),
        'macd': str(round(macd, 4)),
        'macd_signal': str(round(signal, 4)),
        'macd_histogram': str(round(histogram, 4)),
        'bb_upper': str(round(bb_upper, 2)),
        'bb_middle': str(round(bb_middle, 2)),
        'bb_lower': str(round(bb_lower, 2)),
        'volume': str(volumes[0]),
        'vol_20_avg': str(int(vol_20)),
        'vol_ratio': str(round(vol_ratio, 2)),
        'return_1d': str(round(return_1d, 2)),
        'return_5d': str(round(return_5d, 2)),
        'return_20d': str(round(return_20d, 2)),
        'volatility': str(round(volatility, 2)),
        'high_52w': str(round(high_52w, 2)),
        'low_52w': str(round(low_52w, 2)),
        'pct_from_high': str(round(pct_from_high, 2)),
        'pct_from_low': str(round(pct_from_low, 2)),
        'above_ma20': str(above_ma20),
        'above_ma50': str(above_ma50),
        'above_ma200': str(above_ma200),
        'ma_alignment': str(ma_alignment),
        'atr': str(round(atr, 2))
    }

def calculate_rsi(closes, period=14):
    """Calculate RSI"""
    if len(closes) < period + 1:
        return 50
    
    gains = []
    losses = []
    
    for i in range(len(closes) - 1):
        change = closes[i] - closes[i + 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(closes):
    """Calculate MACD (12, 26, 9)"""
    if len(closes) < 26:
        return 0, 0, 0
    
    ema_12 = calculate_ema(closes, 12)
    ema_26 = calculate_ema(closes, 26)
    macd = ema_12 - ema_26
    
    # Signal line (9-day EMA of MACD)
    signal = macd * 0.2  # Simplified
    histogram = macd - signal
    
    return macd, signal, histogram

def calculate_ema(closes, period):
    """Calculate EMA"""
    if len(closes) < period:
        return closes[0]
    
    multiplier = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    
    for price in closes[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema

def calculate_bollinger_bands(closes, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    if len(closes) < period:
        return closes[0], closes[0], closes[0]
    
    middle = sum(closes[:period]) / period
    std = calculate_std(closes[:period])
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return upper, middle, lower

def calculate_std(values):
    """Calculate standard deviation"""
    if len(values) < 2:
        return 0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5

def calculate_atr(highs, lows, closes, period=14):
    """Calculate Average True Range"""
    if len(highs) < period + 1:
        return 0
    
    true_ranges = []
    for i in range(len(highs) - 1):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i + 1])
        low_close = abs(lows[i] - closes[i + 1])
        true_ranges.append(max(high_low, high_close, low_close))
    
    return sum(true_ranges[:period]) / period

def store_features(ticker, date_key, features):
    """Store features in DynamoDB"""
    features_table.put_item(Item={
        'ticker': ticker,
        'date': date_key,
        **features,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

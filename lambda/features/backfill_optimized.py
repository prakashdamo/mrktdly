"""
Optimized backfill - batch reads to reduce cost
"""
import boto3
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
import time

dynamodb = boto3.resource('dynamodb')
price_history_table = dynamodb.Table('mrktdly-price-history')
features_table = dynamodb.Table('mrktdly-features')

# Import feature calculation functions
import sys
sys.path.append('.')
from lambda_function import (
    calculate_rsi, calculate_macd, calculate_ema, 
    calculate_bollinger_bands, calculate_std, calculate_atr
)

TICKERS = [
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

def calculate_features_from_history(history, date_idx):
    """Calculate features for a specific date using pre-loaded history"""
    
    # Get data from date_idx onwards (most recent first)
    closes = [float(h['close']) for h in history[date_idx:]]
    highs = [float(h['high']) for h in history[date_idx:]]
    lows = [float(h['low']) for h in history[date_idx:]]
    volumes = [int(h.get('volume', 0)) for h in history[date_idx:]]
    
    if len(closes) < 50:
        return None
    
    current_price = closes[0]
    
    # Moving Averages
    ma_5 = sum(closes[:5]) / 5 if len(closes) >= 5 else current_price
    ma_10 = sum(closes[:10]) / 10 if len(closes) >= 10 else current_price
    ma_20 = sum(closes[:20]) / 20 if len(closes) >= 20 else current_price
    ma_50 = sum(closes[:50]) / 50 if len(closes) >= 50 else current_price
    ma_200 = sum(closes[:200]) / 200 if len(closes) >= 200 else current_price
    
    # RSI
    rsi = calculate_rsi(closes[:15]) if len(closes) >= 15 else 50
    
    # MACD
    macd, signal, histogram = calculate_macd(closes[:35]) if len(closes) >= 35 else (0, 0, 0)
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes[:20]) if len(closes) >= 20 else (current_price, current_price, current_price)
    
    # Volume
    vol_20 = sum(volumes[:20]) / 20 if len(volumes) >= 20 else volumes[0]
    vol_ratio = volumes[0] / vol_20 if vol_20 > 0 else 1
    
    # Returns
    return_1d = (closes[0] - closes[1]) / closes[1] * 100 if len(closes) > 1 else 0
    return_5d = (closes[0] - closes[5]) / closes[5] * 100 if len(closes) > 5 else 0
    return_20d = (closes[0] - closes[20]) / closes[20] * 100 if len(closes) > 20 else 0
    
    # Volatility
    volatility = calculate_std(closes[:20]) if len(closes) >= 20 else 0
    
    # 52-week high/low
    high_52w = max(closes[:252]) if len(closes) >= 252 else current_price
    low_52w = min(closes[:252]) if len(closes) >= 252 else current_price
    pct_from_high = (current_price - high_52w) / high_52w * 100 if high_52w > 0 else 0
    pct_from_low = (current_price - low_52w) / low_52w * 100 if low_52w > 0 else 0
    
    # Trend
    above_ma20 = 1 if current_price > ma_20 else 0
    above_ma50 = 1 if current_price > ma_50 else 0
    above_ma200 = 1 if current_price > ma_200 else 0
    ma_alignment = 1 if ma_20 > ma_50 > ma_200 else 0
    
    # ATR
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

def backfill_optimized(days=252):
    """Optimized backfill with batched reads"""
    
    print(f'🚀 Starting optimized 1-year backfill')
    print(f'Tickers: {len(TICKERS)}')
    print(f'Days: {days}')
    print(f'Estimated records: {len(TICKERS) * days}')
    print()
    
    total_processed = 0
    total_with_labels = 0
    start_time = time.time()
    
    for i, ticker in enumerate(TICKERS, 1):
        print(f'[{i}/{len(TICKERS)}] {ticker}...', end=' ', flush=True)
        
        try:
            # SINGLE QUERY: Get all history for ticker (batched read!)
            response = price_history_table.query(
                KeyConditionExpression=Key('ticker').eq(ticker),
                ScanIndexForward=False,
                Limit=days + 260  # Extra for calculations + future lookups
            )
            
            history = sorted(response.get('Items', []), key=lambda x: x['date'], reverse=True)
            
            if len(history) < 50:
                print('❌ Not enough data')
                continue
            
            ticker_processed = 0
            ticker_labeled = 0
            
            # Process each date (except last 5 - no future data)
            for date_idx in range(len(history) - 5):
                date = history[date_idx]['date']
                
                # Calculate features using pre-loaded history
                features = calculate_features_from_history(history, date_idx)
                if not features:
                    continue
                
                # Calculate label (5 days forward)
                if date_idx >= 5:
                    current_price = float(history[date_idx]['close'])
                    future_price = float(history[date_idx - 5]['close'])  # 5 days later
                    future_return = (future_price - current_price) / current_price * 100
                    
                    features['label'] = str(1 if future_return > 3 else 0)
                    features['future_return_5d'] = str(round(future_return, 2))
                    ticker_labeled += 1
                
                # Store
                features_table.put_item(Item={
                    'ticker': ticker,
                    'date': date,
                    **features,
                    'timestamp': datetime.now().isoformat()
                })
                
                ticker_processed += 1
            
            total_processed += ticker_processed
            total_with_labels += ticker_labeled
            
            print(f'✓ {ticker_processed} records ({ticker_labeled} labeled)')
            
        except Exception as e:
            print(f'❌ Error: {e}')
    
    elapsed = time.time() - start_time
    
    print()
    print(f'✅ Backfill complete!')
    print(f'Time: {elapsed/60:.1f} minutes')
    print(f'Total records: {total_processed:,}')
    print(f'Records with labels: {total_with_labels:,}')
    print(f'Label rate: {total_with_labels/total_processed*100:.1f}%')
    print(f'Speed: {total_processed/elapsed:.0f} records/second')

if __name__ == '__main__':
    backfill_optimized(days=252)

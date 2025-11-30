"""
Backfill historical features and add labels for ML training
"""
import boto3
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
import time

dynamodb = boto3.resource('dynamodb')
price_history_table = dynamodb.Table('mrktdly-price-history')
features_table = dynamodb.Table('mrktdly-features')

# Import feature calculation from lambda
import sys
sys.path.append('.')
from lambda_function import calculate_features

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

def get_future_return(ticker, date, days_forward=5):
    """Get return N days in the future"""
    try:
        # Get price on date
        response = price_history_table.get_item(Key={'ticker': ticker, 'date': date})
        if 'Item' not in response:
            return None
        current_price = float(response['Item']['close'])
        
        # Get price N days later
        future_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=days_forward+7)).strftime('%Y-%m-%d')
        start_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=days_forward-2)).strftime('%Y-%m-%d')
        
        # Query range to find next trading day
        response = price_history_table.query(
            KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(start_date, future_date),
            Limit=10,
            ScanIndexForward=True
        )
        
        items = response.get('Items', [])
        if len(items) < 2:
            return None
        
        # Find item closest to days_forward
        target_date = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=days_forward)
        closest_item = min(items[1:], key=lambda x: abs((datetime.strptime(x['date'], '%Y-%m-%d') - target_date).days))
        
        future_price = float(closest_item['close'])
        return_pct = (future_price - current_price) / current_price * 100
        
        return return_pct
    except Exception as e:
        print(f'Error getting future return for {ticker} {date}: {e}')
        return None

def backfill_features(days=252):
    """Backfill features for past N days"""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f'Backfilling features from {start_date.date()} to {end_date.date()}')
    print(f'Tickers: {len(TICKERS)}')
    print(f'Estimated records: {len(TICKERS) * days}')
    print()
    
    total_processed = 0
    total_with_labels = 0
    
    for ticker in TICKERS:
        print(f'Processing {ticker}...')
        
        # Get all dates for this ticker
        response = price_history_table.query(
            KeyConditionExpression=Key('ticker').eq(ticker),
            ScanIndexForward=False,
            Limit=days + 50  # Extra for future lookups
        )
        
        dates = sorted([item['date'] for item in response.get('Items', [])])
        
        # Process each date (except last 5 days - no future data for labels)
        for date in dates[:-5]:
            try:
                # Calculate features
                features = calculate_features(ticker, date)
                if not features:
                    continue
                
                # Calculate label (5-day forward return)
                future_return = get_future_return(ticker, date, days_forward=5)
                
                if future_return is not None:
                    # Binary label: 1 if >3%, else 0
                    label = 1 if future_return > 3 else 0
                    features['label'] = str(label)
                    features['future_return_5d'] = str(round(future_return, 2))
                    total_with_labels += 1
                
                # Store features
                features_table.put_item(Item={
                    'ticker': ticker,
                    'date': date,
                    **features,
                    'timestamp': datetime.now().isoformat()
                })
                
                total_processed += 1
                
                if total_processed % 100 == 0:
                    print(f'  Progress: {total_processed} records ({total_with_labels} with labels)')
                
            except Exception as e:
                print(f'  Error on {date}: {e}')
        
        # Rate limiting
        time.sleep(0.5)
    
    print()
    print(f'✅ Backfill complete!')
    print(f'Total records: {total_processed}')
    print(f'Records with labels: {total_with_labels}')
    print(f'Label rate: {total_with_labels/total_processed*100:.1f}%')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=252, help='Number of days to backfill')
    args = parser.parse_args()
    
    backfill_features(args.days)

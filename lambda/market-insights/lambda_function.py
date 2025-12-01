"""
Market Insights API - Generate beautiful visualizations from historical data
"""
import json
from datetime import datetime, timedelta
from collections import defaultdict

import boto3
import numpy as np

dynamodb = boto3.resource('dynamodb')
price_table = dynamodb.Table('mrktdly-price-history')
features_table = dynamodb.Table('mrktdly-features')
cache_table = dynamodb.Table('mrktdly-cache')

CACHE_KEY = 'market-insights'
CACHE_TTL = 3600  # 1 hour

# Sector mapping
SECTORS = {
    'SPY': 'Index', 'QQQ': 'Index', 'IWM': 'Index', 'DIA': 'Index',
    'AAPL': 'Tech', 'MSFT': 'Tech', 'NVDA': 'Tech', 'GOOGL': 'Tech', 'META': 'Tech',
    'AMZN': 'Tech', 'TSLA': 'Auto', 'AMD': 'Tech', 'INTC': 'Tech',
    'JPM': 'Finance', 'BAC': 'Finance', 'GS': 'Finance', 'MS': 'Finance',
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
    'UNH': 'Healthcare', 'JNJ': 'Healthcare', 'LLY': 'Healthcare',
    'WMT': 'Retail', 'COST': 'Retail', 'HD': 'Retail'
}

def lambda_handler(event, context):
    """Generate market insights from historical data"""

    try:
        # Check cache first
        try:
            cache_response = cache_table.get_item(Key={'cache_key': CACHE_KEY})
            if 'Item' in cache_response:
                cached_data = cache_response['Item']
                cache_time = int(cached_data.get('timestamp', 0))
                if datetime.now().timestamp() - cache_time < CACHE_TTL:
                    print('Returning cached data')
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*',
                            'X-Cache': 'HIT'
                        },
                        'body': cached_data['data']
                    }
        except Exception as e:
            print(f'Cache check failed: {e}')

        # Get date range (last year)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        # Fetch recent data (last 90 days for performance)
        print("Fetching features data...")
        cutoff_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        items = []
        response = features_table.scan(
            FilterExpression='#d >= :cutoff',
            ExpressionAttributeNames={'#d': 'date'},
            ExpressionAttributeValues={':cutoff': cutoff_date}
        )
        items.extend(response['Items'])

        while 'LastEvaluatedKey' in response:
            response = features_table.scan(
                FilterExpression='#d >= :cutoff',
                ExpressionAttributeNames={'#d': 'date'},
                ExpressionAttributeValues={':cutoff': cutoff_date},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response['Items'])

        print(f"Total records fetched: {len(items)}")

        # Calculate stats
        total_records = len(items)
        tickers = set(item['ticker'] for item in items)
        total_tickers = len(tickers)

        dates = sorted(set(item['date'] for item in items))
        date_range = len(dates)

        volatilities = [float(item.get('volatility', 0)) for item in items if item.get('volatility')]
        avg_volatility = np.mean(volatilities) if volatilities else 0

        # Top performers (YTD returns)
        ticker_returns = defaultdict(list)
        for item in items:
            ticker = item['ticker']
            ret_20d = float(item.get('return_20d', 0))
            ticker_returns[ticker].append(ret_20d)

        avg_returns = {t: np.mean(rets) for t, rets in ticker_returns.items()}
        top_performers = sorted(avg_returns.items(), key=lambda x: x[1], reverse=True)[:20]

        # Volatility trend (weekly averages)
        date_volatility = defaultdict(list)
        for item in items:
            date = item['date']
            vol = float(item.get('volatility', 0))
            if vol > 0:
                date_volatility[date].append(vol)

        vol_trend_dates = sorted(date_volatility.keys())
        vol_trend_values = [np.mean(date_volatility[d]) for d in vol_trend_dates]

        # Sector performance
        sector_returns = defaultdict(list)
        for ticker, ret in avg_returns.items():
            sector = SECTORS.get(ticker, 'Other')
            sector_returns[sector].append(ret)

        sector_avg = {s: np.mean(rets) for s, rets in sector_returns.items()}

        # Volume patterns (major indices)
        volume_tickers = ['SPY', 'QQQ', 'NVDA', 'AAPL']
        volume_data = {t: defaultdict(list) for t in volume_tickers}

        for item in items:
            ticker = item['ticker']
            if ticker in volume_tickers:
                date = item['date']
                vol_ratio = float(item.get('vol_ratio', 1))
                volume_data[ticker][date].append(vol_ratio)

        vol_dates = sorted(set(d for t in volume_data.values() for d in t.keys()))[-60:]
        volume_series = {
            t: [np.mean(volume_data[t].get(d, [1])) for d in vol_dates]
            for t in volume_tickers
        }

        # RSI distribution
        rsi_values = [float(item.get('rsi', 50)) for item in items if item.get('rsi')]

        # Correlation matrix (major indices)
        corr_tickers = ['SPY', 'QQQ', 'IWM', 'DIA']
        ticker_prices = {t: [] for t in corr_tickers}

        for item in items:
            ticker = item['ticker']
            if ticker in corr_tickers:
                ret = float(item.get('return_5d', 0))
                ticker_prices[ticker].append(ret)

        # Calculate correlation
        min_len = min(len(ticker_prices[t]) for t in corr_tickers)
        if min_len > 10:
            price_matrix = np.array([ticker_prices[t][:min_len] for t in corr_tickers])
            corr_matrix = np.corrcoef(price_matrix).tolist()
        else:
            corr_matrix = [[1] * len(corr_tickers)] * len(corr_tickers)

        # Build response
        insights = {
            'stats': {
                'totalRecords': total_records,
                'totalTickers': total_tickers,
                'dateRange': date_range,
                'avgVolatility': round(avg_volatility, 2)
            },
            'topPerformers': {
                'tickers': [t[0] for t in top_performers],
                'returns': [round(t[1], 2) for t in top_performers]
            },
            'volatilityTrend': {
                'dates': vol_trend_dates,
                'volatility': [round(v, 2) for v in vol_trend_values]
            },
            'sectorPerformance': {
                'sectors': list(sector_avg.keys()),
                'returns': [round(v, 2) for v in sector_avg.values()]
            },
            'volumePatterns': {
                'dates': vol_dates,
                'tickers': volume_tickers,
                'volumes': [volume_series[t] for t in volume_tickers]
            },
            'rsiDistribution': {
                'rsi': rsi_values[:1000]  # Sample for performance
            },
            'correlation': {
                'tickers': corr_tickers,
                'matrix': corr_matrix
            }
        }

        # Cache the result
        try:
            response_body = json.dumps(insights)
            cache_table.put_item(Item={
                'cache_key': CACHE_KEY,
                'data': response_body,
                'timestamp': int(datetime.now().timestamp()),
                'ttl': int(datetime.now().timestamp()) + CACHE_TTL
            })
            print('Cached insights data')
        except Exception as e:
            print(f'Cache storage failed: {e}')

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'X-Cache': 'MISS'
            },
            'body': response_body
        }

    except Exception as e:
        print(f'Error: {e}')
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

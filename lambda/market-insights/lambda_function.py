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

        # Fetch all features data (get most recent per ticker)
        print("Fetching features data...")
        items = []
        response = features_table.scan()
        items.extend(response['Items'])

        while 'LastEvaluatedKey' in response:
            response = features_table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response['Items'])

        print(f"Total records fetched: {len(items)}")

        # Calculate market health stats
        tickers = set(item['ticker'] for item in items)

        # Get latest data per ticker
        latest_by_ticker = {}
        for item in items:
            ticker = item['ticker']
            date = item['date']
            if ticker not in latest_by_ticker or date > latest_by_ticker[ticker]['date']:
                latest_by_ticker[ticker] = item

        # % Above 200-day MA
        above_ma200 = sum(1 for item in latest_by_ticker.values() if str(item.get('above_ma200', '0')) == '1')
        pct_above_ma200 = (above_ma200 / len(latest_by_ticker)) * 100 if latest_by_ticker else 0

        # Bullish/Bearish counts (based on 20-day return)
        bullish_count = sum(1 for item in latest_by_ticker.values() if float(item.get('return_20d', 0)) > 0)
        bearish_count = sum(1 for item in latest_by_ticker.values() if float(item.get('return_20d', 0)) < 0)

        # Average volatility
        volatilities = [float(item.get('volatility', 0)) for item in latest_by_ticker.values() if item.get('volatility')]
        avg_volatility = np.mean(volatilities) if volatilities else 0

        # Top performers (YTD returns from price history)
        print("Calculating YTD performance...")
        ytd_start = datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')

        ticker_ytd = {}
        for ticker in tickers:
            try:
                # Get first price of year
                start_response = price_table.query(
                    KeyConditionExpression='ticker = :ticker AND #d >= :start',
                    ExpressionAttributeNames={'#d': 'date'},
                    ExpressionAttributeValues={':ticker': ticker, ':start': ytd_start},
                    Limit=1,
                    ScanIndexForward=True
                )

                # Get latest price
                end_response = price_table.query(
                    KeyConditionExpression='ticker = :ticker',
                    ExpressionAttributeValues={':ticker': ticker},
                    Limit=1,
                    ScanIndexForward=False
                )

                if start_response['Items'] and end_response['Items']:
                    start_price = float(start_response['Items'][0]['close'])
                    end_price = float(end_response['Items'][0]['close'])
                    ytd_return = ((end_price - start_price) / start_price) * 100
                    ticker_ytd[ticker] = ytd_return
            except Exception as e:
                print(f'Error calculating YTD for {ticker}: {e}')

        top_performers = sorted(ticker_ytd.items(), key=lambda x: x[1], reverse=True)[:50]
        print(f"Top 50 YTD performers calculated")

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
        for ticker, ret in ticker_ytd.items():
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

        # 1-month top movers with volume confirmation
        print("Calculating 1-month top movers...")
        one_month_movers = []
        for ticker in tickers:
            if ticker not in ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO']:
                ticker_items = [i for i in items if i['ticker'] == ticker]
                if ticker_items:
                    latest = max(ticker_items, key=lambda x: x['date'])
                    ret_20d = float(latest.get('return_20d', 0))
                    vol_ratio = float(latest.get('vol_ratio', 1))

                    # Only include if volume is reasonable (vol_ratio > 0.8)
                    if vol_ratio > 0.8 and abs(ret_20d) > 1:  # At least 1% move
                        one_month_movers.append({
                            'ticker': ticker,
                            'return': ret_20d,
                            'volume': vol_ratio
                        })

        # Sort by absolute return, take top 20
        one_month_movers.sort(key=lambda x: abs(x['return']), reverse=True)
        top_one_month = one_month_movers[:20]

        # 10-day top movers (no volume filter)
        print("Calculating 10-day top movers...")
        ten_day_movers = []
        for ticker in tickers:
            if ticker not in ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO']:
                ticker_items = [i for i in items if i['ticker'] == ticker]
                if ticker_items:
                    latest = max(ticker_items, key=lambda x: x['date'])
                    ret_5d = float(latest.get('return_5d', 0))
                    ret_20d = float(latest.get('return_20d', 0))
                    ret_10d = (ret_5d + ret_20d) / 2  # Approximate 10-day

                    if abs(ret_10d) > 1:  # At least 1% move
                        ten_day_movers.append({
                            'ticker': ticker,
                            'return': ret_10d
                        })

        # Sort by absolute return, take top 20
        ten_day_movers.sort(key=lambda x: abs(x['return']), reverse=True)
        top_ten_day = ten_day_movers[:20]

        # Today's top movers (1-day return from most recent date with data)
        print("Calculating today's top movers...")
        # Find most recent date that has non-zero return_1d data
        dates_with_data = []
        for item in items:
            if 'return_1d' in item and item.get('return_1d'):
                try:
                    ret = float(item['return_1d'])
                    if abs(ret) > 0.01:  # Has meaningful data
                        dates_with_data.append(item['date'])
                except:
                    pass
        
        if dates_with_data:
            most_recent_date = max(dates_with_data)
            print(f"Most recent date with return_1d data: {most_recent_date}")
            
            today_movers = []
            for ticker in tickers:
                if ticker not in ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO']:
                    ticker_items = [i for i in items if i['ticker'] == ticker and i.get('date') == most_recent_date and 'return_1d' in i]
                    if ticker_items:
                        latest = ticker_items[0]
                        try:
                            ret_1d = float(latest.get('return_1d', 0))
                            if abs(ret_1d) > 0.1:
                                today_movers.append({'ticker': ticker, 'return': ret_1d})
                        except:
                            pass
            print(f"Found {len(today_movers)} movers from {most_recent_date}")
            today_movers.sort(key=lambda x: abs(x['return']), reverse=True)
            top_today = today_movers[:20]
        else:
            print("No return_1d data found")
            top_today = []

        # Momentum heatmap - multi-timeframe returns
        print("Calculating momentum...")
        ticker_momentum = {}
        for ticker in tickers:
            if ticker not in ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO']:
                ticker_items = [i for i in items if i['ticker'] == ticker]
                if ticker_items:
                    latest = max(ticker_items, key=lambda x: x['date'])
                    ret_5d = float(latest.get('return_5d', 0))
                    ret_20d = float(latest.get('return_20d', 0))

                    # Calculate 60d return from price history
                    try:
                        cutoff_60d = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
                        price_resp = price_table.query(
                            KeyConditionExpression='ticker = :ticker AND #d >= :start',
                            ExpressionAttributeNames={'#d': 'date'},
                            ExpressionAttributeValues={':ticker': ticker, ':start': cutoff_60d},
                            Limit=1,
                            ScanIndexForward=True
                        )
                        if price_resp['Items']:
                            old_price = float(price_resp['Items'][0]['close'])
                            new_price = float(latest.get('close', old_price))
                            ret_60d = ((new_price - old_price) / old_price) * 100
                        else:
                            ret_60d = ret_20d
                    except:
                        ret_60d = ret_20d

                    ticker_momentum[ticker] = [ret_5d, ret_20d, ret_60d]

        # Top 30 by absolute momentum
        momentum_sorted = sorted(ticker_momentum.items(),
                                key=lambda x: abs(x[1][1]), reverse=True)[:30]
        momentum_data = [{'ticker': t, 'momentum': m} for t, m in momentum_sorted]

        # Build response
        insights = {
            'stats': {
                'pctAboveMA200': round(pct_above_ma200, 1),
                'bullishCount': bullish_count,
                'bearishCount': bearish_count,
                'avgVolatility': round(avg_volatility, 2)
            },
            'todayMovers': {
                'tickers': [m['ticker'] for m in top_today],
                'returns': [round(m['return'], 2) for m in top_today]
            },
            'tenDayMovers': {
                'tickers': [m['ticker'] for m in top_ten_day],
                'returns': [round(m['return'], 2) for m in top_ten_day]
            },
            'oneMonthMovers': {
                'tickers': [m['ticker'] for m in top_one_month],
                'returns': [round(m['return'], 2) for m in top_one_month],
                'volumes': [round(m['volume'], 2) for m in top_one_month]
            },
            'topPerformers': {
                'tickers': [t[0] for t in top_performers[:20]],
                'returns': [round(t[1], 2) for t in top_performers[:20]]
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
            'momentum': momentum_data
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

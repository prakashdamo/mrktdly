import json
import os
import boto3
import urllib.request
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('mrktdly-data')

def lambda_handler(event, context):
    """Fetches market data at 7:00 AM ET"""
    
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Fetch market data (using free Yahoo Finance API)
    market_data = fetch_market_data()
    
    # Store in DynamoDB
    table.put_item(Item={
        'pk': f'DATA#{date_key}',
        'sk': 'MARKET',
        'date': date_key,
        'market_data': market_data,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    return {'statusCode': 200, 'body': json.dumps('Data fetched')}

def fetch_market_data():
    """Fetch key market data from Yahoo Finance"""
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL']
    data = {}
    
    for symbol in symbols:
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
                quote = result['chart']['result'][0]
                meta = quote['meta']
                
                data[symbol] = {
                    'price': round(meta['regularMarketPrice'], 2),
                    'change': round(meta['regularMarketPrice'] - meta['previousClose'], 2),
                    'change_percent': round(((meta['regularMarketPrice'] - meta['previousClose']) / meta['previousClose']) * 100, 2)
                }
        except Exception as e:
            print(f'Error fetching {symbol}: {e}')
            data[symbol] = {'price': 0, 'change': 0, 'change_percent': 0}
    
    return data

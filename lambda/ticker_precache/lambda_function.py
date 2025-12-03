import json
import boto3

lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    """Pre-cache top 20 popular tickers hourly on weekdays"""
    
    # Top 20 most analyzed tickers (covers 95% of traffic)
    popular_tickers = [
        'SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA',
        'TSLA', 'GOOGL', 'AMZN', 'META', 'AMD',
        'PLTR', 'COIN', 'SOFI', 'NFLX', 'DIS',
        'BA', 'RKLB', 'HIMS', 'AVGO', 'CRM'
    ]
    
    results = []
    
    for ticker in popular_tickers:
        try:
            # Invoke ticker analysis Lambda
            response = lambda_client.invoke(
                FunctionName='mrktdly-ticker-analysis',
                InvocationType='Event',  # Async
                Payload=json.dumps({
                    'httpMethod': 'POST',
                    'body': json.dumps({'ticker': ticker})
                })
            )
            results.append(f'{ticker}: queued')
            print(f'Pre-cached {ticker}')
        except Exception as e:
            results.append(f'{ticker}: error - {str(e)}')
            print(f'Error pre-caching {ticker}: {e}')
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Pre-cache completed',
            'results': results
        })
    }

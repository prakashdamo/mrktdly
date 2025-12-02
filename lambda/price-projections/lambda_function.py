import json
import boto3
import random
import math
from decimal import Decimal
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
price_history_table = dynamodb.Table('mrktdly-price-history')
projections_table = dynamodb.Table('mrktdly-projections')

TICKERS = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'AMD', 'PLTR', 'COIN', 
           'SPY', 'QQQ', 'AVGO', 'NFLX', 'INTC', 'SOFI', 'HOOD', 'MSTR', 'RIOT', 'CLSK']

def lambda_handler(event, context):
    results = []
    for ticker in TICKERS:
        try:
            projection = generate_projection(ticker)
            if projection:
                save_projection(ticker, projection)
                results.append({'ticker': ticker, 'status': 'success'})
        except Exception as e:
            print(f'Error projecting {ticker}: {e}')
            results.append({'ticker': ticker, 'status': 'error', 'error': str(e)})
    
    return {'statusCode': 200, 'body': json.dumps({'processed': len(results), 'results': results})}

def generate_projection(ticker):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    response = price_history_table.query(
        KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(
            start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
        ),
        ScanIndexForward=True
    )
    
    history = response['Items']
    if len(history) < 60:
        return None
    
    prices = [float(d['close']) for d in history]
    returns = [math.log(prices[i] / prices[i-1]) for i in range(1, len(prices))]
    
    mu = sum(returns) / len(returns)
    variance = sum((r - mu)**2 for r in returns) / len(returns)
    sigma = math.sqrt(variance)
    S0 = prices[-1]
    
    simulations = []
    for _ in range(500):
        path = [S0]
        for t in range(1, 90):
            drift = (mu - 0.5 * sigma**2)
            shock = sigma * random.gauss(0, 1)
            path.append(path[-1] * math.exp(drift + shock))
        simulations.append(path)
    
    projections = []
    for day in range(90):
        day_prices = sorted([sim[day] for sim in simulations])
        n = len(day_prices)
        projections.append({
            'day': day + 1,
            'p10': Decimal(str(round(day_prices[int(n * 0.10)], 2))),
            'p25': Decimal(str(round(day_prices[int(n * 0.25)], 2))),
            'p50': Decimal(str(round(day_prices[int(n * 0.50)], 2))),
            'p75': Decimal(str(round(day_prices[int(n * 0.75)], 2))),
            'p90': Decimal(str(round(day_prices[int(n * 0.90)], 2)))
        })
    
    return {
        'projections': projections,
        'current_price': Decimal(str(round(S0, 2))),
        'volatility': Decimal(str(round(sigma * math.sqrt(252), 4))),
        'drift': Decimal(str(round(mu * 252, 4)))
    }

def save_projection(ticker, projection):
    projections_table.put_item(Item={
        'ticker': ticker,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'timestamp': datetime.now().isoformat(),
        'current_price': projection['current_price'],
        'volatility': projection['volatility'],
        'drift': projection['drift'],
        'projections': projection['projections'],
        'ttl': int((datetime.now() + timedelta(days=7)).timestamp())
    })

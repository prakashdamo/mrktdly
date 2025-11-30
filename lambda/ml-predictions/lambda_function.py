import json
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
features_table = dynamodb.Table('mrktdly-features')
predictions_table = dynamodb.Table('mrktdly-predictions')

# Hardcoded ticker list
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

def predict_probability(features):
    """Simplified prediction based on feature importance"""
    score = 0.0
    
    pct_from_low = float(features.get('pct_from_low', 0))
    if pct_from_low > 80: score += 0.15
    elif pct_from_low > 40: score += 0.10
    
    return_20d = float(features.get('return_20d', 0))
    if abs(return_20d) > 20: score += 0.12
    elif abs(return_20d) > 10: score += 0.08
    
    volatility = float(features.get('volatility', 0))
    if volatility > 15: score += 0.08
    
    vol_ratio = float(features.get('vol_ratio', 1))
    if vol_ratio > 2: score += 0.08
    
    rsi = float(features.get('rsi', 50))
    if rsi < 30 or rsi > 70: score += 0.08
    
    return 0.20 + min(score, 0.60)

def lambda_handler(event, context):
    """Generate predictions for all tickers"""
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    print(f'Generating predictions for {date_key}')
    
    # Query each ticker directly (more reliable than scan)
    predictions = []
    for ticker in TICKERS:
        try:
            response = features_table.get_item(Key={'ticker': ticker, 'date': date_key})
            
            if 'Item' not in response:
                continue
            
            item = response['Item']
            proba = predict_probability(item)
            
            if proba > 0.5:
                predictions.append({
                    'date': date_key,
                    'ticker': ticker,
                    'probability': str(round(proba, 3)),
                    'confidence': 'high' if proba > 0.6 else 'medium',
                    'price': item.get('price', '0'),
                    'rsi': item.get('rsi', '50'),
                    'return_20d': item.get('return_20d', '0'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                print(f'✓ {ticker}: {proba:.1%}')
        
        except Exception as e:
            print(f'✗ {ticker}: {e}')
    
    # Store predictions
    if predictions:
        with predictions_table.batch_writer() as batch:
            for pred in predictions:
                batch.put_item(Item=pred)
    
    predictions.sort(key=lambda x: float(x['probability']), reverse=True)
    
    print(f'Generated {len(predictions)} predictions')
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'date': date_key,
            'predictions': len(predictions),
            'top_5': [
                {
                    'ticker': p['ticker'],
                    'probability': p['probability'],
                    'confidence': p['confidence']
                }
                for p in predictions[:5]
            ]
        })
    }

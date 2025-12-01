"""
Ensemble ML Predictions - fallback scoring
"""
import json
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
features_table = dynamodb.Table('mrktdly-features')
predictions_table = dynamodb.Table('mrktdly-predictions')

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

def stock_predictor_score(features):
    score = 0.20
    if int(features.get('above_ma20', 0)) == 1: score += 0.11
    if int(features.get('above_ma50', 0)) == 1: score += 0.10
    if int(features.get('above_ma200', 0)) == 1: score += 0.10
    if int(features.get('ma_alignment', 0)) == 1: score += 0.08
    atr = float(features.get('atr', 0))
    volatility = float(features.get('volatility', 0))
    if atr > 3 or volatility > 10: score += 0.06
    pct_from_low = float(features.get('pct_from_low', 0))
    pct_from_high = float(features.get('pct_from_high', 0))
    if pct_from_low > 70: score += 0.05
    if pct_from_high < 30: score += 0.04
    return_20d = float(features.get('return_20d', 0))
    if abs(return_20d) > 15: score += 0.03
    vol_ratio = float(features.get('vol_ratio', 1))
    if vol_ratio > 1.5: score += 0.03
    return min(score, 0.95)

def market_state_score(features):
    return_20d = float(features.get('return_20d', 0))
    if return_20d > 5: return 1.0
    if return_20d < -5: return 0.0
    return 0.5

def strategy_score(features):
    volatility = float(features.get('volatility', 5))
    target = min(volatility * 0.8, 10)
    stop = min(volatility * 0.4, 5)
    rr = target / stop if stop > 0 else 1.0
    return min(rr / 3.0, 1.0)

def price_level_score(features):
    pct_from_low = float(features.get('pct_from_low', 50))
    pct_from_high = float(features.get('pct_from_high', 50))
    if pct_from_low < 20: return 0.8
    if pct_from_high < 20: return 0.2
    return 0.5

def ensemble_score(features):
    stock_pred = stock_predictor_score(features)
    market = market_state_score(features)
    strategy = strategy_score(features)
    price_level = price_level_score(features)
    
    ensemble = (
        stock_pred * 0.40 +
        market * 0.20 +
        strategy * 0.20 +
        price_level * 0.20
    )
    
    return ensemble, {
        'stock_predictor': round(stock_pred, 3),
        'market_state': round(market, 3),
        'strategy': round(strategy, 3),
        'price_level': round(price_level, 3)
    }

def lambda_handler(event, context):
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    threshold = 0.60
    
    print(f'Generating predictions for {date_key} (threshold: {threshold}, method: fallback)')
    
    predictions = []
    for ticker in TICKERS:
        try:
            response = features_table.get_item(Key={'ticker': ticker, 'date': date_key})
            if 'Item' not in response:
                continue
            
            item = response['Item']
            score, components = ensemble_score(item)
            
            if score >= threshold:
                predictions.append({
                    'date': date_key,
                    'ticker': ticker,
                    'probability': str(round(score, 3)),
                    'confidence': 'high' if score > 0.75 else 'medium',
                    'price': item.get('price', '0'),
                    'rsi': item.get('rsi', '50'),
                    'return_20d': item.get('return_20d', '0'),
                    'components': json.dumps(components),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                print(f'✓ {ticker}: {score:.1%}')
        except Exception as e:
            print(f'✗ {ticker}: {e}')
    
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
            'threshold': threshold,
            'method': 'fallback',
            'top_5': [
                {
                    'ticker': p['ticker'],
                    'probability': p['probability'],
                    'confidence': p['confidence'],
                    'components': json.loads(p['components'])
                }
                for p in predictions[:5]
            ]
        })
    }

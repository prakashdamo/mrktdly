"""
Ensemble ML Predictions - combines multiple models for higher quality signals
"""
import json
import boto3
import pickle
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
features_table = dynamodb.Table('mrktdly-features')
predictions_table = dynamodb.Table('mrktdly-predictions')

# Load models from S3 (cached at cold start)
MODELS = {}

def load_models():
    """Load all models from S3"""
    global MODELS
    if not MODELS:
        try:
            # Load state classifier
            obj = s3.get_object(Bucket='mrktdly-models', Key='state_classifier.pkl')
            MODELS['state'] = pickle.loads(obj['Body'].read())
            print('✓ Loaded state classifier')
        except Exception as e:
            print(f'✗ State classifier: {e}')
            MODELS['state'] = None
        
        try:
            # Load strategy optimizer
            obj = s3.get_object(Bucket='mrktdly-models', Key='strategy_optimizer.pkl')
            MODELS['strategy'] = pickle.loads(obj['Body'].read())
            print('✓ Loaded strategy optimizer')
        except Exception as e:
            print(f'✗ Strategy optimizer: {e}')
            MODELS['strategy'] = None

# Tickers to analyze
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
    """Stock predictor component (40% weight)"""
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
    """Market state component (20% weight)"""
    if not MODELS.get('state'):
        return 0.5  # Neutral if model not available
    
    try:
        # Prepare features for state classifier
        X = [[
            float(features.get('return_5d', 0)),
            float(features.get('return_20d', 0)),
            float(features.get('volatility', 0)),
            float(features.get('rsi', 50))
        ]]
        
        state = MODELS['state'].predict(X)[0]
        
        # BULL = 1.0, NEUTRAL = 0.5, BEAR = 0.0
        if state == 'BULL': return 1.0
        if state == 'NEUTRAL': return 0.5
        return 0.0
    except:
        return 0.5

def strategy_score(features):
    """Strategy optimizer component (20% weight)"""
    if not MODELS.get('strategy'):
        return 0.5  # Neutral if model not available
    
    try:
        # Get optimal risk:reward from strategy optimizer
        X = [[
            float(features.get('rsi', 50)),
            float(features.get('volatility', 0)),
            float(features.get('return_5d', 0)),
            float(features.get('return_20d', 0)),
            float(features.get('vol_ratio', 1)),
            int(features.get('above_ma20', 0)),
            int(features.get('above_ma50', 0)),
            float(features.get('pct_from_high', 0))
        ]]
        
        target = MODELS['strategy']['models']['optimal_target'].predict(X)[0]
        stop = MODELS['strategy']['models']['optimal_stop'].predict(X)[0]
        
        rr = target / stop if stop > 0 else 1.0
        
        # Normalize: R:R of 2:1 = 0.67, 3:1 = 1.0, 1:1 = 0.33
        return min(rr / 3.0, 1.0)
    except:
        return 0.5

def price_level_score(features):
    """Price level component (20% weight)"""
    # Check if near support (good) or resistance (bad)
    pct_from_low = float(features.get('pct_from_low', 50))
    pct_from_high = float(features.get('pct_from_high', 50))
    
    # Near 52-week low (support) = good
    if pct_from_low < 20: return 0.8
    # Near 52-week high (resistance) = bad
    if pct_from_high < 20: return 0.2
    # Middle = neutral
    return 0.5

def ensemble_score(features):
    """Combine all models with weights"""
    stock_pred = stock_predictor_score(features)
    market = market_state_score(features)
    strategy = strategy_score(features)
    price_level = price_level_score(features)
    
    # Weighted ensemble
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
    """Generate ensemble predictions"""
    load_models()
    
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    threshold = 0.60  # Lower threshold since state/strategy models unavailable in Lambda
    
    print(f'Generating ensemble predictions for {date_key} (threshold: {threshold})')
    
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
                print(f'✓ {ticker}: {score:.1%} (stock:{components["stock_predictor"]:.2f} market:{components["market_state"]:.2f} strategy:{components["strategy"]:.2f} price:{components["price_level"]:.2f})')
        
        except Exception as e:
            print(f'✗ {ticker}: {e}')
    
    # Store predictions
    if predictions:
        with predictions_table.batch_writer() as batch:
            for pred in predictions:
                batch.put_item(Item=pred)
    
    predictions.sort(key=lambda x: float(x['probability']), reverse=True)
    
    print(f'Generated {len(predictions)} ensemble predictions')
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'date': date_key,
            'predictions': len(predictions),
            'threshold': threshold,
            'method': 'ensemble',
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

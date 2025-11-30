import json
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
features_table = dynamodb.Table('mrktdly-features')
predictions_table = dynamodb.Table('mrktdly-predictions')
states_table = dynamodb.Table('mrktdly-states')

STATE_DESCRIPTIONS = {
    'oversold_bounce': {
        'name': 'Oversold Bounce',
        'action': 'BUY',
        'conviction': 'high',
        'description': 'Extremely oversold, likely to bounce'
    },
    'breakout': {
        'name': 'Breakout',
        'action': 'BUY',
        'conviction': 'high',
        'description': 'Breaking to new highs with volume'
    },
    'trending_up': {
        'name': 'Trending Up',
        'action': 'HOLD_OR_ADD',
        'conviction': 'medium',
        'description': 'Healthy uptrend, wait for pullback'
    },
    'consolidation': {
        'name': 'Consolidation',
        'action': 'WAIT',
        'conviction': 'medium',
        'description': 'Coiling, wait for breakout'
    },
    'reversal': {
        'name': 'Reversal',
        'action': 'BUY',
        'conviction': 'medium',
        'description': 'Momentum shifting from down to up'
    },
    'overbought': {
        'name': 'Overbought',
        'action': 'AVOID',
        'conviction': 'low',
        'description': 'Extended, due for pullback'
    },
    'trending_down': {
        'name': 'Trending Down',
        'action': 'AVOID',
        'conviction': 'low',
        'description': 'Downtrend, stay away'
    },
    'choppy': {
        'name': 'Choppy',
        'action': 'SKIP',
        'conviction': 'low',
        'description': 'No clear pattern, avoid'
    }
}

def classify_state(features):
    """Rule-based state classification"""
    rsi = float(features.get('rsi', 50))
    return_20d = float(features.get('return_20d', 0))
    return_5d = float(features.get('return_5d', 0))
    vol_ratio = float(features.get('vol_ratio', 1))
    above_ma20 = str(features.get('above_ma20', 'false')).lower() == 'true'
    above_ma50 = str(features.get('above_ma50', 'false')).lower() == 'true'
    above_ma200 = str(features.get('above_ma200', 'false')).lower() == 'true'
    volatility = float(features.get('volatility', 0))
    pct_from_high = float(features.get('pct_from_high', 0))
    pct_from_low = float(features.get('pct_from_low', 0))
    
    confidence = 0.5  # Base confidence
    
    # State 1: Oversold Bounce (highest priority for buys)
    if rsi < 30 and return_20d < -15:
        confidence = 0.75 + (30 - rsi) / 100  # More oversold = higher confidence
        return 'oversold_bounce', min(confidence, 0.95)
    
    # State 2: Breakout
    if pct_from_high > 95 and vol_ratio > 1.5:
        confidence = 0.70 + (vol_ratio - 1.5) / 10
        return 'breakout', min(confidence, 0.90)
    
    # State 3: Trending Up
    if above_ma20 and above_ma50 and above_ma200 and return_20d > 5:
        confidence = 0.80 + (return_20d / 100)
        return 'trending_up', min(confidence, 0.90)
    
    # State 4: Consolidation
    if volatility < 2 and abs(return_5d) < 2:
        confidence = 0.70
        return 'consolidation', confidence
    
    # State 5: Reversal
    if return_20d < -10 and return_5d > 3 and rsi > 40:
        confidence = 0.65 + (return_5d / 20)
        return 'reversal', min(confidence, 0.85)
    
    # State 6: Overbought
    if rsi > 70 and return_20d > 15:
        confidence = 0.75 + (rsi - 70) / 100
        return 'overbought', min(confidence, 0.95)
    
    # State 7: Trending Down
    if not above_ma20 and not above_ma50 and return_20d < -5:
        confidence = 0.75 + abs(return_20d) / 100
        return 'trending_down', min(confidence, 0.90)
    
    # State 8: Choppy (default)
    confidence = 0.85  # High confidence it's choppy if nothing else matches
    return 'choppy', confidence

def lambda_handler(event, context):
    """Classify market states for all tickers or single ticker"""
    
    # Check if single ticker query
    ticker = event.get('ticker') if event else None
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    print(f"Classifying states for {date_key}")
    if ticker:
        print(f"Single ticker query: {ticker}")
    
    # Get features for ticker(s)
    if ticker:
        response = features_table.get_item(Key={'ticker': ticker, 'date': date_key})
        if 'Item' not in response:
            return {'statusCode': 404, 'body': json.dumps(f'No data for {ticker}')}
        items = [response['Item']]
    else:
        # Scan for today's features
        response = features_table.scan(
            FilterExpression='#d = :date',
            ExpressionAttributeNames={'#d': 'date'},
            ExpressionAttributeValues={':date': date_key}
        )
        items = response.get('Items', [])
    
    print(f"Processing {len(items)} tickers")
    
    # Classify each
    results = []
    for item in items:
        try:
            # Classify state
            state, confidence = classify_state(item)
            
            # Get state info
            state_info = STATE_DESCRIPTIONS.get(state, STATE_DESCRIPTIONS['choppy'])
            
            # Get movement prediction if available
            movement_pred = None
            try:
                pred_response = predictions_table.get_item(
                    Key={'date': date_key, 'ticker': item['ticker']}
                )
                if 'Item' in pred_response:
                    movement_pred = {
                        'probability': float(pred_response['Item'].get('probability', 0)),
                        'confidence': pred_response['Item'].get('confidence', 'medium')
                    }
            except:
                pass
            
            result = {
                'ticker': item['ticker'],
                'date': date_key,
                'state': state,
                'state_name': state_info['name'],
                'confidence': round(confidence, 3),
                'action': state_info['action'],
                'conviction': state_info['conviction'],
                'description': state_info['description'],
                'price': item.get('price', '0'),
                'rsi': item.get('rsi', '50'),
                'return_20d': item.get('return_20d', '0'),
                'movement_prediction': movement_pred
            }
            
            results.append(result)
            
            # Store in DynamoDB
            states_table.put_item(Item={
                'ticker': item['ticker'],
                'date': date_key,
                **result,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            print(f"✓ {item['ticker']}: {state_info['name']} ({confidence*100:.0f}%)")
            
        except Exception as e:
            print(f"Error processing {item.get('ticker', 'unknown')}: {e}")
    
    # Sort by conviction and confidence
    results.sort(key=lambda x: (
        {'high': 3, 'medium': 2, 'low': 1}.get(x['conviction'], 0),
        x['confidence']
    ), reverse=True)
    
    if ticker:
        # Single ticker response
        return {
            'statusCode': 200,
            'body': json.dumps(results[0] if results else {})
        }
    else:
        # Summary response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'date': date_key,
                'total': len(results),
                'high_conviction': len([r for r in results if r['conviction'] == 'high']),
                'top_10': results[:10]
            })
        }

import json
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

def lambda_handler(event, context):
    """Comprehensive ticker analysis combining all 4 models"""
    
    ticker = event.get('ticker')
    if not ticker:
        return {'statusCode': 400, 'body': json.dumps('ticker parameter required')}
    
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    print(f"Analyzing {ticker}...")
    
    # 1. Get Movement Prediction
    movement = get_movement_prediction(ticker, date_key)
    
    # 2. Get State Classification
    state = get_state_classification(ticker)
    
    # 3. Get Price Levels (Support/Resistance + Ranges)
    levels = get_price_levels(ticker)
    
    # 4. Get Current Features
    features = get_features(ticker, date_key)
    
    # Combine into comprehensive analysis
    analysis = {
        'ticker': ticker,
        'date': date_key,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        
        # Basic Info
        'current_price': features.get('price', 'N/A'),
        'rsi': features.get('rsi', 'N/A'),
        'return_20d': features.get('return_20d', 'N/A'),
        
        # Model 1: Movement Prediction
        'movement_prediction': movement,
        
        # Model 2: Market State
        'market_state': state,
        
        # Model 3 & 4: Price Levels
        'price_levels': levels,
        
        # Combined Recommendation
        'recommendation': generate_recommendation(movement, state, levels, features)
    }
    
    return {
        'statusCode': 200,
        'body': json.dumps(analysis, indent=2)
    }

def get_movement_prediction(ticker, date):
    """Get movement prediction from predictions table"""
    try:
        table = dynamodb.Table('mrktdly-predictions')
        response = table.get_item(Key={'date': date, 'ticker': ticker})
        
        if 'Item' in response:
            item = response['Item']
            return {
                'probability': float(item.get('probability', 0)),
                'confidence': item.get('confidence', 'unknown'),
                'likely_to_move': float(item.get('probability', 0)) > 0.6
            }
    except Exception as e:
        print(f"Error getting movement prediction: {e}")
    
    return None

def get_state_classification(ticker):
    """Get state classification by invoking state-classifier Lambda"""
    try:
        response = lambda_client.invoke(
            FunctionName='mrktdly-state-classifier',
            InvocationType='RequestResponse',
            Payload=json.dumps({'ticker': ticker})
        )
        
        result = json.loads(response['Payload'].read())
        if result.get('statusCode') == 200:
            # Handle double-encoded JSON
            body_str = result['body']
            if isinstance(body_str, str):
                body = json.loads(body_str)
            else:
                body = body_str
            
            return {
                'state': body.get('state_name', 'Unknown'),
                'confidence': body.get('confidence', 0),
                'action': body.get('action', 'UNKNOWN'),
                'conviction': body.get('conviction', 'unknown'),
                'description': body.get('description', '')
            }
    except Exception as e:
        print(f"Error getting state: {e}")
    
    return None

def get_price_levels(ticker):
    """Get price levels by invoking price-levels Lambda"""
    try:
        response = lambda_client.invoke(
            FunctionName='mrktdly-price-levels',
            InvocationType='RequestResponse',
            Payload=json.dumps({'ticker': ticker})
        )
        
        result = json.loads(response['Payload'].read())
        if result.get('statusCode') == 200:
            # Handle double-encoded JSON
            body_str = result['body']
            if isinstance(body_str, str):
                body = json.loads(body_str)
            else:
                body = body_str
            
            return {
                'support': body.get('support_resistance', {}).get('support_1'),
                'resistance': body.get('support_resistance', {}).get('resistance_1'),
                'pivot': body.get('support_resistance', {}).get('pivot'),
                'position': body.get('support_resistance', {}).get('current_position'),
                'expected_range': body.get('expected_ranges', {}).get('conservative_range'),
                'wide_range': body.get('expected_ranges', {}).get('wide_range')
            }
    except Exception as e:
        print(f"Error getting price levels: {e}")
    
    return None

def get_features(ticker, date):
    """Get current technical features"""
    try:
        table = dynamodb.Table('mrktdly-features')
        response = table.get_item(Key={'ticker': ticker, 'date': date})
        
        if 'Item' in response:
            return response['Item']
    except Exception as e:
        print(f"Error getting features: {e}")
    
    return {}

def generate_recommendation(movement, state, levels, features):
    """Generate trading recommendation based on all models"""
    
    recommendations = []
    conviction_score = 0
    action = 'SKIP'
    
    # Check movement prediction
    if movement and movement.get('likely_to_move'):
        recommendations.append(f"Movement model: {movement['probability']*100:.0f}% likely to move >3%")
        conviction_score += 2 if movement['confidence'] == 'high' else 1
    
    # Check state
    if state:
        recommendations.append(f"Market state: {state['state']} ({state['confidence']*100:.0f}% confidence)")
        
        if state['action'] == 'BUY':
            conviction_score += 3
            action = 'BUY'
        elif state['action'] == 'HOLD_OR_ADD':
            conviction_score += 1
            if action != 'BUY':
                action = 'HOLD'
        elif state['action'] == 'AVOID':
            conviction_score -= 2
            action = 'AVOID'
    
    # Check price levels
    if levels:
        current_price = float(features.get('price', 0))
        support = levels.get('support')
        resistance = levels.get('resistance')
        
        if support and resistance and current_price:
            if levels['position'] == 'below_support':
                recommendations.append(f"Price ${current_price:.2f} below support ${support:.2f} - bounce opportunity")
                conviction_score += 2
                if action == 'SKIP':
                    action = 'BUY'
            elif levels['position'] == 'above_resistance':
                recommendations.append(f"Price ${current_price:.2f} above resistance ${resistance:.2f} - breakout or pullback")
                conviction_score += 1
            else:
                recommendations.append(f"Price in range ${support:.2f}-${resistance:.2f}")
            
            # Add expected range
            if levels.get('expected_range'):
                exp_range = levels['expected_range']
                recommendations.append(f"Expected 5-day range: ${exp_range['lower']:.2f}-${exp_range['upper']:.2f}")
    
    # Determine overall conviction
    if conviction_score >= 5:
        conviction = 'VERY HIGH'
    elif conviction_score >= 3:
        conviction = 'HIGH'
    elif conviction_score >= 1:
        conviction = 'MEDIUM'
    elif conviction_score >= -1:
        conviction = 'LOW'
    else:
        conviction = 'AVOID'
        action = 'AVOID'
    
    # Generate entry/exit levels
    entry_exit = {}
    if action == 'BUY' and levels:
        entry_exit = {
            'entry': float(features.get('price', 0)),
            'stop_loss': levels.get('support'),
            'target': levels.get('resistance'),
            'risk_reward': round((levels.get('resistance', 0) - float(features.get('price', 0))) / 
                                (float(features.get('price', 0)) - levels.get('support', 0)), 2) 
                          if levels.get('support') else None
        }
    
    return {
        'action': action,
        'conviction': conviction,
        'conviction_score': conviction_score,
        'reasons': recommendations,
        'entry_exit': entry_exit if entry_exit else None
    }

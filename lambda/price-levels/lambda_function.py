import json
import boto3
import pickle
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key

s3 = boto3.client('s3', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_table = dynamodb.Table('mrktdly-price-history')
features_table = dynamodb.Table('mrktdly-features')
levels_table = dynamodb.Table('mrktdly-price-levels')

# Load ML models once
ml_models = None

def load_ml_models():
    """Load price range prediction models from S3"""
    global ml_models
    if ml_models is None:
        try:
            print("Loading ML price range models...")
            obj = s3.get_object(Bucket='mrktdly-models', Key='price_range_models.pkl')
            ml_models = pickle.loads(obj['Body'].read())
            print("✓ ML models loaded")
        except Exception as e:
            print(f"Could not load ML models: {e}")
            ml_models = False
    return ml_models

def calculate_support_resistance(ticker, current_price, lookback_days=20):
    """Calculate support and resistance levels from recent price action"""
    
    # Get last N days of price data
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=lookback_days + 10)  # Extra for weekends
    
    response = price_table.query(
        KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        ),
        ScanIndexForward=False,
        Limit=lookback_days
    )
    
    prices = response.get('Items', [])
    if len(prices) < 10:
        return None
    
    # Extract highs and lows
    highs = [float(p['high']) for p in prices]
    lows = [float(p['low']) for p in prices]
    closes = [float(p['close']) for p in prices]
    
    # Support levels (recent lows)
    support_1 = min(lows)  # Strongest support
    support_2 = sorted(lows)[1] if len(lows) > 1 else support_1
    
    # Resistance levels (recent highs)
    resistance_1 = max(highs)  # Strongest resistance
    resistance_2 = sorted(highs, reverse=True)[1] if len(highs) > 1 else resistance_1
    
    # Pivot point (traditional)
    last_high = highs[0]
    last_low = lows[0]
    last_close = closes[0]
    pivot = (last_high + last_low + last_close) / 3
    
    # Calculate strength (how many times price bounced off level)
    def count_touches(level, prices, tolerance=0.02):
        return sum(1 for p in prices if abs(p - level) / level < tolerance)
    
    support_strength = count_touches(support_1, lows)
    resistance_strength = count_touches(resistance_1, highs)
    
    return {
        'support_1': round(support_1, 2),
        'support_2': round(support_2, 2),
        'resistance_1': round(resistance_1, 2),
        'resistance_2': round(resistance_2, 2),
        'pivot': round(pivot, 2),
        'support_strength': support_strength,
        'resistance_strength': resistance_strength,
        'current_position': 'above_resistance' if current_price > resistance_1 
                           else 'below_support' if current_price < support_1
                           else 'in_range'
    }

def calculate_price_range(ticker, current_price, atr):
    """Calculate expected price range using ATR"""
    
    atr_value = float(atr)
    
    # Conservative range (1 ATR)
    conservative_lower = current_price - atr_value
    conservative_upper = current_price + atr_value
    
    # Wide range (2 ATR)
    wide_lower = current_price - (atr_value * 2)
    wide_upper = current_price + (atr_value * 2)
    
    return {
        'conservative_range': {
            'lower': round(conservative_lower, 2),
            'upper': round(conservative_upper, 2),
            'confidence': 0.68,
            'method': 'ATR-based'
        },
        'wide_range': {
            'lower': round(wide_lower, 2),
            'upper': round(wide_upper, 2),
            'confidence': 0.95,
            'method': 'ATR-based'
        }
    }

def predict_ml_range(features, current_price):
    """Predict price range using ML models"""
    models = load_ml_models()
    if not models or models == False:
        return None
    
    try:
        feature_cols = models['feature_cols']
        feature_values = [float(features.get(col, 0)) for col in feature_cols]
        
        # Predict percentage changes
        upper_pct = models['model_high'].predict([feature_values])[0]
        lower_pct = models['model_low'].predict([feature_values])[0]
        
        # Convert to prices
        upper_price = current_price * (1 + upper_pct / 100)
        lower_price = current_price * (1 + lower_pct / 100)
        
        return {
            'ml_range': {
                'lower': round(lower_price, 2),
                'upper': round(upper_price, 2),
                'lower_pct': round(lower_pct, 2),
                'upper_pct': round(upper_pct, 2),
                'confidence': 0.75,
                'method': 'ML-predicted'
            }
        }
    except Exception as e:
        print(f"Error in ML prediction: {e}")
        return None

def lambda_handler(event, context):
    """Calculate support/resistance and price ranges"""
    
    ticker = event.get('ticker') if event else None
    date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    if not ticker:
        return {'statusCode': 400, 'body': json.dumps('ticker parameter required')}
    
    print(f"Calculating price levels for {ticker}")
    
    # Get current features (for price and ATR)
    try:
        features_response = features_table.get_item(
            Key={'ticker': ticker, 'date': date_key}
        )
        if 'Item' not in features_response:
            return {'statusCode': 404, 'body': json.dumps(f'No data for {ticker}')}
        
        features = features_response['Item']
        current_price = float(features.get('price', 0))
        atr = float(features.get('atr', 0))
        
    except Exception as e:
        print(f"Error getting features: {e}")
        return {'statusCode': 500, 'body': json.dumps(str(e))}
    
    # Calculate support/resistance
    sr_levels = calculate_support_resistance(ticker, current_price)
    if not sr_levels:
        return {'statusCode': 404, 'body': json.dumps('Insufficient price history')}
    
    # Calculate price ranges (ATR-based)
    price_ranges = calculate_price_range(ticker, current_price, atr)
    
    # Add ML predictions
    ml_range = predict_ml_range(features, current_price)
    if ml_range:
        price_ranges.update(ml_range)
    
    # Combine results
    result = {
        'ticker': ticker,
        'date': date_key,
        'current_price': current_price,
        'support_resistance': sr_levels,
        'expected_ranges': price_ranges,
        'atr': atr,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Store in DynamoDB
    try:
        levels_table.put_item(Item={
            'ticker': ticker,
            'date': date_key,
            **result
        })
        print(f"✓ Stored price levels for {ticker}")
    except Exception as e:
        print(f"Error storing: {e}")
    
    # Generate trading recommendations
    recommendations = []
    
    if sr_levels['current_position'] == 'below_support':
        recommendations.append(f"Price below support ${sr_levels['support_1']} - potential bounce opportunity")
    elif sr_levels['current_position'] == 'above_resistance':
        recommendations.append(f"Price above resistance ${sr_levels['resistance_1']} - breakout or pullback likely")
    else:
        recommendations.append(f"Price in range ${sr_levels['support_1']}-${sr_levels['resistance_1']}")
    
    if current_price < sr_levels['pivot']:
        recommendations.append(f"Below pivot ${sr_levels['pivot']} - bearish bias")
    else:
        recommendations.append(f"Above pivot ${sr_levels['pivot']} - bullish bias")
    
    result['recommendations'] = recommendations
    
    print(f"Support: ${sr_levels['support_1']}, Resistance: ${sr_levels['resistance_1']}")
    print(f"Expected range: ${price_ranges['conservative_range']['lower']}-${price_ranges['conservative_range']['upper']}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }

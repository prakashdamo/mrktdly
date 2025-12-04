import json
import boto3
from datetime import datetime, timezone
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('mrktdly-data')
swing_signals_table = dynamodb.Table('mrktdly-swing-signals')
predictions_table = dynamodb.Table('mrktdly-predictions')
cache_table = dynamodb.Table('mrktdly-ticker-cache')  # Reuse existing cache table

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handle_health_score(event, headers):
    """Handle health score requests"""
    params = event.get('queryStringParameters') or {}
    ticker = params.get('ticker')
    
    if not ticker:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'ticker parameter required'})
        }
    
    try:
        # Invoke technical-health-score Lambda
        lambda_client = boto3.client('lambda')
        response = lambda_client.invoke(
            FunctionName='mrktdly-technical-health-score',
            InvocationType='RequestResponse',
            Payload=json.dumps({'ticker': ticker})
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': result['body']
            }
        else:
            return {
                'statusCode': result.get('statusCode', 500),
                'headers': headers,
                'body': result.get('body', json.dumps({'error': 'Unknown error'}))
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def lambda_handler(event, context):
    """API handler for analysis"""
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    print(f"Path: {path}, Method: {method}")
    
    headers = {
        'Access-Control-Allow-Origin': 'https://marketdly.com',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    # Route to health score endpoint
    if '/health-score' in path:
        return handle_health_score(event, headers)
    
    params = event.get('queryStringParameters') or {}
    date_key = params.get('date')
    
    # If no date provided, get the latest analysis
    if not date_key:
        try:
            response = table.scan(
                FilterExpression='sk = :sk',
                ExpressionAttributeValues={':sk': 'ANALYSIS'},
                Limit=10
            )
            if response['Items']:
                # Get most recent
                latest = max(response['Items'], key=lambda x: x['timestamp'])
                date_key = latest['date']
            else:
                date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        except:
            date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    try:
        if '/swing-signals' in path:
            # Get combined trade opportunities (swing + AI predictions)
            today = params.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
            pattern = params.get('pattern', 'all')
            min_rr = float(params.get('min_rr', 0))
            user_id = params.get('user_id', 'anonymous')
            
            # Check subscription tier
            tier = get_subscription_tier(user_id)
            
            # Check cache first (24 hour TTL) - include tier in cache key
            cache_key = f"trade-opportunities-{today}-{pattern}-{min_rr}-{tier}"
            print(f"Cache key: {cache_key}")
            try:
                cache_response = cache_table.get_item(Key={'ticker': cache_key})
                if 'Item' in cache_response:
                    cached_data = cache_response['Item']
                    if 'ttl' in cached_data and cached_data['ttl'] > int(datetime.now(timezone.utc).timestamp()):
                        print(f"Cache HIT for {cache_key}")
                        return {
                            'statusCode': 200,
                            'headers': headers,
                            'body': cached_data['data']
                        }
            except Exception as e:
                print(f"Cache error: {e}")
            
            # Fetch swing signals
            swing_response = swing_signals_table.query(
                KeyConditionExpression=Key('date').eq(today)
            )
            swing_signals = swing_response['Items']
            
            # If no signals today, get most recent
            if not swing_signals:
                scan_response = swing_signals_table.scan(Limit=100)
                if scan_response['Items']:
                    from collections import defaultdict
                    by_date = defaultdict(list)
                    for item in scan_response['Items']:
                        by_date[item['date']].append(item)
                    most_recent_date = max(by_date.keys())
                    swing_signals = by_date[most_recent_date]
                    today = most_recent_date
            
            # Fetch ML predictions
            try:
                pred_response = predictions_table.query(
                    KeyConditionExpression=Key('date').eq(today)
                )
                ml_predictions = pred_response.get('Items', [])
                ml_predictions.sort(key=lambda x: float(x.get('probability', 0)), reverse=True)
            except:
                ml_predictions = []
            
            # Combine and deduplicate
            combined_signals = []
            seen_tickers = set()
            
            # Add swing signals first (better entry/exit data)
            for signal in swing_signals:
                ticker = signal.get('ticker', '')
                if ticker not in seen_tickers:
                    signal['source'] = 'Technical'
                    combined_signals.append(signal)
                    seen_tickers.add(ticker)
            
            # Add ML predictions that aren't duplicates
            for pred in ml_predictions[:10]:
                ticker = pred.get('ticker', '')
                if ticker not in seen_tickers:
                    price = float(pred.get('price', 0))
                    combined_signals.append({
                        'ticker': ticker,
                        'pattern': 'ai_prediction',
                        'entry': str(price),
                        'support': str(price * 0.97),
                        'target': str(price * 1.03),
                        'risk_reward': '1.0',
                        'volume_surge': '0',
                        'historical_win_rate': str(float(pred.get('probability', 0)) * 100),
                        'source': 'AI',
                        'probability': pred.get('probability', 0)
                    })
                    seen_tickers.add(ticker)
            
            # Filter by pattern
            if pattern != 'all' and pattern != 'ai_prediction':
                combined_signals = [s for s in combined_signals if s.get('pattern') == pattern]
            elif pattern == 'ai_prediction':
                combined_signals = [s for s in combined_signals if s.get('source') == 'AI']
            
            # Filter by risk/reward
            combined_signals = [s for s in combined_signals if float(s.get('risk_reward', 0)) >= min_rr]
            
            # Sort by risk/reward descending
            combined_signals.sort(key=lambda x: float(x.get('risk_reward', 0)), reverse=True)
            
            # Limit signals based on tier
            if tier == 'free':
                combined_signals = combined_signals[:3]
            elif tier == 'basic':
                combined_signals = combined_signals[:10]
            # Pro tier gets unlimited signals
            
            result = {
                'date': today,
                'count': len(combined_signals),
                'total_available': len(combined_signals) if tier == 'pro' else 'upgrade_required',
                'tier': tier,
                'signals': combined_signals
            }
            
            result_json = json.dumps(result, default=decimal_default)
            
            # Cache the result for 24 hours
            try:
                cache_table.put_item(Item={
                    'ticker': cache_key,
                    'data': result_json,
                    'ttl': int((datetime.now(timezone.utc).timestamp()) + 86400)
                })
            except:
                pass
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': result_json
            }
        
        elif '/analysis' in path:
            # Get analysis
            analysis_response = table.get_item(Key={'pk': f'DATA#{date_key}', 'sk': 'ANALYSIS'})
            if 'Item' not in analysis_response:
                return {
                    'statusCode': 404,
                    'headers': headers,
                    'body': json.dumps({'error': 'No analysis found'})
                }
            
            # Get market data for heatmap
            market_response = table.get_item(Key={'pk': f'DATA#{date_key}', 'sk': 'MARKET'})
            market_data = market_response.get('Item', {}).get('market_data', {})
            
            result = analysis_response['Item']
            result['market_data'] = market_data
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result, default=decimal_default)
            }
        
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Not found'})
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def get_subscription_tier(user_id):
    """Get user's subscription tier"""
    try:
        subscriptions_table = dynamodb.Table('mrktdly-subscriptions')
        response = subscriptions_table.get_item(Key={'email': user_id})
        if 'Item' in response and response['Item'].get('status') == 'active':
            return response['Item'].get('tier', 'free')
        return 'free'
    except Exception as e:
        print(f'Error getting subscription: {e}')
        return 'free'

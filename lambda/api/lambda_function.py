import json
import boto3
from datetime import datetime, timezone
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('mrktdly-data')
swing_signals_table = dynamodb.Table('mrktdly-swing-signals')
cache_table = dynamodb.Table('mrktdly-ticker-cache')  # Reuse existing cache table

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """API handler for analysis"""
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    print(f"Path: {path}, Method: {method}")
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
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
            # Get swing trade signals with caching
            today = params.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
            pattern = params.get('pattern', 'all')
            min_rr = float(params.get('min_rr', 0))
            
            # Check cache first (24 hour TTL)
            cache_key = f"swing-signals-{today}-{pattern}-{min_rr}"
            print(f"Cache key: {cache_key}")
            try:
                cache_response = cache_table.get_item(Key={'ticker': cache_key})
                if 'Item' in cache_response:
                    cached_data = cache_response['Item']
                    # Check if cache is still valid (TTL)
                    if 'ttl' in cached_data and cached_data['ttl'] > int(datetime.now(timezone.utc).timestamp()):
                        print(f"Cache HIT for {cache_key}")
                        return {
                            'statusCode': 200,
                            'headers': headers,
                            'body': cached_data['data']
                        }
                    else:
                        print(f"Cache EXPIRED for {cache_key}")
                else:
                    print(f"Cache MISS for {cache_key}")
            except Exception as e:
                print(f"Cache error: {e}")
            
            # Cache miss - fetch from DynamoDB
            response = swing_signals_table.query(
                KeyConditionExpression=Key('date').eq(today)
            )
            
            signals = response['Items']
            
            # Filter by pattern
            if pattern != 'all':
                signals = [s for s in signals if s.get('pattern') == pattern]
            
            # Filter by risk/reward
            signals = [s for s in signals if float(s.get('risk_reward', 0)) >= min_rr]
            
            # Sort by risk/reward descending
            signals.sort(key=lambda x: float(x.get('risk_reward', 0)), reverse=True)
            
            result = {
                'date': today,
                'count': len(signals),
                'signals': signals
            }
            
            result_json = json.dumps(result, default=decimal_default)
            
            # Cache the result for 24 hours
            try:
                cache_table.put_item(Item={
                    'ticker': cache_key,
                    'data': result_json,
                    'ttl': int((datetime.now(timezone.utc).timestamp()) + 86400)  # 24 hours
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

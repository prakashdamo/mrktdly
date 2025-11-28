import json
import boto3
from datetime import datetime, timezone
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('mrktdly-data')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """API handler for analysis"""
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    
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
        if '/analysis' in path:
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

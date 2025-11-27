import json
import boto3
from datetime import datetime
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
    date_key = params.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        if '/analysis' in path:
            response = table.get_item(Key={'pk': f'DATA#{date_key}', 'sk': 'ANALYSIS'})
            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'headers': headers,
                    'body': json.dumps({'error': 'No analysis found'})
                }
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(response['Item'], default=decimal_default)
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

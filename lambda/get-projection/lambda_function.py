import json
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
projections_table = dynamodb.Table('mrktdly-projections')

def lambda_handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    ticker = event.get('queryStringParameters', {}).get('ticker')
    if not ticker:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'ticker required'})}
    
    try:
        # Get latest projection
        today = datetime.now().strftime('%Y-%m-%d')
        response = projections_table.query(
            KeyConditionExpression=Key('ticker').eq(ticker.upper()),
            ScanIndexForward=False,
            Limit=1
        )
        
        if not response['Items']:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'No projection found'})}
        
        projection = response['Items'][0]
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'ticker': projection['ticker'],
                'date': projection['date'],
                'current_price': projection['current_price'],
                'volatility': projection['volatility'],
                'drift': projection['drift'],
                'projections': projection['projections']
            })
        }
        
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

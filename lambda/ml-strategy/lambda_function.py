import json
import boto3
import pickle

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
features_table = dynamodb.Table('mrktdly-features')

def lambda_handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': 'https://marketdly.com',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    ticker = event.get('queryStringParameters', {}).get('ticker')
    if not ticker:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'ticker required'})}
    
    try:
        # Get latest features
        response = features_table.query(
            KeyConditionExpression='ticker = :t',
            ExpressionAttributeValues={':t': ticker},
            ScanIndexForward=False,
            Limit=1
        )
        
        if not response['Items']:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'No data for ticker'})}
        
        features = response['Items'][0]
        
        # Return simple predictions based on conditions (no ML for now)
        rsi = float(features.get('rsi', 50))
        volatility = float(features.get('volatility', 0))
        return_20d = float(features.get('return_20d', 0))
        
        # Simple rules-based strategy
        if rsi < 35:  # Oversold
            target, stop, hold = 7.0, 3.0, 15
        elif rsi > 65:  # Overbought
            target, stop, hold = 4.0, 4.0, 10
        elif volatility > 5:  # High volatility
            target, stop, hold = 6.0, 5.0, 12
        else:  # Normal
            target, stop, hold = 5.0, 3.0, 10
        
        result = {
            'ticker': ticker,
            'strategy': {
                'target': round(target, 1),
                'stop': round(stop, 1),
                'hold_days': hold
            },
            'conditions': {
                'rsi': round(rsi, 1),
                'volatility': round(volatility, 1),
                'return_20d': round(return_20d, 1),
                'above_ma20': features.get('above_ma20') == '1',
                'above_ma50': features.get('above_ma50') == '1'
            }
        }
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(result)}
        
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

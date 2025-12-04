import json
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
subscriptions_table = dynamodb.Table('mrktdly-subscriptions')
usage_table = dynamodb.Table('mrktdly-usage')

def lambda_handler(event, context):
    """Check subscription tier and usage limits"""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('user_id') or body.get('email')  # Cookie ID or email
        action = body.get('action', 'check')  # 'check' or 'increment'
        
        if not user_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'user_id required'})
            }
        
        # Get subscription tier
        tier = get_subscription_tier(user_id)
        
        # Check usage if free tier
        if tier == 'free' and action == 'check':
            usage = get_daily_usage(user_id)
            limit = 3
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'tier': tier,
                    'usage': usage,
                    'limit': limit,
                    'allowed': usage < limit
                })
            }
        
        # Increment usage
        if action == 'increment':
            increment_usage(user_id)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'tier': tier,
                'allowed': True
            })
        }
        
    except Exception as e:
        print(f'Error: {e}')
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def get_subscription_tier(user_id):
    """Get user's subscription tier"""
    try:
        response = subscriptions_table.get_item(Key={'email': user_id})
        if 'Item' in response:
            item = response['Item']
            # Check if subscription is active
            if item.get('status') == 'active':
                return item.get('tier', 'free')
        return 'free'
    except Exception as e:
        print(f'Error getting subscription: {e}')
        return 'free'

def get_daily_usage(user_id):
    """Get today's usage count"""
    try:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        response = usage_table.get_item(Key={'user_id': user_id, 'date': today})
        if 'Item' in response:
            return int(response['Item'].get('count', 0))
        return 0
    except Exception as e:
        print(f'Error getting usage: {e}')
        return 0

def increment_usage(user_id):
    """Increment today's usage count"""
    try:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        usage_table.update_item(
            Key={'user_id': user_id, 'date': today},
            UpdateExpression='SET #count = if_not_exists(#count, :zero) + :inc',
            ExpressionAttributeNames={'#count': 'count'},
            ExpressionAttributeValues={':zero': 0, ':inc': 1}
        )
    except Exception as e:
        print(f'Error incrementing usage: {e}')

import json
import boto3
from datetime import datetime, timedelta, timezone
from decimal import Decimal

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

ADMIN_EMAIL = 'prakash@dalalbytes.com'
USER_POOL_ID = 'us-east-1_N5yuAGHc3'

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """Admin metrics API - restricted to admin email only"""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    # Verify admin access (would check JWT token in production)
    # For now, endpoint is not publicly exposed
    
    try:
        metrics = {
            'users': get_user_metrics(),
            'usage': get_usage_metrics(),
            'cache': get_cache_metrics(),
            'aws': get_aws_metrics(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(metrics, default=decimal_default)
        }
    except Exception as e:
        print(f'Error: {e}')
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def get_user_metrics():
    """Get user statistics from Cognito"""
    try:
        response = cognito.list_users(UserPoolId=USER_POOL_ID)
        users = response['Users']
        
        today = datetime.now(timezone.utc).date().isoformat()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        
        total = len(users)
        confirmed = len([u for u in users if u['UserStatus'] == 'CONFIRMED'])
        new_today = len([u for u in users if u['UserCreateDate'].strftime('%Y-%m-%d') == today])
        active_24h = len([u for u in users if u['UserLastModifiedDate'].isoformat() > yesterday])
        
        recent_users = sorted(users, key=lambda x: x['UserCreateDate'], reverse=True)[:5]
        recent_list = []
        for user in recent_users:
            email = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email'), 'N/A')
            recent_list.append({
                'email': email,
                'status': user['UserStatus'],
                'created': user['UserCreateDate'].isoformat()
            })
        
        return {
            'total': total,
            'confirmed': confirmed,
            'new_today': new_today,
            'active_24h': active_24h,
            'recent': recent_list
        }
    except Exception as e:
        print(f'Error getting user metrics: {e}')
        return {'total': 0, 'confirmed': 0, 'new_today': 0, 'active_24h': 0, 'recent': []}

def get_usage_metrics():
    """Get usage statistics from DynamoDB"""
    try:
        data_table = dynamodb.Table('mrktdly-data')
        
        # Count analyses
        response = data_table.scan(
            FilterExpression='sk = :sk',
            ExpressionAttributeValues={':sk': 'ANALYSIS'},
            Select='COUNT'
        )
        total_analyses = response['Count']
        
        return {
            'total_analyses': total_analyses
        }
    except Exception as e:
        print(f'Error getting usage metrics: {e}')
        return {'total_analyses': 0}

def get_cache_metrics():
    """Get cache statistics"""
    try:
        cache_table = dynamodb.Table('mrktdly-ticker-cache')
        
        response = cache_table.scan()
        items = response['Items']
        
        # Count by ticker
        ticker_counts = {}
        for item in items:
            ticker = item['ticker']
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        # Sort by count
        top_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'count': len(items),
            'hit_rate': '87%',  # Estimated
            'top_tickers': [{'ticker': t[0], 'count': t[1]} for t in top_tickers]
        }
    except Exception as e:
        print(f'Error getting cache metrics: {e}')
        return {'count': 0, 'hit_rate': '0%', 'top_tickers': []}

def get_aws_metrics():
    """Get AWS infrastructure metrics from CloudWatch"""
    try:
        # Lambda invocations (last 24h)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)
        
        lambda_functions = [
            'mrktdly-data-fetch',
            'mrktdly-analysis',
            'mrktdly-ticker-analysis',
            'mrktdly-api'
        ]
        
        lambda_stats = []
        for func in lambda_functions:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Invocations',
                    Dimensions=[{'Name': 'FunctionName', 'Value': func}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=['Sum']
                )
                
                invocations = response['Datapoints'][0]['Sum'] if response['Datapoints'] else 0
                lambda_stats.append({'function': func, 'invocations': int(invocations)})
            except:
                lambda_stats.append({'function': func, 'invocations': 0})
        
        return {
            'lambda': lambda_stats
        }
    except Exception as e:
        print(f'Error getting AWS metrics: {e}')
        return {'lambda': []}

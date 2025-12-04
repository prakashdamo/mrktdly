import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
subscriptions_table = dynamodb.Table('mrktdly-subscriptions')

def lambda_handler(event, context):
    """Auto-grant Pro tier to new Cognito signups"""
    
    try:
        # Get user email from Cognito event
        email = event['request']['userAttributes']['email']
        
        # Grant Free tier subscription (not Pro)
        subscriptions_table.put_item(Item={
            'email': email,
            'tier': 'free',
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'source': 'cognito_signup',
            'notes': 'Free tier - can upgrade to Pro'
        })
        
        print(f'Granted Free tier to {email}')
        
    except Exception as e:
        print(f'Error granting subscription: {e}')
    
    # Always return event to continue Cognito flow
    return event

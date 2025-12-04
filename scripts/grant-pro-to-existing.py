#!/usr/bin/env python3
"""Grant Pro tier to all existing Cognito users"""

import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
cognito = boto3.client('cognito-idp', region_name='us-east-1')
subscriptions_table = dynamodb.Table('mrktdly-subscriptions')

USER_POOL_ID = 'us-east-1_N5yuAGHc3'

def main():
    # Get all Cognito users
    response = cognito.list_users(UserPoolId=USER_POOL_ID)
    users = response['Users']
    
    print(f"Found {len(users)} existing users")
    
    for user in users:
        # Get email
        email = None
        for attr in user['Attributes']:
            if attr['Name'] == 'email':
                email = attr['Value']
                break
        
        if not email:
            print(f"Skipping user without email: {user['Username']}")
            continue
        
        # Check if already has subscription
        try:
            existing = subscriptions_table.get_item(Key={'email': email})
            if 'Item' in existing:
                print(f"✓ {email} - Already has subscription ({existing['Item'].get('tier')})")
                continue
        except Exception as e:
            print(f"Error checking {email}: {e}")
        
        # Grant Pro tier
        try:
            subscriptions_table.put_item(Item={
                'email': email,
                'tier': 'pro',
                'status': 'active',
                'created_at': datetime.utcnow().isoformat(),
                'source': 'existing_user_migration',
                'notes': 'Granted Pro tier to existing user'
            })
            print(f"✓ {email} - Granted Pro tier")
        except Exception as e:
            print(f"✗ {email} - Error: {e}")

if __name__ == '__main__':
    main()

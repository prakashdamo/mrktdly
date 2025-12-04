import json
import os
import boto3
import stripe
from datetime import datetime

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

dynamodb = boto3.resource('dynamodb')
subscriptions_table = dynamodb.Table('mrktdly-subscriptions')

def lambda_handler(event, context):
    """Handle Stripe webhook events"""
    
    try:
        payload = event['body']
        sig_header = event['headers'].get('Stripe-Signature')
        
        # Verify webhook signature
        stripe_event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        print(f"Webhook event: {stripe_event['type']}")
        
        # Handle different event types
        if stripe_event['type'] == 'checkout.session.completed':
            handle_checkout_completed(stripe_event['data']['object'])
        
        elif stripe_event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(stripe_event['data']['object'])
        
        elif stripe_event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(stripe_event['data']['object'])
        
        return {'statusCode': 200, 'body': json.dumps({'received': True})}
        
    except Exception as e:
        print(f'Webhook error: {e}')
        return {'statusCode': 400, 'body': json.dumps({'error': str(e)})}

def handle_checkout_completed(session):
    """Upgrade user to paid tier after successful checkout"""
    email = session['customer_email']
    tier = session['metadata'].get('tier', 'pro')
    
    subscriptions_table.update_item(
        Key={'email': email},
        UpdateExpression='SET tier = :tier, #status = :status, stripe_customer_id = :customer, stripe_subscription_id = :subscription, updated_at = :updated',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':tier': tier,
            ':status': 'active',
            ':customer': session.get('customer'),
            ':subscription': session.get('subscription'),
            ':updated': datetime.utcnow().isoformat()
        }
    )
    print(f'Upgraded {email} to {tier} tier')

def handle_subscription_updated(subscription):
    """Handle subscription changes"""
    customer_id = subscription['customer']
    status = subscription['status']
    
    # Get email from customer
    customer = stripe.Customer.retrieve(customer_id)
    email = customer['email']
    
    subscriptions_table.update_item(
        Key={'email': email},
        UpdateExpression='SET #status = :status, updated_at = :updated',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': 'active' if status == 'active' else 'inactive',
            ':updated': datetime.utcnow().isoformat()
        }
    )
    print(f'Updated subscription status for {email}: {status}')

def handle_subscription_deleted(subscription):
    """Downgrade user to free tier when subscription cancelled"""
    customer_id = subscription['customer']
    
    # Get email from customer
    customer = stripe.Customer.retrieve(customer_id)
    email = customer['email']
    
    subscriptions_table.update_item(
        Key={'email': email},
        UpdateExpression='SET tier = :tier, #status = :status, updated_at = :updated',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':tier': 'free',
            ':status': 'cancelled',
            ':updated': datetime.utcnow().isoformat()
        }
    )
    print(f'Downgraded {email} to free tier')

import json
import os
import stripe

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def lambda_handler(event, context):
    """Create Stripe checkout session"""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        tier = body.get('tier', 'pro')  # 'basic' or 'pro'
        
        if not email:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email required'})
            }
        
        # Price IDs (create these in Stripe Dashboard)
        price_ids = {
            'basic': os.environ.get('STRIPE_BASIC_PRICE_ID'),
            'pro': os.environ.get('STRIPE_PRO_PRICE_ID')
        }
        
        if tier not in price_ids or not price_ids[tier]:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid tier'})
            }
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=['card'],
            line_items=[{
                'price': price_ids[tier],
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://marketdly.com/success.html?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://marketdly.com/pricing.html',
            metadata={
                'email': email,
                'tier': tier
            }
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'sessionId': session.id,
                'url': session.url
            })
        }
        
    except Exception as e:
        print(f'Error: {e}')
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

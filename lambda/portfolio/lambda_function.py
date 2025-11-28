import json
import boto3
import urllib.request
from decimal import Decimal
from datetime import datetime
import uuid

dynamodb = boto3.resource('dynamodb')
portfolio_table = dynamodb.Table('mrktdly-portfolio')

def lambda_handler(event, context):
    """Handle portfolio operations"""
    http_method = event.get('httpMethod', '')
    path = event.get('path', '')
    body = json.loads(event.get('body', '{}')) if event.get('body') else {}
    user_email = body.get('user_email') or event.get('queryStringParameters', {}).get('user_email')

    if not user_email:
        return response(400, {'error': 'user_email required'})

    if http_method == 'POST' and 'add' in path:
        return add_holding(user_email, body)
    elif http_method == 'DELETE':
        return delete_holding(user_email, body.get('holding_id'))
    elif http_method == 'GET':
        return get_portfolio(user_email)

    return response(400, {'error': 'Invalid request'})

def add_holding(user_email, data):
    """Add a new holding to portfolio"""
    try:
        holding_id = str(uuid.uuid4())
        item = {
            'user_email': user_email,
            'holding_id': holding_id,
            'ticker': data['ticker'].upper(),
            'shares': Decimal(str(data['shares'])),
            'buy_price': Decimal(str(data['buy_price'])),
            'buy_date': data.get('buy_date', datetime.utcnow().strftime('%Y-%m-%d')),
            'created_at': datetime.utcnow().isoformat()
        }
        portfolio_table.put_item(Item=item)
        return response(200, {'message': 'Holding added', 'holding_id': holding_id})
    except Exception as e:
        return response(500, {'error': str(e)})

def delete_holding(user_email, holding_id):
    """Delete a holding from portfolio"""
    try:
        portfolio_table.delete_item(Key={'user_email': user_email, 'holding_id': holding_id})
        return response(200, {'message': 'Holding deleted'})
    except Exception as e:
        return response(500, {'error': str(e)})

def get_portfolio(user_email):
    """Get user's portfolio with current prices and P&L"""
    try:
        result = portfolio_table.query(KeyConditionExpression='user_email = :email',
                                       ExpressionAttributeValues={':email': user_email})
        holdings = result.get('Items', [])

        if not holdings:
            return response(200, {'holdings': [], 'total_value': 0, 'total_cost': 0, 'total_gain': 0})

        # Fetch current prices
        for holding in holdings:
            current_price = fetch_current_price(holding['ticker'])
            holding['current_price'] = current_price
            holding['current_value'] = float(holding['shares']) * current_price
            holding['cost_basis'] = float(holding['shares']) * float(holding['buy_price'])
            holding['gain_loss'] = holding['current_value'] - holding['cost_basis']
            holding['gain_loss_pct'] = (holding['gain_loss'] / holding['cost_basis'] * 100) if holding['cost_basis'] > 0 else 0

            # Convert Decimal to float for JSON
            holding['shares'] = float(holding['shares'])
            holding['buy_price'] = float(holding['buy_price'])

        # Calculate totals
        total_value = sum(h['current_value'] for h in holdings)
        total_cost = sum(h['cost_basis'] for h in holdings)
        total_gain = total_value - total_cost
        total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0

        return response(200, {
            'holdings': holdings,
            'total_value': round(total_value, 2),
            'total_cost': round(total_cost, 2),
            'total_gain': round(total_gain, 2),
            'total_gain_pct': round(total_gain_pct, 2)
        })
    except Exception as e:
        return response(500, {'error': str(e)})

def fetch_current_price(ticker):
    """Fetch current price from Yahoo Finance"""
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d'
        if not url.startswith('https://'):
            raise ValueError('Only HTTPS URLs are allowed')
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
            data = json.loads(resp.read())
            return data['chart']['result'][0]['meta']['regularMarketPrice']
    except Exception:
        return 0.0

def response(status_code, body):
    """Return API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body)
    }

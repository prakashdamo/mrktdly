import json
import boto3
import urllib.request
from decimal import Decimal
from datetime import datetime
import uuid

dynamodb = boto3.resource('dynamodb')
portfolios_table = dynamodb.Table('mrktdly-portfolios')
performance_table = dynamodb.Table('mrktdly-performance')

def lambda_handler(event, context):
    """Handle portfolio operations"""
    http_method = event.get('httpMethod', '')
    path = event.get('path', '')
    body = json.loads(event.get('body', '{}')) if event.get('body') else {}
    params = event.get('queryStringParameters') or {}
    
    user_email = body.get('user_email') or params.get('user_email')
    
    if 'leaderboard' in path:
        return get_leaderboard(params.get('period', 'all-time'))
    
    if not user_email:
        return response(400, {'error': 'user_email required'})
    
    if http_method == 'POST':
        return create_portfolio(user_email, body)
    elif http_method == 'GET':
        portfolio_id = params.get('portfolio_id')
        if portfolio_id:
            return get_portfolio_detail(portfolio_id)
        return get_user_portfolios(user_email)
    elif http_method == 'DELETE':
        return delete_portfolio(body.get('portfolio_id'), user_email)
    
    return response(400, {'error': 'Invalid request'})

def create_portfolio(user_email, data):
    """Create a new portfolio with % allocations"""
    try:
        holdings = data.get('holdings', [])
        if not holdings or len(holdings) < 3:
            return response(400, {'error': 'Minimum 3 holdings required'})
        
        total_allocation = sum(h.get('allocation_pct', 0) for h in holdings)
        if abs(total_allocation - 100) > 0.01:
            return response(400, {'error': f'Allocations must total 100% (got {total_allocation}%)'})
        
        portfolio_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        # Fetch current prices and lock them
        enriched_holdings = []
        for holding in holdings:
            ticker = holding['ticker'].upper()
            current_price = fetch_current_price(ticker)
            if current_price == 0:
                return response(400, {'error': f'Invalid ticker: {ticker}'})
            
            enriched_holdings.append({
                'ticker': ticker,
                'allocation_pct': Decimal(str(holding['allocation_pct'])),
                'entry_price': Decimal(str(current_price)),
                'entry_date': created_at
            })
        
        portfolio = {
            'portfolio_id': portfolio_id,
            'user_email': user_email,
            'portfolio_name': data.get('portfolio_name', 'My Portfolio'),
            'created_at': created_at,
            'is_public': data.get('is_public', True),
            'status': 'active',
            'holdings': enriched_holdings,
            'starting_value': Decimal('10000')
        }
        
        portfolios_table.put_item(Item=portfolio)
        
        # Create initial performance snapshot
        performance_table.put_item(Item={
            'portfolio_id': portfolio_id,
            'snapshot_date': created_at[:10],
            'total_return_pct': Decimal('0'),
            'portfolio_value': Decimal('10000')
        })
        
        return response(200, {'message': 'Portfolio created', 'portfolio_id': portfolio_id})
    except Exception as e:
        return response(500, {'error': str(e)})

def get_user_portfolios(user_email):
    """Get all portfolios for a user"""
    try:
        result = portfolios_table.query(
            IndexName='user-index',
            KeyConditionExpression='user_email = :email',
            ExpressionAttributeValues={':email': user_email}
        )
        
        portfolios = result.get('Items', [])
        
        # Calculate current performance for each
        for portfolio in portfolios:
            current_value, total_return = calculate_portfolio_value(portfolio)
            portfolio['current_value'] = float(current_value)
            portfolio['total_return_pct'] = float(total_return)
            portfolio['starting_value'] = float(portfolio.get('starting_value', 10000))
            
            # Convert Decimal for JSON
            for holding in portfolio.get('holdings', []):
                holding['allocation_pct'] = float(holding['allocation_pct'])
                holding['entry_price'] = float(holding['entry_price'])
        
        return response(200, {'portfolios': portfolios})
    except Exception as e:
        return response(500, {'error': str(e)})

def get_portfolio_detail(portfolio_id):
    """Get detailed portfolio info with current performance"""
    try:
        result = portfolios_table.get_item(Key={'portfolio_id': portfolio_id})
        portfolio = result.get('Item')
        
        if not portfolio:
            return response(404, {'error': 'Portfolio not found'})
        
        current_value, total_return = calculate_portfolio_value(portfolio)
        
        # Get holdings with current prices
        holdings_detail = []
        for holding in portfolio.get('holdings', []):
            current_price = fetch_current_price(holding['ticker'])
            entry_price = float(holding['entry_price'])
            allocation = float(holding['allocation_pct'])
            
            entry_value = 10000 * (allocation / 100)
            current_holding_value = entry_value * (current_price / entry_price)
            holding_return = ((current_price - entry_price) / entry_price) * 100
            
            holdings_detail.append({
                'ticker': holding['ticker'],
                'allocation_pct': allocation,
                'entry_price': entry_price,
                'current_price': current_price,
                'entry_value': round(entry_value, 2),
                'current_value': round(current_holding_value, 2),
                'return_pct': round(holding_return, 2)
            })
        
        portfolio['holdings'] = holdings_detail
        portfolio['current_value'] = float(current_value)
        portfolio['total_return_pct'] = float(total_return)
        portfolio['starting_value'] = float(portfolio.get('starting_value', 10000))
        
        return response(200, portfolio)
    except Exception as e:
        return response(500, {'error': str(e)})

def delete_portfolio(portfolio_id, user_email):
    """Archive a portfolio (soft delete)"""
    try:
        result = portfolios_table.get_item(Key={'portfolio_id': portfolio_id})
        portfolio = result.get('Item')
        
        if not portfolio or portfolio.get('user_email') != user_email:
            return response(403, {'error': 'Unauthorized'})
        
        portfolios_table.update_item(
            Key={'portfolio_id': portfolio_id},
            UpdateExpression='SET #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'archived'}
        )
        
        return response(200, {'message': 'Portfolio archived'})
    except Exception as e:
        return response(500, {'error': str(e)})

def get_leaderboard(period='all-time'):
    """Get top performing portfolios"""
    try:
        result = portfolios_table.scan(
            FilterExpression='#status = :status AND is_public = :public',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'active', ':public': True}
        )
        
        portfolios = result.get('Items', [])
        
        # Calculate performance for each
        leaderboard = []
        for portfolio in portfolios:
            current_value, total_return = calculate_portfolio_value(portfolio)
            
            leaderboard.append({
                'portfolio_id': portfolio['portfolio_id'],
                'portfolio_name': portfolio['portfolio_name'],
                'user_email': portfolio['user_email'].split('@')[0] + '***',  # Anonymize
                'total_return_pct': float(total_return),
                'current_value': float(current_value),
                'created_at': portfolio['created_at']
            })
        
        # Sort by return
        leaderboard.sort(key=lambda x: x['total_return_pct'], reverse=True)
        
        return response(200, {'leaderboard': leaderboard[:50]})  # Top 50
    except Exception as e:
        return response(500, {'error': str(e)})

def calculate_portfolio_value(portfolio):
    """Calculate current portfolio value and return %"""
    starting_value = float(portfolio.get('starting_value', 10000))
    current_value = 0
    
    for holding in portfolio.get('holdings', []):
        ticker = holding['ticker']
        allocation_pct = float(holding['allocation_pct'])
        entry_price = float(holding['entry_price'])
        
        current_price = fetch_current_price(ticker)
        
        # Calculate value: starting allocation * price change ratio
        entry_value = starting_value * (allocation_pct / 100)
        current_holding_value = entry_value * (current_price / entry_price)
        current_value += current_holding_value
    
    total_return_pct = ((current_value - starting_value) / starting_value) * 100
    
    return Decimal(str(round(current_value, 2))), Decimal(str(round(total_return_pct, 2)))

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

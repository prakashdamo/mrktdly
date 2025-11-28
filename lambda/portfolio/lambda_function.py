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
    
    # Submit to challenge
    if 'submit-challenge' in path and http_method == 'POST':
        return submit_to_challenge(body.get('portfolio_id'), user_email)
    
    # Backtest endpoint
    if 'backtest' in path and params.get('portfolio_id'):
        return backtest_portfolio(params.get('portfolio_id'))
    
    # Portfolio detail view doesn't require user_email
    if http_method == 'GET' and params.get('portfolio_id'):
        return get_portfolio_detail(params.get('portfolio_id'))
    
    if not user_email:
        return response(400, {'error': 'user_email required'})
    
    if http_method == 'POST':
        return create_portfolio(user_email, body)
    elif http_method == 'GET':
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
            'submitted_to_challenge': False,
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
    """Get top performing portfolios submitted to challenge"""
    try:
        result = portfolios_table.scan(
            FilterExpression='#status = :status AND submitted_to_challenge = :submitted',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'active', ':submitted': True}
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
                'created_at': portfolio['created_at'],
                'submitted_at': portfolio.get('submitted_at', portfolio['created_at'])
            })
        
        # Sort by return
        leaderboard.sort(key=lambda x: x['total_return_pct'], reverse=True)
        
        return response(200, {'leaderboard': leaderboard[:50]})  # Top 50
    except Exception as e:
        return response(500, {'error': str(e)})

def submit_to_challenge(portfolio_id, user_email):
    """Submit portfolio to public challenge"""
    try:
        from datetime import datetime as dt
        
        result = portfolios_table.get_item(Key={'portfolio_id': portfolio_id})
        portfolio = result.get('Item')
        
        if not portfolio:
            return response(404, {'error': 'Portfolio not found'})
        
        if portfolio.get('user_email') != user_email:
            return response(403, {'error': 'Unauthorized'})
        
        if portfolio.get('submitted_to_challenge'):
            return response(400, {'error': 'Portfolio already submitted to challenge'})
        
        # Submit to challenge
        portfolios_table.update_item(
            Key={'portfolio_id': portfolio_id},
            UpdateExpression='SET submitted_to_challenge = :submitted, submitted_at = :timestamp',
            ExpressionAttributeValues={
                ':submitted': True,
                ':timestamp': dt.utcnow().isoformat()
            }
        )
        
        return response(200, {'message': 'Portfolio submitted to challenge!'})
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

def fetch_historical_price(ticker, date_str):
    """Fetch historical closing price for a specific date"""
    try:
        from datetime import datetime as dt, timedelta
        target_date = dt.strptime(date_str, '%Y-%m-%d')
        
        # Get data for a week range to handle weekends/holidays
        start_date = target_date - timedelta(days=7)
        end_date = target_date + timedelta(days=1)
        
        start_unix = int(start_date.timestamp())
        end_unix = int(end_date.timestamp())
        
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&period1={start_unix}&period2={end_unix}'
        if not url.startswith('https://'):
            raise ValueError('Only HTTPS URLs are allowed')
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
            data = json.loads(resp.read())
            result = data['chart']['result'][0]
            
            # Get the closest trading day's close price
            closes = result['indicators']['quote'][0]['close']
            # Return last available close price (handles weekends/holidays)
            for price in reversed(closes):
                if price is not None:
                    return price
            return 0.0
    except Exception:
        return 0.0

def backtest_portfolio(portfolio_id):
    """Run backtest for 1, 3, and 5 years back"""
    try:
        from datetime import datetime as dt, timedelta
        
        result = portfolios_table.get_item(Key={'portfolio_id': portfolio_id})
        portfolio = result.get('Item')
        
        if not portfolio:
            return response(404, {'error': 'Portfolio not found'})
        
        today = dt.utcnow()
        backtest_periods = [
            {'years': 1, 'date': (today - timedelta(days=365)).strftime('%Y-%m-%d')},
            {'years': 3, 'date': (today - timedelta(days=365*3)).strftime('%Y-%m-%d')},
            {'years': 5, 'date': (today - timedelta(days=365*5)).strftime('%Y-%m-%d')}
        ]
        
        results = []
        
        for period in backtest_periods:
            backtest_date = period['date']
            holdings_performance = []
            total_value = 0
            
            for holding in portfolio.get('holdings', []):
                ticker = holding['ticker']
                allocation_pct = float(holding['allocation_pct'])
                
                historical_price = fetch_historical_price(ticker, backtest_date)
                current_price = fetch_current_price(ticker)
                
                if historical_price == 0:
                    continue
                
                entry_value = 10000 * (allocation_pct / 100)
                current_value = entry_value * (current_price / historical_price)
                return_pct = ((current_price - historical_price) / historical_price) * 100
                
                holdings_performance.append({
                    'ticker': ticker,
                    'allocation_pct': allocation_pct,
                    'entry_price': round(historical_price, 2),
                    'current_price': round(current_price, 2),
                    'return_pct': round(return_pct, 2)
                })
                
                total_value += current_value
            
            total_return_pct = ((total_value - 10000) / 10000) * 100
            
            results.append({
                'years': period['years'],
                'backtest_date': backtest_date,
                'total_return_pct': round(total_return_pct, 2),
                'portfolio_value': round(total_value, 2),
                'holdings': holdings_performance
            })
        
        # Get actual portfolio performance
        actual_value, actual_return = calculate_portfolio_value(portfolio)
        
        return response(200, {
            'portfolio_name': portfolio['portfolio_name'],
            'actual_return_pct': float(actual_return),
            'actual_created': portfolio['created_at'],
            'backtests': results
        })
    except Exception as e:
        return response(500, {'error': str(e)})

def response(status_code, body):
    """Return API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body)
    }

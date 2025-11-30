import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
signals_table = dynamodb.Table('mrktdly-signal-performance')
price_table = dynamodb.Table('mrktdly-price-history')

def lambda_handler(event, context):
    """Evaluate open signals and update outcomes"""
    
    # Get all open signals
    response = signals_table.query(
        IndexName='status-index',
        KeyConditionExpression=Key('status').eq('OPEN')
    )
    
    open_signals = response['Items']
    evaluated = 0
    closed = 0
    
    for signal in open_signals:
        result = evaluate_signal(signal)
        if result:
            evaluated += 1
            if result['status'] != 'OPEN':
                closed += 1
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'evaluated': evaluated,
            'closed': closed,
            'total_open': len(open_signals)
        })
    }

def evaluate_signal(signal):
    """Check if signal hit target, stop, or expired"""
    
    ticker = signal['ticker']
    signal_date = signal['signal_date']
    entry = float(signal['entry'])
    target = float(signal['target'])
    stop_loss = float(signal['stop_loss'])
    action = signal['action']
    
    # Get price history since signal date
    end_date = datetime.utcnow()
    start_date = datetime.strptime(signal_date, '%Y-%m-%d')
    days_elapsed = (end_date - start_date).days
    
    # Expire after 5 trading days
    if days_elapsed > 7:
        current_price = get_latest_price(ticker)
        if current_price:
            return_pct = calculate_return(action, entry, current_price)
            update_signal(signal, 'EXPIRED', return_pct, days_elapsed)
            return {'status': 'EXPIRED', 'return': return_pct}
    
    # Check each day's price action
    response = price_table.query(
        KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').gte(signal_date),
        ScanIndexForward=True
    )
    
    for day in response['Items']:
        high = float(day['high'])
        low = float(day['low'])
        date = day['date']
        
        if action == 'BUY':
            # Check if target hit
            if high >= target:
                return_pct = calculate_return(action, entry, target)
                days_held = (datetime.strptime(date, '%Y-%m-%d') - start_date).days
                update_signal(signal, 'WIN', return_pct, days_held, date)
                return {'status': 'WIN', 'return': return_pct}
            
            # Check if stop hit
            if low <= stop_loss:
                return_pct = calculate_return(action, entry, stop_loss)
                days_held = (datetime.strptime(date, '%Y-%m-%d') - start_date).days
                update_signal(signal, 'LOSS', return_pct, days_held, date)
                return {'status': 'LOSS', 'return': return_pct}
        
        elif action == 'SELL':
            # Check if target hit (price goes down)
            if low <= target:
                return_pct = calculate_return(action, entry, target)
                days_held = (datetime.strptime(date, '%Y-%m-%d') - start_date).days
                update_signal(signal, 'WIN', return_pct, days_held, date)
                return {'status': 'WIN', 'return': return_pct}
            
            # Check if stop hit (price goes up)
            if high >= stop_loss:
                return_pct = calculate_return(action, entry, stop_loss)
                days_held = (datetime.strptime(date, '%Y-%m-%d') - start_date).days
                update_signal(signal, 'LOSS', return_pct, days_held, date)
                return {'status': 'LOSS', 'return': return_pct}
    
    return {'status': 'OPEN'}

def calculate_return(action, entry, exit_price):
    """Calculate return percentage"""
    if action == 'BUY':
        return round(((exit_price - entry) / entry) * 100, 2)
    else:  # SELL
        return round(((entry - exit_price) / entry) * 100, 2)

def get_latest_price(ticker):
    """Get most recent closing price"""
    try:
        response = price_table.query(
            KeyConditionExpression=Key('ticker').eq(ticker),
            ScanIndexForward=False,
            Limit=1
        )
        if response['Items']:
            return float(response['Items'][0]['close'])
    except:
        pass
    return None

def update_signal(signal, outcome, return_pct, days_held, closed_date=None):
    """Update signal with outcome"""
    
    if closed_date is None:
        closed_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    signals_table.update_item(
        Key={
            'ticker': signal['ticker'],
            'signal_date': signal['signal_date']
        },
        UpdateExpression='SET #status = :status, outcome = :outcome, return_pct = :return_pct, closed_date = :closed_date, days_held = :days_held',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': outcome,
            ':outcome': outcome,
            ':return_pct': Decimal(str(return_pct)),
            ':closed_date': closed_date,
            ':days_held': days_held
        }
    )

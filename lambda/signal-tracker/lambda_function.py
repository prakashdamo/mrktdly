import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
swing_signals_table = dynamodb.Table('mrktdly-swing-signals')
predictions_table = dynamodb.Table('mrktdly-predictions')
price_table = dynamodb.Table('mrktdly-price-history')

def lambda_handler(event, context):
    """Track both swing signals and AI predictions in unified swing-signals table"""
    
    try:
        # Get today's date
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Track AI predictions - copy to swing-signals table
        pred_response = predictions_table.query(
            KeyConditionExpression=Key('date').eq(today)
        )
        for pred in pred_response.get('Items', []):
            track_ai_prediction(pred, today)
        
        # Evaluate all open signals (both technical and AI)
        evaluate_open_signals()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'ai_predictions_tracked': len(pred_response.get('Items', [])),
                'message': 'Unified tracking in swing-signals table'
            })
        }
        
    except Exception as e:
        print(f'Error in signal tracker: {e}')
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def track_ai_prediction(pred, date):
    """Track an AI prediction in swing-signals table"""
    try:
        ticker = pred['ticker']
        
        # Check if active AI prediction already exists for this ticker
        response = swing_signals_table.query(
            KeyConditionExpression=Key('ticker').eq(ticker),
            FilterExpression='#s = :status AND #src = :source',
            ExpressionAttributeNames={'#s': 'status', '#src': 'source'},
            ExpressionAttributeValues={':status': 'active', ':source': 'AI'}
        )
        
        if response['Items']:
            # Update existing prediction with new confirmation
            existing = response['Items'][0]
            conf_dates = existing.get('confirmation_dates', [existing['date']])
            if date not in conf_dates:
                conf_dates.append(date)
                
            swing_signals_table.update_item(
                Key={'ticker': ticker, 'date': existing['date']},
                UpdateExpression='SET signal_count = signal_count + :inc, last_seen = :today, confirmation_dates = :dates',
                ExpressionAttributeValues={
                    ':inc': Decimal('1'),
                    ':today': date,
                    ':dates': conf_dates
                }
            )
            print(f'Updated AI prediction: {ticker} ({len(conf_dates)} confirmations)')
            return
            
        # New AI prediction
        price = float(pred.get('price', 0))
        entry = price
        target = price * 1.03  # 3% target
        stop = price * 0.97    # 3% stop
        
        item = {
            'ticker': ticker,
            'date': date,
            'entry': Decimal(str(entry)),
            'target': Decimal(str(target)),
            'support': Decimal(str(stop)),
            'resistance': Decimal(str(target)),
            'status': 'active',
            'source': 'AI',
            'pattern': 'ai_prediction',
            'risk_reward': Decimal('1.0'),
            'conviction': Decimal(str(float(pred.get('probability', 0)) * 5)),  # Scale to 0-5
            'detected_at': f"{date}T12:00:00",
            'signal_count': Decimal('1'),
            'last_seen': date,
            'confirmation_dates': [date]
        }
        
        swing_signals_table.put_item(Item=item)
        print(f'Tracked AI prediction: {ticker}')
    except Exception as e:
        print(f'Error tracking AI prediction {pred.get("ticker")}: {e}')

def evaluate_open_signals():
    """Evaluate all open signals"""
    response = swing_signals_table.scan(
        FilterExpression='#s = :status',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':status': 'active'}
    )
    
    for signal in response.get('Items', []):
        check_signal_outcome(signal)

def check_signal_outcome(signal):
    """Check if signal hit target, stop, or expired"""
    try:
        ticker = signal['ticker']
        signal_date = signal['date']
        entry = float(signal['entry'])
        target = float(signal['target'])
        stop = float(signal.get('stop_loss', signal.get('support', 0)))
        
        # Get price history since signal date
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
        price_response = price_table.query(
            KeyConditionExpression=Key('ticker').eq(ticker) & Key('date').between(signal_date, end_date)
        )
        
        prices = sorted(price_response.get('Items', []), key=lambda x: x['date'])
        if not prices:
            return
        
        # Check each day
        for i, price_data in enumerate(prices[1:], 1):  # Skip first day (entry)
            high = float(price_data.get('high', 0))
            low = float(price_data.get('low', 0))
            close = float(price_data.get('close', 0))
            
            # Check if hit target
            if high >= target:
                return_pct = (target - entry) / entry * 100
                update_signal(signal, 'WIN', return_pct, price_data['date'], i)
                return
            
            # Check if hit stop
            if low <= stop:
                return_pct = (stop - entry) / entry * 100
                update_signal(signal, 'LOSS', return_pct, price_data['date'], i)
                return
        
        # Check if expired (10 days)
        days_held = len(prices) - 1
        if days_held >= 10:
            latest_close = float(prices[-1].get('close', entry))
            return_pct = (latest_close - entry) / entry * 100
            outcome = 'EXPIRED' if return_pct > 0 else 'LOSS'
            update_signal(signal, outcome, return_pct, prices[-1]['date'], days_held)
            
    except Exception as e:
        print(f'Error checking signal {signal.get("ticker")}: {e}')

def update_signal(signal, outcome, return_pct, close_date, days_held):
    """Update signal with outcome"""
    try:
        swing_signals_table.update_item(
            Key={'ticker': signal['ticker'], 'date': signal['date']},
            UpdateExpression='SET #s = :status, outcome = :outcome, return_pct = :ret, closed_date = :closed, days_held = :days',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':status': 'closed',
                ':outcome': outcome,
                ':ret': Decimal(str(return_pct)),
                ':closed': close_date,
                ':days': Decimal(str(days_held))
            }
        )
        print(f'Updated {signal["ticker"]}: {outcome} {return_pct:+.2f}% in {days_held} days')
    except Exception as e:
        print(f'Error updating signal {signal.get("ticker")}: {e}')

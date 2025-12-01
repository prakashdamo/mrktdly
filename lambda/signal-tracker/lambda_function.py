import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
signals_table = dynamodb.Table('mrktdly-signal-performance')
swing_signals_table = dynamodb.Table('mrktdly-swing-signals')
predictions_table = dynamodb.Table('mrktdly-predictions')
price_table = dynamodb.Table('mrktdly-price-history')

def lambda_handler(event, context):
    """Track both swing signals and AI predictions for performance verification"""
    
    try:
        # Get today's date
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Track swing signals
        swing_response = swing_signals_table.query(
            KeyConditionExpression=Key('date').eq(today)
        )
        for signal in swing_response.get('Items', []):
            track_swing_signal(signal, today)
        
        # Track AI predictions
        pred_response = predictions_table.query(
            KeyConditionExpression=Key('date').eq(today)
        )
        for pred in pred_response.get('Items', []):
            track_ai_prediction(pred, today)
        
        # Evaluate open signals
        evaluate_open_signals()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'swing_signals_tracked': len(swing_response.get('Items', [])),
                'ai_predictions_tracked': len(pred_response.get('Items', []))
            })
        }
        
    except Exception as e:
        print(f'Error in signal tracker: {e}')
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def track_swing_signal(signal, date):
    """Track a swing signal"""
    try:
        entry = float(signal.get('entry', 0))
        target = float(signal.get('target', 0))
        stop = float(signal.get('support', 0))
        
        item = {
            'ticker': signal['ticker'],
            'signal_date': date,  # Required sort key
            'date': date,
            'action': 'BUY',
            'entry': Decimal(str(entry)),
            'target': Decimal(str(target)),
            'stop_loss': Decimal(str(stop)),
            'conviction': Decimal('3.0'),
            'status': 'OPEN',
            'source': 'Technical',
            'pattern': signal.get('pattern', ''),
            'risk_reward': Decimal(str(signal.get('risk_reward', 0)))
        }
        
        signals_table.put_item(
            Item=item,
            ConditionExpression='attribute_not_exists(ticker) AND attribute_not_exists(signal_date)'
        )
        print(f'Tracked swing signal: {signal["ticker"]}')
    except ClientError as e:
        if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
            print(f'Error tracking swing signal {signal.get("ticker")}: {e}')
    except Exception as e:
        print(f'Error tracking swing signal {signal.get("ticker")}: {e}')

def track_ai_prediction(pred, date):
    """Track an AI prediction"""
    try:
        price = float(pred.get('price', 0))
        entry = price
        target = price * 1.03  # 3% target
        stop = price * 0.97    # 3% stop
        
        item = {
            'ticker': pred['ticker'],
            'signal_date': date,  # Required sort key
            'date': date,
            'action': 'BUY',
            'entry': Decimal(str(entry)),
            'target': Decimal(str(target)),
            'stop_loss': Decimal(str(stop)),
            'conviction': Decimal(str(float(pred.get('probability', 0)) * 5)),  # Scale to 0-5
            'status': 'OPEN',
            'source': 'AI',
            'pattern': 'ai_prediction',
            'risk_reward': Decimal('1.0'),
            'probability': Decimal(str(pred.get('probability', 0)))
        }
        
        signals_table.put_item(
            Item=item,
            ConditionExpression='attribute_not_exists(ticker) AND attribute_not_exists(signal_date)'
        )
        print(f'Tracked AI prediction: {pred["ticker"]}')
    except ClientError as e:
        if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
            print(f'Error tracking AI prediction {pred.get("ticker")}: {e}')
    except Exception as e:
        print(f'Error tracking AI prediction {pred.get("ticker")}: {e}')

def evaluate_open_signals():
    """Evaluate all open signals"""
    response = signals_table.scan(
        FilterExpression='#s = :status',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':status': 'OPEN'}
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
        stop = float(signal['stop_loss'])
        
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
        signals_table.update_item(
            Key={'ticker': signal['ticker'], 'date': signal['date']},
            UpdateExpression='SET #s = :status, outcome = :outcome, return_pct = :ret, closed_date = :closed, days_held = :days',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':status': 'CLOSED',
                ':outcome': outcome,
                ':ret': Decimal(str(return_pct)),
                ':closed': close_date,
                ':days': Decimal(str(days_held))
            }
        )
        print(f'Updated {signal["ticker"]}: {outcome} {return_pct:+.2f}% in {days_held} days')
    except Exception as e:
        print(f'Error updating signal {signal.get("ticker")}: {e}')

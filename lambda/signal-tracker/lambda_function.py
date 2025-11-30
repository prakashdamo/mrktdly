import json
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
signals_table = dynamodb.Table('mrktdly-signal-performance')

def lambda_handler(event, context):
    """Record trading signals for performance tracking"""
    
    try:
        # Extract signal data
        ticker = event['ticker']
        recommendation = event['recommendation']
        market_state = event.get('market_state') or {}
        
        action = recommendation.get('action', 'HOLD')
        if action == 'HOLD':
            return {'statusCode': 200, 'body': 'No signal to track'}
        
        entry_exit = recommendation.get('entry_exit', {})
        entry = float(entry_exit.get('entry', 0))
        target = float(entry_exit.get('target', 0))
        stop_loss = float(entry_exit.get('stop_loss', 0))
        
        # Validate signal
        if entry <= 0 or target <= 0 or stop_loss <= 0:
            print(f'Invalid signal: entry={entry}, target={target}, stop={stop_loss}')
            return {'statusCode': 400, 'body': 'Invalid signal: prices must be > 0'}
        
        if action == 'BUY' and target <= entry:
            print(f'Invalid BUY signal: target {target} <= entry {entry}')
            return {'statusCode': 400, 'body': 'Invalid BUY: target must be > entry'}
        
        if action == 'BUY' and stop_loss >= entry:
            print(f'Invalid BUY signal: stop {stop_loss} >= entry {entry}')
            return {'statusCode': 400, 'body': 'Invalid BUY: stop must be < entry'}
        
        if action == 'SELL' and target >= entry:
            print(f'Invalid SELL signal: target {target} >= entry {entry}')
            return {'statusCode': 400, 'body': 'Invalid SELL: target must be < entry'}
        
        if action == 'SELL' and stop_loss <= entry:
            print(f'Invalid SELL signal: stop {stop_loss} <= entry {entry}')
            return {'statusCode': 400, 'body': 'Invalid SELL: stop must be > entry'}
        
        signal = {
            'ticker': ticker,
            'signal_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'entry': Decimal(str(entry)),
            'target': Decimal(str(target)),
            'stop_loss': Decimal(str(stop_loss)),
            'conviction': Decimal(str(recommendation.get('conviction_score', 0))),
            'market_state': market_state.get('state', 'UNKNOWN'),
            'state_confidence': Decimal(str(market_state.get('confidence', 0))),
            'risk_reward': str(entry_exit.get('risk_reward', 'N/A')),
            'status': 'OPEN',
            'outcome': None,
            'return_pct': None,
            'closed_date': None,
            'days_held': None
        }
        
        # Prevent duplicate signals for same ticker on same day
        try:
            signals_table.put_item(
                Item=signal,
                ConditionExpression='attribute_not_exists(ticker) AND attribute_not_exists(signal_date)'
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print(f'Signal already exists for {ticker} on {signal["signal_date"]}')
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'Signal already recorded', 'ticker': ticker})
                }
            raise
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Signal recorded', 'ticker': ticker})
        }
        
    except Exception as e:
        print(f'Error recording signal: {e}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

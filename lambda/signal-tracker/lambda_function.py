import json
import boto3
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
        market_state = event.get('market_state', {})
        
        action = recommendation.get('action', 'HOLD')
        if action == 'HOLD':
            return {'statusCode': 200, 'body': 'No signal to track'}
        
        entry_exit = recommendation.get('entry_exit', {})
        
        signal = {
            'ticker': ticker,
            'signal_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'entry': Decimal(str(entry_exit.get('entry', 0))),
            'target': Decimal(str(entry_exit.get('target', 0))),
            'stop_loss': Decimal(str(entry_exit.get('stop_loss', 0))),
            'conviction': Decimal(str(recommendation.get('conviction_score', 0))),
            'market_state': market_state.get('state', 'UNKNOWN'),
            'state_confidence': Decimal(str(market_state.get('confidence', 0))),
            'risk_reward': entry_exit.get('risk_reward', 'N/A'),
            'status': 'OPEN',
            'outcome': None,
            'return_pct': None,
            'closed_date': None,
            'days_held': None
        }
        
        signals_table.put_item(Item=signal)
        
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

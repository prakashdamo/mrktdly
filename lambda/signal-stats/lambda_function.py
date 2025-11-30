import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
signals_table = dynamodb.Table('mrktdly-signal-performance')

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """Get performance statistics for signals"""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    ticker = event.get('queryStringParameters', {}).get('ticker') if event.get('queryStringParameters') else None
    days = int(event.get('queryStringParameters', {}).get('days', 30)) if event.get('queryStringParameters') else 30
    
    try:
        if ticker:
            stats = get_ticker_stats(ticker, days)
        else:
            stats = get_overall_stats(days)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(stats, default=decimal_to_float)
        }
    except Exception as e:
        print(f'Error: {e}')
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def get_ticker_stats(ticker, days):
    """Get stats for specific ticker"""
    
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    response = signals_table.query(
        KeyConditionExpression=Key('ticker').eq(ticker) & Key('signal_date').gte(cutoff_date)
    )
    
    signals = response['Items']
    return calculate_stats(signals, ticker)

def get_overall_stats(days):
    """Get overall stats across all tickers"""
    
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    # Scan for all signals (in production, use GSI on signal_date)
    response = signals_table.scan()
    
    all_signals = [s for s in response['Items'] if s['signal_date'] >= cutoff_date]
    
    return calculate_stats(all_signals, 'ALL')

def calculate_stats(signals, ticker):
    """Calculate performance metrics"""
    
    if not signals:
        return {
            'ticker': ticker,
            'total_signals': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'expectancy': 0,
            'recent_signals': []
        }
    
    closed_signals = [s for s in signals if s['status'] in ['WIN', 'LOSS', 'EXPIRED']]
    wins = [s for s in closed_signals if s.get('outcome') == 'WIN' or (s.get('return_pct') and float(s['return_pct']) > 0)]
    losses = [s for s in closed_signals if s not in wins]
    
    win_count = len(wins)
    loss_count = len(losses)
    total_closed = len(closed_signals)
    
    win_rate = (win_count / total_closed * 100) if total_closed > 0 else 0
    
    avg_win = sum(float(s['return_pct']) for s in wins) / win_count if win_count > 0 else 0
    avg_loss = sum(float(s['return_pct']) for s in losses) / loss_count if loss_count > 0 else 0
    
    expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss) if total_closed > 0 else 0
    
    # Get recent signals (last 10)
    recent = sorted(signals, key=lambda x: x['signal_date'], reverse=True)[:10]
    recent_signals = [{
        'ticker': s['ticker'],
        'date': s['signal_date'],
        'action': s['action'],
        'entry': float(s['entry']),
        'target': float(s['target']),
        'stop_loss': float(s['stop_loss']),
        'status': s['status'],
        'outcome': s.get('outcome'),
        'return_pct': float(s['return_pct']) if s.get('return_pct') else None,
        'days_held': s.get('days_held'),
        'conviction': s.get('conviction', 'MEDIUM')
    } for s in recent]
    
    # Stats by conviction level (skip if conviction is string)
    try:
        high_conviction = [s for s in closed_signals if isinstance(s.get('conviction'), (int, float, Decimal)) and float(s['conviction']) >= 0.8]
    except:
        high_conviction = []
    high_win_rate = (len([s for s in high_conviction if s['outcome'] == 'WIN']) / len(high_conviction) * 100) if high_conviction else 0
    
    return {
        'ticker': ticker,
        'total_signals': len(signals),
        'open_signals': len([s for s in signals if s['status'] == 'OPEN']),
        'closed_signals': total_closed,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate': round(win_rate, 1),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'expectancy': round(expectancy, 2),
        'risk_reward': round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
        'high_conviction_win_rate': round(high_win_rate, 1),
        'recent_signals': recent_signals
    }

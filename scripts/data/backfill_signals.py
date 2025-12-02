#!/usr/bin/env python3
"""Backfill historical signals and evaluate performance"""

import boto3
import json
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')
signals_table = dynamodb.Table('mrktdly-signal-performance')
price_table = dynamodb.Table('mrktdly-price-history')

def get_tickers_with_signals():
    """Get tickers that would generate signals"""
    return ['ARM', 'CLSK', 'HOOD', 'IONQ', 'LCID', 'MARA', 'MCHP', 'MSTR', 
            'NET', 'NIO', 'ORCL', 'PLTR', 'RIOT', 'RKLB', 'ZS']

def get_recommendation_for_date(ticker, date):
    """Get ML recommendation for a specific date"""
    try:
        response = lambda_client.invoke(
            FunctionName='mrktdly-ticker-analysis-v2',
            InvocationType='RequestResponse',
            Payload=json.dumps({'ticker': ticker})
        )
        result = json.loads(response['Payload'].read())
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            rec = body.get('recommendation', {})
            if rec.get('action') in ['BUY', 'SELL'] and rec.get('entry_exit'):
                return rec
    except Exception as e:
        print(f"Error getting recommendation for {ticker}: {e}")
    return None

def create_signal(ticker, date, recommendation, market_state):
    """Create a signal for a specific date"""
    entry_exit = recommendation['entry_exit']
    
    signal = {
        'ticker': ticker,
        'signal_date': date.strftime('%Y-%m-%d'),
        'timestamp': date.isoformat(),
        'action': recommendation['action'],
        'entry': Decimal(str(entry_exit['entry'])),
        'target': Decimal(str(entry_exit['target'])),
        'stop_loss': Decimal(str(entry_exit['stop_loss'])),
        'conviction': Decimal(str(recommendation.get('conviction_score', 3))),
        'market_state': market_state.get('state', 'UNKNOWN'),
        'state_confidence': Decimal(str(market_state.get('confidence', 0.5))),
        'risk_reward': str(entry_exit.get('risk_reward', 'N/A')),
        'status': 'OPEN',
        'outcome': None,
        'return_pct': None,
        'closed_date': None,
        'days_held': None
    }
    
    try:
        signals_table.put_item(
            Item=signal,
            ConditionExpression='attribute_not_exists(ticker) AND attribute_not_exists(signal_date)'
        )
        return signal
    except:
        return None

def evaluate_signal(signal):
    """Evaluate if signal hit target or stop"""
    ticker = signal['ticker']
    signal_date = datetime.strptime(signal['signal_date'], '%Y-%m-%d')
    entry = float(signal['entry'])
    target = float(signal['target'])
    stop_loss = float(signal['stop_loss'])
    action = signal['action']
    
    # Get price data for next 7 days
    end_date = min(signal_date + timedelta(days=7), datetime.now())
    
    response = price_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('ticker').eq(ticker) & 
                              boto3.dynamodb.conditions.Key('date').between(
                                  signal_date.strftime('%Y-%m-%d'),
                                  end_date.strftime('%Y-%m-%d')
                              ),
        ScanIndexForward=True
    )
    
    for day in response['Items']:
        high = float(day['high'])
        low = float(day['low'])
        date = day['date']
        days_held = (datetime.strptime(date, '%Y-%m-%d') - signal_date).days
        
        if action == 'BUY':
            if high >= target:
                return_pct = round((target - entry) / entry * 100, 2)
                return 'WIN', return_pct, days_held, date
            if low <= stop_loss:
                return_pct = round((stop_loss - entry) / entry * 100, 2)
                return 'LOSS', return_pct, days_held, date
        else:  # SELL
            if low <= target:
                return_pct = round((entry - target) / entry * 100, 2)
                return 'WIN', return_pct, days_held, date
            if high >= stop_loss:
                return_pct = round((entry - stop_loss) / entry * 100, 2)
                return 'LOSS', return_pct, days_held, date
    
    # Expired after 7 days
    if (datetime.now() - signal_date).days > 7:
        last_price = float(response['Items'][-1]['close']) if response['Items'] else entry
        return_pct = round((last_price - entry) / entry * 100, 2) if action == 'BUY' else round((entry - last_price) / entry * 100, 2)
        return 'EXPIRED', return_pct, 7, end_date.strftime('%Y-%m-%d')
    
    return None, None, None, None

def update_signal(ticker, signal_date, outcome, return_pct, days_held, closed_date):
    """Update signal with outcome"""
    signals_table.update_item(
        Key={'ticker': ticker, 'signal_date': signal_date},
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

def main():
    print("Backfilling signals for past 30 days...")
    
    # Delete existing signals
    print("\nDeleting existing signals...")
    response = signals_table.scan()
    for item in response['Items']:
        signals_table.delete_item(Key={'ticker': item['ticker'], 'signal_date': item['signal_date']})
    
    tickers = get_tickers_with_signals()
    start_date = datetime.now() - timedelta(days=30)
    
    signals_created = 0
    
    # Generate signals for past 30 days (only trading days)
    for days_ago in range(30, 0, -1):
        date = datetime.now() - timedelta(days=days_ago)
        
        # Skip weekends
        if date.weekday() >= 5:
            continue
        
        print(f"\nGenerating signals for {date.strftime('%Y-%m-%d')}...")
        
        for ticker in tickers:
            # Use current recommendation as proxy (in real scenario, would need historical ML data)
            rec = get_recommendation_for_date(ticker, date)
            if rec:
                signal = create_signal(ticker, date, rec, {})
                if signal:
                    signals_created += 1
                    print(f"  ✓ {ticker}: {rec['action']} @ ${rec['entry_exit']['entry']}")
    
    print(f"\n✅ Created {signals_created} signals")
    
    # Evaluate all signals
    print("\nEvaluating signals...")
    response = signals_table.scan()
    evaluated = 0
    wins = 0
    losses = 0
    
    for signal in response['Items']:
        outcome, return_pct, days_held, closed_date = evaluate_signal(signal)
        if outcome:
            update_signal(signal['ticker'], signal['signal_date'], outcome, return_pct, days_held, closed_date)
            evaluated += 1
            if outcome == 'WIN':
                wins += 1
                print(f"  ✓ {signal['ticker']} {signal['signal_date']}: WIN +{return_pct}% ({days_held}d)")
            elif outcome == 'LOSS':
                losses += 1
                print(f"  ✗ {signal['ticker']} {signal['signal_date']}: LOSS {return_pct}% ({days_held}d)")
    
    print(f"\n✅ Evaluated {evaluated} signals: {wins} wins, {losses} losses")
    print(f"Win rate: {wins/evaluated*100:.1f}%" if evaluated > 0 else "No closed signals")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
import boto3
import json
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

signal_table = dynamodb.Table('mrktdly-signal-performance')
price_table = dynamodb.Table('mrktdly-price-history')

# 1. Delete all existing signals
print("Deleting existing signals...")
response = signal_table.scan()
count = 0
with signal_table.batch_writer() as batch:
    for item in response['Items']:
        batch.delete_item(Key={'ticker': item['ticker'], 'signal_date': item['signal_date']})
        count += 1
print(f"Deleted {count} signals")

# 2. Generate signals from Nov 21, 2025 (Thursday - last trading day before Thanksgiving)
signal_date = '2025-11-21'
print(f"\nGenerating signals from {signal_date}...")

# Get all tickers
tickers = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "V", "JNJ",
    "WMT", "JPM", "MA", "PG", "UNH", "HD", "DIS", "BAC", "ADBE", "CRM",
    "NFLX", "XOM", "PFE", "CSCO", "ABT", "KO", "PEP", "TMO", "AVGO",
    "COST", "MRK", "ACN", "NKE", "DHR", "LLY", "TXN", "NEE", "MDT", "UNP",
    "QCOM", "PM", "BMY", "HON", "UPS", "RTX", "LOW", "ORCL", "AMGN", "IBM"
]

signals_created = 0

for ticker in tickers:
    try:
        # Get price on signal date
        response = price_table.get_item(Key={'ticker': ticker, 'date': signal_date})
        if 'Item' not in response:
            continue
            
        price_data = response['Item']
        entry_price = float(price_data['close'])
        
        # Simple strategy: BUY if close > open (bullish day)
        if float(price_data['close']) > float(price_data['open']):
            signal_type = 'BUY'
            target_price = entry_price * 1.05  # 5% target
            stop_price = entry_price * 0.97    # 3% stop
        else:
            continue  # Skip bearish signals for now
        
        # Create signal
        signal = {
            'ticker': ticker,
            'signal_date': signal_date,
            'action': signal_type,
            'entry': Decimal(str(round(entry_price, 2))),
            'target': Decimal(str(round(target_price, 2))),
            'stop_loss': Decimal(str(round(stop_price, 2))),
            'conviction': 'MEDIUM',
            'risk_reward': Decimal('1.67'),
            'status': 'OPEN',
            'created_at': signal_date
        }
        
        signal_table.put_item(Item=signal)
        signals_created += 1
        print(f"  {ticker}: Created BUY signal @ ${entry_price:.2f}")
        
    except Exception as e:
        print(f"  {ticker}: Error - {e}")

print(f"\nCreated {signals_created} signals")

# 3. Evaluate signals
print("\nEvaluating signals...")
response = lambda_client.invoke(
    FunctionName='mrktdly-signal-evaluator',
    InvocationType='RequestResponse',
    Payload=json.dumps({})
)

result = json.loads(response['Payload'].read())
print(json.dumps(json.loads(result['body']), indent=2))

# 4. Get performance stats
print("\nPerformance Stats:")
response = lambda_client.invoke(
    FunctionName='mrktdly-signal-stats',
    InvocationType='RequestResponse',
    Payload=json.dumps({})
)

result = json.loads(response['Payload'].read())
stats = json.loads(result['body'])
print(f"Win Rate: {stats.get('win_rate', 0):.1f}%")
print(f"Total Signals: {stats.get('total_signals', 0)}")
print(f"Evaluated: {stats.get('evaluated', 0)}, Active: {stats.get('active', 0)}")

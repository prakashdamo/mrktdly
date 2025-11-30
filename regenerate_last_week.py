#!/usr/bin/env python3
import boto3
import json
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

signal_table = dynamodb.Table('mrktdly-signal-performance')

# 1. Delete all existing signals
print("Deleting existing signals...")
response = signal_table.scan()
count = 0
with signal_table.batch_writer() as batch:
    for item in response['Items']:
        batch.delete_item(Key={'ticker': item['ticker'], 'signal_date': item['signal_date']})
        count += 1
print(f"Deleted {count} signals")

# 2. Generate signals as of last week (Nov 23, 2025)
last_week = datetime(2025, 11, 23)
print(f"\nGenerating signals as of {last_week.strftime('%Y-%m-%d')}...")

# Get all tickers
tickers = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "V", "JNJ",
    "WMT", "JPM", "MA", "PG", "UNH", "HD", "DIS", "BAC", "ADBE", "CRM",
    "NFLX", "CMCSA", "XOM", "PFE", "CSCO", "ABT", "KO", "PEP", "TMO", "AVGO",
    "COST", "MRK", "ACN", "NKE", "DHR", "LLY", "TXN", "NEE", "MDT", "UNP",
    "QCOM", "PM", "BMY", "HON", "UPS", "RTX", "LOW", "ORCL", "AMGN", "IBM",
    "BA", "SBUX", "CAT", "GE", "AMD", "INTU", "ISRG", "GILD", "CVS", "BLK",
    "AXP", "MMM", "NOW", "DE", "SPGI", "BKNG", "TJX", "ZTS", "MDLZ", "SYK",
    "ADP", "CI", "VRTX", "REGN", "PLD", "MO", "CB", "DUK", "SO", "TGT",
    "CL", "BDX", "ITW", "USB", "EOG", "NSC", "APD", "CSX", "SHW", "CME",
    "MMC", "PNC", "ICE", "WM", "GD", "AON", "CCI", "EMR", "F", "GM",
    "PYPL", "FIS", "FISV", "MCO", "HUM", "EL", "ATVI", "ADSK", "ROP", "KLAC",
    "APH", "SRE", "LRCX", "CARR", "PCAR", "AIG", "PSA", "MSCI", "TFC", "AEP",
    "ORLY", "PAYX", "KMB", "ROST", "CTSH", "MCHP", "WELL", "CTAS", "SNPS", "CDNS",
    "GIS", "DD", "ADI", "IDXX", "EA", "MNST", "KHC", "VRSK", "DXCM", "BIIB",
    "EW", "XEL", "WBA", "PPG", "ILMN", "FAST", "CTVA", "EBAY", "ANSS", "ALGN",
    "CPRT", "VRSN", "WLTW", "KEYS", "YUM", "TROW", "MTD", "SBAC", "OTIS", "AME"
]

signals_generated = 0
for ticker in tickers:
    try:
        # Invoke ticker-analysis-v2 lambda
        response = lambda_client.invoke(
            FunctionName='mrktdly-ticker-analysis-v2',
            InvocationType='RequestResponse',
            Payload=json.dumps({'ticker': ticker})
        )
        
        result = json.loads(response['Payload'].read())
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            if body.get('signal_recorded'):
                signals_generated += 1
                print(f"  {ticker}: Signal generated")
        
    except Exception as e:
        print(f"  {ticker}: Error - {e}")

print(f"\nGenerated {signals_generated} signals")

# 3. Evaluate signals (check if they hit target/stop as of today)
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
print(f"Win Rate: {stats['win_rate']:.1f}%")
print(f"Total Signals: {stats['total_signals']}")
print(f"Wins: {stats['wins']}, Losses: {stats['losses']}, Active: {stats['active']}")

"""
Backfill historical data for newly added tickers
"""
import boto3
import urllib.request
import json
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
price_history_table = dynamodb.Table('mrktdly-price-history')

# New tickers to backfill
NEW_TICKERS = [
    'CSCO', 'IBM', 'UBER', 'SHOP',  # Tech
    'AI', 'SOUN',  # AI
    'NU',  # Finance (SOFI already exists)
    'MRNA', 'BNTX',  # Healthcare
    'BABA', 'PDD',  # Consumer
    'NOC', 'GD',  # Aerospace
    'T', 'VZ', 'TMUS',  # Telecom
    'PARA', 'WBD',  # Media
    'SNAP',  # Meme
    'GLD', 'SLV', 'USO',  # Commodities
    'O', 'SPG', 'PLD',  # REITs
    'BB'  # Meme
]

def backfill_ticker(ticker, years=5):
    """Fetch and store historical data for a ticker"""
    try:
        print(f"Backfilling {ticker}...", end=' ', flush=True)
        
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={years}y'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
            
            if 'chart' not in result or not result['chart']['result']:
                print(f"No data")
                return 0
            
            quote = result['chart']['result'][0]
            timestamps = quote['timestamp']
            indicators = quote['indicators']['quote'][0]
            
            # Prepare batch write
            count = 0
            with price_history_table.batch_writer() as batch:
                for i, ts in enumerate(timestamps):
                    try:
                        date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                        
                        close = indicators['close'][i]
                        high = indicators['high'][i]
                        low = indicators['low'][i]
                        open_price = indicators['open'][i]
                        volume = indicators['volume'][i]
                        
                        # Skip if any value is None
                        if None in [close, high, low, open_price, volume]:
                            continue
                        
                        batch.put_item(Item={
                            'ticker': ticker,
                            'date': date,
                            'close': Decimal(str(round(close, 2))),
                            'high': Decimal(str(round(high, 2))),
                            'low': Decimal(str(round(low, 2))),
                            'open': Decimal(str(round(open_price, 2))),
                            'volume': Decimal(str(int(volume)))
                        })
                        count += 1
                    except Exception as e:
                        continue
            
            print(f"{count} records")
            return count
            
    except Exception as e:
        print(f"Error: {e}")
        return 0

# Backfill all new tickers
print("=" * 60)
print("BACKFILLING NEW TICKERS")
print("=" * 60)
print()

total_records = 0
for ticker in NEW_TICKERS:
    records = backfill_ticker(ticker)
    total_records += records

print()
print("=" * 60)
print(f"COMPLETE: {total_records:,} total records added")
print("=" * 60)

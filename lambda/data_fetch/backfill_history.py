"""
Backfill historical price data for all tickers
Run once to populate 5 years of historical data
"""
import json
import boto3
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
import time

dynamodb = boto3.resource('dynamodb')
price_history_table = dynamodb.Table('mrktdly-price-history')

# All tickers we track
TICKERS = [
    # Indices
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO',
    # Mega tech
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'AVGO', 'ORCL', 'ADBE', 'CRM', 'NFLX', 'AMD', 'INTC',
    # Semiconductors
    'TSM', 'ASML', 'QCOM', 'TXN', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'ARM', 'MCHP', 'ON',
    # AI/Cloud
    'PLTR', 'SNOW', 'DDOG', 'NET', 'CRWD', 'ZS', 'PANW', 'WDAY', 'NOW', 'TEAM', 'MDB', 'HUBS',
    # Financials
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'PYPL', 'SQ', 'COIN', 'HOOD',
    # Healthcare
    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'BMY', 'AMGN', 'GILD', 'VRTX', 'REGN',
    # Consumer
    'WMT', 'COST', 'HD', 'TGT', 'LOW', 'NKE', 'SBUX', 'MCD', 'DIS', 'BKNG', 'ABNB',
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL',
    # Industrials
    'BA', 'CAT', 'GE', 'RTX', 'LMT', 'HON', 'UPS', 'UNP', 'DE', 'MMM',
    # EV/Auto
    'F', 'GM', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI',
    # Crypto
    'MSTR', 'RIOT', 'MARA', 'CLSK',
    # Meme
    'GME', 'AMC',
    # Small caps
    'RKLB', 'IONQ', 'SMCI', 'APP', 'CVNA', 'UPST', 'SOFI', 'AFRM'
]

def backfill_ticker(ticker, years=5):
    """Fetch and store historical data for a ticker"""
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={years}y'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read())
            quote = result['chart']['result'][0]
            
            timestamps = quote['timestamp']
            indicators = quote['indicators']['quote'][0]
            
            opens = indicators.get('open', [])
            highs = indicators.get('high', [])
            lows = indicators.get('low', [])
            closes = indicators.get('close', [])
            volumes = indicators.get('volume', [])
            
            stored = 0
            for i in range(len(timestamps)):
                # Skip if any value is None
                if not all([opens[i], highs[i], lows[i], closes[i], volumes[i]]):
                    continue
                
                date = datetime.fromtimestamp(timestamps[i], tz=timezone.utc).strftime('%Y-%m-%d')
                
                try:
                    price_history_table.put_item(Item={
                        'ticker': ticker,
                        'date': date,
                        'open': Decimal(str(round(opens[i], 2))),
                        'high': Decimal(str(round(highs[i], 2))),
                        'low': Decimal(str(round(lows[i], 2))),
                        'close': Decimal(str(round(closes[i], 2))),
                        'volume': int(volumes[i]),
                        'adj_close': Decimal(str(round(closes[i], 2))),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    stored += 1
                except Exception as e:
                    print(f'  Error storing {ticker} {date}: {e}')
            
            print(f'✓ {ticker}: Stored {stored} days')
            return stored
            
    except Exception as e:
        print(f'✗ {ticker}: Error - {e}')
        return 0

def main():
    """Backfill all tickers"""
    print(f'Starting backfill for {len(TICKERS)} tickers...')
    print(f'This will take ~{len(TICKERS) * 2} seconds (rate limiting)')
    print('')
    
    total_stored = 0
    for i, ticker in enumerate(TICKERS, 1):
        print(f'[{i}/{len(TICKERS)}] Processing {ticker}...')
        stored = backfill_ticker(ticker)
        total_stored += stored
        
        # Rate limiting: 2 seconds between requests
        if i < len(TICKERS):
            time.sleep(2)
    
    print('')
    print(f'✅ Backfill complete!')
    print(f'Total records stored: {total_stored:,}')
    print(f'Average per ticker: {total_stored // len(TICKERS)} days')

if __name__ == '__main__':
    main()

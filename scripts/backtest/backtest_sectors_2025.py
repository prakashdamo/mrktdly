import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def get_prices(ticker, start_date, end_date):
    response = table.query(
        KeyConditionExpression='ticker = :ticker AND #d BETWEEN :start AND :end',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={':ticker': ticker, ':start': start_date, ':end': end_date}
    )
    return sorted(response['Items'], key=lambda x: x['date'])

def calculate_indicators(prices):
    closes = [float(p['close']) for p in prices]
    
    sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
    sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else closes[-1]
    
    if len(closes) >= 14:
        gains = [max(closes[i] - closes[i-1], 0) for i in range(-14, 0)]
        losses = [max(closes[i-1] - closes[i], 0) for i in range(-14, 0)]
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
    else:
        rsi = 50
    
    return {'sma20': sma20, 'sma50': sma50, 'rsi': rsi, 'price': closes[-1]}

def backtest_strategy(ticker, strategy, start_date, end_date, initial_capital=10000):
    prices = get_prices(ticker, start_date, end_date)
    if len(prices) < 60:
        return None
    
    cash = initial_capital
    shares = 0
    trades = 0
    
    for i in range(60, len(prices)):
        hist = prices[:i+1]
        ind = calculate_indicators(hist)
        price = float(prices[i]['close'])
        
        if strategy == 'buy_hold':
            if shares == 0:
                shares = cash / price
                cash = 0
                trades += 1
        
        elif strategy == 'ma_crossover':
            if ind['sma20'] > ind['sma50'] and shares == 0:
                shares = cash / price
                cash = 0
                trades += 1
            elif ind['sma20'] < ind['sma50'] and shares > 0:
                cash = shares * price
                shares = 0
                trades += 1
        
        elif strategy == 'rsi':
            if ind['rsi'] < 30 and shares == 0:
                shares = cash / price
                cash = 0
                trades += 1
            elif ind['rsi'] > 70 and shares > 0:
                cash = shares * price
                shares = 0
                trades += 1
    
    final_price = float(prices[-1]['close'])
    final_value = cash + (shares * final_price)
    roi = ((final_value - initial_capital) / initial_capital) * 100
    
    return {'final_value': final_value, 'roi': roi, 'trades': trades}

sectors = {
    'XLK': 'Technology',
    'XLV': 'Healthcare', 
    'XLF': 'Financials',
    'XLE': 'Energy'
}

strategies = ['buy_hold', 'ma_crossover', 'rsi']

print("=" * 80)
print("SECTOR ETF BACKTEST - 2025")
print("=" * 80)
print(f"Period: 2025-01-01 to 2025-11-30")
print(f"Starting Capital: $10,000")
print("=" * 80)

for ticker, sector in sectors.items():
    print(f"\n{ticker} - {sector}")
    print("-" * 60)
    
    best_roi = -999
    best_strategy = None
    
    for strategy in strategies:
        result = backtest_strategy(ticker, strategy, '2025-01-01', '2025-12-02')
        if result:
            print(f"  {strategy:15s}: ${result['final_value']:,.2f} ({result['roi']:+.2f}%) - {result['trades']} trades")
            if result['roi'] > best_roi:
                best_roi = result['roi']
                best_strategy = strategy
    
    print(f"  → Best: {best_strategy} ({best_roi:+.2f}%)")

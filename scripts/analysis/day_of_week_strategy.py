import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def get_prices(ticker, start_date, end_date):
    response = table.query(
        KeyConditionExpression='ticker = :ticker AND #d BETWEEN :start AND :end',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={':ticker': ticker, ':start': start_date, ':end': end_date}
    )
    return sorted(response['Items'], key=lambda x: x['date'])

def backtest_day_strategy(ticker, buy_day, sell_day, start_date, end_date, initial_capital=10000):
    prices = get_prices(ticker, start_date, end_date)
    
    cash = initial_capital
    shares = 0
    trades = 0
    
    for i in range(len(prices)):
        date = datetime.strptime(prices[i]['date'], '%Y-%m-%d')
        day_name = date.strftime('%A')
        price = float(prices[i]['close'])
        
        if day_name == buy_day and shares == 0 and cash > 0:
            shares = cash / price
            cash = 0
            trades += 1
        elif day_name == sell_day and shares > 0:
            cash = shares * price
            shares = 0
            trades += 1
    
    final_price = float(prices[-1]['close'])
    final_value = cash + (shares * final_price)
    roi = ((final_value - initial_capital) / initial_capital) * 100
    
    return {'final_value': final_value, 'roi': roi, 'trades': trades}

tickers = ['SPY', 'QQQ', 'PLTR']
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

print("=" * 100)
print("DAY-OF-WEEK TRADING STRATEGIES - 2025")
print("=" * 100)
print(f"Period: 2025-01-01 to 2025-12-02")
print(f"Starting Capital: $10,000")
print("=" * 100)

# Strategy 1: Buy on X, sell on Friday
print("\n" + "=" * 100)
print("STRATEGY 1: Buy on specific day, sell on Friday")
print("=" * 100)

for ticker in tickers:
    print(f"\n{ticker}")
    print("-" * 100)
    print(f"{'Buy Day':<12} {'Final Value':>12} {'ROI':>8} {'Trades':>8}")
    print("-" * 100)
    
    for buy_day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday']:
        result = backtest_day_strategy(ticker, buy_day, 'Friday', '2025-01-01', '2025-12-02')
        print(f"{buy_day:<12} ${result['final_value']:>11,.0f} {result['roi']:>7.1f}% {result['trades']:>8}")

# Strategy 2: Buy on Monday, sell on X
print("\n" + "=" * 100)
print("STRATEGY 2: Buy on Monday, sell on specific day")
print("=" * 100)

for ticker in tickers:
    print(f"\n{ticker}")
    print("-" * 100)
    print(f"{'Sell Day':<12} {'Final Value':>12} {'ROI':>8} {'Trades':>8}")
    print("-" * 100)
    
    for sell_day in ['Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        result = backtest_day_strategy(ticker, 'Monday', sell_day, '2025-01-01', '2025-12-02')
        print(f"{sell_day:<12} ${result['final_value']:>11,.0f} {result['roi']:>7.1f}% {result['trades']:>8}")

# Strategy 3: Best combination
print("\n" + "=" * 100)
print("STRATEGY 3: All combinations (finding the best)")
print("=" * 100)

for ticker in tickers:
    print(f"\n{ticker}")
    print("-" * 100)
    
    best_roi = -999
    best_combo = None
    
    for buy_day in days:
        for sell_day in days:
            if buy_day == sell_day:
                continue
            result = backtest_day_strategy(ticker, buy_day, sell_day, '2025-01-01', '2025-12-02')
            if result['roi'] > best_roi:
                best_roi = result['roi']
                best_combo = (buy_day, sell_day, result)
    
    print(f"Best: Buy {best_combo[0]}, Sell {best_combo[1]}")
    print(f"Final Value: ${best_combo[2]['final_value']:,.0f}")
    print(f"ROI: {best_combo[2]['roi']:+.1f}%")
    print(f"Trades: {best_combo[2]['trades']}")

# Compare to buy & hold
print("\n" + "=" * 100)
print("COMPARISON TO BUY & HOLD")
print("=" * 100)

for ticker in tickers:
    prices = get_prices(ticker, '2025-01-01', '2025-12-02')
    first_price = float(prices[0]['open'])
    last_price = float(prices[-1]['close'])
    bh_roi = ((last_price - first_price) / first_price) * 100
    
    print(f"\n{ticker} Buy & Hold: {bh_roi:+.1f}%")

import boto3

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
    
    return {'sma20': sma20, 'sma50': sma50, 'rsi': rsi}

def backtest_with_costs(ticker, strategy, start_date, end_date, cost_per_trade=0, initial_capital=10000):
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
                cash -= cost_per_trade
                shares = cash / price
                cash = 0
                trades += 1
        elif strategy == 'ma_crossover':
            if ind['sma20'] > ind['sma50'] and shares == 0:
                cash -= cost_per_trade
                shares = cash / price
                cash = 0
                trades += 1
            elif ind['sma20'] < ind['sma50'] and shares > 0:
                cash = shares * price - cost_per_trade
                shares = 0
                trades += 1
        elif strategy == 'rsi':
            if ind['rsi'] < 30 and shares == 0:
                cash -= cost_per_trade
                shares = cash / price
                cash = 0
                trades += 1
            elif ind['rsi'] > 70 and shares > 0:
                cash = shares * price - cost_per_trade
                shares = 0
                trades += 1
    
    final_value = cash + (shares * float(prices[-1]['close']))
    roi = ((final_value - initial_capital) / initial_capital) * 100
    
    return {'final_value': final_value, 'roi': roi, 'trades': trades}

tickers = ['PLTR', 'TSLA', 'SPY']
strategies = ['buy_hold', 'ma_crossover', 'rsi']
costs = [0, 5, 10]

print("=" * 100)
print("TRANSACTION COST IMPACT ANALYSIS - 2025")
print("=" * 100)
print(f"Period: 2025-01-01 to 2025-11-30")
print(f"Starting Capital: $10,000")
print("=" * 100)

for ticker in tickers:
    print(f"\n{ticker}")
    print("-" * 100)
    
    for strategy in strategies:
        print(f"\n  {strategy.upper()}")
        print(f"  {'Cost/Trade':<12} {'Final Value':>12} {'ROI':>8} {'Trades':>7} {'Cost Impact':>12}")
        print(f"  {'-'*60}")
        
        baseline_roi = None
        for cost in costs:
            result = backtest_with_costs(ticker, strategy, '2025-01-01', '2025-12-02', cost)
            if result:
                if baseline_roi is None:
                    baseline_roi = result['roi']
                    impact = 0
                else:
                    impact = result['roi'] - baseline_roi
                
                print(f"  ${cost:<11} ${result['final_value']:>11,.2f} {result['roi']:>7.2f}% "
                      f"{result['trades']:>7} {impact:>11.2f}%")

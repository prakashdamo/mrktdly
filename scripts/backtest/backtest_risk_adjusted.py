import boto3
from datetime import datetime
import math

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

def backtest_with_metrics(ticker, strategy, start_date, end_date, initial_capital=10000):
    prices = get_prices(ticker, start_date, end_date)
    if len(prices) < 60:
        return None
    
    cash = initial_capital
    shares = 0
    trades = 0
    portfolio_values = []
    peak = initial_capital
    max_drawdown = 0
    
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
        
        value = cash + (shares * price)
        portfolio_values.append(value)
        
        if value > peak:
            peak = value
        drawdown = ((peak - value) / peak) * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    final_value = portfolio_values[-1]
    roi = ((final_value - initial_capital) / initial_capital) * 100
    
    # Calculate Sharpe Ratio
    returns = [(portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1] 
               for i in range(1, len(portfolio_values))]
    avg_return = sum(returns) / len(returns) if returns else 0
    std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns)) if returns else 0
    sharpe = (avg_return / std_return * math.sqrt(252)) if std_return > 0 else 0
    
    return {
        'final_value': final_value,
        'roi': roi,
        'trades': trades,
        'max_drawdown': max_drawdown,
        'sharpe': sharpe
    }

tickers = ['PLTR', 'GOOGL', 'TSLA', 'HIMS', 'SPY']
strategies = ['buy_hold', 'ma_crossover', 'rsi']

print("=" * 90)
print("RISK-ADJUSTED RETURNS ANALYSIS - 2025")
print("=" * 90)
print(f"Period: 2025-01-01 to 2025-11-30")
print(f"Starting Capital: $10,000")
print("=" * 90)

for ticker in tickers:
    print(f"\n{ticker}")
    print("-" * 90)
    print(f"{'Strategy':<15} {'Final Value':>12} {'ROI':>8} {'Trades':>7} {'Max DD':>8} {'Sharpe':>8}")
    print("-" * 90)
    
    for strategy in strategies:
        result = backtest_with_metrics(ticker, strategy, '2025-01-01', '2025-12-02')
        if result:
            print(f"{strategy:<15} ${result['final_value']:>11,.2f} {result['roi']:>7.2f}% "
                  f"{result['trades']:>7} {result['max_drawdown']:>7.2f}% {result['sharpe']:>8.2f}")

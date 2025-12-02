#!/usr/bin/env python3
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def get_pltr_data():
    """Fetch PLTR data for 2025"""
    response = table.query(
        KeyConditionExpression='ticker = :ticker AND #d BETWEEN :start AND :end',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={
            ':ticker': 'PLTR',
            ':start': '2025-01-01',
            ':end': '2025-12-02'
        }
    )
    
    data = []
    for item in response['Items']:
        data.append({
            'date': item['date'],
            'open': float(item['open']),
            'high': float(item['high']),
            'low': float(item['low']),
            'close': float(item['close']),
            'volume': int(item['volume'])
        })
    
    return sorted(data, key=lambda x: x['date'])

def calculate_indicators(data):
    """Calculate technical indicators"""
    for i in range(len(data)):
        # RSI (14-day)
        if i >= 14:
            gains = sum([max(data[j]['close'] - data[j-1]['close'], 0) for j in range(i-13, i+1)])
            losses = sum([max(data[j-1]['close'] - data[j]['close'], 0) for j in range(i-13, i+1)])
            rs = gains / losses if losses > 0 else 100
            data[i]['rsi'] = 100 - (100 / (1 + rs))
        
        # Moving averages
        if i >= 9:
            data[i]['sma10'] = sum([data[j]['close'] for j in range(i-9, i+1)]) / 10
        if i >= 19:
            data[i]['sma20'] = sum([data[j]['close'] for j in range(i-19, i+1)]) / 20
        if i >= 49:
            data[i]['sma50'] = sum([data[j]['close'] for j in range(i-49, i+1)]) / 50
    
    return data

def backtest_buy_hold(data, capital):
    """Buy and hold strategy"""
    shares = capital / data[0]['open']
    final_value = shares * data[-1]['close']
    return final_value, [(data[0]['date'], 'BUY', data[0]['open'], shares)]

def backtest_swing_trading(data, capital):
    """Swing trading: Buy dips, sell rallies"""
    cash = capital
    shares = 0
    trades = []
    
    for i in range(1, len(data)):
        price = data[i]['close']
        prev_price = data[i-1]['close']
        
        # Buy on 5%+ dip
        if shares == 0 and price < prev_price * 0.95:
            shares = cash / price
            cash = 0
            trades.append((data[i]['date'], 'BUY', price, shares))
        
        # Sell on 10%+ gain
        elif shares > 0:
            buy_price = trades[-1][2]
            if price >= buy_price * 1.10:
                cash = shares * price
                trades.append((data[i]['date'], 'SELL', price, shares))
                shares = 0
    
    final_value = cash + (shares * data[-1]['close'])
    return final_value, trades

def backtest_rsi_strategy(data, capital):
    """RSI-based strategy: Buy oversold, sell overbought"""
    cash = capital
    shares = 0
    trades = []
    
    for i in range(len(data)):
        if 'rsi' not in data[i]:
            continue
        
        price = data[i]['close']
        rsi = data[i]['rsi']
        
        # Buy when RSI < 30 (oversold)
        if shares == 0 and rsi < 30:
            shares = cash / price
            cash = 0
            trades.append((data[i]['date'], 'BUY', price, shares))
        
        # Sell when RSI > 70 (overbought)
        elif shares > 0 and rsi > 70:
            cash = shares * price
            trades.append((data[i]['date'], 'SELL', price, shares))
            shares = 0
    
    final_value = cash + (shares * data[-1]['close'])
    return final_value, trades

def backtest_ma_crossover(data, capital):
    """Moving average crossover strategy"""
    cash = capital
    shares = 0
    trades = []
    
    for i in range(1, len(data)):
        if 'sma10' not in data[i] or 'sma50' not in data[i]:
            continue
        
        price = data[i]['close']
        sma10_curr = data[i]['sma10']
        sma50_curr = data[i]['sma50']
        sma10_prev = data[i-1].get('sma10', 0)
        sma50_prev = data[i-1].get('sma50', 0)
        
        # Golden cross: Buy when SMA10 crosses above SMA50
        if shares == 0 and sma10_prev <= sma50_prev and sma10_curr > sma50_curr:
            shares = cash / price
            cash = 0
            trades.append((data[i]['date'], 'BUY', price, shares))
        
        # Death cross: Sell when SMA10 crosses below SMA50
        elif shares > 0 and sma10_prev >= sma50_prev and sma10_curr < sma50_curr:
            cash = shares * price
            trades.append((data[i]['date'], 'SELL', price, shares))
            shares = 0
    
    final_value = cash + (shares * data[-1]['close'])
    return final_value, trades

def backtest_momentum(data, capital):
    """Momentum strategy: Buy strong uptrends"""
    cash = capital
    shares = 0
    trades = []
    
    for i in range(20, len(data)):
        price = data[i]['close']
        
        # Calculate 20-day momentum
        momentum = (price - data[i-20]['close']) / data[i-20]['close']
        
        # Buy on strong momentum (>5%)
        if shares == 0 and momentum > 0.05:
            shares = cash / price
            cash = 0
            trades.append((data[i]['date'], 'BUY', price, shares))
        
        # Sell on negative momentum
        elif shares > 0 and momentum < -0.02:
            cash = shares * price
            trades.append((data[i]['date'], 'SELL', price, shares))
            shares = 0
    
    final_value = cash + (shares * data[-1]['close'])
    return final_value, trades

def main():
    print("=" * 80)
    print("PLTR BACKTEST - 2025 (Jan 1 - Dec 2)")
    print("Starting Capital: $10,000")
    print("=" * 80)
    
    data = get_pltr_data()
    print(f"\nData points: {len(data)}")
    print(f"Start date: {data[0]['date']} - Price: ${data[0]['close']:.2f}")
    print(f"End date: {data[-1]['date']} - Price: ${data[-1]['close']:.2f}")
    print(f"Price change: {((data[-1]['close'] - data[0]['close']) / data[0]['close'] * 100):.2f}%")
    
    data = calculate_indicators(data)
    
    strategies = [
        ("Buy & Hold", backtest_buy_hold),
        ("Swing Trading (5% dip, 10% gain)", backtest_swing_trading),
        ("RSI Strategy (30/70)", backtest_rsi_strategy),
        ("MA Crossover (10/50)", backtest_ma_crossover),
        ("Momentum (20-day)", backtest_momentum)
    ]
    
    results = []
    
    print("\n" + "=" * 80)
    print("STRATEGY RESULTS")
    print("=" * 80)
    
    for name, strategy_func in strategies:
        final_value, trades = strategy_func(data, 10000)
        profit = final_value - 10000
        roi = (profit / 10000) * 100
        
        results.append({
            'name': name,
            'final_value': final_value,
            'profit': profit,
            'roi': roi,
            'trades': trades
        })
        
        print(f"\n{name}:")
        print(f"  Final Value: ${final_value:,.2f}")
        print(f"  Profit: ${profit:,.2f}")
        print(f"  ROI: {roi:.2f}%")
        print(f"  Number of trades: {len([t for t in trades if t[1] == 'BUY'])}")
    
    # Find best strategy
    best = max(results, key=lambda x: x['final_value'])
    
    print("\n" + "=" * 80)
    print("BEST STRATEGY")
    print("=" * 80)
    print(f"\n{best['name']}")
    print(f"Final Value: ${best['final_value']:,.2f}")
    print(f"Profit: ${best['profit']:,.2f}")
    print(f"ROI: {best['roi']:.2f}%")
    
    print("\nTrade History:")
    for trade in best['trades']:
        date, action, price, shares = trade
        print(f"  {date}: {action} {shares:.2f} shares @ ${price:.2f} = ${shares * price:,.2f}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()

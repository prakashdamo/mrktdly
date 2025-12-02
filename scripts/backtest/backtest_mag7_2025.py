#!/usr/bin/env python3
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def get_stock_data(ticker):
    """Fetch stock data for 2025"""
    response = table.query(
        KeyConditionExpression='ticker = :ticker AND #d BETWEEN :start AND :end',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={
            ':ticker': ticker,
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
        if i >= 14:
            gains = sum([max(data[j]['close'] - data[j-1]['close'], 0) for j in range(i-13, i+1)])
            losses = sum([max(data[j-1]['close'] - data[j]['close'], 0) for j in range(i-13, i+1)])
            rs = gains / losses if losses > 0 else 100
            data[i]['rsi'] = 100 - (100 / (1 + rs))
        
        if i >= 9:
            data[i]['sma10'] = sum([data[j]['close'] for j in range(i-9, i+1)]) / 10
        if i >= 49:
            data[i]['sma50'] = sum([data[j]['close'] for j in range(i-49, i+1)]) / 50
    
    return data

def backtest_buy_hold(data, capital):
    shares = capital / data[0]['open']
    final_value = shares * data[-1]['close']
    return final_value, 1

def backtest_swing_trading(data, capital):
    cash = capital
    shares = 0
    trades = 0
    
    for i in range(1, len(data)):
        price = data[i]['close']
        prev_price = data[i-1]['close']
        
        if shares == 0 and price < prev_price * 0.95:
            shares = cash / price
            cash = 0
            trades += 1
        elif shares > 0:
            buy_price = [data[j]['close'] for j in range(i) if data[j].get('bought')][-1] if any(data[j].get('bought') for j in range(i)) else data[0]['close']
            if price >= buy_price * 1.10:
                cash = shares * price
                shares = 0
    
    final_value = cash + (shares * data[-1]['close'])
    return final_value, trades

def backtest_rsi_strategy(data, capital):
    cash = capital
    shares = 0
    trades = 0
    
    for i in range(len(data)):
        if 'rsi' not in data[i]:
            continue
        
        price = data[i]['close']
        rsi = data[i]['rsi']
        
        if shares == 0 and rsi < 30:
            shares = cash / price
            cash = 0
            trades += 1
        elif shares > 0 and rsi > 70:
            cash = shares * price
            shares = 0
    
    final_value = cash + (shares * data[-1]['close'])
    return final_value, trades

def backtest_ma_crossover(data, capital):
    cash = capital
    shares = 0
    trades = 0
    
    for i in range(1, len(data)):
        if 'sma10' not in data[i] or 'sma50' not in data[i]:
            continue
        
        price = data[i]['close']
        sma10_curr = data[i]['sma10']
        sma50_curr = data[i]['sma50']
        sma10_prev = data[i-1].get('sma10', 0)
        sma50_prev = data[i-1].get('sma50', 0)
        
        if shares == 0 and sma10_prev <= sma50_prev and sma10_curr > sma50_curr:
            shares = cash / price
            cash = 0
            trades += 1
        elif shares > 0 and sma10_prev >= sma50_prev and sma10_curr < sma50_curr:
            cash = shares * price
            shares = 0
    
    final_value = cash + (shares * data[-1]['close'])
    return final_value, trades

def backtest_momentum(data, capital):
    cash = capital
    shares = 0
    trades = 0
    
    for i in range(20, len(data)):
        price = data[i]['close']
        momentum = (price - data[i-20]['close']) / data[i-20]['close']
        
        if shares == 0 and momentum > 0.05:
            shares = cash / price
            cash = 0
            trades += 1
        elif shares > 0 and momentum < -0.02:
            cash = shares * price
            shares = 0
    
    final_value = cash + (shares * data[-1]['close'])
    return final_value, trades

def main():
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
    strategies = [
        ("Buy & Hold", backtest_buy_hold),
        ("Swing Trading", backtest_swing_trading),
        ("RSI Strategy", backtest_rsi_strategy),
        ("MA Crossover", backtest_ma_crossover),
        ("Momentum", backtest_momentum)
    ]
    
    print("=" * 100)
    print("MAGNIFICENT 7 BACKTEST - 2025 (Jan 1 - Dec 2)")
    print("Starting Capital: $10,000 per stock")
    print("=" * 100)
    
    all_results = []
    
    for ticker in tickers:
        print(f"\n{'='*100}")
        print(f"{ticker}")
        print('='*100)
        
        try:
            data = get_stock_data(ticker)
            if len(data) < 50:
                print(f"Insufficient data for {ticker}")
                continue
            
            start_price = data[0]['close']
            end_price = data[-1]['close']
            price_change = ((end_price - start_price) / start_price) * 100
            
            print(f"Start: ${start_price:.2f} | End: ${end_price:.2f} | Change: {price_change:+.2f}%")
            
            data = calculate_indicators(data)
            
            results = []
            for name, strategy_func in strategies:
                final_value, trades = strategy_func(data, 10000)
                profit = final_value - 10000
                roi = (profit / 10000) * 100
                results.append({
                    'strategy': name,
                    'final': final_value,
                    'profit': profit,
                    'roi': roi,
                    'trades': trades
                })
            
            best = max(results, key=lambda x: x['final'])
            
            for r in results:
                marker = "🏆" if r == best else "  "
                print(f"{marker} {r['strategy']:20s} | ${r['final']:>10,.0f} | {r['roi']:>+7.2f}% | {r['trades']:>2d} trades")
            
            all_results.append({
                'ticker': ticker,
                'price_change': price_change,
                'best_strategy': best['strategy'],
                'best_roi': best['roi'],
                'best_profit': best['profit']
            })
            
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
    
    print("\n" + "=" * 100)
    print("SUMMARY - BEST STRATEGY PER STOCK")
    print("=" * 100)
    print(f"{'Ticker':<8} {'Price Change':>12} {'Best Strategy':<20} {'ROI':>10} {'Profit':>12}")
    print("-" * 100)
    
    for r in sorted(all_results, key=lambda x: x['best_roi'], reverse=True):
        print(f"{r['ticker']:<8} {r['price_change']:>+11.2f}% {r['best_strategy']:<20} {r['best_roi']:>+9.2f}% ${r['best_profit']:>10,.0f}")
    
    total_profit = sum([r['best_profit'] for r in all_results])
    avg_roi = sum([r['best_roi'] for r in all_results]) / len(all_results)
    
    print("-" * 100)
    print(f"{'TOTAL':<8} {'':>12} {'':>20} {avg_roi:>+9.2f}% ${total_profit:>10,.0f}")
    print("\n" + "=" * 100)

if __name__ == '__main__':
    main()

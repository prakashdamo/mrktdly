#!/usr/bin/env python3
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def get_stock_data(ticker):
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
            'close': float(item['close'])
        })
    
    return sorted(data, key=lambda x: x['date'])

def calculate_indicators(data):
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

def backtest_strategy(data, capital, strategy):
    if strategy == 'buy_hold':
        shares = capital / data[0]['close']
        return shares * data[-1]['close']
    
    elif strategy == 'swing':
        cash = capital
        shares = 0
        for i in range(1, len(data)):
            price = data[i]['close']
            prev_price = data[i-1]['close']
            if shares == 0 and price < prev_price * 0.95:
                shares = cash / price
                cash = 0
                buy_price = price
            elif shares > 0 and price >= buy_price * 1.10:
                cash = shares * price
                shares = 0
        return cash + (shares * data[-1]['close'])
    
    elif strategy == 'ma_crossover':
        cash = capital
        shares = 0
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
            elif shares > 0 and sma10_prev >= sma50_prev and sma10_curr < sma50_curr:
                cash = shares * price
                shares = 0
        return cash + (shares * data[-1]['close'])
    
    elif strategy == 'momentum':
        cash = capital
        shares = 0
        for i in range(20, len(data)):
            price = data[i]['close']
            momentum = (price - data[i-20]['close']) / data[i-20]['close']
            
            if shares == 0 and momentum > 0.05:
                shares = cash / price
                cash = 0
            elif shares > 0 and momentum < -0.02:
                cash = shares * price
                shares = 0
        return cash + (shares * data[-1]['close'])

def main():
    # Test stocks from our previous analysis
    stocks = {
        'PLTR': 'buy_hold',
        'HIMS': 'buy_hold', 
        'BB': 'momentum',
        'AAPL': 'swing',
        'MSFT': 'momentum',
        'GOOGL': 'ma_crossover',
        'AMZN': 'swing',
        'NVDA': 'ma_crossover',
        'META': 'ma_crossover',
        'TSLA': 'swing'
    }
    
    print("=" * 100)
    print("OPTIMAL PORTFOLIO ANALYSIS - 2025")
    print("Finding best allocation of $10,000")
    print("=" * 100)
    
    # Calculate returns for each stock with optimal strategy
    results = []
    for ticker, strategy in stocks.items():
        try:
            data = get_stock_data(ticker)
            if len(data) < 50:
                continue
            
            data = calculate_indicators(data)
            final_value = backtest_strategy(data, 10000, strategy)
            roi = ((final_value - 10000) / 10000) * 100
            
            results.append({
                'ticker': ticker,
                'strategy': strategy,
                'roi': roi,
                'final_value': final_value,
                'profit': final_value - 10000
            })
        except Exception as e:
            print(f"Error with {ticker}: {e}")
    
    results.sort(key=lambda x: x['roi'], reverse=True)
    
    print("\n" + "=" * 100)
    print("INDIVIDUAL STOCK PERFORMANCE (with optimal strategy)")
    print("=" * 100)
    print(f"{'Rank':<6} {'Ticker':<8} {'Strategy':<15} {'ROI':>10} {'Profit':>12} {'Final Value':>14}")
    print("-" * 100)
    
    for i, r in enumerate(results, 1):
        print(f"{i:<6} {r['ticker']:<8} {r['strategy']:<15} {r['roi']:>+9.2f}% ${r['profit']:>10,.0f} ${r['final_value']:>12,.0f}")
    
    # Portfolio scenarios
    print("\n" + "=" * 100)
    print("PORTFOLIO SCENARIOS ($10,000 STARTING CAPITAL)")
    print("=" * 100)
    
    scenarios = [
        ("Top 1 Stock (All-in)", results[:1]),
        ("Top 3 Stocks (Equal Weight)", results[:3]),
        ("Top 5 Stocks (Equal Weight)", results[:5]),
        ("All 10 Stocks (Equal Weight)", results[:10]),
        ("Mag7 Only (Equal Weight)", [r for r in results if r['ticker'] in ['AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA']])
    ]
    
    best_scenario = None
    best_return = 0
    
    for name, stocks_list in scenarios:
        allocation = 10000 / len(stocks_list)
        total_value = sum([backtest_strategy(calculate_indicators(get_stock_data(s['ticker'])), allocation, s['strategy']) for s in stocks_list])
        profit = total_value - 10000
        roi = (profit / 10000) * 100
        
        if roi > best_return:
            best_return = roi
            best_scenario = (name, stocks_list, total_value, profit, roi)
        
        print(f"\n{name}:")
        print(f"  Stocks: {', '.join([s['ticker'] for s in stocks_list])}")
        print(f"  Allocation per stock: ${allocation:,.0f}")
        print(f"  Final Value: ${total_value:,.0f}")
        print(f"  Profit: ${profit:,.0f}")
        print(f"  ROI: {roi:+.2f}%")
    
    print("\n" + "=" * 100)
    print("🏆 BEST PORTFOLIO")
    print("=" * 100)
    name, stocks_list, total_value, profit, roi = best_scenario
    print(f"\nStrategy: {name}")
    print(f"Stocks: {', '.join([s['ticker'] for s in stocks_list])}")
    print(f"Final Value: ${total_value:,.0f}")
    print(f"Profit: ${profit:,.0f}")
    print(f"ROI: {roi:+.2f}%")
    
    print("\n" + "=" * 100)
    print("💡 KEY INSIGHTS")
    print("=" * 100)
    print(f"• Best single stock: {results[0]['ticker']} ({results[0]['roi']:+.2f}% ROI)")
    print(f"• Worst stock: {results[-1]['ticker']} ({results[-1]['roi']:+.2f}% ROI)")
    print(f"• Average ROI across all stocks: {sum([r['roi'] for r in results])/len(results):+.2f}%")
    print(f"• Diversification benefit: {roi - results[0]['roi']:.2f}% {'(worse)' if roi < results[0]['roi'] else '(better)'}")
    print("\n" + "=" * 100)

if __name__ == '__main__':
    main()

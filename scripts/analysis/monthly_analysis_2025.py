import boto3
from datetime import datetime
from collections import defaultdict

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def get_prices(ticker, start_date, end_date):
    response = table.query(
        KeyConditionExpression='ticker = :ticker AND #d BETWEEN :start AND :end',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={':ticker': ticker, ':start': start_date, ':end': end_date}
    )
    return sorted(response['Items'], key=lambda x: x['date'])

def get_monthly_return(prices, year, month):
    month_prices = [p for p in prices if p['date'].startswith(f'{year}-{month:02d}')]
    if len(month_prices) < 2:
        return None
    first = float(month_prices[0]['open'])
    last = float(month_prices[-1]['close'])
    return ((last - first) / first) * 100

tickers = ['SPY', 'QQQ', 'PLTR', 'GOOGL', 'TSLA', 'NVDA', 'HIMS', 'AAPL', 'MSFT', 'AMZN']
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

print("=" * 130)
print("MONTHLY PERFORMANCE ANALYSIS - 2025")
print("=" * 130)

# Get all data
all_data = {}
for ticker in tickers:
    prices = get_prices(ticker, '2025-01-01', '2025-12-02')
    all_data[ticker] = prices

# Monthly returns by ticker
print(f"\n{'Ticker':<8}", end='')
for month in months[:11]:  # Jan-Nov
    print(f"{month:>8}", end='')
print(f"{'YTD':>8}")
print("-" * 130)

monthly_results = defaultdict(dict)

for ticker in tickers:
    print(f"{ticker:<8}", end='')
    ytd_start = float(all_data[ticker][0]['open'])
    ytd_end = float(all_data[ticker][-1]['close'])
    ytd_return = ((ytd_end - ytd_start) / ytd_start) * 100
    
    for month_num in range(1, 12):  # Jan-Nov
        ret = get_monthly_return(all_data[ticker], 2025, month_num)
        monthly_results[month_num][ticker] = ret
        if ret is not None:
            print(f"{ret:>7.1f}%", end='')
        else:
            print(f"{'N/A':>8}", end='')
    
    print(f"{ytd_return:>7.1f}%")

# Find best performer each month
print("\n" + "=" * 130)
print("MONTHLY LEADERS")
print("=" * 130)
print(f"{'Month':<12} {'Leader':<8} {'Return':>10} {'Runner-up':<8} {'Return':>10} {'Worst':<8} {'Return':>10}")
print("-" * 130)

for month_num in range(1, 12):
    month_name = months[month_num - 1]
    returns = [(ticker, ret) for ticker, ret in monthly_results[month_num].items() if ret is not None]
    returns.sort(key=lambda x: x[1], reverse=True)
    
    if len(returns) >= 3:
        best = returns[0]
        second = returns[1]
        worst = returns[-1]
        print(f"{month_name:<12} {best[0]:<8} {best[1]:>9.1f}% {second[0]:<8} {second[1]:>9.1f}% {worst[0]:<8} {worst[1]:>9.1f}%")

# Aggregate patterns
print("\n" + "=" * 130)
print("AGGREGATE MONTHLY PATTERNS (Average across all tickers)")
print("=" * 130)

month_aggregates = []
for month_num in range(1, 12):
    returns = [ret for ret in monthly_results[month_num].values() if ret is not None]
    if returns:
        avg = sum(returns) / len(returns)
        month_aggregates.append((months[month_num - 1], avg, len(returns)))

print(f"{'Month':<12} {'Avg Return':>12} {'Tickers':>10}")
print("-" * 130)
for month, avg, count in month_aggregates:
    print(f"{month:<12} {avg:>11.1f}% {count:>10}")

# Best and worst months
print("\n" + "=" * 130)
print("BEST AND WORST MONTHS (by average)")
print("=" * 130)

sorted_months = sorted(month_aggregates, key=lambda x: x[1], reverse=True)
print("\nBEST MONTHS:")
for i, (month, avg, count) in enumerate(sorted_months[:3], 1):
    print(f"{i}. {month:<12} {avg:>+.2f}%")

print("\nWORST MONTHS:")
for i, (month, avg, count) in enumerate(sorted_months[-3:], 1):
    print(f"{i}. {month:<12} {avg:>+.2f}%")

# Ticker consistency
print("\n" + "=" * 130)
print("TICKER CONSISTENCY (months with positive returns)")
print("=" * 130)

for ticker in tickers:
    positive_months = 0
    total_months = 0
    for month_num in range(1, 12):
        ret = monthly_results[month_num].get(ticker)
        if ret is not None:
            total_months += 1
            if ret > 0:
                positive_months += 1
    
    win_rate = (positive_months / total_months * 100) if total_months > 0 else 0
    print(f"{ticker:<8} {positive_months}/{total_months} months positive ({win_rate:.1f}%)")

# Monthly leader frequency
print("\n" + "=" * 130)
print("MONTHLY LEADER FREQUENCY (how many times each ticker led)")
print("=" * 130)

leader_count = defaultdict(int)
for month_num in range(1, 12):
    returns = [(ticker, ret) for ticker, ret in monthly_results[month_num].items() if ret is not None]
    if returns:
        returns.sort(key=lambda x: x[1], reverse=True)
        leader_count[returns[0][0]] += 1

sorted_leaders = sorted(leader_count.items(), key=lambda x: x[1], reverse=True)
for ticker, count in sorted_leaders:
    print(f"{ticker:<8} led {count} month(s)")

print("\n" + "=" * 130)

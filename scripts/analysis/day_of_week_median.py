import boto3
from datetime import datetime
from statistics import median

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def get_prices(ticker, start_date, end_date):
    response = table.query(
        KeyConditionExpression='ticker = :ticker AND #d BETWEEN :start AND :end',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={':ticker': ticker, ':start': start_date, ':end': end_date}
    )
    return sorted(response['Items'], key=lambda x: x['date'])

def analyze_day_of_week(ticker, start_date, end_date):
    prices = get_prices(ticker, start_date, end_date)
    
    day_stats = {
        'Monday': {'returns': []},
        'Tuesday': {'returns': []},
        'Wednesday': {'returns': []},
        'Thursday': {'returns': []},
        'Friday': {'returns': []}
    }
    
    for i in range(1, len(prices)):
        date = datetime.strptime(prices[i]['date'], '%Y-%m-%d')
        day_name = date.strftime('%A')
        
        if day_name not in day_stats:
            continue
        
        prev_close = float(prices[i-1]['close'])
        curr_close = float(prices[i]['close'])
        daily_return = ((curr_close - prev_close) / prev_close) * 100
        
        day_stats[day_name]['returns'].append(daily_return)
    
    return day_stats

tickers = ['SPY', 'QQQ', 'PLTR', 'GOOGL', 'TSLA', 'NVDA']

print("=" * 110)
print("DAY OF WEEK ANALYSIS - MEAN vs MEDIAN")
print("=" * 110)
print(f"Period: 2025-01-01 to 2025-12-02")
print("=" * 110)

all_results = {}

for ticker in tickers:
    stats = analyze_day_of_week(ticker, '2025-01-01', '2025-12-02')
    all_results[ticker] = stats

# Aggregate
aggregate = {
    'Monday': {'returns': []},
    'Tuesday': {'returns': []},
    'Wednesday': {'returns': []},
    'Thursday': {'returns': []},
    'Friday': {'returns': []}
}

for ticker, stats in all_results.items():
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        aggregate[day]['returns'].extend(stats[day]['returns'])

print(f"\n{'Day':<12} {'Mean':>10} {'Median':>10} {'Difference':>12} {'Count':>8}")
print("-" * 110)

for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
    returns = aggregate[day]['returns']
    if returns:
        mean_return = sum(returns) / len(returns)
        median_return = median(returns)
        diff = mean_return - median_return
        
        print(f"{day:<12} {mean_return:>9.3f}% {median_return:>9.3f}% {diff:>11.3f}% {len(returns):>8}")

print("\n" + "=" * 110)
print("INDIVIDUAL TICKER COMPARISON")
print("=" * 110)

for ticker in tickers:
    print(f"\n{ticker}")
    print("-" * 110)
    print(f"{'Day':<12} {'Mean':>10} {'Median':>10} {'Difference':>12}")
    print("-" * 110)
    
    stats = all_results[ticker]
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        returns = stats[day]['returns']
        if returns:
            mean_return = sum(returns) / len(returns)
            median_return = median(returns)
            diff = mean_return - median_return
            
            print(f"{day:<12} {mean_return:>9.3f}% {median_return:>9.3f}% {diff:>11.3f}%")

print("\n" + "=" * 110)
print("KEY FINDINGS")
print("=" * 110)

# Check if ranking changes
mean_ranking = []
median_ranking = []

for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
    returns = aggregate[day]['returns']
    mean_return = sum(returns) / len(returns)
    median_return = median(returns)
    mean_ranking.append((day, mean_return))
    median_ranking.append((day, median_return))

mean_ranking.sort(key=lambda x: x[1], reverse=True)
median_ranking.sort(key=lambda x: x[1], reverse=True)

print("\nMEAN RANKING:")
for rank, (day, val) in enumerate(mean_ranking, 1):
    print(f"{rank}. {day:<12} {val:>+.3f}%")

print("\nMEDIAN RANKING:")
for rank, (day, val) in enumerate(median_ranking, 1):
    print(f"{rank}. {day:<12} {val:>+.3f}%")

if mean_ranking == median_ranking:
    print("\n✓ Rankings are IDENTICAL - mean and median tell the same story")
else:
    print("\n✗ Rankings DIFFER - outliers are affecting the mean")

print("=" * 110)

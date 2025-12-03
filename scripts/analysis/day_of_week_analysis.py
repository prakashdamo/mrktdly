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

def analyze_day_of_week(ticker, start_date, end_date):
    prices = get_prices(ticker, start_date, end_date)
    
    day_stats = {
        'Monday': {'returns': [], 'up_days': 0, 'down_days': 0},
        'Tuesday': {'returns': [], 'up_days': 0, 'down_days': 0},
        'Wednesday': {'returns': [], 'up_days': 0, 'down_days': 0},
        'Thursday': {'returns': [], 'up_days': 0, 'down_days': 0},
        'Friday': {'returns': [], 'up_days': 0, 'down_days': 0}
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
        if daily_return > 0:
            day_stats[day_name]['up_days'] += 1
        else:
            day_stats[day_name]['down_days'] += 1
    
    return day_stats

tickers = ['SPY', 'QQQ', 'PLTR', 'GOOGL', 'TSLA', 'NVDA']

print("=" * 100)
print("DAY OF WEEK ANALYSIS - 2025")
print("=" * 100)
print(f"Period: 2025-01-01 to 2025-12-02")
print("=" * 100)

all_results = {}

for ticker in tickers:
    print(f"\n{ticker}")
    print("-" * 100)
    
    stats = analyze_day_of_week(ticker, '2025-01-01', '2025-12-02')
    all_results[ticker] = stats
    
    print(f"{'Day':<12} {'Avg Return':>12} {'Win Rate':>10} {'Up Days':>10} {'Down Days':>12} {'Total':>8}")
    print("-" * 100)
    
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        returns = stats[day]['returns']
        if returns:
            avg_return = sum(returns) / len(returns)
            total_days = len(returns)
            win_rate = (stats[day]['up_days'] / total_days * 100) if total_days > 0 else 0
            
            print(f"{day:<12} {avg_return:>11.2f}% {win_rate:>9.1f}% "
                  f"{stats[day]['up_days']:>10} {stats[day]['down_days']:>12} {total_days:>8}")

# Aggregate across all tickers
print("\n" + "=" * 100)
print("AGGREGATE ANALYSIS (All Tickers Combined)")
print("=" * 100)

aggregate = {
    'Monday': {'returns': [], 'up': 0, 'down': 0},
    'Tuesday': {'returns': [], 'up': 0, 'down': 0},
    'Wednesday': {'returns': [], 'up': 0, 'down': 0},
    'Thursday': {'returns': [], 'up': 0, 'down': 0},
    'Friday': {'returns': [], 'up': 0, 'down': 0}
}

for ticker, stats in all_results.items():
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        aggregate[day]['returns'].extend(stats[day]['returns'])
        aggregate[day]['up'] += stats[day]['up_days']
        aggregate[day]['down'] += stats[day]['down_days']

print(f"\n{'Day':<12} {'Avg Return':>12} {'Win Rate':>10} {'Up Days':>10} {'Down Days':>12} {'Total':>8}")
print("-" * 100)

day_order = []
for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
    returns = aggregate[day]['returns']
    if returns:
        avg_return = sum(returns) / len(returns)
        total = len(returns)
        win_rate = (aggregate[day]['up'] / total * 100) if total > 0 else 0
        day_order.append((day, avg_return))
        
        print(f"{day:<12} {avg_return:>11.2f}% {win_rate:>9.1f}% "
              f"{aggregate[day]['up']:>10} {aggregate[day]['down']:>12} {total:>8}")

# Rank days
print("\n" + "=" * 100)
print("RANKING (Best to Worst)")
print("=" * 100)
day_order.sort(key=lambda x: x[1], reverse=True)
for rank, (day, avg_return) in enumerate(day_order, 1):
    print(f"{rank}. {day:<12} {avg_return:>+.3f}%")

print("\n" + "=" * 100)
print("KEY FINDINGS")
print("=" * 100)
best_day = day_order[0]
worst_day = day_order[-1]
print(f"• Best day: {best_day[0]} ({best_day[1]:+.3f}% average)")
print(f"• Worst day: {worst_day[0]} ({worst_day[1]:+.3f}% average)")
print(f"• Difference: {best_day[1] - worst_day[1]:.3f}%")
print("=" * 100)

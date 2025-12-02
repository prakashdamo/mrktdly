#!/usr/bin/env python3
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def get_stock_data(ticker):
    """Get all available stock data"""
    response = table.query(
        KeyConditionExpression='ticker = :ticker',
        ExpressionAttributeValues={':ticker': ticker}
    )
    
    data = []
    for item in response['Items']:
        data.append({
            'date': item['date'],
            'close': float(item['close']),
            'volume': int(item['volume'])
        })
    
    return sorted(data, key=lambda x: x['date'])

def calculate_drawdowns(data):
    """Find all significant drawdowns (10%+ drops)"""
    drawdowns = []
    peak = data[0]['close']
    peak_date = data[0]['date']
    
    for i, point in enumerate(data):
        if point['close'] > peak:
            peak = point['close']
            peak_date = point['date']
        
        drawdown = ((point['close'] - peak) / peak) * 100
        
        if drawdown <= -10:  # 10%+ drop
            # Check if this is a new drawdown or continuation
            if not drawdowns or drawdowns[-1]['trough_date'] != point['date']:
                # Find the trough
                trough = point['close']
                trough_date = point['date']
                
                # Look ahead to find actual bottom
                for j in range(i, min(i+60, len(data))):
                    if data[j]['close'] < trough:
                        trough = data[j]['close']
                        trough_date = data[j]['date']
                    elif data[j]['close'] > peak * 0.95:  # Recovered 95% of peak
                        break
                
                # Check if we already recorded this drawdown
                if not drawdowns or trough_date != drawdowns[-1]['trough_date']:
                    drawdowns.append({
                        'peak_date': peak_date,
                        'peak_price': peak,
                        'trough_date': trough_date,
                        'trough_price': trough,
                        'drawdown_pct': ((trough - peak) / peak) * 100,
                        'duration_days': (datetime.strptime(trough_date, '%Y-%m-%d') - 
                                        datetime.strptime(peak_date, '%Y-%m-%d')).days
                    })
    
    return drawdowns

def calculate_technicals_at_date(data, target_date):
    """Calculate technical indicators at a specific date"""
    # Find index of target date
    idx = None
    for i, d in enumerate(data):
        if d['date'] == target_date:
            idx = i
            break
    
    if not idx or idx < 50:
        return None
    
    # Calculate indicators
    current = data[idx]
    
    # Moving averages
    sma20 = sum([data[i]['close'] for i in range(idx-19, idx+1)]) / 20
    sma50 = sum([data[i]['close'] for i in range(idx-49, idx+1)]) / 50
    
    # RSI
    gains = sum([max(data[i]['close'] - data[i-1]['close'], 0) for i in range(idx-13, idx+1)])
    losses = sum([max(data[i-1]['close'] - data[i]['close'], 0) for i in range(idx-13, idx+1)])
    rs = gains / losses if losses > 0 else 100
    rsi = 100 - (100 / (1 + rs))
    
    # Momentum
    momentum_20d = ((current['close'] - data[idx-20]['close']) / data[idx-20]['close']) * 100
    
    # Signals
    below_sma20 = current['close'] < sma20
    below_sma50 = current['close'] < sma50
    death_cross = sma20 < sma50
    
    return {
        'price': current['close'],
        'sma20': sma20,
        'sma50': sma50,
        'rsi': rsi,
        'momentum_20d': momentum_20d,
        'below_sma20': below_sma20,
        'below_sma50': below_sma50,
        'death_cross': death_cross,
        'warning_score': sum([below_sma20, below_sma50, death_cross, rsi < 40, momentum_20d < -5])
    }

def main():
    print("=" * 120)
    print("MARKET WEAKNESS ANALYSIS - Would Our Approach Have Warned Us?")
    print("=" * 120)
    
    # Analyze SPY as market proxy
    print("\n📊 Analyzing SPY (S&P 500) for market weakness periods...")
    
    spy_data = get_stock_data('SPY')
    drawdowns = calculate_drawdowns(spy_data)
    
    # Filter significant drawdowns (10%+)
    significant_drawdowns = [d for d in drawdowns if d['drawdown_pct'] <= -10]
    
    print(f"\n{'='*120}")
    print(f"SIGNIFICANT MARKET DRAWDOWNS (10%+ drops)")
    print('='*120)
    print(f"Found {len(significant_drawdowns)} significant drawdown periods\n")
    
    for i, dd in enumerate(significant_drawdowns, 1):
        print(f"\n{'='*120}")
        print(f"DRAWDOWN #{i}")
        print('='*120)
        print(f"Peak Date: {dd['peak_date']} @ ${dd['peak_price']:.2f}")
        print(f"Trough Date: {dd['trough_date']} @ ${dd['trough_price']:.2f}")
        print(f"Drawdown: {dd['drawdown_pct']:.2f}%")
        print(f"Duration: {dd['duration_days']} days")
        
        # Check technicals at peak (would we have seen warning?)
        peak_technicals = calculate_technicals_at_date(spy_data, dd['peak_date'])
        
        if peak_technicals:
            print(f"\n🔍 TECHNICAL SIGNALS AT PEAK ({dd['peak_date']}):")
            print(f"  Price: ${peak_technicals['price']:.2f}")
            print(f"  RSI: {peak_technicals['rsi']:.1f} {'⚠️ Overbought' if peak_technicals['rsi'] > 70 else '✅ Normal' if peak_technicals['rsi'] > 40 else '⚠️ Oversold'}")
            print(f"  20-day Momentum: {peak_technicals['momentum_20d']:+.2f}%")
            print(f"  Below 20 MA: {'🔴 YES' if peak_technicals['below_sma20'] else '🟢 NO'}")
            print(f"  Below 50 MA: {'🔴 YES' if peak_technicals['below_sma50'] else '🟢 NO'}")
            print(f"  Death Cross: {'🔴 YES' if peak_technicals['death_cross'] else '🟢 NO'}")
            print(f"  Warning Score: {peak_technicals['warning_score']}/5")
            
            if peak_technicals['warning_score'] >= 3:
                print(f"  ⚠️  STRONG WARNING - Would have suggested caution")
            elif peak_technicals['warning_score'] >= 2:
                print(f"  🟡 MODERATE WARNING - Some red flags")
            else:
                print(f"  ❌ NO WARNING - Technicals looked healthy")
        
        # Check technicals 20 days before peak (early warning?)
        early_date = (datetime.strptime(dd['peak_date'], '%Y-%m-%d') - timedelta(days=20)).strftime('%Y-%m-%d')
        early_idx = None
        for j, d in enumerate(spy_data):
            if d['date'] >= early_date:
                early_idx = j
                break
        
        if early_idx:
            early_technicals = calculate_technicals_at_date(spy_data, spy_data[early_idx]['date'])
            if early_technicals:
                print(f"\n🔍 EARLY WARNING (20 days before peak - {spy_data[early_idx]['date']}):")
                print(f"  RSI: {early_technicals['rsi']:.1f}")
                print(f"  Momentum: {early_technicals['momentum_20d']:+.2f}%")
                print(f"  Warning Score: {early_technicals['warning_score']}/5")
                
                if early_technicals['warning_score'] >= 2:
                    print(f"  ✅ EARLY WARNING DETECTED")
                else:
                    print(f"  ❌ No early warning")
    
    # Analyze 2025 specifically
    print(f"\n{'='*120}")
    print("2025 MARKET ANALYSIS")
    print('='*120)
    
    # Find 2025 data
    data_2025 = [d for d in spy_data if d['date'] >= '2025-01-01']
    
    if data_2025:
        start_price = data_2025[0]['close']
        end_price = data_2025[-1]['close']
        
        # Find worst drawdown in 2025
        worst_dd = 0
        worst_dd_date = None
        peak_2025 = start_price
        
        for point in data_2025:
            if point['close'] > peak_2025:
                peak_2025 = point['close']
            dd = ((point['close'] - peak_2025) / peak_2025) * 100
            if dd < worst_dd:
                worst_dd = dd
                worst_dd_date = point['date']
        
        print(f"\n2025 Performance:")
        print(f"  Start: ${start_price:.2f}")
        print(f"  End: ${end_price:.2f}")
        print(f"  Return: {((end_price - start_price) / start_price * 100):+.2f}%")
        print(f"  Worst Drawdown: {worst_dd:.2f}% on {worst_dd_date}")
        
        if worst_dd > -10:
            print(f"  ✅ 2025 was a STRONG YEAR - No major corrections")
        else:
            print(f"  ⚠️  2025 had significant volatility")
    
    # Summary
    print(f"\n{'='*120}")
    print("📊 EFFECTIVENESS ANALYSIS")
    print('='*120)
    
    warnings_given = sum([1 for dd in significant_drawdowns 
                         if calculate_technicals_at_date(spy_data, dd['peak_date']) 
                         and calculate_technicals_at_date(spy_data, dd['peak_date'])['warning_score'] >= 2])
    
    total_drawdowns = len(significant_drawdowns)
    
    if total_drawdowns > 0:
        effectiveness = (warnings_given / total_drawdowns) * 100
        
        print(f"\n✅ Warnings Given: {warnings_given}/{total_drawdowns} drawdowns")
        print(f"📊 Effectiveness Rate: {effectiveness:.1f}%")
        
        if effectiveness >= 70:
            print(f"🟢 HIGH EFFECTIVENESS - Technical approach would have warned us")
        elif effectiveness >= 50:
            print(f"🟡 MODERATE EFFECTIVENESS - Some warnings missed")
        else:
            print(f"🔴 LOW EFFECTIVENESS - Many warnings missed")
    
    print(f"\n{'='*120}")
    print("💡 KEY FINDINGS")
    print('='*120)
    
    print("\n✅ WHAT WORKS:")
    print("  • RSI overbought (>70) often precedes corrections")
    print("  • Death cross (20 MA < 50 MA) signals trend weakness")
    print("  • Negative momentum confirms downtrend")
    print("  • Multiple signals together = stronger warning")
    
    print("\n⚠️  LIMITATIONS:")
    print("  • Technical signals can be late (already in drawdown)")
    print("  • False positives (warnings without major drops)")
    print("  • Can't predict sudden crashes (black swans)")
    print("  • Works better for gradual corrections than flash crashes")
    
    print("\n🎯 RECOMMENDATIONS:")
    print("  • Use technical signals as RISK MANAGEMENT tool")
    print("  • Don't try to time exact tops/bottoms")
    print("  • Reduce exposure when warning score >= 3")
    print("  • Combine with fundamentals and macro analysis")
    print("  • Always maintain diversification")
    
    print(f"\n{'='*120}")

if __name__ == '__main__':
    main()

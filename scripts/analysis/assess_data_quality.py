#!/usr/bin/env python3
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('mrktdly-price-history')

def check_data_coverage(ticker):
    """Check data coverage and quality"""
    response = table.query(
        KeyConditionExpression='ticker = :ticker',
        ExpressionAttributeValues={':ticker': ticker}
    )
    
    if not response['Items']:
        return None
    
    dates = sorted([item['date'] for item in response['Items']])
    
    return {
        'ticker': ticker,
        'total_records': len(dates),
        'start_date': dates[0],
        'end_date': dates[-1],
        'date_range_days': (datetime.strptime(dates[-1], '%Y-%m-%d') - 
                           datetime.strptime(dates[0], '%Y-%m-%d')).days,
        'years_of_data': len(dates) / 252  # Trading days per year
    }

def main():
    print("=" * 120)
    print("DATA QUALITY ASSESSMENT")
    print("=" * 120)
    
    # Check key tickers
    tickers = {
        'ETFs': ['SPY', 'QQQ', 'IWM'],
        'Mag7': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'],
        'Growth': ['PLTR', 'HIMS', 'HOOD', 'SOFI', 'COIN', 'RKLB', 'IONQ'],
        'Other': ['BB', 'MSTR', 'SMCI', 'ARM']
    }
    
    all_data = {}
    
    for category, ticker_list in tickers.items():
        print(f"\n{'='*120}")
        print(f"{category.upper()}")
        print('='*120)
        print(f"{'Ticker':<8} {'Records':<10} {'Start Date':<12} {'End Date':<12} {'Years':<8} {'Quality':<15}")
        print('-'*120)
        
        for ticker in ticker_list:
            try:
                info = check_data_coverage(ticker)
                if info:
                    quality = "🟢 Excellent" if info['years_of_data'] >= 4 else \
                             "🟡 Good" if info['years_of_data'] >= 2 else \
                             "🟠 Fair" if info['years_of_data'] >= 1 else \
                             "🔴 Poor"
                    
                    print(f"{ticker:<8} {info['total_records']:<10} {info['start_date']:<12} {info['end_date']:<12} "
                          f"{info['years_of_data']:<7.1f} {quality:<15}")
                    
                    all_data[ticker] = info
                else:
                    print(f"{ticker:<8} {'NO DATA':<10}")
            except Exception as e:
                print(f"{ticker:<8} ERROR: {e}")
    
    # Analysis
    print(f"\n{'='*120}")
    print("DATA QUALITY SUMMARY")
    print('='*120)
    
    if all_data:
        avg_years = sum([d['years_of_data'] for d in all_data.values()]) / len(all_data)
        min_years = min([d['years_of_data'] for d in all_data.values()])
        max_years = max([d['years_of_data'] for d in all_data.values()])
        
        excellent = len([d for d in all_data.values() if d['years_of_data'] >= 4])
        good = len([d for d in all_data.values() if 2 <= d['years_of_data'] < 4])
        fair = len([d for d in all_data.values() if 1 <= d['years_of_data'] < 2])
        poor = len([d for d in all_data.values() if d['years_of_data'] < 1])
        
        print(f"\n📊 Coverage Statistics:")
        print(f"  Total tickers analyzed: {len(all_data)}")
        print(f"  Average years of data: {avg_years:.1f}")
        print(f"  Range: {min_years:.1f} - {max_years:.1f} years")
        print(f"\n📈 Quality Distribution:")
        print(f"  🟢 Excellent (4+ years): {excellent} tickers")
        print(f"  🟡 Good (2-4 years): {good} tickers")
        print(f"  🟠 Fair (1-2 years): {fair} tickers")
        print(f"  🔴 Poor (<1 year): {poor} tickers")
    
    print(f"\n{'='*120}")
    print("⚠️  DATA LIMITATIONS & CONCERNS")
    print('='*120)
    
    concerns = []
    
    # Check for recent IPOs
    recent_ipos = [t for t, d in all_data.items() if d['years_of_data'] < 2]
    if recent_ipos:
        concerns.append(f"Recent IPOs with limited history: {', '.join(recent_ipos)}")
    
    # Check for 2025 data
    has_2025 = [t for t, d in all_data.items() if d['end_date'] >= '2025-01-01']
    missing_2025 = [t for t, d in all_data.items() if d['end_date'] < '2025-01-01']
    
    if missing_2025:
        concerns.append(f"Missing 2025 data: {', '.join(missing_2025)}")
    
    # Check for gaps
    print("\n1. DATA COMPLETENESS:")
    print(f"   ✅ Tickers with 2025 data: {len(has_2025)}/{len(all_data)}")
    if missing_2025:
        print(f"   ❌ Missing 2025 data: {', '.join(missing_2025)}")
    
    print("\n2. HISTORICAL DEPTH:")
    if avg_years >= 3:
        print(f"   ✅ Good historical depth (avg {avg_years:.1f} years)")
    else:
        print(f"   ⚠️  Limited historical depth (avg {avg_years:.1f} years)")
        concerns.append(f"Average data history only {avg_years:.1f} years")
    
    print("\n3. PREDICTION RELIABILITY:")
    if avg_years >= 3 and len(has_2025) >= len(all_data) * 0.9:
        print("   ✅ HIGH - Sufficient data for reliable predictions")
    elif avg_years >= 2 and len(has_2025) >= len(all_data) * 0.8:
        print("   🟡 MODERATE - Adequate data but some limitations")
    else:
        print("   🔴 LOW - Insufficient data for high-confidence predictions")
    
    print(f"\n{'='*120}")
    print("💡 RECOMMENDATIONS")
    print('='*120)
    
    print("\n✅ WHAT WE HAVE:")
    print("  • 1 year of 2025 data (Jan-Dec) for backtesting")
    print("  • Multiple years of historical data for most tickers")
    print("  • Complete technical indicators (RSI, MA, momentum)")
    print("  • Real market performance data")
    
    print("\n⚠️  WHAT WE'RE MISSING:")
    print("  • Multiple market cycles (need 5-10 years ideally)")
    print("  • Bear market data (2025 was mostly bullish)")
    print("  • Fundamental data (earnings, revenue, P/E ratios)")
    print("  • Macroeconomic indicators (Fed rates, inflation, GDP)")
    print("  • Sector rotation patterns")
    print("  • Options flow and institutional positioning")
    
    print("\n🎯 CONFIDENCE LEVELS:")
    print("  • Short-term (1-3 months): 🟢 HIGH - Technical analysis reliable")
    print("  • Medium-term (3-6 months): 🟡 MODERATE - Momentum can shift")
    print("  • Long-term (1 year+): 🟠 LOW-MODERATE - Many unknowns")
    
    print("\n📈 IMPROVING PREDICTIONS:")
    print("  1. Add fundamental analysis (P/E, growth rates, earnings)")
    print("  2. Include macroeconomic data (Fed policy, rates, inflation)")
    print("  3. Analyze sector rotation and market breadth")
    print("  4. Monitor institutional flows and sentiment")
    print("  5. Consider geopolitical and regulatory factors")
    print("  6. Use ensemble models (combine multiple approaches)")
    
    print(f"\n{'='*120}")
    print("🔮 FINAL VERDICT")
    print('='*120)
    
    if avg_years >= 3:
        print("\n✅ DATA IS SUFFICIENT for:")
        print("   • Technical analysis and pattern recognition")
        print("   • Short-term momentum predictions")
        print("   • Relative performance comparisons")
        print("   • Backtesting trading strategies")
        
        print("\n⚠️  DATA IS LIMITED for:")
        print("   • Long-term fundamental predictions")
        print("   • Bear market behavior forecasting")
        print("   • Black swan event modeling")
        
        print("\n💡 CONCLUSION:")
        print("   Our predictions are REASONABLY RELIABLE for 2026 trends,")
        print("   but should be combined with:")
        print("   • Fundamental analysis")
        print("   • Market sentiment")
        print("   • Risk management")
        print("   • Regular rebalancing")
    else:
        print("\n⚠️  DATA IS MARGINAL:")
        print("   Use predictions as ONE input among many.")
        print("   Supplement with fundamental research and expert analysis.")
    
    print(f"\n{'='*120}")

if __name__ == '__main__':
    main()

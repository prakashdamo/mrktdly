#!/usr/bin/env python3
"""Test the technical health score function"""

import sys
sys.path.insert(0, '.')
from lambda_function import lambda_handler

# Test with different tickers
test_tickers = ['PLTR', 'GOOGL', 'TSLA', 'MSTR', 'HIMS']

print("=" * 80)
print("TECHNICAL HEALTH SCORE TEST")
print("=" * 80)

for ticker in test_tickers:
    print(f"\n{ticker}:")
    print("-" * 80)
    
    result = lambda_handler({'ticker': ticker}, None)
    
    if result['statusCode'] == 200:
        import json
        data = json.loads(result['body'])
        
        print(f"Score: {data['score']}/100 {data['emoji']}")
        print(f"Rating: {data['rating']}")
        print(f"\nComponents:")
        for component, score in data['components'].items():
            print(f"  {component}: {score}")
        
        print(f"\nTop Signals:")
        for signal in data['signals']:
            print(f"  • {signal}")
        
        print(f"\nTechnicals:")
        print(f"  Price: ${data['technicals']['price']:.2f}")
        print(f"  RSI: {data['technicals']['rsi']}")
        print(f"  1M Momentum: {data['technicals']['momentum_1m']:+.2f}%")
        print(f"  3M Momentum: {data['technicals']['momentum_3m']:+.2f}%")
    else:
        print(f"Error: {result['body']}")

print("\n" + "=" * 80)

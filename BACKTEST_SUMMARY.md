# Last Month Backtest Implementation

## What Was Added

### 1. Backtest Script (`backtest_last_month.py`)
- Analyzes all signals from the last 30 days
- Evaluates each signal against actual price movements
- Calculates key performance metrics:
  - Win rate
  - Average win/loss percentages
  - Expectancy (expected return per trade)
  - Risk:Reward ratio
  - Days held for each trade

### 2. Dashboard Update (`website/performance.html`)
- Added "Last Month Backtest" section with historical performance
- Shows 4 key metrics in a clean grid layout
- Automatically loads backtest data from API
- Matches the existing design aesthetic

## Current Results (as of Nov 30, 2025)

```
Total Signals: 31
Closed: 11 | Open: 20
Win Rate: 45.5% (5/11)
Avg Win: +5.00% | Avg Loss: -3.00%
Expectancy: 0.64%
Risk:Reward: 1.67:1
```

### Winners (5)
- MRK: +5.00% in 4 days
- META: +5.00% in 4 days
- GOOGL: +5.00% in 3 days
- AMZN: +5.00% in 5 days
- BMY: +4.99% in 3 days

### Losses (6)
- ADBE, UPS, HD, TMO, TXN, ABT: -3.00% each

### Open Trades (20)
HON, UNH, CRM, COST, XOM, CSCO, QCOM, LOW, IBM, BAC, AMGN, DIS, PFE, DHR, UNP, NKE, AAPL, MA, LLY, V

## Usage

### Run Backtest Locally
```bash
cd /home/prakash/mrktdly
python3 backtest_last_month.py
```

### View Dashboard
Visit: https://mrktdly-website.s3.amazonaws.com/performance.html

The dashboard now shows:
1. **Overall Performance** - Last 30 days live tracking
2. **Last Month Backtest** - Historical validation
3. **Active Signals** - Current open positions

## Key Insights

- Positive expectancy (+0.64%) indicates profitable system over time
- 1.67:1 risk:reward ratio is healthy
- Win rate of 45.5% is acceptable with this R:R
- Average holding period: 3-5 days for winners
- 64% of signals still open (need more time to resolve)

## Next Steps

1. Monitor open trades as they resolve
2. Run weekly backtests to track consistency
3. Consider adding filters for higher conviction signals
4. Analyze why some signals stopped out immediately (0 days)

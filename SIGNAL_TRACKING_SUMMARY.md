# Signal Tracking System - Summary

## What Was Built (Nov 30, 2025)

### 1. Signal Performance Tracking Infrastructure
- **DynamoDB Table**: `mrktdly-signal-performance`
  - Keys: ticker (partition), signal_date (sort)
  - GSI: status-index for querying OPEN signals
  - Fields: action, entry, target, stop_loss, conviction, risk_reward, status, outcome, return_pct, days_held, closed_date

### 2. Lambda Functions
- **mrktdly-signal-tracker**: Records new signals to DynamoDB
- **mrktdly-signal-evaluator**: Runs daily (9pm UTC via EventBridge), checks if signals hit target/stop/expired
- **mrktdly-signal-stats**: API endpoint to get performance metrics

### 3. Signal Evaluation Logic
- **WIN**: Price hits target
- **LOSS**: Price hits stop loss
- **EXPIRED**: After 7 days without hitting target/stop, closes at current price
- Tracks: return_pct, days_held, closed_date

### 4. Performance Dashboard
- Created `website/performance.html` 
- Displays: win rate, expectancy, avg win/loss, recent signals
- Added navigation link to index.html

## Current State

### Test Results (Nov 21-30, 2025)
Generated 31 BUY signals using simple strategy (close > open):
- **Win Rate**: 0% (no signals hit +5% target in 7 days)
- **Average Return**: +2.77% (all expired but moved up)
- **Expectancy**: +2.77% per trade
- **Best**: META +9.04%, MRK +7.23%
- **Worst**: ADBE -1.25%, XOM -0.99%

### Key Insight
Strategy direction is correct (stocks went up) but targets too aggressive for timeframe. Need either:
- Lower targets (3% instead of 5%)
- Longer holding period (14 days instead of 7)

## Signal Generation Methods

### Method 1: Production (ticker-analysis-v2)
**Status**: Not generating signals
- Has ML model predictions (market state, price ranges)
- Has Bedrock AI analysis
- Missing: Logic to convert predictions into BUY/SELL signals

### Method 2: Backfill Script (backfill_from_date.py)
**Status**: Working, used for testing
- Simple rule: BUY if close > open
- Fixed targets: +5%, stops: -3%
- Used to test signal tracking system

## Files Created/Modified
- `/home/prakash/mrktdly/lambda/signal-tracker/lambda_function.py`
- `/home/prakash/mrktdly/lambda/signal-evaluator/lambda_function.py`
- `/home/prakash/mrktdly/lambda/signal-stats/lambda_function.py`
- `/home/prakash/mrktdly/website/performance.html`
- `/home/prakash/mrktdly/infrastructure/signal-performance-table.json`
- `/home/prakash/mrktdly/backfill_from_date.py`
- `/home/prakash/mrktdly/regenerate_last_week.py`
- `/home/prakash/mrktdly/.gitignore` (updated)

## Bugs Fixed
1. Fibonacci calculation (was using 52-week values instead of 30-day swing)
2. Signal validation (entry/target/stop must be >0)
3. Duplicate signal prevention
4. Signal-stats conviction handling (string vs numeric)

## Next Steps
1. Add signal generation logic to ticker-analysis-v2 based on ML predictions
2. Tune strategy parameters (targets, stops, holding period)
3. Test with real ML-based signals instead of simple close>open rule
4. Consider different strategies for different market states

## Lambda Function Names
All have `mrktdly-` prefix:
- mrktdly-ticker-analysis-v2
- mrktdly-signal-tracker
- mrktdly-signal-evaluator
- mrktdly-signal-stats

## API Endpoints
- Signal Stats: GET via API Gateway (check infrastructure/setup-api.sh for URL)

## EventBridge Schedule
- signal-evaluator runs daily at 9pm UTC (4pm EST)

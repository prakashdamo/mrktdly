# Signal Tracking System

## Overview

Full-circle signal tracking and performance evaluation system for ML trading recommendations.

## Architecture

```
ticker-analysis-v2 (generates signal)
    ↓
signal-tracker (records signal)
    ↓
mrktdly-signal-performance (DynamoDB)
    ↓
signal-evaluator (daily check)
    ↓
Updates outcome (WIN/LOSS/EXPIRED)
    ↓
signal-stats (API)
    ↓
ticker-analysis.html (displays performance)
```

## Components

### 1. DynamoDB Table: `mrktdly-signal-performance`
- **Primary Key**: ticker (HASH), signal_date (RANGE)
- **GSI**: status-index (for querying open signals)
- **Attributes**:
  - action: BUY/SELL
  - entry, target, stop_loss: price levels
  - conviction: 0-1 score
  - status: OPEN/WIN/LOSS/EXPIRED
  - return_pct: actual return
  - days_held: duration

### 2. Lambda: `signal-tracker`
- Triggered by ticker-analysis-v2 when recommendation generated
- Records signal with OPEN status
- Async invocation (doesn't block analysis)

### 3. Lambda: `signal-evaluator`
- Runs daily at 9pm UTC (EventBridge)
- Queries all OPEN signals
- Checks price history to see if target/stop hit
- Updates status and calculates returns
- Expires signals after 5 trading days

### 4. Lambda: `signal-stats`
- API endpoint: GET /signal-stats?ticker=AAPL&days=30
- Calculates:
  - Win rate
  - Avg win/loss
  - Expectancy
  - Risk/reward ratio
  - Recent signals with outcomes

### 5. UI: ticker-analysis.html
- Displays "Model Track Record" section
- Shows win rate, expectancy, R:R
- Lists last 10 signals with outcomes
- Color-coded (green=win, red=loss, blue=open)

## Evaluation Logic

### WIN Condition
- **BUY**: High >= target before low <= stop
- **SELL**: Low <= target before high >= stop

### LOSS Condition
- **BUY**: Low <= stop before high >= target
- **SELL**: High >= stop before low <= target

### EXPIRED Condition
- 5+ trading days pass without hitting target or stop
- Return calculated from entry to current price

## Key Metrics

### Win Rate
```
wins / (wins + losses) * 100
```

### Expectancy (most important)
```
(win_rate * avg_win) - (loss_rate * avg_loss)
```
Example: 65% win rate, +4% avg win, -2% avg loss
= (0.65 × 4%) - (0.35 × 2%) = 1.9% per trade

### Risk/Reward Ratio
```
avg_win / abs(avg_loss)
```

## Deployment

```bash
./deploy-signal-tracking.sh
```

This will:
1. Create DynamoDB table
2. Deploy 3 Lambda functions
3. Update ticker-analysis-v2 to record signals
4. Set up daily EventBridge schedule
5. Configure permissions

## Testing

### 1. Generate a signal
```bash
aws lambda invoke --function-name mrktdly-ticker-analysis-v2 \
  --payload '{"ticker":"AAPL"}' \
  --region us-east-1 response.json
```

### 2. Check signal was recorded
```bash
aws dynamodb query --table-name mrktdly-signal-performance \
  --key-condition-expression "ticker = :t" \
  --expression-attribute-values '{":t":{"S":"AAPL"}}' \
  --region us-east-1
```

### 3. Run evaluator manually
```bash
aws lambda invoke --function-name mrktdly-signal-evaluator \
  --region us-east-1 response.json
```

### 4. Get stats
```bash
curl "https://YOUR_API_GATEWAY/signal-stats?ticker=AAPL&days=30"
```

## API Gateway Setup

Add signal-stats endpoint:
1. Create GET method on /signal-stats
2. Integration: Lambda - mrktdly-signal-stats
3. Enable CORS
4. Deploy to prod stage
5. Update ticker-analysis.html with API URL

## Monitoring

### Check evaluator runs
```bash
aws logs tail /aws/lambda/mrktdly-signal-evaluator --follow
```

### View signal performance
```bash
aws dynamodb scan --table-name mrktdly-signal-performance \
  --filter-expression "outcome = :o" \
  --expression-attribute-values '{":o":{"S":"WIN"}}' \
  --region us-east-1
```

## Future Enhancements

1. **Backfill historical signals** - Analyze past recommendations
2. **Confidence-based filtering** - Only show high conviction signals
3. **Sector performance** - Which sectors does model perform best in
4. **Market regime analysis** - Bull vs bear market performance
5. **Paper trading account** - Live P&L tracking
6. **Alerts** - Notify when signal closes or model performance degrades
7. **Comparative analysis** - Model vs buy-and-hold vs S&P 500

## Notes

- Signals expire after 5 trading days (7 calendar days)
- Evaluator runs daily at 9pm UTC (after market close)
- Performance stats cached for 2 hours
- Only BUY/SELL signals tracked (HOLD/AVOID ignored)

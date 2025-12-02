# Swing Scanner Feature

## Overview
The Swing Scanner detects consolidation breakout patterns with volume confirmation, helping traders identify high-probability swing trade opportunities.

## Architecture

### Components
1. **Lambda Function**: `mrktdly-swing-scanner`
   - Scans all tickers daily for breakout patterns
   - Stores signals in DynamoDB
   - Runtime: Python 3.11, 512MB, 5min timeout

2. **DynamoDB Table**: `mrktdly-swing-signals`
   - Primary Key: `date` (HASH), `ticker` (RANGE)
   - Stores pattern details, entry/exit levels, risk/reward ratios

3. **API Endpoint**: `/swing-signals`
   - Query parameters: `pattern`, `min_rr`, `date`
   - Returns filtered signals sorted by risk/reward

4. **Frontend**: `/swing-scanner.html`
   - Authenticated page (requires login)
   - Filters by pattern type and min R/R
   - Links to ticker analysis pages

## Pattern Detection Logic

### 1. Consolidation Breakout
Identifies stocks breaking out of tight ranges with volume confirmation:

**Criteria:**
- Consolidation period: 35 days (days -40 to -5)
- Price range < 10% during consolidation
- Breakout: Close > 2% above resistance
- Volume surge: 50%+ above average
- Risk/Reward calculated from support to projected target

**Signals Include:**
- Entry price (current close)
- Support level (stop loss)
- Resistance level (breakout point)
- Target (2x range projection)
- Risk/Reward ratio
- Volume surge percentage

### 2. Bull Flag
Strong uptrend followed by tight consolidation and breakout:

**Criteria:**
- Flagpole: 20%+ move in 5-10 days
- Flag: 3-8 day consolidation, < 8% range
- Volume dries up during flag
- Breakout: Close > 1% above flag resistance
- Volume surge: 30%+ above flag average

**Target:**
- Flagpole height projected from breakout point

### 3. Ascending Triangle
Flat resistance with rising support, bullish continuation pattern:

**Criteria:**
- Formation: 15-30 days
- Flat resistance: 3+ tests within 2% range
- Rising support: Higher lows throughout formation
- Breakout: Close > 2% above resistance
- Volume surge: 50%+ above average

**Target:**
- Triangle height (resistance - initial low) projected upward

## Usage

### Run Scanner Manually
```bash
aws lambda invoke \
  --function-name mrktdly-swing-scanner \
  --region us-east-1 \
  output.json
```

### Schedule Daily Scans
Set up EventBridge rule to run after market close:
```bash
aws events put-rule \
  --name mrktdly-daily-swing-scan \
  --schedule-expression "cron(0 22 ? * MON-FRI *)" \
  --region us-east-1

aws events put-targets \
  --rule mrktdly-daily-swing-scan \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:060195792007:function:mrktdly-swing-scanner"
```

### Access Frontend
1. Login at https://mrktdly.com
2. Navigate to Swing Scanner from nav menu
3. Filter by pattern type and min R/R
4. Click ticker to view detailed analysis

## API Examples

### Get All Signals
```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api.mrktdly.com/swing-signals
```

### Filter by Risk/Reward
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.mrktdly.com/swing-signals?min_rr=3"
```

### Get Specific Date
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.mrktdly.com/swing-signals?date=2025-11-29"
```

## Deployment

```bash
./deploy-swing-scanner.sh
```

This will:
1. Update API Lambda with swing-signals endpoint
2. Deploy swing scanner Lambda
3. Upload website files to S3

## Cost Estimate

**One-time setup:**
- DynamoDB table creation: Free

**Daily operations:**
- Lambda execution (100 tickers, ~2 min): $0.0002
- DynamoDB writes (~10 signals/day): $0.00001
- DynamoDB storage (1MB): $0.00025/month
- API calls (100 users/day): Free tier

**Total: ~$0.01/month**

## Future Enhancements

1. **Additional Patterns:**
   - Bull/Bear flags
   - Ascending/descending triangles
   - Cup and handle
   - Head and shoulders

2. **Advanced Filters:**
   - Sector/industry
   - Market cap range
   - Average volume
   - Price range

3. **Alerts:**
   - Email notifications for new signals
   - SMS alerts for high R/R opportunities
   - Webhook integrations

4. **Backtesting:**
   - Historical pattern performance
   - Win rate by pattern type
   - Average R/R achieved

5. **Watchlist Integration:**
   - Add signals directly to portfolio
   - Track signal performance
   - Auto-close on target/stop hit
### 4. Momentum Alignment
RSI and MACD both bullish, price in strong uptrend:

**Criteria:**
- RSI > 55 (showing strength, not overbought)
- MACD above signal line (bullish crossover)
- Price above 20-day MA
- Price above 50-day MA (longer-term trend)
- R/R > 1.5

**Target:**
- 10% above current price (momentum continuation play)
### 5. Volume Breakout
Institutional accumulation with explosive volume:

**Criteria:**
- Volume 3x+ average for current day
- Previous day also had 2x+ volume (2 consecutive high-volume days)
- New 20-day high
- Price up on the day
- R/R > 1.5

**Target:**
- 15% above current price (strong momentum continuation)

**Why it works:**
- Catches institutional buying early
- High volume = conviction
- 2-day requirement filters out single-day spikes

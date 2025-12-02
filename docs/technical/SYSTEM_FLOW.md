# MrktDly System Flow

## Complete End-to-End Flow

### 1. Data Collection (Daily, 4:30 PM ET)
**Lambda:** `data_fetch`
- Triggered by EventBridge schedule after market close
- Fetches OHLCV data from Alpha Vantage API for ~100 tickers
- Stores in DynamoDB table: `mrktdly-price-history`
- Data includes: open, high, low, close, volume for each day

### 2. Signal Generation (Daily, 5:00 PM ET)
**Lambda:** `swing_scanner`
- Triggered 30 mins after data fetch
- Analyzes price history for each ticker
- Detects patterns:
  - MA20 pullback (price near 20-day moving average)
  - Consolidation breakout
  - Bull flags
  - Ascending triangles
  - Volume breakouts
- Calculates:
  - Entry price (current close)
  - Target price (+5% typical)
  - Stop loss (-3% typical)
  - Risk:Reward ratio
  - Support/resistance levels
- Stores signals in: `mrktdly-swing-signals` table
- Returns 5-10 best signals

### 3. Signal Tracking (Daily, 5:05 PM ET)
**Lambda:** `signal-tracker`
- Triggered after swing scanner
- Takes new signals and creates tracking records
- Stores in: `mrktdly-signal-performance` table
- Fields tracked:
  - ticker, signal_date, entry, target, stop_loss
  - status: OPEN/WIN/LOSS/EXPIRED
  - return_pct, days_held
  - conviction level

### 4. Signal Evaluation (Daily, 5:10 PM ET)
**Lambda:** `signal-evaluator`
- Checks all OPEN signals against latest prices
- For each signal:
  - If high >= target → mark as WIN
  - If low <= stop_loss → mark as LOSS
  - If > 10 days old → mark as EXPIRED
- Updates `mrktdly-signal-performance` table
- Calculates actual return percentage

### 5. Performance Stats (On-Demand via API)
**Lambda:** `signal-stats`
**Endpoint:** `GET /signal-stats?days=30`
- Queries last N days of signals
- Calculates:
  - Win rate (wins / total closed)
  - Average win/loss percentages
  - Expectancy (expected return per trade)
  - Risk:Reward ratio
  - Open vs closed signal counts
- Returns JSON for dashboard

### 6. Dashboard Display (Real-time)
**Website:** `performance.html` (CloudFront + S3)
- Loads on page visit
- Fetches from `/signal-stats` API
- Displays:
  - Overall performance (last 30 days)
  - Last month backtest results
  - Active signals with entry/target prices
  - Win rate, expectancy, R:R metrics
- Auto-refreshes data

## Data Flow Diagram

```
Market Close (4:00 PM)
    ↓
[EventBridge Schedule] → data_fetch Lambda
    ↓
Alpha Vantage API → Price Data
    ↓
DynamoDB: price-history table
    ↓
[EventBridge Schedule] → swing_scanner Lambda
    ↓
Pattern Detection → 5-10 Signals
    ↓
DynamoDB: swing-signals table
    ↓
[EventBridge Schedule] → signal-tracker Lambda
    ↓
DynamoDB: signal-performance table (OPEN)
    ↓
[EventBridge Schedule] → signal-evaluator Lambda
    ↓
Check prices → Update status (WIN/LOSS/EXPIRED)
    ↓
DynamoDB: signal-performance table (updated)
    ↓
[User visits dashboard]
    ↓
API Gateway → signal-stats Lambda
    ↓
Query signal-performance table
    ↓
Calculate metrics → Return JSON
    ↓
Dashboard displays results
```

## Key Tables

### mrktdly-price-history
```
ticker (PK) | date (SK) | open | high | low | close | volume
AAPL        | 2025-11-29| 270  | 275  | 268 | 273   | 50M
```

### mrktdly-swing-signals
```
date (PK)   | ticker (SK) | pattern | entry | target | stop_loss | risk_reward
2025-11-30  | SCHW        | ma20_pb | 92.73 | 100.15 | 89.35     | 2.19
```

### mrktdly-signal-performance
```
ticker (PK) | signal_date (SK) | entry | target | stop_loss | status | return_pct | days_held
META        | 2025-11-21       | 594.25| 623.96 | 576.42    | EXPIRED| 9.04       | 9
```

## Manual Operations

### Run Scanner Manually
```bash
aws lambda invoke --function-name mrktdly-swing-scanner --region us-east-1 output.json
```

### Run Backtest
```bash
cd /home/prakash/mrktdly
./backtest_last_month.py
```

### Check Performance
```bash
curl "https://xfi2u4ajm9.execute-api.us-east-1.amazonaws.com/prod/signal-stats?days=30"
```

### Deploy Dashboard
```bash
aws s3 cp website/performance.html s3://mrktdly-website/performance.html
aws cloudfront create-invalidation --distribution-id EFPX5INATD34D --paths "/performance.html"
```

## Current Performance (Last 30 Days)
- **31 signals** generated
- **90.3% win rate** (28 wins, 3 losses)
- **+3.5% avg win** | **-0.8% avg loss**
- **+0.64% expectancy** per trade
- **1.67:1 risk:reward** ratio

## Pattern Detection Logic

### MA20 Pullback
- Price within 2% of 20-day MA
- Uptrend (MA20 > MA50)
- Recent pullback (price < MA20)
- Volume confirmation

### Consolidation Breakout
- Price range < 5% for 10+ days
- Break above resistance
- Volume surge (>1.5x average)

### Bull Flag
- Strong uptrend (>10% in 5 days)
- Consolidation (3-7 days)
- Tight range (<3%)
- Break above flag high

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/signal-stats` | GET | Performance metrics |
| `/swing-scanner` | POST | Generate signals |
| `/ticker-analysis` | GET | Individual ticker analysis |

## Automation Schedule

| Time | Lambda | Action |
|------|--------|--------|
| 4:30 PM | data_fetch | Fetch daily prices |
| 5:00 PM | swing_scanner | Generate signals |
| 5:05 PM | signal-tracker | Track new signals |
| 5:10 PM | signal-evaluator | Evaluate open signals |

All times Eastern, Monday-Friday only.

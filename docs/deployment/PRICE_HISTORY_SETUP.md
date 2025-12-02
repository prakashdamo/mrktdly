# Price History Storage Setup

## Overview
This adds historical price storage to enable future features like charts, backtesting, screeners, and more.

## What It Does
- Stores daily OHLCV (Open, High, Low, Close, Volume) data for all 135+ tracked tickers
- Runs automatically every day with the data-fetch Lambda
- Enables historical queries without hitting Yahoo Finance API

## Setup Instructions

### Step 1: Authenticate AWS
```bash
# If your session expired, re-authenticate
aws configure
# Or if using SSO:
aws sso login
```

### Step 2: Run Setup Script
```bash
cd /home/prakash/mrktdly
./setup-price-history.sh
```

This will:
1. Create `mrktdly-price-history` DynamoDB table
2. Deploy updated `mrktdly-data-fetch` Lambda
3. Trigger a test run

### Step 3: Backfill Historical Data (Optional but Recommended)
```bash
cd lambda/data_fetch
python3 backfill_history.py
```

This will:
- Fetch 5 years of historical data for all tickers
- Store ~65,000 records (135 tickers × ~1,260 trading days)
- Take ~5 minutes (rate limited to 2 seconds per ticker)

## Table Schema

**Table**: `mrktdly-price-history`

**Keys**:
- Partition Key: `ticker` (String) - e.g., "AAPL"
- Sort Key: `date` (String) - e.g., "2025-11-29"

**Attributes**:
- `open` (Decimal) - Opening price
- `high` (Decimal) - Day's high
- `low` (Decimal) - Day's low
- `close` (Decimal) - Closing price
- `volume` (Number) - Trading volume
- `adj_close` (Decimal) - Adjusted close (same as close for now)
- `timestamp` (String) - When record was created

## Query Examples

### Get last 90 days for a ticker
```python
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta

end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

response = price_history_table.query(
    KeyConditionExpression=Key('ticker').eq('AAPL') & Key('date').between(start_date, end_date)
)
prices = response['Items']
```

### Get specific date for all tickers
```python
# Use GSI (if created) or scan with filter
response = price_history_table.scan(
    FilterExpression=Attr('date').eq('2025-11-29')
)
all_prices = response['Items']
```

### Get price on specific date
```python
response = price_history_table.get_item(
    Key={'ticker': 'AAPL', 'date': '2025-11-29'}
)
price = response['Item']
```

## Cost Estimate

**Storage**:
- Year 1: 135 tickers × 252 days × 200 bytes = 6.8 MB = $0.002/month
- Year 5: 34 MB = $0.010/month

**Reads** (assuming 1000 users):
- Historical charts: 500 queries/day = $0.0001/day
- Backtesting: 200 queries/day = $0.00005/day
- Total: ~$0.005/month

**Writes**:
- Daily: 135 writes/day = $0.0002/day = $0.006/month

**Total: ~$0.02/month** (basically free)

## What This Enables

### Immediate
- ✅ Daily price storage (automatic)
- ✅ Historical data available for queries

### Short-term (Week 1-2)
- 📈 Historical price charts on ticker analysis page
- 📊 Portfolio performance tracking over time
- 🔄 Faster backtesting (no Yahoo API calls)

### Medium-term (Month 1-2)
- 🔍 Stock screener (momentum, volume, breakouts)
- 📉 Sector performance history
- 🎯 Support/resistance level detection
- 🔗 Correlation analysis

### Long-term (Month 3+)
- 📅 Seasonality analysis
- 💪 Relative strength rankings
- 🌡️ Market regime detection
- ⚖️ Portfolio rebalancing suggestions

## Verification

Check that data is being stored:
```bash
# View recent records
aws dynamodb scan \
  --table-name mrktdly-price-history \
  --limit 5 \
  --region us-east-1

# Count total records
aws dynamodb scan \
  --table-name mrktdly-price-history \
  --select COUNT \
  --region us-east-1

# Query specific ticker
aws dynamodb query \
  --table-name mrktdly-price-history \
  --key-condition-expression "ticker = :ticker" \
  --expression-attribute-values '{":ticker":{"S":"AAPL"}}' \
  --limit 10 \
  --region us-east-1
```

## Troubleshooting

### Table creation fails
- Check AWS credentials: `aws sts get-caller-identity`
- Verify region: `us-east-1`
- Check if table already exists: `aws dynamodb list-tables --region us-east-1`

### Lambda update fails
- Check function exists: `aws lambda list-functions --region us-east-1 | grep mrktdly-data-fetch`
- Verify zip file: `ls -lh lambda/data_fetch/lambda.zip`

### Backfill script fails
- Install boto3: `pip install boto3`
- Check AWS credentials
- Verify table exists
- Check rate limits (script has 2-second delays)

### No data appearing
- Trigger Lambda manually: `aws lambda invoke --function-name mrktdly-data-fetch --region us-east-1 /tmp/response.json`
- Check Lambda logs: `aws logs tail /aws/lambda/mrktdly-data-fetch --follow --region us-east-1`
- Verify table permissions in Lambda IAM role

## Next Steps

After setup is complete:
1. Let it run for a week to collect daily data
2. Build historical chart feature (Week 2)
3. Add portfolio performance tracking (Week 3)
4. Implement stock screener (Week 4)

## Rollback

If you need to remove this feature:
```bash
# Delete table
aws dynamodb delete-table --table-name mrktdly-price-history --region us-east-1

# Revert Lambda code
cd lambda/data_fetch
git checkout lambda_function.py
zip lambda.zip lambda_function.py
aws lambda update-function-code --function-name mrktdly-data-fetch --zip-file fileb://lambda.zip --region us-east-1
```

---

**Questions?** Check Lambda logs or DynamoDB console for debugging.

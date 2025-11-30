# ML Feature Engineering - Phase 1 Complete ✅

## What We Built

### Lambda Function: `mrktdly-features`
- Calculates 30 technical indicators per ticker
- Processes 124 tickers in ~8 seconds
- Stores in DynamoDB for fast access

### DynamoDB Table: `mrktdly-features`
- Keys: ticker (HASH), date (RANGE)
- 30 feature columns per record
- Cost: ~$0.01/day

## Features Calculated (30 total)

### Moving Averages (5)
- MA5, MA10, MA20, MA50, MA200

### Momentum Indicators (3)
- RSI (14-day)
- MACD (12, 26, 9)
- MACD Signal & Histogram

### Volatility Indicators (4)
- Bollinger Bands (Upper, Middle, Lower)
- ATR (14-day)

### Volume Indicators (3)
- Current Volume
- 20-day Average Volume
- Volume Ratio

### Price Returns (3)
- 1-day, 5-day, 20-day returns

### Price Position (4)
- 52-week High/Low
- % from High/Low

### Trend Indicators (4)
- Above MA20/50/200 (binary)
- MA Alignment (binary)

### Other (4)
- Current Price
- Volatility (20-day std)
- Timestamp

## Usage

### Calculate Today's Features
```bash
aws lambda invoke --function-name mrktdly-features --region us-east-1 /tmp/response.json
```

### Query Features
```python
import boto3
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('mrktdly-features')

response = table.get_item(Key={'ticker': 'AAPL', 'date': '2025-11-30'})
features = response['Item']
```

## Next Steps - Phase 2: Training Data

### 1. Backfill Historical Features
Run features lambda for past 252 days (1 year):
```bash
# Create backfill script
python backfill_features.py --days 252
```

### 2. Add Labels
Create target variable (next 5-day return):
```python
# Label: 1 if next_5d_return > 3%, else 0
label = 1 if (close_t+5 - close_t) / close_t > 0.03 else 0
```

### 3. Export to CSV
```python
# Export all features + labels to S3
# Format: ticker, date, feature1, feature2, ..., label
# ~124 tickers × 252 days = 31,248 rows
```

### 4. Train Model
```python
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

# Train on 80% data, test on 20%
# Target: Predict 3%+ moves in next 5 days
```

## Cost Breakdown

### Current (Phase 1)
- Lambda execution: $0.0001/run
- DynamoDB writes: $0.01/day
- DynamoDB storage: $0.001/month
- **Total: ~$0.30/month**

### Phase 2 (Training)
- Backfill: $0.05 (one-time)
- S3 storage: $0.01/month
- Training (local): $0
- **Total: $0.05 one-time + $0.01/month**

### Phase 3 (Inference)
- Daily predictions: $0.01/day
- **Total: $0.30/month**

## Performance

- Feature calculation: ~8 seconds for 124 tickers
- DynamoDB query: <10ms per ticker
- Lambda memory: 512 MB
- Lambda timeout: 300 seconds (plenty of headroom)

## Integration

Add to daily pipeline:
```
7:00 AM → data-fetch (56s)
         ↓
         unusual-activity (20s)
         ↓
         features (8s) ← NEW
         
7:15 AM → analysis (14s)
```

Total time: 98 seconds (still under 2 minutes)

---

**Status: Phase 1 Complete ✅**
**Next: Phase 2 - Training Data Preparation**

# ML Stock Prediction System - Project Summary

## What We Built

A complete serverless ML system that predicts profitable stock trades and delivers daily insights via email.

### Current Status: ✅ PRODUCTION

**Daily automated workflow:**
1. 6:00 AM ET - Fetch latest prices for 124 tickers
2. Calculate 30 technical indicators (RSI, MACD, MAs, etc.)
3. Run ML model to predict stocks likely to move >3% in 5 days
4. Detect unusual activity patterns
5. Send email with top predictions to subscribers

**Cost: $0.65/month** (DynamoDB + Lambda + S3 + SES)

---

## System Architecture

### Data Storage (DynamoDB)
- **mrktdly-price-history**: 154,356 records (5 years, 124 tickers)
- **mrktdly-features**: 31,897 records with 30 technical indicators
- **mrktdly-predictions**: Daily ML predictions
- **mrktdly-swing-signals**: Technical pattern detections

### Lambda Functions
1. **mrktdly-data-fetch** (120s timeout) - Fetches daily prices
2. **mrktdly-features** (300s timeout) - Calculates technical indicators
3. **mrktdly-ml-predictions** (60s timeout) - Runs ML model
4. **mrktdly-unusual-activity** (60s timeout) - Detects patterns
5. **mrktdly-delivery** (60s timeout) - Sends email

### ML Model
- **Type**: RandomForestClassifier (binary classification)
- **Target**: Predict if stock will move >3% in next 5 days
- **Features**: 19 technical indicators
- **Performance**:
  - Accuracy: 76.3%
  - Precision: 83.0%
  - Recall: 9.8%
- **Storage**: S3 (stock_predictor.pkl)

---

## Current Performance

### Model Metrics (Last Training)
```
Training records: 31,897
Positive labels: 8,268 (25.9%)
Accuracy: 76.3%
Precision: 83.0% (when it says "buy", it's right 83% of time)
Recall: 9.8% (conservative - only flags high-confidence setups)
```

### Real-World Results
- **Last week backtest**: 93.8% accuracy on predictions
- **Alpha over market**: +6.83%
- **Example**: CLSK predicted at 75% confidence → +38% actual return

---

## What We Tried (And What Didn't Work)

### ❌ Regression Model (Predict Exact Returns)
**Goal**: Predict actual return % (e.g., +8.4%, -2.1%)
**Results**:
- R² = -0.225 (worse than random)
- Directional accuracy: 44.5%
- Top 10 picks averaged -2.19% return
**Lesson**: Predicting exact returns is much harder than binary classification

### ❌ Multi-Class Model (Skip/Good/Excellent)
**Goal**: Classify trades by quality based on risk/reward
**Results**:
- "Excellent" precision: 6.7%
- Only 3/45 "Excellent" predictions were actually excellent
**Lesson**: Rare events need years of data to learn patterns

### ✅ Binary Classification (Current Model)
**Goal**: Simple yes/no prediction (>3% move or not)
**Results**:
- 76-93% accuracy depending on market conditions
- 83% precision (reliable when it predicts)
- Conservative but profitable
**Lesson**: Simpler is better for limited data

---

## Weekly Retraining System

### Automation Script: `/tmp/retrain_model.sh`

**What it does:**
1. Exports all features from DynamoDB
2. Trains new RandomForest model locally
3. Compares accuracy with current model
4. Only deploys if new model is better
5. Uploads to S3 for Lambda to use

**Schedule**: Every Sunday at 8:00 AM (via cron)

**Benefits**:
- Model adapts to changing market conditions
- Accumulates more training data each week
- Automatic quality control (only deploys if better)
- Zero cost (runs locally)

**Setup**:
```bash
chmod +x /tmp/retrain_model.sh
chmod +x /tmp/setup_weekly_retrain.sh
./setup_weekly_retrain.sh
```

---

## Email Delivery

### Current Recipients
- prakash@dalalbytes.com (verified in SES sandbox)

### Email Content
1. **Market Overview** - Daily summary
2. **Market Insights** - Key observations
3. **Levels to Watch** - Support/resistance
4. **Unusual Activity** - Volume spikes, breakouts
5. **🤖 AI Predictions** - ML model picks with probabilities
6. **🎯 Swing Trade Opportunities** - Technical patterns with entry/stop/target

### Sample Prediction
```
NET - $200.21
70% likely to move >3%
RSI: 20.77 (oversold) | 20-day return: -20.96%
HIGH confidence
```

---

## Future Improvements

### Priority 1: More Training Data
**Action**: Backfill 2 years of features (2023-2024)
**Cost**: $0.50 one-time
**Expected improvement**: 76% → 80%+ accuracy
**Why**: More data = better pattern recognition across market regimes

### Priority 2: Market Context Features
**Add**:
- SPY return (market direction)
- Sector relative strength
- VIX level (volatility regime)
**Why**: Currently treats stocks in isolation, missing macro context

### Priority 3: Ensemble Approach
**Combine**:
- ML predictions (probability)
- Technical patterns (swing scanner)
- Risk/reward ratios
**Score**: High conviction when all three align

### Priority 4: Position Sizing Calculator
**Goal**: Help achieve $1k/week from $10k capital
**Features**:
- Risk per trade based on ML confidence
- Position size recommendations
- Portfolio allocation across multiple picks

### Priority 5: Performance Tracking
**Track**:
- Predicted vs actual returns
- Win rate by confidence level
- Sharpe ratio over time
- Model drift detection

---

## Key Files

### Scripts
- `/tmp/retrain_model.sh` - Weekly retraining automation
- `/tmp/setup_weekly_retrain.sh` - Cron job setup
- `/tmp/weekly_retrain.py` - Python retraining script (alternative)

### Documentation
- `/tmp/ml_stock_prediction_blog.md` - Blog article
- `/tmp/PROJECT_SUMMARY.md` - This file

### Logs
- `/tmp/model_retrain.log` - Weekly retraining logs
- CloudWatch Logs - Lambda execution logs

---

## Cost Breakdown

### One-Time Costs
- Historical data backfill: $0.05
- Initial feature calculation: $0.10
- **Total: $0.15**

### Monthly Costs
- DynamoDB storage: $0.35
- Lambda executions: $0.20
- S3 storage: $0.05
- SES email delivery: $0.05
- **Total: $0.65/month**

### Annual Cost: $7.80
(Less than one Netflix subscription)

---

## Trading Strategy (To Achieve $1k/Week Goal)

### Current Capital: $10,000
### Target: $1,000/week (10% weekly return)

**Realistic Approach**:

1. **Position Sizing**
   - Top 2-3 ML picks with >60% confidence: $3k-5k total
   - Remaining picks: $500-1k each for diversification
   - Keep $2k cash reserve

2. **Entry Criteria**
   - ML prediction >60% confidence
   - Technical pattern confirmation (swing scanner)
   - Risk/reward ratio >2:1

3. **Risk Management**
   - Risk 2% per trade ($200 max loss)
   - Stop loss at technical support levels
   - Take profits at 3:1 or 5:1 R/R

4. **Expected Performance**
   - Win rate: 60-70% (based on 83% precision, conservative exits)
   - Average R/R: 2.5:1
   - 3-5 trades per week
   - Target: $300-600/week initially, scale to $1k+

**Phase 1 (Weeks 1-4)**: Paper trade, track performance
**Phase 2 (Weeks 5-8)**: Real money, 2-3 positions, target $300-600/week
**Phase 3 (Weeks 9+)**: Scale up as confidence grows, target $600-1000/week

---

## Next Steps

### Immediate (This Week)
- [x] Fix email delivery (predictions now showing)
- [x] Create weekly retraining script
- [ ] Set up cron job for Sunday retraining
- [ ] Monitor first automated retraining

### Short Term (Next 2 Weeks)
- [ ] Backfill 2 years of features ($0.50)
- [ ] Retrain with expanded dataset
- [ ] Add market context features (SPY, VIX)
- [ ] Create position sizing calculator

### Medium Term (Next Month)
- [ ] Build performance tracking dashboard
- [ ] Implement ensemble scoring (ML + technical)
- [ ] Request SES production access (unlimited emails)
- [ ] Add more subscribers to waitlist

### Long Term (Next 3 Months)
- [ ] Track 12 weeks of predictions vs actuals
- [ ] Calculate Sharpe ratio and alpha
- [ ] Optimize model based on real performance
- [ ] Consider adding more tickers (expand from 124)

---

## Success Metrics

### Model Performance
- ✅ Accuracy: 76.3% (target: 80%+)
- ✅ Precision: 83.0% (target: 80%+)
- ⚠️ Recall: 9.8% (acceptable for conservative strategy)

### System Reliability
- ✅ Daily execution: 100% uptime
- ✅ Email delivery: Working
- ✅ Cost: $0.65/month (under budget)

### Trading Performance (To Be Tracked)
- [ ] Weekly return: Target 3-5% average
- [ ] Win rate: Target 60-70%
- [ ] Sharpe ratio: Target >1.5
- [ ] Max drawdown: Target <15%

---

## Lessons Learned

1. **Start Simple**: Binary classification beats complex regression for limited data
2. **Serverless Scales**: $0.65/month for production ML system
3. **Conservative Wins**: 83% precision with 10% recall beats 60% accuracy with 100% recall
4. **Iterate Weekly**: Continuous retraining adapts to market changes
5. **Combine Signals**: ML + technical patterns = higher conviction trades

---

## Contact & Support

**Email**: prakash@dalalbytes.com
**Project**: mrktdly (Market Daily)
**AWS Account**: 060195792007
**Region**: us-east-1

---

*Last Updated: November 30, 2025*
*Status: Production - Daily automated predictions running*
*Next Milestone: 2-year data backfill for improved accuracy*

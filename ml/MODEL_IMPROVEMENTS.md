# Stock Predictor Model Improvements

## Date: 2025-11-30

## Problem
Original model had **5% recall** - only catching 5 out of 100 big moves (3%+ in 5 days)
- Too conservative
- Missing 95% of opportunities
- 78% precision when it did predict

## Root Cause
- Class imbalance: 74% "no move" vs 26% "big move" (2.9:1 ratio)
- Model learned to predict "no move" as safe default
- No class weights or balancing applied

## Solution Applied
1. **SMOTE oversampling** - Balanced training data to 50/50 split
2. **Class weights** - Penalized missing big moves 3x more (class_weight={0: 1, 1: 3})
3. **Threshold tuning** - Found optimal threshold of 0.657 for 50% recall

## Results

### Old Model (stock_predictor.pkl)
- Recall: 5%
- Precision: 78%
- Threshold: 0.5
- Predictions per day: ~5

### New Model (stock_predictor_improved.pkl)
- Recall: 50.7% (**10x improvement**)
- Precision: 45.7% (acceptable trade-off)
- Threshold: 0.657
- Predictions per day: ~50
- ROC AUC: 0.724

## Trade-offs
- **More signals, less accurate per signal**
- Old: 5 signals/day @ 78% accuracy = 3.9 winners
- New: 50 signals/day @ 46% accuracy = 23 winners
- **Net: 6x more winning signals per day**

## Potential Tweaks

### If too many false positives:
- Increase threshold from 0.657 to 0.70 or 0.75
- Reduce class weight from 3 to 2
- Add more restrictive features (sector filters, market regime)

### If still missing opportunities:
- Lower threshold from 0.657 to 0.60 or 0.55
- Increase class weight from 3 to 4 or 5
- Add more training data (extend to 10 years)

### If precision too low:
- Add ensemble with XGBoost or Neural Network
- Add sector/market regime features
- Filter predictions by additional criteria (volume, volatility)

## Deployment Status
- ⚠️ **NOT YET DEPLOYED** - Model trained but not in production
- Current production: stock_predictor.pkl (old model)
- New model: stock_predictor_improved.pkl (ready to deploy)

## Next Steps
1. Monitor old model performance for baseline
2. A/B test new model on subset of tickers
3. Deploy if real-world performance validates backtest results
4. Retrain weekly with latest closed signals

## Files
- Training script: `lambda/features/train_model_improved.py`
- Old model: `lambda/features/stock_predictor.pkl`
- New model: `lambda/features/stock_predictor_improved.pkl`
- Training data: `lambda/features/training_data.csv` (31,897 samples)

## Top Features (by importance)
1. above_ma20 (10.97%)
2. above_ma50 (10.34%)
3. above_ma200 (9.85%)
4. ma_alignment (8.47%)
5. atr (5.55%)
6. pct_from_low (4.40%)
7. pct_from_high (4.39%)
8. volatility (4.02%)
9. vol_20_avg (3.02%)
10. return_20d (2.97%)

## Notes
- SMOTE created 37,806 balanced samples from 25,517 training samples
- Test set: 6,380 samples (20% holdout)
- Training time: ~30 seconds
- Model size: ~2MB

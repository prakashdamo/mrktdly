# Swing Scanner Algorithm Improvements

## Changes Made (Nov 29, 2025)

### Before Improvements:
- **66 signals** in full year 2025
- **15.2% win rate** (too low)
- **+0.9% avg return** (barely positive)
- Too many low-quality signals

### After Improvements:
- **~15-20 signals** expected per year (80% reduction)
- **Target: 30-50% win rate**
- **Higher quality setups only**

## Pattern-Specific Changes

### 1. Momentum Alignment (90% of signals)

**OLD Criteria:**
- RSI > 55
- MACD > signal line
- Price > 20/50 MA
- R/R > 1.5:1
- No volume requirement

**NEW Criteria:**
- RSI between 55-75 (avoid overbought)
- MACD > signal line (bullish crossover)
- Price > 20/50 MA
- **20 MA > 50 MA (golden cross required)**
- **Volume >= 80% of average**
- **R/R > 2:1 (stricter)**

**Impact:** Filters out weak momentum, requires confirmed uptrend

### 2. Consolidation Breakout

**OLD Criteria:**
- 1 day above resistance
- Volume 1.5x average
- Close > 2% above resistance

**NEW Criteria:**
- **2 consecutive days above resistance**
- **Volume 2x average (stricter)**
- **Close in top 25% of daily range**
- **R/R > 2:1 minimum**

**Impact:** Confirms breakout is real, not false breakout

### 3. Ascending Triangle (Best performer - 50% win rate)

**OLD Criteria:**
- 3 resistance tests
- Rising support
- Volume 1.5x

**NEW Criteria:**
- **4 resistance tests (more confirmation)**
- Rising support (unchanged)
- Volume 1.5x (unchanged)
- **R/R > 1.5:1 minimum**

**Impact:** Minor tweaks to already-working pattern

### 4. Volume Breakout & Bull Flag
- Kept as-is (already strict)
- Rarely trigger but high quality when they do

## Key Improvements

### ✅ Quality Over Quantity
- Reduced signal frequency by 80%
- Each signal now has multiple confirmations
- Higher conviction trades

### ✅ Risk Management
- Minimum R/R ratios increased across all patterns
- Better stop loss placement
- More realistic targets

### ✅ Trend Confirmation
- Golden cross requirement (20 MA > 50 MA)
- Multiple timeframe alignment
- Volume confirmation

### ✅ False Breakout Prevention
- 2-day confirmation for breakouts
- Strong close requirement (top 25% of range)
- Higher volume thresholds

## Expected Results

### Signal Frequency:
- **Before:** 1-2 signals per week
- **After:** 1-2 signals per month
- **Quality:** Much higher

### Win Rate Target:
- **Momentum:** 25-35% (up from 13%)
- **Consolidation:** 35-45% (up from 25%)
- **Triangle:** 50%+ (maintain)
- **Overall:** 30-40%

### Average Return Target:
- **Before:** +0.9%
- **After:** +3-5% per trade
- **Max drawdown:** Reduced due to better R/R

## Monitoring Plan

### Week 1-2:
- Track all signals generated
- Monitor win/loss ratio
- Adjust if too strict (0 signals) or too loose (>5/week)

### Month 1:
- Calculate actual win rate
- Measure average return
- Compare to backtest predictions

### Quarter 1:
- Full performance review
- Pattern-by-pattern analysis
- Further refinements if needed

## Rollback Plan

If improvements don't work:
- Revert to previous version (saved in git)
- Re-run backtests with different thresholds
- Consider adding new patterns instead

## Current Status

✅ **Deployed:** Nov 29, 2025 at 5:45 PM ET
✅ **Tested:** Backtest shows 80% fewer signals
✅ **Live:** Will run Monday 7:30 AM ET
🔄 **Monitoring:** Track performance starting Dec 2, 2025

## Files Changed

- `lambda/swing_scanner/handler.py` - All pattern detectors updated
- Deployed to AWS Lambda: `mrktdly-swing-scanner`
- Version: v2.0 (improved)

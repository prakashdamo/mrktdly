# Backtest Tool - Implementation Discussion

## 🎯 Feature Overview

Allow users to backtest different trading strategies on any stock to see historical performance.

---

## 🤔 KEY QUESTIONS TO DISCUSS

### 1. **User Interface / Experience**

**Option A: Simple Form**
```
Ticker: [PLTR ▼]
Start Date: [2025-01-01]
End Date: [2025-12-02]
Strategy: [Buy & Hold ▼]
Capital: [$10,000]
[Run Backtest]
```

**Option B: Interactive Chart**
- Click on chart to set entry/exit points
- Drag sliders for dates
- Real-time results as you adjust

**Option C: Wizard Flow**
- Step 1: Choose stock
- Step 2: Choose dates
- Step 3: Choose strategy
- Step 4: See results

**Question:** Which UX do we prefer?
**Recommendation:** Start with Option A (simple), add Option B later

---

### 2. **Strategies to Support**

**Phase 1 (MVP):**
- ✅ Buy & Hold
- ✅ Swing Trading (buy dips, sell rallies)
- ✅ MA Crossover (10/50 day)
- ✅ RSI Strategy (30/70)
- ✅ Momentum (20-day)

**Phase 2 (Future):**
- Stop Loss (user-defined %)
- Take Profit (user-defined %)
- DCA (Dollar Cost Averaging)
- Rebalancing
- Custom (user defines rules)

**Question:** Is Phase 1 enough for MVP?
**Recommendation:** Yes, 5 strategies is good starting point

---

### 3. **Results Display**

**What to show:**
```
Strategy: Buy & Hold
Period: Jan 1, 2025 - Dec 2, 2025
Starting Capital: $10,000

Results:
✅ Final Value: $22,276
✅ Profit: $12,276
✅ ROI: +122.76%
✅ Number of Trades: 1
✅ Win Rate: 100%
✅ Max Drawdown: -12.2%

Trade History:
Jan 2, 2025: BUY 131.23 shares @ $76.20
Dec 2, 2025: HOLD @ $167.49

[Chart showing equity curve]
[Compare with other strategies]
```

**Question:** What else should we show?
**Ideas:**
- Sharpe ratio?
- Volatility?
- Best/worst trade?
- Monthly returns?

**Recommendation:** Keep it simple for MVP, add advanced metrics later

---

### 4. **Performance / Caching**

**Challenge:** Backtests can be slow (need to process 252 days of data)

**Option A: Real-time Calculation**
- Calculate on-demand
- Pros: Always fresh, no storage
- Cons: Slow (2-5 seconds), expensive compute

**Option B: Pre-calculated Cache**
- Run backtests nightly for popular stocks
- Store results in DynamoDB
- Pros: Instant results
- Cons: Storage cost, stale data

**Option C: Hybrid**
- Cache popular stocks (PLTR, TSLA, etc.)
- Calculate on-demand for others
- Cache result for 24 hours

**Question:** Which approach?
**Recommendation:** Option C (hybrid) - best of both worlds

---

### 5. **Data Requirements**

**Minimum data needed:**
- 252 trading days (1 year) for 1-year backtest
- 504 days for 2-year backtest
- etc.

**Question:** What date ranges to support?
**Options:**
- Last 30 days
- Last 90 days
- Last 6 months
- Last 1 year
- Last 2 years
- Custom range

**Recommendation:** Support all, but default to "Last 1 year"

---

### 6. **Comparison Feature**

**Should users be able to compare strategies side-by-side?**

**Example:**
```
Compare Results for PLTR (2025):

Strategy          ROI      Profit    Trades
Buy & Hold       +122.8%  $12,276      1
Swing Trading    +109.4%  $10,938      8
MA Crossover     +51.1%   $5,113       2
RSI Strategy     +61.6%   $6,157       3
Momentum         +26.1%   $2,612       7

Winner: Buy & Hold 🏆
```

**Question:** Include comparison in MVP?
**Recommendation:** YES - this is the killer feature

---

### 7. **Mobile Experience**

**Challenge:** Backtests generate lots of data (charts, tables)

**Question:** How to handle on mobile?
**Options:**
- Simplified mobile view (just key metrics)
- Full desktop experience (scrollable)
- Mobile app required for full features

**Recommendation:** Simplified mobile view for MVP

---

### 8. **Rate Limiting**

**Challenge:** Users could spam backtests (expensive compute)

**Question:** How to limit usage?
**Options:**
- Free: 5 backtests per day
- Pro: 50 backtests per day
- Premium: Unlimited

**Or:**
- Free: Only pre-cached results
- Pro: On-demand backtests

**Recommendation:** 10 backtests/day for free, unlimited for Pro

---

### 9. **Educational Component**

**Should we explain WHY a strategy won/lost?**

**Example:**
```
Why Buy & Hold won for PLTR:
✅ Strong uptrend (+122% in 2025)
✅ No major corrections
✅ Active trading missed gains

Why Swing Trading lost:
❌ Sold too early (missed 50% of gains)
❌ Transaction costs reduced returns
❌ Timing was difficult

Lesson: Buy & Hold works best in strong uptrends
```

**Question:** Include educational insights?
**Recommendation:** YES - adds huge value, differentiates us

---

### 10. **API / Programmatic Access**

**Question:** Should we offer API access for backtests?
**Use case:** Power users, algo traders, researchers

**Recommendation:** Not for MVP, but plan for it (Phase 3)

---

## 🏗️ TECHNICAL ARCHITECTURE

### Lambda Function: `backtest-engine`

**Input:**
```json
{
  "ticker": "PLTR",
  "start_date": "2025-01-01",
  "end_date": "2025-12-02",
  "strategy": "buy_hold",
  "capital": 10000
}
```

**Output:**
```json
{
  "ticker": "PLTR",
  "strategy": "buy_hold",
  "period": "2025-01-01 to 2025-12-02",
  "starting_capital": 10000,
  "final_value": 22276,
  "profit": 12276,
  "roi": 122.76,
  "trades": [...],
  "equity_curve": [...],
  "max_drawdown": -12.2,
  "win_rate": 100
}
```

### DynamoDB Table: `mrktdly-backtests`

**Schema:**
```
ticker (HASH)
strategy_date (RANGE) - e.g., "buy_hold_2025-01-01_2025-12-02"
result (JSON)
timestamp
ttl (24 hours)
```

### Frontend Component: `BacktestTool.jsx`

**Features:**
- Form for inputs
- Results display
- Comparison table
- Equity curve chart
- Trade history table

---

## 💰 COST ESTIMATE

**Per backtest:**
- Lambda execution: $0.0001 (1 second @ 512MB)
- DynamoDB read: $0.00001 (250 items)
- DynamoDB write: $0.00001 (cache result)
- **Total: ~$0.00012 per backtest**

**At scale:**
- 1,000 backtests/day = $0.12/day = $3.60/month
- 10,000 backtests/day = $1.20/day = $36/month

**Very affordable!**

---

## 📅 IMPLEMENTATION TIMELINE

### Week 1: Core Engine
- [ ] Lambda function with 5 strategies
- [ ] DynamoDB table setup
- [ ] Unit tests

### Week 2: API & Caching
- [ ] API Gateway endpoint
- [ ] Caching logic
- [ ] Rate limiting

### Week 3: Frontend
- [ ] Backtest form
- [ ] Results display
- [ ] Comparison table

### Week 4: Polish
- [ ] Charts (equity curve)
- [ ] Educational insights
- [ ] Mobile optimization

**Total: 4 weeks for full implementation**

---

## 🎯 MVP SCOPE (2 weeks)

**Must Have:**
- ✅ 5 strategies (buy_hold, swing, ma_crossover, rsi, momentum)
- ✅ 1-year backtests
- ✅ Basic results (ROI, profit, trades)
- ✅ Comparison table
- ✅ Caching for popular stocks

**Nice to Have (defer):**
- Charts
- Educational insights
- Custom date ranges
- Advanced metrics

---

## 🚀 LAUNCH STRATEGY

**Phase 1: Soft Launch**
- Enable for Pro users only
- Gather feedback
- Fix bugs

**Phase 2: Public Beta**
- Open to all users (with rate limits)
- Promote on social media
- Monitor usage

**Phase 3: Full Launch**
- Add advanced features
- API access
- Mobile app integration

---

## ❓ OPEN QUESTIONS FOR DISCUSSION

1. **UX:** Simple form vs interactive chart?
2. **Strategies:** 5 enough or need more?
3. **Caching:** Which stocks to pre-cache?
4. **Rate Limits:** 10/day for free users?
5. **Mobile:** Simplified view or full features?
6. **Education:** Include "why" explanations?
7. **Comparison:** Side-by-side or separate?
8. **Date Ranges:** Support custom or predefined only?
9. **Metrics:** Basic or advanced (Sharpe, etc.)?
10. **Launch:** Pro-only first or public beta?

---

## 💡 RECOMMENDATIONS

**For MVP (2 weeks):**
1. Simple form UX
2. 5 strategies (buy_hold, swing, ma_crossover, rsi, momentum)
3. Hybrid caching (popular stocks pre-cached)
4. 10 backtests/day for free users
5. Simplified mobile view
6. Basic educational insights
7. Side-by-side comparison table
8. Predefined date ranges (30d, 90d, 1y)
9. Basic metrics (ROI, profit, trades, max drawdown)
10. Public beta launch (all users)

**This gives us:**
- Fast time to market (2 weeks)
- Core value delivered
- Room to iterate based on feedback
- Low cost to operate

---

## 🎉 SUCCESS CRITERIA

**Metrics to track:**
- Backtests run per day
- Most popular strategies
- Most backtested stocks
- User engagement (time on page)
- Conversion to Pro (if gated)
- User feedback/ratings

**Goal:**
- 100+ backtests/day within first month
- 4+ star rating from users
- 10%+ conversion to Pro (if gated)

---

## 📝 NEXT STEPS

1. **Review this document** - discuss open questions
2. **Finalize scope** - what's in MVP vs later
3. **Create tickets** - break down into tasks
4. **Assign work** - who builds what
5. **Set timeline** - commit to launch date
6. **Build!** 🚀

---

**Ready to discuss? Let's align on the approach!**

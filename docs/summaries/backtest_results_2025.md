# Comprehensive Backtest Results - 2025

**Period:** January 1, 2025 - December 2, 2025  
**Starting Capital:** $10,000  
**Strategies Tested:** Buy & Hold, MA Crossover (20/50), RSI (30/70)

## Executive Summary

- **Best Overall Return:** PLTR Buy & Hold (+119.8%)
- **Best Risk-Adjusted:** GOOGL MA Crossover (Sharpe 3.26)
- **Worst Performer:** HIMS MA Crossover (-50.9%)
- **Most Consistent:** SPY across all strategies (14-16%)

## Individual Stock Results

### PLTR (Palantir)
| Strategy | Final Value | ROI | Trades | Max Drawdown | Sharpe | $5 Fee Impact |
|----------|-------------|-----|--------|--------------|--------|---------------|
| Buy & Hold | $21,980 | +119.8% | 1 | 40.6% | 1.62 | -0.11% |
| MA Crossover | $13,619 | +36.2% | 4 | 25.3% | 1.02 | -0.21% |
| RSI | $12,144 | +21.4% | 3 | 3.2% | 1.99 | -0.17% |

**Winner:** Buy & Hold  
**Key Insight:** Strong uptrend favors buy & hold. RSI had lowest drawdown (3.2%) but missed the big gains.

### GOOGL (Google)
| Strategy | Final Value | ROI | Trades | Max Drawdown | Sharpe | $5 Fee Impact |
|----------|-------------|-----|--------|--------------|--------|---------------|
| Buy & Hold | $16,517 | +65.2% | 1 | 29.9% | 1.85 | -0.08% |
| MA Crossover | $18,908 | +89.1% | 1 | 7.5% | 3.26 | -0.09% |
| RSI | $13,198 | +32.0% | 4 | 7.8% | 1.72 | -0.23% |

**Winner:** MA Crossover  
**Key Insight:** MA Crossover caught the trend early and avoided the worst drawdown. Best Sharpe ratio (3.26).

### TSLA (Tesla)
| Strategy | Final Value | ROI | Trades | Max Drawdown | Sharpe | $5 Fee Impact |
|----------|-------------|-----|--------|--------------|--------|---------------|
| Buy & Hold | $11,026 | +10.3% | 1 | 48.2% | 0.53 | -0.06% |
| MA Crossover | $12,982 | +29.8% | 4 | 21.5% | 0.93 | -0.23% |
| RSI | $13,111 | +31.1% | 3 | 15.7% | 1.36 | -0.18% |

**Winner:** RSI  
**Key Insight:** Volatile stock where active strategies outperformed by 3x. Buy & hold suffered 48% drawdown.

### HIMS (Hims & Hers)
| Strategy | Final Value | ROI | Trades | Max Drawdown | Sharpe | $5 Fee Impact |
|----------|-------------|-----|--------|--------------|--------|---------------|
| Buy & Hold | $15,236 | +52.4% | 1 | 63.1% | 0.96 | -0.08% |
| MA Crossover | $4,906 | -50.9% | 6 | 60.6% | -0.93 | -0.20% |
| RSI | $10,788 | +7.9% | 3 | 23.1% | 0.44 | -0.14% |

**Winner:** Buy & Hold  
**Key Insight:** Extreme volatility. MA Crossover got whipsawed. 63% drawdown is brutal even with positive returns.

### SPY (S&P 500)
| Strategy | Final Value | ROI | Trades | Max Drawdown | Sharpe | $5 Fee Impact |
|----------|-------------|-----|--------|--------------|--------|---------------|
| Buy & Hold | $11,542 | +15.4% | 1 | 19.0% | 0.92 | -0.06% |
| MA Crossover | $11,577 | +15.8% | 1 | 5.1% | 1.87 | -0.06% |
| RSI | $11,445 | +14.5% | 3 | 6.3% | 1.14 | -0.16% |

**Winner:** MA Crossover (marginally)  
**Key Insight:** All strategies performed similarly. MA Crossover reduced drawdown from 19% to 5%.

## Sector ETF Results

### XLK (Technology)
| Strategy | Final Value | ROI | Trades | Max Drawdown | Sharpe |
|----------|-------------|-----|--------|--------------|--------|
| Buy & Hold | $12,218 | +22.2% | 1 | 25.8% | 0.96 |
| MA Crossover | $12,310 | +23.1% | 2 | 10.5% | 1.75 |
| RSI | $11,199 | +12.0% | 3 | 7.9% | 0.75 |

**Winner:** MA Crossover

### XLV (Healthcare)
| Strategy | Final Value | ROI | Trades | Max Drawdown | Sharpe |
|----------|-------------|-----|--------|--------------|--------|
| Buy & Hold | $11,232 | +12.3% | 1 | 14.0% | 0.84 |
| MA Crossover | $10,952 | +9.5% | 3 | 5.4% | 1.08 |
| RSI | $10,035 | +0.3% | 2 | 8.3% | 0.09 |

**Winner:** Buy & Hold

### XLF (Financials)
| Strategy | Final Value | ROI | Trades | Max Drawdown | Sharpe |
|----------|-------------|-----|--------|--------------|--------|
| Buy & Hold | $10,887 | +8.9% | 1 | 15.8% | 0.62 |
| MA Crossover | $10,335 | +3.3% | 2 | 4.6% | 0.44 |
| RSI | $11,165 | +11.7% | 3 | 4.8% | 1.11 |

**Winner:** RSI

### XLE (Energy)
| Strategy | Final Value | ROI | Trades | Max Drawdown | Sharpe |
|----------|-------------|-----|--------|--------------|--------|
| Buy & Hold | $10,574 | +5.7% | 1 | 18.8% | 0.36 |
| MA Crossover | $8,279 | -17.2% | 7 | 19.8% | -0.93 |
| RSI | $12,066 | +20.7% | 5 | 6.5% | 1.39 |

**Winner:** RSI  
**Key Insight:** Energy sector was choppy. RSI strategy crushed buy & hold by 3.6x.

## Transaction Cost Impact

### Impact of $5 per trade fee:
- **Buy & Hold:** -0.05% to -0.11% (minimal)
- **MA Crossover:** -0.09% to -0.34% (moderate)
- **RSI:** -0.14% to -0.28% (moderate)

### Impact of $10 per trade fee:
- **Buy & Hold:** -0.11% to -0.22% (minimal)
- **MA Crossover:** -0.19% to -0.68% (significant)
- **RSI:** -0.28% to -0.55% (significant)

**Key Insight:** Transaction costs hurt active strategies 2-3x more than buy & hold. Energy MA Crossover lost 0.68% with $10 fees due to 7 trades.

## Risk-Adjusted Performance (Sharpe Ratio)

### Top 5 Sharpe Ratios:
1. **GOOGL MA Crossover:** 3.26
2. **PLTR RSI:** 1.99
3. **SPY MA Crossover:** 1.87
4. **GOOGL Buy & Hold:** 1.85
5. **XLK MA Crossover:** 1.75

### Bottom 3 Sharpe Ratios:
1. **HIMS MA Crossover:** -0.93
2. **XLE MA Crossover:** -0.93
3. **XLV RSI:** 0.09

**Key Insight:** GOOGL had the best risk-adjusted returns. High volatility stocks (HIMS) and choppy sectors (Energy) had poor Sharpe ratios.

## Maximum Drawdown Analysis

### Largest Drawdowns:
1. **HIMS Buy & Hold:** 63.1%
2. **HIMS MA Crossover:** 60.6%
3. **TSLA Buy & Hold:** 48.2%
4. **PLTR Buy & Hold:** 40.6%
5. **GOOGL Buy & Hold:** 29.9%

### Smallest Drawdowns:
1. **PLTR RSI:** 3.2%
2. **XLF MA Crossover:** 4.6%
3. **XLF RSI:** 4.8%
4. **SPY MA Crossover:** 5.1%
5. **XLV MA Crossover:** 5.4%

**Key Insight:** Active strategies (RSI, MA Crossover) significantly reduce drawdowns but may sacrifice returns in strong uptrends.

## Key Findings

### 1. Strategy Selection by Stock Type

**Strong Uptrends (PLTR, HIMS):**
- Buy & Hold dominates
- Active strategies miss big gains
- Accept higher drawdowns for higher returns

**Moderate Trends (GOOGL, XLK):**
- MA Crossover wins
- Better risk-adjusted returns
- Reduced drawdowns

**Volatile/Choppy (TSLA, XLE):**
- RSI strategy excels
- Avoids whipsaws
- 2-3x better than buy & hold

**Stable/Index (SPY):**
- All strategies similar
- MA Crossover slightly better
- Minimal difference in returns

### 2. Transaction Costs Matter

- Buy & Hold: Nearly immune to fees (<0.2% impact)
- Active strategies: Lose 0.2-0.7% with realistic fees
- High-frequency strategies (7+ trades) get crushed
- Zero-commission brokers are essential for active trading

### 3. Risk Management

- Max drawdown often more important than returns
- HIMS: +52% return but 63% drawdown = sleepless nights
- GOOGL: +89% return with only 7.5% drawdown = smooth ride
- Sharpe ratio captures this: GOOGL 3.26 vs HIMS 0.96

### 4. Sector Differences

- **Technology (XLK):** MA Crossover best (+23.1%)
- **Healthcare (XLV):** Buy & Hold best (+12.3%)
- **Financials (XLF):** RSI best (+11.7%)
- **Energy (XLE):** RSI crushed it (+20.7% vs +5.7%)

### 5. The Diversification Penalty

- PLTR alone: +119.8%
- SPY (diversified): +15.4%
- Diversification reduces risk but caps upside
- Concentrated bets win big or lose big

## Limitations

1. **Survivorship Bias:** We tested stocks that survived 2025
2. **Overfitting:** Strategies optimized on same data they're tested on
3. **Market Regime:** 2025 was mostly bullish; bear markets differ
4. **Slippage:** Real execution prices differ from close prices
5. **Taxes:** Not accounted for (active strategies trigger more taxes)
6. **Dividends:** Not included in analysis
7. **Black Swans:** Cannot predict rare events

## Recommendations for Blog

### Story Arc:
1. **Hook:** "I tested 5 stocks with 3 strategies. One returned 119%. Another lost 50%."
2. **Setup:** Explain the strategies simply
3. **Results:** Show the data with clear tables
4. **Insights:** What actually matters (risk-adjusted returns, drawdowns)
5. **Honest Limitations:** What backtests can't tell you
6. **Takeaway:** Match strategy to stock type, not one-size-fits-all

### Key Charts to Include:
- Performance comparison bar chart (all stocks, all strategies)
- Drawdown comparison (show the pain)
- Sharpe ratio ranking (risk-adjusted winners)
- Transaction cost impact (why fees matter)
- Sector performance heatmap

### Tone:
- Data-driven but accessible
- Honest about limitations
- No "get rich quick" promises
- Focus on learning, not selling

## Data Verification

✅ All results verified against original backtests  
✅ PLTR Buy & Hold: 119.8% matches original  
✅ Date range: 2025-01-01 to 2025-12-02  
✅ Starting capital: $10,000 consistent across all tests  
✅ First trade uses open price (matching original methodology)  
✅ Subsequent trades use close price  
✅ RSI calculation: sum of gains/losses over 14 days  

**Status:** Ready for blog publication

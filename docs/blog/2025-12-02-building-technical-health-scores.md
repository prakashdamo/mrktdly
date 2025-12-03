# Building a Technical Health Score for Stocks

*December 2, 2025*

Today we added a new feature to help people understand if a stock is healthy or showing weakness. The idea came from analyzing historical market data and realizing that technical indicators could be simplified into a single, easy-to-understand score.

## The Problem

When you look at a stock, there are dozens of technical indicators: RSI, moving averages, momentum, volume trends, and more. It's overwhelming. You need to be an expert to interpret what it all means. We wanted something simpler: a health score from 0 to 100 that anyone could understand at a glance.

## What We Built

A Technical Health Score that combines five key components:

**Moving Averages (30 points)** - Is the stock above its 20, 50, and 200-day moving averages? Are we in a golden cross pattern?

**RSI (20 points)** - Is the stock overbought, oversold, or in a healthy range?

**Momentum (25 points)** - How has the stock performed over the last 1, 3, and 6 months?

**Volume Trend (15 points)** - Is trading volume increasing or decreasing?

**Price Position (10 points)** - How far is the stock from its recent high?

The score shows up as a simple rating:
- 🟢 80-100: Excellent
- 🟡 60-79: Good
- 🟠 40-59: Fair
- 🔴 0-39: Weak

## Testing the Approach

Before building anything, we ran backtests on 2025 data to see if technical analysis actually works. We tested five different strategies on stocks like PLTR, HIMS, TSLA, and the Magnificent 7.

The results were interesting:

For strong uptrending stocks like PLTR (+122% in 2025), buy-and-hold beat everything. But for choppy stocks like TSLA, technical strategies like moving average crossovers actually outperformed by 2x.

We also discovered something important: technical signals don't predict crashes, but they do trigger quickly once a decline starts. In the 2022 bear market, our signals would have triggered just 4 days after the peak, limiting losses to 2.5% instead of the full 25% drawdown. That's useful.

## Building the Feature

The implementation was straightforward:

1. **Lambda function** that fetches price data and calculates the score
2. **API endpoint** that returns the score as JSON
3. **UI components** that display the score on every ticker page

The score appears in two places:
- A small badge in the header for quick reference
- A detailed card showing the breakdown of all components

For example, PLTR currently scores 52/100 (Fair) because:
- It's below its 50-day moving average (bearish)
- RSI is oversold at 32.5 (potential bounce)
- 3-month momentum is positive (+9.4%)
- Volume is increasing

The score tells you at a glance: "This stock is showing some weakness but might be setting up for a bounce."

## What We Learned

**Technical analysis has limits.** It can't predict crashes before they happen. It can't tell you about fundamental changes in a business. It can't account for macro events.

But it can help you manage risk. It can tell you when a stock is losing momentum. It can help you avoid holding through major declines.

**Simplicity matters.** Instead of showing users 15 different indicators, we combined them into one score. It's not perfect, but it's useful.

**Data quality matters.** We have 5 years of daily price data for most stocks. That's enough for technical analysis, but not enough to predict bear markets or black swan events. We're honest about that limitation.

## The Bigger Picture

This feature is part of a larger goal: helping people make better investment decisions by combining multiple approaches.

Technical analysis tells you about price action and momentum. Fundamental analysis (which we'll add later) tells you about business quality and valuation. Sentiment analysis tells you about market psychology.

No single approach is perfect. But together, they give you a more complete picture.

## What's Next

We're planning a backtesting tool that lets users test different strategies on any stock. Want to see if swing trading would have worked better than buy-and-hold for TSLA? You'll be able to test it with real historical data.

We're also thinking about alerts: notify users when a stock's health score drops below a certain threshold, giving them a heads-up before major declines.

## Repository Cleanup

We also spent time organizing the codebase. The repository had grown to 60+ files in the root directory. We reorganized everything into logical folders:

- `docs/` for all documentation
- `scripts/` for all utility scripts
- Clean separation of concerns

It's not glamorous work, but it makes the project easier to maintain and easier for others to contribute to.

## Reflections

Building financial tools is humbling. The market is complex and unpredictable. Every time you think you've found a pattern, you discover its limitations.

The 2025 data showed us that PLTR was the best performer (+122%), and a simple buy-and-hold strategy beat everything else. But that's hindsight. In real-time, you don't know which stock will be the winner.

What you can do is manage risk, stay informed, and make decisions based on multiple data points. That's what we're trying to enable.

The technical health score won't make you rich. But it might help you avoid some losses. And sometimes, not losing is more important than winning big.

---

## Technical Details

For those interested in the implementation:

**Architecture:**
- AWS Lambda for serverless compute
- DynamoDB for caching scores
- API Gateway for REST endpoints
- CloudFront for global CDN
- React components for UI

**Cost:** About $3-36/month depending on usage. Very affordable.

**Open source:** The code is on GitHub. Feel free to look at how it works or suggest improvements.

**Limitations:** 
- Based on 5 years of data (not enough for full market cycles)
- Technical analysis only (no fundamentals yet)
- Can't predict crashes, only react to them
- Works better for some stocks than others

We're transparent about what it can and can't do. That's important.

---

*This feature is live now at [marketdly.com](https://d2d1mtdcy5ucyl.cloudfront.net/ticker-analysis.html). Try it with any ticker symbol.*

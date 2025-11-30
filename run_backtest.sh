#!/bin/bash
# Quick backtest runner

DAYS=${1:-30}

echo "Running backtest for last $DAYS days..."
python3 backtest_last_month.py

echo ""
echo "Dashboard updated at: https://mrktdly-website.s3.amazonaws.com/performance.html"

#!/bin/bash
echo "==================================================================="
echo "GitHub Issue Creator for MarketDly Launch"
echo "==================================================================="
echo ""
echo "Step 1: Get your GitHub token"
echo "  Visit: https://github.com/settings/tokens/new"
echo "  - Name: MarketDly Issue Creator"
echo "  - Scope: Check 'repo'"
echo "  - Click 'Generate token'"
echo ""
read -sp "Step 2: Paste your token here: " GITHUB_TOKEN
echo ""
echo ""
echo "Creating 10 GitHub issues..."
echo ""

export GITHUB_TOKEN
python3 create_github_issues.py

echo ""
echo "Done! Check your repo: https://github.com/prakashdamo/mrktdly/issues"

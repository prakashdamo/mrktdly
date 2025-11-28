#!/bin/bash

# MrktDly User Statistics Dashboard
# Usage: ./scripts/user_stats.sh

USER_POOL_ID="us-east-1_N5yuAGHc3"
REGION="us-east-1"

echo "================================"
echo "📊 MrktDly User Statistics"
echo "================================"
echo ""

# Get all users
USERS=$(aws cognito-idp list-users \
  --user-pool-id $USER_POOL_ID \
  --region $REGION \
  --output json)

# Total users
TOTAL=$(echo "$USERS" | jq '.Users | length')
echo "👥 Total Users: $TOTAL"

# Confirmed users
CONFIRMED=$(echo "$USERS" | jq '[.Users[] | select(.UserStatus == "CONFIRMED")] | length')
echo "✅ Confirmed: $CONFIRMED"

# Unconfirmed users
UNCONFIRMED=$(echo "$USERS" | jq '[.Users[] | select(.UserStatus == "UNCONFIRMED")] | length')
echo "⏳ Pending Verification: $UNCONFIRMED"

# New signups today
TODAY=$(date -u +%Y-%m-%d)
NEW_TODAY=$(echo "$USERS" | jq --arg today "$TODAY" '[.Users[] | select(.UserCreateDate | startswith($today))] | length')
echo "🆕 New Today: $NEW_TODAY"

# Active in last 24 hours
YESTERDAY=$(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S)
ACTIVE_24H=$(echo "$USERS" | jq --arg yesterday "$YESTERDAY" '[.Users[] | select(.UserLastModifiedDate > $yesterday)] | length')
echo "🔥 Active (24h): $ACTIVE_24H"

echo ""
echo "================================"
echo "📋 Recent Users"
echo "================================"
echo ""

# Show last 5 users with details
echo "$USERS" | jq -r '.Users | sort_by(.UserCreateDate) | reverse | .[0:5] | .[] | 
  "Email: " + (.Attributes[] | select(.Name == "email") | .Value) + 
  "\nStatus: " + .UserStatus + 
  "\nJoined: " + .UserCreateDate + 
  "\n---"'

echo ""
echo "================================"
echo "💾 Cache Statistics"
echo "================================"
echo ""

# Get cache table stats
CACHE_COUNT=$(aws dynamodb scan \
  --table-name mrktdly-ticker-cache \
  --select COUNT \
  --region $REGION \
  --output json | jq '.Count')

echo "🔍 Cached Analyses: $CACHE_COUNT"

# Get most analyzed tickers
echo ""
echo "Top Analyzed Tickers:"
aws dynamodb scan \
  --table-name mrktdly-ticker-cache \
  --region $REGION \
  --output json | jq -r '.Items[].ticker.S' | sort | uniq -c | sort -rn | head -5 | awk '{print "  " $2 ": " $1 " times"}'

echo ""

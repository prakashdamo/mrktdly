#!/bin/bash

# Test Technical Health Score integration

echo "🧪 Testing Technical Health Score Integration"
echo "=" * 80

# Test 1: Direct Lambda invocation
echo ""
echo "Test 1: Direct Lambda Function"
echo "Testing PLTR..."
aws lambda invoke \
  --function-name mrktdly-technical-health-score \
  --payload '{"ticker":"PLTR"}' \
  --region us-east-1 \
  response1.json > /dev/null 2>&1

if [ -f response1.json ]; then
  STATUS=$(cat response1.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('statusCode', 'error'))")
  if [ "$STATUS" = "200" ]; then
    echo "✅ Lambda function works"
    SCORE=$(cat response1.json | python3 -c "import sys, json; data=json.loads(json.load(sys.stdin)['body']); print(data['score'])")
    RATING=$(cat response1.json | python3 -c "import sys, json; data=json.loads(json.load(sys.stdin)['body']); print(data['rating'])")
    echo "   Score: $SCORE/100 ($RATING)"
  else
    echo "❌ Lambda function failed"
    cat response1.json
  fi
  rm response1.json
else
  echo "❌ Lambda invocation failed"
fi

# Test 2: API Gateway endpoint
echo ""
echo "Test 2: API Gateway Endpoint"
echo "Testing via API..."
RESPONSE=$(curl -s "https://xfi2u4ajm9.execute-api.us-east-1.amazonaws.com/prod/health-score?ticker=PLTR")

if echo "$RESPONSE" | grep -q "score"; then
  echo "✅ API endpoint works"
  SCORE=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['score'])")
  RATING=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['rating'])")
  echo "   Score: $SCORE/100 ($RATING)"
else
  echo "❌ API endpoint failed"
  echo "$RESPONSE"
fi

# Test 3: Multiple tickers
echo ""
echo "Test 3: Multiple Tickers"
for TICKER in GOOGL TSLA MSTR; do
  echo -n "Testing $TICKER... "
  RESPONSE=$(curl -s "https://xfi2u4ajm9.execute-api.us-east-1.amazonaws.com/prod/health-score?ticker=$TICKER")
  if echo "$RESPONSE" | grep -q "score"; then
    SCORE=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['score'])")
    EMOJI=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['emoji'])")
    echo "$EMOJI $SCORE/100"
  else
    echo "❌ Failed"
  fi
done

echo ""
echo "=" * 80
echo "✅ Integration tests complete!"
echo ""
echo "🌐 View in browser:"
echo "   https://marketdly.com/ticker-analysis.html?ticker=PLTR"
echo ""

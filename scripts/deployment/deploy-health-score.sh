#!/bin/bash

# Complete deployment script for Technical Health Score feature

set -e

echo "🚀 Deploying Technical Health Score Feature"
echo "=" * 80

# Step 1: Create DynamoDB table
echo ""
echo "📊 Step 1: Creating DynamoDB table..."
aws dynamodb create-table \
  --cli-input-json file://infrastructure/technical-scores-table.json \
  --region us-east-1 2>/dev/null && echo "✅ Table created" || echo "ℹ️  Table already exists"

# Step 2: Deploy technical-health-score Lambda
echo ""
echo "📦 Step 2: Deploying technical-health-score Lambda..."
cd lambda/technical-health-score
zip -j lambda.zip lambda_function.py
aws lambda update-function-code \
  --function-name mrktdly-technical-health-score \
  --zip-file fileb://lambda.zip \
  --region us-east-1 2>/dev/null || \
aws lambda create-function \
  --function-name mrktdly-technical-health-score \
  --runtime python3.9 \
  --role arn:aws:iam::060195792007:role/mrktdly-lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda.zip \
  --timeout 30 \
  --memory-size 512 \
  --region us-east-1
echo "✅ Lambda deployed"
cd ../..

# Step 3: Update API Lambda
echo ""
echo "🔌 Step 3: Updating API Lambda..."
cd lambda/api
zip -j lambda.zip lambda_function.py
aws lambda update-function-code \
  --function-name mrktdly-api \
  --zip-file fileb://lambda.zip \
  --region us-east-1
echo "✅ API Lambda updated"
cd ../..

# Step 4: Deploy website
echo ""
echo "🌐 Step 4: Deploying website..."
aws s3 cp website/ticker-analysis.html s3://mrktdly-website/ticker-analysis.html \
  --content-type "text/html" \
  --cache-control "max-age=300" \
  --region us-east-1
echo "✅ Website deployed"

# Step 5: Invalidate CloudFront cache
echo ""
echo "🔄 Step 5: Invalidating CloudFront cache..."
DISTRIBUTION_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?Aliases.Items[?contains(@, 'marketdly.com')]].Id" --output text)
if [ -n "$DISTRIBUTION_ID" ]; then
  aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION_ID \
    --paths "/ticker-analysis.html" \
    --region us-east-1
  echo "✅ Cache invalidated"
else
  echo "ℹ️  No CloudFront distribution found"
fi

# Step 6: Test the endpoint
echo ""
echo "🧪 Step 6: Testing endpoint..."
echo "Testing with PLTR..."
aws lambda invoke \
  --function-name mrktdly-technical-health-score \
  --payload '{"ticker":"PLTR"}' \
  --region us-east-1 \
  response.json > /dev/null

if [ -f response.json ]; then
  echo "✅ Test successful!"
  echo ""
  echo "Sample response:"
  cat response.json | python3 -m json.tool | head -20
  rm response.json
fi

echo ""
echo "=" * 80
echo "✅ Deployment Complete!"
echo ""
echo "🔗 API Endpoint:"
echo "   https://xfi2u4ajm9.execute-api.us-east-1.amazonaws.com/prod/health-score?ticker=PLTR"
echo ""
echo "🌐 Website:"
echo "   https://marketdly.com/ticker-analysis.html?ticker=PLTR"
echo ""
echo "📊 Test it:"
echo "   curl 'https://xfi2u4ajm9.execute-api.us-east-1.amazonaws.com/prod/health-score?ticker=PLTR'"
echo ""

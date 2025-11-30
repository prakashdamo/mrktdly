#!/bin/bash

echo "Setting up price history storage..."
echo ""

# 1. Create DynamoDB table
echo "1. Creating DynamoDB table: mrktdly-price-history"
aws dynamodb create-table \
  --table-name mrktdly-price-history \
  --attribute-definitions \
    AttributeName=ticker,AttributeType=S \
    AttributeName=date,AttributeType=S \
  --key-schema \
    AttributeName=ticker,KeyType=HASH \
    AttributeName=date,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1 \
  --tags Key=Project,Value=mrktdly Key=Purpose,Value=historical-price-storage

echo ""
echo "Waiting for table to be active..."
aws dynamodb wait table-exists --table-name mrktdly-price-history --region us-east-1

echo ""
echo "✅ Table created successfully!"
echo ""

# 2. Deploy updated data-fetch Lambda
echo "2. Deploying updated data-fetch Lambda..."
cd lambda/data_fetch
zip -q lambda.zip lambda_function.py
aws lambda update-function-code \
  --function-name mrktdly-data-fetch \
  --zip-file fileb://lambda.zip \
  --region us-east-1

echo ""
echo "✅ Lambda updated successfully!"
echo ""

# 3. Test by triggering data fetch
echo "3. Triggering data fetch to test..."
aws lambda invoke \
  --function-name mrktdly-data-fetch \
  --region us-east-1 \
  /tmp/response.json

echo ""
echo "✅ Setup complete!"
echo ""
echo "Price history is now being stored in DynamoDB."
echo "Check table: aws dynamodb scan --table-name mrktdly-price-history --limit 5 --region us-east-1"

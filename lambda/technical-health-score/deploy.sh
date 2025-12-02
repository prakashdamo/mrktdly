#!/bin/bash

# Deploy Technical Health Score Lambda

set -e

echo "🚀 Deploying Technical Health Score Lambda..."

# Create DynamoDB table if it doesn't exist
echo "📊 Creating DynamoDB table..."
aws dynamodb create-table \
  --cli-input-json file://../../infrastructure/technical-scores-table.json \
  --region us-east-1 2>/dev/null || echo "Table already exists"

# Package Lambda
echo "📦 Packaging Lambda..."
zip -j lambda.zip lambda_function.py

# Deploy Lambda (update if exists, create if not)
echo "☁️  Deploying to AWS Lambda..."
aws lambda update-function-code \
  --function-name mrktdly-technical-health-score \
  --zip-file fileb://lambda.zip \
  --region us-east-1 2>/dev/null || \
aws lambda create-function \
  --function-name mrktdly-technical-health-score \
  --runtime python3.9 \
  --role arn:aws:iam::060195792007:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda.zip \
  --timeout 30 \
  --memory-size 512 \
  --region us-east-1

echo "✅ Deployment complete!"
echo ""
echo "Test with:"
echo "aws lambda invoke --function-name mrktdly-technical-health-score --payload '{\"ticker\":\"PLTR\"}' response.json --region us-east-1"

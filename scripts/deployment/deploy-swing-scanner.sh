#!/bin/bash
set -e

echo "Deploying Swing Scanner..."

# Deploy API Lambda (with swing-signals endpoint)
echo "1. Updating API Lambda..."
cd lambda/api
zip -r lambda.zip lambda_function.py
aws lambda update-function-code \
  --function-name mrktdly-api \
  --zip-file fileb://lambda.zip \
  --region us-east-1
cd ../..

# Deploy Swing Scanner Lambda
echo "2. Updating Swing Scanner Lambda..."
cd lambda/swing_scanner
zip lambda.zip handler.py
aws lambda update-function-code \
  --function-name mrktdly-swing-scanner \
  --zip-file fileb://lambda.zip \
  --region us-east-1
cd ../..

# Upload website files to S3
echo "3. Uploading website files..."
aws s3 cp website/swing-scanner.html s3://mrktdly-website/ --region us-east-1
aws s3 cp website/index.html s3://mrktdly-website/ --region us-east-1

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Run the scanner: aws lambda invoke --function-name mrktdly-swing-scanner --region us-east-1 output.json"
echo "2. Visit: https://mrktdly.com/swing-scanner.html"

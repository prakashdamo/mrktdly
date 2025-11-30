#!/bin/bash

# First run the swing scanner to generate signals
echo "Running swing scanner..."
aws lambda invoke \
  --function-name mrktdly-swing-scanner \
  --region us-east-1 \
  scanner-output.json

echo ""
echo "Scanner output:"
cat scanner-output.json | jq -r '.body' | jq .

echo ""
echo "Sending test email with swing signals..."
aws lambda invoke \
  --function-name mrktdly-delivery \
  --region us-east-1 \
  delivery-output.json

echo ""
echo "Delivery output:"
cat delivery-output.json | jq .

echo ""
echo "✅ Check your email for the daily summary with swing signals!"

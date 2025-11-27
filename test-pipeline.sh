#!/bin/bash

echo "🚀 Testing MrktDly Pipeline"
echo "=============================="
echo ""

# Step 1: Fetch market data
echo "1️⃣  Fetching market data..."
aws lambda invoke --function-name mrktdly-data-fetch --region us-east-1 /tmp/fetch-output.json > /dev/null
cat /tmp/fetch-output.json
echo ""
sleep 2

# Step 2: Generate analysis
echo "2️⃣  Generating analysis with Bedrock..."
aws lambda invoke --function-name mrktdly-analysis --region us-east-1 /tmp/analysis-output.json > /dev/null
cat /tmp/analysis-output.json
echo ""
sleep 2

# Step 3: Check what was generated
echo "3️⃣  Checking generated analysis..."
DATE=$(date -u +%Y-%m-%d)
aws dynamodb get-item \
  --table-name mrktdly-data \
  --key "{\"pk\":{\"S\":\"DATA#$DATE\"},\"sk\":{\"S\":\"ANALYSIS\"}}" \
  --region us-east-1 \
  --query 'Item.analysis.M' \
  --output json | head -30
echo ""

# Step 4: Test delivery (will send to waitlist)
echo "4️⃣  Testing email delivery..."
echo "⚠️  This will send emails to everyone on the waitlist!"
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]
then
    aws lambda invoke --function-name mrktdly-delivery --region us-east-1 /tmp/delivery-output.json > /dev/null
    cat /tmp/delivery-output.json
    echo ""
fi

echo "✅ Pipeline test complete!"
echo ""
echo "To check waitlist:"
echo "aws dynamodb scan --table-name mrktdly-waitlist --region us-east-1"

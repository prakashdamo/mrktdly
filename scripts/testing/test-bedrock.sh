#!/bin/bash
echo "Testing Bedrock access..."
aws lambda invoke --function-name mrktdly-analysis --region us-east-1 /tmp/test-analysis.json
echo ""
echo "Checking logs for Bedrock response..."
aws logs tail /aws/lambda/mrktdly-analysis --region us-east-1 --since 1m --format short | grep -i "bedrock\|error"

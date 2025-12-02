#!/bin/bash

REGION="us-east-1"
ROLE_ARN="arn:aws:iam::060195792007:role/lambda-role"

echo "Deploying Signal Tracking System..."

# 1. Deploy signal-tracker Lambda
echo "Deploying signal-tracker..."
cd lambda/signal-tracker
zip -q lambda.zip lambda_function.py
aws lambda create-function \
  --function-name mrktdly-signal-tracker \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda.zip \
  --timeout 30 \
  --region $REGION 2>/dev/null || \
aws lambda update-function-code \
  --function-name mrktdly-signal-tracker \
  --zip-file fileb://lambda.zip \
  --region $REGION
cd ../..

# 2. Deploy signal-evaluator Lambda
echo "Deploying signal-evaluator..."
cd lambda/signal-evaluator
zip -q lambda.zip lambda_function.py
aws lambda create-function \
  --function-name mrktdly-signal-evaluator \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda.zip \
  --timeout 300 \
  --region $REGION 2>/dev/null || \
aws lambda update-function-code \
  --function-name mrktdly-signal-evaluator \
  --zip-file fileb://lambda.zip \
  --region $REGION
cd ../..

# 3. Deploy signal-stats Lambda
echo "Deploying signal-stats..."
cd lambda/signal-stats
zip -q lambda.zip lambda_function.py
aws lambda create-function \
  --function-name mrktdly-signal-stats \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda.zip \
  --timeout 30 \
  --region $REGION 2>/dev/null || \
aws lambda update-function-code \
  --function-name mrktdly-signal-stats \
  --zip-file fileb://lambda.zip \
  --region $REGION
cd ../..

# 4. Update ticker-analysis-v2 to record signals
echo "Updating ticker-analysis-v2..."
cd lambda/ticker-analysis-v2
zip -q lambda.zip lambda_function.py
aws lambda update-function-code \
  --function-name mrktdly-ticker-analysis-v2 \
  --zip-file fileb://lambda.zip \
  --region $REGION
cd ../..

# 5. Update ticker-analysis (main) with fixed fibonacci
echo "Updating ticker-analysis..."
cd lambda/ticker-analysis
zip -q lambda.zip lambda_function.py
aws lambda update-function-code \
  --function-name mrktdly-ticker-analysis \
  --zip-file fileb://lambda.zip \
  --region $REGION
cd ../..

# 6. Create EventBridge rule to run evaluator daily
echo "Setting up daily evaluation schedule..."
aws events put-rule \
  --name mrktdly-daily-signal-evaluation \
  --schedule-expression "cron(0 21 * * ? *)" \
  --region $REGION 2>/dev/null

aws lambda add-permission \
  --function-name mrktdly-signal-evaluator \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:$REGION:060195792007:rule/mrktdly-daily-signal-evaluation \
  --region $REGION 2>/dev/null

aws events put-targets \
  --rule mrktdly-daily-signal-evaluation \
  --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:060195792007:function:mrktdly-signal-evaluator" \
  --region $REGION

echo "✅ Signal tracking system deployed!"
echo ""
echo "Next steps:"
echo "1. Add signal-stats API endpoint to API Gateway"
echo "2. Update ticker-analysis.html with your API Gateway URL"
echo "3. Test by generating a signal via ticker-analysis-v2"
echo "4. Wait for daily evaluator to run (9pm UTC) or invoke manually"

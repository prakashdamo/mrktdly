#!/bin/bash

API_ID="xfi2u4ajm9"
REGION="us-east-1"
LAMBDA_ARN="arn:aws:lambda:us-east-1:060195792007:function:mrktdly-waitlist"

# Get root resource
ROOT_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[0].id' --output text)

# Create /waitlist resource
RESOURCE_ID=$(aws apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_ID --path-part waitlist --region $REGION --query 'id' --output text)

# Create POST method
aws apigateway put-method --rest-api-id $API_ID --resource-id $RESOURCE_ID --http-method POST --authorization-type NONE --region $REGION

# Create OPTIONS method for CORS
aws apigateway put-method --rest-api-id $API_ID --resource-id $RESOURCE_ID --http-method OPTIONS --authorization-type NONE --region $REGION

# Set up Lambda integration for POST
aws apigateway put-integration --rest-api-id $API_ID --resource-id $RESOURCE_ID --http-method POST --type AWS_PROXY --integration-http-method POST --uri arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations --region $REGION

# Set up Lambda integration for OPTIONS
aws apigateway put-integration --rest-api-id $API_ID --resource-id $RESOURCE_ID --http-method OPTIONS --type AWS_PROXY --integration-http-method POST --uri arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations --region $REGION

# Give API Gateway permission to invoke Lambda
aws lambda add-permission --function-name mrktdly-waitlist --statement-id apigateway-invoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:$REGION:060195792007:$API_ID/*/*" --region $REGION

# Deploy API
aws apigateway create-deployment --rest-api-id $API_ID --stage-name prod --region $REGION

echo "API Gateway URL: https://$API_ID.execute-api.$REGION.amazonaws.com/prod/waitlist"

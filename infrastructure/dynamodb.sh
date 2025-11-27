#!/bin/bash

# Create main data table
aws dynamodb create-table \
    --table-name mrktdly-data \
    --attribute-definitions \
        AttributeName=pk,AttributeType=S \
        AttributeName=sk,AttributeType=S \
    --key-schema \
        AttributeName=pk,KeyType=HASH \
        AttributeName=sk,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

# Create waitlist table
aws dynamodb create-table \
    --table-name mrktdly-waitlist \
    --attribute-definitions \
        AttributeName=email,AttributeType=S \
    --key-schema \
        AttributeName=email,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

echo "DynamoDB tables created successfully"

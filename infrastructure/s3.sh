#!/bin/bash

# Create S3 bucket for videos
aws s3 mb s3://mrktdly-videos --region us-east-1

# Enable public read access for videos
aws s3api put-bucket-policy --bucket mrktdly-videos --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::mrktdly-videos/videos/*"
  }]
}'

# Enable CORS
aws s3api put-bucket-cors --bucket mrktdly-videos --cors-configuration '{
  "CORSRules": [{
    "AllowedOrigins": ["https://mrktdly.com", "https://www.mrktdly.com"],
    "AllowedMethods": ["GET"],
    "AllowedHeaders": ["*"]
  }]
}'

echo "S3 bucket created successfully"

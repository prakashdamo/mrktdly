# Stripe Integration Deployment Guide

## Overview
This guide walks through completing the Stripe payment integration for MarketDly's freemium model.

## Current State
- ✅ Code written for checkout and webhook Lambdas
- ✅ Frontend updated with checkout buttons
- ✅ New signups get "free" tier (not Pro)
- ⏳ Stripe account setup needed
- ⏳ Lambda deployment with Stripe library needed

---

## Step 1: Stripe Account Setup

### 1.1 Create Stripe Account
1. Go to https://stripe.com
2. Sign up for account
3. Complete business verification

### 1.2 Create Products & Prices
1. Go to Stripe Dashboard → Products
2. Create **Basic Plan**:
   - Name: "MarketDly Basic"
   - Price: $9.00 USD
   - Billing: Recurring monthly
   - Copy the **Price ID** (starts with `price_`)
3. Create **Pro Plan**:
   - Name: "MarketDly Pro"
   - Price: $29.00 USD
   - Billing: Recurring monthly
   - Copy the **Price ID** (starts with `price_`)

### 1.3 Get API Keys
1. Go to Stripe Dashboard → Developers → API Keys
2. Copy **Secret Key** (starts with `sk_live_` or `sk_test_`)
3. Copy **Publishable Key** (starts with `pk_live_` or `pk_test_`)

---

## Step 2: Deploy Stripe Checkout Lambda

### 2.1 Create Stripe Layer
```bash
# Create directory for Stripe library
mkdir -p /tmp/stripe-layer/python
cd /tmp/stripe-layer/python

# Install Stripe library
pip3 install stripe -t .

# Create layer zip
cd /tmp/stripe-layer
zip -r stripe-layer.zip python/

# Upload to AWS Lambda Layer
aws lambda publish-layer-version \
  --layer-name stripe-python \
  --zip-file fileb://stripe-layer.zip \
  --compatible-runtimes python3.11 \
  --region us-east-1
```

Copy the **Layer ARN** from output (e.g., `arn:aws:lambda:us-east-1:123456789:layer:stripe-python:1`)

### 2.2 Deploy Checkout Lambda
```bash
cd /home/prakash/marketdly/lambda/stripe-checkout
zip function.zip lambda_function.py

aws lambda create-function \
  --function-name mrktdly-stripe-checkout \
  --runtime python3.11 \
  --role arn:aws:iam::060195792007:role/mrktdly-lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --region us-east-1 \
  --layers <STRIPE_LAYER_ARN> \
  --environment Variables="{
    STRIPE_SECRET_KEY=<YOUR_STRIPE_SECRET_KEY>,
    STRIPE_BASIC_PRICE_ID=<YOUR_BASIC_PRICE_ID>,
    STRIPE_PRO_PRICE_ID=<YOUR_PRO_PRICE_ID>
  }"
```

Replace:
- `<STRIPE_LAYER_ARN>` with Layer ARN from 2.1
- `<YOUR_STRIPE_SECRET_KEY>` with Secret Key from 1.3
- `<YOUR_BASIC_PRICE_ID>` with Basic Price ID from 1.2
- `<YOUR_PRO_PRICE_ID>` with Pro Price ID from 1.2

### 2.3 Add to API Gateway
```bash
# Get API Gateway ID
aws apigateway get-rest-apis --region us-east-1 --query "items[?name=='mrktdly-api'].id" --output text

# Create resource and method (manual in AWS Console or via CLI)
# POST /stripe-checkout → mrktdly-stripe-checkout Lambda
```

---

## Step 3: Deploy Stripe Webhook Lambda

### 3.1 Deploy Webhook Lambda
```bash
cd /home/prakash/marketdly/lambda/stripe-webhook
zip function.zip lambda_function.py

aws lambda create-function \
  --function-name mrktdly-stripe-webhook \
  --runtime python3.11 \
  --role arn:aws:iam::060195792007:role/mrktdly-lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --region us-east-1 \
  --layers <STRIPE_LAYER_ARN> \
  --environment Variables="{
    STRIPE_SECRET_KEY=<YOUR_STRIPE_SECRET_KEY>,
    STRIPE_WEBHOOK_SECRET=placeholder
  }"
```

Note: We'll update STRIPE_WEBHOOK_SECRET in step 3.3

### 3.2 Add to API Gateway
```bash
# Create POST /stripe-webhook → mrktdly-stripe-webhook Lambda
# Make sure to disable API Gateway authentication for this endpoint
```

### 3.3 Configure Stripe Webhook
1. Go to Stripe Dashboard → Developers → Webhooks
2. Click "Add endpoint"
3. Endpoint URL: `https://xfi2u4ajm9.execute-api.us-east-1.amazonaws.com/prod/stripe-webhook`
4. Select events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Click "Add endpoint"
6. Copy the **Signing Secret** (starts with `whsec_`)
7. Update Lambda environment variable:
```bash
aws lambda update-function-configuration \
  --function-name mrktdly-stripe-webhook \
  --environment Variables="{
    STRIPE_SECRET_KEY=<YOUR_STRIPE_SECRET_KEY>,
    STRIPE_WEBHOOK_SECRET=<YOUR_WEBHOOK_SECRET>
  }" \
  --region us-east-1
```

---

## Step 4: Test the Integration

### 4.1 Test Signup Flow
1. Go to https://marketdly.com
2. Click "Sign Up Free"
3. Create account
4. Verify you get "free" tier (3 ticker/day limit)

### 4.2 Test Upgrade Flow
1. Go to https://marketdly.com/pricing.html
2. Click "Subscribe Now" on Pro plan
3. Complete Stripe checkout (use test card: 4242 4242 4242 4242)
4. Verify redirect to success page
5. Check DynamoDB - subscription should show tier="pro"
6. Test unlimited ticker access

### 4.3 Test Webhook
1. Go to Stripe Dashboard → Webhooks
2. Click on your webhook
3. Click "Send test webhook"
4. Select `checkout.session.completed`
5. Check CloudWatch logs for mrktdly-stripe-webhook

---

## Step 5: Go Live

### 5.1 Switch to Live Mode
1. In Stripe Dashboard, toggle from "Test mode" to "Live mode"
2. Get new Live API keys
3. Create new Live products/prices
4. Update Lambda environment variables with Live keys

### 5.2 Update Existing Users (Optional)
If you want to keep existing users on Pro:
```bash
# They're already set to Pro from previous migration
# No action needed unless you want to downgrade them
```

---

## Pricing Summary

**Free Tier (No Payment):**
- 3 ticker analyses per day
- 3 sample trade signals
- Daily market summary email (no signals)
- Market intelligence page

**Basic Tier ($9/month):**
- Unlimited ticker analyses
- Daily email summaries
- (No trade signals)

**Pro Tier ($29/month):**
- Everything in Basic
- All trade signals (Technical + AI)
- 2x daily emails with signals
- Performance tracking
- Portfolio management

---

## Troubleshooting

### Checkout not working
- Check Lambda logs: `aws logs tail /aws/lambda/mrktdly-stripe-checkout --follow`
- Verify Stripe keys are correct
- Check API Gateway integration

### Webhook not firing
- Verify webhook URL is correct
- Check webhook signing secret
- Test webhook from Stripe Dashboard
- Check Lambda logs: `aws logs tail /aws/lambda/mrktdly-stripe-webhook --follow`

### User not upgraded after payment
- Check webhook logs
- Verify email matches between Stripe and DynamoDB
- Manually update: `aws dynamodb update-item --table-name mrktdly-subscriptions --key '{"email":{"S":"user@example.com"}}' --update-expression "SET tier = :t" --expression-attribute-values '{":t":{"S":"pro"}}'`

---

## Security Notes

- Never commit Stripe keys to git
- Use environment variables for all secrets
- Verify webhook signatures (already implemented)
- Use HTTPS only
- Enable Stripe Radar for fraud detection

---

## Support

For issues:
1. Check CloudWatch logs
2. Review Stripe Dashboard → Events
3. Test with Stripe test cards: https://stripe.com/docs/testing

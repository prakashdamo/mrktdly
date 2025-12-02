# MrktDly Testing Guide

## ✅ What's Deployed

### Complete Pipeline (Text-Based)
1. **Data Fetch** (7:00 AM ET) - Fetches SPY, QQQ, NVDA, TSLA, AAPL prices
2. **Analysis** (7:15 AM ET) - Generates educational analysis with Bedrock
3. **Delivery** (8:00 AM ET) - Sends email to waitlist subscribers

### Scheduled Times (Mon-Fri)
- 7:00 AM ET (12:00 UTC) - Data fetch
- 7:15 AM ET (12:15 UTC) - Analysis generation
- 8:00 AM ET (13:00 UTC) - Email delivery

## 🧪 Manual Testing

### Test Full Pipeline
```bash
cd /home/prakash/mrktdly
./test-pipeline.sh
```

### Test Individual Steps

**1. Fetch Market Data**
```bash
aws lambda invoke --function-name mrktdly-data-fetch --region us-east-1 /tmp/out.json
cat /tmp/out.json
```

**2. Generate Analysis**
```bash
aws lambda invoke --function-name mrktdly-analysis --region us-east-1 /tmp/out.json
cat /tmp/out.json
```

**3. Check Analysis in DynamoDB**
```bash
DATE=$(date -u +%Y-%m-%d)
aws dynamodb get-item \
  --table-name mrktdly-data \
  --key "{\"pk\":{\"S\":\"DATA#$DATE\"},\"sk\":{\"S\":\"ANALYSIS\"}}" \
  --region us-east-1
```

**4. Send Test Email** (⚠️ sends to all waitlist subscribers)
```bash
aws lambda invoke --function-name mrktdly-delivery --region us-east-1 /tmp/out.json
cat /tmp/out.json
```

## 📧 Email Setup Required

Before emails will work, you need to:

### 1. Verify Email Address in SES
```bash
aws ses verify-email-identity --email-address daily@mrktdly.com --region us-east-1
```
Check your email and click the verification link.

### 2. Verify Your Test Email
```bash
aws ses verify-email-identity --email-address YOUR_EMAIL@example.com --region us-east-1
```

### 3. Request Production Access (Optional)
SES starts in sandbox mode (can only send to verified emails). To send to anyone:
```bash
# Submit request in AWS Console:
# SES → Account Dashboard → Request production access
```

## 🎯 Test Scenarios

### Scenario 1: End-to-End Test
1. Add your email to waitlist via website
2. Run `./test-pipeline.sh`
3. Check your inbox for the email

### Scenario 2: Check Scheduled Execution
Wait until 8:00 AM ET on a weekday, then:
```bash
# Check CloudWatch Logs
aws logs tail /aws/lambda/mrktdly-delivery --since 1h --region us-east-1
```

### Scenario 3: Verify Analysis Quality
```bash
DATE=$(date -u +%Y-%m-%d)
aws dynamodb get-item \
  --table-name mrktdly-data \
  --key "{\"pk\":{\"S\":\"DATA#$DATE\"},\"sk\":{\"S\":\"ANALYSIS\"}}" \
  --region us-east-1 \
  --query 'Item.analysis' \
  --output json | jq
```

## 📊 Check Waitlist
```bash
aws dynamodb scan --table-name mrktdly-waitlist --region us-east-1
```

## 🐛 Troubleshooting

### Analysis Generation Fails
- Check Bedrock access: `aws bedrock list-foundation-models --region us-east-1`
- Check Lambda logs: `aws logs tail /aws/lambda/mrktdly-analysis --since 1h --region us-east-1`

### Email Not Sending
- Verify SES email: `aws ses get-identity-verification-attributes --identities daily@mrktdly.com --region us-east-1`
- Check Lambda logs: `aws logs tail /aws/lambda/mrktdly-delivery --since 1h --region us-east-1`

### No Market Data
- Check if markets are open (Mon-Fri, 9:30 AM - 4:00 PM ET)
- Yahoo Finance API may have rate limits

## 📝 Sample Email Output

The email includes:
- **Market Overview**: 2-3 sentence summary
- **Educational Focus**: 3 key concepts to learn
- **Levels to Watch**: Technical levels on SPY, QQQ
- **Risk Factors**: Things to be aware of
- **Disclaimer**: Educational content only

## ✅ Success Criteria

- [ ] Data fetch runs successfully
- [ ] Analysis generates with Bedrock
- [ ] Email sends to verified addresses
- [ ] Content is educational (no "buy/sell" language)
- [ ] Disclaimers are prominent
- [ ] Pipeline runs automatically at scheduled times

## 🚀 Next Steps

Once testing is complete:
1. Verify SES for production sending
2. Add more subscribers to waitlist
3. Monitor for 1 week
4. Collect feedback
5. Add video generation (optional)
6. Enable payments (after legal review)

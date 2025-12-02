# MrktDly Deployment Guide

## ✅ Infrastructure Deployed

### AWS Resources Created:
- ✅ DynamoDB Tables:
  - `mrktdly-data` - Stores daily market data and analysis
  - `mrktdly-waitlist` - Stores email signups
- ✅ S3 Bucket: `mrktdly-videos` - Stores generated videos
- ✅ Lambda Function: `mrktdly-data-fetch` - Fetches market data daily at 7 AM ET
- ✅ EventBridge Rule: `mrktdly-daily-7am` - Triggers Lambda at 7 AM ET (12:00 UTC)
- ✅ IAM Role: `mrktdly-lambda-role` - Lambda execution role with necessary permissions

## 🚀 Deploy Frontend to Vercel

### Step 1: Push to GitHub
```bash
cd /home/prakash/mrktdly
git remote add origin https://github.com/YOUR_USERNAME/mrktdly.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Vercel
1. Go to https://vercel.com/new
2. Import your `mrktdly` repository
3. Set Root Directory to `frontend`
4. Add Environment Variables:
   - `AWS_ACCESS_KEY_ID` = Your AWS access key
   - `AWS_SECRET_ACCESS_KEY` = Your AWS secret key
   - `AWS_REGION` = us-east-1
5. Click Deploy

### Step 3: Configure Custom Domain
1. In Vercel project settings → Domains
2. Add `mrktdly.com` and `www.mrktdly.com`
3. Update your domain's nameservers or add CNAME records as instructed

## 📊 Test the System

### Test Data Fetch Lambda
```bash
aws lambda invoke --function-name mrktdly-data-fetch --region us-east-1 /tmp/output.json
cat /tmp/output.json
```

### Check DynamoDB for Data
```bash
aws dynamodb scan --table-name mrktdly-data --region us-east-1 --max-items 5
```

### Test Waitlist Signup
Once deployed, visit your site and sign up with an email, then check:
```bash
aws dynamodb scan --table-name mrktdly-waitlist --region us-east-1
```

## 🔧 Next Steps

### 1. Complete the Pipeline (Optional - for full automation)
The remaining Lambda functions need to be created:
- `mrktdly-analysis` - Generates analysis using Bedrock (7:15 AM ET)
- `mrktdly-video-gen` - Creates video (7:30 AM ET)  
- `mrktdly-delivery` - Sends emails (8:00 AM ET)

### 2. Manual Review Dashboard
Before automating delivery, build a review dashboard where you can:
- See the generated analysis
- Preview the video
- Approve/edit before sending
- Manually trigger delivery

### 3. Get API Keys
- Alpha Vantage: https://www.alphavantage.co/support/#api-key (Free)
- NewsAPI: https://newsapi.org/register (Free tier available)
- ElevenLabs: https://elevenlabs.io (For voice generation)

### 4. Legal Review
Before accepting payments:
- Have a lawyer review all disclaimers
- Create proper Terms of Service
- Set up business entity
- Get E&O insurance

## 💰 Current Monthly Costs

| Service | Cost |
|---------|------|
| DynamoDB (on-demand) | ~$1 |
| S3 Storage | ~$1 |
| Lambda Executions | ~$1 |
| Vercel (Hobby) | $0 |
| **Total** | **~$3/mo** |

## 📝 Environment Variables Needed

### For Lambda Functions:
- `ALPHA_VANTAGE_KEY` - Market data API
- `NEWS_API_KEY` - News data
- `ELEVENLABS_KEY` - Voice synthesis
- `DYNAMODB_TABLE` - mrktdly-data
- `S3_BUCKET` - mrktdly-videos

### For Next.js:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`

## 🎯 Launch Checklist

- [x] AWS infrastructure deployed
- [x] Landing page created
- [x] Waitlist functionality working
- [ ] Push to GitHub
- [ ] Deploy to Vercel
- [ ] Configure mrktdly.com domain
- [ ] Test waitlist signup
- [ ] Create first manual video
- [ ] Send to 10 beta testers
- [ ] Collect feedback
- [ ] Legal review
- [ ] Enable payments (later)

## 📧 Support

Questions? Check the code comments or AWS CloudWatch logs for debugging.

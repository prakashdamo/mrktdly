# MarketDly Email Setup - CRITICAL PRIORITY

## Email Addresses Needed

1. `admin@marketdly.com` - Admin notifications, system alerts
2. `uncled@marketdly.com` - Personal email for Uncle D
3. `support@marketdly.com` - Customer support
4. `noreply@marketdly.com` - Automated emails (signals, notifications)

---

## Setup Steps

### Step 1: Verify Domain in SES

```bash
# Verify domain
aws ses verify-domain-identity --domain marketdly.com --region us-east-1

# Get verification token
aws ses get-identity-verification-attributes --identities marketdly.com --region us-east-1
```

### Step 2: Add DNS Records to Route53

**TXT Record for Verification:**
```
Name: _amazonses.marketdly.com
Type: TXT
Value: [token from Step 1]
TTL: 300
```

**DKIM Records (for deliverability):**
```bash
# Get DKIM tokens
aws ses verify-domain-dkim --domain marketdly.com --region us-east-1
```

Add 3 CNAME records returned by above command.

**MX Record (to receive email):**
```
Name: marketdly.com
Type: MX
Priority: 10
Value: inbound-smtp.us-east-1.amazonaws.com
TTL: 300
```

### Step 3: Set Up Email Receiving (Forward to Gmail)

**Create S3 bucket for email storage:**
```bash
aws s3 mb s3://marketdly-emails --region us-east-1
```

**Create SES receipt rule:**
```bash
aws ses create-receipt-rule-set --rule-set-name marketdly-rules --region us-east-1

aws ses set-active-receipt-rule-set --rule-set-name marketdly-rules --region us-east-1
```

**Add receipt rule to forward emails:**
```json
{
  "Name": "forward-to-gmail",
  "Enabled": true,
  "Recipients": [
    "admin@marketdly.com",
    "uncled@marketdly.com",
    "support@marketdly.com"
  ],
  "Actions": [
    {
      "S3Action": {
        "BucketName": "marketdly-emails",
        "ObjectKeyPrefix": "incoming/"
      }
    },
    {
      "LambdaAction": {
        "FunctionArn": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:email-forwarder"
      }
    }
  ]
}
```

### Step 4: Create Lambda Email Forwarder

**Lambda function to forward emails to Gmail:**

```python
# lambda/email-forwarder.py
import boto3
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ses = boto3.client('ses', region_name='us-east-1')
s3 = boto3.client('s3')

# Forwarding map
FORWARD_MAP = {
    'admin@marketdly.com': 'your-gmail@gmail.com',
    'uncled@marketdly.com': 'your-gmail@gmail.com',
    'support@marketdly.com': 'your-gmail@gmail.com'
}

def lambda_handler(event, context):
    # Get email from S3
    record = event['Records'][0]
    message_id = record['ses']['mail']['messageId']
    
    # Fetch email from S3
    bucket = 'marketdly-emails'
    key = f'incoming/{message_id}'
    
    obj = s3.get_object(Bucket=bucket, Key=key)
    raw_email = obj['Body'].read()
    
    # Parse email
    msg = email.message_from_bytes(raw_email)
    
    # Get recipient
    recipient = record['ses']['receipt']['recipients'][0]
    forward_to = FORWARD_MAP.get(recipient)
    
    if not forward_to:
        return {'statusCode': 200, 'body': 'No forwarding rule'}
    
    # Forward email
    ses.send_raw_email(
        Source=recipient,
        Destinations=[forward_to],
        RawMessage={'Data': raw_email}
    )
    
    return {'statusCode': 200, 'body': 'Email forwarded'}
```

### Step 5: Configure Gmail "Send As"

**In Gmail:**
1. Settings → Accounts → "Send mail as"
2. Add: `uncled@marketdly.com`
3. SMTP Server: `email-smtp.us-east-1.amazonaws.com`
4. Port: 587
5. Username: [SES SMTP credentials]
6. Password: [SES SMTP password]

**Get SMTP credentials:**
```bash
aws iam create-user --user-name ses-smtp-user
aws iam attach-user-policy --user-name ses-smtp-user --policy-arn arn:aws:iam::aws:policy/AmazonSesSendingAccess
aws iam create-access-key --user-name ses-smtp-user
```

### Step 6: Request Production Access

**Move SES out of sandbox:**
1. Go to SES Console
2. Request production access
3. Fill out form:
   - Use case: Trading signals and notifications
   - Expected volume: 10,000 emails/month
   - Bounce/complaint handling: Yes, we monitor
4. Wait 24 hours for approval

---

## Testing

**Test sending:**
```bash
aws ses send-email \
  --from noreply@marketdly.com \
  --to your-gmail@gmail.com \
  --subject "Test Email" \
  --text "This is a test" \
  --region us-east-1
```

**Test receiving:**
1. Send email to `uncled@marketdly.com`
2. Check your Gmail
3. Should arrive within 1 minute

**Test reply:**
1. Reply from Gmail
2. Should show as from `uncled@marketdly.com`

---

## Cost

**SES:**
- First 62,000 emails/month: FREE
- After: $0.10 per 1,000 emails

**S3 (email storage):**
- ~$0.50/month (negligible)

**Lambda:**
- First 1M requests: FREE

**Total: $0/month** (until you hit 62k emails)

---

## Email Templates

### Welcome Email
```
From: noreply@marketdly.com
Subject: Welcome to MarketDly!

Hi {name},

Welcome to MarketDly! Your account is ready.

Start receiving daily trading signals:
https://marketdly.com/dashboard

Questions? Reply to support@marketdly.com

Best,
The MarketDly Team
```

### Signal Notification
```
From: noreply@marketdly.com
Subject: New Signal: {ticker} - {signal_type}

{ticker} - {signal_type}
Entry: ${entry_price}
Stop: ${stop_loss}
Target: ${target}

View full analysis:
https://marketdly.com/signals/{signal_id}
```

### Support Response
```
From: support@marketdly.com
Subject: Re: {subject}

Hi {name},

[Your response here]

Best,
Uncle D
MarketDly Support
```

---

## Monitoring

**CloudWatch Alarms:**
- SES bounce rate > 5%
- SES complaint rate > 0.1%
- Email delivery failures

**Daily checks:**
- Check SES reputation dashboard
- Review bounces/complaints
- Monitor delivery rates

---

## Troubleshooting

**Emails not sending:**
1. Check SES is out of sandbox
2. Verify domain in SES console
3. Check DNS records propagated
4. Review CloudWatch logs

**Emails going to spam:**
1. Add SPF record: `v=spf1 include:amazonses.com ~all`
2. Verify DKIM configured
3. Add DMARC record: `v=DMARC1; p=none; rua=mailto:admin@marketdly.com`
4. Warm up sending (start slow)

**Not receiving emails:**
1. Check MX record configured
2. Verify receipt rule active
3. Check S3 bucket for emails
4. Review Lambda logs

---

## Priority: CRITICAL
## Timeline: Set up before launch
## Owner: Prakash
## Status: TODO

---

**Created:** December 5, 2024
**Last Updated:** December 5, 2024

# SES Production Access Request

## Use Case
Daily market analysis newsletter for stock traders and investors. Users sign up via website (marketdly.com) to receive:
- Daily market summaries with AI-powered insights
- Technical analysis and key levels to watch
- Unusual activity alerts (volume spikes, breakouts, etc.)
- Swing trade signals

## Website
https://marketdly.com

## Email Type
Transactional and Marketing (Newsletter)

## Sending Rate
- Current: ~10 emails/day
- Expected: 100-500 emails/day within 3 months
- Peak: 1,000 emails/day within 6 months

## Compliance
- Double opt-in via website waitlist form
- Unsubscribe link in every email
- Bounce/complaint handling via SNS notifications
- No purchased lists - only organic signups

## Bounce/Complaint Handling
- SNS topics configured for bounces and complaints
- Automatic removal of bounced/complained emails from waitlist
- Monitoring via CloudWatch metrics
- Bounce rate target: <5%
- Complaint rate target: <0.1%

## From Address
daily@mrktdly.com (verified)

## Reply-To Address
support@mrktdly.com

## Content
Educational market analysis and trading insights. No spam, no promotional content from third parties.

---

## How to Submit

1. Go to AWS Console → SES → Account Dashboard
2. Click "Request production access"
3. Fill in the form with above details
4. Submit request

Typical approval time: 24-48 hours

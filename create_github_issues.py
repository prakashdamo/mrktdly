#!/usr/bin/env python3
"""
Create GitHub issues for MarketDly launch blockers.

Usage:
    export GITHUB_TOKEN=your_token_here
    python3 create_github_issues.py
    
Or:
    python3 create_github_issues.py YOUR_TOKEN_HERE
"""

import requests
import sys
import os

REPO_OWNER = "prakashdamo"
REPO_NAME = "mrktdly"

issues = [
    {
        "title": "🔴 Create Login/Signup Page with Cognito Integration",
        "body": """**Priority:** 🔴 Critical - Blocking Launch
**Labels:** authentication, frontend, critical
**Estimate:** 30 minutes

## Description
Users cannot sign in or create accounts. All "Sign In" buttons redirect to dashboard which requires auth, creating an infinite loop.

## Acceptance Criteria
- [ ] Create login.html page with Cognito Hosted UI integration
- [ ] Add "Sign In" and "Sign Up" tabs/buttons
- [ ] Configure Cognito redirect URLs
- [ ] Test successful login flow
- [ ] Test successful signup flow

## Technical Details
- Use AWS Cognito Hosted UI or custom form with amazon-cognito-identity-js
- Redirect after login: `/dashboard.html`
- Store tokens in localStorage
- Update auth-helper.js redirect from `/index.html` to `/login.html`

## Files to Modify
- Create: `/website/login.html`
- Update: `/website/js/auth-helper.js` (change redirect target)""",
        "labels": ["authentication", "frontend", "critical", "blocking-launch"]
    },
    {
        "title": "🔴 Update All CTAs to Point to Login Page",
        "body": """**Priority:** 🔴 Critical - Blocking Launch
**Labels:** frontend, navigation, critical
**Estimate:** 15 minutes

## Description
Homepage, pricing page, and navigation "Sign In" buttons all point to `/dashboard.html` which requires authentication, causing redirect loops.

## Acceptance Criteria
- [ ] Update homepage "Sign In" button → `/login.html`
- [ ] Update homepage "Start Free Trial" → `/login.html?mode=signup`
- [ ] Update pricing page "Subscribe" buttons → `/login.html?mode=signup&tier=basic|pro`
- [ ] Update navigation "Sign In" → `/login.html`
- [ ] Add "Sign Up" button to navigation

## Files to Modify
- `/website/index.html`
- `/website/pricing.html`
- `/website/js/nav.js`""",
        "labels": ["frontend", "navigation", "critical", "blocking-launch"]
    },
    {
        "title": "🔴 Enable Tier Gating on Protected Pages",
        "body": """**Priority:** 🔴 Critical - Blocking Launch
**Labels:** backend, security, critical
**Estimate:** 30 minutes

## Description
Performance page has tier gating disabled (`tier = 'pro'` hardcoded). Dashboard ticker analysis and portfolio pages have no tier checks. Users can access Pro features without paying.

## Acceptance Criteria
- [ ] Remove `tier = 'pro'` override in performance.html
- [ ] Add tier check to dashboard ticker analysis (Pro only)
- [ ] Add tier check to portfolio page (Pro only)
- [ ] Show upgrade prompts for insufficient tier
- [ ] Test Free user cannot access signals
- [ ] Test Basic user can access performance page
- [ ] Test Pro user can access all features

## Technical Details
- Use existing `getUserTier()` function
- Show upgrade modal/banner for blocked features
- Free: Dashboard, Market Intelligence, Blog only
- Basic: + Performance page, signals (7-day history)
- Pro: + Ticker analysis, Portfolio, full history

## Files to Modify
- `/website/performance.html` (line 152: remove tier override)
- `/website/dashboard.html` (add tier check to analyzeTicker())
- `/website/portfolio.html` (add tier check on page load)""",
        "labels": ["backend", "security", "critical", "blocking-launch"]
    },
    {
        "title": "🔴 Implement 7-Day Signal History Filter for Basic Tier",
        "body": """**Priority:** 🔴 Critical - Blocking Launch
**Labels:** backend, tier-gating, critical
**Estimate:** 30 minutes

## Description
Basic tier advertises "7-day signal history" but performance page shows all signals regardless of tier.

## Acceptance Criteria
- [ ] Filter closed signals to last 7 days for Basic tier
- [ ] Show "Upgrade to Pro for full history" message
- [ ] Pro tier sees all signals (no filter)
- [ ] Test Basic user sees only 7 days
- [ ] Test Pro user sees all history

## Technical Details
- Filter in `loadModelPerformance()` function
- Compare signal date with `new Date() - 7 days`
- Add upgrade banner below closed signals for Basic users

## Files to Modify
- `/website/performance.html` (loadModelPerformance function)""",
        "labels": ["backend", "tier-gating", "critical", "blocking-launch"]
    },
    {
        "title": "🔴 Connect Stripe Checkout to Pricing Page",
        "body": """**Priority:** 🔴 Critical - Blocking Launch
**Labels:** payments, stripe, critical
**Estimate:** 1 hour

## Description
"Subscribe" buttons on pricing page don't trigger Stripe checkout. Users cannot pay for Basic or Pro tiers.

## Acceptance Criteria
- [ ] Create Stripe checkout sessions for Basic ($9.99/mo)
- [ ] Create Stripe checkout sessions for Pro ($19.99/mo)
- [ ] Update pricing page buttons to call checkout Lambda
- [ ] Configure success/cancel URLs
- [ ] Test successful payment flow
- [ ] Verify subscription created in Stripe
- [ ] Verify DynamoDB updated via webhook

## Technical Details
- Use existing `mrktdly-stripe-checkout` Lambda
- Success URL: `/success.html?session_id={CHECKOUT_SESSION_ID}`
- Cancel URL: `/pricing.html`
- Pass user email and tier to Lambda

## Files to Modify
- `/website/pricing.html` (add checkout JavaScript)
- `/lambda/stripe-checkout/lambda_function.py` (verify configuration)
- Create: `/website/success.html` (payment success page)""",
        "labels": ["payments", "stripe", "critical", "blocking-launch"]
    },
    {
        "title": "🔴 Test and Verify Stripe Webhook Integration",
        "body": """**Priority:** 🔴 Critical - Blocking Launch
**Labels:** payments, stripe, testing, critical
**Estimate:** 30 minutes

## Description
Stripe webhook Lambda exists but hasn't been tested end-to-end. Need to verify payment → webhook → DynamoDB subscription update flow.

## Acceptance Criteria
- [ ] Configure Stripe webhook endpoint URL
- [ ] Test `checkout.session.completed` event
- [ ] Verify subscription record created in mrktdly-subscriptions table
- [ ] Test `customer.subscription.updated` event
- [ ] Test `customer.subscription.deleted` event (cancellation)
- [ ] Verify tier changes reflected immediately
- [ ] Test failed payment handling

## Technical Details
- Webhook URL: API Gateway endpoint for mrktdly-stripe-webhook
- Verify webhook signing secret configured
- Check CloudWatch logs for errors
- Test with Stripe CLI: `stripe trigger checkout.session.completed`

## Files to Verify
- `/lambda/stripe-webhook/lambda_function.py`
- DynamoDB table: `mrktdly-subscriptions`""",
        "labels": ["payments", "stripe", "testing", "critical", "blocking-launch"]
    },
    {
        "title": "🟡 Add Upgrade Prompts for Free Tier Limits",
        "body": """**Priority:** 🟡 Important - Should Fix
**Labels:** frontend, monetization, enhancement
**Estimate:** 30 minutes

## Description
Free tier users can hit usage limits but don't see clear upgrade prompts. Need to guide them to paid tiers.

## Acceptance Criteria
- [ ] Show upgrade modal when free user tries to access signals
- [ ] Show upgrade modal when free user tries ticker analysis
- [ ] Show upgrade modal when free user tries portfolio
- [ ] Include pricing comparison in modal
- [ ] "Upgrade Now" button → pricing page
- [ ] Track upgrade prompt impressions

## Files to Modify
- `/website/performance.html`
- `/website/dashboard.html`
- `/website/portfolio.html`
- Create: `/website/js/upgrade-modal.js`""",
        "labels": ["frontend", "monetization", "enhancement"]
    },
    {
        "title": "🟡 Test Cognito Post-Signup Welcome Email",
        "body": """**Priority:** 🟡 Important - Should Fix
**Labels:** authentication, email, testing
**Estimate:** 15 minutes

## Description
Cognito post-signup trigger exists but welcome email hasn't been verified.

## Acceptance Criteria
- [ ] Create test account via signup flow
- [ ] Verify welcome email received
- [ ] Check email formatting and links
- [ ] Verify email comes from correct sender
- [ ] Test email on mobile and desktop clients

## Files to Verify
- `/lambda/cognito-post-signup/lambda_function.py`""",
        "labels": ["authentication", "email", "testing"]
    },
    {
        "title": "🟡 Add User-Friendly Error Messages",
        "body": """**Priority:** 🟡 Important - Should Fix
**Labels:** frontend, ux, enhancement
**Estimate:** 30 minutes

## Description
API errors show raw error messages or fail silently. Need user-friendly error handling.

## Acceptance Criteria
- [ ] Add error toast/banner component
- [ ] Handle authentication errors (session expired)
- [ ] Handle API errors (500, 503)
- [ ] Handle network errors (offline)
- [ ] Handle payment errors (card declined)
- [ ] Show actionable error messages

## Files to Modify
- `/website/js/auth-helper.js`
- Create: `/website/js/error-handler.js`""",
        "labels": ["frontend", "ux", "enhancement"]
    },
    {
        "title": "🟢 Make Historical Performance Stats Public",
        "body": """**Priority:** 🟢 Nice to Have - Post-Launch
**Labels:** frontend, marketing, enhancement
**Estimate:** 1 hour

## Description
Free tier advertises "Performance Dashboard Access" but performance page requires login. Consider making historical stats public while keeping signals private.

## Acceptance Criteria
- [ ] Create public performance stats page (no login required)
- [ ] Show overall win rate, expectancy, trade count
- [ ] Show performance charts
- [ ] Hide individual signal details (require login)
- [ ] Add "Sign up to see signals" CTA
- [ ] Update pricing page to reflect public stats

## Files to Create
- `/website/public-performance.html`""",
        "labels": ["frontend", "marketing", "enhancement", "post-launch"]
    }
]

def create_issues(token):
    """Create GitHub issues using the API"""
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    
    created = []
    failed = []
    
    for issue in issues:
        print(f"Creating: {issue['title']}")
        
        response = requests.post(url, json=issue, headers=headers)
        
        if response.status_code == 201:
            issue_data = response.json()
            created.append(issue_data['html_url'])
            print(f"  ✓ Created: {issue_data['html_url']}")
        else:
            failed.append((issue['title'], response.status_code, response.text))
            print(f"  ✗ Failed: {response.status_code}")
    
    print(f"\n{'='*70}")
    print(f"Summary: {len(created)} created, {len(failed)} failed")
    print(f"{'='*70}\n")
    
    if created:
        print("Created issues:")
        for url in created:
            print(f"  - {url}")
    
    if failed:
        print("\nFailed issues:")
        for title, code, error in failed:
            print(f"  - {title} (HTTP {code})")
            print(f"    {error[:100]}")

if __name__ == "__main__":
    # Get token from argument or environment
    token = None
    
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        token = os.environ.get('GITHUB_TOKEN')
    
    if not token:
        print("Error: GitHub token required")
        print("\nUsage:")
        print("  export GITHUB_TOKEN=your_token_here")
        print("  python3 create_github_issues.py")
        print("\nOr:")
        print("  python3 create_github_issues.py YOUR_TOKEN_HERE")
        print("\nCreate a token at: https://github.com/settings/tokens")
        print("Required scope: 'repo'")
        sys.exit(1)
    
    create_issues(token)

# MrktDly Scripts

## User Statistics

### Quick Stats (One Line)
```bash
./scripts/quick_stats.sh
```
Output: `👥 Users: 1 | ✅ Confirmed: 1 | 🆕 Today: 1`

### Full Dashboard
```bash
./scripts/user_stats.sh
```

Shows:
- Total users
- Confirmed vs pending
- New signups today
- Active users (24h)
- Recent user list
- Cache statistics
- Top analyzed tickers

### Manual Queries

**List all users:**
```bash
aws cognito-idp list-users \
  --user-pool-id us-east-1_N5yuAGHc3 \
  --region us-east-1
```

**Count only:**
```bash
aws cognito-idp list-users \
  --user-pool-id us-east-1_N5yuAGHc3 \
  --region us-east-1 \
  --query 'length(Users)' \
  --output text
```

**User emails:**
```bash
aws cognito-idp list-users \
  --user-pool-id us-east-1_N5yuAGHc3 \
  --region us-east-1 \
  --query 'Users[*].Attributes[?Name==`email`].Value' \
  --output text
```

## Cache Statistics

**Cached tickers:**
```bash
aws dynamodb scan \
  --table-name mrktdly-ticker-cache \
  --region us-east-1 \
  --query 'Items[*].ticker.S' \
  --output text
```

**Cache count:**
```bash
aws dynamodb scan \
  --table-name mrktdly-ticker-cache \
  --select COUNT \
  --region us-east-1 \
  --query 'Count' \
  --output text
```

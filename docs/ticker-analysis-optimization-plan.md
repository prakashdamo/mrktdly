# Ticker Analysis Page Optimization - Test Plan

## Problem Statement

**Current Issue:** Ticker analysis page takes 8+ seconds to load after clicking "Analyze"

**Root Causes Identified:**
1. Sequential API calls (ticker-analysis → health-score → signal-stats)
2. Claude AI analysis in critical path (~5-7 seconds)
3. Comprehensive analysis Lambda call (~2-3 seconds)
4. No caching strategy for expensive operations
5. Frontend waits for all data before displaying anything

**Performance Breakdown (AMD test):**
- Ticker Analysis API: 658ms (21.2%)
- Health Score API: 811ms (26.1%)
- Signal Stats API: 409ms (13.2%)
- ML Strategy API: 1,229ms (39.6%)
- **Total Sequential: 3,107ms**
- **Potential with Parallel: ~1,229ms (60% improvement)**

## Optimization Strategy

### Phase 1: Quick Wins (No Breaking Changes)
**Goal:** Reduce load time from 8s to 2s
**Risk:** Low
**Effort:** 2 hours

1. **Make API calls parallel in frontend**
   - Change: `Promise.all()` instead of sequential awaits
   - Impact: Save ~1.9s (60% of API time)
   - Test: Verify all data still loads correctly

2. **Add performance monitoring**
   - Add: Console timing logs
   - Impact: Visibility into bottlenecks
   - Test: Check browser console shows timing

### Phase 2: Backend Optimization (Moderate Risk)
**Goal:** Reduce load time from 2s to 0.5s
**Risk:** Medium
**Effort:** 4 hours

1. **Remove AI analysis from critical path**
   - Change: Return `analysis: null` initially
   - Impact: Save ~5-7s on cache miss
   - Test: Page displays without AI, shows "Loading..."

2. **Remove comprehensive analysis call**
   - Change: Skip Lambda-to-Lambda call
   - Impact: Save ~2-3s
   - Test: Page works without comprehensive data

3. **Add async AI loading endpoint**
   - New: `/ai-analysis?ticker=X` endpoint
   - Impact: AI loads in background
   - Test: AI populates after page loads

### Phase 3: Caching Strategy (Low Risk)
**Goal:** Instant loads for cached tickers
**Risk:** Low
**Effort:** 2 hours

1. **Pre-cache popular tickers**
   - Add: EventBridge rule every 5 minutes
   - Cache: Top 20 tickers (SPY, QQQ, AAPL, etc.)
   - Test: Popular tickers load in <500ms

2. **Extend cache TTL**
   - Change: 5 min → 15 min for ticker analysis
   - Impact: More cache hits
   - Test: Verify stale data acceptable

## Test Plan

### Pre-Deployment Tests

#### 1. API Response Structure Tests
```bash
# Test ticker-analysis returns correct structure
curl -X POST .../ticker-analysis -d '{"ticker":"AAPL"}' | jq 'keys'
# Expected: ["ticker", "data", "analysis", "comprehensive", "projection"]

# Test health-score has CORS
curl -I .../health-score?ticker=AAPL | grep access-control
# Expected: access-control-allow-origin: *

# Test signal-stats works
curl .../signal-stats?ticker=AAPL | jq '.total_signals'
# Expected: number
```

#### 2. Lambda Function Tests
```bash
# Test ticker-analysis Lambda
aws lambda invoke --function-name mrktdly-ticker-analysis \
  --payload '{"body":"{\"ticker\":\"AAPL\"}"}' /tmp/out.json
cat /tmp/out.json | jq '.statusCode'
# Expected: 200

# Test health-score Lambda
aws lambda invoke --function-name mrktdly-technical-health-score \
  --payload '{"ticker":"AAPL"}' /tmp/out.json
cat /tmp/out.json | jq '.statusCode'
# Expected: 200
```

#### 3. Frontend Unit Tests
```javascript
// Test parallel loading
const start = performance.now();
await loadAllDataParallel('AAPL');
const duration = performance.now() - start;
console.assert(duration < 2000, 'Parallel load should be <2s');

// Test null analysis handling
const data = {ticker: 'AAPL', data: {...}, analysis: null};
displayAnalysis(data); // Should not throw error
```

### Deployment Tests

#### 1. Smoke Tests (After Each Deploy)
```bash
# Test 1: Page loads without errors
curl -s https://mrktdly.com/ticker-analysis.html | grep "Ticker Analysis"
# Expected: HTML with title

# Test 2: API endpoints respond
for endpoint in ticker-analysis health-score signal-stats; do
  curl -s .../prod/$endpoint?ticker=AAPL | jq '.error // "OK"'
done
# Expected: All return "OK" or valid data

# Test 3: Cache is working
curl -X POST .../ticker-analysis -d '{"ticker":"SPY"}' -w "%{time_total}\n"
curl -X POST .../ticker-analysis -d '{"ticker":"SPY"}' -w "%{time_total}\n"
# Expected: Second call faster than first
```

#### 2. Performance Tests
```bash
# Test popular tickers (should be fast)
for ticker in SPY QQQ AAPL MSFT NVDA; do
  time curl -X POST .../ticker-analysis -d "{\"ticker\":\"$ticker\"}"
done
# Expected: <1s for cached, <3s for uncached

# Test parallel vs sequential
node test_parallel_performance.js
# Expected: Parallel saves >50% time
```

#### 3. Browser Tests
```javascript
// Open DevTools Console
// Test 1: Analyze AAPL
// Expected: 
// - "Loading health score and signals for AAPL"
// - "Health data: {...}"
// - "Signal data: {...}"
// - Page displays in <2s

// Test 2: Check for errors
// Expected: No red errors in console

// Test 3: Verify all sections load
document.querySelectorAll('[id*="loading"]').length === 0
// Expected: true (no loading spinners stuck)
```

### Rollback Criteria

**Rollback if:**
1. Error rate > 5% (check CloudWatch)
2. Load time > 10s (worse than before)
3. Any section permanently shows "Loading..."
4. CORS errors in browser console
5. Cache hit rate < 50% for popular tickers

**Rollback command:**
```bash
cd /home/prakash/marketdly
git checkout HEAD~1 website/ticker-analysis.html
git checkout HEAD~1 lambda/ticker-analysis/lambda_function.py
# Deploy reverted versions
```

## Optimized Execution Plan

### Step 1: Baseline Measurement (15 min)
```bash
# Create performance test script
node create_baseline_test.js
# Run 10 times, record average
# Document: Current avg load time, cache hit rate
```

### Step 2: Frontend Parallel Loading (30 min)
```bash
# Change: Promise.all() for health + signals
# Test: Verify both load, check console logs
# Deploy: Frontend only
# Measure: Should see ~60% improvement in API time
```

### Step 3: Backend Optimization (1 hour)
```bash
# Change: Remove AI + comprehensive from critical path
# Test: Verify page displays with analysis: null
# Deploy: Lambda + Frontend
# Measure: Should see <2s load time
```

### Step 4: Validation (15 min)
```bash
# Test 5 popular tickers
# Test 5 random tickers
# Check error logs
# Verify cache working
```

### Step 5: Monitor (24 hours)
```bash
# Watch CloudWatch metrics
# Check error rate
# Monitor user feedback
# Adjust cache TTL if needed
```

## Success Metrics

**Before:**
- Load time: 8+ seconds
- Cache hit rate: Unknown
- User experience: Long wait, spinner

**After (Target):**
- Load time: <2s (cached), <3s (uncached)
- Cache hit rate: >70% for popular tickers
- User experience: Instant display, progressive loading

**Measurement:**
```bash
# Average load time
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=mrktdly-ticker-analysis \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average

# Error rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=mrktdly-ticker-analysis \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

## Risk Mitigation

### Risk 1: Breaking Changes
**Mitigation:** 
- Test with 5 different tickers before deploy
- Keep rollback script ready
- Deploy during low-traffic hours

### Risk 2: Cache Inconsistency
**Mitigation:**
- Add cache version to key
- Clear cache on deploy
- Monitor stale data complaints

### Risk 3: CORS Issues
**Mitigation:**
- Test CORS headers before deploy
- Add OPTIONS handler to all endpoints
- Test from actual domain, not localhost

### Risk 4: Null Pointer Errors
**Mitigation:**
- Add null checks for all optional fields
- Test with analysis: null explicitly
- Add error boundaries in frontend

## Review & Optimization

### Plan Review

**Strengths:**
✅ Phased approach with clear rollback points
✅ Specific success metrics
✅ Comprehensive test coverage
✅ Risk mitigation strategies

**Weaknesses:**
❌ No load testing (what if 100 users hit at once?)
❌ No monitoring dashboard setup
❌ Missing user acceptance criteria
❌ No A/B testing plan

### Optimized Plan

**Changes:**
1. **Add load testing:** Use Artillery or k6 to simulate 50 concurrent users
2. **Setup CloudWatch dashboard:** Before starting, create dashboard with key metrics
3. **Add feature flag:** Use environment variable to toggle optimization on/off
4. **Simplify Phase 2:** Skip AI async endpoint initially, just return null and cache with AI later
5. **Add canary deployment:** Deploy to 10% of users first

**Revised Timeline:**
- Setup (monitoring + baseline): 30 min
- Phase 1 (parallel loading): 30 min
- Phase 2 (backend optimization): 1 hour
- Phase 3 (caching): 30 min
- Validation + monitoring: 30 min
- **Total: 3.5 hours** (down from 8 hours)

**Key Simplification:**
Instead of creating new AI endpoint, just:
1. Return analysis: null on cache miss
2. Show "Loading..." in UI
3. Next request will have cached AI analysis
4. User refreshes or comes back later, it's there

This avoids:
- New Lambda function
- New API Gateway route
- Complex async loading logic
- CORS configuration for new endpoint

**Result:** Same user experience, 50% less code, 50% less risk.

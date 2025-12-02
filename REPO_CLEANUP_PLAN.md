# Repository Cleanup Plan

## 📋 Current Issues

### 1. **Root Directory Clutter** (Too many files in root)
- 22 untracked files
- Multiple backtest scripts
- Analysis scripts
- Documentation files scattered

### 2. **Temporary/Test Files**
- `.weekend-work-summary.txt.swp` (vim swap file)
- `output.json` (test output)
- `backtest_results.txt` (old results)
- `email_preview.html` (test file)

### 3. **Duplicate/Old Documentation**
- Multiple SUMMARY files
- Old deployment docs
- Scattered markdown files

---

## 🗂️ Proposed Structure

```
marketdly/
├── docs/                    # All documentation
│   ├── deployment/
│   │   ├── AWS_DEPLOYMENT.md
│   │   ├── DEPLOYMENT.md
│   │   ├── DEPLOYMENT_SUMMARY.md
│   │   └── DEPLOYMENT_CHECKLIST.md
│   ├── features/
│   │   ├── FEATURE_RECOMMENDATIONS.md
│   │   ├── HEALTH_SCORE_INTEGRATION.md
│   │   ├── BACKTEST_TOOL_DISCUSSION.md
│   │   └── IMPLEMENTATION_SUMMARY.md
│   ├── technical/
│   │   ├── SYSTEM_FLOW.md
│   │   ├── ALGORITHM_IMPROVEMENTS.md
│   │   ├── ML_FEATURES.md
│   │   └── MODEL_SUMMARY.txt
│   ├── guides/
│   │   ├── TESTING.md
│   │   ├── CONTRIBUTING.md
│   │   └── READY_TO_TEST.md
│   └── summaries/
│       ├── SWING_SCANNER_SUMMARY.md
│       ├── SIGNAL_TRACKING_SUMMARY.md
│       ├── BACKTEST_SUMMARY.md
│       └── UI_ANALYSIS.md
│
├── scripts/                 # All utility scripts
│   ├── analysis/
│   │   ├── analyze_market_weakness.py
│   │   ├── analyze_signal_timing.py
│   │   ├── assess_data_quality.py
│   │   └── discover_patterns.py
│   ├── backtest/
│   │   ├── backtest_pltr_2025.py
│   │   ├── backtest_hims_2025.py
│   │   ├── backtest_tsla_2025.py
│   │   ├── backtest_bb_2025.py
│   │   ├── backtest_mag7_2025.py
│   │   ├── backtest_swings.py
│   │   ├── backtest_3months.py
│   │   ├── backtest_full_year.py
│   │   ├── backtest_last_week.py
│   │   ├── backtest_last_month.py
│   │   ├── backtest_current_signals.py
│   │   ├── backtest_ml_strategy.py
│   │   └── run_backtest.sh
│   ├── prediction/
│   │   ├── predict_2026_portfolio.py
│   │   ├── predict_etfs_2026.py
│   │   └── optimal_portfolio_2025.py
│   ├── deployment/
│   │   ├── deploy-health-score.sh
│   │   ├── deploy-signal-tracking.sh
│   │   ├── deploy-swing-scanner.sh
│   │   └── setup-price-history.sh
│   ├── data/
│   │   ├── backfill_signals.py
│   │   ├── backfill_new_tickers.py
│   │   ├── backfill_from_date.py
│   │   └── regenerate_last_week.py
│   ├── ml/
│   │   ├── train_models.py
│   │   ├── convert_onnx.py
│   │   └── optimize_ticker_strategy.py
│   └── testing/
│       ├── test-health-score-integration.sh
│       ├── test-email-with-swings.sh
│       ├── test-pipeline.sh
│       ├── test-bedrock.sh
│       ├── test_email_preview.py
│       └── run_tests.sh
│
├── lambda/                  # Lambda functions (keep as is)
├── infrastructure/          # Infrastructure configs (keep as is)
├── website/                 # Frontend files (keep as is)
├── ml/                      # ML models (keep as is)
├── tests/                   # Unit tests (keep as is)
├── .github/                 # GitHub configs (keep as is)
├── .venv/                   # Virtual env (keep as is)
│
├── README.md               # Main readme
├── .gitignore              # Git ignore
├── requirements-test.txt   # Test requirements
├── requirements-lint.txt   # Lint requirements
└── lambda_fallback.py      # Keep in root (used by lambdas)
```

---

## 🗑️ Files to DELETE

### Temporary/Test Files:
- [ ] `.weekend-work-summary.txt.swp` (vim swap file)
- [ ] `output.json` (test output)
- [ ] `backtest_results.txt` (old results)
- [ ] `email_preview.html` (test file)
- [ ] `ses-production-request.md` (one-time request)
- [ ] `frontend/` directory (if empty or unused)

---

## 📁 Files to MOVE

### To `docs/deployment/`:
- [ ] AWS_DEPLOYMENT.md
- [ ] DEPLOYMENT.md
- [ ] DEPLOYMENT_SUMMARY.md
- [ ] DEPLOYMENT_CHECKLIST.md
- [ ] PRICE_HISTORY_SETUP.md

### To `docs/features/`:
- [ ] FEATURE_RECOMMENDATIONS.md
- [ ] HEALTH_SCORE_INTEGRATION.md
- [ ] BACKTEST_TOOL_DISCUSSION.md
- [ ] IMPLEMENTATION_SUMMARY.md
- [ ] MARKET_INSIGHTS.md
- [ ] UI_ANALYSIS.md
- [ ] UI_IMPROVEMENTS_PHASE1.md

### To `docs/technical/`:
- [ ] SYSTEM_FLOW.md
- [ ] ALGORITHM_IMPROVEMENTS.md
- [ ] ML_FEATURES.md
- [ ] MODEL_SUMMARY.txt

### To `docs/guides/`:
- [ ] TESTING.md
- [ ] CONTRIBUTING.md
- [ ] READY_TO_TEST.md

### To `docs/summaries/`:
- [ ] SUMMARY.md
- [ ] SWING_SCANNER.md
- [ ] SWING_SCANNER_SUMMARY.md
- [ ] SWING_SCANNER_V3_SUMMARY.md
- [ ] SIGNAL_TRACKING.md
- [ ] SIGNAL_TRACKING_SUMMARY.md
- [ ] BACKTEST_SUMMARY.md

### To `scripts/analysis/`:
- [ ] analyze_market_weakness.py
- [ ] analyze_signal_timing.py
- [ ] assess_data_quality.py
- [ ] discover_patterns.py

### To `scripts/backtest/`:
- [ ] backtest_*.py (all backtest scripts)
- [ ] run_backtest.sh

### To `scripts/prediction/`:
- [ ] predict_2026_portfolio.py
- [ ] predict_etfs_2026.py
- [ ] optimal_portfolio_2025.py

### To `scripts/deployment/`:
- [ ] deploy-health-score.sh
- [ ] deploy-signal-tracking.sh
- [ ] deploy-swing-scanner.sh
- [ ] setup-price-history.sh

### To `scripts/data/`:
- [ ] backfill_signals.py
- [ ] backfill_new_tickers.py
- [ ] backfill_from_date.py
- [ ] regenerate_last_week.py

### To `scripts/ml/`:
- [ ] train_models.py
- [ ] convert_onnx.py
- [ ] optimize_ticker_strategy.py

### To `scripts/testing/`:
- [ ] test-*.sh (all test scripts)
- [ ] test_*.py (all test scripts)
- [ ] run_tests.sh

---

## ✅ Files to KEEP in Root

- README.md
- .gitignore
- requirements-test.txt
- requirements-lint.txt
- lambda_fallback.py (used by lambdas)

---

## 🔧 Implementation Script

Run this to execute the cleanup:

```bash
cd /home/prakash/marketdly

# Create new directory structure
mkdir -p docs/{deployment,features,technical,guides,summaries}
mkdir -p scripts/{analysis,backtest,prediction,deployment,data,ml,testing}

# Move documentation
mv AWS_DEPLOYMENT.md DEPLOYMENT.md DEPLOYMENT_SUMMARY.md DEPLOYMENT_CHECKLIST.md PRICE_HISTORY_SETUP.md docs/deployment/
mv FEATURE_RECOMMENDATIONS.md HEALTH_SCORE_INTEGRATION.md BACKTEST_TOOL_DISCUSSION.md IMPLEMENTATION_SUMMARY.md MARKET_INSIGHTS.md UI_ANALYSIS.md UI_IMPROVEMENTS_PHASE1.md docs/features/
mv SYSTEM_FLOW.md ALGORITHM_IMPROVEMENTS.md ML_FEATURES.md MODEL_SUMMARY.txt docs/technical/
mv TESTING.md CONTRIBUTING.md READY_TO_TEST.md docs/guides/
mv SUMMARY.md SWING_SCANNER*.md SIGNAL_TRACKING*.md BACKTEST_SUMMARY.md docs/summaries/

# Move scripts
mv analyze_*.py assess_data_quality.py discover_patterns.py scripts/analysis/
mv backtest_*.py run_backtest.sh scripts/backtest/
mv predict_*.py optimal_portfolio_2025.py scripts/prediction/
mv deploy-*.sh setup-price-history.sh scripts/deployment/
mv backfill_*.py regenerate_last_week.py scripts/data/
mv train_models.py convert_onnx.py optimize_ticker_strategy.py scripts/ml/
mv test-*.sh test_*.py run_tests.sh scripts/testing/

# Delete temporary files
rm -f .weekend-work-summary.txt.swp output.json backtest_results.txt email_preview.html ses-production-request.md

# Update .gitignore
echo "*.swp" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".venv/" >> .gitignore
echo "output.json" >> .gitignore
echo "*.log" >> .gitignore

# Git add all changes
git add -A
git commit -m "Reorganize repository structure - move docs and scripts to dedicated folders"
```

---

## 📊 Before vs After

### Before:
```
marketdly/
├── 60+ files in root (cluttered)
├── lambda/
├── website/
└── ...
```

### After:
```
marketdly/
├── docs/           # All documentation organized
├── scripts/        # All scripts organized
├── lambda/         # Lambda functions
├── infrastructure/ # Infrastructure
├── website/        # Frontend
├── ml/             # ML models
├── tests/          # Unit tests
└── 5 files in root (clean)
```

---

## ✅ Benefits

1. **Cleaner root directory** - Only 5 essential files
2. **Better organization** - Easy to find files
3. **Logical grouping** - Related files together
4. **Easier navigation** - Clear folder structure
5. **Better for new contributors** - Obvious where things go
6. **Easier maintenance** - Know where to add new files

---

## 🚀 Next Steps

1. Review this plan
2. Run the implementation script
3. Test that nothing breaks
4. Update README with new structure
5. Commit changes to git

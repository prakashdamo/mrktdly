#!/usr/bin/env python3
"""Train improved models with SMOTE"""
import pickle

import boto3
import numpy as np
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
features_table = dynamodb.Table('mrktdly-features')

print("Fetching training data...")
response = features_table.scan()
items = response['Items']
while 'LastEvaluatedKey' in response:
    response = features_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response['Items'])

print(f"Loaded {len(items)} records")

# Prepare features
X, y = [], []
for item in items:
    try:
        X.append([
            float(item.get('return_5d', 0)),
            float(item.get('return_20d', 0)),
            float(item.get('volatility', 0)),
            float(item.get('rsi', 50)),
            float(item.get('atr', 0)),
            float(item.get('vol_ratio', 1)),
            int(item.get('above_ma20', 0)),
            int(item.get('above_ma50', 0)),
            int(item.get('above_ma200', 0)),
            int(item.get('ma_alignment', 0)),
            float(item.get('pct_from_high', 0)),
            float(item.get('pct_from_low', 0))
        ])
        y.append(1 if item.get('label') in ['big_move', '1', 1] else 0)
    except (ValueError, TypeError, KeyError):
        continue

X = np.array(X)
y = np.array(y)

print(f"Training samples: {len(X)}")
counts = np.bincount(y)
if len(counts) == 2:
    pct_0 = 100 * counts[0] / len(y)
    pct_1 = 100 * counts[1] / len(y)
    print(f"Class distribution: {counts} ({pct_0:.1f}% no_move, {pct_1:.1f}% big_move)")
else:
    print(f"Class distribution: {counts} (only one class found)")

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Apply SMOTE
print("\nApplying SMOTE...")
smote = SMOTE(random_state=42)
X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
print(f"After SMOTE: {len(X_train_balanced)} samples, {np.bincount(y_train_balanced)}")

# Train stock predictor
print("\nTraining stock predictor...")
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    class_weight={0: 1, 1: 3},
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_balanced, y_train_balanced)

# Find optimal threshold
y_proba = model.predict_proba(X_test)[:, 1]
thresholds = np.arange(0.3, 0.9, 0.01)
best_threshold, best_f1 = 0.5, 0
for t in thresholds:
    y_pred = (y_proba >= t).astype(int)
    tp = np.sum((y_pred == 1) & (y_test == 1))
    fp = np.sum((y_pred == 1) & (y_test == 0))
    fn = np.sum((y_pred == 0) & (y_test == 1))
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    if f1 > best_f1:
        best_f1, best_threshold = f1, t

print(f"Optimal threshold: {best_threshold:.3f}")

# Test performance
y_pred = (y_proba >= best_threshold).astype(int)
tp = np.sum((y_pred == 1) & (y_test == 1))
fp = np.sum((y_pred == 1) & (y_test == 0))
fn = np.sum((y_pred == 0) & (y_test == 1))
precision = tp / (tp + fp) if (tp + fp) > 0 else 0
recall = tp / (tp + fn) if (tp + fn) > 0 else 0
print(f"Precision: {precision:.1%}, Recall: {recall:.1%}, Predictions: {np.sum(y_pred)}/{len(y_test)}")

# Save
with open('stock_predictor_smote.pkl', 'wb') as f:
    pickle.dump({'model': model, 'threshold': best_threshold}, f)
print("✓ Saved stock_predictor_smote.pkl")

# Train state classifier (4 features)
print("\nTraining state classifier...")
X_state, y_state = [], []
for item in items:
    try:
        X_state.append([
            float(item.get('return_5d', 0)),
            float(item.get('return_20d', 0)),
            float(item.get('volatility', 0)),
            float(item.get('rsi', 50))
        ])
        # Classify as BULL/NEUTRAL/BEAR
        ret_20d = float(item.get('return_20d', 0))
        if ret_20d > 5:
            y_state.append('BULL')
        elif ret_20d < -5:
            y_state.append('BEAR')
        else:
            y_state.append('NEUTRAL')
    except (ValueError, TypeError, KeyError):
        continue

X_state = np.array(X_state)
y_state = np.array(y_state)

state_model = RandomForestClassifier(
    n_estimators=50, max_depth=5, random_state=42, n_jobs=-1
)
state_model.fit(X_state, y_state)

with open('state_classifier_fixed.pkl', 'wb') as f:
    pickle.dump(state_model, f)
print("✓ Saved state_classifier_fixed.pkl")

# Train strategy optimizer (8 features)
print("\nTraining strategy optimizer...")
X_strategy, y_target, y_stop = [], [], []
for item in items:
    try:
        X_strategy.append([
            float(item.get('rsi', 50)),
            float(item.get('volatility', 0)),
            float(item.get('return_5d', 0)),
            float(item.get('return_20d', 0)),
            float(item.get('vol_ratio', 1)),
            int(item.get('above_ma20', 0)),
            int(item.get('above_ma50', 0)),
            float(item.get('pct_from_high', 0))
        ])
        vol = float(item.get('volatility', 5))
        y_target.append(min(vol * 0.8, 10))
        y_stop.append(min(vol * 0.4, 5))
    except (ValueError, TypeError, KeyError):
        continue

X_strategy = np.array(X_strategy)
y_target = np.array(y_target)
y_stop = np.array(y_stop)

target_model = RandomForestRegressor(
    n_estimators=50, max_depth=5, random_state=42, n_jobs=-1
)
target_model.fit(X_strategy, y_target)

stop_model = RandomForestRegressor(
    n_estimators=50, max_depth=5, random_state=42, n_jobs=-1
)
stop_model.fit(X_strategy, y_stop)

strategy_data = {
    'models': {
        'optimal_target': target_model,
        'optimal_stop': stop_model
    }
}

with open('strategy_optimizer_fixed.pkl', 'wb') as f:
    pickle.dump(strategy_data, f)
print("✓ Saved strategy_optimizer_fixed.pkl")

print("\n✓ All models trained successfully!")

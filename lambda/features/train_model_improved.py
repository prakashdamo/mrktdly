"""
Train ML model with improved recall for 3%+ moves
- Adds class weights to handle imbalance
- Tunes threshold for better recall
- Uses SMOTE for oversampling
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, precision_recall_curve
from imblearn.over_sampling import SMOTE
import pickle

# Load data
print('Loading training data...')
df = pd.read_csv('training_data.csv')
print(f'Loaded {len(df)} records')
print()

# Prepare features
feature_cols = [col for col in df.columns if col not in ['ticker', 'date', 'label', 'future_return_5d', 'timestamp']]
X = df[feature_cols].astype(float)
y = df['label'].astype(int)

print(f'Features: {len(feature_cols)}')
print(f'Samples: {len(X)}')
print(f'Class distribution:')
print(f'  No big move (0): {(y==0).sum()} ({(y==0).sum()/len(y)*100:.1f}%)')
print(f'  Big move (1):    {(y==1).sum()} ({(y==1).sum()/len(y)*100:.1f}%)')
print(f'  Imbalance ratio: {(y==0).sum()/(y==1).sum():.1f}:1')
print()

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f'Train: {len(X_train)} | Test: {len(X_test)}')
print()

# Apply SMOTE to balance training data
print('Applying SMOTE to balance training data...')
smote = SMOTE(random_state=42)
X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
print(f'After SMOTE: {len(X_train_balanced)} samples')
print(f'  No big move: {(y_train_balanced==0).sum()}')
print(f'  Big move:    {(y_train_balanced==1).sum()}')
print()

# Train model with class weights
print('Training Random Forest with class weights...')
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    min_samples_split=50,
    class_weight={0: 1, 1: 3},  # Penalize missing big moves 3x more
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_balanced, y_train_balanced)
print('✓ Training complete')
print()

# Evaluate with default threshold (0.5)
print('='*60)
print('EVALUATION WITH DEFAULT THRESHOLD (0.5)')
print('='*60)
y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

print('Classification Report:')
print(classification_report(y_test, y_pred, target_names=['No Move', 'Big Move']))
print()

print('Confusion Matrix:')
cm = confusion_matrix(y_test, y_pred)
print(f'True Negatives:  {cm[0,0]:4d} | False Positives: {cm[0,1]:4d}')
print(f'False Negatives: {cm[1,0]:4d} | True Positives:  {cm[1,1]:4d}')
print()

recall_default = cm[1,1] / (cm[1,1] + cm[1,0])
precision_default = cm[1,1] / (cm[1,1] + cm[0,1])
print(f'Precision: {precision_default:.1%} | Recall: {recall_default:.1%}')
print()

auc = roc_auc_score(y_test, y_pred_proba)
print(f'ROC AUC Score: {auc:.3f}')
print()

# Find optimal threshold
print('='*60)
print('FINDING OPTIMAL THRESHOLD')
print('='*60)
precisions, recalls, thresholds = precision_recall_curve(y_test, y_pred_proba)

# Find threshold that gives ~50% recall with best precision
target_recall = 0.5
best_threshold = 0.5
best_precision = 0
for p, r, t in zip(precisions, recalls, thresholds):
    if r >= target_recall and p > best_precision:
        best_precision = p
        best_threshold = t

print(f'Target recall: {target_recall:.0%}')
print(f'Optimal threshold: {best_threshold:.3f}')
print(f'Expected precision: {best_precision:.1%}')
print()

# Evaluate with optimal threshold
y_pred_optimal = (y_pred_proba >= best_threshold).astype(int)
cm_optimal = confusion_matrix(y_test, y_pred_optimal)

print('='*60)
print(f'EVALUATION WITH OPTIMAL THRESHOLD ({best_threshold:.3f})')
print('='*60)
print('Classification Report:')
print(classification_report(y_test, y_pred_optimal, target_names=['No Move', 'Big Move']))
print()

print('Confusion Matrix:')
print(f'True Negatives:  {cm_optimal[0,0]:4d} | False Positives: {cm_optimal[0,1]:4d}')
print(f'False Negatives: {cm_optimal[1,0]:4d} | True Positives:  {cm_optimal[1,1]:4d}')
print()

recall_optimal = cm_optimal[1,1] / (cm_optimal[1,1] + cm_optimal[1,0])
precision_optimal = cm_optimal[1,1] / (cm_optimal[1,1] + cm_optimal[0,1])
print(f'Precision: {precision_optimal:.1%} | Recall: {recall_optimal:.1%}')
print()

print('IMPROVEMENT:')
print(f'  Recall:    {recall_default:.1%} → {recall_optimal:.1%} ({(recall_optimal/recall_default-1)*100:+.0f}%)')
print(f'  Precision: {precision_default:.1%} → {precision_optimal:.1%} ({(precision_optimal/precision_default-1)*100:+.0f}%)')
print()

# Feature importance
print('Top 10 Most Important Features:')
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for i, row in feature_importance.head(10).iterrows():
    print(f'  {row["feature"]:20s} {row["importance"]:.4f}')
print()

# Save model with optimal threshold
model_file = 'stock_predictor_improved.pkl'
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': model,
        'features': feature_cols,
        'threshold': best_threshold
    }, f)
print(f'✅ Model saved to {model_file}')
print(f'   Using threshold: {best_threshold:.3f}')
print()

# Compare predictions
print('='*60)
print('PREDICTION COMPARISON ON RECENT DATA')
print('='*60)
test_df = df[df['date'] >= '2025-11-15'].copy()
if len(test_df) > 0:
    X_recent = test_df[feature_cols].astype(float)
    proba = model.predict_proba(X_recent)[:, 1]
    
    pred_default = (proba >= 0.5).astype(int)
    pred_optimal = (proba >= best_threshold).astype(int)
    
    print(f'Old model (threshold=0.5):  {pred_default.sum()} predictions')
    print(f'New model (threshold={best_threshold:.3f}): {pred_optimal.sum()} predictions')
    print(f'Increase: {pred_optimal.sum() - pred_default.sum()} more signals ({(pred_optimal.sum()/pred_default.sum()-1)*100:+.0f}%)')
    print()
    
    # Show new predictions
    test_df['probability'] = proba
    test_df['old_pred'] = pred_default
    test_df['new_pred'] = pred_optimal
    
    new_signals = test_df[(test_df['new_pred'] == 1) & (test_df['old_pred'] == 0)].sort_values('probability', ascending=False)
    
    if len(new_signals) > 0:
        print(f'NEW SIGNALS (caught by improved model):')
        for _, row in new_signals.head(10).iterrows():
            print(f"  {row['ticker']:6s} {row['date']} | Probability: {row['probability']:.1%}")

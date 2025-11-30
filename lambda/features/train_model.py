"""
Train ML model to predict 3%+ moves in next 5 days
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
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
print(f'Positive class: {y.sum()} ({y.sum()/len(y)*100:.1f}%)')
print()

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f'Train: {len(X_train)} | Test: {len(X_test)}')
print()

# Train model
print('Training Random Forest...')
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    min_samples_split=50,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)
print('✓ Training complete')
print()

# Evaluate
print('Evaluating on test set...')
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

auc = roc_auc_score(y_test, y_pred_proba)
print(f'ROC AUC Score: {auc:.3f}')
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

# Save model
model_file = 'stock_predictor.pkl'
with open(model_file, 'wb') as f:
    pickle.dump({
        'model': model,
        'features': feature_cols,
        'threshold': 0.5
    }, f)
print(f'✅ Model saved to {model_file}')
print()

# Test predictions on recent data
print('Sample Predictions (high confidence):')
test_df = df[df['date'] >= '2025-11-15'].copy()
if len(test_df) > 0:
    X_recent = test_df[feature_cols].astype(float)
    proba = model.predict_proba(X_recent)[:, 1]
    test_df['prediction_proba'] = proba
    
    # Show high confidence predictions
    high_conf = test_df[proba > 0.6].sort_values('prediction_proba', ascending=False).head(10)
    
    for _, row in high_conf.iterrows():
        print(f"  {row['ticker']:6s} {row['date']} | Probability: {row['prediction_proba']:.1%} | Actual: {row.get('future_return_5d', 'N/A')}%")

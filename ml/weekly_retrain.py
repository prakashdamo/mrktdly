#!/usr/bin/env python3
"""
Weekly model retraining script
Run every Sunday to update model with latest data
Only deploys if new model is more accurate than current
"""
import boto3
import pandas as pd
import pickle
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

# AWS setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')
features_table = dynamodb.Table('mrktdly-features')

BUCKET = 'mrktdly-models'
MODEL_KEY = 'stock_predictor.pkl'
METRICS_KEY = 'model_metrics.json'

print("="*60)
print(f"WEEKLY MODEL RETRAINING - {datetime.now().strftime('%Y-%m-%d')}")
print("="*60)

# Step 1: Download all features with labels
print("\n[1/6] Downloading training data from DynamoDB...")
response = features_table.scan()
items = response['Items']
while 'LastEvaluatedKey' in response:
    response = features_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response['Items'])

df = pd.DataFrame(items)
df = df[df['label'].notna()]
print(f"Total records: {len(df)}")

# Step 2: Prepare features
print("\n[2/6] Preparing features...")
feature_cols = ['ma_5', 'ma_10', 'ma_20', 'ma_50', 'ma_200', 'rsi', 'macd', 'macd_signal',
                'bb_upper', 'bb_middle', 'bb_lower', 'atr', 'vol_ratio', 'return_1d',
                'return_5d', 'return_20d', 'volatility', 'pct_from_high', 'pct_from_low']

for col in feature_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['label'] = pd.to_numeric(df['label'], errors='coerce')
df = df.dropna(subset=feature_cols + ['label'])

X = df[feature_cols]
y = df['label']

print(f"Clean records: {len(X)}")
print(f"Positive labels (>3% moves): {y.sum()} ({y.mean()*100:.1f}%)")

# Step 3: Train new model
print("\n[3/6] Training new model...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

new_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    min_samples_split=20,
    random_state=42,
    n_jobs=-1
)
new_model.fit(X_train, y_train)

# Step 4: Evaluate new model
print("\n[4/6] Evaluating new model...")
y_pred = new_model.predict(X_test)
y_proba = new_model.predict_proba(X_test)[:, 1]

new_accuracy = accuracy_score(y_test, y_pred)
new_precision = precision_score(y_test, y_pred, zero_division=0)
new_recall = recall_score(y_test, y_pred, zero_division=0)
new_auc = roc_auc_score(y_test, y_proba)

print(f"New model performance:")
print(f"  Accuracy:  {new_accuracy*100:.1f}%")
print(f"  Precision: {new_precision*100:.1f}%")
print(f"  Recall:    {new_recall*100:.1f}%")
print(f"  ROC AUC:   {new_auc:.3f}")

# Step 5: Compare with current model
print("\n[5/6] Comparing with current model...")
try:
    # Download current model
    s3.download_file(BUCKET, MODEL_KEY, '/tmp/current_model.pkl')
    with open('/tmp/current_model.pkl', 'rb') as f:
        current_model = pickle.load(f)
    
    # Evaluate current model on same test set
    y_pred_current = current_model.predict(X_test)
    current_accuracy = accuracy_score(y_test, y_pred_current)
    
    print(f"Current model accuracy: {current_accuracy*100:.1f}%")
    print(f"New model accuracy:     {new_accuracy*100:.1f}%")
    
    if new_accuracy > current_accuracy:
        print(f"✓ New model is better (+{(new_accuracy-current_accuracy)*100:.1f}%)")
        deploy = True
    else:
        print(f"✗ Current model is better, keeping it")
        deploy = False
        
except Exception as e:
    print(f"No current model found or error: {e}")
    print("Deploying new model as first version")
    deploy = True

# Step 6: Deploy if better
if deploy:
    print("\n[6/6] Deploying new model...")
    
    # Save model
    with open('/tmp/new_model.pkl', 'wb') as f:
        pickle.dump(new_model, f)
    
    # Upload to S3
    s3.upload_file('/tmp/new_model.pkl', BUCKET, MODEL_KEY)
    
    # Save metrics
    metrics = {
        'date': datetime.now().isoformat(),
        'accuracy': float(new_accuracy),
        'precision': float(new_precision),
        'recall': float(new_recall),
        'roc_auc': float(new_auc),
        'training_records': len(X),
        'positive_rate': float(y.mean())
    }
    
    import json
    s3.put_object(
        Bucket=BUCKET,
        Key=METRICS_KEY,
        Body=json.dumps(metrics, indent=2)
    )
    
    print(f"✓ Model deployed to s3://{BUCKET}/{MODEL_KEY}")
    print(f"✓ Metrics saved to s3://{BUCKET}/{METRICS_KEY}")
else:
    print("\n[6/6] Keeping current model (no deployment)")

print("\n" + "="*60)
print("RETRAINING COMPLETE")
print("="*60)

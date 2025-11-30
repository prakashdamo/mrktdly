#!/bin/bash
# Weekly model retraining script
# Run every Sunday: ./retrain_model.sh

set -e

echo "=========================================="
echo "Weekly Model Retraining"
echo "Date: $(date)"
echo "=========================================="

# Step 1: Export training data from DynamoDB
echo -e "\n[1/5] Exporting training data..."
aws dynamodb scan \
  --table-name mrktdly-features \
  --region us-east-1 \
  --output json > /tmp/features_export.json

# Step 2: Train model locally
echo -e "\n[2/5] Training new model..."
python3 << 'PYTHON_SCRIPT'
import json
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score

# Load data
with open('/tmp/features_export.json') as f:
    data = json.load(f)

items = data['Items']
print(f"Total records: {len(items)}")

# Convert DynamoDB format to flat dict
records = []
for item in items:
    record = {}
    for key, value in item.items():
        if 'S' in value:
            record[key] = value['S']
        elif 'N' in value:
            record[key] = float(value['N'])
    records.append(record)

df = pd.DataFrame(records)
df = df[df['label'].notna()]

# Features
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
print(f"Positive labels: {y.sum()} ({y.mean()*100:.1f}%)")

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)

print(f"\nNew model performance:")
print(f"  Accuracy:  {accuracy*100:.1f}%")
print(f"  Precision: {precision*100:.1f}%")
print(f"  Recall:    {recall*100:.1f}%")

# Save model
with open('/tmp/new_model.pkl', 'wb') as f:
    pickle.dump(model, f)

# Save metrics
with open('/tmp/model_metrics.txt', 'w') as f:
    f.write(f"accuracy={accuracy}\n")
    f.write(f"precision={precision}\n")
    f.write(f"recall={recall}\n")

print("\n✓ Model saved to /tmp/new_model.pkl")
PYTHON_SCRIPT

# Step 3: Compare with current model
echo -e "\n[3/5] Comparing with current model..."
aws s3 cp s3://mrktdly-models/stock_predictor.pkl /tmp/current_model.pkl 2>/dev/null || echo "No current model found"

if [ -f /tmp/current_model.pkl ]; then
    # Get current model accuracy (stored in S3)
    CURRENT_ACC=$(aws s3 cp s3://mrktdly-models/model_metrics.txt - 2>/dev/null | grep accuracy | cut -d= -f2 || echo "0")
    NEW_ACC=$(grep accuracy /tmp/model_metrics.txt | cut -d= -f2)
    
    echo "Current model accuracy: $(echo "$CURRENT_ACC * 100" | bc)%"
    echo "New model accuracy:     $(echo "$NEW_ACC * 100" | bc)%"
    
    if (( $(echo "$NEW_ACC > $CURRENT_ACC" | bc -l) )); then
        echo "✓ New model is better, deploying..."
        DEPLOY=true
    else
        echo "✗ Current model is better, keeping it"
        DEPLOY=false
    fi
else
    echo "No current model, deploying new model..."
    DEPLOY=true
fi

# Step 4: Deploy if better
if [ "$DEPLOY" = true ]; then
    echo -e "\n[4/5] Deploying new model to S3..."
    aws s3 cp /tmp/new_model.pkl s3://mrktdly-models/stock_predictor.pkl --region us-east-1
    aws s3 cp /tmp/model_metrics.txt s3://mrktdly-models/model_metrics.txt --region us-east-1
    echo "✓ Model deployed"
else
    echo -e "\n[4/5] Skipping deployment"
fi

# Step 5: Cleanup
echo -e "\n[5/5] Cleaning up..."
rm -f /tmp/features_export.json /tmp/new_model.pkl /tmp/current_model.pkl /tmp/model_metrics.txt

echo -e "\n=========================================="
echo "Retraining complete!"
echo "=========================================="

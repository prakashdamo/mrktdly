#!/usr/bin/env python3
"""
Model Feasibility Testing Framework
Tests different ML models on existing data to compare performance
"""
import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import time

def load_data():
    """Load features from DynamoDB export"""
    print("Loading data...")
    import boto3
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    features_table = dynamodb.Table('mrktdly-features')
    
    response = features_table.scan()
    items = response['Items']
    while 'LastEvaluatedKey' in response:
        response = features_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    df = pd.DataFrame(items)
    df = df[df['label'].notna()]
    
    # Feature columns
    feature_cols = ['ma_5', 'ma_10', 'ma_20', 'ma_50', 'ma_200', 'rsi', 'macd', 'macd_signal',
                    'bb_upper', 'bb_middle', 'bb_lower', 'atr', 'vol_ratio', 'return_1d',
                    'return_5d', 'return_20d', 'volatility', 'pct_from_high', 'pct_from_low']
    
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['label'] = pd.to_numeric(df['label'], errors='coerce')
    df = df.dropna(subset=feature_cols + ['label'])
    
    X = df[feature_cols]
    y = df['label']
    
    print(f"Loaded {len(X)} records")
    print(f"Positive rate: {y.mean()*100:.1f}%")
    
    return X, y

def test_model(name, model, X_train, X_test, y_train, y_test):
    """Test a single model and return metrics"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    # Train
    start = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start
    
    # Predict
    start = time.time()
    y_pred = model.predict(X_test)
    predict_time = time.time() - start
    
    # Metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    # ROC AUC (if model supports predict_proba)
    try:
        y_proba = model.predict_proba(X_test)[:, 1]
        roc_auc = roc_auc_score(y_test, y_proba)
    except:
        roc_auc = None
    
    # Cross-validation score (on subset for speed)
    cv_scores = cross_val_score(model, X_train[:1000], y_train[:1000], cv=3, scoring='accuracy')
    cv_mean = cv_scores.mean()
    
    results = {
        'name': name,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'roc_auc': roc_auc,
        'cv_accuracy': cv_mean,
        'train_time': train_time,
        'predict_time': predict_time,
        'predictions_per_sec': len(X_test) / predict_time
    }
    
    print(f"Accuracy:  {accuracy*100:.1f}%")
    print(f"Precision: {precision*100:.1f}%")
    print(f"Recall:    {recall*100:.1f}%")
    print(f"F1 Score:  {f1:.3f}")
    if roc_auc:
        print(f"ROC AUC:   {roc_auc:.3f}")
    print(f"CV Accuracy: {cv_mean*100:.1f}%")
    print(f"Train time: {train_time:.1f}s")
    print(f"Predict time: {predict_time:.3f}s ({results['predictions_per_sec']:.0f} pred/sec)")
    
    return results

def main():
    """Test multiple models and compare"""
    print("="*60)
    print("MODEL FEASIBILITY STUDY")
    print("="*60)
    
    # Load data
    X, y = load_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Define models to test
    models = {
        'Random Forest (Current)': RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
        ),
        'Gradient Boosting': GradientBoostingClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42
        ),
        'Logistic Regression': LogisticRegression(
            max_iter=1000, random_state=42
        ),
        'Random Forest (Deep)': RandomForestClassifier(
            n_estimators=200, max_depth=20, random_state=42, n_jobs=-1
        ),
        'Neural Network': MLPClassifier(
            hidden_layer_sizes=(100, 50), max_iter=500, random_state=42
        ),
    }
    
    # Test each model
    results = []
    for name, model in models.items():
        try:
            result = test_model(name, model, X_train, X_test, y_train, y_test)
            results.append(result)
        except Exception as e:
            print(f"Error testing {name}: {e}")
    
    # Summary comparison
    print(f"\n{'='*60}")
    print("SUMMARY COMPARISON")
    print(f"{'='*60}")
    
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('accuracy', ascending=False)
    
    print("\nRanked by Accuracy:")
    for _, row in df_results.iterrows():
        print(f"{row['name']:30s} {row['accuracy']*100:5.1f}%  "
              f"Precision: {row['precision']*100:5.1f}%  "
              f"Recall: {row['recall']*100:5.1f}%  "
              f"F1: {row['f1']:.3f}")
    
    # Best model
    best = df_results.iloc[0]
    current = df_results[df_results['name'] == 'Random Forest (Current)'].iloc[0]
    
    print(f"\n{'='*60}")
    print("RECOMMENDATION")
    print(f"{'='*60}")
    print(f"Current model: {current['name']}")
    print(f"  Accuracy: {current['accuracy']*100:.1f}%")
    print(f"  Precision: {current['precision']*100:.1f}%")
    print(f"  Speed: {current['predictions_per_sec']:.0f} pred/sec")
    
    print(f"\nBest model: {best['name']}")
    print(f"  Accuracy: {best['accuracy']*100:.1f}%")
    print(f"  Precision: {best['precision']*100:.1f}%")
    print(f"  Speed: {best['predictions_per_sec']:.0f} pred/sec")
    
    improvement = (best['accuracy'] - current['accuracy']) * 100
    if improvement > 1:
        print(f"\n✓ SWITCH RECOMMENDED: +{improvement:.1f}% accuracy improvement")
    elif improvement > 0:
        print(f"\n⚠ MARGINAL: Only +{improvement:.1f}% improvement, may not be worth switching")
    else:
        print(f"\n✗ KEEP CURRENT: Current model is best")
    
    # Save results
    df_results.to_csv('/tmp/model_comparison.csv', index=False)
    print(f"\nDetailed results saved to: /tmp/model_comparison.csv")

if __name__ == '__main__':
    main()

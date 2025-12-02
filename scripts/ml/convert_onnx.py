#!/usr/bin/env python3
"""Convert models to ONNX"""
import pickle

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

# Stock predictor
print("Converting stock_predictor...")
with open('stock_predictor_smote.pkl', 'rb') as f:
    data = pickle.load(f)  # nosec B301
    model = data['model']

initial_type = [('input', FloatTensorType([None, 12]))]
onnx_model = convert_sklearn(model, initial_types=initial_type, target_opset=12)
with open('stock_predictor.onnx', 'wb') as f:
    f.write(onnx_model.SerializeToString())
size_mb = len(onnx_model.SerializeToString()) / 1024 / 1024
print(f"✓ stock_predictor.onnx ({size_mb:.1f}MB)")

# State classifier
print("\nConverting state_classifier...")
with open('state_classifier_fixed.pkl', 'rb') as f:
    model = pickle.load(f)  # nosec B301

initial_type = [('input', FloatTensorType([None, 4]))]
onnx_model = convert_sklearn(model, initial_types=initial_type, target_opset=12)
with open('state_classifier.onnx', 'wb') as f:
    f.write(onnx_model.SerializeToString())
size_mb = len(onnx_model.SerializeToString()) / 1024 / 1024
print(f"✓ state_classifier.onnx ({size_mb:.1f}MB)")

# Strategy optimizer
print("\nConverting strategy_optimizer...")
with open('strategy_optimizer_fixed.pkl', 'rb') as f:
    data = pickle.load(f)  # nosec B301

initial_type = [('input', FloatTensorType([None, 8]))]

target_model = data['models']['optimal_target']
onnx_model = convert_sklearn(target_model, initial_types=initial_type, target_opset=12)
with open('strategy_optimizer_optimal_target.onnx', 'wb') as f:
    f.write(onnx_model.SerializeToString())
size_mb = len(onnx_model.SerializeToString()) / 1024 / 1024
print(f"✓ optimal_target.onnx ({size_mb:.1f}MB)")

stop_model = data['models']['optimal_stop']
onnx_model = convert_sklearn(stop_model, initial_types=initial_type, target_opset=12)
with open('strategy_optimizer_optimal_stop.onnx', 'wb') as f:
    f.write(onnx_model.SerializeToString())
size_mb = len(onnx_model.SerializeToString()) / 1024 / 1024
print(f"✓ optimal_stop.onnx ({size_mb:.1f}MB)")

print("\n✓ All models converted to ONNX!")

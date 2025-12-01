#!/usr/bin/env python3
"""Convert sklearn models to ONNX format for Lambda deployment"""
import pickle
import boto3
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

s3 = boto3.client('s3')

def convert_model(model_name, input_features):
    """Convert a model from S3 to ONNX"""
    print(f"\n{'='*60}")
    print(f"Converting {model_name}")
    print(f"{'='*60}")
    
    # Download from S3
    print(f"Downloading from S3...")
    obj = s3.get_object(Bucket='mrktdly-models', Key=f'{model_name}.pkl')
    model_data = pickle.loads(obj['Body'].read())
    
    # Handle different model structures
    if isinstance(model_data, dict):
        if 'model' in model_data:
            model = model_data['model']
            print(f"Model type: {type(model).__name__}")
        elif 'models' in model_data:
            # Strategy optimizer has multiple models
            print("Multi-model structure detected")
            for key, submodel in model_data['models'].items():
                print(f"  Converting {key}...")
                initial_type = [('input', FloatTensorType([None, input_features]))]
                onnx_model = convert_sklearn(submodel, initial_types=initial_type)
                
                onnx_filename = f'{model_name}_{key}.onnx'
                with open(onnx_filename, 'wb') as f:
                    f.write(onnx_model.SerializeToString())
                
                # Upload to S3
                s3.upload_file(onnx_filename, 'mrktdly-models', onnx_filename)
                print(f"  ✓ Uploaded {onnx_filename}")
            return
    else:
        model = model_data
    
    # Convert to ONNX
    print(f"Converting to ONNX...")
    initial_type = [('input', FloatTensorType([None, input_features]))]
    onnx_model = convert_sklearn(model, initial_types=initial_type)
    
    # Save locally
    onnx_filename = f'{model_name}.onnx'
    with open(onnx_filename, 'wb') as f:
        f.write(onnx_model.SerializeToString())
    
    print(f"ONNX model size: {len(onnx_model.SerializeToString()) / 1024 / 1024:.2f} MB")
    
    # Upload to S3
    s3.upload_file(onnx_filename, 'mrktdly-models', onnx_filename)
    print(f"✓ Uploaded to S3: {onnx_filename}")

def main():
    print("\n🔄 Converting sklearn models to ONNX\n")
    
    # Convert state classifier (4 features: return_5d, return_20d, volatility, rsi)
    try:
        convert_model('state_classifier', 4)
    except Exception as e:
        print(f"✗ State classifier failed: {e}")
    
    # Convert strategy optimizer (8 features)
    try:
        convert_model('strategy_optimizer', 8)
    except Exception as e:
        print(f"✗ Strategy optimizer failed: {e}")
    
    print("\n" + "="*60)
    print("CONVERSION COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Create Lambda layer with onnxruntime")
    print("2. Update ml-predictions Lambda to use ONNX models")
    print("3. Test predictions")

if __name__ == '__main__':
    main()

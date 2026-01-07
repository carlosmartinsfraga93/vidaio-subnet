#!/usr/bin/env python3
"""
Quick verification of the model file to ensure it matches the checkpoint.
"""

import torch
import sys
from pathlib import Path

def verify_model(model_path):
    print(f"📂 Checking model file: {model_path}")
    
    if not Path(model_path).exists():
        print(f"❌ File not found!")
        return False
    
    file_size = Path(model_path).stat().st_size / (1024*1024)
    print(f"   File size: {file_size:.2f} MB")
    
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
    
    print(f"\n📋 Model Info:")
    print(f"   Model type: {checkpoint.get('model_type', 'NOT FOUND')}")
    print(f"   Image size: {checkpoint.get('image_size', 'NOT FOUND')}")
    print(f"   Classes: {len(checkpoint.get('class_mapping', {}))}")
    print(f"   Best val acc: {checkpoint.get('best_val_acc', 'NOT FOUND')}")
    
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
        
        # Check first layer
        first_key = [k for k in state_dict.keys() if 'features.0' in k or 'image_features.0.0.0.weight' in k]
        if first_key:
            first_layer = state_dict[first_key[0]]
            print(f"\n🏗️  Architecture:")
            print(f"   First layer channels: {first_layer.shape[0]}")
            
            # Check classifier
            classifier_key = [k for k in state_dict.keys() if 'classifier.1.weight' in k and 'image_model' not in k]
            if classifier_key:
                classifier = state_dict[classifier_key[0]]
                print(f"   Classifier input features: {classifier.shape[1]}")
        
        # Verify it's EfficientNet (24 channels) not MobileNet (16 channels)
        if first_layer.shape[0] == 24:
            print(f"\n✅ Model is EfficientNet v2 S (correct - 24 channels)")
        elif first_layer.shape[0] == 16:
            print(f"\n❌ Model is MobileNet v3 Small (wrong - 16 channels)")
            print(f"   This is the OLD model. You need to use the NEW 85MB model.")
        else:
            print(f"\n⚠️  Unexpected architecture: {first_layer.shape[0]} channels")
    
    return True

if __name__ == "__main__":
    model_path = sys.argv[1] if len(sys.argv) > 1 else "services/compress/models/scene_classifier_model.pth"
    verify_model(model_path)



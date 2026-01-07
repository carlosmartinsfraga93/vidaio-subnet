#!/usr/bin/env python3
"""
Check the actual architecture in a checkpoint file.
"""

import torch
import sys
from pathlib import Path

def check_checkpoint(checkpoint_path):
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    
    print(f"📂 Checkpoint: {checkpoint_path}")
    print(f"\n📋 Metadata:")
    print(f"   Model type: {checkpoint.get('model_type', 'NOT FOUND')}")
    print(f"   Image size: {checkpoint.get('image_size', 'NOT FOUND')}")
    print(f"   Classes: {len(checkpoint.get('class_mapping', {}))}")
    print(f"   Metrics: {len(checkpoint.get('available_metrics', []))}")
    print(f"   Best val acc: {checkpoint.get('best_val_acc', 'NOT FOUND')}")
    print(f"   Epoch: {checkpoint.get('epoch', 'NOT FOUND')}")
    
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
        print(f"\n🏗️  Architecture Analysis:")
        
        # Check first layer to determine model type
        first_layer_keys = [k for k in state_dict.keys() if 'features.0' in k or 'image_model.features.0' in k]
        if first_layer_keys:
            print(f"\n   First layer keys (sample):")
            for key in sorted(first_layer_keys)[:5]:
                shape = state_dict[key].shape
                print(f"   - {key}: {shape}")
        
        # Check for mobilenet vs efficientnet patterns
        mobilenet_keys = [k for k in state_dict.keys() if 'block' in k.lower()]
        efficientnet_keys = [k for k in state_dict.keys() if 'features.' in k and 'block' not in k.lower()]
        
        print(f"\n   Model structure indicators:")
        print(f"   - Keys with 'block': {len(mobilenet_keys)} (MobileNet pattern)")
        print(f"   - Keys with 'features.' (no block): {len(efficientnet_keys)} (EfficientNet pattern)")
        
        # Check classifier input size
        classifier_keys = [k for k in state_dict.keys() if 'classifier' in k.lower()]
        if classifier_keys:
            print(f"\n   Classifier layer:")
            for key in sorted(classifier_keys):
                if 'weight' in key:
                    shape = state_dict[key].shape
                    print(f"   - {key}: {shape}")
                    if len(shape) == 2:
                        print(f"     → Input features: {shape[1]}")
        
        # Check image_features structure
        image_features_keys = [k for k in state_dict.keys() if 'image_features' in k]
        if image_features_keys:
            print(f"\n   Image features structure (sample):")
            for key in sorted(image_features_keys)[:5]:
                shape = state_dict[key].shape
                print(f"   - {key}: {shape}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_checkpoint_architecture.py <checkpoint_path>")
        sys.exit(1)
    
    checkpoint_path = Path(sys.argv[1])
    if not checkpoint_path.exists():
        print(f"❌ Error: Checkpoint not found: {checkpoint_path}")
        sys.exit(1)
    
    check_checkpoint(checkpoint_path)



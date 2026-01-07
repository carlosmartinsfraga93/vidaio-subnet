#!/usr/bin/env python3
"""
Check if the EfficientNet model has the correct image size (384) saved in the checkpoint
"""

import torch
import sys
import os

def check_model_checkpoint(model_path):
    """Check the model checkpoint for image size and other metadata"""
    
    print("\n" + "="*80)
    print("CHECKING MODEL CHECKPOINT")
    print("="*80)
    
    print(f"\n📁 Model path: {model_path}")
    
    # Check if file exists
    if not os.path.exists(model_path):
        print(f"❌ Model file not found: {model_path}")
        return False
    
    # Get file size
    file_size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f"📊 Model file size: {file_size_mb:.2f} MB")
    
    try:
        # Load checkpoint
        print(f"\n📖 Loading checkpoint...")
        checkpoint = torch.load(model_path, map_location='cpu')
        
        print(f"✅ Checkpoint loaded successfully")
        
        # Check what's in the checkpoint
        print(f"\n📋 Checkpoint keys:")
        for key in checkpoint.keys():
            if key != 'model_state_dict':  # Don't print the huge state dict
                value = checkpoint[key]
                if isinstance(value, (list, dict)):
                    print(f"   {key:30s}: {type(value).__name__} (length: {len(value)})")
                else:
                    print(f"   {key:30s}: {value}")
        
        # Check image size specifically
        print(f"\n" + "="*80)
        print("IMAGE SIZE CHECK")
        print("="*80)
        
        image_size = checkpoint.get('image_size', None)
        
        if image_size is None:
            print(f"❌ WARNING: 'image_size' not found in checkpoint!")
            print(f"   The model will default to 224x224")
            print(f"   This is INCORRECT if you trained with 384x384!")
            return False
        else:
            print(f"✅ Image size found: {image_size}x{image_size}")
            
            if image_size == 384:
                print(f"✅ CORRECT: Model is configured for 384x384 images")
                return True
            elif image_size == 224:
                print(f"⚠️  WARNING: Model is configured for 224x224 images")
                print(f"   If you trained with 384x384, this is INCORRECT!")
                return False
            else:
                print(f"⚠️  WARNING: Unusual image size: {image_size}x{image_size}")
                return False
        
    except Exception as e:
        print(f"❌ Error loading checkpoint: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_inference_code():
    """Check if the inference code properly uses image_size from checkpoint"""
    
    print("\n" + "="*80)
    print("CHECKING INFERENCE CODE")
    print("="*80)
    
    try:
        # Add services/compress to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'compress'))
        
        from utils.classify_scene import load_scene_classifier_model
        
        print(f"\n✅ Successfully imported load_scene_classifier_model")
        
        # Check the function signature
        import inspect
        sig = inspect.signature(load_scene_classifier_model)
        print(f"\n📋 Function signature:")
        print(f"   {sig}")
        
        # Check if it returns image_size
        source = inspect.getsource(load_scene_classifier_model)
        
        if 'image_size' in source and 'checkpoint.get' in source:
            print(f"\n✅ Code loads image_size from checkpoint")
            
            # Find the line
            for line in source.split('\n'):
                if 'image_size' in line and 'checkpoint.get' in line:
                    print(f"   Found: {line.strip()}")
        else:
            print(f"\n❌ WARNING: Code may not load image_size from checkpoint")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking inference code: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    
    model_path = 'services/compress/models/scene_classifier_model.pth'
    
    # Check model checkpoint
    checkpoint_ok = check_model_checkpoint(model_path)
    
    # Check inference code
    code_ok = check_inference_code()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if checkpoint_ok and code_ok:
        print(f"\n✅ EVERYTHING LOOKS GOOD!")
        print(f"   - Model checkpoint has correct image_size (384)")
        print(f"   - Inference code loads image_size from checkpoint")
        print(f"   - Images will be resized to 384x384 during inference")
        return 0
    elif not checkpoint_ok and code_ok:
        print(f"\n❌ PROBLEM DETECTED!")
        print(f"   - Model checkpoint is missing image_size or has wrong value")
        print(f"   - Inference code is correct, but will use default 224x224")
        print(f"\n🔧 FIX: Re-save the model with image_size=384 in checkpoint")
        return 1
    elif checkpoint_ok and not code_ok:
        print(f"\n❌ PROBLEM DETECTED!")
        print(f"   - Model checkpoint has correct image_size")
        print(f"   - Inference code may not be loading it properly")
        print(f"\n🔧 FIX: Update inference code to load image_size from checkpoint")
        return 1
    else:
        print(f"\n❌ MULTIPLE PROBLEMS DETECTED!")
        print(f"   - Model checkpoint issue")
        print(f"   - Inference code issue")
        return 1


if __name__ == "__main__":
    sys.exit(main())


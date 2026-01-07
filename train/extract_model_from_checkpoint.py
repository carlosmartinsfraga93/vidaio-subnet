#!/usr/bin/env python3
"""
Extract model weights from training checkpoint to create a lightweight model file.
This removes the optimizer state and keeps only the model weights and metadata.
"""

import torch
import argparse
from pathlib import Path

def extract_model_from_checkpoint(checkpoint_path, output_path):
    """
    Extract model weights from a training checkpoint.
    
    Args:
        checkpoint_path: Path to the checkpoint file (e.g., checkpoint_best.pth)
        output_path: Path to save the extracted model file
    """
    print(f"📂 Loading checkpoint from: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    
    # Check if it's a valid checkpoint
    if 'model_state_dict' not in checkpoint:
        raise ValueError(f"Invalid checkpoint: {checkpoint_path} - missing 'model_state_dict'")
    
    # Extract only the necessary information (no optimizer state)
    model_checkpoint = {
        'model_state_dict': checkpoint['model_state_dict'],
        'available_metrics': checkpoint.get('available_metrics', []),
        'class_mapping': checkpoint.get('class_mapping', {}),
        'model_type': checkpoint.get('model_type', 'mobilenet_v3_small'),
        'image_size': checkpoint.get('image_size', 224),
        'confidence_threshold': checkpoint.get('confidence_threshold', 0.5),
        'best_val_acc': checkpoint.get('best_val_acc', 0.0),
        'epoch': checkpoint.get('epoch', 0)
    }
    
    # Save the lightweight model file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model_checkpoint, output_path)
    
    # Calculate file sizes
    checkpoint_size = Path(checkpoint_path).stat().st_size
    model_size = output_path.stat().st_size
    
    print(f"✅ Model extracted successfully!")
    print(f"   Checkpoint size: {checkpoint_size / (1024*1024):.2f} MB")
    print(f"   Model size: {model_size / (1024*1024):.2f} MB")
    print(f"   Reduction: {(1 - model_size/checkpoint_size)*100:.1f}%")
    print(f"   Saved to: {output_path}")
    print(f"\n   Model info:")
    print(f"   - Model type: {model_checkpoint['model_type']}")
    print(f"   - Image size: {model_checkpoint['image_size']}x{model_checkpoint['image_size']}")
    print(f"   - Classes: {len(model_checkpoint['class_mapping'])}")
    print(f"   - Metrics: {len(model_checkpoint['available_metrics'])}")
    print(f"   - Best val acc: {model_checkpoint['best_val_acc']:.2f}%")
    print(f"   - Epoch: {model_checkpoint['epoch']}")

def main():
    parser = argparse.ArgumentParser(
        description="Extract model weights from training checkpoint"
    )
    parser.add_argument(
        'checkpoint',
        type=str,
        help='Path to checkpoint file (e.g., train/models/scene_2025_1227_1819/checkpoint_best.pth)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output path for model file (default: same directory as checkpoint with name scene_classifier_model.pth)'
    )
    
    args = parser.parse_args()
    
    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        print(f"❌ Error: Checkpoint file not found: {checkpoint_path}")
        return 1
    
    # Default output path
    if args.output is None:
        output_path = checkpoint_path.parent / "scene_classifier_model.pth"
    else:
        output_path = Path(args.output)
    
    try:
        extract_model_from_checkpoint(checkpoint_path, output_path)
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())



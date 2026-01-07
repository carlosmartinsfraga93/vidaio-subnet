#!/usr/bin/env python3
"""
Check training status and progress
"""

import os
import sys
import json
import torch
from pathlib import Path
from datetime import datetime

def format_size(size_bytes):
    """Format file size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def check_scene_classifier(version_dir):
    """Check scene classifier training status"""
    model_path = version_dir / "scene_classifier_model.pth"
    history_path = version_dir / "training_history.json"
    
    status = {
        'exists': False,
        'epoch': None,
        'best_val_acc': None,
        'model_type': None,
        'model_name': None,
        'history': None,
        'file_size': None
    }
    
    if model_path.exists():
        status['exists'] = True
        status['file_size'] = format_size(model_path.stat().st_size)
        
        try:
            checkpoint = torch.load(model_path, map_location='cpu')
            status['epoch'] = checkpoint.get('epoch', None)
            status['best_val_acc'] = checkpoint.get('best_val_acc', None)
            status['model_type'] = checkpoint.get('model_type', None)
            
            # Convert to readable name
            model_name_map = {
                'mobilenet_v3_small': 'MobileNet V3 Small',
                'efficientnet_v2_s': 'EfficientNet V2 S',
                'resnet18': 'ResNet-18',
                'squeezenet1_1': 'SqueezeNet 1.1'
            }
            status['model_name'] = model_name_map.get(status['model_type'], status['model_type'])
        except Exception as e:
            status['error'] = str(e)
    
    if history_path.exists():
        try:
            with open(history_path, 'r') as f:
                history = json.load(f)
            status['history'] = {
                'total_epochs': len(history),
                'latest': history[-1] if history else None,
                'best': max(history, key=lambda x: x.get('val_acc', 0)) if history else None
            }
        except Exception as e:
            status['history_error'] = str(e)
    
    return status

def check_pipeline(version_dir):
    """Check preprocessing pipeline training status"""
    model_path = version_dir / "preprocessing_pipeline.pkl"
    metadata_path = version_dir / "pipeline_metadata.json"
    eval_path = version_dir / "pipeline_evaluation.json"
    
    status = {
        'exists': False,
        'file_size': None,
        'metadata': None,
        'evaluation': None
    }
    
    if model_path.exists():
        status['exists'] = True
        status['file_size'] = format_size(model_path.stat().st_size)
    
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r') as f:
                status['metadata'] = json.load(f)
        except Exception as e:
            status['metadata_error'] = str(e)
    
    if eval_path.exists():
        try:
            with open(eval_path, 'r') as f:
                status['evaluation'] = json.load(f)
        except Exception as e:
            status['eval_error'] = str(e)
    
    return status

def main():
    models_dir = Path("models")
    version = os.environ.get('MODEL_VERSION', 'latest')
    
    if version == 'latest':
        if models_dir.exists():
            versions = sorted([d for d in models_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)
            if versions:
                version = versions[0].name
            else:
                print("❌ No model versions found")
                return
        else:
            print("❌ Models directory not found")
            return
    
    version_dir = models_dir / version
    
    if not version_dir.exists():
        print(f"❌ Version {version} not found")
        return
    
    print(f"📊 Training Status: {version}")
    print("=" * 60)
    print(f"Directory: {version_dir}")
    print()
    
    # Scene Classifier
    print("🎯 Scene Classifier")
    print("-" * 60)
    scene_status = check_scene_classifier(version_dir)
    
    if scene_status['exists']:
        print(f"✅ Model: {scene_status['model_name']} ({scene_status['model_type']})")
        print(f"   File: {scene_status['file_size']}")
        if scene_status['epoch']:
            print(f"   Epoch: {scene_status['epoch']}")
        if scene_status['best_val_acc']:
            print(f"   Best Val Accuracy: {scene_status['best_val_acc']:.2f}%")
        
        if scene_status['history']:
            h = scene_status['history']
            print(f"   Total Epochs: {h['total_epochs']}")
            if h['latest']:
                latest = h['latest']
                print(f"   Latest - Train: {latest.get('train_acc', 0):.2f}%, Val: {latest.get('val_acc', 0):.2f}%")
            if h['best']:
                best = h['best']
                print(f"   Best - Epoch {best.get('epoch')}: Val Acc {best.get('val_acc', 0):.2f}%")
    else:
        print("⏳ Training in progress or not started")
    
    print()
    
    # Pipeline
    print("🔧 Preprocessing Pipeline")
    print("-" * 60)
    pipeline_status = check_pipeline(version_dir)
    
    if pipeline_status['exists']:
        print(f"✅ Model exists ({pipeline_status['file_size']})")
        if pipeline_status['metadata']:
            m = pipeline_status['metadata']
            print(f"   Type: {m.get('model_type', 'N/A')}")
            print(f"   Estimators: {m.get('n_estimators', 'N/A')}")
            print(f"   Training Samples: {m.get('training_samples', 'N/A')}")
        
        if pipeline_status['evaluation']:
            e = pipeline_status['evaluation']
            print(f"   MAE: {e.get('mae', 0):.4f}")
            print(f"   R²: {e.get('r2', 0):.4f}")
    else:
        print("⏳ Training in progress or not started")
        # Check data preparation
        data_dir = Path("datasets/vmaf_pipeline")
        if data_dir.exists():
            csv_count = len(list(data_dir.glob("*.csv")))
            print(f"   Data files: {csv_count}")
    
    print()
    print("📁 All files:")
    for f in sorted(version_dir.iterdir()):
        if f.is_file():
            size = format_size(f.stat().st_size)
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"   {f.name:40} {size:>10} ({mtime})")

if __name__ == "__main__":
    main()


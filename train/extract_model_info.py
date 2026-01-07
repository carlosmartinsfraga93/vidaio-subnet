#!/usr/bin/env python3
"""
Extract detailed model information for version_info.json
"""

import os
import sys
import json
import argparse
import torch
import pickle
import hashlib
from pathlib import Path
from datetime import datetime

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_file_size(filepath):
    """Get file size in bytes and human-readable format"""
    size = os.path.getsize(filepath)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return size, f"{size:.2f} {unit}"
        size /= 1024.0
    return size, f"{size:.2f} TB"

def get_readable_model_name(model_type):
    """Convert model type identifier to readable name"""
    model_name_map = {
        'mobilenet_v3_small': 'MobileNet V3 Small',
        'efficientnet_v2_s': 'EfficientNet V2 S',
        'resnet18': 'ResNet-18',
        'squeezenet1_1': 'SqueezeNet 1.1'
    }
    return model_name_map.get(model_type, model_type.title().replace('_', ' '))

def extract_scene_classifier_info(model_path):
    """Extract information from scene classifier model"""
    if not os.path.exists(model_path):
        return None
    
    info = {
        'file': os.path.basename(model_path),
        'file_size_bytes': os.path.getsize(model_path),
        'file_size': get_file_size(model_path)[1],
        'sha256': get_file_hash(model_path)
    }
    
    try:
        checkpoint = torch.load(model_path, map_location='cpu')
        
        # Extract checkpoint information
        info['checkpoint'] = {
            'epoch': checkpoint.get('epoch', 'unknown'),
            'best_val_acc': checkpoint.get('best_val_acc', 'unknown'),
            'model_type': checkpoint.get('model_type', 'unknown'),
            'class_mapping': checkpoint.get('class_mapping', {}),
            'available_metrics': checkpoint.get('available_metrics', [])
        }
        
        # Extract model architecture information
        state_dict = checkpoint.get('model_state_dict', {})
        if state_dict:
            info['architecture'] = {
                'num_parameters': sum(p.numel() for p in state_dict.values()),
                'num_layers': len(state_dict),
                'layer_names': list(state_dict.keys())[:10]  # First 10 layers
            }
            
            # Count parameters by type
            param_counts = {}
            for key in state_dict.keys():
                layer_type = key.split('.')[0] if '.' in key else key
                param_counts[layer_type] = param_counts.get(layer_type, 0) + 1
            info['architecture']['layer_types'] = param_counts
        
        # Model type specific info
        model_type = checkpoint.get('model_type', 'unknown')
        info['model_type'] = model_type  # Identifier (e.g., "efficientnet_v2_s")
        info['model_name'] = get_readable_model_name(model_type)  # Readable name (e.g., "EfficientNet V2 S")
        info['architecture']['backbone'] = model_type
        info['architecture']['backbone_name'] = get_readable_model_name(model_type)
        
        # Class information
        class_mapping = checkpoint.get('class_mapping', {})
        if class_mapping:
            info['classes'] = {
                'num_classes': len(class_mapping),
                'class_names': list(class_mapping.keys()) if isinstance(class_mapping, dict) else class_mapping
            }
        
    except Exception as e:
        info['error'] = f"Failed to load model: {str(e)}"
    
    return info

def extract_pipeline_info(pipeline_path):
    """Extract information from preprocessing pipeline"""
    if not os.path.exists(pipeline_path):
        return None
    
    info = {
        'file': os.path.basename(pipeline_path),
        'file_size_bytes': os.path.getsize(pipeline_path),
        'file_size': get_file_size(pipeline_path)[1],
        'sha256': get_file_hash(pipeline_path)
    }
    
    try:
        with open(pipeline_path, 'rb') as f:
            pipeline = pickle.load(f)
        
        # Extract pipeline steps
        if hasattr(pipeline, 'steps'):
            info['pipeline_steps'] = [step[0] for step in pipeline.steps]
        
        # Extract final estimator
        if hasattr(pipeline, 'steps') and len(pipeline.steps) > 0:
            final_step = pipeline.steps[-1]
            estimator = final_step[1]
            
            info['estimator'] = {
                'type': type(estimator).__name__,
                'module': type(estimator).__module__
            }
            
            # Extract estimator-specific parameters
            if hasattr(estimator, 'n_estimators'):
                info['estimator']['n_estimators'] = estimator.n_estimators
            if hasattr(estimator, 'learning_rate'):
                info['estimator']['learning_rate'] = estimator.learning_rate
            if hasattr(estimator, 'max_depth'):
                info['estimator']['max_depth'] = estimator.max_depth
            if hasattr(estimator, 'min_samples_split'):
                info['estimator']['min_samples_split'] = estimator.min_samples_split
            if hasattr(estimator, 'min_samples_leaf'):
                info['estimator']['min_samples_leaf'] = estimator.min_samples_leaf
            if hasattr(estimator, 'subsample'):
                info['estimator']['subsample'] = estimator.subsample
        
        # Try to load metadata file
        metadata_path = Path(pipeline_path).parent / "pipeline_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            info['metadata'] = metadata
        
        # Try to load evaluation file
        eval_path = Path(pipeline_path).parent / "pipeline_evaluation.json"
        if eval_path.exists():
            with open(eval_path, 'r') as f:
                eval_data = json.load(f)
            info['evaluation'] = eval_data
        
    except Exception as e:
        info['error'] = f"Failed to load pipeline: {str(e)}"
    
    return info

def extract_training_history(history_path):
    """Extract training history information"""
    if not os.path.exists(history_path):
        return None
    
    try:
        with open(history_path, 'r') as f:
            history = json.load(f)
        
        if not history:
            return None
        
        # Calculate statistics
        train_losses = [h['train_loss'] for h in history]
        train_accs = [h['train_acc'] for h in history]
        val_losses = [h['val_loss'] for h in history]
        val_accs = [h['val_acc'] for h in history]
        
        return {
            'file': os.path.basename(history_path),
            'num_epochs': len(history),
            'final_metrics': history[-1] if history else {},
            'best_metrics': {
                'best_train_acc': max(train_accs) if train_accs else None,
                'best_val_acc': max(val_accs) if val_accs else None,
                'lowest_train_loss': min(train_losses) if train_losses else None,
                'lowest_val_loss': min(val_losses) if val_losses else None
            },
            'all_epochs': history  # Includes metrics for each epoch/checkpoint
        }
    except Exception as e:
        return {'error': f"Failed to load history: {str(e)}"}

def extract_checkpoint_info(models_dir):
    """Extract information from all checkpoint files"""
    checkpoints = []
    checkpoint_files = sorted(Path(models_dir).glob("checkpoint_epoch_*.pth"))
    
    for checkpoint_path in checkpoint_files:
        try:
            checkpoint = torch.load(checkpoint_path, map_location='cpu')
            epoch = checkpoint.get('epoch', 'unknown')
            val_acc = checkpoint.get('best_val_acc', None)
            
            checkpoints.append({
                'file': checkpoint_path.name,
                'epoch': epoch,
                'best_val_acc': float(val_acc) if val_acc is not None else None,
                'file_size_bytes': checkpoint_path.stat().st_size,
                'file_size': get_file_size(checkpoint_path)[1]
            })
        except Exception as e:
            checkpoints.append({
                'file': checkpoint_path.name,
                'error': str(e)
            })
    
    return checkpoints if checkpoints else None

def main():
    parser = argparse.ArgumentParser(description="Extract model information")
    parser.add_argument("--models_dir", type=str, required=True, help="Models directory")
    parser.add_argument("--output", type=str, required=True, help="Output JSON file")
    parser.add_argument("--version", type=str, required=True, help="Model version")
    
    args = parser.parse_args()
    
    models_dir = Path(args.models_dir)
    
    # Extract information
    scene_classifier_path = models_dir / "scene_classifier_model.pth"
    pipeline_path = models_dir / "preprocessing_pipeline.pkl"
    history_path = models_dir / "training_history.json"
    
    version_info = {
        'version': args.version,
        'created_at': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'models': {}
    }
    
    # Scene classifier info
    scene_info = extract_scene_classifier_info(scene_classifier_path)
    if scene_info:
        version_info['models']['scene_classifier'] = scene_info
    
    # Pipeline info
    pipeline_info = extract_pipeline_info(pipeline_path)
    if pipeline_info:
        version_info['models']['preprocessing_pipeline'] = pipeline_info
    
    # Training history
    history_info = extract_training_history(history_path)
    if history_info:
        version_info['training_history'] = history_info
    
    # Checkpoint files
    checkpoint_info = extract_checkpoint_info(models_dir)
    if checkpoint_info:
        version_info['checkpoints'] = checkpoint_info
    
    # Save version info
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(version_info, f, indent=2)
    
    print(f"✅ Model information extracted to: {output_path}")
    return version_info

if __name__ == "__main__":
    main()


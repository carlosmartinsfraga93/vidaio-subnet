#!/usr/bin/env python3
"""
Train scene classifier model for compression.

Uses EfficientNet V2 S for best performance.
"""

import os
import sys
import argparse
import pickle
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import numpy as np
from tqdm import tqdm
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.compress.utils.classify_scene import (
    CombinedModel,
    CLASS_MAPPING,
    VIDEO_METRICS
)


class SceneClassifierDataset(Dataset):
    def __init__(self, dataset_file, transform=None):
        with open(dataset_file, 'rb') as f:
            self.data = pickle.load(f)
        
        # Default size will be set by training script
        self.transform = transform or transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        # Load and transform first frame (or average multiple frames)
        frame_path = item['frame_paths'][0] if item['frame_paths'] else None
        if not frame_path or not os.path.exists(frame_path):
            # Create dummy image if frame missing (size will be set by transform)
            image = Image.new('RGB', (224, 224), color='black')
        else:
            image = Image.open(frame_path).convert('RGB')
        
        image_tensor = self.transform(image)
        
        # Get metrics
        metrics = torch.FloatTensor(item['metrics'])
        
        # Get label
        label = torch.LongTensor([item['label_id']])[0]
        
        return image_tensor, metrics, label


def train_epoch(model, dataloader, criterion, optimizer, device, max_grad_norm=1.0):
    """Train for one epoch with gradient clipping"""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    pbar = tqdm(dataloader, desc="Training")
    for images, metrics, labels in pbar:
        images = images.to(device)
        metrics = metrics.to(device)
        labels = labels.to(device)
        
        optimizer.zero_grad()
        outputs = model(images, metrics)
        loss = criterion(outputs, labels)
        loss.backward()
        
        # Gradient clipping to prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        
        optimizer.step()
        
        running_loss += loss.item()
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()
        
        pbar.set_postfix({
            'loss': f'{loss.item():.4f}',
            'acc': f'{100*correct/total:.2f}%'
        })
    
    epoch_loss = running_loss / len(dataloader)
    epoch_acc = 100 * correct / total
    
    return epoch_loss, epoch_acc


def validate(model, dataloader, criterion, device, class_names=None):
    """Validate model with per-class accuracy"""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    class_correct = {}
    class_total = {}
    
    with torch.no_grad():
        for images, metrics, labels in tqdm(dataloader, desc="Validating"):
            images = images.to(device)
            metrics = metrics.to(device)
            labels = labels.to(device)
            
            outputs = model(images, metrics)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            # Per-class accuracy
            for i in range(labels.size(0)):
                label = labels[i].item()
                class_total[label] = class_total.get(label, 0) + 1
                if predicted[i] == labels[i]:
                    class_correct[label] = class_correct.get(label, 0) + 1
    
    epoch_loss = running_loss / len(dataloader)
    epoch_acc = 100 * correct / total
    
    # Print per-class accuracy
    if class_names:
        print(f"   Per-class accuracy:")
        for class_id in sorted(class_total.keys()):
            class_name = class_names.get(class_id, f"Class {class_id}")
            acc = 100 * class_correct.get(class_id, 0) / class_total[class_id]
            print(f"      {class_name}: {acc:.2f}% ({class_correct.get(class_id, 0)}/{class_total[class_id]})")
    
    return epoch_loss, epoch_acc


def main():
    parser = argparse.ArgumentParser(description="Train scene classifier model")
    parser.add_argument("--data_dir", type=str, required=True,
                       help="Directory containing prepared dataset (dataset.pkl)")
    parser.add_argument("--output_dir", type=str, default="models",
                       help="Output directory for trained model")
    parser.add_argument("--model", type=str, default="efficientnet_v2_s",
                       choices=["mobilenet_v3_small", "efficientnet_v2_s", "resnet18", "squeezenet1_1"],
                       help="Model architecture")
    parser.add_argument("--epochs", type=int, default=50,
                       help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=32,
                       help="Batch size")
    parser.add_argument("--learning_rate", type=float, default=0.001,
                       help="Learning rate")
    parser.add_argument("--weight_decay", type=float, default=1e-4,
                       help="Weight decay")
    parser.add_argument("--device", type=str, default="cuda",
                       help="Device to use (cuda/cpu)")
    parser.add_argument("--num_workers", type=int, default=4,
                       help="Number of data loading workers")
    parser.add_argument("--resume", type=str, default=None,
                       help="Resume from checkpoint")
    parser.add_argument("--image_size", type=int, default=224,
                       help="Input image size (224 or 384, default=224)")
    parser.add_argument("--early_stopping_patience", type=int, default=30,
                       help="Early stopping patience (epochs without improvement)")
    
    args = parser.parse_args()
    
    # Setup
    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    dataset_file = Path(args.data_dir) / "dataset.pkl"
    if not dataset_file.exists():
        print(f"❌ Dataset file not found: {dataset_file}")
        print(f"   Please run prepare_scene_classifier_data.py first")
        return
    
    print(f"Loading dataset from {dataset_file}...")
    
    # Split dataset (80/10/10)
    with open(dataset_file, 'rb') as f:
        all_data = pickle.load(f)
    
    if len(all_data) == 0:
        print(f"❌ Dataset is empty! No videos found.")
        print(f"   Please:")
        print(f"   1. Download videos: python download_datasets.py --sources youtube --num_videos 1000")
        print(f"   2. Prepare data: python prepare_scene_classifier_data.py --data_dir datasets/videos --output_dir datasets/scene_classifier")
        return
    
    print(f"Loaded {len(all_data)} samples")
    
    # Filter out "other" class - we'll handle it via confidence threshold in inference
    print(f"\n📊 Filtering dataset (excluding 'other' class)...")
    filtered_data = [item for item in all_data if item['label'] != 'other']
    excluded_count = len(all_data) - len(filtered_data)
    print(f"   Excluded {excluded_count} 'other' samples")
    print(f"   Training with {len(filtered_data)} samples (4 classes)")
    
    # Create new class mapping without "other"
    SPECIFIC_CLASS_MAPPING = {
        'Screen Content / Text': 0,
        'Animation / Cartoon / Rendered Graphics': 1,
        'Faces / People': 2,
        'Gaming Content': 3
    }
    
    # Remap label_ids to new 4-class system
    for item in filtered_data:
        old_label = item['label']
        if old_label in SPECIFIC_CLASS_MAPPING:
            item['label_id'] = SPECIFIC_CLASS_MAPPING[old_label]
        else:
            # Should not happen after filtering, but handle just in case
            continue
    
    # Validate image size
    if args.image_size not in [224, 384]:
        print(f"⚠️  Warning: Image size {args.image_size} not standard. Using 224 or 384 recommended.")
    
    np.random.seed(42)
    np.random.shuffle(filtered_data)
    
    train_size = int(0.8 * len(filtered_data))
    val_size = int(0.1 * len(filtered_data))
    
    train_data = filtered_data[:train_size]
    val_data = filtered_data[train_size:train_size+val_size]
    test_data = filtered_data[train_size+val_size:]
    
    # Save splits
    for split_name, split_data in [("train", train_data), ("val", val_data), ("test", test_data)]:
        split_file = Path(args.data_dir) / f"{split_name}_dataset.pkl"
        with open(split_file, 'wb') as f:
            pickle.dump(split_data, f)
    
    # Create datasets with configurable image size
    img_size = args.image_size
    train_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=10),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    train_dataset = SceneClassifierDataset(Path(args.data_dir) / "train_dataset.pkl", train_transform)
    val_dataset = SceneClassifierDataset(Path(args.data_dir) / "val_dataset.pkl", val_transform)
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True
    )
    
    print(f"Train samples: {len(train_dataset)}")
    print(f"Val samples: {len(val_dataset)}")
    
    # Use 4-class mapping (without "other")
    SPECIFIC_CLASS_MAPPING = {
        'Screen Content / Text': 0,
        'Animation / Cartoon / Rendered Graphics': 1,
        'Faces / People': 2,
        'Gaming Content': 3
    }
    inv_class_mapping = {v: k for k, v in SPECIFIC_CLASS_MAPPING.items()}
    
    # Create model with 4 classes
    num_classes = 4  # Only 4 specific classes
    metrics_dim = len(VIDEO_METRICS)
    
    model = CombinedModel(
        num_classes=num_classes,
        model_type=args.model,
        use_pretrained=True,  # Use ImageNet weights
        metrics_dim=metrics_dim
    )
    model = model.to(device)
    
    # Calculate class weights for imbalanced data (4 classes)
    label_counts = {}
    for item in train_data:
        label_id = item['label_id']
        label_counts[label_id] = label_counts.get(label_id, 0) + 1
    
    total_samples = len(train_data)
    num_classes = 4
    
    class_weights = []
    for i in range(num_classes):
        count = label_counts.get(i, 1)  # Avoid division by zero
        # Inverse frequency weighting
        weight = total_samples / (num_classes * count)
        # Cap weights to prevent extreme values (max 3x for balanced dataset)
        weight = min(weight, 3.0)
        # Also set minimum weight to 0.7
        weight = max(weight, 0.7)
        class_weights.append(weight)
    
    class_weights_tensor = torch.FloatTensor(class_weights).to(device)
    
    # Print label info
    print(f"   Label distribution in training set (4 classes):")
    for class_id in range(num_classes):
        label_name = inv_class_mapping.get(class_id, f"Class {class_id}")
        count = label_counts.get(class_id, 0)
        weight = class_weights[class_id]
        print(f"      {label_name} (id={class_id}): {count} samples, weight={weight:.2f}")
    
    # Loss with class weights
    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
    
    # Optimizer with lower initial learning rate for fine-tuning
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
        betas=(0.9, 0.999),
        eps=1e-8
    )
    
    # Better learning rate scheduler: Cosine annealing with warm restarts
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=10, T_mult=2, eta_min=1e-6
    )
    
    # Also keep ReduceLROnPlateau as backup
    plateau_scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5, patience=10
    )
    
    # Training loop
    best_val_acc = 0.0
    best_epoch = 0
    train_history = []
    epochs_without_improvement = 0
    
    start_epoch = 0
    if args.resume:
        checkpoint = torch.load(args.resume)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        start_epoch = checkpoint['epoch']
        best_val_acc = checkpoint.get('best_val_acc', 0.0)
        print(f"Resumed from epoch {start_epoch}")
    
    print(f"\n🚀 Starting training...")
    print(f"   Model: {args.model}")
    print(f"   Image size: {args.image_size}x{args.image_size}")
    print(f"   Epochs: {args.epochs}")
    print(f"   Batch size: {args.batch_size}")
    print(f"   Learning rate: {args.learning_rate}")
    
    for epoch in range(start_epoch, args.epochs):
        print(f"\n{'='*60}")
        print(f"Epoch {epoch+1}/{args.epochs}")
        print(f"{'='*60}")
        
        # Train
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device, max_grad_norm=1.0)
        
        # Validate
        val_loss, val_acc = validate(model, val_loader, criterion, device, class_names=inv_class_mapping)
        
        # Update learning rate (use both schedulers)
        scheduler.step()  # Cosine annealing
        plateau_scheduler.step(val_acc)  # Reduce on plateau
        
        current_lr = optimizer.param_groups[0]['lr']
        
        # Save history
        train_history.append({
            'epoch': epoch + 1,
            'train_loss': train_loss,
            'train_acc': train_acc,
            'val_loss': val_loss,
            'val_acc': val_acc
        })
        
        print(f"\nEpoch {epoch+1} Summary:")
        print(f"   Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"   Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
        print(f"   Learning Rate: {current_lr:.6f}")
        
        # Save best model
        if val_acc > best_val_acc:
            improvement = val_acc - best_val_acc
            best_val_acc = val_acc
            best_epoch = epoch + 1
            epochs_without_improvement = 0
            
            # Save with 4-class mapping (without "other")
            SPECIFIC_CLASS_MAPPING = {
                'Screen Content / Text': 0,
                'Animation / Cartoon / Rendered Graphics': 1,
                'Faces / People': 2,
                'Gaming Content': 3
            }
            checkpoint = {
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'best_val_acc': best_val_acc,
                'available_metrics': VIDEO_METRICS,
                'class_mapping': SPECIFIC_CLASS_MAPPING,  # 4 classes only
                'model_type': args.model,
                'image_size': args.image_size,
                'confidence_threshold': 0.5  # Threshold for "other" classification
            }
            
            model_path = output_dir / "scene_classifier_model.pth"
            torch.save(checkpoint, model_path)
            print(f"   ✅ Saved best model (val_acc: {val_acc:.2f}%, improvement: +{improvement:.2f}%)")
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= args.early_stopping_patience:
                print(f"\n⏹️  Early stopping triggered after {args.early_stopping_patience} epochs without improvement")
                print(f"   Best validation accuracy: {best_val_acc:.2f}% (epoch {best_epoch})")
                break
        
        # Save checkpoint
        checkpoint_path = output_dir / f"checkpoint_epoch_{epoch+1}.pth"
        torch.save(checkpoint, checkpoint_path)
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"Training Complete!")
    print(f"{'='*60}")
    print(f"Best validation accuracy: {best_val_acc:.2f}% (epoch {best_epoch})")
    print(f"Model saved to: {output_dir / 'scene_classifier_model.pth'}")
    
    # Save training history
    history_file = output_dir / "training_history.json"
    with open(history_file, 'w') as f:
        json.dump(train_history, f, indent=2)
    
    # Cleanup checkpoints: keep only best and last
    print(f"\n🧹 Cleaning up checkpoints...")
    checkpoint_files = sorted(output_dir.glob("checkpoint_epoch_*.pth"))
    
    if len(checkpoint_files) > 0:
        # Keep the last checkpoint (final epoch)
        last_checkpoint = checkpoint_files[-1]
        last_checkpoint_renamed = output_dir / "checkpoint_last.pth"
        
        # Rename last checkpoint
        if last_checkpoint.exists():
            last_checkpoint.rename(last_checkpoint_renamed)
            print(f"   ✅ Kept last checkpoint: {last_checkpoint_renamed.name}")
        
        # The best checkpoint is already saved as scene_classifier_model.pth
        # But also keep the best epoch checkpoint if it exists
        best_checkpoint = output_dir / f"checkpoint_epoch_{best_epoch}.pth"
        if best_checkpoint.exists() and best_checkpoint != last_checkpoint_renamed:
            best_checkpoint_renamed = output_dir / "checkpoint_best.pth"
            best_checkpoint.rename(best_checkpoint_renamed)
            print(f"   ✅ Kept best checkpoint: {best_checkpoint_renamed.name} (epoch {best_epoch})")
        
        # Delete all other intermediate checkpoints
        deleted_count = 0
        for checkpoint in checkpoint_files:
            if checkpoint.exists():
                checkpoint.unlink()
                deleted_count += 1
        
        if deleted_count > 0:
            print(f"   🗑️  Deleted {deleted_count} intermediate checkpoint(s)")
        
        print(f"   📁 Final checkpoints:")
        print(f"      - scene_classifier_model.pth (best model)")
        if (output_dir / "checkpoint_best.pth").exists():
            print(f"      - checkpoint_best.pth (best epoch {best_epoch})")
        if (output_dir / "checkpoint_last.pth").exists():
            print(f"      - checkpoint_last.pth (last epoch {args.epochs})")
    else:
        print(f"   ℹ️  No checkpoint files to clean up")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Analyze scene classifier dataset and performance.

Evaluates whether current dataset size and 66.8% accuracy is sufficient.
"""

import os
import sys
import argparse
import pickle
import json
from pathlib import Path
from collections import Counter
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.compress.utils.classify_scene import CLASS_MAPPING


def analyze_dataset(dataset_file):
    """Analyze dataset statistics"""
    print(f"📊 Analyzing dataset: {dataset_file}")
    print("=" * 60)
    
    if not os.path.exists(dataset_file):
        print(f"❌ Dataset file not found: {dataset_file}")
        return None
    
    # Load dataset
    with open(dataset_file, 'rb') as f:
        data = pickle.load(f)
    
    print(f"✅ Loaded dataset")
    print(f"   Total samples: {len(data)}")
    print()
    
    # Analyze class distribution
    labels = [item.get('label', 'unknown') for item in data]
    label_counts = Counter(labels)
    
    print("📈 Class Distribution:")
    print("-" * 60)
    total = len(labels)
    for label in sorted(CLASS_MAPPING.keys()):
        count = label_counts.get(label, 0)
        percentage = 100 * count / total if total > 0 else 0
        bar = "█" * int(percentage / 2)
        print(f"   {label:40s}: {count:4d} ({percentage:5.1f}%) {bar}")
    
    print()
    
    # Check for class imbalance
    counts = list(label_counts.values())
    min_count = min(counts) if counts else 0
    max_count = max(counts) if counts else 0
    imbalance_ratio = max_count / min_count if min_count > 0 else float('inf')
    
    print("⚖️  Class Balance Analysis:")
    print("-" * 60)
    if imbalance_ratio < 2.0:
        print(f"   ✅ Well balanced (ratio: {imbalance_ratio:.2f})")
    elif imbalance_ratio < 5.0:
        print(f"   ⚠️  Moderate imbalance (ratio: {imbalance_ratio:.2f})")
        print(f"      Consider data augmentation or class weights")
    else:
        print(f"   ❌ Severe imbalance (ratio: {imbalance_ratio:.2f})")
        print(f"      Strongly recommend balancing the dataset")
    
    print()
    
    # Minimum samples per class
    min_samples = min(counts) if counts else 0
    print(f"📉 Minimum samples per class: {min_samples}")
    
    # Recommendations
    print()
    print("💡 Dataset Size Recommendations:")
    print("-" * 60)
    
    if total < 200:
        print(f"   ❌ Very small dataset ({total} samples)")
        print(f"      Minimum recommended: 500+ samples")
        print(f"      Target: 1000-2000 samples")
        recommendation = "insufficient"
    elif total < 500:
        print(f"   ⚠️  Small dataset ({total} samples)")
        print(f"      Minimum recommended: 500+ samples")
        print(f"      Target: 1000-2000 samples")
        recommendation = "small"
    elif total < 1000:
        print(f"   ✅ Moderate dataset ({total} samples)")
        print(f"      Good for initial training")
        print(f"      Target: 1000-2000 samples for best results")
        recommendation = "moderate"
    else:
        print(f"   ✅ Good dataset size ({total} samples)")
        print(f"      Sufficient for training")
        recommendation = "sufficient"
    
    return {
        'total_samples': total,
        'class_distribution': dict(label_counts),
        'imbalance_ratio': imbalance_ratio,
        'min_samples_per_class': min_samples,
        'recommendation': recommendation
    }


def evaluate_accuracy(accuracy, num_classes=6):
    """Evaluate if accuracy is sufficient"""
    print()
    print("🎯 Accuracy Analysis:")
    print("=" * 60)
    print(f"   Current validation accuracy: {accuracy:.2f}%")
    print()
    
    # Baseline comparisons
    random_baseline = 100.0 / num_classes
    print(f"📊 Baseline Comparisons:")
    print(f"   Random guessing (6 classes): {random_baseline:.1f}%")
    print(f"   Your model: {accuracy:.2f}%")
    print(f"   Improvement over random: {accuracy / random_baseline:.2f}x")
    print()
    
    # Accuracy evaluation
    print("📈 Accuracy Assessment:")
    print("-" * 60)
    
    if accuracy < 50:
        print(f"   ❌ Poor performance ({accuracy:.1f}%)")
        print(f"      Model is barely better than random")
        print(f"      Strongly recommend:")
        print(f"      - More training data (2000+ samples)")
        print(f"      - Check for data quality issues")
        print(f"      - Consider different model architecture")
        assessment = "poor"
    elif accuracy < 65:
        print(f"   ⚠️  Below average ({accuracy:.1f}%)")
        print(f"      Model is learning but needs improvement")
        print(f"      Recommendations:")
        print(f"      - More training data (1500+ samples)")
        print(f"      - Check class balance")
        print(f"      - Try longer training or different hyperparameters")
        assessment = "below_average"
    elif accuracy < 75:
        print(f"   ✅ Decent performance ({accuracy:.1f}%)")
        print(f"      Model is working but can be improved")
        print(f"      For production use, consider:")
        print(f"      - More training data (1000-2000 samples)")
        print(f"      - Fine-tuning hyperparameters")
        print(f"      - Data augmentation")
        assessment = "decent"
    elif accuracy < 85:
        print(f"   ✅ Good performance ({accuracy:.1f}%)")
        print(f"      Model is performing well")
        print(f"      Minor improvements possible with:")
        print(f"      - More diverse training data")
        print(f"      - Hyperparameter tuning")
        assessment = "good"
    else:
        print(f"   ✅ Excellent performance ({accuracy:.1f}%)")
        print(f"      Model is performing very well")
        print(f"      Ready for production use")
        assessment = "excellent"
    
    return assessment


def main():
    parser = argparse.ArgumentParser(description="Analyze scene classifier dataset and performance")
    parser.add_argument("--dataset", type=str, required=True,
                       help="Path to dataset.pkl file")
    parser.add_argument("--accuracy", type=float, default=66.8,
                       help="Current validation accuracy (default: 66.8)")
    
    args = parser.parse_args()
    
    # Analyze dataset
    dataset_stats = analyze_dataset(args.dataset)
    
    if dataset_stats is None:
        return
    
    # Evaluate accuracy
    accuracy_assessment = evaluate_accuracy(args.accuracy)
    
    # Combined recommendations
    print()
    print("=" * 60)
    print("📋 Final Recommendations:")
    print("=" * 60)
    
    total_samples = dataset_stats['total_samples']
    min_per_class = dataset_stats['min_samples_per_class']
    
    if accuracy_assessment in ["poor", "below_average"]:
        print("❌ Dataset is likely insufficient for good performance")
        print()
        print("Recommended actions:")
        print("   1. Collect more training data:")
        print(f"      - Current: {total_samples} samples")
        print(f"      - Target: 1500-2000+ samples")
        print(f"      - Minimum per class: 200+ samples")
        print()
        print("   2. Check data quality:")
        print("      - Verify labels are correct")
        print("      - Remove ambiguous/unclear samples")
        print("      - Ensure class balance")
        print()
        print("   3. Consider:")
        print("      - Data augmentation")
        print("      - Class weights in loss function")
        print("      - Longer training (more epochs)")
        print("      - Different model architecture")
        
    elif accuracy_assessment == "decent":
        if total_samples < 1000:
            print("⚠️  Dataset size is limiting performance")
            print()
            print("Recommended actions:")
            print("   1. Collect more data:")
            print(f"      - Current: {total_samples} samples")
            print(f"      - Target: 1000-2000 samples")
            print()
            print("   2. Current accuracy (66.8%) is acceptable but can improve")
            print("      - More data should push accuracy to 75-80%+")
            print()
            print("   3. For production:")
            print("      - Can use current model if 66.8% is acceptable")
            print("      - Or wait for more data for better performance")
        else:
            print("✅ Dataset size is adequate")
            print()
            print("Current accuracy (66.8%) can be improved with:")
            print("   - Hyperparameter tuning")
            print("   - Longer training")
            print("   - Better data augmentation")
            print("   - More diverse samples")
    else:
        print("✅ Performance is good!")
        print("   Current dataset and accuracy are sufficient")
    
    print()
    print("=" * 60)
    
    # Save analysis
    analysis = {
        'dataset_stats': dataset_stats,
        'accuracy': args.accuracy,
        'accuracy_assessment': accuracy_assessment,
        'recommendations': {
            'needs_more_data': accuracy_assessment in ["poor", "below_average"] or 
                             (accuracy_assessment == "decent" and total_samples < 1000),
            'target_samples': 2000 if accuracy_assessment in ["poor", "below_average"] else 1000,
            'min_samples_per_class': 200 if accuracy_assessment in ["poor", "below_average"] else 100
        }
    }
    
    output_file = Path(args.dataset).parent / "dataset_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"💾 Analysis saved to: {output_file}")


if __name__ == "__main__":
    main()





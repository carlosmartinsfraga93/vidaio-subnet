#!/usr/bin/env python3
"""
Find optimal number of estimators for gradient boosting.

Tests different n_estimators values and finds the best one based on validation performance.
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import json
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.compress.utils.data_preprocessing import (
    ColumnDropper,
    VMAFScaler,
    TargetExtractor,
    CQScaler,
    ResolutionTransformer,
    FeatureScaler,
    FrameRateTransformer
)
from sklearn.pipeline import Pipeline


def create_pipeline(n_estimators):
    """Create preprocessing pipeline with specified n_estimators"""
    feature_columns = [
        'metrics_avg_motion',
        'metrics_avg_edge_density',
        'metrics_avg_texture',
        'metrics_avg_temporal_information',
        'metrics_avg_spatial_information',
        'metrics_avg_color_complexity',
        'metrics_avg_motion_variance',
        'metrics_avg_grain_noise'
    ]
    
    predictor = GradientBoostingRegressor(
        n_estimators=n_estimators,
        learning_rate=0.1,
        max_depth=6,
        min_samples_split=2,
        min_samples_leaf=1,
        subsample=0.8,
        random_state=42,
        verbose=0  # Suppress output during grid search
    )
    
    pipeline = Pipeline([
        ('column_dropper', ColumnDropper(columns_to_drop=['video_id', 'original_path', 'codec'])),
        ('resolution_transformer', ResolutionTransformer(
            resolution_column='metrics_resolution',
            verbose=False
        )),
        ('frame_rate_transformer', FrameRateTransformer(
            frame_rate_column='metrics_frame_rate',
            verbose=False
        )),
        ('cq_scaler', CQScaler(
            cq_column='cq',
            codec='auto',
            verbose=False
        )),
        ('feature_scaler', FeatureScaler(
            columns_to_scale=feature_columns,
            scaling_type='minmax',
            excluded_columns=[],
            verbose=False
        )),
        ('vmaf_scaler', VMAFScaler(
            target_column='vmaf',
            clip_values=True,
            verbose=False
        )),
        ('target_extractor', TargetExtractor(
            target_column='vmaf',
            vmaf_scaler=None
        )),
        ('vmaf_predictor', predictor)
    ])
    
    return pipeline


def main():
    parser = argparse.ArgumentParser(description="Find optimal n_estimators for gradient boosting")
    parser.add_argument("--data_dir", type=str, required=True,
                       help="Directory containing vmaf_dataset.csv")
    parser.add_argument("--test_size", type=float, default=0.2,
                       help="Test set size (0.0 to 1.0)")
    parser.add_argument("--min_estimators", type=int, default=100,
                       help="Minimum n_estimators to test")
    parser.add_argument("--max_estimators", type=int, default=1000,
                       help="Maximum n_estimators to test")
    parser.add_argument("--step", type=int, default=100,
                       help="Step size for n_estimators")
    parser.add_argument("--output", type=str, default="estimator_analysis.json",
                       help="Output file for results")
    
    args = parser.parse_args()
    
    # Load dataset
    dataset_file = Path(args.data_dir) / "vmaf_dataset.csv"
    if not dataset_file.exists():
        print(f"❌ Dataset file not found: {dataset_file}")
        return
    
    print(f"📊 Loading dataset from {dataset_file}...")
    df = pd.read_csv(dataset_file)
    print(f"   Dataset shape: {df.shape}")
    
    # Prepare data
    X = df.drop('vmaf', axis=1)
    y = df['vmaf']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=42
    )
    print(f"   Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    print()
    
    # Test different n_estimators
    n_estimators_range = range(args.min_estimators, args.max_estimators + 1, args.step)
    results = []
    
    print("🔍 Testing different n_estimators values...")
    print("=" * 80)
    print(f"{'Estimators':<12} {'Train R²':<12} {'Test R²':<12} {'Test RMSE':<12} {'Time (s)':<12}")
    print("-" * 80)
    
    best_r2 = -np.inf
    best_n_estimators = None
    best_result = None
    
    for n_est in n_estimators_range:
        start_time = time.time()
        
        # Create and train pipeline
        pipeline = create_pipeline(n_est)
        pipeline.fit(X_train, y_train)
        
        # Evaluate
        y_train_pred = pipeline.predict(X_train)
        y_test_pred = pipeline.predict(X_test)
        
        train_r2 = r2_score(y_train, y_train_pred)
        test_r2 = r2_score(y_test, y_test_pred)
        test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
        
        elapsed = time.time() - start_time
        
        result = {
            'n_estimators': n_est,
            'train_r2': float(train_r2),
            'test_r2': float(test_r2),
            'test_rmse': float(test_rmse),
            'test_mae': float(mean_absolute_error(y_test, y_test_pred)),
            'training_time': elapsed
        }
        results.append(result)
        
        # Check if best
        if test_r2 > best_r2:
            best_r2 = test_r2
            best_n_estimators = n_est
            best_result = result
        
        # Print results
        marker = " ⭐" if n_est == best_n_estimators else ""
        print(f"{n_est:<12} {train_r2:<12.4f} {test_r2:<12.4f} {test_rmse:<12.4f} {elapsed:<12.1f}{marker}")
    
    print("=" * 80)
    print()
    
    # Summary
    print("📊 Results Summary:")
    print("-" * 80)
    print(f"   Best n_estimators: {best_n_estimators}")
    print(f"   Best Test R²:      {best_r2:.4f}")
    print(f"   Best Test RMSE:    {best_result['test_rmse']:.4f}")
    print(f"   Best Test MAE:     {best_result['test_mae']:.4f}")
    print(f"   Training time:     {best_result['training_time']:.1f}s")
    print()
    
    # Check for overfitting
    train_r2_best = best_result['train_r2']
    gap = train_r2_best - best_r2
    print("🔍 Overfitting Analysis:")
    print("-" * 80)
    if gap < 0.01:
        print(f"   ✅ No significant overfitting (gap: {gap:.4f})")
    elif gap < 0.05:
        print(f"   ⚠️  Minor overfitting (gap: {gap:.4f})")
        print(f"      Consider regularization or early stopping")
    else:
        print(f"   ❌ Significant overfitting (gap: {gap:.4f})")
        print(f"      Model is memorizing training data")
        print(f"      Consider: lower learning_rate, more regularization, or fewer estimators")
    print()
    
    # Recommendations
    print("💡 Recommendations:")
    print("-" * 80)
    
    # Find where improvement plateaus
    improvements = []
    for i in range(1, len(results)):
        prev_r2 = results[i-1]['test_r2']
        curr_r2 = results[i]['test_r2']
        improvement = curr_r2 - prev_r2
        improvements.append((results[i]['n_estimators'], improvement))
    
    # Find where improvement drops below threshold
    threshold = 0.001  # 0.1% improvement
    plateau_point = None
    for n_est, improvement in improvements:
        if improvement < threshold:
            plateau_point = n_est
            break
    
    if plateau_point:
        print(f"   📈 Performance plateaus around {plateau_point} estimators")
        print(f"      (improvement < {threshold*100}% after this point)")
        print(f"   💡 Recommended: {plateau_point - args.step} estimators")
        print(f"      (good balance of performance and training time)")
    else:
        print(f"   📈 Performance still improving at {args.max_estimators} estimators")
        print(f"   💡 Consider testing higher values (up to 1000-1500)")
    
    # Training time consideration
    avg_time_per_100 = np.mean([r['training_time'] for r in results]) / (args.max_estimators / 100)
    estimated_time_500 = avg_time_per_100 * 5
    
    print(f"   ⏱️  Estimated training time for 500 estimators: ~{estimated_time_500:.0f}s")
    print()
    
    # Save results
    output_data = {
        'dataset_size': len(df),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'best_n_estimators': best_n_estimators,
        'best_metrics': best_result,
        'all_results': results,
        'recommendations': {
            'optimal_estimators': plateau_point - args.step if plateau_point else best_n_estimators,
            'best_estimators': best_n_estimators,
            'overfitting_gap': gap
        }
    }
    
    output_file = Path(args.output)
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"💾 Results saved to: {output_file}")
    print()
    print("🚀 To train with optimal n_estimators:")
    print(f"   python train_preprocessing_pipeline.py \\")
    print(f"       --data_dir {args.data_dir} \\")
    print(f"       --output models/v20251223/preprocessing_pipeline.pkl \\")
    print(f"       --model_type gradient_boosting \\")
    print(f"       --n_estimators {best_n_estimators}")


if __name__ == "__main__":
    main()




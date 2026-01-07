#!/usr/bin/env python3
"""
Train preprocessing pipeline for VMAF prediction.

Creates a scikit-learn pipeline with feature scalers and VMAF prediction model.
"""

import os
import sys
import argparse
import pickle
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

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


def create_preprocessing_pipeline(model_type='gradient_boosting', n_estimators=200):
    """Create preprocessing pipeline with VMAF predictor"""
    
    # Define columns
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
    
    # Create pipeline
    if model_type == 'gradient_boosting':
        predictor = GradientBoostingRegressor(
            n_estimators=n_estimators,
            learning_rate=0.1,
            max_depth=6,
            min_samples_split=2,
            min_samples_leaf=1,
            subsample=0.8,
            random_state=42,
            verbose=1
        )
    elif model_type == 'random_forest':
        predictor = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=15,
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1,
            verbose=1
        )
    elif model_type == 'xgboost':
        predictor = xgb.XGBRegressor(
            n_estimators=n_estimators,
            learning_rate=0.1,
            max_depth=6,
            min_child_weight=1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=1
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
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
    parser = argparse.ArgumentParser(description="Train preprocessing pipeline")
    parser.add_argument("--data_dir", type=str, required=True,
                       help="Directory containing vmaf_dataset.csv")
    parser.add_argument("--output", type=str, default="models/preprocessing_pipeline.pkl",
                       help="Output path for trained pipeline")
    parser.add_argument("--model_type", type=str, default="gradient_boosting",
                       choices=["gradient_boosting", "random_forest", "xgboost"],
                       help="VMAF prediction model type")
    parser.add_argument("--n_estimators", type=int, default=200,
                       help="Number of estimators for ensemble model")
    parser.add_argument("--test_size", type=float, default=0.2,
                       help="Test set size (0.0 to 1.0)")
    parser.add_argument("--random_state", type=int, default=42,
                       help="Random state for reproducibility")
    
    args = parser.parse_args()
    
    # Create output directory early (needed for evaluation file)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    dataset_file = Path(args.data_dir) / "vmaf_dataset.csv"
    if not dataset_file.exists():
        print(f"❌ Dataset file not found: {dataset_file}")
        return
    
    print(f"Loading dataset from {dataset_file}...")
    df = pd.read_csv(dataset_file)
    
    print(f"Dataset shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    
    # Prepare data
    X = df.drop('vmaf', axis=1)
    y = df['vmaf']
    
    # Split data
    if args.test_size > 0:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=args.test_size, random_state=args.random_state
        )
        print(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    else:
        X_train, y_train = X, y
        X_test, y_test = None, None
    
    # Create and train pipeline
    print(f"\n🚀 Training preprocessing pipeline...")
    print(f"   Model type: {args.model_type}")
    print(f"   Estimators: {args.n_estimators}")
    
    pipeline = create_preprocessing_pipeline(
        model_type=args.model_type,
        n_estimators=args.n_estimators
    )
    
    # Train
    print("\nTraining pipeline...")
    pipeline.fit(X_train, y_train)
    
    # Evaluate
    if X_test is not None:
        print("\nEvaluating on test set...")
        y_pred = pipeline.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)
        
        print(f"\nTest Set Metrics:")
        print(f"   MAE:  {mae:.4f}")
        print(f"   MSE:  {mse:.4f}")
        print(f"   RMSE: {rmse:.4f}")
        print(f"   R²:   {r2:.4f}")
        
        # Save evaluation results
        eval_results = {
            'mae': float(mae),
            'mse': float(mse),
            'rmse': float(rmse),
            'r2': float(r2),
            'test_samples': len(X_test)
        }
        
        eval_file = output_path.parent / "pipeline_evaluation.json"
        with open(eval_file, 'w') as f:
            json.dump(eval_results, f, indent=2)
        print(f"   Evaluation results saved to: {eval_file}")
    
    # Save pipeline
    
    with open(output_path, 'wb') as f:
        pickle.dump(pipeline, f)
    
    print(f"\n✅ Pipeline training complete!")
    print(f"   Pipeline saved to: {output_path}")
    
    # Save metadata
    metadata = {
        'model_type': args.model_type,
        'n_estimators': args.n_estimators,
        'training_samples': len(X_train),
        'test_samples': len(X_test) if X_test is not None else 0,
        'features': X_train.columns.tolist()
    }
    
    metadata_file = output_path.parent / "pipeline_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    main()



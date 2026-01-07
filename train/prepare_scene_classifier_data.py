#!/usr/bin/env python3
"""
Prepare training data for scene classifier model.

Extracts frames and video metrics from videos and creates labeled dataset.
"""

import os
import sys
import argparse
import json
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
import torch
from PIL import Image
import cv2

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.compress.utils.analyze_video_fast import analyze_video_fast
from services.compress.utils.classify_scene import (
    extract_frames_from_scene,
    CLASS_MAPPING,
    VIDEO_METRICS
)


class SceneClassifierDataPreparer:
    def __init__(self, data_dir, output_dir):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "frames").mkdir(exist_ok=True)
        (self.output_dir / "metrics").mkdir(exist_ok=True)
        
    def extract_video_features(self, video_path):
        """Extract video metrics and frames"""
        try:
            # Extract video metrics
            video_features = analyze_video_fast(
                str(video_path),
                max_frames=150,
                logging_enabled=False,
                include_quality_metrics=False
            )
            
            if not video_features:
                return None
            
            # Extract frames (3 frames from middle of video)
            # Get video duration
            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            cap.release()
            
            if duration < 1.0:  # Skip very short videos
                return None
            
            # Extract frames from middle section
            start_time = duration * 0.3
            end_time = duration * 0.7
            frame_paths = extract_frames_from_scene(
                str(video_path),
                start_time,
                end_time,
                num_frames=3,
                output_dir=str(self.output_dir / "frames" / video_path.stem)
            )
            
            if not frame_paths:
                return None
            
            # Extract metrics values
            metrics_values = []
            for metric in VIDEO_METRICS:
                if metric in video_features:
                    metrics_values.append(float(video_features[metric]))
                else:
                    metrics_values.append(0.0)
            
            return {
                'video_path': str(video_path),
                'frame_paths': frame_paths,
                'metrics': metrics_values,
                'duration': duration,
                'fps': fps
            }
            
        except Exception as e:
            print(f"Error processing {video_path}: {e}")
            return None
    
    def prepare_dataset(self, videos_dir, labels_file=None):
        """Prepare dataset from videos directory"""
        print(f"\n📊 Preparing scene classifier dataset...")
        print(f"   Videos directory: {videos_dir}")
        print(f"   Output directory: {self.output_dir}")
        
        # Load labels if provided
        labels_dict = {}
        if labels_file and os.path.exists(labels_file):
            with open(labels_file, 'r') as f:
                labels_dict = json.load(f)
            print(f"   Loaded {len(labels_dict)} labels from {labels_file}")
        
        # Find all video files
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        video_files = []
        for ext in video_extensions:
            video_files.extend(Path(videos_dir).rglob(f"*{ext}"))
        
        print(f"   Found {len(video_files)} video files")
        
        # Process videos
        dataset = []
        failed = 0
        
        for video_path in tqdm(video_files, desc="Processing videos"):
            # Get label (from file path or labels file)
            label = self._infer_label(video_path, labels_dict)
            if not label:
                continue
            
            # Extract features
            features = self.extract_video_features(video_path)
            if not features:
                failed += 1
                continue
            
            # Add label
            features['label'] = label
            features['label_id'] = CLASS_MAPPING.get(label, CLASS_MAPPING['other'])
            
            dataset.append(features)
        
        print(f"\n✅ Processed {len(dataset)} videos successfully")
        print(f"   Failed: {failed} videos")
        
        # Save dataset
        dataset_file = self.output_dir / "dataset.pkl"
        with open(dataset_file, 'wb') as f:
            pickle.dump(dataset, f)
        
        # Create summary
        self._create_summary(dataset)
        
        return dataset
    
    def _infer_label(self, video_path, labels_dict):
        """Infer label from file path or labels dict"""
        # Check labels dict first
        if str(video_path) in labels_dict:
            return labels_dict[str(video_path)]
        
        # Infer from directory structure
        path_parts = Path(video_path).parts
        for part in path_parts:
            part_lower = part.lower()
            if 'gaming' in part_lower or 'game' in part_lower:
                return 'Gaming Content'
            elif 'animation' in part_lower or 'cartoon' in part_lower:
                return 'Animation / Cartoon / Rendered Graphics'
            elif 'face' in part_lower or 'people' in part_lower or 'person' in part_lower:
                return 'Faces / People'
            elif 'text' in part_lower or 'screen' in part_lower or 'document' in part_lower:
                return 'Screen Content / Text'
        
        # Default to 'other' if cannot infer
        return 'other'
    
    def _create_summary(self, dataset):
        """Create dataset summary"""
        summary = {
            'total_videos': len(dataset),
            'label_distribution': {},
            'avg_duration': 0,
            'metrics_stats': {}
        }
        
        durations = []
        label_counts = {}
        
        for item in dataset:
            label = item['label']
            label_counts[label] = label_counts.get(label, 0) + 1
            durations.append(item.get('duration', 0))
        
        summary['label_distribution'] = label_counts
        summary['avg_duration'] = np.mean(durations) if durations else 0
        
        # Save summary
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📊 Dataset Summary:")
        print(f"   Total videos: {summary['total_videos']}")
        print(f"   Average duration: {summary['avg_duration']:.2f}s")
        print(f"   Label distribution:")
        for label, count in label_counts.items():
            print(f"      {label}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Prepare scene classifier training data")
    parser.add_argument("--data_dir", type=str, required=True,
                       help="Directory containing video files")
    parser.add_argument("--output_dir", type=str, required=True,
                       help="Output directory for prepared dataset")
    parser.add_argument("--labels_file", type=str, default=None,
                       help="JSON file mapping video paths to labels")
    
    args = parser.parse_args()
    
    preparer = SceneClassifierDataPreparer(args.data_dir, args.output_dir)
    dataset = preparer.prepare_dataset(args.data_dir, args.labels_file)
    
    print(f"\n✅ Dataset preparation complete!")
    print(f"   Dataset saved to: {args.output_dir}/dataset.pkl")


if __name__ == "__main__":
    main()



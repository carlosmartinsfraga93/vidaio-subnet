#!/usr/bin/env python3
"""
Debug script to process a single video and see what's happening
"""

import os
import sys
import argparse
from pathlib import Path
import cv2
import subprocess
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.compress.utils.analyze_video_fast import analyze_video_fast
from train.prepare_preprocessing_pipeline_data import PreprocessingPipelineDataPreparer


def debug_single_video(video_path, output_dir="debug_output"):
    """Debug processing of a single video"""
    print(f"🔍 Debugging video processing")
    print(f"   Video: {video_path}")
    print("=" * 60)
    
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    # Step 1: Check video properties
    print("\n1️⃣  Checking video properties...")
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    print(f"   Duration: {duration:.2f}s")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps:.2f}")
    print(f"   Total frames: {total_frames}")
    
    if duration > 600:
        print(f"   ⚠️  Video is longer than 600s - will be skipped!")
        return
    
    # Step 2: Extract video features
    print("\n2️⃣  Extracting video features...")
    try:
        video_features = analyze_video_fast(
            str(video_path),
            max_frames=150,
            logging_enabled=False
        )
        
        if not video_features:
            print("   ❌ Feature extraction returned None - video will be skipped")
            return
        
        print(f"   ✅ Features extracted successfully")
        print(f"   Metrics: {list(video_features.keys())[:5]}...")
    except Exception as e:
        print(f"   ❌ Feature extraction failed: {e}")
        return
    
    # Step 3: Test encoding
    print("\n3️⃣  Testing video encoding...")
    preparer = PreprocessingPipelineDataPreparer(".", ".")
    
    # Test AV1 encoding
    print("   Testing AV1 encoding...")
    temp_dir = Path(tempfile.mkdtemp())
    encoded_path = temp_dir / "test_av1.mp4"
    
    cq_value = 30  # Test with one CQ value
    success = preparer.encode_video(video_path, encoded_path, 'av1_nvenc', cq_value)
    
    if success:
        print(f"   ✅ AV1 encoding successful: {encoded_path}")
        encoded_size = encoded_path.stat().st_size if encoded_path.exists() else 0
        original_size = video_path.stat().st_size
        print(f"   Original size: {original_size / 1024 / 1024:.2f} MB")
        print(f"   Encoded size: {encoded_size / 1024 / 1024:.2f} MB")
        print(f"   Compression ratio: {original_size / encoded_size:.2f}x" if encoded_size > 0 else "N/A")
    else:
        print(f"   ❌ AV1 encoding failed")
        print(f"   Check if NVENC is available: nvidia-smi")
        return
    
    # Step 4: Test VMAF calculation
    print("\n4️⃣  Testing VMAF calculation...")
    if preparer.has_vmaf_support:
        print("   ✅ VMAF support available")
        print("   Calculating VMAF (this may take a moment)...")
        
        # Try direct FFmpeg command to see errors
        print("   Running FFmpeg VMAF command...")
        output_file = temp_dir / "vmaf_output.json"
        cmd = [
            preparer.ffmpeg_bin, '-y',
            '-i', str(video_path),
            '-i', str(encoded_path),
            '-lavfi', f'libvmaf=log_fmt=json:log_path={output_file}',
            '-f', 'null', '-'
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )
        
        if result.returncode != 0:
            print(f"   ❌ FFmpeg command failed!")
            print(f"   Return code: {result.returncode}")
            print(f"   Error output:")
            print(result.stderr.decode('utf-8', errors='ignore')[:500])
        else:
            print(f"   ✅ FFmpeg command succeeded")
            if output_file.exists():
                import json
                with open(output_file, 'r') as f:
                    vmaf_data = json.load(f)
                if 'frames' in vmaf_data and len(vmaf_data['frames']) > 0:
                    scores = [f.get('metrics', {}).get('vmaf', 0) for f in vmaf_data['frames']]
                    vmaf_score = sum(scores) / len(scores) if scores else None
                    print(f"   ✅ VMAF calculated: {vmaf_score:.2f}")
                else:
                    print(f"   ⚠️  VMAF data structure unexpected")
                    print(f"   Keys: {list(vmaf_data.keys())}")
            else:
                print(f"   ❌ VMAF output file not created")
        
        # Also try the preparer's method
        vmaf_score = preparer.calculate_vmaf(video_path, encoded_path)
        
        if vmaf_score is not None:
            print(f"   ✅ Preparer method VMAF: {vmaf_score:.2f}")
        else:
            print(f"   ❌ Preparer method VMAF calculation returned None")
            print(f"   This is why samples aren't being collected!")
    else:
        print("   ⚠️  VMAF support not available")
        print("   Will use estimated VMAF (not accurate)")
        vmaf_score = 50.0  # Placeholder
    
    # Step 5: Check what would be saved
    print("\n5️⃣  What would be saved to dataset:")
    if success and (vmaf_score is not None or not preparer.has_vmaf_support):
        print("   ✅ This video would create a dataset sample!")
        print(f"   Codec: av1_nvenc")
        print(f"   CQ: {cq_value}")
        if vmaf_score:
            print(f"   VMAF: {vmaf_score:.2f}")
        print(f"   Resolution: {width}x{height}")
        print(f"   FPS: {fps:.2f}")
    else:
        print("   ❌ This video would NOT create a dataset sample")
        if not success:
            print("      Reason: Encoding failed")
        if preparer.has_vmaf_support and vmaf_score is None:
            print("      Reason: VMAF calculation failed")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    
    print("\n" + "=" * 60)
    print("✅ Debug complete!")


def main():
    parser = argparse.ArgumentParser(description="Debug preprocessing pipeline for a single video")
    parser.add_argument("video_path", type=str, help="Path to video file")
    parser.add_argument("--output_dir", type=str, default="debug_output", help="Output directory")
    
    args = parser.parse_args()
    
    debug_single_video(args.video_path, args.output_dir)


if __name__ == "__main__":
    main()


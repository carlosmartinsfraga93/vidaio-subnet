"""
Test script for Netflix Per-Title Encoding

This script demonstrates how to use the Netflix per-title encoding module
and compares it with the traditional lookup table method.
"""

import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netflix_per_title_encoder import (
    netflix_per_title_encoding,
    should_use_netflix_per_title,
    ENABLE_NETFLIX_PER_TITLE
)


def test_netflix_per_title():
    """
    Test Netflix per-title encoding on a sample video.
    """
    
    print("=" * 80)
    print("Netflix Per-Title Encoding Test")
    print("=" * 80)
    
    # Check if enabled
    print(f"\n1. Checking if Netflix per-title is enabled...")
    print(f"   ENABLE_NETFLIX_PER_TITLE = {ENABLE_NETFLIX_PER_TITLE}")
    
    if not ENABLE_NETFLIX_PER_TITLE:
        print("\n   ⚠️ Netflix per-title is DISABLED!")
        print("   To enable, edit netflix_per_title_encoder.py:")
        print("   Set ENABLE_NETFLIX_PER_TITLE = True")
        return
    
    # Sample configuration
    config = {
        'video_processing': {
            'use_netflix_per_title': True,
            'netflix_fast_mode': False,  # Use 4 probes
            'codec': 'av1_nvenc',
            'codec_mode': 'CRF',
            'target_vmaf': 93.0,
            'target_quality': 'High',
            'target_bitrate': 10.0,
        },
        'vmaf_calculation': {
            'use_vmafneg': False,
            'calculate_scene_vmaf': True,
            'vmaf_use_sampling': True,
            'vmaf_num_clips': 3,
            'vmaf_clip_duration': 2,
        },
        'model_paths': {
            'default_vmaf_model': None,
            'vmafneg_model': None,
        },
        'directories': {
            'temp_dir': './videos/temp_scenes',
            'encoded_scenes_dir': './videos/encoded_scenes',
        }
    }
    
    print(f"\n2. Configuration:")
    print(f"   Codec: {config['video_processing']['codec']}")
    print(f"   Target VMAF: {config['video_processing']['target_vmaf']}")
    print(f"   Fast Mode: {config['video_processing']['netflix_fast_mode']}")
    print(f"   Use Netflix: {should_use_netflix_per_title(config)}")
    
    # Sample scene metadata
    # Look for videos in the tmp folder (where downloaded videos are stored)
    tmp_folder = "/workspace/vidaio-subnet/tmp"
    test_video_path = None

    # Try to find any .mp4 file in tmp folder
    if os.path.exists(tmp_folder):
        for file in os.listdir(tmp_folder):
            if file.endswith('.mp4'):
                test_video_path = os.path.join(tmp_folder, file)
                break

    # Fallback to default path
    if not test_video_path:
        test_video_path = "./videos/test_scene.mp4"

    if not os.path.exists(test_video_path):
        print(f"\n   ⚠️ Test video not found!")
        print(f"   Searched in:")
        print(f"   - {tmp_folder}")
        print(f"   - ./videos/test_scene.mp4")
        print(f"\n   Please provide a test video file in one of these locations.")
        print(f"   You can use any short video (5-10 seconds) for testing.")
        return
    
    scene_metadata = {
        'path': test_video_path,
        'scene_number': 1,
        'duration': 5.0,
        'start_time': 0.0,
        'end_time': 5.0,
        'scene_type': 'default',  # Will be classified
        'original_video_metadata': {
            'target_codec': 'av1_nvenc'
        }
    }
    
    print(f"\n3. Test video:")
    print(f"   Path: {test_video_path}")
    print(f"   Duration: {scene_metadata['duration']}s")
    
    # Create directories
    os.makedirs(config['directories']['temp_dir'], exist_ok=True)
    os.makedirs(config['directories']['encoded_scenes_dir'], exist_ok=True)
    
    # Prepare resources
    resources = {
        'temp_dir': config['directories']['temp_dir'],
        'encoded_scenes_dir': config['directories']['encoded_scenes_dir']
    }
    
    print(f"\n4. Running Netflix per-title encoding...")
    print("-" * 80)
    
    start_time = time.time()
    
    try:
        result = netflix_per_title_encoding(
            scene_metadata=scene_metadata,
            config=config,
            resources=resources,
            target_vmaf=config['video_processing']['target_vmaf'],
            target_quality_level='High',
            logging_enabled=True
        )
        
        total_time = time.time() - start_time
        
        print("-" * 80)
        print(f"\n5. Results:")
        print(f"   ✅ Encoding successful!")
        print(f"   Encoded path: {result.get('encoded_path')}")
        print(f"   Optimal CQ: {result.get('cq_used')}")
        print(f"   Actual VMAF: {result.get('actual_vmaf', 'N/A')}")
        print(f"   Estimated VMAF: {result.get('estimated_vmaf', 'N/A')}")
        print(f"   Total time: {total_time:.1f}s")
        print(f"   Encoding method: {result.get('encoding_method')}")
        
        # Show probe results
        probe_results = result.get('probe_results', [])
        if probe_results:
            print(f"\n   Probe Results:")
            for cq, vmaf, size in probe_results:
                status = "✅" if vmaf and vmaf >= config['video_processing']['target_vmaf'] else "⚠️"
                print(f"      {status} CQ={cq}: VMAF={vmaf:.2f if vmaf else 'N/A'}, Size={size:.2f} MB")
        
    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)


def compare_methods():
    """
    Compare Netflix per-title vs lookup table method.
    
    This requires running the same video through both methods.
    """
    print("\n" + "=" * 80)
    print("Comparison: Netflix Per-Title vs Lookup Table")
    print("=" * 80)
    
    print("\nThis comparison requires:")
    print("1. A test video file")
    print("2. Running encoding with both methods")
    print("3. Comparing results")
    
    print("\nTo run comparison:")
    print("1. First run with ENABLE_NETFLIX_PER_TITLE = False (lookup table)")
    print("2. Then run with ENABLE_NETFLIX_PER_TITLE = True (Netflix per-title)")
    print("3. Compare the results")
    
    print("\nExpected differences:")
    print("- Netflix per-title: More accurate VMAF, optimal file size, slower")
    print("- Lookup table: Faster, may not achieve target VMAF exactly")


if __name__ == "__main__":
    test_netflix_per_title()
    compare_methods()


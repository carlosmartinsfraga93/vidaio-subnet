"""
Quick test script for Netflix Per-Title Encoding
Automatically finds videos in /workspace/vidaio-subnet/tmp folder
"""

import os
import sys
import time
import glob

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netflix_per_title_encoder import (
    netflix_per_title_encoding,
    should_use_netflix_per_title,
    ENABLE_NETFLIX_PER_TITLE,
    ENABLE_PARALLEL_ENCODING,
    ENABLE_PARALLEL_VMAF
)


def find_test_video():
    """Find a test video in the tmp folder."""
    tmp_folder = "/workspace/vidaio-subnet/tmp"
    
    if not os.path.exists(tmp_folder):
        print(f"❌ Tmp folder not found: {tmp_folder}")
        return None
    
    # Find all .mp4 files
    video_files = glob.glob(os.path.join(tmp_folder, "*.mp4"))
    
    if not video_files:
        print(f"❌ No .mp4 files found in {tmp_folder}")
        return None
    
    # Use the first video found
    return video_files[0]


def main():
    print("=" * 80)
    print("Netflix Per-Title Encoding - Quick Test")
    print("=" * 80)
    
    # Check if enabled
    print(f"\n✅ Configuration:")
    print(f"   ENABLE_NETFLIX_PER_TITLE = {ENABLE_NETFLIX_PER_TITLE}")
    print(f"   ENABLE_PARALLEL_ENCODING = {ENABLE_PARALLEL_ENCODING}")
    print(f"   ENABLE_PARALLEL_VMAF = {ENABLE_PARALLEL_VMAF}")
    
    if not ENABLE_NETFLIX_PER_TITLE:
        print("\n❌ Netflix per-title is DISABLED!")
        print("   To enable, edit services/compress/netflix_per_title_encoder.py:")
        print("   Set ENABLE_NETFLIX_PER_TITLE = True")
        return
    
    # Find test video
    print(f"\n🔍 Looking for test video in /workspace/vidaio-subnet/tmp...")
    test_video = find_test_video()
    
    if not test_video:
        print("\n❌ No test video found!")
        print("   Please download a video to /workspace/vidaio-subnet/tmp/")
        return
    
    print(f"✅ Found test video: {os.path.basename(test_video)}")
    print(f"   Size: {os.path.getsize(test_video) / (1024*1024):.2f} MB")
    
    # Get video duration
    try:
        import subprocess
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', test_video]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        duration = float(result.stdout.strip()) if result.returncode == 0 else 5.0
    except:
        duration = 5.0
    
    print(f"   Duration: {duration:.1f}s")
    
    # Configuration
    config = {
        'video_processing': {
            'use_netflix_per_title': True,
            'netflix_fast_mode': True,  # Use fast mode for quick test
            'codec': 'av1_nvenc',
            'codec_mode': 'CRF',
            'target_vmaf': 93.0,
            'target_quality': 'High',
            'target_bitrate': 10.0,
        },
        'vmaf_calculation': {
            'use_vmafneg': True,  # Use vmafneg model (same as validator)
            'calculate_scene_vmaf': True,
            'vmaf_use_sampling': True,
            'vmaf_num_clips': 1,  # Fast mode: 1 clip
            'vmaf_clip_duration': 1,  # Fast mode: 1 second
        },
        'model_paths': {
            'default_vmaf_model': None,
            'vmafneg_model': '/usr/local/share/vmaf/model/vmaf_v0.6.1neg.json',  # vmafneg model path
        },
        'directories': {
            'temp_dir': '/workspace/vidaio-subnet/tmp/netflix_test',
            'encoded_scenes_dir': '/workspace/vidaio-subnet/tmp/netflix_test_output',
        }
    }
    
    # Create directories
    os.makedirs(config['directories']['temp_dir'], exist_ok=True)
    os.makedirs(config['directories']['encoded_scenes_dir'], exist_ok=True)
    
    # Scene metadata
    scene_metadata = {
        'path': test_video,
        'scene_number': 1,
        'duration': duration,
        'start_time': 0.0,
        'end_time': duration,
        'scene_type': 'default',
        'original_video_metadata': {
            'target_codec': 'av1_nvenc'
        }
    }
    
    # Resources
    resources = {
        'temp_dir': config['directories']['temp_dir'],
        'encoded_scenes_dir': config['directories']['encoded_scenes_dir']
    }
    
    print(f"\n🎬 Running Netflix Per-Title Encoding...")
    print(f"   Mode: Fast (3 probes, 1 VMAF clip)")
    print(f"   Target VMAF: 93.0")
    print("-" * 80)
    
    start_time = time.time()
    
    try:
        result = netflix_per_title_encoding(
            scene_metadata=scene_metadata,
            config=config,
            resources=resources,
            target_vmaf=93.0,
            target_quality_level='High',
            logging_enabled=True
        )
        
        total_time = time.time() - start_time
        
        print("-" * 80)
        print(f"\n✅ SUCCESS!")
        print(f"   Encoded path: {result.get('encoded_path')}")
        print(f"   Optimal CQ: {result.get('cq_used')}")
        print(f"   Actual VMAF: {result.get('actual_vmaf', 'N/A')}")
        print(f"   Total time: {total_time:.1f}s")
        
        # Show probe results
        probe_results = result.get('probe_results', [])
        if probe_results:
            print(f"\n   Probe Results:")
            for cq, vmaf, size in probe_results:
                status = "✅" if vmaf and vmaf >= 93.0 else "⚠️"
                vmaf_str = f"{vmaf:.2f}" if vmaf is not None else "N/A"
                print(f"      {status} CQ={cq}: VMAF={vmaf_str}, Size={size:.2f} MB")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()


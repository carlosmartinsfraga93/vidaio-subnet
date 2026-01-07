"""
Debug script to test fast VMAF calculation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.calculate_vmaf_fast import calculate_vmaf_fast_libvmaf

# Test with actual files
reference = "/workspace/vidaio-subnet/tmp/a2024802-4ba1-48d4-9d9f-e6d737e7a2d2.mp4"
distorted = "/workspace/vidaio-subnet/tmp/netflix_test/netflix_probes_scene_1/probe_cq22.mp4"

print("Testing Fast VMAF Calculation")
print("=" * 80)
print(f"Reference: {reference}")
print(f"Distorted: {distorted}")
print(f"Reference exists: {os.path.exists(reference)}")
print(f"Distorted exists: {os.path.exists(distorted)}")
print()

if os.path.exists(reference) and os.path.exists(distorted):
    print("Running VMAF calculation...")
    vmaf_score = calculate_vmaf_fast_libvmaf(
        reference_path=reference,
        distorted_path=distorted,
        model_path=None,
        num_clips=1,
        clip_duration=1.0,
        max_frames_per_clip=30,
        logging_enabled=True
    )
    
    print()
    print("=" * 80)
    if vmaf_score is not None:
        print(f"✅ VMAF Score: {vmaf_score:.2f}")
    else:
        print("❌ VMAF calculation failed")
else:
    print("❌ Files not found!")
    print("\nPlease run the Netflix test first to generate encoded files:")
    print("  python services/compress/test_netflix_quick.py")


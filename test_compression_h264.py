#!/usr/bin/env python3
"""
Test compression with H.264 (libx264) encoder - works with current FFmpeg build.
This tests if VMAF calculation is working, using available encoders.
"""

import os
import sys
import json
from pathlib import Path

# Add services/compress directory to path
compress_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'services', 'compress')
sys.path.insert(0, compress_dir)

# Import full compression pipeline
from server import video_compressor

def test_h264_compression():
    """Test compression with H.264 encoder (available in current FFmpeg)"""
    
    print("="*80)
    print("H.264 COMPRESSION TEST (with VMAF)")
    print("="*80)
    print()
    print("This tests compression using libx264 (H.264) encoder")
    print("which is available in your current FFmpeg build.")
    print()
    
    # Find test video
    test_video = "tmp/def5313c-40c9-4563-b28b-c846dc3795ee.mp4"
    
    if not os.path.exists(test_video):
        print(f"❌ Test video not found: {test_video}")
        print()
        print("Please ensure you have a test video in the tmp/ directory")
        return False
    
    print(f"📁 Test video: {test_video}")
    print()
    
    # Configuration for H.264 compression
    config = {
        'target_quality': 'Low',  # Low = VMAF 85
        'target_codec': 'h264',   # Use H.264 instead of AV1
        'codec_mode': 'CRF',      # Use CRF mode for H.264
        'max_duration': 3600,
        'output_dir': 'output',
        'scene_detection_mode': 'disabled',  # Disable scene detection for faster testing
        'enable_preprocessing': False,       # Skip preprocessing
        'enable_time_based_fallback': False,
        'ai_encoding_method': 'quality_based_cq_lookup',
        'verbose': True
    }
    
    print("🎬 Starting compression test...")
    print(f"   Codec: H.264 (libx264)")
    print(f"   Target Quality: Low (VMAF ~85)")
    print(f"   Mode: CRF")
    print()
    
    try:
        # Run compression
        result = video_compressor(
            video_path=test_video,
            config=config
        )
        
        print()
        print("="*80)
        print("TEST RESULTS")
        print("="*80)
        print()
        
        if result and 'output_path' in result:
            output_path = result['output_path']
            report_path = result.get('report_path', '')
            
            print(f"✅ Compression completed!")
            print(f"   Output: {output_path}")
            print(f"   Report: {report_path}")
            print()
            
            # Check if VMAF was calculated
            if report_path and os.path.exists(report_path):
                with open(report_path, 'r') as f:
                    report = json.load(f)
                
                vmaf_score = report.get('vmaf_score')
                
                if vmaf_score is not None and vmaf_score > 0:
                    print(f"✅ VMAF CALCULATION WORKING!")
                    print(f"   VMAF Score: {vmaf_score:.2f}")
                    print()
                    
                    # Show compression stats
                    original_size = report.get('original_size_mb', 0)
                    compressed_size = report.get('compressed_size_mb', 0)
                    compression_ratio = report.get('compression_ratio', 0)
                    
                    print("📊 Compression Statistics:")
                    print(f"   Original Size: {original_size:.2f} MB")
                    print(f"   Compressed Size: {compressed_size:.2f} MB")
                    print(f"   Compression Ratio: {compression_ratio:.2f}x")
                    print(f"   VMAF Score: {vmaf_score:.2f}")
                    print()
                    
                    return True
                else:
                    print(f"❌ VMAF calculation failed")
                    print(f"   VMAF Score: {vmaf_score}")
                    print()
                    return False
            else:
                print(f"❌ Report file not found: {report_path}")
                return False
        else:
            print(f"❌ Compression failed")
            print(f"   Result: {result}")
            return False
            
    except Exception as e:
        print()
        print(f"❌ Error during compression: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    success = test_h264_compression()
    print()
    
    if success:
        print("="*80)
        print("✅ SUCCESS!")
        print("="*80)
        print()
        print("VMAF calculation is working with H.264 encoder.")
        print()
        print("Next steps:")
        print("  1. Rebuild FFmpeg with NVENC support:")
        print("     bash rebuild_ffmpeg_with_nvenc.sh")
        print()
        print("  2. After rebuild, test with AV1:")
        print("     python quick_test_vmaf_fix.py")
        print()
    else:
        print("="*80)
        print("❌ FAILED")
        print("="*80)
        print()
        print("VMAF calculation is not working.")
        print("Check the error messages above.")
        print()
    
    sys.exit(0 if success else 1)


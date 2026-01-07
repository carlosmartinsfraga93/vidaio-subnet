#!/usr/bin/env python3
"""
Test script for local video compression testing.
Tests compression with files from tmp folder.
"""

import os
import sys
import json
from pathlib import Path

# Add services/compress directory to path
compress_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'services', 'compress')
sys.path.insert(0, compress_dir)

# Import full compression pipeline (includes VMAF calculation)
from server import video_compressor

def test_compression(video_path, target_vmaf=85.0, target_codec='av1', codec_mode='VBR', target_bitrate=20.0):
    """
    Test compression with a local video file.
    
    Args:
        video_path: Path to the video file
        target_vmaf: Target VMAF score (85.0, 89.0, or 93.0)
        target_codec: Target codec ('av1', 'h264', etc.)
        codec_mode: Codec mode ('VBR', 'CRF', etc.)
        target_bitrate: Target bitrate in Mbps
    """
    print(f"\n🧪 === Testing Local Video Compression ===")
    print(f"   📁 Video: {video_path}")
    print(f"   🎯 VMAF: {target_vmaf}")
    print(f"   🎥 Codec: {target_codec}")
    print(f"   ⚙️ Mode: {codec_mode}")
    print(f"   📊 Bitrate: {target_bitrate} Mbps\n")
    
    if not os.path.exists(video_path):
        print(f"❌ Error: Video file not found: {video_path}")
        return False
    
    # Determine quality level from VMAF
    if target_vmaf >= 93.0:
        target_quality = 'High'
    elif target_vmaf >= 89.0:
        target_quality = 'Medium'
    else:
        target_quality = 'Low'
    
    # Default config
    config = {
        'model_paths': {
            'scene_classifier_model': 'services/compress/models/scene_classifier_model.pth',
            'preprocessing_pipeline': 'services/compress/models/preprocessing_pipeline.pkl'
        },
        'video_processing': {
            'target_codec': target_codec,
            'codec_mode': codec_mode,
            'target_bitrate': target_bitrate,
            'target_vmaf': target_vmaf,
            'target_quality': target_quality
        },
        'directories': {
            'temp_dir': 'tmp/test_output'
        }
    }
    
    try:
        # Use full compression pipeline (includes VMAF calculation)
        print("📋 Running full compression pipeline (includes VMAF calculation)...")
        
        # Map codec name
        codec_map = {
            'av1': 'av1_nvenc',
            'h264': 'h264_nvenc',
            'hevc': 'hevc_nvenc'
        }
        mapped_codec = codec_map.get(target_codec.lower(), target_codec)
        
        # Run full compression
        output_path = video_compressor(
            input_file=video_path,
            target_quality=target_quality,
            target_codec=mapped_codec,
            codec_mode=codec_mode,
            target_bitrate=target_bitrate,
            max_duration=3600,
            output_dir='output',
            skip_scene_detection=True,  # Use time-based for testing
            skip_preprocessing=True
        )
        
        if output_path and os.path.exists(output_path):
            input_size = os.path.getsize(video_path) / (1024 * 1024)
            output_size = os.path.getsize(output_path) / (1024 * 1024)
            compression_ratio = ((input_size - output_size) / input_size * 100) if input_size > 0 else 0
            size_ratio = output_size / input_size if input_size > 0 else 1.0
            
            print(f"\n✅ Compression successful!")
            print(f"   📥 Input: {input_size:.2f} MB")
            print(f"   📤 Output: {output_size:.2f} MB")
            print(f"   📊 Compression: {compression_ratio:.1f}% reduction")
            print(f"   📊 Size Ratio: {size_ratio:.4f} ({1/size_ratio:.2f}x compression)")
            print(f"   📁 Output file: {output_path}")
            
            # Try to find and display report
            video_name = Path(video_path).stem
            report_pattern = f"{video_name}*_encoding_report.json"
            output_dir = Path("output")
            reports = list(output_dir.glob(report_pattern))
            
            if reports:
                # Get most recent report
                latest_report = max(reports, key=lambda x: x.stat().st_mtime)
                print(f"\n📄 Report generated: {latest_report.name}")
                
                # Load and show VMAF
                try:
                    with open(latest_report, 'r') as f:
                        report_data = json.load(f)
                    final_vmaf = report_data.get('quality_metrics', {}).get('final_vmaf_score')
                    if final_vmaf is not None:
                        print(f"   ✅ VMAF: {final_vmaf:.2f}")
                    else:
                        print(f"   ⚠️  VMAF: NULL (check report for details)")
                except Exception as e:
                    print(f"   ⚠️  Could not read report: {e}")
            
            return True
        else:
            print(f"\n❌ Compression failed: No output file generated")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during compression: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test local video compression")
    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument("--vmaf", type=float, default=85.0, help="Target VMAF (85.0, 89.0, or 93.0)")
    parser.add_argument("--codec", type=str, default="av1", help="Target codec (av1, h264, etc.)")
    parser.add_argument("--mode", type=str, default="VBR", help="Codec mode (VBR, CRF)")
    parser.add_argument("--bitrate", type=float, default=20.0, help="Target bitrate in Mbps")
    
    args = parser.parse_args()
    
    # Test with the provided video
    success = test_compression(
        video_path=args.video_path,
        target_vmaf=args.vmaf,
        target_codec=args.codec,
        codec_mode=args.mode,
        target_bitrate=args.bitrate
    )
    
    sys.exit(0 if success else 1)


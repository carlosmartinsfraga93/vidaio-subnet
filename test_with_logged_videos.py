#!/usr/bin/env python3
"""
Test compression with logged videos from compression_logs directory.

This script allows you to:
1. List all available logged videos
2. Test compression code changes with real request data
3. Compare results with original compression
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add services/compress directory to path
compress_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'services', 'compress')
sys.path.insert(0, compress_dir)

from server import video_compressor, map_codec_name


def list_logged_videos():
    """List all available logged videos."""
    logs_dir = Path("compression_logs")
    videos_dir = logs_dir / "videos"
    metadata_dir = logs_dir / "metadata"
    
    if not videos_dir.exists():
        print("❌ No compression logs found. Run some compressions first!")
        return []
    
    videos = []
    for video_file in sorted(videos_dir.glob("*.mp4")):
        request_id = video_file.stem
        metadata_file = metadata_dir / f"{request_id}.json"
        
        # Load metadata if available
        metadata = None
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading metadata for {request_id}: {e}")
        
        size_mb = video_file.stat().st_size / (1024 * 1024)
        videos.append({
            'request_id': request_id,
            'path': str(video_file),
            'size_mb': round(size_mb, 2),
            'metadata': metadata
        })
    
    return videos


def display_video_list(videos):
    """Display list of available videos."""
    print(f"\n{'='*80}")
    print(f"📹 AVAILABLE LOGGED VIDEOS ({len(videos)} total)")
    print(f"{'='*80}\n")
    
    for i, video in enumerate(videos, 1):
        print(f"{i}. Request ID: {video['request_id']}")
        print(f"   Path: {video['path']}")
        print(f"   Size: {video['size_mb']} MB")
        
        if video['metadata']:
            req_data = video['metadata'].get('request_data', {})
            print(f"   Original Request:")
            print(f"     - VMAF: {req_data.get('vmaf_threshold', 'N/A')}")
            print(f"     - Codec: {req_data.get('target_codec', 'N/A')}")
            print(f"     - Mode: {req_data.get('codec_mode', 'N/A')}")
            print(f"     - Bitrate: {req_data.get('target_bitrate', 'N/A')} Mbps")
            
            status = video['metadata'].get('error')
            if status:
                print(f"   Status: ❌ Failed - {status}")
            else:
                print(f"   Status: ✅ Success")
        
        print()


def test_compression_with_logged_video(video_path, vmaf=89.0, codec='av1', mode='VBR', bitrate=20.0):
    """
    Test compression with a logged video.
    
    Args:
        video_path: Path to the logged video
        vmaf: Target VMAF threshold
        codec: Target codec
        mode: Codec mode
        bitrate: Target bitrate in Mbps
    """
    print(f"\n{'='*80}")
    print(f"🧪 TESTING COMPRESSION")
    print(f"{'='*80}\n")
    print(f"📁 Video: {video_path}")
    print(f"🎯 VMAF: {vmaf}")
    print(f"🎥 Codec: {codec}")
    print(f"⚙️ Mode: {mode}")
    print(f"📊 Bitrate: {bitrate} Mbps\n")
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return None
    
    # Map VMAF to quality
    if vmaf >= 93.0:
        target_quality = 'High'
    elif vmaf >= 89.0:
        target_quality = 'Medium'
    else:
        target_quality = 'Low'
    
    # Map codec name
    ffmpeg_codec = map_codec_name(codec, prefer_gpu=True)
    
    try:
        print("🎬 Starting compression...\n")
        
        # Run compression
        output_path = video_compressor(
            input_file=video_path,
            target_quality=target_quality,
            target_codec=ffmpeg_codec,
            codec_mode=mode,
            target_bitrate=bitrate,
            max_duration=3600,
            output_dir='output',
            skip_scene_detection=True,
            skip_preprocessing=True
        )
        
        if output_path and Path(output_path).exists():
            print(f"\n✅ Compression completed successfully!")
            print(f"   📁 Output: {output_path}")
            
            # Show file sizes
            input_size = Path(video_path).stat().st_size / (1024 * 1024)
            output_size = Path(output_path).stat().st_size / (1024 * 1024)
            compression_ratio = (1 - output_size / input_size) * 100
            
            print(f"\n📊 Results:")
            print(f"   Input size:  {input_size:.2f} MB")
            print(f"   Output size: {output_size:.2f} MB")
            print(f"   Compression: {compression_ratio:+.1f}%")
            
            return output_path
        else:
            print(f"\n❌ Compression failed!")
            return None
            
    except Exception as e:
        print(f"\n❌ Error during compression: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Test compression with logged videos")
    parser.add_argument("--list", action="store_true", help="List all available logged videos")
    parser.add_argument("--request-id", type=str, help="Request ID of video to test")
    parser.add_argument("--vmaf", type=float, default=89.0, help="Target VMAF (default: 89.0)")
    parser.add_argument("--codec", type=str, default="av1", help="Target codec (default: av1)")
    parser.add_argument("--mode", type=str, default="VBR", help="Codec mode (default: VBR)")
    parser.add_argument("--bitrate", type=float, default=20.0, help="Target bitrate in Mbps (default: 20.0)")
    
    args = parser.parse_args()
    
    # Get list of videos
    videos = list_logged_videos()
    
    if not videos:
        return
    
    # If --list, just display and exit
    if args.list:
        display_video_list(videos)
        return
    
    # If --request-id specified, test that video
    if args.request_id:
        video = next((v for v in videos if v['request_id'] == args.request_id), None)
        if not video:
            print(f"❌ Request ID not found: {args.request_id}")
            print("\nAvailable request IDs:")
            for v in videos:
                print(f"  - {v['request_id']}")
            return
        
        test_compression_with_logged_video(
            video['path'],
            vmaf=args.vmaf,
            codec=args.codec,
            mode=args.mode,
            bitrate=args.bitrate
        )
    else:
        # Interactive mode
        display_video_list(videos)
        print("Use --request-id <ID> to test a specific video")
        print("Use --list to just list videos")


if __name__ == "__main__":
    main()


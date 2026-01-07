#!/usr/bin/env python3
"""
Test CRF compression with a specific video URL.

This script sends a compression request to the local video-compressor service
using CRF mode (Constant Rate Factor - quality-based encoding).
"""

import httpx
import json
import sys
from datetime import datetime


def test_compression(
    video_url: str,
    vmaf_threshold: float = 89.0,
    target_codec: str = "hevc",
    codec_mode: str = "CRF",
    target_bitrate: float = 20.0
):
    """
    Test video compression with CRF mode.
    
    Args:
        video_url: URL of the video to compress
        vmaf_threshold: Target VMAF quality (85-95)
        target_codec: Codec to use (av1, hevc, h264, vp9)
        codec_mode: Encoding mode (CRF, VBR, CBR)
        target_bitrate: Target bitrate in Mbps (for VBR/CBR)
    """
    
    # Compression service endpoint
    url = "http://localhost:29116/compress-video"
    
    # Prepare request payload
    payload = {
        "payload_url": video_url,
        "vmaf_threshold": vmaf_threshold,
        "target_codec": target_codec,
        "codec_mode": codec_mode,
        "target_bitrate": target_bitrate,
        "max_duration": 3600,
        "output_dir": "./output"
    }
    
    print("=" * 80)
    print("🎬 VIDEO COMPRESSION TEST - CRF MODE")
    print("=" * 80)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Service: {url}")
    print(f"\n📋 Request Parameters:")
    print(f"   Video URL: {video_url[:80]}...")
    print(f"   VMAF Threshold: {vmaf_threshold}")
    print(f"   Target Codec: {target_codec}")
    print(f"   Codec Mode: {codec_mode}")
    print(f"   Target Bitrate: {target_bitrate} Mbps")
    print("=" * 80)
    print()
    
    try:
        # Send request with extended timeout (10 minutes for compression)
        print("🚀 Sending compression request...")
        timeout = httpx.Timeout(30.0, read=600.0)  # 30s connect, 10min read
        
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload)
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                
                print("\n" + "=" * 80)
                print("✅ COMPRESSION SUCCESSFUL")
                print("=" * 80)
                print(f"📁 Compressed Video: {result.get('compressed_video_name', 'N/A')}")
                print(f"🔗 Sharing Link: {result.get('sharing_link', 'N/A')[:80]}...")
                print(f"📊 Response: {json.dumps(result, indent=2)}")
                print("=" * 80)
                
                return True
                
            else:
                print("\n" + "=" * 80)
                print(f"❌ COMPRESSION FAILED - HTTP {response.status_code}")
                print("=" * 80)
                print(f"Response: {response.text}")
                print("=" * 80)
                
                return False
                
    except httpx.ConnectTimeout:
        print("\n" + "=" * 80)
        print("❌ CONNECTION TIMEOUT")
        print("=" * 80)
        print("Could not connect to the compression service.")
        print("Make sure the service is running: pm2 status video-compressor")
        print("=" * 80)
        return False
        
    except httpx.ReadTimeout:
        print("\n" + "=" * 80)
        print("❌ READ TIMEOUT")
        print("=" * 80)
        print("The compression took too long (>10 minutes).")
        print("Check the service logs: pm2 logs video-compressor")
        print("=" * 80)
        return False
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ ERROR: {type(e).__name__}")
        print("=" * 80)
        print(f"{e}")
        print("=" * 80)
        return False


if __name__ == "__main__":
    # Default test URL - using a publicly available test video
    # This is a 30-second Big Buck Bunny clip (open source test video)
    default_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

    # Allow custom URL from command line
    video_url = sys.argv[1] if len(sys.argv) > 1 else default_url

    print(f"💡 Using test video URL: {video_url[:80]}...")
    print(f"💡 To use a different URL, run: python test_crf_with_url.py <your_url>")
    print()
    
    # Run test
    success = test_compression(
        video_url=video_url,
        vmaf_threshold=89.0,
        target_codec="hevc",
        codec_mode="CRF",
        target_bitrate=20.0
    )
    
    sys.exit(0 if success else 1)


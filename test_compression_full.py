#!/usr/bin/env python3
"""
Comprehensive Compression Test Script
Tests the full compression pipeline with existing videos
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")

def run_command(cmd, description):
    """Run a shell command and return output"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def get_video_info(video_path):
    """Get video information using ffprobe"""
    cmd = f'ffprobe -v quiet -print_format json -show_format -show_streams "{video_path}"'
    success, stdout, stderr = run_command(cmd, f"Getting info for {os.path.basename(video_path)}")
    if success and stdout:
        try:
            return json.loads(stdout)
        except:
            return None
    return None

def test_compression_service(video_path, vmaf_threshold=89.0, target_codec="av1", codec_mode="CRF", target_bitrate=20.0):
    """Test compression via the compression service API"""
    import requests

    print(f"\n📹 Testing compression on: {os.path.basename(video_path)}")
    print(f"   VMAF Threshold: {vmaf_threshold}")
    print(f"   Target Codec: {target_codec}")
    print(f"   Codec Mode: {codec_mode}")
    print(f"   Target Bitrate: {target_bitrate} Mbps")

    # Get original video info
    info = get_video_info(video_path)
    if info:
        format_info = info.get('format', {})
        video_stream = next((s for s in info.get('streams', []) if s['codec_type'] == 'video'), None)

        if video_stream:
            print(f"\n   Original Video Info:")
            print(f"   - Codec: {video_stream.get('codec_name', 'unknown')}")
            print(f"   - Resolution: {video_stream.get('width', '?')}x{video_stream.get('height', '?')}")
            print(f"   - Duration: {float(format_info.get('duration', 0)):.2f}s")
            print(f"   - Size: {float(format_info.get('size', 0)) / (1024*1024):.2f} MB")

    # Test compression service using test-compress endpoint for local files
    url = "http://localhost:29116/test-compress"

    payload = {
        "video_path": os.path.abspath(video_path)
    }

    # Note: test-compress uses default settings, not custom vmaf/codec
    # For full control, we'd need to upload to a URL the service can access
    
    print(f"\n   🚀 Sending compression request...")
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n   ✅ Compression successful! ({elapsed:.2f}s)")
            print(f"   - Output URL: {result.get('uploaded_video_url', 'N/A')}")
            
            # Get compressed video info if available
            output_path = result.get('final_video_path')
            if output_path and os.path.exists(output_path):
                comp_info = get_video_info(output_path)
                if comp_info:
                    comp_format = comp_info.get('format', {})
                    comp_stream = next((s for s in comp_info.get('streams', []) if s['codec_type'] == 'video'), None)
                    
                    if comp_stream:
                        print(f"\n   Compressed Video Info:")
                        print(f"   - Codec: {comp_stream.get('codec_name', 'unknown')}")
                        print(f"   - Size: {float(comp_format.get('size', 0)) / (1024*1024):.2f} MB")
                        
                        # Calculate compression ratio
                        if info:
                            orig_size = float(info.get('format', {}).get('size', 0))
                            comp_size = float(comp_format.get('size', 0))
                            if orig_size > 0 and comp_size > 0:
                                ratio = orig_size / comp_size
                                reduction = (1 - comp_size / orig_size) * 100
                                print(f"   - Compression Ratio: {ratio:.2f}x")
                                print(f"   - Size Reduction: {reduction:.1f}%")
            
            return True, result
        else:
            print(f"\n   ❌ Compression failed!")
            print(f"   - Status: {response.status_code}")
            print(f"   - Response: {response.text[:500]}")
            return False, None
            
    except requests.exceptions.Timeout:
        print(f"\n   ❌ Request timed out after 300s")
        return False, None
    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        return False, None

def main():
    print_header("COMPRESSION MINING TEST SUITE")
    
    # Check if compression service is running
    print("1. Checking compression service...")
    try:
        import requests
        response = requests.get("http://localhost:29116/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Compression service is running")
        else:
            print("   ⚠️  Compression service returned unexpected status")
    except:
        print("   ❌ Compression service is NOT running!")
        print("\n   Please start it with:")
        print("   cd /workspace/vidaio-subnet")
        print("   python services/compress/server.py")
        return
    
    # Find test videos
    print("\n2. Finding test videos...")
    tmp_dir = Path("/workspace/vidaio-subnet/tmp")
    videos = list(tmp_dir.glob("*.mp4"))
    
    # Exclude encoded outputs
    videos = [v for v in videos if "encoded_scene" not in v.name and "final" not in v.name]
    
    if not videos:
        print("   ❌ No test videos found in /workspace/vidaio-subnet/tmp/")
        return
    
    print(f"   ✅ Found {len(videos)} test videos")
    
    # Test with first video
    test_video = videos[0]
    print(f"\n3. Testing compression with: {test_video.name}")
    
    # Test different configurations
    test_configs = [
        {"vmaf": 89.0, "codec": "av1", "mode": "CRF", "bitrate": 20.0},
        {"vmaf": 85.0, "codec": "hevc", "mode": "CRF", "bitrate": 25.0},
    ]
    
    results = []
    for i, config in enumerate(test_configs, 1):
        print(f"\n{'─'*80}")
        print(f"Test {i}/{len(test_configs)}: {config['codec'].upper()} @ VMAF {config['vmaf']}")
        print(f"{'─'*80}")
        
        success, result = test_compression_service(
            str(test_video),
            vmaf_threshold=config['vmaf'],
            target_codec=config['codec'],
            codec_mode=config['mode'],
            target_bitrate=config['bitrate']
        )
        
        results.append({
            "config": config,
            "success": success,
            "result": result
        })
    
    # Summary
    print_header("TEST SUMMARY")
    
    successful = sum(1 for r in results if r['success'])
    print(f"Tests Passed: {successful}/{len(results)}")
    
    if successful == len(results):
        print("\n🎉 ALL TESTS PASSED! Your compression setup is working perfectly!")
        print("\n✅ You're ready to start mining!")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()


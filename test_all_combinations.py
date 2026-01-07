#!/usr/bin/env python3
"""
Test script to test all combinations of codecs and modes with local videos.
Tests: AV1 & HEVC with CRF & VBR modes using videos from tmp folder.
"""

import requests
import json
import os
import glob
from datetime import datetime
from pathlib import Path
import time

# Configuration
SERVICE_URL = "http://localhost:29116/compress-video"
TMP_FOLDER = "tmp"
RESULTS_FILE = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# Test configurations
CODECS = ["av1", "hevc"]
MODES = ["CRF", "VBR"]
VMAF_THRESHOLD = 89.0
TARGET_BITRATE = 20.0  # Will be auto-calculated for VBR mode

def get_video_files(folder):
    """Get all video files from the specified folder."""
    video_extensions = ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.webm']
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(glob.glob(os.path.join(folder, ext)))
    
    return video_files

def upload_to_s3_and_get_url(video_path):
    """
    Upload video to S3 and get a public URL.
    For now, we'll use a placeholder - you'll need to implement actual S3 upload.
    """
    # TODO: Implement actual S3 upload
    # For testing, we'll use the Google sample video URL
    print(f"⚠️  Note: Using sample URL instead of uploading {video_path}")
    return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

def run_compression_test(video_url, video_name, codec, mode):
    """Run a single compression test."""
    print(f"\n{'='*80}")
    print(f"🎬 Testing: {video_name}")
    print(f"   Codec: {codec.upper()}, Mode: {mode}")
    print(f"{'='*80}")
    
    payload = {
        "payload_url": video_url,
        "vmaf_threshold": VMAF_THRESHOLD,
        "target_codec": codec,
        "codec_mode": mode,
        "target_bitrate": TARGET_BITRATE
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(SERVICE_URL, json=payload, timeout=600)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS ({elapsed_time:.1f}s)")
            print(f"   Status: {result.get('status')}")
            
            return {
                "success": True,
                "video_name": video_name,
                "codec": codec,
                "mode": mode,
                "elapsed_time": elapsed_time,
                "response": result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
            return {
                "success": False,
                "video_name": video_name,
                "codec": codec,
                "mode": mode,
                "elapsed_time": elapsed_time,
                "error": f"HTTP {response.status_code}: {response.text}",
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ EXCEPTION: {str(e)}")
        
        return {
            "success": False,
            "video_name": video_name,
            "codec": codec,
            "mode": mode,
            "elapsed_time": elapsed_time,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def main():
    print("="*80)
    print("🎬 VIDEO COMPRESSION TEST - ALL COMBINATIONS")
    print("="*80)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Service: {SERVICE_URL}")
    print(f"📁 Video folder: {TMP_FOLDER}")
    print(f"🎯 VMAF Threshold: {VMAF_THRESHOLD}")
    print(f"📊 Target Bitrate: {TARGET_BITRATE} Mbps")
    print("="*80)
    
    # Get video files
    video_files = get_video_files(TMP_FOLDER)
    
    if not video_files:
        print(f"❌ No video files found in {TMP_FOLDER}")
        return
    
    print(f"\n📹 Found {len(video_files)} video(s):")
    for i, video in enumerate(video_files, 1):
        print(f"   {i}. {os.path.basename(video)}")
    
    # Calculate total tests
    total_tests = len(video_files) * len(CODECS) * len(MODES)
    print(f"\n🧪 Total tests to run: {total_tests}")
    print(f"   Videos: {len(video_files)}")
    print(f"   Codecs: {len(CODECS)} ({', '.join(CODECS)})")
    print(f"   Modes: {len(MODES)} ({', '.join(MODES)})")
    
    # Confirm before starting
    response = input(f"\n⚠️  This will run {total_tests} compression tests. Continue? (y/n): ")
    if response.lower() != 'y':
        print("❌ Test cancelled.")
        return
    
    # Run tests
    results = []
    test_num = 0
    
    for video_path in video_files:
        video_name = os.path.basename(video_path)
        
        # Upload to S3 and get URL (or use existing URL)
        video_url = upload_to_s3_and_get_url(video_path)
        
        for codec in CODECS:
            for mode in MODES:
                test_num += 1
                print(f"\n{'='*80}")
                print(f"📊 Test {test_num}/{total_tests}")
                print(f"{'='*80}")
                
                result = run_compression_test(video_url, video_name, codec, mode)
                results.append(result)
                
                # Save results after each test
                with open(RESULTS_FILE, 'w') as f:
                    json.dump(results, f, indent=2)
                
                # Wait a bit between tests
                if test_num < total_tests:
                    print(f"\n⏳ Waiting 5 seconds before next test...")
                    time.sleep(5)
    
    # Print summary
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    print(f"📁 Results saved to: {RESULTS_FILE}")
    
    # Print detailed results
    print(f"\n{'='*80}")
    print("📋 DETAILED RESULTS")
    print(f"{'='*80}")
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['video_name']} | {result['codec'].upper()} | {result['mode']} | {result['elapsed_time']:.1f}s")
        if not result['success']:
            print(f"   Error: {result.get('error', 'Unknown error')}")
    
    print(f"\n{'='*80}")
    print(f"🎉 All tests completed!")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()


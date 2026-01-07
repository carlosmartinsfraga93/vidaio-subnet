#!/usr/bin/env python3
"""
Direct FFmpeg Compression Test
Tests hardware encoding without the compression service
"""

import os
import subprocess
import time
from pathlib import Path

def run_ffmpeg_test(input_video, output_video, codec="av1_nvenc", cq=30):
    """Test FFmpeg encoding directly"""
    
    print(f"\n{'='*80}")
    print(f"Testing {codec} encoding")
    print(f"{'='*80}\n")
    
    print(f"Input:  {input_video}")
    print(f"Output: {output_video}")
    print(f"Codec:  {codec}")
    print(f"CQ:     {cq}")
    
    # Build FFmpeg command
    if codec == "av1_nvenc":
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-c:v", "av1_nvenc",
            "-preset", "p6",
            "-cq", str(cq),
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            output_video
        ]
    elif codec == "hevc_nvenc":
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-c:v", "hevc_nvenc",
            "-preset", "p4",
            "-cq", str(cq),
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            output_video
        ]
    else:
        print(f"❌ Unsupported codec: {codec}")
        return False
    
    print(f"\n🚀 Starting encoding...")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0 and os.path.exists(output_video):
            # Get file sizes
            input_size = os.path.getsize(input_video) / (1024 * 1024)
            output_size = os.path.getsize(output_video) / (1024 * 1024)
            ratio = input_size / output_size if output_size > 0 else 0
            reduction = (1 - output_size / input_size) * 100 if input_size > 0 else 0
            
            print(f"\n✅ Encoding successful!")
            print(f"\n📊 Results:")
            print(f"   Time:        {elapsed:.2f}s")
            print(f"   Input size:  {input_size:.2f} MB")
            print(f"   Output size: {output_size:.2f} MB")
            print(f"   Ratio:       {ratio:.2f}x")
            print(f"   Reduction:   {reduction:.1f}%")
            
            # Get video info
            info_cmd = [
                "ffprobe", "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "stream=codec_name,width,height",
                "-of", "default=noprint_wrappers=1",
                output_video
            ]
            
            info_result = subprocess.run(info_cmd, capture_output=True, text=True)
            if info_result.returncode == 0:
                print(f"\n📹 Output video info:")
                for line in info_result.stdout.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        print(f"   {key}: {value}")
            
            return True
        else:
            print(f"\n❌ Encoding failed!")
            print(f"Return code: {result.returncode}")
            if result.stderr:
                print(f"\nError output:")
                print(result.stderr[-1000:])  # Last 1000 chars
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n❌ Encoding timed out after 300s")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("  DIRECT FFMPEG HARDWARE ENCODING TEST")
    print("="*80)
    
    # Find test video
    tmp_dir = Path("/workspace/vidaio-subnet/tmp")
    videos = [v for v in tmp_dir.glob("*.mp4") if "encoded" not in v.name and "final" not in v.name]
    
    if not videos:
        print("\n❌ No test videos found in /workspace/vidaio-subnet/tmp/")
        return
    
    test_video = str(videos[0])
    print(f"\n📹 Using test video: {os.path.basename(test_video)}")
    
    # Get video info
    info_cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,duration",
        "-show_entries", "format=size",
        "-of", "default=noprint_wrappers=1",
        test_video
    ]
    
    info_result = subprocess.run(info_cmd, capture_output=True, text=True)
    if info_result.returncode == 0:
        print(f"\n📊 Input video info:")
        for line in info_result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                print(f"   {key}: {value}")
    
    # Create output directory
    output_dir = Path("/workspace/vidaio-subnet/test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Test configurations
    tests = [
        {"codec": "av1_nvenc", "cq": 30, "name": "AV1 (CQ=30)"},
        {"codec": "hevc_nvenc", "cq": 28, "name": "HEVC (CQ=28)"},
    ]
    
    results = []
    for i, test in enumerate(tests, 1):
        output_file = output_dir / f"test_{test['codec']}_cq{test['cq']}.mp4"
        
        print(f"\n\n{'#'*80}")
        print(f"# Test {i}/{len(tests)}: {test['name']}")
        print(f"{'#'*80}")
        
        success = run_ffmpeg_test(
            test_video,
            str(output_file),
            codec=test['codec'],
            cq=test['cq']
        )
        
        results.append({"test": test['name'], "success": success})
        
        if not success:
            print(f"\n⚠️  Test failed, but continuing...")
    
    # Summary
    print("\n\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80 + "\n")
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status}  {result['test']}")
    
    passed = sum(1 for r in results if r['success'])
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All hardware encoders working perfectly!")
        print("✅ Your RTX 5090 is ready for compression mining!")
    else:
        print("\n⚠️  Some encoders failed. Check the errors above.")

if __name__ == "__main__":
    main()


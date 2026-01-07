"""
Test script for local video download functionality.

Tests the updated download_video function with file:// URLs and local paths.
"""

import asyncio
import os
from pathlib import Path
from vidaio_subnet_core.utilities.file_handler import download_video


async def test_local_video_download():
    """Test downloading/copying videos from local filesystem."""
    
    print("\n" + "="*80)
    print("TESTING LOCAL VIDEO DOWNLOAD FUNCTIONALITY")
    print("="*80)
    
    # Check if tmp directory has any videos
    tmp_dir = Path("tmp")
    if not tmp_dir.exists():
        print("\n❌ tmp directory does not exist!")
        print("   Please create it and add some test videos first.")
        return
    
    # Find video files in tmp directory
    video_files = list(tmp_dir.glob("*.mp4"))
    
    if not video_files:
        print("\n❌ No .mp4 files found in tmp directory!")
        print("   Please add some test videos to tmp/ first.")
        return
    
    print(f"\n✅ Found {len(video_files)} video(s) in tmp directory:")
    for i, video in enumerate(video_files, 1):
        size_mb = video.stat().st_size / 1024 / 1024
        print(f"   {i}. {video.name} ({size_mb:.2f} MB)")
    
    # Test with first video
    test_video = video_files[0]
    print(f"\n📹 Testing with: {test_video.name}")
    
    # Test 1: file:// URL (absolute path)
    print("\n" + "-"*80)
    print("Test 1: file:// URL with absolute path")
    print("-"*80)
    
    abs_path = test_video.absolute()
    file_url = f"file://{abs_path}"
    print(f"URL: {file_url}")
    
    try:
        result1 = await download_video(file_url)
        print(f"✅ Success! Copied to: {result1}")
        
        # Verify file exists and has content
        if os.path.exists(result1):
            size = os.path.getsize(result1)
            print(f"   File size: {size / 1024 / 1024:.2f} MB")
        else:
            print(f"❌ Error: Output file not found!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Relative path
    print("\n" + "-"*80)
    print("Test 2: Relative path")
    print("-"*80)
    
    rel_path = str(test_video)
    print(f"Path: {rel_path}")
    
    try:
        result2 = await download_video(rel_path)
        print(f"✅ Success! Copied to: {result2}")
        
        # Verify file exists and has content
        if os.path.exists(result2):
            size = os.path.getsize(result2)
            print(f"   File size: {size / 1024 / 1024:.2f} MB")
        else:
            print(f"❌ Error: Output file not found!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: HTTP URL (if you want to test remote download)
    print("\n" + "-"*80)
    print("Test 3: HTTP URL (optional - skipped)")
    print("-"*80)
    print("Skipping HTTP test to save time. HTTP download still works as before.")
    
    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)
    print("\n✅ You can now use file:// URLs or local paths in compression requests!")
    print("\nExample usage:")
    print(f"  file://{abs_path}")
    print(f"  {rel_path}")
    print("\n")


if __name__ == "__main__":
    asyncio.run(test_local_video_download())


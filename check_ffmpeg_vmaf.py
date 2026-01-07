#!/usr/bin/env python3
"""
Check if FFmpeg has libvmaf support.
"""
import subprocess
import sys

def check_ffmpeg_vmaf():
    """Check if FFmpeg has libvmaf filter support."""
    print("Checking FFmpeg for libvmaf support...")
    print("="*60)
    
    # Check FFmpeg version
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg found: {version_line}")
        else:
            print("❌ FFmpeg not found or error running ffmpeg -version")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg not found in PATH")
        return False
    except Exception as e:
        print(f"❌ Error checking FFmpeg: {e}")
        return False
    
    # Check for libvmaf filter
    print("\nChecking for libvmaf filter...")
    try:
        result = subprocess.run(
            ['ffmpeg', '-filters'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if 'libvmaf' in result.stdout:
            print("✅ libvmaf filter is available!")
            print("\nYou can use VMAF calculation.")
            return True
        else:
            print("❌ libvmaf filter NOT found in FFmpeg")
            print("\nFFmpeg needs to be compiled with libvmaf support.")
            print("\nTo install FFmpeg with libvmaf:")
            print("1. Install libvmaf development libraries")
            print("2. Recompile FFmpeg with --enable-libvmaf")
            print("3. Or use a pre-built FFmpeg with libvmaf support")
            return False
            
    except Exception as e:
        print(f"❌ Error checking filters: {e}")
        return False

if __name__ == "__main__":
    has_vmaf = check_ffmpeg_vmaf()
    sys.exit(0 if has_vmaf else 1)


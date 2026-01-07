#!/usr/bin/env python3
"""
Check if FFmpeg has libvmaf support and can calculate VMAF scores.
"""

import subprocess
import sys

def check_ffmpeg_version():
    """Check FFmpeg version."""
    print("="*80)
    print("1. Checking FFmpeg Version")
    print("="*80)
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        print(result.stdout.split('\n')[0])  # First line has version
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_libvmaf_filter():
    """Check if FFmpeg has libvmaf filter."""
    print("\n" + "="*80)
    print("2. Checking for libvmaf Filter")
    print("="*80)
    try:
        result = subprocess.run(['ffmpeg', '-filters'], capture_output=True, text=True, timeout=5)
        
        # Search for libvmaf in filters
        for line in result.stdout.split('\n'):
            if 'libvmaf' in line.lower():
                print(f"✅ Found: {line.strip()}")
                return True
        
        print("❌ libvmaf filter NOT found in FFmpeg")
        print("\nFFmpeg was not compiled with --enable-libvmaf")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_vmaf_model_paths():
    """Check common VMAF model file locations."""
    print("\n" + "="*80)
    print("3. Checking for VMAF Model Files")
    print("="*80)
    
    import os
    common_paths = [
        '/usr/local/share/model/',
        '/usr/share/model/',
        '/opt/vmaf/model/',
        './models/',
        '/usr/local/share/vmaf/',
        '/usr/share/vmaf/'
    ]
    
    found_models = []
    for path in common_paths:
        if os.path.exists(path):
            print(f"✅ Directory exists: {path}")
            try:
                files = os.listdir(path)
                vmaf_files = [f for f in files if 'vmaf' in f.lower()]
                if vmaf_files:
                    print(f"   Found models: {vmaf_files}")
                    found_models.extend([os.path.join(path, f) for f in vmaf_files])
            except Exception as e:
                print(f"   ⚠️ Cannot list directory: {e}")
        else:
            print(f"❌ Directory not found: {path}")
    
    if found_models:
        print(f"\n✅ Found {len(found_models)} VMAF model file(s)")
        return True
    else:
        print("\n⚠️ No VMAF model files found in common locations")
        print("   libvmaf will try to use its built-in default model")
        return False

def test_vmaf_calculation():
    """Test if VMAF calculation actually works."""
    print("\n" + "="*80)
    print("4. Testing VMAF Calculation (Quick Test)")
    print("="*80)
    
    # Create a simple test: compare a video with itself (should get VMAF ~100)
    print("This test requires a sample video file.")
    print("Skipping actual VMAF calculation test.")
    print("To test manually, run:")
    print("  ffmpeg -i input.mp4 -i output.mp4 \\")
    print("    -filter_complex '[0:v]setpts=PTS-STARTPTS[ref];[1:v]setpts=PTS-STARTPTS[dist];[ref][dist]libvmaf' \\")
    print("    -f null -")
    return None

def main():
    print("🔍 FFmpeg libvmaf Support Diagnostic Tool")
    print("="*80)
    
    results = {
        'ffmpeg_installed': check_ffmpeg_version(),
        'libvmaf_filter': check_libvmaf_filter(),
        'vmaf_models': check_vmaf_model_paths(),
    }
    
    test_vmaf_calculation()
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    if results['ffmpeg_installed']:
        print("✅ FFmpeg is installed")
    else:
        print("❌ FFmpeg is NOT installed")
    
    if results['libvmaf_filter']:
        print("✅ libvmaf filter is available")
    else:
        print("❌ libvmaf filter is NOT available")
        print("   → FFmpeg needs to be recompiled with --enable-libvmaf")
    
    if results['vmaf_models']:
        print("✅ VMAF model files found")
    else:
        print("⚠️ VMAF model files not found (will use built-in default)")
    
    print("\n" + "="*80)
    print("🎯 RECOMMENDATION")
    print("="*80)
    
    if not results['libvmaf_filter']:
        print("❌ CRITICAL: FFmpeg does not have libvmaf support!")
        print("\nYou need to:")
        print("1. Install libvmaf library")
        print("2. Recompile FFmpeg with --enable-libvmaf flag")
        print("\nOr use a pre-built FFmpeg with libvmaf support:")
        print("  - Docker: linuxserver/ffmpeg")
        print("  - Static builds: https://johnvansickle.com/ffmpeg/")
        return 1
    
    if results['libvmaf_filter'] and not results['vmaf_models']:
        print("⚠️ WARNING: libvmaf is available but no model files found")
        print("\nThis should still work using libvmaf's built-in default model.")
        print("If VMAF calculation fails, install VMAF model files:")
        print("  git clone https://github.com/Netflix/vmaf.git")
        print("  cp vmaf/model/* /usr/local/share/model/")
        return 0
    
    if all(results.values()):
        print("✅ Everything looks good!")
        print("\nFFmpeg has libvmaf support and model files are available.")
        return 0
    
    return 1

if __name__ == "__main__":
    sys.exit(main())


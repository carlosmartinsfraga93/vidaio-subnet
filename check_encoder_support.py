#!/usr/bin/env python3
"""
Check what video encoders are available in FFmpeg.
This helps diagnose why av1_nvenc is not working.
"""
import subprocess
import sys

def run_command(cmd):
    """Run a command and return output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def main():
    print("="*80)
    print("FFMPEG ENCODER SUPPORT CHECK")
    print("="*80)
    
    # Check FFmpeg version
    print("\n1. FFmpeg Version:")
    print("-" * 40)
    code, out, err = run_command(['ffmpeg', '-version'])
    if code == 0:
        print(out.split('\n')[0])
    else:
        print(f"❌ FFmpeg not found: {err}")
        return
    
    # Check for NVIDIA GPU
    print("\n2. NVIDIA GPU Check:")
    print("-" * 40)
    code, out, err = run_command(['nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'])
    if code == 0:
        print(f"✅ GPU Found: {out.strip()}")
    else:
        print(f"❌ No NVIDIA GPU detected or nvidia-smi not available")
    
    # Check available encoders
    print("\n3. Available Video Encoders:")
    print("-" * 40)
    code, out, err = run_command(['ffmpeg', '-encoders'])
    
    if code != 0:
        print(f"❌ Failed to get encoders: {err}")
        return
    
    # Parse encoders
    encoders = {
        'av1_nvenc': '❌ NOT AVAILABLE',
        'hevc_nvenc': '❌ NOT AVAILABLE',
        'h264_nvenc': '❌ NOT AVAILABLE',
        'libsvtav1': '❌ NOT AVAILABLE',
        'libaom-av1': '❌ NOT AVAILABLE',
        'libx264': '❌ NOT AVAILABLE',
        'libx265': '❌ NOT AVAILABLE',
        'libvpx-vp9': '❌ NOT AVAILABLE',
    }
    
    for line in out.split('\n'):
        for encoder in encoders.keys():
            if encoder in line:
                encoders[encoder] = '✅ AVAILABLE'
    
    print("\nHardware Encoders (NVENC - requires NVIDIA GPU):")
    print(f"  av1_nvenc:  {encoders['av1_nvenc']}")
    print(f"  hevc_nvenc: {encoders['hevc_nvenc']}")
    print(f"  h264_nvenc: {encoders['h264_nvenc']}")
    
    print("\nSoftware Encoders (CPU-based):")
    print(f"  libsvtav1:  {encoders['libsvtav1']}")
    print(f"  libaom-av1: {encoders['libaom-av1']}")
    print(f"  libx264:    {encoders['libx264']}")
    print(f"  libx265:    {encoders['libx265']}")
    print(f"  libvpx-vp9: {encoders['libvpx-vp9']}")
    
    # Check for libvmaf
    print("\n4. VMAF Support:")
    print("-" * 40)
    code, out, err = run_command(['ffmpeg', '-filters'])
    if 'libvmaf' in out:
        print("✅ libvmaf filter AVAILABLE")
    else:
        print("❌ libvmaf filter NOT AVAILABLE")
    
    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS:")
    print("="*80)
    
    if encoders['av1_nvenc'] == '❌ NOT AVAILABLE':
        print("\n⚠️  av1_nvenc is NOT available. Possible reasons:")
        print("   1. FFmpeg was not compiled with --enable-nvenc")
        print("   2. NVIDIA GPU drivers are not installed")
        print("   3. GPU does not support AV1 encoding (requires RTX 40-series or newer)")
        print("\n💡 Solutions:")
        if encoders['libsvtav1'] == '✅ AVAILABLE':
            print("   ✅ Use libsvtav1 (CPU-based AV1 encoder) - AVAILABLE")
            print("      Change codec from 'av1' to 'libsvtav1' in test script")
        elif encoders['libx264'] == '✅ AVAILABLE':
            print("   ✅ Use libx264 (H.264 encoder) - AVAILABLE")
            print("      Change codec from 'av1' to 'h264' in test script")
        else:
            print("   ❌ Need to rebuild FFmpeg with encoder support")
    else:
        print("\n✅ av1_nvenc is available - hardware encoding should work!")
    
    if 'libvmaf' not in out:
        print("\n⚠️  libvmaf is NOT available")
        print("   This is needed for VMAF quality scoring")
        print("   FFmpeg needs to be rebuilt with --enable-libvmaf")

if __name__ == "__main__":
    main()


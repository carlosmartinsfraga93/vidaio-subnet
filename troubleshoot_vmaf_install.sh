#!/bin/bash
# Troubleshoot libvmaf installation

echo "=========================================="
echo "Troubleshooting libvmaf Installation"
echo "=========================================="

# Check which FFmpeg is being used
echo ""
echo "1. Checking which FFmpeg is being used:"
which ffmpeg
ffmpeg -version | head -n 1

# Check if libvmaf libraries are installed
echo ""
echo "2. Checking for libvmaf libraries:"
if [ -f /usr/local/lib/libvmaf.so ] || [ -f /usr/lib/libvmaf.so ] || [ -f /usr/lib/x86_64-linux-gnu/libvmaf.so ]; then
    echo "✅ Found libvmaf library files:"
    find /usr/local/lib /usr/lib /usr/lib/x86_64-linux-gnu -name "*vmaf*" 2>/dev/null | head -5
else
    echo "❌ libvmaf library files not found in standard locations"
    echo "   Searching in all locations..."
    find /usr -name "*vmaf*" 2>/dev/null | head -10
fi

# Check pkg-config
echo ""
echo "3. Checking pkg-config for libvmaf:"
if pkg-config --exists libvmaf; then
    echo "✅ pkg-config found libvmaf:"
    pkg-config --modversion libvmaf
    pkg-config --cflags libvmaf
    pkg-config --libs libvmaf
else
    echo "❌ pkg-config cannot find libvmaf"
    echo "   This means FFmpeg configure couldn't find it either"
fi

# Check library path
echo ""
echo "4. Checking library search path:"
echo "   LD_LIBRARY_PATH: ${LD_LIBRARY_PATH:-not set}"
echo "   /etc/ld.so.conf.d entries:"
ls -la /etc/ld.so.conf.d/ 2>/dev/null | head -5

# Check if new FFmpeg was installed
echo ""
echo "5. Checking FFmpeg installation locations:"
echo "   /usr/local/bin/ffmpeg:"
if [ -f /usr/local/bin/ffmpeg ]; then
    /usr/local/bin/ffmpeg -version | head -n 1
    echo "   Checking for libvmaf:"
    /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -i vmaf || echo "   ❌ No libvmaf"
else
    echo "   ❌ /usr/local/bin/ffmpeg not found"
fi

echo ""
echo "   System ffmpeg:"
ffmpeg -filters 2>/dev/null | grep -i vmaf || echo "   ❌ No libvmaf"

# Check FFmpeg configure log
echo ""
echo "6. Checking FFmpeg build configuration:"
if [ -f ffmpeg/config.log ]; then
    echo "   Checking config.log for libvmaf:"
    grep -i "libvmaf" ffmpeg/config.log | tail -5
    echo ""
    echo "   Checking if libvmaf was enabled:"
    grep -i "enable.*vmaf" ffmpeg/config.log | tail -3
else
    echo "   ⚠️  config.log not found (build may have been cleaned)"
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="


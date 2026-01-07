#!/bin/bash
# Fix libvmaf detection issues after FFmpeg build

set -e

echo "🔧 Fixing libvmaf detection..."
echo "================================"
echo ""

# Check if libvmaf is installed
echo "1. Checking if libvmaf library exists..."
if [ -f "/usr/local/lib/libvmaf.so" ] || [ -f "/usr/lib/x86_64-linux-gnu/libvmaf.so" ]; then
    echo "   ✅ libvmaf library found"
else
    echo "   ❌ libvmaf library not found in standard locations"
    echo "   Searching for libvmaf..."
    find /usr -name "libvmaf.so*" 2>/dev/null | head -5
fi

# Update library cache
echo ""
echo "2. Updating library cache..."
ldconfig

# Check pkg-config
echo ""
echo "3. Checking pkg-config for libvmaf..."
if pkg-config --exists libvmaf; then
    echo "   ✅ pkg-config found libvmaf"
    pkg-config --modversion libvmaf
    pkg-config --libs libvmaf
    pkg-config --cflags libvmaf
else
    echo "   ⚠️  pkg-config doesn't find libvmaf"
    echo "   This might be the issue - libvmaf needs a .pc file"
fi

# Check FFmpeg configuration
echo ""
echo "4. Checking FFmpeg configuration..."
if [ -f "/usr/local/bin/ffmpeg" ]; then
    echo "   FFmpeg location: /usr/local/bin/ffmpeg"
    /usr/local/bin/ffmpeg -version | head -3
    echo ""
    echo "   Checking for libvmaf in FFmpeg filters:"
    /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -i vmaf || echo "   ❌ libvmaf not found"
    echo ""
    echo "   Checking FFmpeg configuration:"
    /usr/local/bin/ffmpeg -buildconf 2>/dev/null | grep -i vmaf || echo "   ❌ libvmaf not in build config"
else
    echo "   ⚠️  FFmpeg not found at /usr/local/bin/ffmpeg"
    which ffmpeg
fi

# Check if we need to rebuild with explicit paths
echo ""
echo "5. Checking library paths..."
echo "   LD_LIBRARY_PATH: ${LD_LIBRARY_PATH:-not set}"
echo "   /etc/ld.so.conf.d/ contents:"
ls -la /etc/ld.so.conf.d/ 2>/dev/null | head -5

echo ""
echo "=========================================="
echo "Diagnosis complete!"
echo ""
echo "If libvmaf is not detected, possible fixes:"
echo ""
echo "Option 1: Rebuild FFmpeg with explicit libvmaf paths"
echo "  Run: ./rebuild_ffmpeg_with_explicit_vmaf.sh"
echo ""
echo "Option 2: Check if libvmaf is in a non-standard location"
echo "  Run: find /usr -name 'libvmaf.so*'"
echo ""
echo "Option 3: Install libvmaf via package manager (if available)"
echo "  apt-get install libvmaf-dev (may not be available)"
echo ""


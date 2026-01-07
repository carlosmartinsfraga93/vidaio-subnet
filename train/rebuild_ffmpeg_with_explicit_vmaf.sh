#!/bin/bash
# Rebuild FFmpeg with explicit libvmaf paths

set -e

echo "🔨 Rebuilding FFmpeg with explicit libvmaf configuration"
echo "=========================================================="
echo ""

# Find libvmaf installation
echo "1. Locating libvmaf installation..."
VMAF_LIB_DIR=""
VMAF_INCLUDE_DIR=""

# Check common locations
for dir in /usr/local/lib /usr/lib/x86_64-linux-gnu /usr/lib; do
    if [ -f "$dir/libvmaf.so" ] || [ -f "$dir/libvmaf.a" ]; then
        VMAF_LIB_DIR="$dir"
        echo "   ✅ Found libvmaf library in: $dir"
        break
    fi
done

for dir in /usr/local/include /usr/include; do
    if [ -d "$dir/libvmaf" ] || [ -f "$dir/libvmaf.h" ]; then
        VMAF_INCLUDE_DIR="$dir"
        echo "   ✅ Found libvmaf headers in: $dir"
        break
    fi
done

if [ -z "$VMAF_LIB_DIR" ]; then
    echo "   ❌ libvmaf library not found. Building VMAF first..."
    cd /tmp
    if [ ! -d "vmaf" ]; then
        git clone https://github.com/Netflix/vmaf.git
    fi
    cd vmaf/libvmaf
    meson setup build --buildtype release -Denable_avx512=true
    ninja -vC build
    ninja -vC build install
    ldconfig
    
    VMAF_LIB_DIR="/usr/local/lib"
    VMAF_INCLUDE_DIR="/usr/local/include"
fi

# Set PKG_CONFIG_PATH if needed
export PKG_CONFIG_PATH="${PKG_CONFIG_PATH}:/usr/local/lib/pkgconfig:/usr/lib/pkgconfig"

# Build FFmpeg with explicit paths
echo ""
echo "2. Rebuilding FFmpeg with explicit libvmaf paths..."
cd /tmp
if [ -d "ffmpeg" ]; then
    cd ffmpeg
    make distclean 2>/dev/null || true
else
    git clone https://git.ffmpeg.org/ffmpeg.git
    cd ffmpeg
fi

# Configure with explicit libvmaf paths
echo "   Configuring FFmpeg..."
./configure \
    --enable-gpl \
    --enable-version3 \
    --enable-nonfree \
    --enable-libvmaf \
    --extra-cflags="-I${VMAF_INCLUDE_DIR}" \
    --extra-ldflags="-L${VMAF_LIB_DIR} -Wl,-rpath,${VMAF_LIB_DIR}" \
    --enable-libx264 \
    --enable-libx265 \
    --enable-libvpx \
    --enable-libfdk-aac \
    --enable-libmp3lame \
    --enable-libopus \
    --enable-libvorbis \
    --enable-libtheora \
    --enable-libwebp \
    --enable-libfreetype \
    --enable-libfontconfig \
    --enable-libfribidi \
    --enable-libass \
    --enable-openssl \
    --enable-shared \
    --enable-pic \
    --prefix=/usr/local

echo ""
echo "   Building FFmpeg (this may take 20-40 minutes)..."
make -j$(nproc)

echo ""
echo "   Installing FFmpeg..."
make install
ldconfig

# Verify
echo ""
echo "3. Verifying installation..."
if /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
    echo "   ✅ SUCCESS! libvmaf filter is now available!"
    echo ""
    echo "   FFmpeg version:"
    /usr/local/bin/ffmpeg -version | head -1
    echo ""
    echo "   libvmaf filter:"
    /usr/local/bin/ffmpeg -filters 2>/dev/null | grep libvmaf
else
    echo "   ❌ Still not found. Checking build log..."
    echo ""
    echo "   FFmpeg configuration:"
    /usr/local/bin/ffmpeg -buildconf 2>/dev/null | head -20
    echo ""
    echo "   Available filters (searching for vmaf):"
    /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -i vmaf || echo "   No vmaf-related filters found"
    echo ""
    echo "   Try running: ./fix_libvmaf_detection.sh for more diagnostics"
fi


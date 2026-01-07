#!/bin/bash
# Add libsvtav1 encoder to existing FFmpeg build
# This provides a software AV1 fallback when av1_nvenc isn't supported

set -e

echo "================================================================================"
echo "Adding libsvtav1 Support to FFmpeg"
echo "================================================================================"
echo ""
echo "This will:"
echo "  1. Build and install SVT-AV1 library"
echo "  2. Rebuild FFmpeg with libsvtav1 support (keeps NVENC + libvmaf)"
echo "  3. Provide software AV1 encoding fallback"
echo ""
echo "⚠️  This will take 20-40 minutes"
echo ""

# Install SVT-AV1 dependencies
echo "1. Installing SVT-AV1 build dependencies..."
echo "----------------------------------------"
sudo apt-get update
sudo apt-get install -y cmake nasm meson ninja-build

# Build SVT-AV1
echo ""
echo "2. Building SVT-AV1 library..."
echo "----------------------------------------"
cd /tmp
if [ -d "SVT-AV1" ]; then
    rm -rf SVT-AV1
fi

git clone https://gitlab.com/AOMediaCodec/SVT-AV1.git
cd SVT-AV1
cd Build
cmake .. -G"Unix Makefiles" -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install
sudo ldconfig

echo "✅ SVT-AV1 library installed"

# Rebuild FFmpeg with libsvtav1
echo ""
echo "3. Rebuilding FFmpeg with libsvtav1 + NVENC + libvmaf..."
echo "----------------------------------------"

FFMPEG_DIR="/tmp/ffmpeg"
cd /tmp

if [ -d "$FFMPEG_DIR" ]; then
    echo "Removing old FFmpeg build directory..."
    rm -rf "$FFMPEG_DIR"
fi

echo "Cloning FFmpeg..."
git clone https://git.ffmpeg.org/ffmpeg.git "$FFMPEG_DIR"
cd "$FFMPEG_DIR"

# Set paths
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/lib:$LD_LIBRARY_PATH
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH

echo ""
echo "Configuring FFmpeg with NVENC + libvmaf + libsvtav1..."
./configure \
    --enable-gpl \
    --enable-version3 \
    --enable-nonfree \
    --enable-cuda-nvcc \
    --enable-nvenc \
    --enable-libvmaf \
    --enable-libsvtav1 \
    --enable-libx264 \
    --enable-libx265 \
    --enable-libvpx \
    --enable-libfdk-aac \
    --enable-libmp3lame \
    --enable-libopus \
    --enable-shared \
    --enable-pic \
    --prefix=/usr/local \
    --extra-cflags="-I/usr/local/cuda/include -I/usr/local/include" \
    --extra-ldflags="-L/usr/local/cuda/lib64 -L/usr/local/lib"

echo ""
echo "Building FFmpeg (this will take 20-40 minutes)..."
make -j$(nproc)

echo ""
echo "Installing FFmpeg..."
sudo make install
sudo ldconfig

# Verify installation
echo ""
echo "================================================================================"
echo "Verifying Installation"
echo "================================================================================"

echo ""
echo "Checking encoders:"
ENCODERS=$(/usr/local/bin/ffmpeg -encoders 2>/dev/null)

if echo "$ENCODERS" | grep -q "libsvtav1"; then
    echo "   ✅ libsvtav1 is available"
else
    echo "   ❌ libsvtav1 NOT available"
fi

if echo "$ENCODERS" | grep -q "av1_nvenc"; then
    echo "   ✅ av1_nvenc is available"
else
    echo "   ❌ av1_nvenc NOT available (requires driver 570+)"
fi

if /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
    echo "   ✅ libvmaf filter is available"
else
    echo "   ❌ libvmaf filter NOT available"
fi

echo ""
echo "================================================================================"
echo "Installation Complete!"
echo "================================================================================"
echo ""
echo "FFmpeg version:"
/usr/local/bin/ffmpeg -version | head -1
echo ""
echo "✅ You now have software AV1 encoding fallback (libsvtav1)!"
echo ""
echo "Encoding priority:"
echo "  1. av1_nvenc (hardware, fastest) - if driver 570+ available"
echo "  2. libsvtav1 (software, slower) - automatic fallback"
echo ""
echo "Next step: Test compression with: python quick_test_vmaf_fix.py"
echo ""


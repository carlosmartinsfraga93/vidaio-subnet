#!/bin/bash
# Fix libvmaf installation issues

set -e

echo "=========================================="
echo "Fixing libvmaf Installation"
echo "=========================================="

WORK_DIR=$(pwd)
VMAF_DIR="$WORK_DIR/libvmaf"

# Step 1: Ensure libvmaf is properly installed
echo ""
echo "Step 1: Installing/Reinstalling libvmaf"
echo "----------------------------------------"

if [ ! -d "$VMAF_DIR" ]; then
    echo "Cloning libvmaf..."
    git clone https://github.com/Netflix/vmaf.git "$VMAF_DIR"
fi

cd "$VMAF_DIR"
git pull

echo "Building libvmaf..."
cd libvmaf

# Clean previous build
rm -rf build

# Build with proper paths
meson setup build --buildtype release --prefix=/usr/local
ninja -C build
sudo ninja -C build install

# Update library cache
sudo ldconfig

echo "✅ libvmaf installed"

# Step 2: Verify pkg-config can find it
echo ""
echo "Step 2: Verifying pkg-config"
echo "----------------------------------------"

if pkg-config --exists libvmaf; then
    echo "✅ pkg-config found libvmaf"
    pkg-config --modversion libvmaf
else
    echo "❌ pkg-config still cannot find libvmaf"
    echo "   Creating pkg-config file manually..."
    
    # Create pkg-config file
    sudo mkdir -p /usr/local/lib/pkgconfig
    cat <<EOF | sudo tee /usr/local/lib/pkgconfig/libvmaf.pc
prefix=/usr/local
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include

Name: libvmaf
Description: VMAF library
Version: 2.3.1
Libs: -L\${libdir} -lvmaf
Cflags: -I\${includedir}
EOF
    
    export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
    echo "✅ Created pkg-config file"
fi

# Step 3: Rebuild FFmpeg with explicit paths
echo ""
echo "Step 3: Rebuilding FFmpeg with libvmaf"
echo "----------------------------------------"

FFMPEG_DIR="$WORK_DIR/ffmpeg"
cd "$WORK_DIR"

if [ ! -d "$FFMPEG_DIR" ]; then
    echo "Cloning FFmpeg..."
    git clone https://git.ffmpeg.org/ffmpeg.git "$FFMPEG_DIR"
fi

cd "$FFMPEG_DIR"
git pull

# Clean previous build
make distclean 2>/dev/null || true

# Configure with explicit libvmaf paths
echo "Configuring FFmpeg..."
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

./configure \
    --enable-libvmaf \
    --enable-libx264 \
    --enable-libx265 \
    --enable-libvpx \
    --enable-libfdk-aac \
    --enable-libmp3lame \
    --enable-libopus \
    --enable-nonfree \
    --enable-gpl \
    --enable-version3 \
    --prefix=/usr/local \
    --extra-cflags="-I/usr/local/include" \
    --extra-ldflags="-L/usr/local/lib"

# Check if libvmaf was detected
echo ""
echo "Checking configure output for libvmaf:"
if grep -q "libvmaf.*yes" config.log; then
    echo "✅ libvmaf was detected by configure"
else
    echo "❌ libvmaf was NOT detected by configure"
    echo "   Showing relevant config.log lines:"
    grep -i "vmaf" config.log | tail -10
    exit 1
fi

# Build
echo ""
echo "Building FFmpeg (this may take 20-30 minutes)..."
make -j$(nproc)

# Install
echo ""
echo "Installing FFmpeg..."
sudo make install
sudo ldconfig

# Verify
echo ""
echo "=========================================="
echo "Verifying Installation"
echo "=========================================="

# Use the newly installed FFmpeg
export PATH=/usr/local/bin:$PATH

if /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
    echo "✅ SUCCESS! FFmpeg with libvmaf installed!"
    echo ""
    echo "FFmpeg version:"
    /usr/local/bin/ffmpeg -version | head -n 1
    echo ""
    echo "libvmaf filter:"
    /usr/local/bin/ffmpeg -filters 2>/dev/null | grep libvmaf
    echo ""
    echo "⚠️  Note: Make sure /usr/local/bin is in your PATH"
    echo "   Current PATH: $PATH"
    echo ""
    echo "   To use the new FFmpeg, either:"
    echo "   1. Add to PATH: export PATH=/usr/local/bin:\$PATH"
    echo "   2. Or create alias: alias ffmpeg=/usr/local/bin/ffmpeg"
else
    echo "❌ Installation failed. libvmaf filter still not found."
    echo "   Please check the build logs above."
    exit 1
fi


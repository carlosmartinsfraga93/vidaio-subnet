#!/bin/bash
# Install FFmpeg with libvmaf support - Multiple methods

set -e

echo "🔧 Installing FFmpeg with libvmaf support"
echo "=========================================="
echo ""

# Method 1: Check if conda is available (easiest)
if command -v conda &> /dev/null; then
    echo "✅ Conda found! This is the easiest method."
    echo ""
    echo "Installing FFmpeg with libvmaf via conda..."
    conda install -c conda-forge ffmpeg -y
    echo ""
    echo "Verifying installation..."
    if ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
        echo "✅ Success! FFmpeg now has libvmaf support!"
        exit 0
    else
        echo "⚠️  Conda FFmpeg doesn't have libvmaf, trying other methods..."
    fi
fi

# Method 2: Try snap (if available)
if command -v snap &> /dev/null; then
    echo "📦 Trying snap package..."
    snap install ffmpeg 2>/dev/null || true
    if ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
        echo "✅ Success! FFmpeg now has libvmaf support!"
        exit 0
    fi
fi

# Method 3: Build from source (most reliable but time-consuming)
echo ""
echo "⚠️  Pre-built packages don't have libvmaf support."
echo ""
echo "You have two options:"
echo ""
echo "Option A: Build FFmpeg from source with libvmaf (30-60 minutes)"
echo "  - Most reliable"
echo "  - Full control over features"
echo "  - Run: ./build_ffmpeg_with_vmaf.sh"
echo ""
echo "Option B: Continue without libvmaf (not recommended for training)"
echo "  - Training will use estimated VMAF scores"
echo "  - Models will be less accurate"
echo "  - You can continue training now"
echo ""
read -p "Build FFmpeg from source? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "⚠️  Continuing without libvmaf support."
    echo "   Training will use estimated VMAF scores."
    exit 0
fi

# Build from source
echo ""
echo "🔨 Building FFmpeg from source with libvmaf..."
echo "This will take 30-60 minutes..."
echo ""

# Install build dependencies
echo "Installing build dependencies..."
apt-get update -qq
apt-get install -y \
    build-essential \
    nasm \
    yasm \
    cmake \
    git \
    pkg-config \
    libx264-dev \
    libx265-dev \
    libvpx-dev \
    libfdk-aac-dev \
    libmp3lame-dev \
    libopus-dev \
    libvorbis-dev \
    libtheora-dev \
    libwebp-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libfribidi-dev \
    libass-dev \
    libssl-dev \
    zlib1g-dev \
    ninja-build \
    meson \
    doxygen \
    xxd

# Build VMAF first
echo ""
echo "Building VMAF library..."
cd /tmp
if [ -d "vmaf" ]; then
    rm -rf vmaf
fi
git clone https://github.com/Netflix/vmaf.git
cd vmaf/libvmaf
meson setup build --buildtype release -Denable_avx512=true
ninja -vC build
ninja -vC build install
ldconfig

# Build FFmpeg
echo ""
echo "Building FFmpeg..."
cd /tmp
if [ -d "ffmpeg" ]; then
    rm -rf ffmpeg
fi
git clone https://git.ffmpeg.org/ffmpeg.git
cd ffmpeg

./configure \
    --enable-gpl \
    --enable-version3 \
    --enable-nonfree \
    --enable-libvmaf \
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

make -j$(nproc)
make install
ldconfig

# Verify
echo ""
echo "Verifying installation..."
if ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
    echo "✅ Success! FFmpeg now has libvmaf support!"
    ffmpeg -version | head -1
else
    echo "❌ Installation failed. libvmaf filter not found."
    exit 1
fi


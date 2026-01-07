#!/bin/bash
# Build FFmpeg from source with libvmaf support
# This takes 30-60 minutes

set -e

echo "🔨 Building FFmpeg with libvmaf support from source"
echo "==================================================="
echo "⚠️  This will take 30-60 minutes"
echo ""

# Check if already installed
if ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
    echo "✅ FFmpeg already has libvmaf support!"
    exit 0
fi

# Install build dependencies
echo "📦 Installing build dependencies..."
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

# Build VMAF library
echo ""
echo "🔨 Building VMAF library..."
cd /tmp
if [ -d "vmaf" ]; then
    echo "   Removing existing vmaf directory..."
    rm -rf vmaf
fi

echo "   Cloning VMAF repository..."
git clone https://github.com/Netflix/vmaf.git
cd vmaf/libvmaf

echo "   Configuring VMAF build..."
meson setup build --buildtype release -Denable_avx512=true

echo "   Building VMAF (this may take 10-15 minutes)..."
ninja -vC build

echo "   Installing VMAF..."
ninja -vC build install
ldconfig

echo "✅ VMAF library built and installed!"

# Build FFmpeg
echo ""
echo "🔨 Building FFmpeg..."
cd /tmp
if [ -d "ffmpeg" ]; then
    echo "   Removing existing ffmpeg directory..."
    rm -rf ffmpeg
fi

echo "   Cloning FFmpeg repository..."
git clone https://git.ffmpeg.org/ffmpeg.git
cd ffmpeg

echo "   Configuring FFmpeg build..."
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

echo "   Building FFmpeg (this may take 20-40 minutes)..."
make -j$(nproc)

echo "   Installing FFmpeg..."
make install
ldconfig

# Verify installation
echo ""
echo "🔍 Verifying installation..."
if ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
    echo "✅ SUCCESS! FFmpeg now has libvmaf support!"
    echo ""
    echo "FFmpeg version:"
    ffmpeg -version | head -1
    echo ""
    echo "libvmaf filter is available!"
else
    echo "❌ ERROR: Installation may have failed. libvmaf filter not found."
    echo "   Check the build logs above for errors."
    exit 1
fi


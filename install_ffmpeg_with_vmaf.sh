#!/bin/bash
# Install FFmpeg with libvmaf support
# This script installs libvmaf and rebuilds FFmpeg with VMAF support

set -e

echo "=========================================="
echo "Installing FFmpeg with libvmaf support"
echo "=========================================="

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo "Cannot detect OS. Assuming Ubuntu/Debian."
    OS="ubuntu"
fi

echo "Detected OS: $OS"

# Install dependencies
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    echo "Installing dependencies for Ubuntu/Debian..."
    sudo apt-get update
    sudo apt-get install -y \
        build-essential \
        git \
        nasm \
        yasm \
        cmake \
        meson \
        ninja-build \
        libx264-dev \
        libx265-dev \
        libvpx-dev \
        libfdk-aac-dev \
        libmp3lame-dev \
        libopus-dev \
        pkg-config \
        python3-pip \
        python3-setuptools

elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "rocky" ]; then
    echo "Installing dependencies for CentOS/RHEL..."
    sudo yum install -y epel-release
    sudo yum groupinstall -y "Development Tools"
    sudo yum install -y \
        git \
        nasm \
        yasm \
        cmake \
        meson \
        ninja-build \
        libx264-devel \
        libx265-devel \
        libvpx-devel \
        fdk-aac-devel \
        lame-devel \
        opus-devel \
        pkgconfig \
        python3-pip \
        python3-setuptools
else
    echo "Unsupported OS. Please install dependencies manually."
    exit 1
fi

# Install libvmaf
echo ""
echo "=========================================="
echo "Installing libvmaf"
echo "=========================================="

WORK_DIR=$(pwd)
VMAF_DIR="$WORK_DIR/libvmaf"
FFMPEG_DIR="$WORK_DIR/ffmpeg"

# Clone or update libvmaf
if [ -d "$VMAF_DIR" ]; then
    echo "libvmaf directory exists, updating..."
    cd "$VMAF_DIR"
    git pull
else
    echo "Cloning libvmaf..."
    git clone https://github.com/Netflix/vmaf.git "$VMAF_DIR"
    cd "$VMAF_DIR"
fi

# Build libvmaf
echo "Building libvmaf..."
cd "$VMAF_DIR/libvmaf"
meson setup build --buildtype release
ninja -C build
sudo ninja -C build install
sudo ldconfig

echo "✅ libvmaf installed"

# Install FFmpeg with libvmaf
echo ""
echo "=========================================="
echo "Installing FFmpeg with libvmaf"
echo "=========================================="

# Clone or update FFmpeg
if [ -d "$FFMPEG_DIR" ]; then
    echo "FFmpeg directory exists, updating..."
    cd "$FFMPEG_DIR"
    git pull
else
    echo "Cloning FFmpeg..."
    git clone https://git.ffmpeg.org/ffmpeg.git "$FFMPEG_DIR"
    cd "$FFMPEG_DIR"
fi

# Configure FFmpeg
echo "Configuring FFmpeg with libvmaf support..."
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
    --prefix=/usr/local

# Build FFmpeg
echo "Building FFmpeg (this may take 10-30 minutes)..."
make -j$(nproc)

# Install FFmpeg
echo "Installing FFmpeg..."
sudo make install
sudo ldconfig

# Verify installation
echo ""
echo "=========================================="
echo "Verifying installation"
echo "=========================================="

if ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
    echo "✅ FFmpeg with libvmaf installed successfully!"
    echo ""
    echo "FFmpeg version:"
    ffmpeg -version | head -n 1
    echo ""
    echo "libvmaf filter available:"
    ffmpeg -filters 2>/dev/null | grep libvmaf
else
    echo "❌ Installation may have failed. libvmaf filter not found."
    echo "Please check the build logs above for errors."
    exit 1
fi

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo "You can now use VMAF calculation in the compression pipeline."


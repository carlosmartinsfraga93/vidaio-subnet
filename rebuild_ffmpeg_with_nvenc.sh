#!/bin/bash
# Rebuild FFmpeg with BOTH libvmaf AND NVENC support
# This fixes the missing av1_nvenc encoder issue

set -e

echo "================================================================================"
echo "Rebuilding FFmpeg with libvmaf + NVENC Support"
echo "================================================================================"
echo ""
echo "This will:"
echo "  1. Install NVIDIA CUDA toolkit and headers (required for NVENC)"
echo "  2. Rebuild FFmpeg with --enable-nvenc and --enable-cuda-nvcc"
echo "  3. Enable hardware-accelerated AV1/HEVC/H.264 encoding"
echo ""
echo "⚠️  This will take 30-60 minutes"
echo ""

# Check for NVIDIA GPU
echo "1. Checking for NVIDIA GPU..."
echo "----------------------------------------"
if ! nvidia-smi &>/dev/null; then
    echo "❌ ERROR: nvidia-smi not found. NVIDIA drivers may not be installed."
    echo "   Please install NVIDIA drivers first."
    exit 1
fi

GPU_INFO=$(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader)
echo "✅ GPU Found: $GPU_INFO"
echo ""

# Install CUDA toolkit and NVENC headers
echo "2. Installing CUDA toolkit and NVENC headers..."
echo "----------------------------------------"

# Check if CUDA is already installed
if [ -d "/usr/local/cuda" ]; then
    echo "✅ CUDA toolkit already installed at /usr/local/cuda"
else
    echo "Installing CUDA toolkit..."
    # For Ubuntu 24.04, install CUDA 12.x
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
    sudo dpkg -i cuda-keyring_1.1-1_all.deb
    sudo apt-get update
    sudo apt-get install -y cuda-toolkit-12-6 cuda-nvcc-12-6
    rm cuda-keyring_1.1-1_all.deb
fi

# Install NVENC headers (nv-codec-headers)
echo ""
echo "Installing NVENC headers..."
cd /tmp
if [ -d "nv-codec-headers" ]; then
    rm -rf nv-codec-headers
fi
git clone https://git.videolan.org/git/ffmpeg/nv-codec-headers.git
cd nv-codec-headers
make
sudo make install
echo "✅ NVENC headers installed"
echo ""

# Verify libvmaf is still installed
echo "3. Verifying libvmaf installation..."
echo "----------------------------------------"
if pkg-config --exists libvmaf; then
    VMAF_VERSION=$(pkg-config --modversion libvmaf)
    echo "✅ libvmaf $VMAF_VERSION is installed"
else
    echo "❌ libvmaf not found. Please run fix_vmaf_install.sh first."
    exit 1
fi
echo ""

# Rebuild FFmpeg
echo "4. Rebuilding FFmpeg with NVENC + libvmaf..."
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

# Set CUDA paths
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/lib:/usr/local/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:/usr/local/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH

echo ""
echo "Configuring FFmpeg with NVENC + libvmaf support..."
./configure \
    --enable-gpl \
    --enable-version3 \
    --enable-nonfree \
    --enable-cuda-nvcc \
    --enable-nvenc \
    --enable-libvmaf \
    --enable-libdav1d \
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
echo "1. Checking libvmaf support:"
if /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
    echo "   ✅ libvmaf filter is available"
else
    echo "   ❌ libvmaf filter NOT found"
fi

echo ""
echo "2. Checking NVENC encoders:"
ENCODERS=$(/usr/local/bin/ffmpeg -encoders 2>/dev/null)

if echo "$ENCODERS" | grep -q "av1_nvenc"; then
    echo "   ✅ av1_nvenc is available"
else
    echo "   ❌ av1_nvenc NOT available"
fi

if echo "$ENCODERS" | grep -q "hevc_nvenc"; then
    echo "   ✅ hevc_nvenc is available"
else
    echo "   ❌ hevc_nvenc NOT available"
fi

if echo "$ENCODERS" | grep -q "h264_nvenc"; then
    echo "   ✅ h264_nvenc is available"
else
    echo "   ❌ h264_nvenc NOT available"
fi

echo ""
echo "================================================================================"
echo "Installation Complete!"
echo "================================================================================"
echo ""
echo "FFmpeg version:"
/usr/local/bin/ffmpeg -version | head -1
echo ""
echo "✅ You can now use hardware-accelerated encoding with av1_nvenc!"
echo ""
echo "Next steps:"
echo "  1. Run: python check_encoder_support.py"
echo "  2. Test compression: python quick_test_vmaf_fix.py"
echo ""


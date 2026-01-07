#!/bin/bash
# Setup script for training environment

set -e

echo "🚀 Setting up training environment..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    ffmpeg \
    wget \
    curl \
    build-essential \
    nasm \
    ninja-build \
    meson \
    doxygen \
    xxd

# Check if FFmpeg has VMAF support
echo "🔍 Checking FFmpeg VMAF support..."
if ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
    echo "✅ FFmpeg has VMAF support (libvmaf filter)"
else
    echo "⚠️  FFmpeg may not have VMAF support. VMAF calculation might not work."
    echo "   For full VMAF support, you may need to build VMAF from source:"
    echo "   See: docs/validator_setup.md#install-vmaf"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Verify GPU availability
echo "🔍 Checking GPU availability..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
    echo "✅ GPU detected"
else
    echo "⚠️  No GPU detected. Training will be slow on CPU."
fi

# Verify FFmpeg
echo "🔍 Verifying FFmpeg..."
ffmpeg -version | head -n 1

# Verify yt-dlp
echo "🔍 Verifying yt-dlp..."
if command -v yt-dlp &> /dev/null; then
    yt-dlp --version
else
    echo "⚠️  yt-dlp not found. Installing..."
    pip install yt-dlp
fi

# Verify Python packages
echo "🔍 Verifying Python packages..."
python3 -c "import torch; print(f'PyTorch: {torch.__version__}')" 2>/dev/null || echo "⚠️  PyTorch not installed yet"
python3 -c "import cv2; print(f'OpenCV: {cv2.__version__}')" 2>/dev/null || echo "⚠️  OpenCV not installed yet"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Install Python dependencies: pip install -r requirements.txt"
echo "   2. (Optional) Build VMAF from source if needed: see docs/validator_setup.md"
echo "   3. Run training: ./run_training.sh"


#!/bin/bash
# Install libvmaf for FFmpeg

set -e

echo "🔧 Installing libvmaf for FFmpeg..."
echo "===================================="

# Check if FFmpeg already has libvmaf
if ffmpeg -filters 2>/dev/null | grep -q libvmaf; then
    echo "✅ FFmpeg already has libvmaf support!"
    exit 0
fi

echo "⚠️  FFmpeg does not have libvmaf support."
echo ""
echo "To enable VMAF calculation, you need to:"
echo ""
echo "Option 1: Install FFmpeg with libvmaf support (Recommended)"
echo "  - Use a pre-built FFmpeg with libvmaf (e.g., from conda-forge)"
echo "  - Or compile FFmpeg from source with --enable-libvmaf"
echo ""
echo "Option 2: Build VMAF from source"
echo "  See: train/INSTALL_VMAF.md"
echo ""
echo "Option 3: Continue without VMAF (not recommended)"
echo "  Training will use estimated VMAF scores based on compression ratio"
echo "  This will result in lower quality models"
echo ""
read -p "Continue anyway? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo ""
echo "⚠️  Continuing without libvmaf support..."
echo "   VMAF scores will be estimated (not accurate)"


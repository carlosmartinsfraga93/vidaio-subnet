#!/bin/bash
# Fix FFmpeg PATH to use the version with libvmaf

echo "🔧 Fixing FFmpeg PATH"
echo "====================="
echo ""

# Check current ffmpeg
CURRENT_FFMPEG=$(which ffmpeg)
echo "Current ffmpeg: $CURRENT_FFMPEG"

# Check if /usr/local/bin/ffmpeg has libvmaf
if [ -f "/usr/local/bin/ffmpeg" ]; then
    if /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -q "libvmaf"; then
        echo "✅ /usr/local/bin/ffmpeg has libvmaf support"
        echo ""
        echo "To use it, run one of these:"
        echo ""
        echo "Option 1: Add to PATH for this session"
        echo "  export PATH=/usr/local/bin:\$PATH"
        echo ""
        echo "Option 2: Create alias in your shell"
        echo "  alias ffmpeg=/usr/local/bin/ffmpeg"
        echo ""
        echo "Option 3: Update training scripts (already done - they auto-detect)"
        echo "  The training scripts will now automatically use /usr/local/bin/ffmpeg"
        echo ""
        echo "Option 4: Make it permanent"
        echo "  echo 'export PATH=/usr/local/bin:\$PATH' >> ~/.bashrc"
        echo "  source ~/.bashrc"
    else
        echo "❌ /usr/local/bin/ffmpeg does not have libvmaf"
    fi
else
    echo "❌ /usr/local/bin/ffmpeg not found"
fi


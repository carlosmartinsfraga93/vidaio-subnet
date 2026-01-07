#!/bin/bash
# Fix FFmpeg path to use the one with libvmaf

set -e

echo "=========================================="
echo "Fixing FFmpeg Path"
echo "=========================================="

# Check if /usr/local/bin/ffmpeg has libvmaf
if /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -q "libvmaf"; then
    echo "✅ /usr/local/bin/ffmpeg has libvmaf support"
else
    echo "❌ /usr/local/bin/ffmpeg does not have libvmaf"
    exit 1
fi

# Check current FFmpeg
CURRENT_FFMPEG=$(which ffmpeg)
echo ""
echo "Current FFmpeg location: $CURRENT_FFMPEG"

# Option 1: Replace venv FFmpeg with symlink
if [[ "$CURRENT_FFMPEG" == *"/venv/"* ]]; then
    echo ""
    echo "Option 1: Replacing venv FFmpeg with symlink to /usr/local/bin/ffmpeg"
    read -p "Replace $CURRENT_FFMPEG? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup old FFmpeg
        if [ -f "$CURRENT_FFMPEG" ]; then
            echo "Backing up old FFmpeg..."
            sudo mv "$CURRENT_FFMPEG" "${CURRENT_FFMPEG}.old"
        fi
        
        # Create symlink
        echo "Creating symlink..."
        sudo ln -sf /usr/local/bin/ffmpeg "$CURRENT_FFMPEG"
        
        # Also replace ffprobe if it exists
        FFPROBE_PATH=$(dirname "$CURRENT_FFMPEG")/ffprobe
        if [ -f "$FFPROBE_PATH" ]; then
            echo "Replacing ffprobe..."
            sudo mv "$FFPROBE_PATH" "${FFPROBE_PATH}.old"
            sudo ln -sf /usr/local/bin/ffprobe "$FFPROBE_PATH"
        fi
        
        echo "✅ FFmpeg replaced"
    fi
fi

# Option 2: Update PATH in shell config
echo ""
echo "Option 2: Update PATH to prioritize /usr/local/bin"
echo "Add this to your ~/.bashrc or activate script:"
echo "  export PATH=/usr/local/bin:\$PATH"

# Verify
echo ""
echo "=========================================="
echo "Verifying Fix"
echo "=========================================="

# Check which FFmpeg is now used
NEW_FFMPEG=$(which ffmpeg)
echo "FFmpeg location: $NEW_FFMPEG"

# Check if it has libvmaf
if ffmpeg -filters 2>/dev/null | grep -q "libvmaf"; then
    echo "✅ SUCCESS! FFmpeg now has libvmaf support!"
    echo ""
    echo "FFmpeg version:"
    ffmpeg -version | head -n 1
    echo ""
    echo "libvmaf filter:"
    ffmpeg -filters 2>/dev/null | grep libvmaf
else
    echo "❌ Still using FFmpeg without libvmaf"
    echo ""
    echo "Try running:"
    echo "  export PATH=/usr/local/bin:\$PATH"
    echo "  which ffmpeg"
    echo "  ffmpeg -filters | grep libvmaf"
fi


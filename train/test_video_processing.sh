#!/bin/bash
# Test processing of a single video to debug issues

VIDEOS_DIR="${1:-datasets/videos}"

echo "🔍 Testing video processing"
echo "============================"
echo ""

# Find first video
FIRST_VIDEO=$(find "$VIDEOS_DIR" -type f \( -name "*.mp4" -o -name "*.avi" -o -name "*.mov" \) 2>/dev/null | head -1)

if [ -z "$FIRST_VIDEO" ]; then
    echo "❌ No videos found in $VIDEOS_DIR"
    exit 1
fi

echo "Testing with: $(basename "$FIRST_VIDEO")"
echo ""

# Run debug script
python debug_preprocessing_pipeline.py "$FIRST_VIDEO"

echo ""
echo "💡 If encoding fails, check:"
echo "   - nvidia-smi (GPU available?)"
echo "   - ffmpeg -encoders | grep nvenc (NVENC available?)"
echo ""
echo "💡 If VMAF fails, check:"
echo "   - ffmpeg -filters | grep libvmaf (libvmaf available?)"
echo "   - /usr/local/bin/ffmpeg -filters | grep libvmaf"




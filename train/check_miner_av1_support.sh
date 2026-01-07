#!/bin/bash
# Check if miner environment can decode AV1 videos

echo "🔍 Checking AV1 Decoder Support for Miner"
echo "=========================================="
echo ""

# Check FFmpeg AV1 decoder
echo "1. Checking FFmpeg AV1 decoder support:"
if command -v ffmpeg &> /dev/null; then
    FFMPEG_PATH=$(which ffmpeg)
    echo "   FFmpeg location: $FFMPEG_PATH"
    
    if ffmpeg -decoders 2>/dev/null | grep -qi "libdav1d\|av1"; then
        echo "   ✅ AV1 decoder available (libdav1d)"
        AV1_DECODER=true
    else
        echo "   ❌ AV1 decoder NOT available"
        echo "   ⚠️  Miner will fail when processing AV1-encoded videos"
        AV1_DECODER=false
    fi
else
    echo "   ❌ FFmpeg not found in PATH"
    AV1_DECODER=false
fi

echo ""
echo "2. Checking FFmpeg AV1 encoder support:"
if command -v ffmpeg &> /dev/null; then
    if ffmpeg -encoders 2>/dev/null | grep -qi "av1_nvenc\|av1"; then
        echo "   ✅ AV1 encoder available (NVENC)"
        AV1_ENCODER=true
    else
        echo "   ❌ AV1 encoder NOT available"
        AV1_ENCODER=false
    fi
else
    AV1_ENCODER=false
fi

echo ""
echo "=========================================="
echo "Summary:"
echo "=========================================="

if [ "$AV1_ENCODER" = true ] && [ "$AV1_DECODER" = true ]; then
    echo "✅ Full AV1 support: Can encode AND decode AV1"
    echo "   → Miner will work with AV1-encoded videos"
    echo "   → No changes needed"
elif [ "$AV1_ENCODER" = true ] && [ "$AV1_DECODER" = false ]; then
    echo "⚠️  Partial AV1 support: Can encode but CANNOT decode AV1"
    echo "   → Miner will FAIL when calculating VMAF on AV1 videos"
    echo ""
    echo "💡 Solutions:"
    echo "   1. Install AV1 decoder: sudo apt-get install libdav1d-dev libdav1d6"
    echo "   2. OR switch to HEVC training: ./switch_to_hevc_training.sh"
elif [ "$AV1_ENCODER" = false ]; then
    echo "❌ No AV1 support: Cannot encode AV1"
    echo "   → Use HEVC instead: ./switch_to_hevc_training.sh"
else
    echo "❌ Unknown state"
fi

echo ""



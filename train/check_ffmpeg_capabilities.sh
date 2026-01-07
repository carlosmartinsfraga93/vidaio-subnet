#!/bin/bash
# Check FFmpeg capabilities

echo "🔍 Checking FFmpeg capabilities"
echo "================================="
echo ""

check_ffmpeg() {
    local ffmpeg_path="$1"
    local name="$2"
    
    if [ ! -f "$ffmpeg_path" ]; then
        echo "❌ $name: Not found"
        return
    fi
    
    echo "📹 $name: $ffmpeg_path"
    
    # Check libvmaf
    if $ffmpeg_path -filters 2>/dev/null | grep -q libvmaf; then
        echo "   ✅ libvmaf: Available"
    else
        echo "   ❌ libvmaf: Not available"
    fi
    
    # Check NVENC
    if $ffmpeg_path -encoders 2>/dev/null | grep -qi nvenc; then
        echo "   ✅ NVENC: Available"
        $ffmpeg_path -encoders 2>/dev/null | grep -i nvenc | sed 's/^/      /'
    else
        echo "   ❌ NVENC: Not available"
    fi
    
    echo ""
}

check_ffmpeg "/usr/local/bin/ffmpeg" "Built FFmpeg"
check_ffmpeg "$(which ffmpeg)" "PATH FFmpeg"

echo "💡 Recommendation:"
if /usr/local/bin/ffmpeg -encoders 2>/dev/null | grep -qi nvenc; then
    echo "   ✅ Use /usr/local/bin/ffmpeg (has both libvmaf and NVENC)"
elif which ffmpeg &>/dev/null && $(which ffmpeg) -encoders 2>/dev/null | grep -qi nvenc; then
    echo "   ⚠️  Use PATH ffmpeg for encoding, /usr/local/bin/ffmpeg for VMAF"
    echo "   (Script will handle this automatically)"
else
    echo "   ❌ Need to rebuild FFmpeg with NVENC support"
fi




#!/bin/bash
# Verify FFmpeg libvmaf support and fix PATH if needed

set -e

echo "🔍 Verifying FFmpeg libvmaf support"
echo "===================================="
echo ""

# Check which ffmpeg is being used
echo "1. Checking which ffmpeg binary is in use:"
WHICH_FFMPEG=$(which ffmpeg)
echo "   Current ffmpeg: $WHICH_FFMPEG"

# Check both system and local ffmpeg
echo ""
echo "2. Checking system ffmpeg:"
if command -v ffmpeg &> /dev/null; then
    SYSTEM_FFMPEG=$(which ffmpeg)
    echo "   Location: $SYSTEM_FFMPEG"
    if $SYSTEM_FFMPEG -filters 2>/dev/null | grep -q "libvmaf"; then
        echo "   ✅ System ffmpeg HAS libvmaf support!"
    else
        echo "   ❌ System ffmpeg does NOT have libvmaf"
    fi
fi

echo ""
echo "3. Checking /usr/local/bin/ffmpeg (our build):"
if [ -f "/usr/local/bin/ffmpeg" ]; then
    echo "   Location: /usr/local/bin/ffmpeg"
    if /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -q "libvmaf"; then
        echo "   ✅ Built ffmpeg HAS libvmaf support!"
        echo ""
        echo "   Available VMAF filters:"
        /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -i vmaf
    else
        echo "   ❌ Built ffmpeg does NOT have libvmaf"
    fi
else
    echo "   ❌ /usr/local/bin/ffmpeg not found"
fi

# Check PATH
echo ""
echo "4. Checking PATH:"
echo "   PATH: $PATH"
if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
    echo "   ⚠️  /usr/local/bin is NOT in PATH"
    echo "   This means 'ffmpeg' command uses system version, not our build!"
else
    echo "   ✅ /usr/local/bin is in PATH"
fi

# Solution
echo ""
echo "=========================================="
echo "SOLUTION:"
echo "=========================================="
echo ""

if [ -f "/usr/local/bin/ffmpeg" ] && /usr/local/bin/ffmpeg -filters 2>/dev/null | grep -q "libvmaf"; then
    echo "✅ Your built FFmpeg HAS libvmaf support!"
    echo ""
    if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
        echo "⚠️  But /usr/local/bin is not first in PATH"
        echo ""
        echo "Fix by running one of these:"
        echo ""
        echo "Option 1: Add to PATH for current session"
        echo "  export PATH=/usr/local/bin:\$PATH"
        echo ""
        echo "Option 2: Use full path"
        echo "  /usr/local/bin/ffmpeg -filters | grep libvmaf"
        echo ""
        echo "Option 3: Create alias"
        echo "  alias ffmpeg=/usr/local/bin/ffmpeg"
        echo ""
        echo "Option 4: Make it permanent (add to ~/.bashrc)"
        echo "  echo 'export PATH=/usr/local/bin:\$PATH' >> ~/.bashrc"
        echo "  source ~/.bashrc"
        echo ""
        echo "After fixing PATH, verify with:"
        echo "  ffmpeg -filters | grep libvmaf"
    else
        echo "✅ Everything is set up correctly!"
        echo ""
        echo "Verify with:"
        echo "  ffmpeg -filters | grep libvmaf"
    fi
else
    echo "❌ FFmpeg with libvmaf not found"
    echo "   Run: ./rebuild_ffmpeg_with_explicit_vmaf.sh"
fi


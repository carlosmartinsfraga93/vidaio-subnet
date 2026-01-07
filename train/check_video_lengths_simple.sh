#!/bin/bash
# Simple script to check video lengths

VIDEOS_DIR="${1:-datasets/videos}"

echo "📹 Video Lengths in: $VIDEOS_DIR"
echo "================================="
echo ""

# Find FFprobe
if [ -f "/usr/local/bin/ffprobe" ]; then
    FFPROBE="/usr/local/bin/ffprobe"
elif command -v ffprobe &> /dev/null; then
    FFPROBE=$(which ffprobe)
else
    echo "❌ ffprobe not found!"
    exit 1
fi

# Check first 20 videos
echo "First 20 videos:"
echo "----------------"
count=0
for video in $(find "$VIDEOS_DIR" -type f \( -name "*.mp4" -o -name "*.avi" -o -name "*.mov" \) 2>/dev/null | head -20); do
    duration=$($FFPROBE -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
    if [ -n "$duration" ]; then
        duration_int=$(printf "%.0f" "$duration")
        filename=$(basename "$video" | cut -c1-50)
        status=""
        if (( duration_int <= 30 )); then
            status="✅ (will process)"
        else
            status="⏭️  (skipped, >30s)"
        fi
        printf "  %-50s %6ss %s\n" "$filename" "$duration_int" "$status"
        count=$((count + 1))
    fi
done

echo ""
echo "Total checked: $count videos"




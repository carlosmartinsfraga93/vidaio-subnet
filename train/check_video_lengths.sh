#!/bin/bash
# Check video lengths in a directory

VIDEOS_DIR="${1:-datasets/videos}"

echo "📹 Checking video lengths in: $VIDEOS_DIR"
echo "=========================================="
echo ""

# Count total videos
total=$(find "$VIDEOS_DIR" -type f \( -name "*.mp4" -o -name "*.avi" -o -name "*.mov" -o -name "*.mkv" -o -name "*.webm" \) 2>/dev/null | wc -l)
echo "Total videos: $total"
echo ""

# Use ffprobe to get durations
echo "Analyzing video durations..."
echo ""

# Find FFmpeg binary (prioritize /usr/local/bin)
FFPROBE_BIN=""
if [ -f "/usr/local/bin/ffprobe" ]; then
    FFPROBE_BIN="/usr/local/bin/ffprobe"
elif command -v ffprobe &> /dev/null; then
    FFPROBE_BIN=$(which ffprobe)
else
    echo "❌ ffprobe not found!"
    exit 1
fi

echo "Using: $FFPROBE_BIN"
echo ""

# Get durations and categorize
short_count=0
medium_count=0
long_count=0
very_long_count=0
total_duration=0

# Process each video
while IFS= read -r video; do
    duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
    
    if [ -n "$duration" ] && [ "$duration" != "N/A" ]; then
        duration_int=$(printf "%.0f" "$duration")
        total_duration=$(echo "$total_duration + $duration" | bc -l 2>/dev/null || echo "$total_duration")
        
        if (( $(echo "$duration <= 30" | bc -l 2>/dev/null || echo 0) )); then
            short_count=$((short_count + 1))
        elif (( $(echo "$duration <= 60" | bc -l 2>/dev/null || echo 0) )); then
            medium_count=$((medium_count + 1))
        elif (( $(echo "$duration <= 300" | bc -l 2>/dev/null || echo 0) )); then
            long_count=$((long_count + 1))
        else
            very_long_count=$((very_long_count + 1))
        fi
    fi
done < <(find "$VIDEOS_DIR" -type f \( -name "*.mp4" -o -name "*.avi" -o -name "*.mov" -o -name "*.mkv" -o -name "*.webm" \) 2>/dev/null | head -100)

echo "📊 Duration Distribution (first 100 videos):"
echo "   ≤ 30 seconds:  $short_count videos (will be processed)"
echo "   31-60 seconds: $medium_count videos"
echo "   61-300 seconds: $long_count videos"
echo "   > 300 seconds:  $very_long_count videos"
echo ""

# Quick check with a sample
echo "Sample video durations (first 10):"
echo "-----------------------------------"
count=0
for video in $(find "$VIDEOS_DIR" -type f \( -name "*.mp4" -o -name "*.avi" -o -name "*.mov" \) 2>/dev/null | head -10); do
    duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
    if [ -n "$duration" ]; then
        duration_formatted=$(printf "%.2f" "$duration")
        filename=$(basename "$video")
        echo "  $filename: ${duration_formatted}s"
    fi
done

echo ""
echo "💡 To see all video lengths:"
echo "   for f in $VIDEOS_DIR/**/*.mp4; do echo \"\$(basename \$f): \$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"\$f\" 2>/dev/null | cut -d. -f1)s\"; done"




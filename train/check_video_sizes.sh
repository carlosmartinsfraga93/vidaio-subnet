#!/bin/bash
# Check video file sizes and durations

DATA_DIR="${1:-datasets/videos}"

echo "📊 Video Size Analysis"
echo "====================="
echo ""

total_videos=0
total_size=0
oversized=0
long_videos=0

for video in $(find "$DATA_DIR" -name "*.mp4" -type f); do
    total_videos=$((total_videos + 1))
    
    # Get file size
    size_bytes=$(stat -f%z "$video" 2>/dev/null || stat -c%s "$video" 2>/dev/null || echo "0")
    size_mb=$((size_bytes / 1024 / 1024))
    total_size=$((total_size + size_mb))
    
    # Get duration
    duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null | cut -d. -f1)
    duration=${duration:-0}
    duration_min=$((duration / 60))
    duration_sec=$((duration % 60))
    
    # Check if oversized
    if [ "$size_mb" -gt 500 ]; then
        oversized=$((oversized + 1))
        echo "⚠️  $(basename "$video"): ${size_mb}MB, ${duration_min}m ${duration_sec}s"
    fi
    
    # Check if too long
    if [ "$duration" -gt 600 ]; then
        long_videos=$((long_videos + 1))
    fi
done

echo ""
echo "📈 Summary:"
echo "  Total videos: $total_videos"
echo "  Total size: ${total_size}MB (~$((total_size / 1024))GB)"
if [ "$total_videos" -gt 0 ]; then
    avg_size=$((total_size / total_videos))
    echo "  Average size: ${avg_size}MB per video"
fi

if [ "$oversized" -gt 0 ]; then
    echo ""
    echo "⚠️  $oversized videos exceed 500MB"
    echo "   Run: ./cleanup_oversized_videos.sh"
fi

if [ "$long_videos" -gt 0 ]; then
    echo ""
    echo "⚠️  $long_videos videos exceed 10 minutes"
    echo "   Run: ./cleanup_oversized_videos.sh"
fi



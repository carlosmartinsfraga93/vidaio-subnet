#!/bin/bash
# Remove videos that are too large or too long

DATA_DIR="${1:-datasets/videos}"
MAX_SIZE_MB=500
MAX_DURATION_SEC=600  # 10 minutes

echo "🧹 Cleaning up oversized videos..."
echo "===================================="
echo ""
echo "Max file size: ${MAX_SIZE_MB}MB"
echo "Max duration: ${MAX_DURATION_SEC}s (10 minutes)"
echo ""

total_removed=0
total_size_freed=0

for video in $(find "$DATA_DIR" -name "*.mp4" -type f); do
    # Check file size
    size_bytes=$(stat -f%z "$video" 2>/dev/null || stat -c%s "$video" 2>/dev/null || echo "0")
    size_mb=$((size_bytes / 1024 / 1024))
    
    # Check duration
    duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null | cut -d. -f1)
    duration=${duration:-0}
    
    should_remove=false
    reason=""
    
    if [ "$size_mb" -gt "$MAX_SIZE_MB" ]; then
        should_remove=true
        reason="size (${size_mb}MB > ${MAX_SIZE_MB}MB)"
    fi
    
    if [ "$duration" -gt "$MAX_DURATION_SEC" ]; then
        should_remove=true
        if [ -n "$reason" ]; then
            reason="${reason}, duration (${duration}s > ${MAX_DURATION_SEC}s)"
        else
            reason="duration (${duration}s > ${MAX_DURATION_SEC}s)"
        fi
    fi
    
    if [ "$should_remove" = true ]; then
        echo "❌ Removing: $(basename "$video")"
        echo "   Reason: $reason"
        total_size_freed=$((total_size_freed + size_mb))
        rm -f "$video"
        total_removed=$((total_removed + 1))
    fi
done

echo ""
echo "===================================="
echo "✅ Removed $total_removed videos"
echo "💾 Freed ~${total_size_freed}MB"
echo "===================================="



#!/bin/bash
# Check download progress and estimate time remaining

DATA_DIR="${1:-datasets/videos}"

echo "📊 Download Progress Check"
echo "=========================="
echo ""

# Count videos by category
total=0
for category in gaming animation faces text mixed; do
    count=$(find "$DATA_DIR/$category" -name "*.mp4" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
        size=$(du -sh "$DATA_DIR/$category" 2>/dev/null | cut -f1)
        echo "  $category: $count videos ($size)"
        total=$((total + count))
    fi
done

echo ""
echo "Total videos: $total"
echo ""

# Estimate time
if [ "$total" -gt 0 ]; then
    # Average download time per video: ~30-60 seconds
    # With 50 videos per category = 250 videos total
    # Estimated time: 250 * 45 seconds = ~3 hours
    
    videos_per_category=200
    total_target=$((videos_per_category * 5))  # 5 categories
    
    if [ "$total" -lt "$total_target" ]; then
        remaining=$((total_target - total))
        estimated_minutes=$((remaining * 1))  # ~1 minute per video average
        estimated_hours=$((estimated_minutes / 60))
        estimated_mins=$((estimated_minutes % 60))
        
        echo "📈 Progress: $total / $total_target videos ($((total * 100 / total_target))%)"
        echo "⏱️  Estimated time remaining: ~${estimated_hours}h ${estimated_mins}m"
    else
        echo "✅ Download complete!"
    fi
else
    echo "⚠️  No videos found yet. Downloads may still be in progress."
fi

echo ""
echo "💡 Tips:"
echo "  - Downloads run in background, you can check progress anytime"
echo "  - Lower quality videos (360p-720p) download faster"
echo "  - Network speed affects download time significantly"
echo "  - YouTube may rate limit, causing temporary slowdowns"



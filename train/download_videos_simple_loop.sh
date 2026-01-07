#!/bin/bash
# Simple loop-based download that retries until count is reached

set -e

echo "🚀 Downloading videos (retry until target reached)..."
echo "======================================"

# Configuration
OUTPUT_DIR="datasets/videos"
TARGET_PER_CATEGORY=200
BATCH_SIZE=50  # Download this many per attempt

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Categories
declare -A CATEGORIES=(
    ["gaming"]="gaming gameplay -shorts"
    ["animation"]="animation cartoon -shorts"
    ["faces"]="people talking portrait -shorts"
    ["text"]="screen recording tutorial -shorts"
    ["mixed"]="nature landscape city -shorts"
)

echo ""
echo "Strategy: Download in batches of $BATCH_SIZE until reaching $TARGET_PER_CATEGORY per category"
echo ""

total_downloaded=0

for category in "${!CATEGORIES[@]}"; do
    query="${CATEGORIES[$category]}"
    category_dir="$OUTPUT_DIR/$category"
    mkdir -p "$category_dir"
    
    echo "=========================================="
    echo "📥 Category: $category"
    echo "=========================================="
    
    output_template="$category_dir/%(title)s.%(ext)s"
    
    JS_RUNTIME=""
    if command -v node &> /dev/null; then
        JS_RUNTIME="--js-runtimes node"
    fi
    
    batch_num=1
    
    while true; do
        current_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
        
        if [ "$current_count" -ge "$TARGET_PER_CATEGORY" ]; then
            echo "   ✅ Target reached: $current_count videos"
            break
        fi
        
        needed=$((TARGET_PER_CATEGORY - current_count))
        to_download=$((needed < BATCH_SIZE ? needed : BATCH_SIZE))
        
        echo ""
        echo "   Batch $batch_num: $current_count / $TARGET_PER_CATEGORY videos"
        echo "   Downloading $to_download more..."
        
        yt-dlp \
            "ytsearch${to_download}:${query}" \
            -f "22/18/best[height<=720][ext=mp4]/best[height<=480][ext=mp4]/best[ext=mp4]/best" \
            -o "$output_template" \
            --no-playlist \
            --match-filter "duration <= 600 & !is_live & !is_upcoming & duration > 30" \
            --ignore-errors \
            --max-downloads "$to_download" \
            --merge-output-format "mp4" \
            --retries 1 \
            --fragment-retries 1 \
            --max-filesize 500M \
            --no-warnings \
            $JS_RUNTIME \
            --progress 2>&1 | tail -5
        
        new_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
        downloaded_this_batch=$((new_count - current_count))
        
        echo "   ✅ Batch $batch_num complete: +$downloaded_this_batch videos (total: $new_count)"
        
        # If no new videos downloaded, try different search terms
        if [ "$downloaded_this_batch" -eq 0 ]; then
            echo "   ⚠️  No new videos. Trying alternative search..."
            sleep 2
        fi
        
        batch_num=$((batch_num + 1))
        
        # Safety limit: max 20 batches per category
        if [ "$batch_num" -gt 20 ]; then
            echo "   ⚠️  Reached max batches (20). Stopping."
            break
        fi
        
        sleep 2
    done
    
    final_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    total_downloaded=$((total_downloaded + final_count))
    
    echo ""
done

echo "======================================"
echo "✅ Complete! Total: $total_downloaded videos"
echo "======================================"



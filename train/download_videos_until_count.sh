#!/bin/bash
# Download script that keeps running until target count is reached

set -e

echo "🚀 Downloading videos (will retry until target count reached)..."
echo "======================================"

# Configuration
OUTPUT_DIR="datasets/videos"
NUM_VIDEOS_PER_CATEGORY=200
MAX_ATTEMPTS=5  # Maximum number of search attempts per category
VIDEOS_PER_SEARCH=100  # Videos to search per attempt

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Categories and search queries
declare -A CATEGORIES=(
    ["gaming"]="gaming gameplay -shorts"
    ["animation"]="animation cartoon -shorts"
    ["faces"]="people talking portrait -shorts"
    ["text"]="screen recording tutorial -shorts"
    ["mixed"]="nature landscape city -shorts"
)

echo ""
echo "Downloading videos by category..."
echo "   Target: $NUM_VIDEOS_PER_CATEGORY videos per category"
echo "   Will retry until target is reached (max $MAX_ATTEMPTS attempts)"
echo ""

total_downloaded=0

for category in "${!CATEGORIES[@]}"; do
    query="${CATEGORIES[$category]}"
    category_dir="$OUTPUT_DIR/$category"
    mkdir -p "$category_dir"
    
    echo "=========================================="
    echo "📥 Category: $category"
    echo "   Query: $query"
    echo "   Target: $NUM_VIDEOS_PER_CATEGORY videos"
    echo "=========================================="
    
    output_template="$category_dir/%(title)s.%(ext)s"
    
    # Check for Node.js
    JS_RUNTIME=""
    if command -v node &> /dev/null; then
        JS_RUNTIME="--js-runtimes node"
    fi
    
    # Count videos before download
    videos_before=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    current_count=$videos_before
    attempt=1
    
    # Keep trying until we reach target count
    while [ "$current_count" -lt "$NUM_VIDEOS_PER_CATEGORY" ] && [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
        needed=$((NUM_VIDEOS_PER_CATEGORY - current_count))
        
        echo ""
        echo "Attempt $attempt/$MAX_ATTEMPTS:"
        echo "   Current: $current_count videos"
        echo "   Needed: $needed more videos"
        echo "   Searching for: $VIDEOS_PER_SEARCH videos..."
        echo ""
        
        # Download with flexible format selection
        yt-dlp \
            "ytsearch${VIDEOS_PER_SEARCH}:${query}" \
            -f "22/18/best[height<=720][ext=mp4]/best[height<=480][ext=mp4]/best[height<=360][ext=mp4]/best[ext=mp4]/best" \
            -o "$output_template" \
            --no-playlist \
            --match-filter "duration <= 600 & !is_live & !is_upcoming & duration > 30" \
            --ignore-errors \
            --max-downloads "$VIDEOS_PER_SEARCH" \
            --merge-output-format "mp4" \
            --retries 2 \
            --fragment-retries 2 \
            --max-filesize 500M \
            --no-warnings \
            $JS_RUNTIME \
            --progress \
            --newline 2>&1 | grep -v "WARNING\|SABR\|format" | grep -E "(download|ERROR|youtube.*Downloading|100%)" || true
        
        # Count current videos
        current_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
        new_in_attempt=$((current_count - videos_before))
        
        echo ""
        echo "   ✅ After attempt $attempt: $current_count videos ($new_in_attempt new)"
        
        # Check if we reached target
        if [ "$current_count" -ge "$NUM_VIDEOS_PER_CATEGORY" ]; then
            echo "   🎯 Target reached!"
            break
        fi
        
        # Update videos_before for next iteration
        videos_before=$current_count
        attempt=$((attempt + 1))
        
        # Small delay between attempts
        if [ "$attempt" -le "$MAX_ATTEMPTS" ]; then
            echo "   ⏳ Waiting 5 seconds before next attempt..."
            sleep 5
        fi
    done
    
    new_downloads=$((current_count - videos_before))
    total_downloaded=$((total_downloaded + new_downloads))
    
    echo ""
    echo "=========================================="
    echo "✅ Category complete: $category"
    if [ "$current_count" -ge "$NUM_VIDEOS_PER_CATEGORY" ]; then
        echo "   ✅ Target reached: $current_count videos"
    else
        echo "   ⚠️  Partial: $current_count / $NUM_VIDEOS_PER_CATEGORY videos"
        echo "   (Reached max attempts: $MAX_ATTEMPTS)"
    fi
    echo "=========================================="
    echo ""
done

echo "======================================"
echo "✅ All downloads complete!"
echo "📊 Total new videos: $total_downloaded"
echo "📁 Videos saved to: $OUTPUT_DIR"
echo "======================================"



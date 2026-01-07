#!/bin/bash
# Robust download script with better error handling and format selection

set -e

echo "🚀 Downloading videos for training (ROBUST MODE)..."
echo "======================================"

# Configuration
OUTPUT_DIR="datasets/videos"
NUM_VIDEOS_PER_CATEGORY=200

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Categories and search queries (avoiding "shorts" in search)
declare -A CATEGORIES=(
    ["gaming"]="gaming gameplay -shorts"
    ["animation"]="animation cartoon -shorts"
    ["faces"]="people talking portrait -shorts"
    ["text"]="screen recording tutorial -shorts"
    ["mixed"]="nature landscape city -shorts"
)

echo ""
echo "Downloading videos by category..."
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
    
    # Check for Node.js (optional, reduces warnings)
    JS_RUNTIME=""
    if command -v node &> /dev/null; then
        JS_RUNTIME="--js-runtimes node"
    fi
    
    # Count videos before download
    videos_before=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    
    echo ""
    echo "Starting download..."
    echo ""
    
    # Use simpler, more robust format selection
    # Priority: 720p -> 480p -> 360p -> any available
    # Exclude shorts, live streams, and upcoming videos
    yt-dlp \
        "ytsearch${NUM_VIDEOS_PER_CATEGORY}:${query}" \
        -f "22/18/best[height<=720][ext=mp4]/best[height<=480][ext=mp4]/best[height<=360][ext=mp4]/best[ext=mp4]/best" \
        -o "$output_template" \
        --no-playlist \
        --match-filter "duration <= 600 & !is_live & !is_upcoming & duration > 30" \
        --ignore-errors \
        --max-downloads "$NUM_VIDEOS_PER_CATEGORY" \
        --merge-output-format "mp4" \
        --retries 2 \
        --fragment-retries 2 \
        --max-filesize 500M \
        --no-warnings \
        $JS_RUNTIME \
        --progress \
        --newline 2>&1 | grep -v "WARNING\|SABR\|format" | grep -E "(download|ERROR|youtube.*Downloading|100%)" || true
    
    downloaded=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    new_downloads=$((downloaded - videos_before))
    total_downloaded=$((total_downloaded + new_downloads))
    
    echo ""
    echo "=========================================="
    echo "✅ Category complete: $category"
    echo "   New videos: $new_downloads"
    echo "   Total in category: $downloaded"
    echo "=========================================="
    echo ""
done

echo "======================================"
echo "✅ All downloads complete!"
echo "📊 Total new videos: $total_downloaded"
echo "📁 Videos saved to: $OUTPUT_DIR"
echo "======================================"



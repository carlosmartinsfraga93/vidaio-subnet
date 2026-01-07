#!/bin/bash
# Verbose download script - shows ALL progress details

set -e

echo "🚀 Downloading videos for training (VERBOSE MODE)..."
echo "======================================"

# Configuration
OUTPUT_DIR="datasets/videos"
NUM_VIDEOS_PER_CATEGORY=200

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Categories and search queries
declare -A CATEGORIES=(
    ["gaming"]="gaming gameplay"
    ["animation"]="animation cartoon"
    ["faces"]="people talking portrait"
    ["text"]="screen recording tutorial"
    ["mixed"]="nature landscape city"
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
    echo "Starting download (showing full progress)..."
    echo ""
    
    # Run yt-dlp with flexible format selection
    # Format priority: 720p -> 480p -> 360p -> any available
    # Exclude shorts, prefer mp4, max 10 minutes, max 500MB
    yt-dlp \
        "ytsearch${NUM_VIDEOS_PER_CATEGORY}:${query}" \
        -f "best[height<=720][ext=mp4][duration<=600]/best[height<=480][ext=mp4][duration<=600]/best[height<=360][ext=mp4][duration<=600]/22/18/136+140/best[height<=720][duration<=600]/best[height<=480][duration<=600]/best[duration<=600]" \
        -o "$output_template" \
        --no-playlist \
        --no-playlist-reverse \
        --match-filter "duration <= 600 & !is_live & !is_upcoming" \
        --ignore-errors \
        --max-downloads "$NUM_VIDEOS_PER_CATEGORY" \
        --merge-output-format "mp4" \
        --retries 2 \
        --fragment-retries 2 \
        --max-filesize 500M \
        --no-warnings \
        $JS_RUNTIME \
        --progress \
        --newline
    
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


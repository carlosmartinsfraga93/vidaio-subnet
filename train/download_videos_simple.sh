#!/bin/bash
# Simple script to download videos using yt-dlp

set -e

echo "🚀 Downloading videos for training..."
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
    
    echo "📥 Category: $category"
    echo "   Query: $query"
    echo "   Target: $NUM_VIDEOS_PER_CATEGORY videos"
    
    output_template="$category_dir/%(title)s.%(ext)s"
    
    # Check for Node.js (optional, reduces warnings)
    JS_RUNTIME=""
    if command -v node &> /dev/null; then
        JS_RUNTIME="--js-runtimes node"
    fi
    
    # Count videos before download
    videos_before=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    
    echo "   Starting download..."
    echo "   (Progress will show below)"
    echo ""
    
    yt-dlp \
        "ytsearch${NUM_VIDEOS_PER_CATEGORY}:${query}" \
        -f "best[height<=720][ext=mp4][duration<=600]/best[height<=480][ext=mp4][duration<=600]/best[height<=360][ext=mp4][duration<=600]/22/18/136+140/best[height<=720][duration<=600]/best[height<=480][duration<=600]/best[duration<=600]" \
        -o "$output_template" \
        --no-playlist \
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
        --newline \
        --progress-template "[download] %(progress.downloaded_bytes)s/%(progress.total_bytes)s @ %(progress.speed)s | ETA: %(progress.eta)s | %(info.title)s" 2>&1 | while IFS= read -r line; do
            # Show download progress lines
            if [[ "$line" =~ \[download\] ]]; then
                echo "   $line"
            # Show video info (skip warnings)
            elif [[ "$line" =~ \[youtube\] ]] && [[ "$line" =~ Downloading ]] && [[ ! "$line" =~ WARNING ]]; then
                echo "   $line"
            # Show errors (but not format warnings)
            elif [[ "$line" =~ ERROR ]] && [[ ! "$line" =~ format ]]; then
                echo "   ❌ $line"
            # Show completion
            elif [[ "$line" =~ has\ already\ been\ downloaded ]] || [[ "$line" =~ 100% ]]; then
                echo "   ✅ $line"
            fi
        done
    
    echo ""
    
    downloaded=$(find "$category_dir" -name "*.mp4" | wc -l)
    total_downloaded=$((total_downloaded + downloaded))
    
    echo "   ✅ Downloaded: $downloaded videos"
    echo ""
done

echo "======================================"
echo "✅ Total videos downloaded: $total_downloaded"
echo "📁 Videos saved to: $OUTPUT_DIR"
echo "======================================"


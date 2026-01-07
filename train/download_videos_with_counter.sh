#!/bin/bash
# Download script with video counter and progress

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
    
    # Run yt-dlp and parse output for progress
    yt-dlp \
        "ytsearch${NUM_VIDEOS_PER_CATEGORY}:${query}" \
        -f "bestvideo[ext=mp4][height<=720][duration<=600]+bestaudio[ext=m4a]/bestvideo[ext=mp4][height<=480][duration<=600]+bestaudio[ext=m4a]/best[ext=mp4][height<=720][duration<=600]/best[height<=480][duration<=600]" \
        -o "$output_template" \
        --no-playlist \
        --ignore-errors \
        --max-downloads "$NUM_VIDEOS_PER_CATEGORY" \
        --merge-output-format "mp4" \
        --retries 3 \
        --fragment-retries 3 \
        --max-filesize 500M \
        $JS_RUNTIME \
        --progress \
        --newline 2>&1 | while IFS= read -r line; do
            # Extract and display key information
            if [[ "$line" =~ \[download\]\ *([0-9.]+)% ]]; then
                percent="${BASH_REMATCH[1]}"
                # Get current video count
                current_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
                echo "[$current_count/$NUM_VIDEOS_PER_CATEGORY] $line"
            elif [[ "$line" =~ \[youtube\]\ ([^:]+):\ Downloading ]]; then
                video_id="${BASH_REMATCH[1]}"
                echo "📹 Fetching video: $video_id"
            elif [[ "$line" =~ 100% ]]; then
                current_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
                echo "✅ [$current_count/$NUM_VIDEOS_PER_CATEGORY] Completed: $(echo "$line" | grep -oP '(?<=] ).*' || echo "$line")"
            elif [[ "$line" =~ ERROR ]]; then
                echo "❌ ERROR: $line"
            elif [[ "$line" =~ WARNING.*format ]]; then
                echo "⚠️  WARNING: $line"
            fi
        done
    
    downloaded=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    new_downloads=$((downloaded - videos_before))
    total_downloaded=$((total_downloaded + new_downloads))
    
    echo ""
    echo "=========================================="
    echo "✅ Category complete: $category"
    echo "   Downloaded: $new_downloads new videos"
    echo "   Total: $downloaded videos"
    echo "=========================================="
    echo ""
done

echo "======================================"
echo "✅ All downloads complete!"
echo "📊 Total videos: $total_downloaded"
echo "📁 Location: $OUTPUT_DIR"
echo "======================================"



#!/bin/bash
# Specifically target categories that are below target

set -e

OUTPUT_DIR="datasets/videos"
TARGET=200

echo "🔧 Fixing categories below target..."
echo ""

# Check each category
for category in gaming animation faces text mixed; do
    category_dir="$OUTPUT_DIR/$category"
    
    if [ ! -d "$category_dir" ]; then
        continue
    fi
    
    current=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    needed=$((TARGET - current))
    
    if [ "$needed" -gt 0 ]; then
        echo "📥 $category: $current / $TARGET (need $needed more)"
        
        # Use category-specific search terms
        case $category in
            gaming)
                query="gaming gameplay walkthrough -shorts"
                ;;
            animation)
                query="animation cartoon animated movie -shorts"
                ;;
            faces)
                query="people talking interview vlog -shorts"
                ;;
            text)
                query="screen recording tutorial howto -shorts"
                ;;
            mixed)
                query="nature landscape city travel documentary -shorts"
                ;;
        esac
        
        output_template="$category_dir/%(title)s.%(ext)s"
        
        JS_RUNTIME=""
        if command -v node &> /dev/null; then
            JS_RUNTIME="--js-runtimes node"
        fi
        
        echo "   Searching: $query"
        echo "   Downloading $needed videos..."
        
        yt-dlp \
            "ytsearch${needed}:${query}" \
            -f "22/18/best[height<=720][ext=mp4]/best[ext=mp4]/best" \
            -o "$output_template" \
            --no-playlist \
            --match-filter "duration <= 600 & !is_live & !is_upcoming & duration > 30" \
            --ignore-errors \
            --max-downloads "$needed" \
            --merge-output-format "mp4" \
            --max-filesize 500M \
            --no-warnings \
            $JS_RUNTIME \
            --progress
        
        new_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
        downloaded=$((new_count - current))
        echo "   ✅ Downloaded $downloaded videos (total: $new_count)"
        echo ""
    else
        echo "✅ $category: $current videos (target reached)"
    fi
done

echo "✅ Done!"



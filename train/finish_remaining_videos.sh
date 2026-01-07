#!/bin/bash
# Quick script to finish the last few videos for each category

set -e

OUTPUT_DIR="datasets/videos"
TARGET=200

echo "🎯 Finishing remaining videos..."
echo ""

for category in gaming animation faces text mixed; do
    category_dir="$OUTPUT_DIR/$category"
    
    if [ ! -d "$category_dir" ]; then
        continue
    fi
    
    current=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    needed=$((TARGET - current))
    
    if [ "$needed" -le 0 ]; then
        echo "✅ $category: $current videos (complete)"
        continue
    fi
    
    echo "📥 $category: $current / $TARGET (need $needed more)"
    
    output_template="$category_dir/%(title)s.%(ext)s"
    archive_file="$category_dir/.downloaded_archive.txt"
    touch "$archive_file"
    
    JS_RUNTIME=""
    if command -v node &> /dev/null; then
        JS_RUNTIME="--js-runtimes node"
    fi
    
    # Category-specific diverse search terms with date variations
    case $category in
        gaming)
            queries=("video games 2024" "gaming gameplay 2023" "gameplay video 2022" "gaming moments 2021" "gameplay compilation 2020" "gaming highlights 2019" "video games gameplay" "gaming content" "gameplay video" "gaming moments")
            ;;
        animation)
            queries=("cartoon animation 2024" "animated video 2023" "cartoon video 2022" "animation content 2021" "animated content 2020" "cartoon content 2019" "cartoon animation" "animated video" "cartoon video" "animation content")
            ;;
        faces)
            queries=("people talking 2024" "interview video 2023" "conversation video 2022" "talking people 2021" "people speaking 2020" "person talking 2019" "people talking" "interview video" "conversation video" "talking people")
            ;;
        text)
            queries=("tutorial video 2024" "how to guide 2023" "screen recording 2022" "tutorial content 2021" "how to tutorial 2020" "screen tutorial 2019" "tutorial video" "how to guide" "screen recording" "tutorial content")
            ;;
        mixed)
            queries=("nature video 2024" "travel video 2023" "documentary video 2022" "city video 2021" "landscape video 2020" "scenic video 2019" "nature content 2018" "travel content 2017" "documentary content 2016" "city content 2015" "outdoor video 2014" "adventure video 2013" "nature video" "travel video" "documentary video" "city video")
            ;;
    esac
    
    downloaded_any=false
    
    for query in "${queries[@]}"; do
        if [ "$needed" -le 0 ]; then
            break
        fi
        
        echo "   Trying: $query"
        
        # Try with date filter first, then without
        for search_query in "${query} -shorts" "${query}"; do
            yt-dlp \
                "ytsearch$((needed * 2)):${search_query}" \
                -f "22/18/best[height<=720][ext=mp4]/best[ext=mp4]/best" \
                -o "$output_template" \
                --no-playlist \
                --download-archive "$archive_file" \
                --match-filter "duration <= 900 & !is_live & !is_upcoming & duration > 15" \
                --ignore-errors \
                --max-downloads "$needed" \
                --merge-output-format "mp4" \
                --max-filesize 500M \
                --no-warnings \
                $JS_RUNTIME \
                --progress 2>&1 | grep -E "(download|100%|ERROR)" || true
            
            new_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
            downloaded=$((new_count - current))
            
            if [ "$downloaded" -gt 0 ]; then
                current=$new_count
                break
            fi
        done
        
        if [ "$downloaded" -gt 0 ]; then
            echo "   ✅ +$downloaded videos (total: $current)"
            needed=$((TARGET - current))
            downloaded_any=true
        else
            echo "   ⚠️  No new videos from this query"
        fi
        
        sleep 2
    done
    
    final=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    if [ "$final" -ge "$TARGET" ]; then
        echo "   🎯 $category complete: $final videos"
    else
        echo "   ⚠️  $category: $final / $TARGET videos"
    fi
    echo ""
done

echo "✅ Done!"


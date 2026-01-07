#!/bin/bash
# Continue downloading until all categories reach target count

set -e

echo "🚀 Continuing downloads to reach target counts..."
echo "======================================"

# Configuration
OUTPUT_DIR="datasets/videos"
TARGET_PER_CATEGORY=200
BATCH_SIZE=30  # Smaller batches = more search variety
MAX_BATCHES=50  # Increased limit for stubborn categories

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Categories with extensive search term variations
declare -A CATEGORY_SEARCHES=(
    ["gaming"]="gaming gameplay|esports competitive|game walkthrough|video game review|gaming montage|gameplay highlights|let's play|gameplay compilation|gaming moments|game review|gameplay footage|gaming compilation|gameplay video|gaming content|video games|gameplay montage|gaming highlights|gameplay moments|gaming clips|gameplay clips|gaming stream|gameplay stream"
    ["animation"]="animation cartoon|animated movie|cartoon show|anime episode|animated short film|cartoon series|animated video|cartoon animation|2d animation|3d animation|animated clip|cartoon clip|animation video|cartoon video|animated content|cartoon content|animation film|cartoon film|animated series|cartoon series episode"
    ["faces"]="people talking|interview conversation|portrait vlog|talking head|person speaking|face closeup|interview video|conversation video|talking video|portrait video|person talking|face video|people video|talking people|interview clip|conversation clip|portrait clip|face talking|person video|people speaking|talking person|face portrait"
    ["text"]="screen recording|tutorial guide|presentation slides|how to tutorial|software demo|screen capture|tutorial video|how to guide|software tutorial|screen tutorial|presentation video|demo video|screen share|tutorial content|how to video|software guide|screen video|presentation content|tutorial walkthrough|software walkthrough|screen demo|tutorial content"
    ["mixed"]="nature landscape|city travel|documentary film|travel vlog|nature documentary|city tour|nature video|landscape video|travel video|documentary video|city video|scenic video|nature content|landscape content|travel content|documentary content|city content|scenic content|nature film|travel film|documentary series|city life|nature scenes|travel scenes|landscape scenes|city scenes|nature photography|travel photography|documentary photography"
)

echo ""
echo "Target: $TARGET_PER_CATEGORY videos per category"
echo "Will download in batches of $BATCH_SIZE until targets are reached"
echo ""

total_downloaded=0

for category in "${!CATEGORY_SEARCHES[@]}"; do
    searches="${CATEGORY_SEARCHES[$category]}"
    category_dir="$OUTPUT_DIR/$category"
    mkdir -p "$category_dir"
    
    current_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    needed=$((TARGET_PER_CATEGORY - current_count))
    
    if [ "$needed" -le 0 ]; then
        echo "✅ $category: $current_count videos (target reached)"
        total_downloaded=$((total_downloaded + current_count))
        continue
    fi
    
    echo "=========================================="
    echo "📥 Category: $category"
    echo "   Current: $current_count videos"
    echo "   Needed: $needed more videos"
    echo "=========================================="
    
    output_template="$category_dir/%(title)s.%(ext)s"
    
    JS_RUNTIME=""
    if command -v node &> /dev/null; then
        JS_RUNTIME="--js-runtimes node"
    fi
    
    batch_num=1
    last_count=$current_count
    search_index=1
    
    # Convert search string to array
    IFS='|' read -ra SEARCH_ARRAY <<< "$searches"
    
    while [ "$current_count" -lt "$TARGET_PER_CATEGORY" ] && [ "$batch_num" -le "$MAX_BATCHES" ]; do
        needed=$((TARGET_PER_CATEGORY - current_count))
        to_download=$((needed < BATCH_SIZE ? needed : BATCH_SIZE))
        
        # Rotate through search terms
        search_idx=$(((batch_num - 1) % ${#SEARCH_ARRAY[@]}))
        query="${SEARCH_ARRAY[$search_idx]} -shorts"
        
        echo ""
        echo "   Batch $batch_num: $current_count / $TARGET_PER_CATEGORY videos"
        echo "   Search: $query"
        echo "   Downloading $to_download more..."
        
        # Try downloading with current search term
        # Use --download-archive to skip already downloaded videos
        archive_file="$category_dir/.downloaded_archive.txt"
        touch "$archive_file"
        
        yt-dlp \
            "ytsearch${to_download}:${query}" \
            -f "22/18/best[height<=720][ext=mp4]/best[height<=480][ext=mp4]/best[ext=mp4]/best" \
            -o "$output_template" \
            --no-playlist \
            --download-archive "$archive_file" \
            --match-filter "duration <= 600 & !is_live & !is_upcoming & duration > 20" \
            --ignore-errors \
            --max-downloads "$to_download" \
            --merge-output-format "mp4" \
            --retries 1 \
            --fragment-retries 1 \
            --max-filesize 500M \
            --no-warnings \
            $JS_RUNTIME \
            --progress 2>&1 | tail -3 || true
        
        # Count new videos
        current_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
        downloaded_this_batch=$((current_count - last_count))
        last_count=$current_count
        
        echo "   ✅ Batch $batch_num: +$downloaded_this_batch videos (total: $current_count)"
        
        # If no progress, try alternative search terms
        if [ "$downloaded_this_batch" -eq 0 ]; then
            echo "   ⚠️  No new videos. Trying alternative search terms..."
            
            # Try each alternative search term
            for alt_query in "${SEARCH_ARRAY[@]}"; do
                if [ "$alt_query" = "${SEARCH_ARRAY[$search_idx]}" ]; then
                    continue  # Skip the one we just tried
                fi
                
                echo "   Trying: $alt_query"
                yt-dlp \
                    "ytsearch${to_download}:${alt_query} -shorts" \
                    -f "22/18/best[height<=720][ext=mp4]/best[ext=mp4]/best" \
                    -o "$output_template" \
                    --no-playlist \
                    --download-archive "$archive_file" \
                    --match-filter "duration <= 600 & !is_live & !is_upcoming & duration > 20" \
                    --ignore-errors \
                    --max-downloads "$to_download" \
                    --merge-output-format "mp4" \
                    --max-filesize 500M \
                    --no-warnings \
                    $JS_RUNTIME \
                    --progress 2>&1 | tail -3 || true
                
                current_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
                downloaded_this_batch=$((current_count - last_count))
                last_count=$current_count
                
                if [ "$downloaded_this_batch" -gt 0 ]; then
                    echo "   ✅ Alternative search worked: +$downloaded_this_batch videos"
                    break
                fi
            done
            
            # If still no progress, try without duration filter (but keep other filters)
            if [ "$downloaded_this_batch" -eq 0 ]; then
                echo "   ⚠️  Still no progress. Trying relaxed filters and different search..."
                # Try completely different search terms
                case $category in
                    gaming)
                        relaxed_queries=("video games" "gameplay" "gaming content" "game video")
                        ;;
                    animation)
                        relaxed_queries=("cartoon" "animated" "animation" "cartoon video")
                        ;;
                    faces)
                        relaxed_queries=("people" "talking" "interview" "conversation")
                        ;;
                    text)
                        relaxed_queries=("tutorial" "guide" "how to" "screen")
                        ;;
                    mixed)
                        relaxed_queries=("nature" "travel" "documentary" "city" "landscape" "scenic" "outdoor" "adventure")
                        ;;
                esac
                
                for relaxed_query in "${relaxed_queries[@]}"; do
                    echo "   Trying relaxed: $relaxed_query"
                    yt-dlp \
                        "ytsearch${to_download}:${relaxed_query} -shorts" \
                        -f "22/18/best[height<=720][ext=mp4]/best[ext=mp4]/best" \
                        -o "$output_template" \
                        --no-playlist \
                        --download-archive "$archive_file" \
                        --match-filter "duration <= 900 & !is_live & !is_upcoming & duration > 15" \
                        --ignore-errors \
                        --max-downloads "$to_download" \
                        --merge-output-format "mp4" \
                        --max-filesize 500M \
                        --no-warnings \
                        $JS_RUNTIME \
                        --progress 2>&1 | tail -3 || true
                    
                    current_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
                    downloaded_this_batch=$((current_count - last_count))
                    last_count=$current_count
                    
                    if [ "$downloaded_this_batch" -gt 0 ]; then
                        echo "   ✅ Relaxed search worked: +$downloaded_this_batch videos"
                        break
                    fi
                done
                
                current_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
                downloaded_this_batch=$((current_count - last_count))
                last_count=$current_count
                
                if [ "$downloaded_this_batch" -gt 0 ]; then
                    echo "   ✅ Relaxed filters worked: +$downloaded_this_batch videos"
                fi
            fi
        fi
        
        # Check if target reached
        if [ "$current_count" -ge "$TARGET_PER_CATEGORY" ]; then
            echo "   🎯 Target reached!"
            break
        fi
        
        batch_num=$((batch_num + 1))
        sleep 3  # Small delay between batches
    done
    
    final_count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    total_downloaded=$((total_downloaded + final_count))
    
    if [ "$final_count" -ge "$TARGET_PER_CATEGORY" ]; then
        echo "   ✅ $category complete: $final_count videos"
    else
        echo "   ⚠️  $category partial: $final_count / $TARGET_PER_CATEGORY videos"
    fi
    echo ""
done

echo "======================================"
echo "✅ Download session complete!"
echo "📊 Total videos: $total_downloaded"
echo "📁 Location: $OUTPUT_DIR"
echo "======================================"


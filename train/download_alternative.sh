#!/bin/bash
# Alternative download method using different strategies

set -e

echo "🚀 Alternative video download methods..."
echo "========================================"

OUTPUT_DIR="datasets/videos"
mkdir -p "$OUTPUT_DIR"

# Method 1: Try with different format selection
echo ""
echo "Method 1: Downloading with flexible format selection..."
echo "------------------------------------------------------"

categories=("gaming" "animation" "faces" "text" "mixed")
queries=("gaming gameplay" "animation cartoon" "people talking" "screen recording" "nature landscape")

for i in "${!categories[@]}"; do
    category="${categories[$i]}"
    query="${queries[$i]}"
    category_dir="$OUTPUT_DIR/$category"
    mkdir -p "$category_dir"
    
    echo "📥 $category: $query"
    
    # Try multiple format strategies
    yt-dlp \
        "ytsearch50:${query}" \
        -f "best[height<=720]/worst[height>=360]" \
        -o "$category_dir/%(title)s.%(ext)s" \
        --no-playlist \
        --ignore-errors \
        --max-downloads 50 \
        --merge-output-format "mp4" \
        --retries 2 \
        --progress 2>&1 | grep -E "(Downloading|ERROR|WARNING)" || true
    
    count=$(find "$category_dir" -name "*.mp4" 2>/dev/null | wc -l)
    echo "   ✅ $count videos"
    echo ""
done

total=$(find "$OUTPUT_DIR" -name "*.mp4" 2>/dev/null | wc -l)
echo "========================================"
echo "✅ Total: $total videos downloaded"
echo "========================================"

if [ "$total" -lt 100 ]; then
    echo ""
    echo "⚠️  Low video count. Recommendations:"
    echo "   1. Update yt-dlp: pip install --upgrade yt-dlp"
    echo "   2. Use Pexels API: python download_datasets.py --sources pexels --pexels_api_key YOUR_KEY"
    echo "   3. Use your own videos: Place them in $OUTPUT_DIR/"
fi



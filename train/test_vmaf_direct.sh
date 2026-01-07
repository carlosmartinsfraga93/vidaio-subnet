#!/bin/bash
# Test direct FFmpeg VMAF calculation

echo "🧪 Testing direct FFmpeg VMAF calculation"
echo "=========================================="
echo ""

# Find a test video
VIDEO=$(find datasets/videos -name "*.mp4" | head -1)

if [ -z "$VIDEO" ]; then
    echo "❌ No videos found"
    exit 1
fi

echo "Test video: $(basename "$VIDEO")"
echo ""

# Create a test encoded video
TEMP_DIR=$(mktemp -d)
ENCODED="$TEMP_DIR/test_encoded.mp4"
OUTPUT_JSON="$TEMP_DIR/vmaf_output.json"

echo "1. Encoding test video..."
/venv/main/bin/ffmpeg -y -i "$VIDEO" -c:v av1_nvenc -cq 30 -preset p6 -b:v 0 -an -t 10 "$ENCODED" 2>&1 | tail -3

if [ ! -f "$ENCODED" ]; then
    echo "❌ Encoding failed"
    exit 1
fi

echo "✅ Encoding successful"
echo ""

echo "2. Calculating VMAF with /usr/local/bin/ffmpeg..."
echo "   Using filter_complex to handle resolution differences..."
/usr/local/bin/ffmpeg -y \
    -i "$VIDEO" \
    -i "$ENCODED" \
    -filter_complex "[0:v]setpts=PTS-STARTPTS[ref];[1:v]setpts=PTS-STARTPTS,scale=iw:ih[dist];[ref][dist]libvmaf=log_fmt=json:log_path=$OUTPUT_JSON" \
    -f null - \
    -t 10 2>&1

if [ -f "$OUTPUT_JSON" ]; then
    echo ""
    echo "✅ VMAF calculation successful!"
    echo ""
    echo "VMAF output (first few frames):"
    python3 -c "import json; data=json.load(open('$OUTPUT_JSON')); frames=data.get('frames',[]); scores=[f.get('metrics',{}).get('vmaf',0) for f in frames[:5]]; print(f'Scores: {scores}'); print(f'Average: {sum(scores)/len(scores) if scores else 0:.2f}')" 2>/dev/null || echo "Could not parse JSON"
else
    echo ""
    echo "❌ VMAF calculation failed - no output file"
fi

# Cleanup
rm -rf "$TEMP_DIR"


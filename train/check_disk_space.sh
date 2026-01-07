#!/bin/bash
# Check disk space and estimate if there's enough for training

echo "💾 Disk Space Check"
echo "==================="
echo ""

# Overall disk usage
echo "📊 Overall Disk Usage:"
df -h / | tail -1 | awk '{print "  Total: " $2 "\n  Used:  " $3 " (" $5 ")\n  Free:  " $4}'
echo ""

# Check current directory (workspace)
CURRENT_DIR=$(pwd)
echo "📁 Current Directory: $CURRENT_DIR"
df -h "$CURRENT_DIR" | tail -1 | awk '{print "  Available: " $4}'
echo ""

# Check training directories
echo "📂 Training Directories:"
if [ -d "datasets" ]; then
    echo "  datasets/:"
    du -sh datasets 2>/dev/null | awk '{print "    " $1}'
    if [ -d "datasets/videos" ]; then
        video_count=$(find datasets/videos -name "*.mp4" 2>/dev/null | wc -l)
        video_size=$(du -sh datasets/videos 2>/dev/null | awk '{print $1}')
        echo "    Videos: $video_count files ($video_size)"
    fi
else
    echo "  datasets/: Not created yet"
fi

if [ -d "models" ]; then
    echo "  models/:"
    du -sh models 2>/dev/null | awk '{print "    " $1}'
else
    echo "  models/: Not created yet"
fi
echo ""

# Estimate space needed
echo "💡 Space Requirements:"
echo "  Videos (1000 videos, 360p-720p): ~50-100 GB"
echo "  Training data (processed): ~10-20 GB"
echo "  Models (trained): ~500 MB - 2 GB"
echo "  Total estimated: ~60-120 GB"
echo ""

# Check if enough space
AVAILABLE=$(df -h "$CURRENT_DIR" | tail -1 | awk '{print $4}' | sed 's/[^0-9.]//g')
AVAILABLE_GB=$(echo "$AVAILABLE" | sed 's/[^0-9.]//g')

# Simple check (if available space contains "G" or is > 100)
if df -h "$CURRENT_DIR" | tail -1 | grep -q "G"; then
    AVAILABLE_NUM=$(df -h "$CURRENT_DIR" | tail -1 | awk '{print $4}' | sed 's/G//')
    if (( $(echo "$AVAILABLE_NUM > 100" | bc -l 2>/dev/null || echo "0") )); then
        echo "✅ Sufficient disk space available"
    elif (( $(echo "$AVAILABLE_NUM > 50" | bc -l 2>/dev/null || echo "0") )); then
        echo "⚠️  Moderate disk space - may need to clean up after training"
    else
        echo "❌ Low disk space - consider:"
        echo "   1. Reducing number of videos"
        echo "   2. Using lower quality videos"
        echo "   3. Cleaning up after each training step"
    fi
else
    echo "⚠️  Check available space manually"
fi

echo ""
echo "🔍 Quick Commands:"
echo "  df -h              # Show all disk usage"
echo "  du -sh datasets/   # Show datasets folder size"
echo "  du -sh models/     # Show models folder size"



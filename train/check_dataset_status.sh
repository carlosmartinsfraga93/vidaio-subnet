#!/bin/bash
# Check current dataset status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DATA_DIR="datasets/vmaf_pipeline"

echo "📊 Dataset Status Check"
echo "======================"
echo ""

if [ ! -f "$DATA_DIR/vmaf_dataset.csv" ]; then
    echo "❌ Dataset file not found: $DATA_DIR/vmaf_dataset.csv"
    echo ""
    echo "💡 Run data preparation first:"
    echo "   python prepare_preprocessing_pipeline_data.py --data_dir datasets/videos --output_dir $DATA_DIR"
    exit 1
fi

# Count samples
SAMPLE_COUNT=$(tail -n +2 "$DATA_DIR/vmaf_dataset.csv" | wc -l)
FILE_SIZE=$(du -h "$DATA_DIR/vmaf_dataset.csv" | cut -f1)

echo "✅ Dataset file exists: $DATA_DIR/vmaf_dataset.csv"
echo "   Samples: $SAMPLE_COUNT"
echo "   File size: $FILE_SIZE"
echo ""

# Check if data preparation is running
if pgrep -f "prepare_preprocessing_pipeline_data.py" > /dev/null; then
    echo "⚠️  Data preparation script is currently running!"
    echo "   The CSV file may be overwritten when it finishes."
    echo ""
    echo "💡 Safe options:"
    echo "   1. Wait for data preparation to finish"
    echo "   2. Use train_with_existing_data.sh (creates safe copy)"
    echo "   3. Copy CSV manually: cp $DATA_DIR/vmaf_dataset.csv $DATA_DIR/vmaf_dataset_backup.csv"
else
    echo "✅ No data preparation script running"
    echo "   Safe to train with current dataset"
fi

echo ""

# Recommendations
if [ "$SAMPLE_COUNT" -lt 100 ]; then
    echo "❌ Very few samples ($SAMPLE_COUNT)"
    echo "   Recommendation: Wait for more data (target: 1000+ samples)"
elif [ "$SAMPLE_COUNT" -lt 500 ]; then
    echo "⚠️  Few samples ($SAMPLE_COUNT)"
    echo "   Can train, but more samples recommended (target: 1000+ samples)"
    echo "   Expected performance: Moderate"
elif [ "$SAMPLE_COUNT" -lt 1000 ]; then
    echo "✅ Good sample count ($SAMPLE_COUNT)"
    echo "   Can train with good results"
    echo "   More samples will improve performance (target: 2000+ samples)"
else
    echo "✅ Excellent sample count ($SAMPLE_COUNT)"
    echo "   Ready for training with best results"
fi

echo ""
echo "📈 Training recommendations:"
echo "   - Minimum: 100 samples (may overfit)"
echo "   - Good: 500-1000 samples"
echo "   - Best: 2000+ samples"
echo ""
echo "🚀 To train with current dataset:"
echo "   ./train_with_existing_data.sh"





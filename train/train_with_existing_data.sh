#!/bin/bash
# Safe training script that uses existing CSV without conflicts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
DATA_DIR="datasets/vmaf_pipeline"
MODEL_VERSION="${MODEL_VERSION:-$(date +%Y%m%d_%H%M%S)}"
MODELS_DIR="models/v${MODEL_VERSION}"

echo "🚀 Training with existing dataset (safe mode)"
echo "============================================"
echo ""

# Check if CSV exists
if [ ! -f "$DATA_DIR/vmaf_dataset.csv" ]; then
    echo "❌ Dataset file not found: $DATA_DIR/vmaf_dataset.csv"
    echo "   Run prepare_preprocessing_pipeline_data.py first"
    exit 1
fi

# Count samples
SAMPLE_COUNT=$(tail -n +2 "$DATA_DIR/vmaf_dataset.csv" | wc -l)
echo "📊 Dataset found: $SAMPLE_COUNT samples"

if [ "$SAMPLE_COUNT" -lt 100 ]; then
    echo "⚠️  Warning: Very few samples ($SAMPLE_COUNT). Model may not train well."
    read -p "   Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
elif [ "$SAMPLE_COUNT" -lt 500 ]; then
    echo "⚠️  Warning: Few samples ($SAMPLE_COUNT). Consider waiting for more data."
    echo "   (Recommended: 1000+ samples for best results)"
    read -p "   Continue with current samples? (y/n, default=y): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "   ✅ Proceeding with $SAMPLE_COUNT samples..."
    else
        exit 1
    fi
else
    echo "✅ Sufficient samples for training"
fi

# Create safe copy of CSV (in case data preparation is still running)
SAFE_DATA_DIR="$DATA_DIR/safe_copy_${MODEL_VERSION}"
mkdir -p "$SAFE_DATA_DIR"
echo ""
echo "📋 Creating safe copy of dataset..."
cp "$DATA_DIR/vmaf_dataset.csv" "$SAFE_DATA_DIR/vmaf_dataset.csv"
if [ -f "$DATA_DIR/summary.json" ]; then
    cp "$DATA_DIR/summary.json" "$SAFE_DATA_DIR/summary.json"
fi
echo "   ✅ Safe copy created: $SAFE_DATA_DIR/vmaf_dataset.csv"

# Create models directory
mkdir -p "$MODELS_DIR"

# Train preprocessing pipeline
echo ""
echo "🎯 Training preprocessing pipeline..."
echo "-------------------------------------"
echo "   Model: Gradient Boosting (200 estimators)"
echo "   Output: $MODELS_DIR/preprocessing_pipeline.pkl"
echo "   Samples: $SAMPLE_COUNT"
echo ""

python train_preprocessing_pipeline.py \
    --data_dir "$SAFE_DATA_DIR" \
    --output "$MODELS_DIR/preprocessing_pipeline.pkl" \
    --model_type gradient_boosting \
    --n_estimators 200 \
    --test_size 0.2

# Extract model information
echo ""
echo "📝 Extracting model information..."
python extract_model_info.py \
    --models_dir "$MODELS_DIR" \
    --output "$MODELS_DIR/version_info.json"

echo ""
echo "✅ Training complete!"
echo "   Model saved to: $MODELS_DIR/preprocessing_pipeline.pkl"
echo "   Version info: $MODELS_DIR/version_info.json"
echo ""
echo "💡 To use this model, copy it to services/compress/models/:"
echo "   cp $MODELS_DIR/preprocessing_pipeline.pkl ../services/compress/models/"





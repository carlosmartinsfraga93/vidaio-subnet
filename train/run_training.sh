#!/bin/bash
# Complete training pipeline script

set -e

# Redirect output to log file if LOG_FILE is set
if [ -n "$LOG_FILE" ]; then
    exec > >(tee -a "$LOG_FILE") 2>&1
fi

echo "🚀 Starting compression model training pipeline..."
echo "=================================================="

# Configuration
DATA_DIR="datasets/videos"
SCENE_DATA_DIR="datasets/scene_classifier"
PIPELINE_DATA_DIR="datasets/vmaf_pipeline"
BASE_MODELS_DIR="models"

# Versioning: Use provided version or generate timestamp-based version
if [ -z "$MODEL_VERSION" ]; then
    MODEL_VERSION="v$(date +%Y%m%d_%H%M%S)"
fi

MODELS_DIR="$BASE_MODELS_DIR/$MODEL_VERSION"
NUM_VIDEOS=5000

echo "📦 Model version: $MODEL_VERSION"
echo "📁 Models will be saved to: $MODELS_DIR"
echo ""

# Step 1: Download datasets
echo ""
echo "Step 1: Downloading datasets..."
echo "--------------------------------"
if [ ! -d "$DATA_DIR" ] || [ -z "$(find $DATA_DIR -name "*.mp4" -o -name "*.avi" -o -name "*.mov" 2>/dev/null | head -1)" ]; then
    echo "No videos found. Downloading videos..."
    echo ""
    echo "Option 1: Use simple download script (recommended)"
    echo "  ./download_videos_simple.sh"
    echo ""
    echo "Option 2: Use Python download script"
    echo "  python download_datasets.py --sources youtube --num_videos $NUM_VIDEOS --output_dir $DATA_DIR"
    echo ""
    echo "⚠️  Please download videos first, then run this script again."
    echo "   Or run: ./download_videos_simple.sh"
    exit 1
else
    video_count=$(find $DATA_DIR -name "*.mp4" -o -name "*.avi" -o -name "*.mov" 2>/dev/null | wc -l)
    echo "Found $video_count videos in dataset, skipping download..."
fi

# Step 2: Prepare scene classifier data
echo ""
echo "Step 2: Preparing scene classifier data..."
echo "------------------------------------------"
if [ -f "$SCENE_DATA_DIR/dataset.pkl" ] || [ -f "$SCENE_DATA_DIR/train_dataset.pkl" ]; then
    echo "✅ Scene classifier dataset already exists"
    echo "   Found: $SCENE_DATA_DIR/dataset.pkl or train_dataset.pkl"
    read -p "   Skip dataset preparation? (y/n, default=y): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "   ⏭️  Skipping scene classifier data preparation..."
    else
        echo "   🔄 Reprocessing scene classifier data..."
        python prepare_scene_classifier_data.py \
            --data_dir $DATA_DIR \
            --output_dir $SCENE_DATA_DIR
    fi
else
    echo "   📊 Preparing scene classifier dataset..."
    python prepare_scene_classifier_data.py \
        --data_dir $DATA_DIR \
        --output_dir $SCENE_DATA_DIR
fi

# Step 3: Train scene classifier
echo ""
echo "Step 3: Training scene classifier..."
echo "------------------------------------"
echo "   Model: EfficientNet V2 S (best performance)"
echo "   Output: $MODELS_DIR/scene_classifier_model.pth"
mkdir -p "$MODELS_DIR"
python train_scene_classifier.py \
    --data_dir $SCENE_DATA_DIR \
    --output_dir $MODELS_DIR \
    --model efficientnet_v2_s \
    --epochs 50 \
    --batch_size 32 \
    --learning_rate 0.001

# Step 4: Prepare preprocessing pipeline data
echo ""
echo "Step 4: Preparing preprocessing pipeline data..."
echo "------------------------------------------------"
if [ -f "$PIPELINE_DATA_DIR/vmaf_dataset.csv" ]; then
    echo "✅ Preprocessing pipeline dataset already exists"
    echo "   Found: $PIPELINE_DATA_DIR/vmaf_dataset.csv"
    read -p "   Skip dataset preparation? (y/n, default=y): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "   ⏭️  Skipping preprocessing pipeline data preparation..."
    else
        echo "   ⚠️  This step takes a long time (encoding videos)..."
        echo "   🔄 Reprocessing preprocessing pipeline data..."
        python prepare_preprocessing_pipeline_data.py \
            --data_dir $DATA_DIR \
            --output_dir $PIPELINE_DATA_DIR \
            --max_videos 500 \
            --max_encodings_per_video 10
    fi
else
    echo "   ⚠️  This step takes a long time (encoding videos)..."
    echo "   📊 Preparing preprocessing pipeline dataset..."
    python prepare_preprocessing_pipeline_data.py \
        --data_dir $DATA_DIR \
        --output_dir $PIPELINE_DATA_DIR \
        --max_videos 500 \
        --max_encodings_per_video 10 \
        --max_duration 600
fi

# Step 5: Train preprocessing pipeline
echo ""
echo "Step 5: Training preprocessing pipeline..."
echo "------------------------------------------"
echo "   Model: Gradient Boosting (200 estimators)"
echo "   Output: $MODELS_DIR/preprocessing_pipeline.pkl"
python train_preprocessing_pipeline.py \
    --data_dir $PIPELINE_DATA_DIR \
    --output $MODELS_DIR/preprocessing_pipeline.pkl \
    --model_type gradient_boosting \
    --n_estimators 200

# Step 6: Extract model information and create version info file
echo ""
echo "Step 6: Extracting model information..."
echo "---------------------------------------"
VERSION_INFO_FILE="$MODELS_DIR/version_info.json"

# Count dataset samples
TOTAL_VIDEOS=$(find $DATA_DIR -name "*.mp4" -o -name "*.avi" -o -name "*.mov" 2>/dev/null | wc -l)
SCENE_SAMPLES=$(find $SCENE_DATA_DIR -name "*.pkl" 2>/dev/null | wc -l)
PIPELINE_SAMPLES=$(find $PIPELINE_DATA_DIR -name "*.csv" 2>/dev/null | wc -l)

# Extract detailed model information using Python script
python extract_model_info.py \
    --models_dir "$MODELS_DIR" \
    --output "$VERSION_INFO_FILE" \
    --version "$MODEL_VERSION" 2>/dev/null || {
    # Fallback if extraction fails - create basic version info
    echo "⚠️  Model extraction failed, creating basic version info..."
    cat > "$VERSION_INFO_FILE" << EOF
{
    "version": "$MODEL_VERSION",
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "models": {
        "scene_classifier": {
            "file": "scene_classifier_model.pth",
            "type": "EfficientNet V2 S",
            "architecture": "CombinedModel (image features + video metrics)",
            "classes": 6,
            "training_config": {
                "epochs": 50,
                "batch_size": 32,
                "learning_rate": 0.001
            }
        },
        "preprocessing_pipeline": {
            "file": "preprocessing_pipeline.pkl",
            "type": "Gradient Boosting",
            "n_estimators": 200,
            "purpose": "VMAF prediction for optimal CQ selection"
        }
    },
    "dataset": {
        "total_videos": $TOTAL_VIDEOS,
        "scene_classifier_samples": $SCENE_SAMPLES,
        "pipeline_samples": $PIPELINE_SAMPLES
    }
}
EOF
}

# Add dataset information to version info if it exists
if [ -f "$VERSION_INFO_FILE" ]; then
    python3 << PYEOF
import json
import sys

version_file = "$VERSION_INFO_FILE"
try:
    with open(version_file, 'r') as f:
        data = json.load(f)
    
    # Add dataset information
    if 'dataset' not in data:
        data['dataset'] = {}
    data['dataset']['total_videos'] = $TOTAL_VIDEOS
    data['dataset']['scene_classifier_samples'] = $SCENE_SAMPLES
    data['dataset']['pipeline_samples'] = $PIPELINE_SAMPLES
    
    # Add training configuration
    if 'training_config' not in data:
        data['training_config'] = {
            "scene_classifier": {
                "epochs": 50,
                "batch_size": 32,
                "learning_rate": 0.001,
                "model": "efficientnet_v2_s"
            },
            "preprocessing_pipeline": {
                "model_type": "gradient_boosting",
                "n_estimators": 200
            }
        }
    
    with open(version_file, 'w') as f:
        json.dump(data, f, indent=2)
except Exception as e:
    print(f"Warning: Could not update version info: {e}", file=sys.stderr)
PYEOF
fi

echo "✅ Version info saved to: $VERSION_INFO_FILE"

echo ""
echo "=================================================="
echo "✅ Training pipeline complete!"
echo "=================================================="
echo ""
echo "📦 Model Version: $MODEL_VERSION"
echo "📁 Models saved to: $MODELS_DIR"
echo ""
echo "Trained models:"
echo "  ✅ $MODELS_DIR/scene_classifier_model.pth"
echo "     - Type: EfficientNet V2 S"
echo "     - Purpose: Scene classification (6 categories)"
echo ""
echo "  ✅ $MODELS_DIR/preprocessing_pipeline.pkl"
echo "     - Type: Gradient Boosting (200 estimators)"
echo "     - Purpose: VMAF prediction for CQ optimization"
echo ""
echo "📋 Version info: $VERSION_INFO_FILE"
echo ""
echo "💡 To use these models, copy them to services/compress/models/:"
echo "   cp $MODELS_DIR/scene_classifier_model.pth ../services/compress/models/"
echo "   cp $MODELS_DIR/preprocessing_pipeline.pkl ../services/compress/models/"
echo ""


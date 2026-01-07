#!/bin/bash
# Monitor training progress

set -e

MODELS_DIR="${MODELS_DIR:-models}"
VERSION="${MODEL_VERSION:-latest}"

# Find latest version if not specified
if [ "$VERSION" = "latest" ]; then
    if [ -d "$MODELS_DIR" ]; then
        VERSION=$(ls -t "$MODELS_DIR" 2>/dev/null | head -1)
    else
        echo "❌ No models directory found"
        exit 1
    fi
fi

VERSION_DIR="$MODELS_DIR/$VERSION"

echo "📊 Training Progress Monitor"
echo "============================"
echo "Version: $VERSION"
echo "Directory: $VERSION_DIR"
echo ""

# Check if training is in progress
if [ ! -d "$VERSION_DIR" ]; then
    echo "⚠️  Version directory not found. Training may not have started."
    exit 1
fi

# Scene Classifier Progress
echo "🎯 Scene Classifier Training"
echo "----------------------------"
SCENE_MODEL="$VERSION_DIR/scene_classifier_model.pth"
SCENE_HISTORY="$VERSION_DIR/training_history.json"

if [ -f "$SCENE_MODEL" ]; then
    echo "✅ Model file exists"
    
    # Try to extract checkpoint info
    if command -v python3 &> /dev/null; then
        python3 << PYEOF
import torch
import json
import sys

try:
    checkpoint = torch.load("$SCENE_MODEL", map_location='cpu')
    epoch = checkpoint.get('epoch', 'unknown')
    val_acc = checkpoint.get('best_val_acc', 'unknown')
    model_type = checkpoint.get('model_type', 'unknown')
    
    print(f"   Epoch: {epoch}")
    print(f"   Best Val Accuracy: {val_acc:.2f}%" if isinstance(val_acc, (int, float)) else f"   Best Val Accuracy: {val_acc}")
    print(f"   Model: {model_type}")
    
    # Check training history
    try:
        with open("$SCENE_HISTORY", 'r') as f:
            history = json.load(f)
        if history:
            last = history[-1]
            print(f"   Last Epoch - Train Acc: {last.get('train_acc', 'N/A'):.2f}%, Val Acc: {last.get('val_acc', 'N/A'):.2f}%")
            print(f"   Total Epochs Completed: {len(history)}")
    except:
        pass
except Exception as e:
    print(f"   ⚠️  Could not read checkpoint: {e}")
PYEOF
    else
        echo "   ⚠️  Python not available for detailed info"
    fi
else
    echo "⏳ Model not yet created (training in progress or not started)"
fi

# Check training history file
if [ -f "$SCENE_HISTORY" ]; then
    echo ""
    echo "📈 Training History:"
    if command -v python3 &> /dev/null; then
        python3 << PYEOF
import json
try:
    with open("$SCENE_HISTORY", 'r') as f:
        history = json.load(f)
    if history:
        print(f"   Total epochs: {len(history)}")
        if len(history) > 0:
            last = history[-1]
            print(f"   Latest - Epoch {last.get('epoch', 'N/A')}:")
            print(f"     Train Loss: {last.get('train_loss', 'N/A'):.4f}, Train Acc: {last.get('train_acc', 'N/A'):.2f}%")
            print(f"     Val Loss: {last.get('val_loss', 'N/A'):.4f}, Val Acc: {last.get('val_acc', 'N/A'):.2f}%")
        
        # Show best epoch
        if len(history) > 0:
            best_val_acc = max(h.get('val_acc', 0) for h in history)
            best_epoch = next((h for h in history if h.get('val_acc') == best_val_acc), None)
            if best_epoch:
                print(f"   Best - Epoch {best_epoch.get('epoch', 'N/A')}: Val Acc: {best_epoch.get('val_acc', 'N/A'):.2f}%")
except Exception as e:
    print(f"   ⚠️  Error reading history: {e}")
PYEOF
    fi
fi

echo ""
echo "🔧 Preprocessing Pipeline Training"
echo "-----------------------------------"
PIPELINE_MODEL="$VERSION_DIR/preprocessing_pipeline.pkl"
PIPELINE_METADATA="$VERSION_DIR/pipeline_metadata.json"
PIPELINE_EVAL="$VERSION_DIR/pipeline_evaluation.json"

if [ -f "$PIPELINE_MODEL" ]; then
    echo "✅ Pipeline model exists"
    
    if [ -f "$PIPELINE_METADATA" ]; then
        if command -v python3 &> /dev/null; then
            python3 << PYEOF
import json
try:
    with open("$PIPELINE_METADATA", 'r') as f:
        metadata = json.load(f)
    print(f"   Model Type: {metadata.get('model_type', 'N/A')}")
    print(f"   Estimators: {metadata.get('n_estimators', 'N/A')}")
    print(f"   Training Samples: {metadata.get('training_samples', 'N/A')}")
    print(f"   Test Samples: {metadata.get('test_samples', 'N/A')}")
except Exception as e:
    print(f"   ⚠️  Error reading metadata: {e}")
PYEOF
        fi
    fi
    
    if [ -f "$PIPELINE_EVAL" ]; then
        echo ""
        echo "📊 Evaluation Metrics:"
        if command -v python3 &> /dev/null; then
            python3 << PYEOF
import json
try:
    with open("$PIPELINE_EVAL", 'r') as f:
        eval_data = json.load(f)
    print(f"   MAE:  {eval_data.get('mae', 'N/A'):.4f}")
    print(f"   MSE:  {eval_data.get('mse', 'N/A'):.4f}")
    print(f"   RMSE: {eval_data.get('rmse', 'N/A'):.4f}")
    print(f"   R²:   {eval_data.get('r2', 'N/A'):.4f}")
except Exception as e:
    print(f"   ⚠️  Error reading evaluation: {e}")
PYEOF
        fi
    fi
else
    echo "⏳ Pipeline model not yet created"
    
    # Check if data preparation is in progress
    PIPELINE_DATA_DIR="datasets/vmaf_pipeline"
    if [ -d "$PIPELINE_DATA_DIR" ]; then
        CSV_COUNT=$(find "$PIPELINE_DATA_DIR" -name "*.csv" 2>/dev/null | wc -l)
        echo "   Data files prepared: $CSV_COUNT"
    fi
fi

echo ""
echo "📁 Files in version directory:"
ls -lh "$VERSION_DIR" 2>/dev/null | tail -n +2 | awk '{print "   " $9 " (" $5 ")"}'

echo ""
echo "💡 Tips:"
echo "   - Run this script periodically: watch -n 60 ./monitor_training.sh"
echo "   - Check specific version: MODEL_VERSION=v1.0.0 ./monitor_training.sh"
echo "   - View full history: cat $VERSION_DIR/training_history.json | python3 -m json.tool"


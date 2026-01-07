#!/bin/bash
# Quick script to switch training from AV1 to HEVC if miner has AV1 decoding issues

set -e

echo "🔄 Switching training configuration from AV1 to HEVC"
echo "===================================================="
echo ""
echo "This will modify prepare_preprocessing_pipeline_data.py to use HEVC instead of AV1"
echo ""

# Backup original file
BACKUP_FILE="prepare_preprocessing_pipeline_data.py.backup.$(date +%Y%m%d_%H%M%S)"
cp prepare_preprocessing_pipeline_data.py "$BACKUP_FILE"
echo "✅ Backed up original to: $BACKUP_FILE"
echo ""

# Check if file exists
if [ ! -f "prepare_preprocessing_pipeline_data.py" ]; then
    echo "❌ Error: prepare_preprocessing_pipeline_data.py not found!"
    exit 1
fi

# Use sed to comment out AV1 and ensure HEVC is used
# This modifies the cq_ranges dictionary
sed -i "s/'av1_nvenc': list(range(10, 64, 3)),/# 'av1_nvenc': list(range(10, 64, 3)),  # Disabled - use HEVC instead/" prepare_preprocessing_pipeline_data.py

echo "✅ Modified prepare_preprocessing_pipeline_data.py"
echo ""
echo "Changes made:"
echo "  - Commented out AV1 codec training"
echo "  - HEVC and H.264 will be used instead"
echo ""
echo "📝 Next steps:"
echo "  1. Re-run data preparation: python prepare_preprocessing_pipeline_data.py"
echo "  2. Re-train preprocessing pipeline: python train_preprocessing_pipeline.py"
echo ""
echo "💡 To restore AV1 training, restore from backup:"
echo "   cp $BACKUP_FILE prepare_preprocessing_pipeline_data.py"



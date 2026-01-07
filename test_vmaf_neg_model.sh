#!/bin/bash
# Test if VMAF NEG model is accessible

echo "=================================="
echo "Testing VMAF NEG Model"
echo "=================================="
echo ""

# Test 1: Check if model file exists
echo "1. Checking model file..."
if [ -f "/usr/local/share/vmaf/model/vmaf_v0.6.1neg.json" ]; then
    echo "   ✅ Model file found: /usr/local/share/vmaf/model/vmaf_v0.6.1neg.json"
    ls -lh /usr/local/share/vmaf/model/vmaf_v0.6.1neg.json
else
    echo "   ❌ Model file NOT found"
fi
echo ""

# Test 2: List all VMAF models in the directory
echo "2. Available VMAF models:"
ls -lh /usr/local/share/vmaf/model/ 2>/dev/null || echo "   Directory not found"
echo ""

# Test 3: Check if vmaf tool can use the model
echo "3. Testing VMAF tool with NEG model..."
echo "   (This will fail without input files, but should show if model is recognized)"
vmaf --model version=vmaf_v0.6.1neg 2>&1 | head -5
echo ""

echo "=================================="
echo "Test Complete"
echo "=================================="


#!/usr/bin/env python3
"""
Test if VMAF NEG model is accessible and working.
"""

import os
import subprocess

print("="*80)
print("🧪 Testing VMAF NEG Model Access")
print("="*80)
print()

# Test 1: Check if model file exists
print("1. Checking model file locations...")
model_paths = [
    "/usr/local/share/vmaf/model/vmaf_v0.6.1neg.json",
    "/usr/share/vmaf/model/vmaf_v0.6.1neg.json",
    "./models/vmaf/vmaf_v0.6.1neg.json",
    "services/compress/models/vmaf/vmaf_v0.6.1neg.json"
]

found_model = None
for model_path in model_paths:
    if os.path.exists(model_path):
        size = os.path.getsize(model_path)
        print(f"   ✅ Found: {model_path} ({size:,} bytes)")
        found_model = model_path
    else:
        print(f"   ❌ Not found: {model_path}")

print()

if not found_model:
    print("❌ ERROR: VMAF NEG model not found!")
    print("   Run: python install_vmaf_neg_model.py")
    exit(1)

# Test 2: Test VMAF tool with the model
print("2. Testing VMAF tool with NEG model...")
print(f"   Using model: {found_model}")
print()

# This will fail because we don't have input files, but it will show if the model is recognized
cmd = ['vmaf', '--model', f'path={found_model}']
result = subprocess.run(cmd, capture_output=True, text=True)

if "no such built-in model" in result.stderr.lower():
    print("   ❌ VMAF tool cannot find the model")
    print(f"   Error: {result.stderr}")
elif "reference" in result.stderr.lower() or "required" in result.stderr.lower():
    print("   ✅ VMAF tool recognized the model!")
    print("   (Error is expected - we didn't provide input files)")
else:
    print(f"   ⚠️  Unexpected output:")
    print(f"   {result.stderr}")

print()
print("="*80)
print("✅ Test Complete")
print("="*80)
print()
print("📋 Summary:")
print(f"   Model file: {found_model}")
print(f"   Status: {'✅ Ready' if found_model else '❌ Not installed'}")
print()


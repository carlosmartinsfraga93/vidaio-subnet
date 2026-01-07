#!/usr/bin/env python3
"""
Download and install VMAF NEG model for validator compatibility.

The VMAF NEG model (vmaf_v0.6.1neg) is used by validators to score videos.
This script downloads the model from Netflix's VMAF GitHub repository.
"""

import os
import sys
import urllib.request
import json

# Model URLs from Netflix VMAF GitHub
VMAF_NEG_JSON_URL = "https://raw.githubusercontent.com/Netflix/vmaf/master/model/vmaf_v0.6.1neg.json"
VMAF_NEG_PKL_URL = "https://raw.githubusercontent.com/Netflix/vmaf/master/model/vmaf_float_v0.6.1neg.pkl"
VMAF_NEG_PKL_MODEL_URL = "https://raw.githubusercontent.com/Netflix/vmaf/master/model/vmaf_float_v0.6.1neg.pkl.model"

# Installation directories (try multiple locations)
INSTALL_DIRS = [
    "/usr/local/share/vmaf/model",
    "/usr/share/vmaf/model",
    "./models/vmaf",
    "services/compress/models/vmaf"
]

def download_file(url, dest_path):
    """Download a file from URL to destination path."""
    print(f"📥 Downloading: {url}")
    print(f"   → {dest_path}")
    
    try:
        urllib.request.urlretrieve(url, dest_path)
        file_size = os.path.getsize(dest_path)
        print(f"   ✅ Downloaded ({file_size:,} bytes)")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def install_vmaf_neg_model():
    """Download and install VMAF NEG model files."""
    print("="*80)
    print("🎬 VMAF NEG Model Installer")
    print("="*80)
    print()
    
    # Find writable installation directory
    install_dir = None
    for dir_path in INSTALL_DIRS:
        try:
            os.makedirs(dir_path, exist_ok=True)
            # Test if writable
            test_file = os.path.join(dir_path, ".test_write")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            install_dir = dir_path
            print(f"✅ Using installation directory: {install_dir}")
            break
        except Exception as e:
            print(f"⚠️  Cannot use {dir_path}: {e}")
    
    if not install_dir:
        print()
        print("❌ ERROR: No writable installation directory found!")
        print()
        print("Please create one of these directories with write permissions:")
        for dir_path in INSTALL_DIRS:
            print(f"   - {dir_path}")
        return False
    
    print()
    print("📦 Downloading VMAF NEG model files...")
    print()
    
    # Download JSON model (main model file)
    json_path = os.path.join(install_dir, "vmaf_v0.6.1neg.json")
    if not download_file(VMAF_NEG_JSON_URL, json_path):
        return False
    
    # Download PKL model (optional, for compatibility)
    pkl_path = os.path.join(install_dir, "vmaf_float_v0.6.1neg.pkl")
    download_file(VMAF_NEG_PKL_URL, pkl_path)
    
    # Download PKL.model file (optional, for compatibility)
    pkl_model_path = os.path.join(install_dir, "vmaf_float_v0.6.1neg.pkl.model")
    download_file(VMAF_NEG_PKL_MODEL_URL, pkl_model_path)
    
    print()
    print("="*80)
    print("✅ VMAF NEG Model Installation Complete!")
    print("="*80)
    print()
    print(f"📁 Model location: {install_dir}")
    print()
    print("📋 Installed files:")
    for filename in os.listdir(install_dir):
        if 'vmaf' in filename.lower():
            filepath = os.path.join(install_dir, filename)
            size = os.path.getsize(filepath)
            print(f"   ✅ {filename} ({size:,} bytes)")
    
    print()
    print("🔧 Configuration:")
    print(f"   Add this to your config:")
    print(f"   'vmafneg_model': '{json_path}'")
    print()
    
    return True

if __name__ == "__main__":
    success = install_vmaf_neg_model()
    sys.exit(0 if success else 1)


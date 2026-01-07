#!/usr/bin/env python3
"""
Miner Readiness Check
Verifies all prerequisites for compression mining
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def check_item(description, check_func):
    """Run a check and print result"""
    print(f"Checking: {description}...", end=" ")
    try:
        result, message = check_func()
        if result:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ {message}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            return True, f"Installed ({version.split()[2]})"
        return False, "Not found"
    except FileNotFoundError:
        return False, "Not installed"
    except Exception as e:
        return False, str(e)


def check_vmaf():
    """Check if VMAF filter is available in FFmpeg"""
    try:
        result = subprocess.run(['ffmpeg', '-filters'], capture_output=True, text=True, timeout=5)
        if 'vmaf' in result.stdout.lower():
            return True, "VMAF filter available"
        return False, "VMAF filter not found"
    except Exception as e:
        return False, str(e)


def check_gpu_encoding():
    """Check if GPU encoding is available"""
    try:
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=5)
        encoders = result.stdout.lower()
        
        gpu_encoders = []
        if 'h264_nvenc' in encoders:
            gpu_encoders.append('NVENC')
        if 'hevc_nvenc' in encoders:
            gpu_encoders.append('HEVC_NVENC')
        if 'av1_nvenc' in encoders:
            gpu_encoders.append('AV1_NVENC')
        
        if gpu_encoders:
            return True, f"Available ({', '.join(gpu_encoders)})"
        return False, "No GPU encoders found (CPU encoding only)"
    except Exception as e:
        return False, str(e)


def check_python_packages():
    """Check if required Python packages are installed"""
    required = ['torch', 'fastapi', 'aiohttp', 'loguru', 'bittensor']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if not missing:
        return True, "All required packages installed"
    return False, f"Missing: {', '.join(missing)}"


def check_scene_classifier_model():
    """Check if scene classifier model exists"""
    model_path = Path("services/compress/models/scene_classifier_model.pth")
    
    if model_path.exists():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        return True, f"Found ({size_mb:.1f} MB)"
    return False, "Model not found"


def check_compression_service():
    """Check if compression service is running"""
    try:
        import requests
        response = requests.get("http://localhost:29116/health", timeout=3)
        if response.status_code == 200:
            return True, "Running on port 29116"
        return False, f"Unexpected status: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Not running (start with: python services/compress/server.py)"
    except Exception as e:
        return False, str(e)


def check_storage_config():
    """Check if storage is configured"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from vidaio_subnet_core import CONFIG
        
        # Check if storage client is configured
        if hasattr(CONFIG, 'storage') and CONFIG.storage:
            return True, "Storage configured"
        return False, "Storage not configured in CONFIG"
    except Exception as e:
        return False, f"Config error: {e}"


def check_disk_space():
    """Check available disk space"""
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb = free // (2**30)
        
        if free_gb > 50:
            return True, f"{free_gb} GB available"
        elif free_gb > 20:
            return True, f"⚠️  {free_gb} GB available (low)"
        return False, f"Only {free_gb} GB available (need at least 20 GB)"
    except Exception as e:
        return False, str(e)


def main():
    print_header("COMPRESSION MINER READINESS CHECK")
    
    checks = [
        ("FFmpeg Installation", check_ffmpeg),
        ("VMAF Support", check_vmaf),
        ("GPU Encoding", check_gpu_encoding),
        ("Python Packages", check_python_packages),
        ("Scene Classifier Model", check_scene_classifier_model),
        ("Compression Service", check_compression_service),
        ("Storage Configuration", check_storage_config),
        ("Disk Space", check_disk_space),
    ]
    
    results = []
    for description, check_func in checks:
        result = check_item(description, check_func)
        results.append((description, result))
    
    # Summary
    print_header("SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Checks Passed: {passed}/{total}\n")
    
    if passed == total:
        print("🎉 ALL CHECKS PASSED!")
        print("\nYour miner is ready for compression mining!")
        print("\nNext steps:")
        print("  1. Run end-to-end test: python test_end_to_end_compression.py")
        print("  2. Start your miner: python neurons/miner.py --netuid <netuid> --wallet.name <wallet>")
    else:
        print("⚠️  SOME CHECKS FAILED")
        print("\nFailed checks:")
        for description, result in results:
            if not result:
                print(f"  ❌ {description}")
        
        print("\nPlease fix the failed checks before starting your miner.")
        print("See TESTING_GUIDE.md for troubleshooting help.")


if __name__ == "__main__":
    main()


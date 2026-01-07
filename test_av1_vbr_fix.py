#!/usr/bin/env python3
"""
Quick test to verify AV1 VBR mode fix.
Tests that av1_nvenc uses 'vbr' instead of 'vbr_hq'.
"""

import requests
import json
import time

SERVICE_URL = "http://localhost:29116/compress-video"
SAMPLE_VIDEO_URL = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

def test_av1_vbr():
    """Test AV1 with VBR mode."""
    print("="*80)
    print("🧪 Testing AV1 + VBR Mode Fix")
    print("="*80)
    
    payload = {
        "payload_url": SAMPLE_VIDEO_URL,
        "vmaf_threshold": 89.0,
        "target_codec": "av1",
        "codec_mode": "VBR",
        "target_bitrate": 20.0
    }
    
    print(f"\n📊 Test Configuration:")
    print(f"   Codec: AV1")
    print(f"   Mode: VBR")
    print(f"   Target Bitrate: 20.0 Mbps")
    print(f"   VMAF Threshold: 89.0")
    
    print(f"\n🚀 Sending request...")
    start_time = time.time()
    
    try:
        response = requests.post(SERVICE_URL, json=payload, timeout=600)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ SUCCESS! ({elapsed:.1f}s)")
            print(f"   Status: {result.get('status')}")
            print(f"\n📊 Result:")
            print(json.dumps(result, indent=2))
            return True
        else:
            print(f"\n❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ EXCEPTION ({elapsed:.1f}s): {str(e)}")
        return False

def test_av1_crf():
    """Test AV1 with CRF mode (should still work)."""
    print("\n" + "="*80)
    print("🧪 Testing AV1 + CRF Mode (Baseline)")
    print("="*80)
    
    payload = {
        "payload_url": SAMPLE_VIDEO_URL,
        "vmaf_threshold": 89.0,
        "target_codec": "av1",
        "codec_mode": "CRF",
        "target_bitrate": 20.0
    }
    
    print(f"\n📊 Test Configuration:")
    print(f"   Codec: AV1")
    print(f"   Mode: CRF")
    print(f"   Target Bitrate: 20.0 Mbps")
    print(f"   VMAF Threshold: 89.0")
    
    print(f"\n🚀 Sending request...")
    start_time = time.time()
    
    try:
        response = requests.post(SERVICE_URL, json=payload, timeout=600)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ SUCCESS! ({elapsed:.1f}s)")
            print(f"   Status: {result.get('status')}")
            return True
        else:
            print(f"\n❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ EXCEPTION ({elapsed:.1f}s): {str(e)}")
        return False

if __name__ == "__main__":
    print("="*80)
    print("🎬 AV1 VBR MODE FIX VERIFICATION")
    print("="*80)
    print(f"Service: {SERVICE_URL}")
    print(f"Video: BigBuckBunny (sample)")
    print("="*80)
    
    # Test VBR mode (the fix)
    vbr_success = test_av1_vbr()
    
    # Wait between tests
    if vbr_success:
        print("\n⏳ Waiting 10 seconds before next test...")
        time.sleep(10)
        
        # Test CRF mode (baseline)
        crf_success = test_av1_crf()
    else:
        crf_success = False
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"AV1 + VBR: {'✅ PASS' if vbr_success else '❌ FAIL'}")
    print(f"AV1 + CRF: {'✅ PASS' if crf_success else '❌ FAIL'}")
    print("="*80)
    
    if vbr_success and crf_success:
        print("🎉 All tests passed! AV1 VBR mode is working correctly.")
    elif vbr_success:
        print("⚠️  VBR mode works, but CRF mode failed.")
    else:
        print("❌ VBR mode still failing. Check the logs.")


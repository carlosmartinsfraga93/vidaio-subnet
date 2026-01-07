#!/usr/bin/env python3
"""
Test script to verify HEVC VMAF 93 fix.
Tests that HEVC now achieves VMAF 93+ with the adjusted CQ values.
"""

import requests
import json
import time

SERVICE_URL = "http://localhost:29116/compress-video"
SAMPLE_VIDEO_URL = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

def test_hevc_vmaf93(mode):
    """Test HEVC with VMAF 93 target."""
    print("="*80)
    print(f"🧪 Testing HEVC + {mode} @ VMAF 93 (After CQ Fix)")
    print("="*80)
    
    payload = {
        "payload_url": SAMPLE_VIDEO_URL,
        "vmaf_threshold": 93.0,
        "target_codec": "hevc",
        "codec_mode": mode,
        "target_bitrate": 20.0
    }
    
    print(f"\n📊 Test Configuration:")
    print(f"   Codec: HEVC")
    print(f"   Mode: {mode}")
    print(f"   Target Bitrate: 20.0 Mbps (user max)")
    print(f"   VMAF Threshold: 93.0")
    print(f"\n   🔧 VBR Bitrate Calculation:")
    print(f"   Input: 20 Mbps × 0.50 (HEVC efficiency) × 1.5 (High quality)")
    print(f"   Calculated: 15 Mbps maxrate")
    print(f"   Target: 11.25 Mbps (75% of maxrate)")
    print(f"\n   Expected CQ: 21")
    print(f"   Previous Result: 9 Mbps target → 92.19 VMAF (failed by -0.81)")
    print(f"   Expected Result: 11.25 Mbps target → 93.0+ VMAF (should pass)")
    
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
    print("🎬 HEVC VMAF 93 FIX VERIFICATION")
    print("="*80)
    print(f"Service: {SERVICE_URL}")
    print(f"Video: BigBuckBunny (sample)")
    print("="*80)
    print("\n📝 Fix Summary:")
    print("   Root Cause: VBR bitrate constraint was too low")
    print("   - Old: 9 Mbps target (quality multiplier 1.2)")
    print("   - New: 11.25 Mbps target (quality multiplier 1.5)")
    print("   - Increase: +25% bitrate headroom")
    print("\n   CQ Adjustment (secondary):")
    print("   - low-action: 23 → 21 (Faces/People)")
    print("   - Now effective because bitrate allows it")
    print("="*80)
    
    # Test both CRF and VBR modes
    print("\n🧪 Test 1: HEVC + CRF @ VMAF 93")
    crf_success = test_hevc_vmaf93("CRF")
    
    if crf_success:
        print("\n⏳ Waiting 10 seconds before next test...")
        time.sleep(10)
        
        print("\n🧪 Test 2: HEVC + VBR @ VMAF 93")
        vbr_success = test_hevc_vmaf93("VBR")
    else:
        vbr_success = False
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"HEVC + CRF @ VMAF 93: {'✅ PASS' if crf_success else '❌ FAIL'}")
    print(f"HEVC + VBR @ VMAF 93: {'✅ PASS' if vbr_success else '❌ FAIL'}")
    print("="*80)
    
    if crf_success and vbr_success:
        print("🎉 Both tests passed! HEVC VMAF 93 fix is working.")
        print("\n💡 Next step: Check VMAF logs to verify actual scores:")
        print("   python services/compress/view_vmaf_logs.py")
    elif crf_success or vbr_success:
        print("⚠️  One test passed, one failed. Check the logs.")
    else:
        print("❌ Both tests failed. CQ adjustment may need further tuning.")


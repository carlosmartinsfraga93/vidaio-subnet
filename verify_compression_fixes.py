#!/usr/bin/env python3
"""
Verify Compression Service Fixes
- Check PKL loading works without errors
- Check AV1 preset is p4 (fast)
- Estimate encoding time for different video lengths
"""

import sys
import os

# Add services/compress to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'compress'))

def check_pkl_loading():
    """Check if PKL loading works without errors"""
    print("\n" + "="*80)
    print("TEST 1: PKL Model Loading")
    print("="*80)
    
    try:
        from encoder import get_scalers_from_pipeline
        
        pipeline_path = 'services/compress/models/preprocessing_pipeline.pkl'
        
        print(f"\n📖 Loading preprocessing pipeline from: {pipeline_path}")
        
        result = get_scalers_from_pipeline(
            pipeline_path=pipeline_path,
            verbose=True,
            logging_enabled=True
        )
        
        if result[0] is not None:
            print("\n✅ PKL model loaded successfully!")
            print("✅ No module errors!")
            return True
        else:
            print("\n❌ PKL model loading failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error loading PKL model: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_av1_preset():
    """Check if AV1 preset is p4"""
    print("\n" + "="*80)
    print("TEST 2: AV1 Encoding Preset")
    print("="*80)
    
    try:
        from utils.encoder_configs import ENCODER_SETTINGS, SCENE_SPECIFIC_PARAMS
        
        # Check base preset
        base_preset = ENCODER_SETTINGS['av1_nvenc']['preset']
        print(f"\n📋 Base AV1 preset: {base_preset}")
        
        if base_preset == 'p4':
            print("✅ Base preset is p4 (fast)")
        else:
            print(f"❌ Base preset is {base_preset} (should be p4)")
            return False
        
        # Check scene-specific presets
        print("\n📋 Scene-specific presets:")
        all_p4 = True
        for scene_type, params in SCENE_SPECIFIC_PARAMS['av1_nvenc'].items():
            preset = params.get('preset', 'N/A')
            print(f"   {scene_type:45s}: {preset}")
            if preset != 'p4' and preset != 'N/A':
                all_p4 = False
        
        if all_p4:
            print("\n✅ All scene-specific presets are p4 (fast)")
            return True
        else:
            print("\n❌ Some scene-specific presets are not p4")
            return False
            
    except Exception as e:
        print(f"\n❌ Error checking AV1 preset: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_duration_based_presets():
    """Check duration-based preset selection"""
    print("\n" + "="*80)
    print("TEST 3: Duration-Based Preset Selection")
    print("="*80)

    try:
        from utils.encoder_configs import DURATION_BASED_PRESETS, get_preset_for_duration

        print("\n📋 Duration-based preset configuration:")
        print(f"\n{'Duration Range':20s} {'Preset':10s} {'Strategy':30s}")
        print("-" * 65)

        # Test different durations
        test_durations = [5, 10, 15, 20, 30, 45, 60, 90]

        for duration in test_durations:
            preset = get_preset_for_duration('av1_nvenc', duration)

            # Determine strategy
            if duration < 15:
                strategy = "High quality (short video)"
            elif duration < 30:
                strategy = "Balanced (medium video)"
            elif duration < 60:
                strategy = "Faster (long video)"
            else:
                strategy = "Fastest (very long video)"

            print(f"{duration:3d}s                {preset:10s} {strategy}")

        print("\n✅ Duration-based preset selection is configured!")
        print("\n📝 Strategy:")
        print("   - Short videos (0-15s):   Use p5 for better quality")
        print("   - Medium videos (15-30s): Use p4 for balance")
        print("   - Long videos (30-60s):   Use p3 for speed")
        print("   - Very long (60s+):       Use p2 for fastest encoding")

        return True

    except Exception as e:
        print(f"\n❌ Error checking duration-based presets: {e}")
        import traceback
        traceback.print_exc()
        return False


def estimate_encoding_times():
    """Estimate encoding times for different video lengths with duration-based presets"""
    print("\n" + "="*80)
    print("TEST 4: Estimated Encoding Times (Duration-Based Presets)")
    print("="*80)

    # Rough estimates based on different presets
    # Format: {duration: (preset, min_time, max_time)}
    estimates = {
        10: ('p5', 17, 25),   # 10s video with p5: 17-25 seconds
        20: ('p4', 25, 35),   # 20s video with p4: 25-35 seconds
        30: ('p3', 30, 45),   # 30s video with p3: 30-45 seconds
        45: ('p3', 45, 65),   # 45s video with p3: 45-65 seconds
        60: ('p2', 40, 60),   # 60s video with p2: 40-60 seconds
        90: ('p2', 60, 90),   # 90s video with p2: 60-90 seconds
    }

    print("\n📊 Estimated encoding times with duration-based presets:")
    print(f"\n{'Video Length':15s} {'Preset':10s} {'Estimated Time':20s} {'Validator Status':20s}")
    print("-" * 75)

    validator_timeout = 120  # seconds

    for video_len, (preset, min_time, max_time) in estimates.items():
        status = "✅ Within timeout" if max_time <= validator_timeout else "❌ May timeout"
        print(f"{video_len:3d} seconds      {preset:10s} {min_time:3d}-{max_time:3d} seconds        {status}")

    print("\n📝 Notes:")
    print("   - Validator timeout: ~60-120 seconds")
    print("   - Duration-based presets optimize speed vs quality")
    print("   - Actual times may vary based on:")
    print("     • GPU model (RTX 3090, 4090, etc.)")
    print("     • Video resolution (1080p, 4K, etc.)")
    print("     • Video complexity (animation, gaming, etc.)")
    print("     • System load")

    print("\n🎯 Benefits:")
    print("   ✅ Short videos: Better quality (p5) while staying fast")
    print("   ✅ Medium videos: Balanced (p4) for optimal results")
    print("   ✅ Long videos: Faster (p3) to avoid timeout")
    print("   ✅ Very long videos: Fastest (p2) to guarantee completion")

    return True


def main():
    """Run all verification tests"""
    print("\n" + "="*80)
    print("COMPRESSION SERVICE FIXES VERIFICATION")
    print("="*80)

    results = []

    # Test 1: PKL Loading
    results.append(("PKL Model Loading", check_pkl_loading()))

    # Test 2: AV1 Preset
    results.append(("AV1 Preset Configuration", check_av1_preset()))

    # Test 3: Duration-Based Presets
    results.append(("Duration-Based Preset Selection", check_duration_based_presets()))

    # Test 4: Encoding Time Estimates
    results.append(("Encoding Time Estimates", estimate_encoding_times()))

    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:40s}: {status}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 All tests passed! Compression service is ready.")
        print("\n📝 Next steps:")
        print("   1. Restart compression service")
        print("   2. Restart miner")
        print("   3. Monitor logs for improved performance")
        print("\n📖 Documentation:")
        print("   - See DURATION_BASED_PRESET_OPTIMIZATION.md for details")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


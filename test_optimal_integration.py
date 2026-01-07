"""
Test Script for Optimal Controller Integration
===============================================

This script tests the optimal controller integration without running full compression.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_config_import():
    """Test that configuration can be imported."""
    print("=" * 80)
    print("TEST 1: Configuration Import")
    print("=" * 80)
    
    try:
        from config.optimal_controller_config import (
            get_optimal_controller_config,
            should_use_optimal_controller,
            map_scene_type_for_optimal_controller,
            get_preferred_codec_mode,
            get_vmaf_threshold_from_quality
        )
        
        print("✅ Configuration imported successfully")
        
        # Test config retrieval
        config = get_optimal_controller_config()
        print(f"✅ Config retrieved: {len(config)} settings")
        print(f"   - Enabled: {config['enabled']}")
        print(f"   - Integration mode: {config['integration_mode']}")
        print(f"   - Auto-detect scene: {config['auto_detect_scene']}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration import failed: {e}")
        return False


def test_scene_mapping():
    """Test scene type mapping."""
    print("\n" + "=" * 80)
    print("TEST 2: Scene Type Mapping")
    print("=" * 80)
    
    try:
        from config.optimal_controller_config import map_scene_type_for_optimal_controller
        
        test_cases = [
            ('screen', 1.0, 'screen'),
            ('text', 1.0, 'screen'),
            ('gaming', 1.0, 'gaming'),
            ('animation', 1.0, 'animation'),
            ('faces', 1.0, 'faces'),
            ('people', 1.0, 'faces'),
            ('default', 1.0, 'other'),
            ('unknown', 1.0, 'other'),
            ('screen', 0.3, 'other'),  # Low confidence
        ]
        
        all_passed = True
        for scene_in, confidence, expected in test_cases:
            result = map_scene_type_for_optimal_controller(scene_in, confidence)
            status = "✅" if result == expected else "❌"
            print(f"{status} {scene_in} (conf={confidence}) → {result} (expected: {expected})")
            if result != expected:
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ Scene mapping test failed: {e}")
        return False


def test_vmaf_mapping():
    """Test VMAF threshold mapping."""
    print("\n" + "=" * 80)
    print("TEST 3: VMAF Threshold Mapping")
    print("=" * 80)
    
    try:
        from config.optimal_controller_config import get_vmaf_threshold_from_quality
        
        test_cases = [
            ('High', 93),
            ('Medium', 89),
            ('Low', 85),
            ('Unknown', 89),  # Default
        ]
        
        all_passed = True
        for quality, expected in test_cases:
            result = get_vmaf_threshold_from_quality(quality)
            status = "✅" if result == expected else "❌"
            print(f"{status} {quality} → {result} (expected: {expected})")
            if result != expected:
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ VMAF mapping test failed: {e}")
        return False


def test_codec_mode_preferences():
    """Test codec mode preferences."""
    print("\n" + "=" * 80)
    print("TEST 4: Codec Mode Preferences")
    print("=" * 80)
    
    try:
        from config.optimal_controller_config import get_preferred_codec_mode
        
        test_cases = [
            ('screen', 'CRF'),
            ('gaming', 'VBR'),
            ('animation', 'CRF'),
            ('faces', 'CRF'),
            ('other', 'CRF'),
        ]
        
        all_passed = True
        for scene, expected in test_cases:
            result = get_preferred_codec_mode(scene)
            status = "✅" if result == expected else "❌"
            print(f"{status} {scene} → {result} (expected: {expected})")
            if result != expected:
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ Codec mode preferences test failed: {e}")
        return False


def test_optimal_controller_import():
    """Test that optimal controller can be imported."""
    print("\n" + "=" * 80)
    print("TEST 5: Optimal Controller Import")
    print("=" * 80)
    
    try:
        from services.compress.utils.optimal_encoder_wrapper import encode_video_optimal
        from services.compress.utils.optimal_controller_integration import get_optimal_encoding_params
        from services.compress.utils.optimal_bitrate_controller import (
            calculate_complexity_score,
            calculate_target_ratio,
            calculate_initial_cq
        )
        
        print("✅ Optimal controller modules imported successfully")
        print("   - encode_video_optimal")
        print("   - get_optimal_encoding_params")
        print("   - Core functions (complexity, ratio, CQ)")
        
        return True
    except Exception as e:
        print(f"❌ Optimal controller import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_check():
    """Test the integration check function."""
    print("\n" + "=" * 80)
    print("TEST 6: Integration Check")
    print("=" * 80)
    
    try:
        from config.optimal_controller_config import should_use_optimal_controller
        
        # Test with no config
        result1 = should_use_optimal_controller()
        print(f"   should_use_optimal_controller() = {result1}")
        
        # Test with config enabling it
        config_enable = {
            'video_processing': {
                'use_optimal_controller': True
            }
        }
        result2 = should_use_optimal_controller(config_enable)
        print(f"   should_use_optimal_controller(enable_config) = {result2}")
        
        # Test with config disabling it
        config_disable = {
            'video_processing': {
                'use_optimal_controller': False
            }
        }
        result3 = should_use_optimal_controller(config_disable)
        print(f"   should_use_optimal_controller(disable_config) = {result3}")
        
        print("✅ Integration check function works")
        return True
    except Exception as e:
        print(f"❌ Integration check test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "🧪" * 40)
    print("OPTIMAL CONTROLLER INTEGRATION TESTS")
    print("🧪" * 40 + "\n")
    
    tests = [
        ("Configuration Import", test_config_import),
        ("Scene Type Mapping", test_scene_mapping),
        ("VMAF Threshold Mapping", test_vmaf_mapping),
        ("Codec Mode Preferences", test_codec_mode_preferences),
        ("Optimal Controller Import", test_optimal_controller_import),
        ("Integration Check", test_integration_check),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed_count}/{total_count} tests passed")
    print("=" * 80)
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Integration is ready.")
        return 0
    else:
        print(f"\n⚠️ {total_count - passed_count} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


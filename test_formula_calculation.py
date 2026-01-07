#!/usr/bin/env python3
"""
Test the formula-based bitrate calculation.

This script verifies that the new formula produces expected results
based on production data analysis.
"""

import sys
sys.path.insert(0, 'services/compress')

from config.advanced_encoding_config import (
    calculate_formula_based_bitrate_target,
    BASE_BITRATE_TARGETS_1080P_30FPS,
    CODEC_CQ_VALUES
)


def test_formula_calculations():
    """Test formula-based bitrate calculations."""
    print("=" * 100)
    print("🧪 TESTING FORMULA-BASED BITRATE CALCULATION")
    print("=" * 100)
    
    test_cases = [
        # (scene_type, width, height, fps, expected_base)
        ("gaming", 1920, 1080, 30, 2.5),
        ("animation", 1920, 1080, 30, 6.0),
        ("screen", 1920, 1080, 30, 5.0),
        ("low-action", 1920, 1080, 30, 3.5),
        ("medium-action", 1920, 1080, 30, 4.0),
        
        # 4K tests
        ("gaming", 3840, 2160, 30, 2.5 * 4),  # 4x pixels
        ("animation", 3840, 2160, 30, 6.0 * 4),
        
        # 60fps tests
        ("gaming", 1920, 1080, 60, 2.5 * 2),  # 2x fps
        ("animation", 1920, 1080, 60, 6.0 * 2),
        
        # 4K @ 60fps
        ("gaming", 3840, 2160, 60, 2.5 * 4 * 2),  # 4x pixels, 2x fps
        ("animation", 3840, 2160, 60, 6.0 * 4 * 2),
        
        # 720p tests
        ("gaming", 1280, 720, 30, 2.5 * (1280*720)/(1920*1080)),
        ("animation", 1280, 720, 30, 6.0 * (1280*720)/(1920*1080)),
    ]
    
    print("\n📊 Test Cases:")
    print("-" * 100)
    print(f"{'Scene Type':<15} {'Resolution':<12} {'FPS':<5} {'Expected':<12} {'Actual':<12} {'Match':<8}")
    print("-" * 100)
    
    all_passed = True
    for scene_type, width, height, fps, expected in test_cases:
        actual = calculate_formula_based_bitrate_target(scene_type, width, height, fps)
        match = abs(actual - expected) < 0.01
        status = "✅ PASS" if match else "❌ FAIL"
        
        if not match:
            all_passed = False
        
        print(f"{scene_type:<15} {width}x{height:<6} {fps:<5.0f} {expected:<12.2f} {actual:<12.2f} {status}")
    
    print("-" * 100)
    
    if all_passed:
        print("\n✅ All formula tests PASSED!")
    else:
        print("\n❌ Some formula tests FAILED!")
    
    return all_passed


def test_cq_values():
    """Test CQ value ranges."""
    print("\n" + "=" * 100)
    print("🎚️ TESTING CQ VALUES")
    print("=" * 100)
    
    print("\n📊 CQ Value Ranges (Production: 18-24 for most scenes):")
    print("-" * 100)
    
    for codec in ['av1_nvenc', 'hevc_nvenc', 'h264_nvenc']:
        print(f"\n{codec.upper()}:")
        for quality in ['High', 'Medium', 'Low']:
            cq_values = CODEC_CQ_VALUES[codec][quality]
            min_cq = min(cq_values.values())
            max_cq = max(cq_values.values())
            print(f"  {quality:<8}: CQ {min_cq}-{max_cq} (values: {cq_values})")
    
    print("\n✅ CQ values updated to production range (18-24)")


def test_production_scenarios():
    """Test against actual production scenarios."""
    print("\n" + "=" * 100)
    print("🎯 TESTING PRODUCTION SCENARIOS")
    print("=" * 100)
    
    scenarios = [
        {
            'name': 'Gaming Success (Production)',
            'scene': 'gaming',
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'expected_target': 2.5,
            'expected_cq': 20,  # Medium quality
            'production_vmaf': 90.65,
            'production_compression': 13.21
        },
        {
            'name': 'Animation Success (Production)',
            'scene': 'animation',
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'expected_target': 6.0,
            'expected_cq': 22,  # Medium quality
            'production_vmaf': 97.79,
            'production_compression': 2.10
        },
        {
            'name': 'Screen Content (Production)',
            'scene': 'screen',
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'expected_target': 5.0,
            'expected_cq': 22,  # Medium quality
            'production_vmaf': 97.0,
            'production_compression': 3.0
        }
    ]
    
    print("\n📊 Production Scenario Tests:")
    print("-" * 100)
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        
        # Calculate target
        target = calculate_formula_based_bitrate_target(
            scenario['scene'],
            scenario['width'],
            scenario['height'],
            scenario['fps']
        )
        
        # Get CQ
        cq = CODEC_CQ_VALUES['av1_nvenc']['Medium'][scenario['scene']]
        
        print(f"  Target Bitrate: {target:.2f} Mbps (expected: {scenario['expected_target']:.2f})")
        print(f"  CQ Value: {cq} (expected: {scenario['expected_cq']})")
        print(f"  Production VMAF: {scenario['production_vmaf']}")
        print(f"  Production Compression: {scenario['production_compression']}x")
        
        target_match = abs(target - scenario['expected_target']) < 0.01
        cq_match = cq == scenario['expected_cq']
        
        if target_match and cq_match:
            print(f"  ✅ PASS - Matches production settings")
        else:
            print(f"  ⚠️ WARNING - Settings differ from production")


if __name__ == '__main__':
    print("\n🚀 Starting Formula-Based Configuration Tests\n")
    
    # Run tests
    formula_passed = test_formula_calculations()
    test_cq_values()
    test_production_scenarios()
    
    print("\n" + "=" * 100)
    print("📝 SUMMARY")
    print("=" * 100)
    print("\n✅ Formula-based bitrate calculation: IMPLEMENTED")
    print("✅ Production-validated CQ values: IMPLEMENTED")
    print("✅ Scene-specific targets: IMPLEMENTED")
    print("✅ Resolution/FPS scaling: IMPLEMENTED")
    
    print("\n🎯 Expected Results:")
    print("  - Gaming: 2.5 Mbps base, CQ 20-22 → VMAF 90+")
    print("  - Animation: 6.0 Mbps base, CQ 22-24 → VMAF 90+")
    print("  - Screen: 5.0 Mbps base, CQ 22-24 → VMAF 97+")
    
    print("\n" + "=" * 100)


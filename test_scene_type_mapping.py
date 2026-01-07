#!/usr/bin/env python3
"""
Test scene type mapping to verify plumbing fix.

This test ensures that descriptive classifier outputs like
"Animation / Cartoon / Rendered Graphics" are correctly mapped
to canonical scene types like "animation" for the optimal controller.
"""

import sys
import os

# Add services/compress to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'compress'))

def test_scene_type_mapping():
    """Test that scene type mapping works correctly."""
    from config.optimal_controller_config import map_scene_type_for_optimal_controller
    
    print("\n" + "="*80)
    print("SCENE TYPE MAPPING TEST")
    print("="*80 + "\n")
    
    test_cases = [
        # (classifier_output, confidence, expected_mapping)
        ("Animation / Cartoon / Rendered Graphics", 0.119, "animation"),
        ("animation", 1.0, "animation"),
        ("cartoon", 1.0, "animation"),
        ("anime", 1.0, "animation"),
        
        ("Gaming Content", 0.8, "gaming"),
        ("gaming", 1.0, "gaming"),
        ("game", 1.0, "gaming"),
        
        ("Screen Content / Text", 0.9, "screen"),
        ("screen", 1.0, "screen"),
        ("text", 1.0, "screen"),
        ("desktop", 1.0, "screen"),
        
        ("Faces / People", 0.7, "faces"),
        ("faces", 1.0, "faces"),
        ("people", 1.0, "faces"),
        ("portrait", 1.0, "faces"),
        
        ("other", 1.0, "other"),
        ("unclear", 1.0, "other"),
        
        # Low confidence should map to 'other'
        ("Animation / Cartoon / Rendered Graphics", 0.05, "other"),
        ("gaming", 0.08, "other"),
    ]
    
    all_passed = True
    for classifier_output, confidence, expected in test_cases:
        result = map_scene_type_for_optimal_controller(classifier_output, confidence)
        passed = result == expected
        status = "✅" if passed else "❌"
        
        print(f"{status} '{classifier_output}' (conf={confidence:.3f})")
        print(f"   → {result} (expected: {expected})")
        
        if not passed:
            all_passed = False
            print(f"   ⚠️ FAILED: Got '{result}' but expected '{expected}'")
        print()
    
    print("="*80)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*80 + "\n")
    
    return all_passed


def test_consistency_check():
    """Test that the same scene type is used for both CQ lookup and optimal controller."""
    print("\n" + "="*80)
    print("CONSISTENCY CHECK TEST")
    print("="*80 + "\n")
    
    # Import both mapping functions
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'compress'))
    from config.optimal_controller_config import map_scene_type_for_optimal_controller
    from encoder import map_scene_type_to_lookup_key
    
    test_cases = [
        "Animation / Cartoon / Rendered Graphics",
        "Gaming Content",
        "Screen Content / Text",
        "Faces / People",
    ]
    
    print("Checking that both mapping functions produce compatible results:\n")
    
    for classifier_output in test_cases:
        optimal_mapping = map_scene_type_for_optimal_controller(classifier_output, 1.0)
        lookup_mapping = map_scene_type_to_lookup_key(classifier_output)
        
        # Check if they're compatible (not necessarily identical, but semantically equivalent)
        compatible = (
            (optimal_mapping == 'animation' and lookup_mapping == 'animation') or
            (optimal_mapping == 'gaming' and lookup_mapping == 'high-action') or
            (optimal_mapping == 'screen' and lookup_mapping == 'low-action') or
            (optimal_mapping == 'faces' and lookup_mapping == 'low-action') or
            (optimal_mapping == 'other' and lookup_mapping in ['medium-action', 'default'])
        )
        
        status = "✅" if compatible else "⚠️"
        print(f"{status} '{classifier_output}'")
        print(f"   Optimal controller: {optimal_mapping}")
        print(f"   CQ lookup:          {lookup_mapping}")
        print()
    
    print("="*80 + "\n")


if __name__ == "__main__":
    success = test_scene_type_mapping()
    test_consistency_check()
    
    sys.exit(0 if success else 1)


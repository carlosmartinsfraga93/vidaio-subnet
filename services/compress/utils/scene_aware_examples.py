"""
Scene-Aware Optimal Controller Examples
========================================

Demonstrates the scene-aware score-maximizing formula.
"""

from optimal_bitrate_controller import (
    calculate_complexity_score,
    calculate_target_bitrate,
    calculate_initial_cq,
    normalize_scene_type
)


def example_scene_comparison():
    """Compare different scene types with same complexity."""
    
    print("=" * 80)
    print("SCENE-AWARE COMPARISON: Same Complexity, Different Scenes")
    print("=" * 80)
    
    # Same complexity metrics for all scenes
    grain = 0.08
    texture = 0.08
    motion = 0.04
    complexity = calculate_complexity_score(grain, texture, motion)
    
    bitrate_orig = 30.0  # 30 Mbps original
    codec = 'av1'
    mode = 'CRF'
    vmaf_threshold = 89
    
    scenes = ['screen', 'gaming', 'animation', 'faces', 'other']
    
    print(f"\nShared parameters:")
    print(f"  Complexity: {complexity:.2f}")
    print(f"  Original bitrate: {bitrate_orig} Mbps")
    print(f"  Codec: {codec}, Mode: {mode}, Threshold: {vmaf_threshold}")
    
    print(f"\n{'Scene':<12} {'Ratio':<8} {'Bitrate':<10} {'Min Safe':<10} {'CQ':<5}")
    print("-" * 55)
    
    for scene in scenes:
        target_bitrate, target_ratio, min_bitrate = calculate_target_bitrate(
            bitrate_orig=bitrate_orig,
            complexity=complexity,
            motion=motion,
            codec=codec,
            vmaf_threshold=vmaf_threshold,
            mode=mode,
            scene_type=scene,
            grain=grain,
            texture=texture
        )
        
        initial_cq = calculate_initial_cq(complexity, codec, scene)
        
        print(f"{scene:<12} {target_ratio:<8.1f} {target_bitrate:<10.2f} {min_bitrate:<10.2f} {initial_cq:<5}")
    
    print("\n💡 Observations:")
    print("   - Screen: Highest ratio (20×), lowest min bitrate, highest CQ")
    print("   - Gaming: Lower ratio (19×), higher min bitrate, lower CQ (riskier)")
    print("   - Faces: Lowest ratio (17.5×), highest min bitrate (VMAF-sensitive)")
    print("   - Animation: Medium ratio (18.5×), medium settings")


def example_complexity_impact_by_scene():
    """Show how complexity affects different scenes."""
    
    print("\n" + "=" * 80)
    print("COMPLEXITY IMPACT: Easy vs Hard Content by Scene")
    print("=" * 80)
    
    # Easy content
    easy_complexity = calculate_complexity_score(0.05, 0.05, 0.02)
    
    # Hard content
    hard_complexity = calculate_complexity_score(0.12, 0.12, 0.08)
    
    bitrate_orig = 30.0
    codec = 'av1'
    mode = 'CRF'
    vmaf_threshold = 89
    
    scenes = ['screen', 'gaming', 'faces']
    
    print(f"\n{'Scene':<12} {'Complexity':<12} {'Ratio':<8} {'Bitrate':<10} {'CQ':<5}")
    print("-" * 55)
    
    for scene in scenes:
        # Easy content
        target_bitrate_easy, target_ratio_easy, _ = calculate_target_bitrate(
            bitrate_orig=bitrate_orig,
            complexity=easy_complexity,
            motion=0.02,
            codec=codec,
            vmaf_threshold=vmaf_threshold,
            mode=mode,
            scene_type=scene,
            grain=0.05,
            texture=0.05
        )
        cq_easy = calculate_initial_cq(easy_complexity, codec, scene)
        
        # Hard content
        target_bitrate_hard, target_ratio_hard, _ = calculate_target_bitrate(
            bitrate_orig=bitrate_orig,
            complexity=hard_complexity,
            motion=0.08,
            codec=codec,
            vmaf_threshold=vmaf_threshold,
            mode=mode,
            scene_type=scene,
            grain=0.12,
            texture=0.12
        )
        cq_hard = calculate_initial_cq(hard_complexity, codec, scene)
        
        print(f"{scene:<12} Easy (0.44)   {target_ratio_easy:<8.1f} {target_bitrate_easy:<10.2f} {cq_easy:<5}")
        print(f"{scene:<12} Hard (1.70)   {target_ratio_hard:<8.1f} {target_bitrate_hard:<10.2f} {cq_hard:<5}")
        print()
    
    print("💡 Observations:")
    print("   - Screen: Least affected by complexity (k_s=0.8)")
    print("   - Gaming: Most affected by complexity (k_s=1.4)")
    print("   - Faces: Highly affected (k_s=1.3), VMAF-sensitive")


def example_vbr_buffer_sizes():
    """Show scene-specific VBR buffer sizes."""
    
    print("\n" + "=" * 80)
    print("VBR BUFFER SIZES: Scene-Specific Settings")
    print("=" * 80)
    
    from optimal_bitrate_controller import calculate_vbr_settings
    
    target_bitrate = 3.0  # 3 Mbps
    scenes = ['screen', 'gaming', 'animation', 'faces', 'other']
    
    print(f"\nTarget bitrate: {target_bitrate} Mbps")
    print(f"\n{'Scene':<12} {'b:v':<8} {'maxrate':<10} {'bufsize':<10} {'Multiplier':<12}")
    print("-" * 60)
    
    for scene in scenes:
        settings = calculate_vbr_settings(target_bitrate, scene)
        multiplier = settings['bufsize'] / target_bitrate
        
        print(f"{scene:<12} {settings['b:v']:<8.2f} {settings['maxrate']:<10.2f} "
              f"{settings['bufsize']:<10.2f} {multiplier:<12.1f}×")
    
    print("\n💡 Observations:")
    print("   - Gaming/Animation: 3.0× buffer (higher for spikes)")
    print("   - Screen/Faces/Other: 2.5× buffer (standard)")


def example_real_world_scenarios():
    """Real-world encoding scenarios."""
    
    print("\n" + "=" * 80)
    print("REAL-WORLD SCENARIOS")
    print("=" * 80)
    
    scenarios = [
        {
            'name': 'Screen Recording (Tutorial)',
            'scene': 'screen',
            'grain': 0.03,
            'texture': 0.04,
            'motion': 0.02,
            'bitrate_orig': 25.0,
            'codec': 'av1',
            'mode': 'CRF',
            'threshold': 89
        },
        {
            'name': 'Gaming Stream (Fast Action)',
            'scene': 'gaming',
            'grain': 0.10,
            'texture': 0.11,
            'motion': 0.09,
            'bitrate_orig': 50.0,
            'codec': 'av1',
            'mode': 'VBR',
            'threshold': 89
        },
        {
            'name': 'Animated Movie',
            'scene': 'animation',
            'grain': 0.08,
            'texture': 0.09,
            'motion': 0.05,
            'bitrate_orig': 35.0,
            'codec': 'hevc',
            'mode': 'CRF',
            'threshold': 85
        },
        {
            'name': 'Video Conference',
            'scene': 'faces',
            'grain': 0.06,
            'texture': 0.06,
            'motion': 0.03,
            'bitrate_orig': 20.0,
            'codec': 'av1',
            'mode': 'VBR',
            'threshold': 89
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print("-" * 60)
        
        complexity = calculate_complexity_score(
            scenario['grain'],
            scenario['texture'],
            scenario['motion']
        )
        
        target_bitrate, target_ratio, min_bitrate = calculate_target_bitrate(
            bitrate_orig=scenario['bitrate_orig'],
            complexity=complexity,
            motion=scenario['motion'],
            codec=scenario['codec'],
            vmaf_threshold=scenario['threshold'],
            mode=scenario['mode'],
            scene_type=scenario['scene'],
            grain=scenario['grain'],
            texture=scenario['texture']
        )
        
        print(f"  Scene: {scenario['scene']}, Codec: {scenario['codec']}, Mode: {scenario['mode']}")
        print(f"  Original: {scenario['bitrate_orig']:.1f} Mbps → Target: {target_bitrate:.2f} Mbps")
        print(f"  Compression: {target_ratio:.1f}× (min safe: {min_bitrate:.2f} Mbps)")
        print(f"  Complexity: {complexity:.2f}")
        
        if scenario['mode'] == 'CRF':
            cq = calculate_initial_cq(complexity, scenario['codec'], scenario['scene'])
            print(f"  Initial CQ: {cq}")


if __name__ == "__main__":
    example_scene_comparison()
    example_complexity_impact_by_scene()
    example_vbr_buffer_sizes()
    example_real_world_scenarios()
    
    print("\n" + "=" * 80)
    print("✅ All scene-aware examples completed!")
    print("=" * 80)


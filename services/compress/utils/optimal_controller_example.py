"""
Example usage of Optimal Bitrate Controller
============================================

Demonstrates how to use the score-maximizing formula in practice.
"""

from optimal_controller_integration import (
    get_optimal_encoding_params,
    update_encoding_params_after_result,
    format_encoding_command_params
)


def example_single_pass_encoding():
    """Example: Single-pass encoding with optimal parameters."""
    
    print("=" * 80)
    print("EXAMPLE 1: Single-Pass Encoding")
    print("=" * 80)
    
    # Input parameters
    video_path = "input_video.mp4"
    codec = "av1"
    mode = "CRF"
    vmaf_threshold = 89
    
    # Get optimal encoding parameters
    params = get_optimal_encoding_params(
        video_path=video_path,
        codec=codec,
        mode=mode,
        vmaf_threshold=vmaf_threshold,
        logging_enabled=True
    )
    
    # Format for FFmpeg
    ffmpeg_params = format_encoding_command_params(params, codec, mode)
    
    print(f"\n📝 FFmpeg Parameters:")
    for key, value in ffmpeg_params.items():
        print(f"   -{key} {value}")
    
    print(f"\n✅ Ready to encode with CQ={params['initial_cq']}")
    print(f"   Expected ratio: {params['target_ratio']:.1f}x")
    print(f"   Target bitrate: {params['target_bitrate']:.2f} Mbps")


def example_adaptive_encoding():
    """Example: Adaptive encoding with feedback loop."""
    
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Adaptive Encoding (Multi-Pass)")
    print("=" * 80)
    
    # Initial parameters
    video_path = "input_video.mp4"
    codec = "hevc"
    mode = "VBR"
    vmaf_threshold = 85
    
    # Pass 1: Get initial parameters
    print("\n🎬 PASS 1: Initial Encoding")
    print("-" * 80)
    params = get_optimal_encoding_params(
        video_path=video_path,
        codec=codec,
        mode=mode,
        vmaf_threshold=vmaf_threshold,
        logging_enabled=True
    )
    
    # Simulate encoding result (in real code, you'd actually encode)
    print("\n🎥 Encoding with VBR settings...")
    simulated_vmaf = 87.5  # Simulated result
    simulated_bitrate_actual = 3.2  # Mbps
    bitrate_orig = params['metrics']['bitrate_mbps']
    
    print(f"   Result: VMAF={simulated_vmaf:.2f}, Bitrate={simulated_bitrate_actual:.2f} Mbps")
    
    # Pass 2: Update parameters based on result
    print("\n🔄 PASS 2: Adaptive Update")
    print("-" * 80)
    updated_params = update_encoding_params_after_result(
        current_params=params,
        vmaf_score=simulated_vmaf,
        bitrate_actual=simulated_bitrate_actual,
        bitrate_orig=bitrate_orig,
        codec=codec,
        mode=mode,
        vmaf_threshold=vmaf_threshold,
        logging_enabled=True
    )
    
    # Show updated parameters
    ffmpeg_params = format_encoding_command_params(updated_params, codec, mode)
    print(f"\n📝 Updated FFmpeg Parameters:")
    for key, value in ffmpeg_params.items():
        print(f"   -{key} {value}")


def example_crf_with_ceiling():
    """Example: CRF mode with VBR ceiling guard."""
    
    print("\n" + "=" * 80)
    print("EXAMPLE 3: CRF with VBR Ceiling Guard")
    print("=" * 80)
    
    # Initial parameters
    video_path = "input_video.mp4"
    codec = "av1"
    mode = "CRF"
    vmaf_threshold = 89
    
    # Pass 1: CRF encoding
    print("\n🎬 PASS 1: CRF Encoding")
    print("-" * 80)
    params = get_optimal_encoding_params(
        video_path=video_path,
        codec=codec,
        mode=mode,
        vmaf_threshold=vmaf_threshold,
        logging_enabled=True
    )
    
    # Simulate result: High VMAF but bitrate too high (hurting ratio)
    print("\n🎥 Encoding with CRF...")
    simulated_vmaf = 95.0  # Good quality
    simulated_bitrate_actual = 8.5  # Too high! (target was ~3 Mbps)
    bitrate_orig = params['metrics']['bitrate_mbps']
    
    print(f"   Result: VMAF={simulated_vmaf:.2f}, Bitrate={simulated_bitrate_actual:.2f} Mbps")
    print(f"   ⚠️ Bitrate is {simulated_bitrate_actual / params['target_bitrate']:.2f}x target!")
    
    # Pass 2: Apply VBR ceiling
    print("\n🔄 PASS 2: VBR Ceiling Guard")
    print("-" * 80)
    updated_params = update_encoding_params_after_result(
        current_params=params,
        vmaf_score=simulated_vmaf,
        bitrate_actual=simulated_bitrate_actual,
        bitrate_orig=bitrate_orig,
        codec=codec,
        mode=mode,
        vmaf_threshold=vmaf_threshold,
        logging_enabled=True
    )
    
    if updated_params.get('apply_vbr_ceiling', False):
        print(f"\n✅ VBR ceiling will be applied in next pass")
        ffmpeg_params = format_encoding_command_params(updated_params, codec, mode)
        print(f"📝 VBR Parameters:")
        for key, value in ffmpeg_params.items():
            print(f"   -{key} {value}")


def example_comparison_table():
    """Example: Compare different scenarios."""
    
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Scenario Comparison")
    print("=" * 80)
    
    scenarios = [
        ("Easy content, AV1, CRF, T=89", "av1", "CRF", 89, 0.05, 0.05, 0.02),
        ("Hard content, AV1, CRF, T=89", "av1", "CRF", 89, 0.12, 0.12, 0.08),
        ("Easy content, HEVC, VBR, T=85", "hevc", "VBR", 85, 0.05, 0.05, 0.02),
        ("Hard content, HEVC, VBR, T=85", "hevc", "VBR", 85, 0.12, 0.12, 0.08),
    ]
    
    print(f"\n{'Scenario':<35} {'Codec':<6} {'Mode':<4} {'T':<3} {'Ratio':<7} {'Bitrate':<8} {'CQ/VBR'}")
    print("-" * 100)
    
    for desc, codec, mode, threshold, grain, texture, motion in scenarios:
        from optimal_bitrate_controller import (
            calculate_complexity_score,
            calculate_target_bitrate,
            calculate_initial_cq
        )
        
        complexity = calculate_complexity_score(grain, texture, motion)
        bitrate_orig = 30.0  # Assume 30 Mbps original
        
        target_bitrate, target_ratio, _ = calculate_target_bitrate(
            bitrate_orig=bitrate_orig,
            complexity=complexity,
            motion=motion,
            codec=codec,
            vmaf_threshold=threshold,
            mode=mode,
            grain=grain,
            texture=texture
        )
        
        if mode == "CRF":
            cq = calculate_initial_cq(complexity, codec)
            param_str = f"CQ={cq}"
        else:
            param_str = f"{target_bitrate:.2f}M"
        
        print(f"{desc:<35} {codec:<6} {mode:<4} {threshold:<3} {target_ratio:<7.1f} {target_bitrate:<8.2f} {param_str}")


if __name__ == "__main__":
    # Run all examples
    example_single_pass_encoding()
    example_adaptive_encoding()
    example_crf_with_ceiling()
    example_comparison_table()
    
    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)


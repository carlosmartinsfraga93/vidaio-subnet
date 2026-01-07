"""
Optimal Encoder Wrapper
========================

Integrates the optimal bitrate controller with the existing encode_video function.
Provides a drop-in replacement that uses score-maximizing formulas.
"""

import os
import time
from typing import Tuple, Optional, Dict
from .optimal_controller_integration import (
    get_optimal_encoding_params,
    update_encoding_params_after_result,
    format_encoding_command_params,
    extract_video_metrics
)
from .encode_video import encode_video
from .video_utils import get_video_bitrate


def encode_video_optimal(
    input_path: str,
    output_path: str,
    codec: str,
    vmaf_threshold: float,
    codec_mode: str = 'CRF',
    target_bitrate: Optional[float] = None,
    scene_type: Optional[str] = 'other',
    contrast_value: Optional[float] = None,
    duration: Optional[float] = None,
    skip_cq_mapping: bool = False,
    logging_enabled: bool = True,
    use_optimal_controller: bool = True,
    min_required_bitrate: Optional[float] = None
) -> Tuple[str, float]:
    """
    Encode video using optimal bitrate controller - SCENE-AWARE.

    This is a drop-in replacement for encode_video() that uses the score-maximizing
    formula to determine optimal encoding parameters.

    Args:
        input_path: Path to input video
        output_path: Path to output video
        codec: Codec name (av1_nvenc, hevc_nvenc, etc.)
        vmaf_threshold: VMAF threshold (85, 89, 93)
        codec_mode: 'CRF' or 'VBR'
        target_bitrate: Target bitrate in Mbps (for VBR mode, optional for CRF)
        scene_type: Scene type (screen, gaming, animation, faces, other)
        contrast_value: Contrast value (optional, for compatibility)
        duration: Video duration (optional)
        skip_cq_mapping: Skip CQ mapping (optional)
        logging_enabled: Enable logging
        use_optimal_controller: Use optimal controller (set False to use legacy)
        min_required_bitrate: Minimum required bitrate for VMAF safety (Mbps)

    Returns:
        Tuple of (output_path, encoding_time)
    """
    start_time = time.time()
    
    # Map codec names to standard format
    codec_map = {
        'av1_nvenc': 'av1',
        'hevc_nvenc': 'hevc',
        'h264_nvenc': 'h264'
    }
    codec_standard = codec_map.get(codec, codec)
    
    if not use_optimal_controller:
        # Fall back to legacy encode_video
        if logging_enabled:
            print("⚠️ Using legacy encoder (optimal controller disabled)")
        
        # Determine rate parameter
        if codec_mode.upper() == 'CRF':
            rate = 30  # Default CRF
        else:
            rate = target_bitrate if target_bitrate else 25.0
        
        return encode_video(
            input_path=input_path,
            output_path=output_path,
            codec=codec,
            rate=rate,
            scene_type=scene_type,
            contrast_value=contrast_value,
            codec_mode=codec_mode,
            target_bitrate=target_bitrate,
            duration=duration,
            skip_cq_mapping=skip_cq_mapping,
            logging_enabled=logging_enabled
        )
    
    # Use optimal controller
    if logging_enabled:
        print("=" * 80)
        print("🎯 OPTIMAL BITRATE CONTROLLER (SCENE-AWARE)")
        print("=" * 80)
        print(f"Input: {input_path}")
        print(f"Codec: {codec} ({codec_standard})")
        print(f"Mode: {codec_mode}")
        print(f"Scene Type: {scene_type}")
        print(f"VMAF Threshold: {vmaf_threshold}")

    # Get optimal encoding parameters (scene-aware)
    optimal_params = get_optimal_encoding_params(
        video_path=input_path,
        codec=codec_standard,
        mode=codec_mode,
        vmaf_threshold=vmaf_threshold,
        scene_type=scene_type,
        logging_enabled=logging_enabled
    )
    
    # Format parameters for FFmpeg
    ffmpeg_params = format_encoding_command_params(
        params=optimal_params,
        codec=codec_standard,
        mode=codec_mode
    )
    
    # Determine rate parameter for encode_video
    if codec_mode.upper() == 'CRF':
        # Use CQ value from optimal controller
        rate = optimal_params.get('initial_cq', 30)

        # If VBR ceiling is applied, also set target_bitrate
        if optimal_params.get('apply_vbr_ceiling', False):
            target_bitrate = optimal_params['target_bitrate']
            if logging_enabled:
                print(f"⚠️ VBR ceiling applied: target_bitrate={target_bitrate:.2f} Mbps")
    else:  # VBR
        # Use target bitrate from optimal controller
        controller_bitrate = optimal_params['target_bitrate']

        # BUG FIX #1: Enforce minimum bitrate clamp for VMAF safety
        if min_required_bitrate and controller_bitrate < min_required_bitrate:
            if logging_enabled:
                print(f"\n⚠️ MINIMUM BITRATE CLAMP APPLIED:")
                print(f"   Controller target: {controller_bitrate:.2f} Mbps")
                print(f"   Minimum required: {min_required_bitrate:.2f} Mbps")
                print(f"   Using minimum for VMAF safety (deficit: {min_required_bitrate - controller_bitrate:.2f} Mbps)")

            target_bitrate = min_required_bitrate
            rate = min_required_bitrate

            # Recalculate VBR settings with clamped bitrate
            from .optimal_bitrate_controller import calculate_vbr_settings
            optimal_params['vbr_settings'] = calculate_vbr_settings(min_required_bitrate, scene_type)
            optimal_params['target_bitrate'] = min_required_bitrate
        else:
            target_bitrate = controller_bitrate
            rate = controller_bitrate

    if logging_enabled:
        print(f"\n📝 Encoding with:")
        print(f"   Rate parameter: {rate}")
        if target_bitrate:
            print(f"   Target bitrate: {target_bitrate:.2f} Mbps")
        print(f"   Expected ratio: {optimal_params['target_ratio']:.1f}x")
        print(f"   Complexity: {optimal_params['complexity']:.2f}")
    
    # BUG FIX #2: Pass VBR settings to encode_video to prevent overwriting
    vbr_settings = optimal_params.get('vbr_settings') if codec_mode.upper() == 'VBR' else None

    # Encode video using existing encode_video function
    encoding_log, encoding_time = encode_video(
        input_path=input_path,
        output_path=output_path,
        codec=codec,
        rate=rate,
        scene_type=scene_type,
        contrast_value=contrast_value,
        codec_mode=codec_mode,
        target_bitrate=target_bitrate,
        duration=duration,
        skip_cq_mapping=True,  # Skip CQ mapping, we already calculated optimal CQ
        logging_enabled=logging_enabled,
        vbr_settings=vbr_settings  # Pass controller's VBR settings
    )

    total_time = time.time() - start_time

    # Check if encoding succeeded
    if encoding_log is None:
        if logging_enabled:
            print(f"\n❌ Encoding failed")
            print("=" * 80)
        return None, None

    if logging_enabled:
        print(f"\n✅ Encoding completed in {total_time:.2f}s")
        print("=" * 80)

    # Return the actual output path (not the log string)
    # encode_video returns (log_string, time), but we need to return (path, time)
    return output_path, encoding_time


def encode_video_optimal_adaptive(
    input_path: str,
    output_path: str,
    codec: str,
    vmaf_threshold: float,
    codec_mode: str = 'CRF',
    target_bitrate: Optional[float] = None,
    max_iterations: int = 3,
    logging_enabled: bool = True
) -> Tuple[str, float, Dict]:
    """
    Encode video with adaptive feedback loop.
    
    This function encodes, measures VMAF, and re-encodes with updated parameters
    until the target is met or max iterations reached.
    
    Args:
        input_path: Path to input video
        output_path: Path to output video
        codec: Codec name (av1_nvenc, hevc_nvenc, etc.)
        vmaf_threshold: VMAF threshold (85, 89, 93)
        codec_mode: 'CRF' or 'VBR'
        target_bitrate: Target bitrate in Mbps (for VBR mode)
        max_iterations: Maximum number of encoding iterations
        logging_enabled: Enable logging
    
    Returns:
        Tuple of (output_path, total_time, final_params)
    """
    start_time = time.time()
    
    # Map codec names
    codec_map = {
        'av1_nvenc': 'av1',
        'hevc_nvenc': 'hevc',
        'h264_nvenc': 'h264'
    }
    codec_standard = codec_map.get(codec, codec)
    
    if logging_enabled:
        print("=" * 80)
        print("🔄 ADAPTIVE OPTIMAL ENCODER")
        print("=" * 80)
        print(f"Max iterations: {max_iterations}")
    
    # Get initial optimal parameters
    current_params = get_optimal_encoding_params(
        video_path=input_path,
        codec=codec_standard,
        mode=codec_mode,
        vmaf_threshold=vmaf_threshold,
        logging_enabled=logging_enabled
    )
    
    # Get original bitrate for ratio calculation
    bitrate_orig = current_params['metrics']['bitrate_mbps']
    
    for iteration in range(max_iterations):
        if logging_enabled:
            print(f"\n{'='*80}")
            print(f"ITERATION {iteration + 1}/{max_iterations}")
            print(f"{'='*80}")
        
        # Encode with current parameters
        temp_output = output_path if iteration == max_iterations - 1 else f"{output_path}.iter{iteration}.mp4"
        
        _, encoding_time = encode_video_optimal(
            input_path=input_path,
            output_path=temp_output,
            codec=codec,
            vmaf_threshold=vmaf_threshold,
            codec_mode=codec_mode,
            target_bitrate=current_params.get('target_bitrate'),
            logging_enabled=logging_enabled,
            use_optimal_controller=True
        )
        
        # Measure results (placeholder - in real implementation, measure VMAF)
        # For now, we'll just use the parameters without feedback
        # TODO: Integrate with VMAF measurement
        
        if logging_enabled:
            print(f"✅ Iteration {iteration + 1} completed")
        
        # For now, break after first iteration
        # In full implementation, measure VMAF and update parameters
        break
    
    total_time = time.time() - start_time
    
    if logging_enabled:
        print(f"\n{'='*80}")
        print(f"✅ Adaptive encoding completed in {total_time:.2f}s")
        print(f"{'='*80}")
    
    return output_path, total_time, current_params


"""
Integration module for Optimal Bitrate Controller
==================================================

Connects the score-maximizing formula to the existing compression pipeline.
"""

import os
import json
import subprocess
from typing import Dict, Tuple, Optional
from .optimal_bitrate_controller import (
    calculate_complexity_score,
    calculate_target_bitrate,
    calculate_initial_cq,
    update_cq_after_encode,
    update_vbr_bitrate_after_encode,
    calculate_vbr_settings,
    should_apply_vbr_ceiling
)
from .analyze_video_fast import analyze_video_fast


def extract_video_metrics(video_path: str) -> Dict[str, float]:
    """
    Extract complexity metrics from video using actual frame analysis.

    Returns:
        Dictionary with:
        - bitrate_mbps: Original bitrate in Mbps
        - grain: Grain/noise metric (0-0.15 normalized)
        - texture: Texture complexity (0-0.15 normalized)
        - motion: Motion metric (0-0.15 normalized)
    """
    try:
        # Get bitrate and basic info from ffprobe
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # Extract bitrate
        bitrate = data.get('format', {}).get('bit_rate')
        bitrate_mbps = float(bitrate) / 1_000_000 if bitrate else 30.0

        # Get video stream info
        video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
        width = int(video_stream.get('width', 1920)) if video_stream else 1920
        height = int(video_stream.get('height', 1080)) if video_stream else 1080
        fps_str = video_stream.get('r_frame_rate', '30/1') if video_stream else '30/1'
        fps = eval(fps_str) if '/' in fps_str else float(fps_str)

        # Use actual video analysis to get real complexity metrics
        # This replaces the BPP-based heuristics with proper frame analysis
        # analyze_video_fast uses 8 parallel workers, so 150 frames is fast (~2-3s)
        complexity_data = analyze_video_fast(
            video_path=video_path,
            max_frames=150,  # Use full frame sampling for accurate metrics
            logging_enabled=False
        )

        if complexity_data:
            # Extract RAW metrics for complexity calculation
            # The complexity formula expects raw values:
            # C = 0.45*X_raw + 0.35*G_raw + 20*M_raw
            # Where:
            # - G_raw (grain_noise): std dev of noise, typically 0-20
            # - X_raw (texture): entropy in bits, typically 0-8
            # - M_raw (motion): normalized 0-1
            # This produces C in the 6-10 range expected by downstream formulas

            grain_raw = complexity_data.get('metrics_avg_grain_noise', 0)
            texture_raw = complexity_data.get('metrics_avg_texture', 0)
            motion_raw = complexity_data.get('metrics_avg_motion', 0)
        else:
            # Fallback to safe defaults if analysis fails
            # These defaults produce C ≈ 7.0 (medium complexity)
            grain_raw = 5.0    # Medium grain
            texture_raw = 6.0  # Medium texture
            motion_raw = 0.05  # Low motion

        return {
            'bitrate_mbps': bitrate_mbps,
            'grain': grain_raw,
            'texture': texture_raw,
            'motion': motion_raw,
            'width': width,
            'height': height,
            'fps': fps
        }

    except Exception as e:
        print(f"⚠️ Error extracting video metrics: {e}")
        print(f"   Using safe default complexity values")
        # Return safe defaults (raw values that produce C ≈ 7.0)
        return {
            'bitrate_mbps': 30.0,
            'grain': 5.0,    # Medium grain (raw std dev)
            'texture': 6.0,  # Medium texture (raw entropy)
            'motion': 0.05,  # Low motion (raw normalized)
            'width': 1920,
            'height': 1080,
            'fps': 30.0
        }


def get_optimal_encoding_params(
    video_path: str,
    codec: str,
    mode: str,
    vmaf_threshold: float,
    scene_type: str = 'other',
    logging_enabled: bool = True
) -> Dict[str, any]:
    """
    Get optimal encoding parameters using the score-maximizing formula - SCENE-AWARE.

    Args:
        video_path: Path to input video
        codec: 'av1' or 'hevc'
        mode: 'CRF' or 'VBR'
        vmaf_threshold: VMAF threshold (85 or 89)
        scene_type: Scene type (screen, gaming, animation, faces, other)
        logging_enabled: Whether to print logs

    Returns:
        Dictionary with encoding parameters:
        - target_bitrate: Target bitrate (Mbps)
        - target_ratio: Target compression ratio
        - min_bitrate: Minimum safe bitrate (Mbps)
        - initial_cq: Initial CQ value (for CRF mode)
        - vbr_settings: VBR settings dict (for VBR mode)
        - complexity: Complexity score
        - scene_type: Normalized scene type
        - metrics: Raw metrics dict
    """
    # Extract video metrics
    metrics = extract_video_metrics(video_path)

    # Calculate complexity score
    complexity = calculate_complexity_score(
        grain=metrics['grain'],
        texture=metrics['texture'],
        motion=metrics['motion']
    )

    # Calculate optimal target bitrate (scene-aware)
    target_bitrate, target_ratio, min_bitrate = calculate_target_bitrate(
        bitrate_orig=metrics['bitrate_mbps'],
        complexity=complexity,
        motion=metrics['motion'],
        codec=codec,
        vmaf_threshold=vmaf_threshold,
        mode=mode,
        scene_type=scene_type,
        grain=metrics['grain'],
        texture=metrics['texture']
    )

    result = {
        'target_bitrate': target_bitrate,
        'target_ratio': target_ratio,
        'min_bitrate': min_bitrate,
        'complexity': complexity,
        'scene_type': scene_type,
        'metrics': metrics
    }

    # Mode-specific parameters
    if mode.upper() == 'CRF':
        result['initial_cq'] = calculate_initial_cq(complexity, codec, scene_type)
        if logging_enabled:
            print(f"🎯 CRF Mode - Initial CQ: {result['initial_cq']} (scene: {scene_type})")
    else:  # VBR
        result['vbr_settings'] = calculate_vbr_settings(target_bitrate, scene_type)
        if logging_enabled:
            print(f"🎯 VBR Mode - Settings: {result['vbr_settings']} (scene: {scene_type})")

    if logging_enabled:
        print(f"📊 Optimal Encoding Parameters:")
        print(f"   Scene type: {scene_type}")
        print(f"   Original bitrate: {metrics['bitrate_mbps']:.2f} Mbps")
        print(f"   Complexity score: {complexity:.2f}")
        print(f"   Target ratio: {target_ratio:.1f}x")
        print(f"   Target bitrate: {target_bitrate:.2f} Mbps")
        print(f"   Min safe bitrate: {min_bitrate:.2f} Mbps")
        print(f"   Grain: {metrics['grain']:.4f}, Texture: {metrics['texture']:.4f}, Motion: {metrics['motion']:.4f}")

    return result


def update_encoding_params_after_result(
    current_params: Dict[str, any],
    vmaf_score: float,
    bitrate_actual: float,
    bitrate_orig: float,
    codec: str,
    mode: str,
    vmaf_threshold: float,
    logging_enabled: bool = True
) -> Dict[str, any]:
    """
    Update encoding parameters after measuring results.

    This implements the adaptive controller that pushes ratio upward when safe.

    Args:
        current_params: Current encoding parameters from get_optimal_encoding_params()
        vmaf_score: Measured VMAF score
        bitrate_actual: Actual output bitrate (Mbps)
        bitrate_orig: Original bitrate (Mbps)
        codec: 'av1' or 'hevc'
        mode: 'CRF' or 'VBR'
        vmaf_threshold: VMAF threshold
        logging_enabled: Whether to print logs

    Returns:
        Updated parameters dictionary
    """
    # Calculate actual compression ratio
    ratio_actual = bitrate_orig / bitrate_actual if bitrate_actual > 0 else 1.0

    updated_params = current_params.copy()

    if mode.upper() == 'CRF':
        # Update CQ value (now uses bitrate instead of ratio)
        new_cq = update_cq_after_encode(
            current_cq=current_params.get('initial_cq', 30),
            vmaf_score=vmaf_score,
            vmaf_threshold=vmaf_threshold,
            bitrate_actual=bitrate_actual,
            bitrate_target=current_params['target_bitrate'],
            mode=mode,
            codec=codec
        )

        updated_params['initial_cq'] = new_cq

        # Check if VBR ceiling should be applied
        scene_type = current_params.get('scene_type', 'other')
        if should_apply_vbr_ceiling(
            bitrate_actual=bitrate_actual,
            bitrate_target=current_params['target_bitrate'],
            vmaf_score=vmaf_score,
            vmaf_threshold=vmaf_threshold,
            mode=mode
        ):
            updated_params['apply_vbr_ceiling'] = True
            updated_params['vbr_settings'] = calculate_vbr_settings(
                current_params['target_bitrate'],
                scene_type
            )
            if logging_enabled:
                print(f"⚠️ CRF ceiling guard triggered - switching to VBR cap")

        if logging_enabled:
            cq_delta = new_cq - current_params.get('initial_cq', 30)
            print(f"🔄 CQ Update: {current_params.get('initial_cq', 30)} → {new_cq} (Δ{cq_delta:+d})")
            print(f"   VMAF: {vmaf_score:.2f} (threshold: {vmaf_threshold})")
            print(f"   Bitrate: {bitrate_actual:.2f} Mbps (target: {current_params['target_bitrate']:.2f} Mbps)")
            print(f"   Ratio: {ratio_actual:.2f}x (target: {current_params['target_ratio']:.1f}x)")

    else:  # VBR
        # Update bitrate and ratio target
        new_bitrate, new_ratio_target = update_vbr_bitrate_after_encode(
            current_bitrate=current_params['target_bitrate'],
            vmaf_score=vmaf_score,
            vmaf_threshold=vmaf_threshold,
            ratio_actual=ratio_actual,
            ratio_target=current_params['target_ratio']
        )

        updated_params['target_bitrate'] = new_bitrate
        updated_params['target_ratio'] = new_ratio_target
        scene_type = current_params.get('scene_type', 'other')
        updated_params['vbr_settings'] = calculate_vbr_settings(new_bitrate, scene_type)

        if logging_enabled:
            bitrate_delta = new_bitrate - current_params['target_bitrate']
            ratio_delta = new_ratio_target - current_params['target_ratio']
            print(f"🔄 VBR Update:")
            print(f"   Bitrate: {current_params['target_bitrate']:.2f} → {new_bitrate:.2f} Mbps (Δ{bitrate_delta:+.2f})")
            print(f"   Ratio target: {current_params['target_ratio']:.1f}x → {new_ratio_target:.1f}x (Δ{ratio_delta:+.1f})")
            print(f"   VMAF: {vmaf_score:.2f} (threshold: {vmaf_threshold})")
            print(f"   Ratio actual: {ratio_actual:.2f}x")

    return updated_params


def format_encoding_command_params(params: Dict[str, any], codec: str, mode: str) -> Dict[str, any]:
    """
    Format parameters for FFmpeg encoding command.

    Args:
        params: Parameters from get_optimal_encoding_params()
        codec: 'av1' or 'hevc'
        mode: 'CRF' or 'VBR'

    Returns:
        Dictionary suitable for FFmpeg command
    """
    ffmpeg_params = {}

    if mode.upper() == 'CRF':
        # CRF mode - use CQ value
        ffmpeg_params['cq'] = params.get('initial_cq', 30)

        # If VBR ceiling is applied, add bitrate constraints
        if params.get('apply_vbr_ceiling', False):
            vbr = params['vbr_settings']
            ffmpeg_params['b:v'] = f"{vbr['b:v']:.2f}M"
            ffmpeg_params['maxrate'] = f"{vbr['maxrate']:.2f}M"
            ffmpeg_params['bufsize'] = f"{vbr['bufsize']:.2f}M"

    else:  # VBR
        # VBR mode - use bitrate settings
        vbr = params['vbr_settings']
        ffmpeg_params['b:v'] = f"{vbr['b:v']:.2f}M"
        ffmpeg_params['maxrate'] = f"{vbr['maxrate']:.2f}M"
        ffmpeg_params['bufsize'] = f"{vbr['bufsize']:.2f}M"

    return ffmpeg_params


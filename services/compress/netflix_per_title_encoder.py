"""
Netflix Per-Title Encoding Module

This module implements Netflix's per-title encoding approach:
1. Encode the same scene with multiple CQ values (convex hull search)
2. Calculate VMAF for each encoding
3. Find the optimal CQ that achieves target VMAF with smallest file size

References:
- Netflix Tech Blog: "Per-Title Encode Optimization"
- https://netflixtechblog.com/per-title-encode-optimization-7e99442b62a2
"""

import os
import time
import concurrent.futures
from typing import Dict, List, Tuple, Optional, Any

from utils.encode_video import encode_video
from utils.calculate_vmaf_adv import calculate_vmaf_advanced
from utils.calculate_vmaf_fast import calculate_vmaf_fast_libvmaf


# ============================================================================
# CONFIGURATION
# ============================================================================

# Hardcoded switch to enable/disable Netflix per-title encoding
ENABLE_NETFLIX_PER_TITLE = False  # Set to True to enable

# CQ probe points for convex hull search
# These are the CQ values we'll test to find the optimal encoding
CQ_PROBE_POINTS = {
    'av1_nvenc': [12, 18, 24, 30],      # 4 probe points for AV1
    'hevc_nvenc': [15, 21, 27, 33],     # 4 probe points for HEVC
    'h264_nvenc': [15, 21, 27, 33],     # 4 probe points for H.264
}

# Minimum CQ probe points (for faster mode)
CQ_PROBE_POINTS_FAST = {
    'av1_nvenc': [15, 22, 30],          # 3 probe points (faster)
    'hevc_nvenc': [18, 25, 32],         # 3 probe points (faster)
    'h264_nvenc': [18, 25, 32],         # 3 probe points (faster)
}

# VMAF calculation settings for per-title encoding
VMAF_SETTINGS_PER_TITLE = {
    'use_sampling': True,
    'num_clips': 3,           # 3 clips for good accuracy
    'clip_duration': 2,       # 2 seconds per clip
    'use_parallel': False,    # Set to True to enable parallel VMAF
}

# Enable parallel encoding (encode multiple CQ values simultaneously)
ENABLE_PARALLEL_ENCODING = True

# Enable parallel VMAF calculation
ENABLE_PARALLEL_VMAF = True

# Enable fast VMAF calculation (uses libvmaf directly, 5-10x faster)
# Disabled for now due to compatibility issues - use standard method with vmafneg
ENABLE_FAST_VMAF = False


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def get_cq_probe_points(codec: str, fast_mode: bool = False) -> List[int]:
    """
    Get CQ probe points for the given codec.
    
    Args:
        codec: Codec name (av1_nvenc, hevc_nvenc, h264_nvenc)
        fast_mode: If True, use fewer probe points for faster encoding
        
    Returns:
        List of CQ values to probe
    """
    probe_points = CQ_PROBE_POINTS_FAST if fast_mode else CQ_PROBE_POINTS
    return probe_points.get(codec, CQ_PROBE_POINTS['av1_nvenc'])


def encode_with_cq(
    scene_path: str,
    output_dir: str,
    codec: str,
    cq: int,
    scene_type: str,
    codec_mode: str,
    target_bitrate: Optional[float],
    duration: float,
    probe_index: int,
    logging_enabled: bool = True
) -> Tuple[Optional[str], float, int]:
    """
    Encode a scene with a specific CQ value.

    Args:
        scene_path: Path to scene video file
        output_dir: Directory to save encoded file
        codec: Codec to use
        cq: CQ value to use
        scene_type: Scene classification
        codec_mode: Codec mode (CRF/VBR/CBR)
        target_bitrate: Target bitrate for VBR/CBR
        duration: Scene duration
        probe_index: Index of this probe point
        logging_enabled: Enable logging

    Returns:
        Tuple of (encoded_path, encoding_time, cq_used)
    """
    output_path = os.path.join(output_dir, f"probe_{probe_index}_cq{cq}.mp4")

    try:
        if logging_enabled:
            print(f"      🎬 Probe {probe_index}: Encoding with CQ={cq}...")

        start_time = time.time()
        _, encoding_time = encode_video(
            input_path=scene_path,
            output_path=output_path,
            codec=codec,
            rate=cq,
            scene_type=scene_type,
            contrast_value=0.5,
            codec_mode=codec_mode,
            target_bitrate=target_bitrate,
            duration=duration,
            skip_cq_mapping=True,  # CQ is already codec-specific
            logging_enabled=False  # Suppress individual encoding logs
        )

        if os.path.exists(output_path):
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            if logging_enabled:
                print(f"         ✅ CQ={cq}: {file_size_mb:.2f} MB, {encoding_time:.1f}s")
            return output_path, encoding_time, cq
        else:
            if logging_enabled:
                print(f"         ❌ CQ={cq}: Encoding failed")
            return None, 0.0, cq

    except Exception as e:
        if logging_enabled:
            print(f"         ❌ CQ={cq}: Error - {e}")
        return None, 0.0, cq


def calculate_vmaf_for_probe(
    original_path: str,
    encoded_path: str,
    cq: int,
    config: Dict[str, Any],
    logging_enabled: bool = True
) -> Tuple[int, Optional[float], float]:
    """
    Calculate VMAF score for a probe encoding.

    Args:
        original_path: Path to original scene
        encoded_path: Path to encoded scene
        cq: CQ value used
        config: Configuration dict
        logging_enabled: Enable logging

    Returns:
        Tuple of (cq, vmaf_score, file_size_mb)
    """
    try:
        if logging_enabled:
            print(f"      📊 Calculating VMAF for CQ={cq}...")

        # Use fast VMAF if enabled (5-10x faster)
        if ENABLE_FAST_VMAF:
            vmaf_config = config.get('vmaf_calculation', {})
            num_clips = vmaf_config.get('vmaf_num_clips', VMAF_SETTINGS_PER_TITLE['num_clips'])
            clip_duration = vmaf_config.get('vmaf_clip_duration', VMAF_SETTINGS_PER_TITLE['clip_duration'])

            # Get model path
            use_vmafneg = vmaf_config.get('use_vmafneg', False)
            if use_vmafneg:
                model_path = config.get('model_paths', {}).get('vmafneg_model')
            else:
                model_path = config.get('model_paths', {}).get('default_vmaf_model')

            vmaf_score = calculate_vmaf_fast_libvmaf(
                reference_path=original_path,
                distorted_path=encoded_path,
                model_path=model_path,
                num_clips=num_clips,
                clip_duration=clip_duration,
                max_frames_per_clip=30,
                logging_enabled=logging_enabled
            )

            # Fallback to old method if fast VMAF fails
            if vmaf_score is None:
                if logging_enabled:
                    print(f"         ⚠️ Fast VMAF failed, falling back to standard method...")
                vmaf_score = calculate_vmaf_advanced(
                    input_file=original_path,
                    encoded_file=encoded_path,
                    use_sampling=VMAF_SETTINGS_PER_TITLE['use_sampling'],
                    num_clips=VMAF_SETTINGS_PER_TITLE['num_clips'],
                    clip_duration=VMAF_SETTINGS_PER_TITLE['clip_duration'],
                    use_downscaling=False,
                    use_parallel=VMAF_SETTINGS_PER_TITLE['use_parallel'],
                    use_vmafneg=config.get('vmaf_calculation', {}).get('use_vmafneg', False),
                    default_vmaf_model_path_config=config.get('model_paths', {}).get('default_vmaf_model'),
                    vmafneg_model_path_config=config.get('model_paths', {}).get('vmafneg_model'),
                    use_frame_rate_scaling=False,
                    logging_enabled=False
                )
        else:
            # Use original VMAF calculation (slower but more configurable)
            vmaf_score = calculate_vmaf_advanced(
                input_file=original_path,
                encoded_file=encoded_path,
                use_sampling=VMAF_SETTINGS_PER_TITLE['use_sampling'],
                num_clips=VMAF_SETTINGS_PER_TITLE['num_clips'],
                clip_duration=VMAF_SETTINGS_PER_TITLE['clip_duration'],
                use_downscaling=False,
                use_parallel=VMAF_SETTINGS_PER_TITLE['use_parallel'],
                use_vmafneg=config.get('vmaf_calculation', {}).get('use_vmafneg', False),
                default_vmaf_model_path_config=config.get('model_paths', {}).get('default_vmaf_model'),
                vmafneg_model_path_config=config.get('model_paths', {}).get('vmafneg_model'),
                use_frame_rate_scaling=False,
                logging_enabled=False
            )

        file_size_mb = os.path.getsize(encoded_path) / (1024 * 1024)

        if logging_enabled and vmaf_score is not None:
            print(f"         ✅ CQ={cq}: VMAF={vmaf_score:.2f}, Size={file_size_mb:.2f} MB")

        return cq, vmaf_score, file_size_mb

    except Exception as e:
        if logging_enabled:
            print(f"         ❌ CQ={cq}: VMAF calculation failed - {e}")
        return cq, None, 0.0


def find_optimal_cq(
    probe_results: List[Tuple[int, float, float]],
    target_vmaf: float,
    logging_enabled: bool = True
) -> Tuple[int, float, float]:
    """
    Find the optimal CQ value that achieves target VMAF with smallest file size.

    Uses linear interpolation between probe points to estimate the best CQ.

    Args:
        probe_results: List of (cq, vmaf, file_size_mb) tuples
        target_vmaf: Target VMAF score
        logging_enabled: Enable logging

    Returns:
        Tuple of (optimal_cq, estimated_vmaf, estimated_file_size_mb)
    """
    # Filter out failed probes
    valid_results = [(cq, vmaf, size) for cq, vmaf, size in probe_results if vmaf is not None]

    if not valid_results:
        if logging_enabled:
            print(f"      ❌ No valid probe results!")
        return 25, 0.0, 0.0  # Fallback to default CQ

    # Sort by CQ (ascending)
    valid_results.sort(key=lambda x: x[0])

    if logging_enabled:
        print(f"\n      📊 Probe Results:")
        for cq, vmaf, size in valid_results:
            status = "✅" if vmaf >= target_vmaf else "⚠️"
            print(f"         {status} CQ={cq}: VMAF={vmaf:.2f}, Size={size:.2f} MB")

    # Find the two probe points that bracket the target VMAF
    lower_probe = None
    upper_probe = None

    for i in range(len(valid_results)):
        cq, vmaf, size = valid_results[i]

        if vmaf >= target_vmaf:
            upper_probe = (cq, vmaf, size)
            if i > 0:
                lower_probe = valid_results[i - 1]
            break

    # Case 1: Target VMAF is higher than all probes → use lowest CQ
    if upper_probe is None:
        optimal_cq, optimal_vmaf, optimal_size = valid_results[0]
        if logging_enabled:
            print(f"      🎯 Target VMAF too high, using lowest CQ={optimal_cq}")
        return optimal_cq, optimal_vmaf, optimal_size

    # Case 2: Target VMAF is lower than all probes → use highest CQ
    if lower_probe is None:
        optimal_cq, optimal_vmaf, optimal_size = upper_probe
        if logging_enabled:
            print(f"      🎯 Target VMAF already achieved, using CQ={optimal_cq}")
        return optimal_cq, optimal_vmaf, optimal_size

    # Case 3: Interpolate between lower and upper probes
    lower_cq, lower_vmaf, lower_size = lower_probe
    upper_cq, upper_vmaf, upper_size = upper_probe

    # Linear interpolation to find optimal CQ
    # VMAF increases as CQ decreases (inverse relationship)
    vmaf_range = upper_vmaf - lower_vmaf
    cq_range = upper_cq - lower_cq

    if vmaf_range > 0:
        # Interpolate CQ based on VMAF
        vmaf_ratio = (target_vmaf - lower_vmaf) / vmaf_range
        optimal_cq = int(lower_cq + (cq_range * (1 - vmaf_ratio)))  # Inverse relationship

        # Estimate VMAF and file size at optimal CQ
        estimated_vmaf = target_vmaf
        estimated_size = lower_size + (upper_size - lower_size) * (1 - vmaf_ratio)
    else:
        # VMAF range is too small, use upper probe
        optimal_cq = upper_cq
        estimated_vmaf = upper_vmaf
        estimated_size = upper_size

    if logging_enabled:
        print(f"      🎯 Optimal CQ={optimal_cq} (interpolated between {lower_cq} and {upper_cq})")
        print(f"         Estimated VMAF={estimated_vmaf:.2f}, Size={estimated_size:.2f} MB")

    return optimal_cq, estimated_vmaf, estimated_size


def netflix_per_title_encoding(
    scene_metadata: Dict[str, Any],
    config: Dict[str, Any],
    resources: Dict[str, Any],
    target_vmaf: float = 93.0,
    target_quality_level: Optional[str] = None,
    logging_enabled: bool = True
) -> Dict[str, Any]:
    """
    Netflix per-title encoding: Find optimal CQ by probing multiple values.

    This is the main entry point for Netflix per-title encoding.

    Process:
    1. Get CQ probe points for the codec
    2. Encode scene with each CQ value (optionally in parallel)
    3. Calculate VMAF for each encoding (optionally in parallel)
    4. Find optimal CQ that achieves target VMAF with smallest file size
    5. Return the best encoding

    Args:
        scene_metadata: Scene metadata dict
        config: Configuration dict
        resources: Resources dict (temp directories, etc.)
        target_vmaf: Target VMAF score
        target_quality_level: Target quality level (High/Medium/Low)
        logging_enabled: Enable logging

    Returns:
        Updated scene metadata with encoding results
    """
    if logging_enabled:
        print(f"\n   🎬 Netflix Per-Title Encoding")

    start_time = time.time()

    # Extract scene info
    scene_path = scene_metadata.get('path')
    scene_number = scene_metadata.get('scene_number', 0)
    scene_type = scene_metadata.get('scene_type', 'default')
    scene_duration = scene_metadata.get('duration', 0)

    # Get codec from metadata or config
    codec = scene_metadata.get('original_video_metadata', {}).get('target_codec') or \
            config.get('video_processing', {}).get('codec', 'av1_nvenc')

    codec_mode = config.get('video_processing', {}).get('codec_mode', 'CRF')
    target_bitrate = config.get('video_processing', {}).get('target_bitrate')

    # Create temp directory for probe encodings
    temp_dir = resources.get('temp_dir', '/tmp')
    probe_dir = os.path.join(temp_dir, f"netflix_probes_scene_{scene_number}")
    os.makedirs(probe_dir, exist_ok=True)

    # Get CQ probe points
    fast_mode = config.get('video_processing', {}).get('netflix_fast_mode', False)
    cq_probes = get_cq_probe_points(codec, fast_mode=fast_mode)

    if logging_enabled:
        print(f"      📋 Scene {scene_number}: {scene_type}")
        print(f"      🎯 Target VMAF: {target_vmaf:.1f}")
        print(f"      🔍 Probing CQ values: {cq_probes}")

    # Step 1: Encode with all CQ probe points
    encoding_results = []
    encoding_start_time = time.time()

    if ENABLE_PARALLEL_ENCODING:
        if logging_enabled:
            print(f"      ⚡ Parallel encoding enabled ({len(cq_probes)} encodings)")

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(cq_probes)) as executor:
            futures = []
            for i, cq in enumerate(cq_probes):
                future = executor.submit(
                    encode_with_cq,
                    scene_path, probe_dir, codec, cq, scene_type,
                    codec_mode, target_bitrate, scene_duration, i, logging_enabled
                )
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                encoding_results.append(result)
    else:
        if logging_enabled:
            print(f"      🔄 Sequential encoding ({len(cq_probes)} encodings)")

        for i, cq in enumerate(cq_probes):
            result = encode_with_cq(
                scene_path, probe_dir, codec, cq, scene_type,
                codec_mode, target_bitrate, scene_duration, i, logging_enabled
            )
            encoding_results.append(result)

    actual_encoding_time = time.time() - encoding_start_time

    # Filter successful encodings
    successful_encodings = [(path, enc_time, cq) for path, enc_time, cq in encoding_results if path is not None]

    if not successful_encodings:
        if logging_enabled:
            print(f"      ❌ All probe encodings failed!")
        return scene_metadata

    total_encoding_time = sum(enc_time for _, enc_time, _ in successful_encodings)

    if logging_enabled:
        if ENABLE_PARALLEL_ENCODING:
            print(f"      ✅ Encoded {len(successful_encodings)}/{len(cq_probes)} probes in {actual_encoding_time:.1f}s (wall-clock time)")
            print(f"         💡 Individual encoding times: {', '.join([f'{t:.1f}s' for _, t, _ in successful_encodings])}")
        else:
            print(f"      ✅ Encoded {len(successful_encodings)}/{len(cq_probes)} probes in {total_encoding_time:.1f}s")

    # Step 2: Calculate VMAF for all encodings
    vmaf_results = []
    vmaf_start_time = time.time()

    if ENABLE_PARALLEL_VMAF:
        if logging_enabled:
            print(f"      ⚡ Parallel VMAF calculation enabled")

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(successful_encodings)) as executor:
            futures = []
            for encoded_path, _, cq in successful_encodings:
                future = executor.submit(
                    calculate_vmaf_for_probe,
                    scene_path, encoded_path, cq, config, logging_enabled
                )
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                vmaf_results.append(result)
    else:
        if logging_enabled:
            print(f"      🔄 Sequential VMAF calculation")

        for encoded_path, _, cq in successful_encodings:
            result = calculate_vmaf_for_probe(
                scene_path, encoded_path, cq, config, logging_enabled
            )
            vmaf_results.append(result)

    actual_vmaf_time = time.time() - vmaf_start_time

    if logging_enabled:
        if ENABLE_PARALLEL_VMAF:
            print(f"      ✅ VMAF calculated for {len(vmaf_results)} probes in {actual_vmaf_time:.1f}s (wall-clock time)")
        else:
            print(f"      ✅ VMAF calculated for {len(vmaf_results)} probes in {actual_vmaf_time:.1f}s")

    # Step 3: Find optimal CQ
    optimal_cq, estimated_vmaf, estimated_size = find_optimal_cq(
        vmaf_results, target_vmaf, logging_enabled
    )

    # Step 4: Find the encoding closest to optimal CQ
    # (We may already have it from our probes!)
    best_encoding = None
    best_cq_diff = float('inf')

    for encoded_path, enc_time, cq in successful_encodings:
        cq_diff = abs(cq - optimal_cq)
        if cq_diff < best_cq_diff:
            best_cq_diff = cq_diff
            best_encoding = (encoded_path, enc_time, cq)

    if best_encoding is None:
        if logging_enabled:
            print(f"      ❌ No suitable encoding found!")
        return scene_metadata

    best_path, best_enc_time, best_cq = best_encoding

    # Get actual VMAF for the best encoding
    best_vmaf = None
    for cq, vmaf, size in vmaf_results:
        if cq == best_cq:
            best_vmaf = vmaf
            break

    # Copy best encoding to final output path
    output_scene_path = os.path.join(
        resources.get('encoded_scenes_dir', temp_dir),
        f"scene_{scene_number}_encoded.mp4"
    )

    import shutil
    shutil.copy2(best_path, output_scene_path)

    # Clean up probe encodings
    try:
        shutil.rmtree(probe_dir)
    except Exception as e:
        if logging_enabled:
            print(f"      ⚠️ Failed to clean up probe directory: {e}")

    total_time = time.time() - start_time

    if logging_enabled:
        print(f"\n      ✅ Netflix Per-Title Complete:")
        print(f"         Optimal CQ: {best_cq}")
        vmaf_str = f"{best_vmaf:.2f}" if best_vmaf is not None else "N/A"
        print(f"         Actual VMAF: {vmaf_str}")
        print(f"         File size: {os.path.getsize(output_scene_path) / (1024 * 1024):.2f} MB")
        print(f"         Total time: {total_time:.1f}s")

    # Update scene metadata
    scene_metadata.update({
        'encoded_path': output_scene_path,
        'encoding_time': total_time,
        'cq_used': best_cq,
        'actual_vmaf': best_vmaf,
        'encoding_method': 'netflix_per_title',
        'probe_results': vmaf_results,
        'optimal_cq': optimal_cq,
        'estimated_vmaf': estimated_vmaf
    })

    return scene_metadata


# ============================================================================
# INTEGRATION HELPER
# ============================================================================

def should_use_netflix_per_title(config: Dict[str, Any]) -> bool:
    """
    Check if Netflix per-title encoding should be used.

    This checks both the hardcoded switch and config settings.

    Args:
        config: Configuration dict

    Returns:
        True if Netflix per-title should be used
    """
    # Check hardcoded switch first
    if not ENABLE_NETFLIX_PER_TITLE:
        return False

    # Check config override
    return config.get('video_processing', {}).get('use_netflix_per_title', False)





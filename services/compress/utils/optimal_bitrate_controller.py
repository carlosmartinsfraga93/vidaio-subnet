"""
Optimal Bitrate Controller - Scene-Aware Score-Maximizing Formula
==================================================================

Primary objective: Maximize compression ratio (15×–20×)
Hard constraint: Never miss VMAF threshold (miss ⇒ Final = 0)
Secondary objective: Keep small VMAF safety margin; don't waste bits

Supports: CRF/VBR modes, AV1/HEVC codecs
Scene types: Screen, Gaming, Animation, Faces, Other

UPDATED: Now includes scene-aware parameters for optimal scoring
"""

import math
from typing import Tuple, Dict, Optional


def clamp(min_val: float, value: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(value, max_val))


def calculate_complexity_score(grain: float, texture: float, motion: float) -> float:
    """
    Calculate content complexity score from RAW analyzer metrics.

    C = 0.45*X_raw + 0.35*G_raw + 20*M_raw

    Args:
        grain: G_raw - Grain/noise std dev from analyze_video_fast (typically 0-20)
        texture: X_raw - Texture entropy in bits from analyze_video_fast (typically 0-8)
        motion: M_raw - Motion metric from analyze_video_fast (normalized 0-1)

    Returns:
        Complexity score C (typically 6-10 for normal content)

    Example:
        grain=2.27, texture=5.64, motion=0.097
        C = 0.45*5.64 + 0.35*2.27 + 20*0.097 = 2.538 + 0.795 + 1.94 = 5.27
    """
    return 0.45 * texture + 0.35 * grain + 20.0 * motion


# Scene-aware configuration constants
SCENE_TYPES = ['screen', 'gaming', 'animation', 'faces', 'other']

# Scene-dependent bitrate normalization ranges (4K30 tuned)
SCENE_BITRATE_CLAMP = {
    'screen': (18.0, 60.0),
    'faces': (20.0, 65.0),
    'gaming': (22.0, 70.0),
    'animation': (20.0, 75.0),
    'other': (20.0, 65.0)
}

# Scene-specific complexity thresholds C0(scene)
# Below this threshold, no complexity backoff is applied
SCENE_COMPLEXITY_THRESHOLD = {
    'animation': 3.0,
    'faces': 4.0,
    'gaming': 4.5,
    'screen': 6.0,
    'other': 4.0
}

# Codec-specific backoff coefficients
# HEVC is more sensitive to complexity, AV1 holds quality better
CODEC_BACKOFF_COEFFICIENT = {
    'hevc': 1.5,
    'av1': 1.0
}

# Minimum bitrate floors for 4K30, target_vmaf >= 93 (Mbps)
SCENE_MIN_BITRATE_4K30_T93 = {
    'animation': 10.0,
    'faces': 8.0,
    'gaming': 7.0,
    'screen': 4.0,
    'other': 8.0
}

# Scene base minimum bitrates (Mbps, 4K30, aggressive but safe)
SCENE_BASE_BITRATE = {
    'screen': 1.0,
    'faces': 2.2,
    'gaming': 2.8,
    'animation': 2.4,
    'other': 2.0
}

# Scene complexity coefficients for minimum bitrate
SCENE_COMPLEXITY_COEFF = {
    'screen': {'a': 0.18, 'b': 6.0},
    'faces': {'a': 0.26, 'b': 8.0},
    'gaming': {'a': 0.30, 'b': 9.0},
    'animation': {'a': 0.28, 'b': 8.0},
    'other': {'a': 0.25, 'b': 8.0}
}

# Scene-aware initial CQ values for CRF mode
SCENE_INITIAL_CQ = {
    'av1': {
        'screen': 32,
        'gaming': 28,
        'animation': 30,
        'faces': 27,
        'other': 29
    },
    'hevc': {
        'screen': 28,
        'gaming': 24,
        'animation': 26,
        'faces': 23,
        'other': 25
    }
}

# Scene-specific buffer size multipliers for VBR
SCENE_VBR_BUFSIZE = {
    'screen': 2.5,
    'faces': 2.5,
    'gaming': 3.0,  # Higher for gaming
    'animation': 3.0,  # Higher for animation
    'other': 2.5
}


def normalize_scene_type(scene_type: Optional[str]) -> str:
    """
    Normalize scene type to standard format.

    Args:
        scene_type: Scene type string (case-insensitive)

    Returns:
        Normalized scene type (lowercase)
    """
    if not scene_type:
        return 'other'

    scene_lower = scene_type.lower()

    # Map common variations
    if 'screen' in scene_lower or 'desktop' in scene_lower:
        return 'screen'
    elif 'game' in scene_lower or 'gaming' in scene_lower:
        return 'gaming'
    elif 'anim' in scene_lower or 'cartoon' in scene_lower:
        return 'animation'
    elif 'face' in scene_lower or 'portrait' in scene_lower or 'people' in scene_lower:
        return 'faces'
    else:
        return 'other'


def normalize_original_bitrate(
    bitrate_orig: float,
    complexity: float,
    scene_type: str = 'other',
    use_floor: bool = True
) -> float:
    """
    Normalize original bitrate to reduce ffprobe noise (scene-aware).

    Scene-dependent clamp (4K30 tuned):
    - Screen: clamp(18, B_orig, 60)
    - Faces: clamp(20, B_orig, 65)
    - Gaming: clamp(22, B_orig, 70)
    - Animation: clamp(20, B_orig, 75)
    - Other: clamp(20, B_orig, 65)

    Then apply hard-content floor:
    B_floor(C) = clamp(20, 18 + 6*(C - 6.0), 45)
    B_orig,n = max(B_orig,n, B_floor(C))

    Args:
        bitrate_orig: Original bitrate from ffprobe (Mbps)
        complexity: Complexity score C
        scene_type: Scene type (screen, gaming, animation, faces, other)
        use_floor: Whether to apply content-based floor

    Returns:
        Normalized bitrate
    """
    # Normalize scene type
    scene = normalize_scene_type(scene_type)

    # Scene-dependent clamp
    min_bitrate, max_bitrate = SCENE_BITRATE_CLAMP.get(scene, (20.0, 65.0))
    b_norm = clamp(min_bitrate, bitrate_orig, max_bitrate)

    # Optional content-based floor
    if use_floor:
        b_floor = clamp(20.0, 18.0 + 6.0 * (complexity - 6.0), 45.0)
        b_norm = max(b_norm, b_floor)

    return b_norm


def calculate_target_ratio(
    complexity: float,
    vmaf_threshold: float,
    codec: str,
    scene_type: str = 'other'
) -> float:
    """
    Calculate target compression ratio with VMAF-aware base ratios.

    Step A: Raw complexity is already computed (passed in)

    Step B: Choose base ratio by VMAF target
    - target_vmaf >= 93: base_ratio = 10-14×
    - target_vmaf >= 89: base_ratio = 14-18×
    - else: base_ratio = 18.5×

    Step C: Backoff ratio by scene-adjusted complexity
    C0(scene) thresholds:
    - animation: 3.0
    - faces: 4.0
    - gaming: 4.5
    - screen: 6.0

    ratio = base_ratio - k × max(0, C - C0)

    k coefficients (codec-dependent):
    - HEVC: k = 1.5 (more sensitive)
    - AV1: k = 1.0 (holds quality better)

    Clamp ratio:
    - target_vmaf >= 93: ratio ∈ [8, 14]
    - target_vmaf >= 89: ratio ∈ [10, 18.5]
    - else: ratio ∈ [15, 20]

    Args:
        complexity: Complexity score C (raw metrics)
        vmaf_threshold: VMAF threshold (85, 89, 93, etc.)
        codec: 'av1' or 'hevc'
        scene_type: Scene type (screen, gaming, animation, faces, other)

    Returns:
        Target compression ratio
    """
    # Normalize scene type
    scene = normalize_scene_type(scene_type)

    # Step B: Choose base ratio by VMAF target
    if vmaf_threshold >= 93:
        base_ratio = 12.0  # Middle of 10-14 range
        ratio_min, ratio_max = 8.0, 14.0
    elif vmaf_threshold >= 89:
        base_ratio = 16.0  # Middle of 14-18 range
        ratio_min, ratio_max = 10.0, 18.5
    else:
        base_ratio = 18.5
        ratio_min, ratio_max = 15.0, 20.0

    # Step C: Get scene-specific complexity threshold
    c0 = SCENE_COMPLEXITY_THRESHOLD.get(scene, 4.0)

    # Get codec-specific backoff coefficient
    codec_lower = codec.lower()
    if 'av1' in codec_lower:
        k = CODEC_BACKOFF_COEFFICIENT['av1']
    else:  # HEVC
        k = CODEC_BACKOFF_COEFFICIENT['hevc']

    # Calculate target ratio with complexity backoff
    r_target = base_ratio - k * max(0.0, complexity - c0)

    # Clamp to appropriate range
    return clamp(ratio_min, r_target, ratio_max)


def calculate_minimum_bitrate(
    complexity: float,
    motion: float,
    codec: str,
    vmaf_threshold: float,
    mode: str,
    scene_type: str = 'other'
) -> float:
    """
    Predict minimum bitrate to clear VMAF threshold - SCENE-AWARE.

    Safety margin:
    - m = 2 (CRF)
    - m = 3 (VBR) - VBR tends to be less stable

    Scene base minima (Mbps, 4K30, aggressive but safe):
    - Screen: B0 = 1.0
    - Faces: B0 = 2.2
    - Gaming: B0 = 2.8
    - Animation: B0 = 2.4
    - Other: B0 = 2.0

    Complexity term:
    B_min = B0 * (1 + a_s * max(0, C - 6.2)) + b_s * M

    Coefficients:
    - Screen: a_s=0.18, b_s=6.0
    - Faces: a_s=0.26, b_s=8.0
    - Gaming: a_s=0.30, b_s=9.0
    - Animation: a_s=0.28, b_s=8.0
    - Other: a_s=0.25, b_s=8.0

    Then apply:
    - Threshold strictness: T=89 → ×1.10, T=85 → ×1.00
    - VBR risk bump: VBR → ×1.08, CRF → ×1.00

    Args:
        complexity: Complexity score C
        motion: Motion metric M
        codec: 'av1' or 'hevc' (not used in scene-aware version)
        vmaf_threshold: VMAF threshold (85 or 89)
        mode: 'CRF' or 'VBR'
        scene_type: Scene type (screen, gaming, animation, faces, other)

    Returns:
        Minimum bitrate (Mbps)
    """
    # Normalize scene type
    scene = normalize_scene_type(scene_type)

    # Get scene base bitrate
    b0 = SCENE_BASE_BITRATE.get(scene, 2.0)

    # Get scene complexity coefficients
    coeffs = SCENE_COMPLEXITY_COEFF.get(scene, {'a': 0.25, 'b': 8.0})
    a_s = coeffs['a']
    b_s = coeffs['b']

    # Calculate minimum bitrate
    b_min = b0 * (1.0 + a_s * max(0.0, complexity - 6.2)) + b_s * motion

    # Threshold strictness bias
    if vmaf_threshold >= 93:
        # CRITICAL: High VMAF thresholds (93+) need much more conservative bitrates
        # Aggressive ratio chasing at T=93 causes failures
        b_min *= 1.50  # 50% increase for T=93+
    elif vmaf_threshold >= 89:
        b_min *= 1.10
    else:  # 85
        b_min *= 1.00

    # VBR risk bump
    if mode.upper() == 'VBR':
        b_min *= 1.08

    # Clamp to reasonable range (increased upper bound for high VMAF)
    max_bitrate = 15.0 if vmaf_threshold >= 93 else 10.0
    return clamp(0.8, b_min, max_bitrate)


def calculate_target_bitrate(
    bitrate_orig: float,
    complexity: float,
    motion: float,
    codec: str,
    vmaf_threshold: float,
    mode: str,
    scene_type: str = 'other',
    grain: float = 0.0,
    texture: float = 0.0
) -> Tuple[float, float, float]:
    """
    Calculate optimal target bitrate for score maximization - SCENE-AWARE.

    This is the core "push ratio as far as possible without losing threshold" rule.

    Args:
        bitrate_orig: Original bitrate from ffprobe (Mbps)
        complexity: Complexity score C (or will be calculated from grain/texture/motion)
        motion: Motion metric M
        codec: 'av1' or 'hevc'
        vmaf_threshold: VMAF threshold (85 or 89)
        mode: 'CRF' or 'VBR'
        scene_type: Scene type (screen, gaming, animation, faces, other)
        grain: Grain metric (optional, for complexity calculation)
        texture: Texture metric (optional, for complexity calculation)

    Returns:
        Tuple of (target_bitrate, target_ratio, min_bitrate)
    """
    # Calculate complexity if not provided
    if complexity == 0.0 and (grain > 0.0 or texture > 0.0):
        complexity = calculate_complexity_score(grain, texture, motion)

    # Normalize scene type
    scene = normalize_scene_type(scene_type)

    # Step 1: Normalize original bitrate (scene-aware)
    b_orig_norm = normalize_original_bitrate(bitrate_orig, complexity, scene_type, use_floor=True)

    # Step 2: Calculate target ratio (VMAF-aware, scene-aware, codec-aware)
    r_target = calculate_target_ratio(complexity, vmaf_threshold, codec, scene_type)

    # Step 3: Bitrate implied by ratio
    b_ratio = b_orig_norm / r_target

    # Step 4: Calculate minimum bitrate for threshold safety (scene-aware)
    b_min = calculate_minimum_bitrate(complexity, motion, codec, vmaf_threshold, mode, scene_type)

    # Step 5: Apply resolution-based bitrate floor for high VMAF targets
    # For 4K30, target_vmaf >= 93, enforce scene-specific minimums
    if vmaf_threshold >= 93:
        # Get video resolution from bitrate_orig (approximate)
        # 4K30 typically has bitrate > 15 Mbps, 1080p30 typically < 10 Mbps
        is_4k = bitrate_orig > 15.0

        if is_4k:
            # Apply 4K30 floor
            floor_4k = SCENE_MIN_BITRATE_4K30_T93.get(scene, 8.0)
            b_min = max(b_min, floor_4k)
        else:
            # For 1080p, scale down by 4x (resolution ratio)
            floor_1080p = SCENE_MIN_BITRATE_4K30_T93.get(scene, 8.0) / 4.0
            b_min = max(b_min, floor_1080p)

    # Step 6: Final target bitrate (push ratio but respect safety)
    b_target = max(b_ratio, b_min)

    return b_target, r_target, b_min


def calculate_initial_cq(complexity: float, codec: str, scene_type: str = 'other') -> int:
    """
    Calculate initial CQ value for CRF mode - SCENE-AWARE.

    Scene-aware initial CQ:

    AV1:
    - Screen: 32
    - Gaming: 28
    - Animation: 30
    - Faces: 27
    - Other: 29

    HEVC:
    - Screen: 28
    - Gaming: 24
    - Animation: 26
    - Faces: 23
    - Other: 25

    Then adjust for complexity:
    CQ_init = CQ_scene + 1.8 * (C - 6.2)

    Clamp:
    - AV1: [20, 38]
    - HEVC: [18, 34]

    Args:
        complexity: Complexity score C
        codec: 'av1' or 'hevc'
        scene_type: Scene type (screen, gaming, animation, faces, other)

    Returns:
        Initial CQ value
    """
    codec_lower = codec.lower()
    scene = normalize_scene_type(scene_type)

    # Get codec-specific scene baselines
    if 'av1' in codec_lower:
        cq_scene = SCENE_INITIAL_CQ['av1'].get(scene, 29)
        cq_min, cq_max = 20, 38
    else:  # HEVC
        cq_scene = SCENE_INITIAL_CQ['hevc'].get(scene, 25)
        cq_min, cq_max = 18, 34

    # Adjust for complexity
    cq = cq_scene + 1.8 * (complexity - 6.2)

    return int(clamp(cq_min, cq, cq_max))


def update_cq_after_encode(
    current_cq: int,
    vmaf_score: float,
    vmaf_threshold: float,
    bitrate_actual: float,
    bitrate_target: float,
    mode: str,
    codec: str
) -> int:
    """
    Update CQ value after measuring VMAF and actual bitrate - UPDATED LOGIC.

    Safety margin:
    - m = 2 (CRF)
    - m = 3 (VBR)

    Update logic (REVISED):
    1. If threshold at risk:
       - margin < 0: CQ -= 4 (rescue immediately)
       - margin < m: CQ -= 2
    2. If safe, check bitrate:
       - B_actual > 1.10*B_target: CQ += 2 (squeeze more)
       - margin ≥ m + 4: CQ += 1 (keep squeezing)
       - Else: keep

    Args:
        current_cq: Current CQ value
        vmaf_score: Measured VMAF score
        vmaf_threshold: VMAF threshold
        bitrate_actual: Actual output bitrate (Mbps)
        bitrate_target: Target bitrate (Mbps)
        mode: 'CRF' or 'VBR'
        codec: 'av1' or 'hevc'

    Returns:
        Updated CQ value
    """
    # Safety margin
    margin_safety = 2 if mode.upper() == 'CRF' else 3

    # Calculate margin
    margin = vmaf_score - vmaf_threshold

    # Determine CQ adjustment
    cq_delta = 0

    # Priority 1: Threshold safety
    if margin < 0:
        cq_delta = -4  # Emergency rescue
    elif margin < margin_safety:
        cq_delta = -2  # Cautious rescue

    # Priority 2: Push compression (only if safe)
    elif bitrate_actual > 1.10 * bitrate_target:
        cq_delta = +2  # Bitrate too high, squeeze more
    elif margin >= margin_safety + 4:
        cq_delta = +1  # High margin, keep squeezing
    # Else: keep current CQ

    new_cq = current_cq + cq_delta

    # Clamp to valid ranges
    codec_lower = codec.lower()
    if 'av1' in codec_lower:
        return int(clamp(20, new_cq, 38))
    else:  # HEVC
        return int(clamp(18, new_cq, 34))


def update_vbr_bitrate_after_encode(
    current_bitrate: float,
    vmaf_score: float,
    vmaf_threshold: float,
    ratio_actual: float,
    ratio_target: float
) -> Tuple[float, float]:
    """
    Update VBR bitrate target after encoding (single-step controller).

    Safety margin: m = 3 (VBR)

    Update rule:
    - If margin < 0: B_target *= 1.35 (emergency), R_target = max(15, R_target - 2)
    - Else if 0 ≤ margin < m: B_target *= 1.15, R_target = max(15, R_target - 1)
    - Else if margin ≥ m + 4 and R_actual < 20: B_target *= 0.92 (squeeze more)
    - Else: keep

    Args:
        current_bitrate: Current target bitrate (Mbps)
        vmaf_score: Measured VMAF score
        vmaf_threshold: VMAF threshold
        ratio_actual: Actual compression ratio achieved
        ratio_target: Current target ratio

    Returns:
        Tuple of (new_bitrate, new_ratio_target)
    """
    margin_safety = 3  # VBR safety margin
    margin = vmaf_score - vmaf_threshold

    new_bitrate = current_bitrate
    new_ratio_target = ratio_target

    # Emergency: threshold missed
    if margin < 0:
        new_bitrate *= 1.35
        new_ratio_target = max(15.0, ratio_target - 2.0)

    # Caution: too close to threshold
    elif 0 <= margin < margin_safety:
        new_bitrate *= 1.15
        new_ratio_target = max(15.0, ratio_target - 1.0)

    # Opportunity: safe margin, can squeeze more
    elif margin >= margin_safety + 4 and ratio_actual < 20:
        new_bitrate *= 0.92

    # Else: keep current settings

    return new_bitrate, new_ratio_target


def calculate_vbr_settings(target_bitrate: float, scene_type: str = 'other') -> Dict[str, float]:
    """
    Calculate VBR rate control settings (tight VBV) - SCENE-AWARE.

    b:v = B_target
    maxrate = 1.05 * B_target
    bufsize = scene-dependent multiplier * B_target

    Scene-specific buffer sizes:
    - Screen: 2.5×
    - Faces: 2.5×
    - Gaming: 3.0× (higher for spikes)
    - Animation: 3.0× (higher for spikes)
    - Other: 2.5×

    Args:
        target_bitrate: Target bitrate (Mbps)
        scene_type: Scene type (screen, gaming, animation, faces, other)

    Returns:
        Dictionary with VBR settings
    """
    scene = normalize_scene_type(scene_type)
    bufsize_mult = SCENE_VBR_BUFSIZE.get(scene, 2.5)

    # Convert to Python float to avoid numpy.float64 issues
    return {
        'b:v': float(target_bitrate),
        'maxrate': float(1.05 * target_bitrate),
        'bufsize': float(bufsize_mult * target_bitrate)
    }


def should_apply_vbr_ceiling(
    bitrate_actual: float,
    bitrate_target: float,
    vmaf_score: float,
    vmaf_threshold: float,
    mode: str
) -> bool:
    """
    Check if CRF ceiling guard should be applied.

    Optional: "CRF ceiling guard"
    If CRF output bitrate is unexpectedly high (hurting ratio), enforce a VBR "cap" pass:
    If B_actual > 1.25 * B_target and margin ≥ m: run VBR with B_target to stabilize.

    This gives you the best of both: CRF for score, VBR for stability.

    Args:
        bitrate_actual: Actual output bitrate (Mbps)
        bitrate_target: Target bitrate (Mbps)
        vmaf_score: VMAF score
        vmaf_threshold: VMAF threshold
        mode: Current mode ('CRF' or 'VBR')

    Returns:
        True if VBR ceiling should be applied
    """
    if mode.upper() != 'CRF':
        return False

    margin_safety = 2  # CRF safety margin
    margin = vmaf_score - vmaf_threshold

    # Apply VBR cap if bitrate is too high and we have safety margin
    return bitrate_actual > 1.25 * bitrate_target and margin >= margin_safety


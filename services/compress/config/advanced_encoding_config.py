"""
Advanced Encoding Configuration System

This module provides granular control over encoding parameters based on:
- Scene type (animation, low-action, medium-action, high-action)
- Codec (av1_nvenc, hevc_nvenc, h264_nvenc)
- Quality level (High, Medium, Low)
- Bitrate range (low, medium, high)

Each combination has optimized CQ values and quality multipliers to achieve
target VMAF scores while maximizing compression.
"""

# Scene type mappings
SCENE_TYPES = {
    'animation': 'Animation / Cartoon / Rendered Graphics',
    'low-action': 'Faces / People',
    'medium-action': 'Screen Content / Text',
    'high-action': 'Gaming Content',
    'default': 'other'
}

# Codec efficiency ratings (relative to H.264)
# DYNAMIC COMPRESSION: Balanced multipliers that adapt to content
# These represent realistic compression ratios while maintaining quality
CODEC_EFFICIENCY = {
    'av1_nvenc': 0.25,   # AV1 can achieve 75% reduction vs H.264 (was 0.02)
    'hevc_nvenc': 0.35,  # HEVC can achieve 65% reduction vs H.264 (was 0.03)
    'h264_nvenc': 0.50,  # H.264 baseline - 50% reduction with better encoding (was 0.05)
    'libx265': 0.35,     # Software HEVC - same as hevc_nvenc
    'libx264': 0.50,     # Software H.264 - same as h264_nvenc
}

# Bitrate range classifications (Mbps)
BITRATE_RANGES = {
    'low': (0, 10),      # Low bitrate videos
    'medium': (10, 30),  # Medium bitrate videos
    'high': (30, 100),   # High bitrate videos
}

# ============================================================================
# MINIMUM BITRATE REQUIREMENTS FOR VBR MODE
# ============================================================================
# FORMULA-BASED BITRATE TARGETS (Based on Production Data Analysis)
# ============================================================================
# These are scene-specific bitrate floors derived from production logs
# Below these thresholds, VMAF collapses regardless of CQ settings
#
# Base values are for 1080p @ 30fps
# Scale by: B_target = B_base × (W×H / 1920×1080) × (FPS / 30)
#
# Production evidence:
# - Gaming: 2.4 Mbps → VMAF 90.65 ✅ | 0.9 Mbps → VMAF 58.46 ❌
# - Animation: 5.4 Mbps → VMAF 97.79 ✅ | 3.4 Mbps → VMAF 28.95 ❌
# - Screen: 4.5-7.4 Mbps → VMAF 97-99 ✅
# ============================================================================

BASE_BITRATE_TARGETS_1080P_30FPS = {
    'screen': 5.0,      # Screen content: 4.5-7.0 Mbps range
    'gaming': 2.5,      # Gaming: 2.4-4.0 Mbps range (HARD FLOOR!)
    'animation': 6.0,   # Animation: 5.4-9.0 Mbps range (HARD FLOOR!)
    'low-action': 3.5,  # Faces/people: 3.0-5.0 Mbps range
    'medium-action': 4.0,  # General content: 3.5-6.0 Mbps range
    'high-action': 2.5,    # Same as gaming (high motion)
    'default': 4.0
}

# Legacy minimum bitrate (kept for backward compatibility)
# Will be replaced by formula-based calculation
MINIMUM_BITRATE_FOR_QUALITY = {
    'high-action': {  # Gaming content
        'High': 2.5,
        'Medium': 2.0,
        'Low': 1.5
    },
    'medium-action': {  # General content
        'High': 2.0,
        'Medium': 1.5,
        'Low': 1.0
    },
    'low-action': {  # Faces/Text
        'High': 1.5,
        'Medium': 1.0,
        'Low': 0.8
    },
    'animation': {  # Animation
        'High': 1.2,
        'Medium': 0.8,
        'Low': 0.6
    },
    'default': {  # Fallback
        'High': 1.8,
        'Medium': 1.2,
        'Low': 0.9
    }
}


# ============================================================================
# CODEC-SPECIFIC CQ VALUES
# ============================================================================
# These are the actual CQ/QP values used by each codec
# Lower CQ = Higher quality, larger files
# Higher CQ = Lower quality, smaller files

CODEC_CQ_VALUES = {
    # AV1 NVENC - Reference codec (model trained on this)
    # ⚠️ FORMULA-BASED APPROACH: CQ values from production data analysis
    # Production evidence: CQ 20-24 range achieves VMAF 90+ with good compression
    # Lower CQ = Better quality, bitrate target ensures compression
    'av1_nvenc': {
        'High': {  # VMAF 93 target - Production: CQ 18-22
            'animation': 20,      # Animation: CQ 22-24 in production
            'low-action': 20,     # Faces/text: CQ 22-24 in production
            'medium-action': 20,  # General: CQ 22-24 in production
            'high-action': 18,    # Gaming: CQ 20-22 in production
            'screen': 20,         # Screen: CQ 22-24 in production
            'gaming': 18,         # Gaming: CQ 20-22 in production
            'default': 20
        },
        'Medium': {  # VMAF 89 target - Production: CQ 20-24
            'animation': 22,      # Animation: CQ 22-24 in production
            'low-action': 22,     # Faces/text: CQ 22-24 in production
            'medium-action': 22,  # General: CQ 22-24 in production
            'high-action': 20,    # Gaming: CQ 20-22 in production
            'screen': 22,         # Screen: CQ 22-24 in production
            'gaming': 20,         # Gaming: CQ 20-22 in production
            'default': 22
        },
        'Low': {  # VMAF 85 target - Production: CQ 22-26
            'animation': 24,      # Animation: CQ 22-24 in production
            'low-action': 24,     # Faces/text: CQ 22-24 in production
            'medium-action': 24,  # General: CQ 22-24 in production
            'high-action': 22,    # Gaming: CQ 20-22 in production
            'screen': 24,         # Screen: CQ 22-24 in production
            'gaming': 22,         # Gaming: CQ 20-22 in production
            'default': 24
        }
    },

    # HEVC NVENC - Hardware HEVC encoder
    # HEVC uses QP scale (0-51), formula-based approach from production data
    # HEVC needs ~2 points lower CQ than AV1 for same quality
    'hevc_nvenc': {
        'High': {  # VMAF 93 target - Production: CQ 18-22
            'animation': 18,      # Animation: CQ 20-22 in production
            'low-action': 18,     # Faces/text: CQ 20-22 in production
            'medium-action': 18,  # General: CQ 20-22 in production
            'high-action': 16,    # Gaming: CQ 18-20 in production
            'screen': 18,         # Screen: CQ 20-22 in production
            'gaming': 16,         # Gaming: CQ 18-20 in production
            'default': 18
        },
        'Medium': {  # VMAF 89 target - Production: CQ 20-24
            'animation': 20,      # Animation: CQ 20-22 in production
            'low-action': 20,     # Faces/text: CQ 20-22 in production
            'medium-action': 20,  # General: CQ 20-22 in production
            'high-action': 18,    # Gaming: CQ 18-20 in production
            'screen': 20,         # Screen: CQ 20-22 in production
            'gaming': 18,         # Gaming: CQ 18-20 in production
            'default': 20
        },
        'Low': {  # VMAF 85 target - Production: CQ 22-26
            'animation': 22,      # Animation: CQ 20-22 in production
            'low-action': 22,     # Faces/text: CQ 20-22 in production
            'medium-action': 22,  # General: CQ 20-22 in production
            'high-action': 20,    # Gaming: CQ 18-20 in production
            'screen': 22,         # Screen: CQ 20-22 in production
            'gaming': 20,         # Gaming: CQ 18-20 in production
            'default': 22
        }
    },

    # H.264 NVENC - Hardware H.264 encoder
    # H.264 uses QP scale (0-51), less efficient so needs lower CQ than AV1/HEVC
    # H.264 needs ~2 points lower CQ than HEVC for same quality
    'h264_nvenc': {
        'High': {  # VMAF 93 target - Production: CQ 18-22
            'animation': 18,      # Animation: CQ 20-22 in production
            'low-action': 18,     # Faces/text: CQ 20-22 in production
            'medium-action': 18,  # General: CQ 20-22 in production
            'high-action': 16,    # Gaming: CQ 18-20 in production
            'screen': 18,         # Screen: CQ 20-22 in production
            'gaming': 16,         # Gaming: CQ 18-20 in production
            'default': 18
        },
        'Medium': {  # VMAF 89 target - Production: CQ 20-24
            'animation': 20,      # Animation: CQ 20-22 in production
            'low-action': 20,     # Faces/text: CQ 20-22 in production
            'medium-action': 20,  # General: CQ 20-22 in production
            'high-action': 18,    # Gaming: CQ 18-20 in production
            'screen': 20,         # Screen: CQ 20-22 in production
            'gaming': 18,         # Gaming: CQ 18-20 in production
            'default': 20
        },
        'Low': {  # VMAF 85 target - Production: CQ 22-26
            'animation': 22,      # Animation: CQ 20-22 in production
            'low-action': 22,     # Faces/text: CQ 20-22 in production
            'medium-action': 22,  # General: CQ 20-22 in production
            'high-action': 20,    # Gaming: CQ 18-20 in production
            'screen': 22,         # Screen: CQ 20-22 in production
            'gaming': 20,         # Gaming: CQ 18-20 in production
            'default': 22
        }
    }
}


# ============================================================================
# QUALITY MULTIPLIERS FOR VBR MODE
# ============================================================================
# These multipliers adjust the target bitrate based on quality level and scene
# Formula: target_bitrate = input_bitrate * codec_efficiency * quality_multiplier

QUALITY_MULTIPLIERS = {
    'High': {  # VMAF 93 - Need more bitrate headroom
        'animation': 1.4,      # Animation compresses well, moderate headroom
        'low-action': 1.6,     # Faces need more bitrate for detail
        'medium-action': 1.5,  # Balanced
        'high-action': 1.7,    # High motion needs most bitrate
        'default': 1.5
    },
    'Medium': {  # VMAF 89 - Balanced bitrate
        'animation': 1.2,      # Animation compresses well
        'low-action': 1.3,     # Faces need moderate bitrate
        'medium-action': 1.3,  # Balanced
        'high-action': 1.4,    # High motion needs more
        'default': 1.3
    },
    'Low': {  # VMAF 85 - Aggressive compression
        'animation': 0.9,      # Very aggressive for animation
        'low-action': 1.0,     # Moderate for faces
        'medium-action': 1.0,  # Balanced
        'high-action': 1.1,    # Still need some headroom for motion
        'default': 1.0
    }
}


# ============================================================================
# BITRATE-SPECIFIC CQ ADJUSTMENTS
# ============================================================================
# Additional CQ adjustments based on input bitrate range
# These are ADDED to the base CQ values above
# Positive values = higher CQ = more compression (for high bitrate inputs)
# Negative values = lower CQ = less compression (for low bitrate inputs)

BITRATE_CQ_ADJUSTMENTS = {
    'low': {  # 0-10 Mbps input - Already compressed, be gentle
        'High': -2,    # Lower CQ to preserve quality
        'Medium': -1,  # Slight reduction
        'Low': 0       # No change
    },
    'medium': {  # 10-30 Mbps input - Standard range
        'High': 0,     # No adjustment
        'Medium': 0,   # No adjustment
        'Low': 0       # No adjustment
    },
    'high': {  # 30+ Mbps input - High bitrate, can compress more
        'High': 1,     # Slightly higher CQ
        'Medium': 2,   # More compression
        'Low': 3       # Aggressive compression
    }
}


# ============================================================================
# CODEC-SPECIFIC BITRATE MULTIPLIER ADJUSTMENTS
# ============================================================================
# Fine-tune bitrate multipliers per codec
# These are MULTIPLIED with the quality multipliers above

CODEC_BITRATE_MULTIPLIERS = {
    'av1_nvenc': {
        'low': 1.1,    # AV1 needs slightly more bitrate for low-bitrate inputs
        'medium': 1.0,
        'high': 0.9    # AV1 can compress high-bitrate inputs more
    },
    'hevc_nvenc': {
        'low': 1.05,
        'medium': 1.0,
        'high': 0.95
    },
    'h264_nvenc': {
        'low': 1.0,
        'medium': 1.0,
        'high': 1.0    # H.264 less efficient, keep consistent
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_bitrate_range(bitrate_mbps: float) -> str:
    """Classify bitrate into low/medium/high range."""
    for range_name, (min_br, max_br) in BITRATE_RANGES.items():
        if min_br <= bitrate_mbps < max_br:
            return range_name
    return 'high'  # Default to high for anything above 100 Mbps


def get_cq_value(
    codec: str,
    quality_level: str,
    scene_type: str,
    input_bitrate_mbps: float = None
) -> int:
    """
    Get the optimal CQ value for given parameters.

    Args:
        codec: Codec name (av1_nvenc, hevc_nvenc, h264_nvenc)
        quality_level: Quality level (High, Medium, Low)
        scene_type: Scene type (animation, low-action, medium-action, high-action)
        input_bitrate_mbps: Input video bitrate in Mbps (optional, reserved for future use)

    Returns:
        Optimal CQ value
    """
    # Get base CQ value from standard lookup table
    codec_config = CODEC_CQ_VALUES.get(codec, CODEC_CQ_VALUES['av1_nvenc'])
    quality_config = codec_config.get(quality_level, codec_config['Medium'])
    base_cq = quality_config.get(scene_type, quality_config['default'])

    # Apply bitrate adjustment if provided
    if input_bitrate_mbps is not None:
        bitrate_range = get_bitrate_range(input_bitrate_mbps)
        adjustment = BITRATE_CQ_ADJUSTMENTS[bitrate_range].get(quality_level, 0)
        base_cq += adjustment

    # Clamp to valid range
    if codec in ['hevc_nvenc', 'h264_nvenc']:
        return max(10, min(51, base_cq))
    else:  # av1_nvenc
        return max(10, min(63, base_cq))


def get_quality_multiplier(
    quality_level: str,
    scene_type: str,
    codec: str = None,
    input_bitrate_mbps: float = None
) -> float:
    """
    Get the optimal quality multiplier for VBR mode.

    Args:
        quality_level: Quality level (High, Medium, Low)
        scene_type: Scene type (animation, low-action, medium-action, high-action)
        codec: Codec name (optional, for codec-specific adjustments)
        input_bitrate_mbps: Input video bitrate in Mbps (optional)

    Returns:
        Quality multiplier for bitrate calculation
    """
    # Get base multiplier
    quality_config = QUALITY_MULTIPLIERS.get(quality_level, QUALITY_MULTIPLIERS['Medium'])
    base_multiplier = quality_config.get(scene_type, quality_config['default'])

    # Apply codec-specific adjustment if provided
    if codec and input_bitrate_mbps is not None:
        bitrate_range = get_bitrate_range(input_bitrate_mbps)
        codec_adjustment = CODEC_BITRATE_MULTIPLIERS.get(codec, {}).get(bitrate_range, 1.0)
        base_multiplier *= codec_adjustment

    return base_multiplier


def calculate_formula_based_bitrate_target(
    scene_type: str,
    width: int,
    height: int,
    fps: float
) -> float:
    """
    Calculate scene-specific bitrate target using production-validated formula.

    Formula: B_target = B_base × (W×H / 1920×1080) × (FPS / 30)

    Production evidence:
    - Gaming: 2.4 Mbps → VMAF 90.65 ✅ | 0.9 Mbps → VMAF 58.46 ❌
    - Animation: 5.4 Mbps → VMAF 97.79 ✅ | 3.4 Mbps → VMAF 28.95 ❌
    - Screen: 4.5-7.4 Mbps → VMAF 97-99 ✅

    Args:
        scene_type: Scene type (screen, gaming, animation, low-action, medium-action, high-action)
        width: Video width in pixels
        height: Video height in pixels
        fps: Video frame rate

    Returns:
        Target bitrate in Mbps
    """
    # Get base bitrate for scene type (1080p @ 30fps)
    base_bitrate = BASE_BITRATE_TARGETS_1080P_30FPS.get(scene_type, BASE_BITRATE_TARGETS_1080P_30FPS['default'])

    # Scale by resolution
    pixel_ratio = (width * height) / (1920 * 1080)

    # Scale by FPS
    fps_ratio = fps / 30.0

    # Calculate target
    target_bitrate = base_bitrate * pixel_ratio * fps_ratio

    return target_bitrate


def get_minimum_bitrate(
    quality_level: str,
    scene_type: str
) -> float:
    """
    Get minimum required bitrate for a given quality level and scene type.

    DEPRECATED: Use calculate_formula_based_bitrate_target() instead.
    Kept for backward compatibility.

    Args:
        quality_level: Quality level (High, Medium, Low)
        scene_type: Scene type (animation, low-action, medium-action, high-action)

    Returns:
        Minimum bitrate in Mbps
    """
    scene_config = MINIMUM_BITRATE_FOR_QUALITY.get(scene_type, MINIMUM_BITRATE_FOR_QUALITY['default'])
    return scene_config.get(quality_level, scene_config.get('Medium', 10))


def get_target_bitrate(
    input_bitrate_mbps: float,
    codec: str,
    quality_level: str,
    scene_type: str,
    max_bitrate_mbps: float = None
) -> float:
    """
    Calculate optimal target bitrate for VBR mode.

    Args:
        input_bitrate_mbps: Input video bitrate in Mbps
        codec: Codec name (av1_nvenc, hevc_nvenc, h264_nvenc)
        quality_level: Quality level (High, Medium, Low)
        scene_type: Scene type (animation, low-action, medium-action, high-action)
        max_bitrate_mbps: Maximum allowed bitrate (optional)

    Returns:
        Target bitrate in Mbps
    """
    # Get codec efficiency
    efficiency = CODEC_EFFICIENCY.get(codec, 0.60)

    # Get quality multiplier
    multiplier = get_quality_multiplier(quality_level, scene_type, codec, input_bitrate_mbps)

    # Calculate target
    target = input_bitrate_mbps * efficiency * multiplier

    # Apply max limit if provided
    if max_bitrate_mbps:
        target = min(target, max_bitrate_mbps)

    # Ensure minimum
    target = max(0.5, target)

    return target


def get_encoding_config(
    codec: str,
    quality_level: str,
    scene_type: str,
    input_bitrate_mbps: float,
    max_bitrate_mbps: float = None
) -> dict:
    """
    Get complete encoding configuration for given parameters.

    Args:
        codec: Codec name (av1_nvenc, hevc_nvenc, h264_nvenc)
        quality_level: Quality level (High, Medium, Low)
        scene_type: Scene type (animation, low-action, medium-action, high-action)
        input_bitrate_mbps: Input video bitrate in Mbps
        max_bitrate_mbps: Maximum allowed bitrate (optional)

    Returns:
        Dictionary with complete encoding configuration
    """
    cq = get_cq_value(codec, quality_level, scene_type, input_bitrate_mbps)
    target_bitrate = get_target_bitrate(
        input_bitrate_mbps, codec, quality_level, scene_type, max_bitrate_mbps
    )
    quality_multiplier = get_quality_multiplier(
        quality_level, scene_type, codec, input_bitrate_mbps
    )

    return {
        'codec': codec,
        'quality_level': quality_level,
        'scene_type': scene_type,
        'input_bitrate_mbps': input_bitrate_mbps,
        'cq_value': cq,
        'target_bitrate_mbps': round(target_bitrate, 2),
        'quality_multiplier': round(quality_multiplier, 2),
        'codec_efficiency': CODEC_EFFICIENCY.get(codec, 0.60),
        'bitrate_range': get_bitrate_range(input_bitrate_mbps)
    }


def print_encoding_config(config: dict) -> None:
    """Pretty print encoding configuration."""
    print("\n" + "="*70)
    print("🎬 ENCODING CONFIGURATION")
    print("="*70)
    print(f"  Codec:              {config['codec']}")
    print(f"  Quality Level:      {config['quality_level']}")
    print(f"  Scene Type:         {config['scene_type']}")
    print(f"  Input Bitrate:      {config['input_bitrate_mbps']:.2f} Mbps")
    print(f"  Bitrate Range:      {config['bitrate_range']}")
    print("-"*70)
    print(f"  CQ Value:           {config['cq_value']}")
    print(f"  Target Bitrate:     {config['target_bitrate_mbps']:.2f} Mbps")
    print(f"  Quality Multiplier: {config['quality_multiplier']:.2f}x")
    print(f"  Codec Efficiency:   {config['codec_efficiency']*100:.0f}%")
    print("="*70 + "\n")


# ============================================================================
# EXPECTED RESULTS TABLE
# ============================================================================
# Expected VMAF scores and compression ratios for each configuration

EXPECTED_RESULTS = {
    'av1_nvenc': {
        'High': {  # VMAF 93 target
            'animation': {'vmaf': (92, 95), 'compression': (8, 12)},
            'low-action': {'vmaf': (91, 94), 'compression': (6, 10)},
            'medium-action': {'vmaf': (92, 95), 'compression': (5, 8)},
            'high-action': {'vmaf': (91, 94), 'compression': (4, 7)},
        },
        'Medium': {  # VMAF 89 target
            'animation': {'vmaf': (88, 91), 'compression': (10, 15)},
            'low-action': {'vmaf': (87, 90), 'compression': (8, 12)},
            'medium-action': {'vmaf': (88, 91), 'compression': (6, 10)},
            'high-action': {'vmaf': (87, 90), 'compression': (5, 8)},
        },
        'Low': {  # VMAF 85 target
            'animation': {'vmaf': (84, 87), 'compression': (12, 18)},
            'low-action': {'vmaf': (83, 86), 'compression': (10, 14)},
            'medium-action': {'vmaf': (84, 87), 'compression': (8, 12)},
            'high-action': {'vmaf': (83, 86), 'compression': (6, 10)},
        }
    },
    'hevc_nvenc': {
        'High': {  # VMAF 93 target
            'animation': {'vmaf': (92, 95), 'compression': (6, 10)},
            'low-action': {'vmaf': (91, 94), 'compression': (5, 8)},
            'medium-action': {'vmaf': (92, 95), 'compression': (4, 7)},
            'high-action': {'vmaf': (91, 94), 'compression': (3, 6)},
        },
        'Medium': {  # VMAF 89 target
            'animation': {'vmaf': (88, 91), 'compression': (8, 12)},
            'low-action': {'vmaf': (87, 90), 'compression': (6, 10)},
            'medium-action': {'vmaf': (88, 91), 'compression': (5, 8)},
            'high-action': {'vmaf': (87, 90), 'compression': (4, 7)},
        },
        'Low': {  # VMAF 85 target
            'animation': {'vmaf': (84, 87), 'compression': (10, 14)},
            'low-action': {'vmaf': (83, 86), 'compression': (8, 12)},
            'medium-action': {'vmaf': (84, 87), 'compression': (6, 10)},
            'high-action': {'vmaf': (83, 86), 'compression': (5, 8)},
        }
    },
    'h264_nvenc': {
        'High': {  # VMAF 93 target
            'animation': {'vmaf': (92, 95), 'compression': (4, 7)},
            'low-action': {'vmaf': (91, 94), 'compression': (3, 6)},
            'medium-action': {'vmaf': (92, 95), 'compression': (3, 5)},
            'high-action': {'vmaf': (91, 94), 'compression': (2, 4)},
        },
        'Medium': {  # VMAF 89 target
            'animation': {'vmaf': (88, 91), 'compression': (5, 8)},
            'low-action': {'vmaf': (87, 90), 'compression': (4, 7)},
            'medium-action': {'vmaf': (88, 91), 'compression': (3, 6)},
            'high-action': {'vmaf': (87, 90), 'compression': (3, 5)},
        },
        'Low': {  # VMAF 85 target
            'animation': {'vmaf': (84, 87), 'compression': (6, 10)},
            'low-action': {'vmaf': (83, 86), 'compression': (5, 8)},
            'medium-action': {'vmaf': (84, 87), 'compression': (4, 7)},
            'high-action': {'vmaf': (83, 86), 'compression': (3, 6)},
        }
    }
}


def get_expected_results(codec: str, quality_level: str, scene_type: str) -> dict:
    """Get expected VMAF and compression for given configuration."""
    codec_results = EXPECTED_RESULTS.get(codec, EXPECTED_RESULTS['av1_nvenc'])
    quality_results = codec_results.get(quality_level, codec_results['Medium'])
    return quality_results.get(scene_type, quality_results.get('low-action', {}))


# ============================================================================
# NETFLIX PER-TITLE ENCODING CONFIGURATION
# ============================================================================
# Configuration for Netflix per-title encoding
# This is an alternative to the lookup table method above

NETFLIX_PER_TITLE_CONFIG = {
    # Enable Netflix per-title encoding
    # Note: Also requires ENABLE_NETFLIX_PER_TITLE = True in netflix_per_title_encoder.py
    'use_netflix_per_title': False,  # Set to True to enable

    # Fast mode: Use 3 probe points instead of 4 (faster but slightly less accurate)
    'netflix_fast_mode': False,  # Set to True for 60s timeout scenarios

    # VMAF calculation settings for per-title encoding
    'vmaf_calculation': {
        'use_vmafneg': False,  # Set to True to use VMAFNEG model
        'calculate_scene_vmaf': True,
        'vmaf_use_sampling': True,
        'vmaf_num_clips': 3,  # Reduce to 1 for faster VMAF
        'vmaf_clip_duration': 2,  # Reduce to 1 for faster VMAF
    },

    # Model paths (optional, will use defaults if not specified)
    'model_paths': {
        'default_vmaf_model': None,  # Will use system default
        'vmafneg_model': None,  # Will use system default
    },
}




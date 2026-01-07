"""
Optimal Bitrate Controller Configuration
=========================================

Feature flags and settings for the scene-aware optimal bitrate controller.
"""

# Feature flag to enable/disable optimal controller
ENABLE_OPTIMAL_CONTROLLER = True  # Set to True to enable

# Adaptive encoding settings
ENABLE_ADAPTIVE_ENCODING = False  # Multi-pass adaptive encoding
MAX_ADAPTIVE_PASSES = 3  # Maximum number of adaptive passes

# Scene type detection
AUTO_DETECT_SCENE_TYPE = True  # Auto-detect scene type from classifier
SCENE_TYPE_MAPPING = {
    # Map classifier scene types to optimal controller scene types
    'screen': 'screen',
    'text': 'screen',
    'desktop': 'screen',
    'gaming': 'gaming',
    'game': 'gaming',
    'animation': 'animation',
    'cartoon': 'animation',
    'anime': 'animation',
    'faces': 'faces',
    'people': 'faces',
    'portrait': 'faces',
    'interview': 'faces',
    'default': 'other',
    'other': 'other',
    'nature': 'other',
    'sports': 'other',
    'action': 'other'
}

# Fallback settings
FALLBACK_TO_LOOKUP_TABLE = True  # Fallback to lookup table if optimal controller fails
FALLBACK_ON_VMAF_FAILURE = True  # Fallback if VMAF threshold is missed

# Logging
OPTIMAL_CONTROLLER_LOGGING = True  # Enable detailed logging

# Performance settings
OPTIMAL_CONTROLLER_TIMEOUT = 300  # Timeout in seconds (5 minutes)

# Integration mode
INTEGRATION_MODE = 'hybrid'  # 'optimal_only', 'lookup_only', 'hybrid'
# - optimal_only: Use only optimal controller
# - lookup_only: Use only lookup table (legacy)
# - hybrid: Try optimal controller, fallback to lookup table

# Scene-specific overrides (optional)
SCENE_OVERRIDES = {
    # Override scene type for specific conditions
    # Example: Force 'screen' for very low motion content
    'force_screen_on_low_motion': False,
    'low_motion_threshold': 0.02,
    
    # Example: Force 'gaming' for very high motion content
    'force_gaming_on_high_motion': False,
    'high_motion_threshold': 0.10
}

# VMAF threshold mapping
VMAF_THRESHOLD_MAP = {
    'High': 93,
    'Medium': 89,
    'Low': 85
}

# Codec mode preferences by scene type
CODEC_MODE_PREFERENCES = {
    'screen': 'CRF',      # CRF preferred for screen
    'gaming': 'VBR',      # VBR preferred for gaming (better spike handling)
    'animation': 'CRF',   # CRF preferred for animation
    'faces': 'CRF',       # CRF preferred for faces
    'other': 'CRF'        # CRF default
}

# High VMAF threshold settings
HIGH_VMAF_THRESHOLD = 93  # Threshold considered "high" requiring conservative encoding
FORCE_CRF_FOR_HIGH_VMAF = False  # Set True to force CRF mode for VMAF >= HIGH_VMAF_THRESHOLD

# Minimum confidence threshold for scene classification
# Lowered from 0.5 to 0.10 to preserve scene classifications with low but valid confidence
# (e.g., animation with 0.119 confidence should not default to 'other')
MIN_SCENE_CONFIDENCE = 0.10  # Use 'other' if confidence < threshold


def get_optimal_controller_config():
    """Get optimal controller configuration."""
    return {
        'enabled': ENABLE_OPTIMAL_CONTROLLER,
        'adaptive_encoding': ENABLE_ADAPTIVE_ENCODING,
        'max_adaptive_passes': MAX_ADAPTIVE_PASSES,
        'auto_detect_scene': AUTO_DETECT_SCENE_TYPE,
        'scene_mapping': SCENE_TYPE_MAPPING,
        'fallback_to_lookup': FALLBACK_TO_LOOKUP_TABLE,
        'fallback_on_vmaf_failure': FALLBACK_ON_VMAF_FAILURE,
        'logging': OPTIMAL_CONTROLLER_LOGGING,
        'timeout': OPTIMAL_CONTROLLER_TIMEOUT,
        'integration_mode': INTEGRATION_MODE,
        'scene_overrides': SCENE_OVERRIDES,
        'vmaf_threshold_map': VMAF_THRESHOLD_MAP,
        'codec_mode_preferences': CODEC_MODE_PREFERENCES,
        'min_scene_confidence': MIN_SCENE_CONFIDENCE
    }


def should_use_optimal_controller(config=None):
    """
    Determine if optimal controller should be used.
    
    Args:
        config: Optional config dict with video_processing settings
    
    Returns:
        bool: True if optimal controller should be used
    """
    # Check global feature flag
    if not ENABLE_OPTIMAL_CONTROLLER:
        return False
    
    # Check integration mode
    if INTEGRATION_MODE == 'lookup_only':
        return False
    
    # Check config override if provided
    if config:
        video_config = config.get('video_processing', {})
        use_optimal = video_config.get('use_optimal_controller', ENABLE_OPTIMAL_CONTROLLER)
        if not use_optimal:
            return False
    
    return True


def map_scene_type_for_optimal_controller(scene_type, confidence=1.0):
    """
    Map classifier scene type to optimal controller scene type.

    The AI scene classifier returns descriptive names like:
    - 'Screen Content / Text' → 'screen'
    - 'Animation / Cartoon / Rendered Graphics' → 'animation'
    - 'Faces / People' → 'faces'
    - 'Gaming Content' → 'gaming'
    - 'other' → 'other'

    Args:
        scene_type: Scene type from classifier (can be descriptive string)
        confidence: Confidence score (0-1)

    Returns:
        str: Mapped scene type for optimal controller (screen|gaming|animation|faces|other)
    """
    # Use 'other' if confidence is too low
    if confidence < MIN_SCENE_CONFIDENCE:
        return 'other'

    # Normalize scene type
    scene_lower = str(scene_type).lower() if scene_type else 'other'

    # First try exact match
    if scene_lower in SCENE_TYPE_MAPPING:
        return SCENE_TYPE_MAPPING[scene_lower]

    # Then try keyword-based matching for descriptive classifier outputs
    # Check for canonical scene type keywords in order of specificity
    if 'animation' in scene_lower or 'cartoon' in scene_lower or 'anime' in scene_lower:
        return 'animation'
    elif 'gaming' in scene_lower or 'game' in scene_lower:
        return 'gaming'
    elif 'screen' in scene_lower or 'text' in scene_lower or 'desktop' in scene_lower:
        return 'screen'
    elif 'face' in scene_lower or 'people' in scene_lower or 'portrait' in scene_lower:
        return 'faces'

    # Default fallback
    return 'other'


def get_preferred_codec_mode(scene_type):
    """
    Get preferred codec mode for scene type.
    
    Args:
        scene_type: Scene type
    
    Returns:
        str: Preferred codec mode ('CRF' or 'VBR')
    """
    return CODEC_MODE_PREFERENCES.get(scene_type, 'CRF')


def get_vmaf_threshold_from_quality(quality_level):
    """
    Get VMAF threshold from quality level.
    
    Args:
        quality_level: Quality level ('High', 'Medium', 'Low')
    
    Returns:
        float: VMAF threshold
    """
    return VMAF_THRESHOLD_MAP.get(quality_level, 89)


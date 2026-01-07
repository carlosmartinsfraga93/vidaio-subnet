"""
Netflix Per-Title Encoding Configuration Example

This file shows how to configure and enable Netflix per-title encoding.

To enable Netflix per-title encoding:
1. Set ENABLE_NETFLIX_PER_TITLE = True in netflix_per_title_encoder.py
2. Add 'use_netflix_per_title': True to your config
3. Optionally configure the settings below
"""

# ============================================================================
# EXAMPLE CONFIGURATION
# ============================================================================

NETFLIX_PER_TITLE_CONFIG = {
    'video_processing': {
        # Enable Netflix per-title encoding
        'use_netflix_per_title': True,
        
        # Fast mode: Use 3 probe points instead of 4 (faster but less accurate)
        'netflix_fast_mode': False,
        
        # Standard encoding settings (still used)
        'codec': 'av1_nvenc',
        'codec_mode': 'CRF',
        'target_vmaf': 93.0,
        'target_quality': 'High',
        'target_bitrate': 10.0,
    },
    
    'vmaf_calculation': {
        # VMAF settings for per-title encoding
        'use_vmafneg': False,  # Set to True to use VMAFNEG model
        'calculate_scene_vmaf': True,
        'vmaf_use_sampling': True,
        'vmaf_num_clips': 3,
        'vmaf_clip_duration': 2,
    },
    
    'model_paths': {
        'default_vmaf_model': '/usr/local/share/vmaf/model/vmaf_v0.6.1.json',
        'vmafneg_model': '/usr/local/share/vmaf/model/vmaf_v0.6.1neg.json',
    },
    
    'directories': {
        'temp_dir': './videos/temp_scenes',
        'encoded_scenes_dir': './videos/encoded_scenes',
    }
}


# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

# In netflix_per_title_encoder.py, you can adjust these settings:

# 1. Enable parallel encoding (encode multiple CQ values simultaneously)
#    ENABLE_PARALLEL_ENCODING = True  # Default: True
#    - Speeds up encoding by 2-3x
#    - Requires more CPU/GPU resources

# 2. Enable parallel VMAF calculation
#    ENABLE_PARALLEL_VMAF = True  # Default: True
#    - Speeds up VMAF calculation by 2-3x
#    - Requires more CPU resources

# 3. Adjust CQ probe points
#    CQ_PROBE_POINTS = {
#        'av1_nvenc': [12, 18, 24, 30],  # 4 points (default)
#        # or
#        'av1_nvenc': [15, 22, 30],      # 3 points (faster)
#    }

# 4. Adjust VMAF calculation settings
#    VMAF_SETTINGS_PER_TITLE = {
#        'use_sampling': True,
#        'num_clips': 3,        # Reduce to 1 for faster VMAF
#        'clip_duration': 2,    # Reduce to 1 for faster VMAF
#        'use_parallel': False,
#    }


# ============================================================================
# EXPECTED PERFORMANCE
# ============================================================================

"""
For a 5-second scene:

Lookup Table Method (current):
- Scene classification: ~1s
- Encoding (1x): ~5-10s
- Total: ~6-11s

Netflix Per-Title (4 probes, sequential):
- Scene classification: ~1s
- Encoding (4x sequential): ~20-40s
- VMAF (4x sequential): ~12-20s
- Total: ~33-61s (5-6x slower)

Netflix Per-Title (4 probes, parallel encoding + parallel VMAF):
- Scene classification: ~1s
- Encoding (4x parallel): ~5-10s
- VMAF (4x parallel): ~3-5s
- Total: ~9-16s (1.5-2x slower than lookup table)

Netflix Per-Title (3 probes, parallel, fast VMAF):
- Scene classification: ~1s
- Encoding (3x parallel): ~5-10s
- VMAF (3x parallel, 1 clip): ~1-2s
- Total: ~7-13s (similar to lookup table!)

Recommendation:
- For production: Use parallel encoding + parallel VMAF with 3-4 probes
- For development/testing: Use fast mode with 3 probes
- For maximum speed: Use lookup table method
"""


# ============================================================================
# INTEGRATION EXAMPLE
# ============================================================================

def example_usage():
    """
    Example of how to use Netflix per-title encoding in your code.
    """
    
    # Method 1: Enable globally in netflix_per_title_encoder.py
    # Set ENABLE_NETFLIX_PER_TITLE = True
    
    # Method 2: Enable via config
    config = {
        'video_processing': {
            'use_netflix_per_title': True,
            'netflix_fast_mode': False,
            'codec': 'av1_nvenc',
            'target_vmaf': 93.0,
        }
    }
    
    # The encoder will automatically use Netflix per-title if enabled
    from encoder import ai_encoding
    
    scene_metadata = {
        'path': '/path/to/scene.mp4',
        'scene_number': 1,
        'duration': 5.0,
    }
    
    resources = {
        'scene_classifier_model': None,  # Your model
        'available_metrics': [],
        'device': 'cuda',
        'feature_scaler_step': None,
        'class_mapping': None,
    }
    
    success, result = ai_encoding(
        scene_metadata=scene_metadata,
        config=config,
        resources=resources,
        target_vmaf=93.0,
        target_quality_level='High',
        logging_enabled=True
    )
    
    if success:
        print(f"Encoding successful!")
        print(f"Optimal CQ: {result['cq_used']}")
        print(f"VMAF: {result.get('actual_vmaf', 'N/A')}")
        print(f"Compression: {result['compression_ratio']:.2f}x")
        print(f"Method: {result.get('encoding_method', 'unknown')}")


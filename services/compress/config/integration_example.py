"""
Integration example for advanced encoding configuration.

This shows how to integrate the advanced config system into server.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.compress.config.advanced_encoding_config import (
    get_encoding_config,
    get_quality_multiplier,
    get_cq_value,
    get_target_bitrate,
    print_encoding_config,
    get_expected_results
)


def integrate_with_server_vbr_mode(
    ffmpeg_codec: str,
    target_quality: str,
    scene_type: str,
    input_bitrate_mbps: float,
    max_bitrate_mbps: float
):
    """
    Example integration for VBR mode in server.py
    
    Replace the existing VBR bitrate calculation section with this.
    """
    
    # Map scene type to config format
    scene_mapping = {
        'Faces / People': 'low-action',
        'Animation / Cartoon / Rendered Graphics': 'animation',
        'Screen Content / Text': 'medium-action',
        'Gaming Content': 'high-action',
        'other': 'default',
        'unclear': 'default'
    }
    scene_type_mapped = scene_mapping.get(scene_type, 'default')
    
    # Get complete encoding configuration
    config = get_encoding_config(
        codec=ffmpeg_codec,
        quality_level=target_quality,
        scene_type=scene_type_mapped,
        input_bitrate_mbps=input_bitrate_mbps,
        max_bitrate_mbps=max_bitrate_mbps
    )
    
    # Print configuration for logging
    print_encoding_config(config)
    
    # Get expected results
    expected = get_expected_results(ffmpeg_codec, target_quality, scene_type_mapped)
    if expected:
        vmaf_range = expected.get('vmaf', (0, 0))
        comp_range = expected.get('compression', (0, 0))
        print(f"📊 Expected Results:")
        print(f"   VMAF: {vmaf_range[0]}-{vmaf_range[1]}")
        print(f"   Compression: {comp_range[0]}-{comp_range[1]}x")
    
    return config


def integrate_with_encoder_cq_lookup(
    codec: str,
    target_quality: str,
    scene_type: str,
    input_bitrate_mbps: float = None
):
    """
    Example integration for CQ lookup in encoder.py
    
    Replace get_cq_from_lookup_table() with this.
    """
    
    # Map scene type to config format
    scene_mapping = {
        'Faces / People': 'low-action',
        'Animation / Cartoon / Rendered Graphics': 'animation',
        'Screen Content / Text': 'medium-action',
        'Gaming Content': 'high-action',
        'other': 'default',
        'unclear': 'default'
    }
    scene_type_mapped = scene_mapping.get(scene_type, 'default')
    
    # Get CQ value
    cq = get_cq_value(
        codec=codec,
        quality_level=target_quality,
        scene_type=scene_type_mapped,
        input_bitrate_mbps=input_bitrate_mbps
    )
    
    print(f"🎚️ CQ Lookup: {codec} / {target_quality} / {scene_type_mapped}")
    if input_bitrate_mbps:
        print(f"   Input bitrate: {input_bitrate_mbps:.2f} Mbps")
    print(f"   → CQ: {cq}")
    
    return cq


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("ADVANCED ENCODING CONFIGURATION - EXAMPLES")
    print("="*80)
    
    # Example 1: HEVC Medium Quality, Faces (like the failed request)
    print("\n📌 Example 1: HEVC Medium Quality, Faces / People")
    print("-" * 80)
    config1 = integrate_with_server_vbr_mode(
        ffmpeg_codec='hevc_nvenc',
        target_quality='Medium',
        scene_type='Faces / People',
        input_bitrate_mbps=23.81,
        max_bitrate_mbps=30.0
    )
    
    # Example 2: AV1 High Quality, Animation
    print("\n📌 Example 2: AV1 High Quality, Animation")
    print("-" * 80)
    config2 = integrate_with_server_vbr_mode(
        ffmpeg_codec='av1_nvenc',
        target_quality='High',
        scene_type='Animation / Cartoon / Rendered Graphics',
        input_bitrate_mbps=50.0,
        max_bitrate_mbps=60.0
    )
    
    # Example 3: H.264 Low Quality, Gaming
    print("\n📌 Example 3: H.264 Low Quality, Gaming Content")
    print("-" * 80)
    config3 = integrate_with_server_vbr_mode(
        ffmpeg_codec='h264_nvenc',
        target_quality='Low',
        scene_type='Gaming Content',
        input_bitrate_mbps=15.0,
        max_bitrate_mbps=20.0
    )
    
    # Example 4: CQ lookup only
    print("\n📌 Example 4: CQ Lookup Only")
    print("-" * 80)
    cq = integrate_with_encoder_cq_lookup(
        codec='hevc_nvenc',
        target_quality='Medium',
        scene_type='Faces / People',
        input_bitrate_mbps=23.81
    )
    
    # Comparison table
    print("\n" + "="*80)
    print("CONFIGURATION COMPARISON")
    print("="*80)
    print(f"{'Codec':<15} {'Quality':<10} {'Scene':<20} {'CQ':<5} {'Target BR':<12} {'Multiplier':<12}")
    print("-" * 80)
    print(f"{config1['codec']:<15} {config1['quality_level']:<10} {config1['scene_type']:<20} "
          f"{config1['cq_value']:<5} {config1['target_bitrate_mbps']:<12.2f} {config1['quality_multiplier']:<12.2f}")
    print(f"{config2['codec']:<15} {config2['quality_level']:<10} {config2['scene_type']:<20} "
          f"{config2['cq_value']:<5} {config2['target_bitrate_mbps']:<12.2f} {config2['quality_multiplier']:<12.2f}")
    print(f"{config3['codec']:<15} {config3['quality_level']:<10} {config3['scene_type']:<20} "
          f"{config3['cq_value']:<5} {config3['target_bitrate_mbps']:<12.2f} {config3['quality_multiplier']:<12.2f}")
    print("="*80 + "\n")


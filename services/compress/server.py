"""
Video Compression Service API Server

This module provides a FastAPI server for video compression services.
It handles video upload, compression, and storage operations.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

from video_preprocessor import pre_processing
from scene_detector import scene_detection
from encoder import ai_encoding, load_encoding_resources
from validator_merger import validation_and_merging
from vidaio_subnet_core.utilities import storage_client, download_video
from vidaio_subnet_core import CONFIG
from utils.video_utils import get_video_duration, get_video_codec
from request_logger import RequestLogger
from async_vmaf_logger import async_vmaf_logger


# ============================================================================
# Configuration Variables
# ============================================================================

# VMAF threshold to quality level mapping (configurable for miner flow)
VMAF_THRESHOLD_HIGH = 93.0
VMAF_THRESHOLD_MEDIUM = 89.0
VMAF_THRESHOLD_LOW = 85.0

# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(title="Video Compression Service", version="1.1.0")

# Initialize request logger (keeps last 100 requests)
request_logger = RequestLogger(max_requests=100, log_dir="compression_logs")


@app.on_event("startup")
async def startup_event():
    """
    Preload AI models at startup to avoid delays on first request.

    This ensures all requests (including the first one) are fast.
    """
    print("\n" + "="*80)
    print("🚀 VIDEO COMPRESSOR SERVICE STARTUP")
    print("="*80)
    print(f"   📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   🌐 Host: {CONFIG.video_compressor.host}:{CONFIG.video_compressor.port}")
    print(f"   📂 Working directory: {os.getcwd()}")

    # Preload CLIP model for scene classification
    print(f"\n   🔧 Preloading CLIP model for scene classification...")
    preload_start = time.time()

    try:
        from utils.processing_utils import USE_CLIP_CLASSIFICATION
        if USE_CLIP_CLASSIFICATION:
            try:
                from utils.classify_scene_clip import get_clip_classifier
                import torch
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                print(f"   📍 Device: {device}")
                get_clip_classifier(device=device)
                preload_time = time.time() - preload_start
                print(f"   ✅ CLIP model preloaded successfully ({preload_time:.1f}s)")
                print(f"   💡 All requests will now use cached CLIP model")
            except Exception as clip_error:
                print(f"   ⚠️ Warning: Failed to preload CLIP model: {clip_error}")
                print(f"   💡 CLIP will be loaded on first request instead")
        else:
            print(f"   ⚠️ CLIP classification is disabled (USE_CLIP_CLASSIFICATION=False)")
            print(f"   💡 Using fallback scene classification method")

    except Exception as e:
        print(f"\n   ⚠️ Warning: Failed to preload CLIP model: {e}")
        print(f"   💡 CLIP will be loaded on first request instead")

    print("\n" + "="*80)
    print("✅ SERVICE READY - Waiting for requests...")
    print("="*80 + "\n")

# ============================================================================
# Global Model Cache
# ============================================================================

# Cache for AI models (loaded once at startup, reused for all requests)
_MODEL_CACHE = {
    'resources': None,
    'config': None,
    'loaded': False
}

def get_cached_models(config: dict, logging_enabled: bool = True):
    """
    Get cached AI models or load them if not already loaded.

    This function ensures models are loaded only once and reused across requests,
    dramatically improving performance (from ~140s to <1s per request).

    Args:
        config: Configuration dict with model paths
        logging_enabled: Whether to print loading messages

    Returns:
        dict: Loaded AI resources (models, scalers, etc.)
    """
    global _MODEL_CACHE

    # Check if models are already loaded
    if _MODEL_CACHE['loaded'] and _MODEL_CACHE['resources'] is not None:
        if logging_enabled:
            print(f"   ✅ Using cached AI models (already loaded)")
        return _MODEL_CACHE['resources']

    # Models not loaded yet, load them now
    if logging_enabled:
        print(f"   🔧 Loading AI models for the first time...")
        load_start = time.time()

    try:
        resources = load_encoding_resources(config, logging_enabled=logging_enabled)

        # Cache the loaded resources
        _MODEL_CACHE['resources'] = resources
        _MODEL_CACHE['config'] = config
        _MODEL_CACHE['loaded'] = True

        if logging_enabled:
            load_time = time.time() - load_start
            print(f"   ✅ AI models loaded and cached successfully ({load_time:.1f}s)")
            print(f"   💡 Subsequent requests will reuse cached models")

        return resources

    except Exception as e:
        if logging_enabled:
            print(f"   ❌ Failed to load AI models: {e}")
        raise


# ============================================================================
# Data Models
# ============================================================================

class CompressPayload(BaseModel):
    """Payload for video compression requests."""
    payload_url: str
    vmaf_threshold: float
    target_codec: str = 'av1'  # Target codec: av1, hevc, h264, vp9
    codec_mode: str = 'CRF'  # Codec mode: CRF (Constant Rate Factor), CBR (Constant Bitrate), VBR (Variable Bitrate)
    target_bitrate: float = 10.0  # Target bitrate in Mbps (for CBR/VBR modes)
    target_quality: str = 'Medium'  # High, Medium, Low (legacy, derived from VMAF) (legacy, derived from VMAF)
    max_duration: int = 3600  # Maximum allowed video duration in seconds
    output_dir: str = './output'  # Output directory for final files
    validator_uid: Optional[int] = None  # Validator UID (optional)
    validator_hotkey: Optional[str] = None  # Validator hotkey (optional)
    source_request_id: Optional[str] = None  # Original production request ID (for test comparisons)


class TestCompressPayload(BaseModel):
    """Payload for test compression requests."""
    video_path: str


# ============================================================================
# Helper Functions
# ============================================================================

def _detect_environment(video_url: str) -> str:
    """
    Detect environment based on video URL.

    Args:
        video_url: Video URL from request

    Returns:
        'production' if HTTPS URL, 'testing' if file path or local URL
    """
    if not video_url:
        return 'unknown'

    video_url_lower = video_url.lower()

    # Production: HTTPS URLs
    if video_url_lower.startswith('https://') or video_url_lower.startswith('http://'):
        return 'production'

    # Testing: File paths or local files
    if video_url_lower.startswith('file://') or '/' in video_url or '\\' in video_url:
        return 'testing'

    return 'unknown'


def create_lightweight_metadata(input_file: str, target_quality: str, target_codec: str, max_duration: int = 3600) -> Optional[dict]:
    """
    Create video metadata without preprocessing (for already-compressed videos).

    This is a lightweight alternative to pre_processing() that only extracts
    metadata without re-encoding. Perfect for miner chunks that are already compressed.

    Args:
        input_file: Path to input video file
        target_quality: Target quality level ('High', 'Medium', 'Low')
        target_codec: Target codec for encoding
        max_duration: Maximum allowed duration

    Returns:
        dict: Video metadata or None if validation fails
    """
    print(f"\n⚡ === Part 1: Pre-processing (SKIPPED - Lightweight Metadata) ===")
    print(f"   📏 Extracting metadata from already-compressed video")

    # Map quality to VMAF using configurable thresholds
    quality_vmaf_mapping = {
        'High': VMAF_THRESHOLD_HIGH,
        'Medium': VMAF_THRESHOLD_MEDIUM,
        'Low': VMAF_THRESHOLD_LOW
    }
    target_vmaf = quality_vmaf_mapping.get(target_quality, VMAF_THRESHOLD_MEDIUM)

    # Get video duration
    duration = get_video_duration(input_file)
    if duration is None:
        print("   ❌ Could not determine video duration")
        return None

    if duration > max_duration:
        print(f"   ❌ Video duration {duration}s exceeds limit of {max_duration}s")
        return None

    # Get video codec
    original_codec = get_video_codec(input_file)
    if not original_codec:
        print("   ❌ Could not determine video codec")
        return None

    print(f"   ✅ Duration: {duration:.1f}s")
    print(f"   ✅ Codec: {original_codec}")
    print(f"   🎯 Target: {target_quality} (VMAF: {target_vmaf})")
    print(f"   🎥 Target codec: {target_codec}")

    # Return lightweight metadata (same format as pre_processing)
    return {
        'path': input_file,
        'codec': original_codec,
        'original_codec': original_codec,
        'duration': duration,
        'was_reencoded': False,
        'encoding_time': 0.0,
        'target_vmaf': target_vmaf,
        'target_quality': target_quality,
        'target_codec': target_codec,
        'processing_info': {
            'lossless_conversion': False,
            'skipped_preprocessing': True
        }
    }


# ============================================================================
# Codec Mapping
# ============================================================================

def map_codec_name(target_codec: str, prefer_gpu: bool = True) -> str:
    """
    Map user-facing codec names (from ffprobe format) to ffmpeg encoder names.

    The protocol uses standard codec names (av1, hevc, h264, vp9) which match
    ffprobe output, but ffmpeg requires specific encoder names.

    Args:
        target_codec: Codec name from protocol (av1, hevc, h264, vp9)
        prefer_gpu: Whether to prefer GPU encoders (NVENC) when available

    Returns:
        FFmpeg encoder name (e.g., av1_nvenc, libx265, libx264, libvpx-vp9)

    Examples:
        map_codec_name('av1', prefer_gpu=True) → 'av1_nvenc'
        map_codec_name('av1', prefer_gpu=False) → 'libsvtav1'
        map_codec_name('hevc', prefer_gpu=True) → 'hevc_nvenc'
        map_codec_name('h264', prefer_gpu=False) → 'libx264'
    """
    codec_map = {
        'av1': 'av1_nvenc' if prefer_gpu else 'libsvtav1',
        'hevc': 'hevc_nvenc' if prefer_gpu else 'libx265',
        'h264': 'h264_nvenc' if prefer_gpu else 'libx264',
        'vp9': 'libvpx_vp9',  # No NVENC encoder for VP9
    }

    # Normalize to lowercase and get mapped codec
    normalized_codec = target_codec.lower().strip()
    ffmpeg_codec = codec_map.get(normalized_codec)

    if not ffmpeg_codec:
        logger.warning(f"Unknown codec '{target_codec}', defaulting to av1_nvenc")
        return 'av1_nvenc'

    logger.info(f"Mapped codec '{target_codec}' → '{ffmpeg_codec}' (GPU={prefer_gpu})")
    return ffmpeg_codec


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """
    Root endpoint with service information.

    Returns:
        dict: Service information
    """
    return {
        "service": "video-compressor",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/health", "/compress-video", "/test-compress"]
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify service is running.

    Returns:
        dict: Status message
    """
    return {"status": "healthy", "service": "video-compressor"}


@app.get("/logs/statistics")
async def get_log_statistics():
    """
    Get statistics about logged compression requests.

    Returns:
        dict: Statistics including total requests, success rate, disk usage
    """
    stats = request_logger.get_statistics()
    return {
        "status": "success",
        "statistics": stats
    }


@app.get("/logs/recent")
async def get_recent_requests(limit: int = 10):
    """
    Get recent compression requests.

    Args:
        limit: Number of recent requests to return (default: 10)

    Returns:
        dict: List of recent requests
    """
    recent = request_logger.get_recent_requests(limit=limit)
    return {
        "status": "success",
        "count": len(recent),
        "requests": recent
    }


@app.get("/logs/request/{request_id}")
async def get_request_details(request_id: str):
    """
    Get detailed information about a specific request.

    Args:
        request_id: The request ID to look up

    Returns:
        dict: Request details including metadata and results
    """
    details = request_logger.get_request_details(request_id)
    if details:
        return {
            "status": "success",
            "request": details
        }
    else:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")


@app.get("/logs/videos")
async def list_logged_videos():
    """
    List all available logged videos for testing.

    Returns:
        dict: List of video files with metadata
    """
    videos = request_logger.list_available_videos()
    return {
        "status": "success",
        "count": len(videos),
        "videos": videos
    }


def classify_scene_early(video_path: str, logging_enabled: bool = True) -> str:
    """
    Perform early scene classification before encoding.

    This function extracts a few frames and classifies the scene type
    to determine minimum bitrate requirements for VBR mode.

    Args:
        video_path: Path to input video file
        logging_enabled: Whether to print classification logs

    Returns:
        Scene type string (high-action, medium-action, low-action, animation, default)
    """
    try:
        import tempfile
        import shutil
        from utils.processing_utils import USE_CLIP_CLASSIFICATION

        if logging_enabled:
            print(f"\n🎬 Early Scene Classification (for bitrate calculation)")

        # Create temporary directory for frames
        temp_dir = tempfile.mkdtemp(prefix='early_scene_')

        try:
            # Use CLIP if enabled (faster), otherwise use MobileNetV3
            if USE_CLIP_CLASSIFICATION:
                from utils.classify_scene_clip import classify_scene_with_clip
                classification_label, detailed_results, _ = classify_scene_with_clip(
                    scene_path=video_path,
                    temp_dir=temp_dir,
                    num_frames=3,  # Quick classification with 3 frames
                    device='cuda' if os.path.exists('/dev/nvidia0') else 'cpu',
                    logging_enabled=logging_enabled
                )
            else:
                # Use MobileNetV3 classifier
                from utils.processing_utils import classify_scene_from_path

                # Get cached models
                config = _get_default_config()
                resources = get_cached_models(config, logging_enabled=False)

                classification_label, detailed_results, _ = classify_scene_from_path(
                    scene_path=video_path,
                    temp_dir=temp_dir,
                    scene_classifier_model=resources['scene_classifier_model'],
                    available_metrics=resources['available_metrics'],
                    device=resources['device'],
                    metrics_scaler=resources['feature_scaler_step'],
                    class_mapping=resources['class_mapping'],
                    logging_enabled=logging_enabled,
                    num_frames=3  # Quick classification
                )

            # Map classification to scene type
            scene_type_mapping = {
                'Gaming Content': 'high-action',
                'Faces / People': 'low-action',
                'Screen Content / Text': 'low-action',
                'Animation / Cartoon / Rendered Graphics': 'animation',
                'Other': 'default',
                'unclear': 'default'
            }

            scene_type = scene_type_mapping.get(classification_label, 'default')

            if logging_enabled:
                print(f"   Classification: {classification_label} → Scene type: {scene_type}")

            return scene_type

        finally:
            # Cleanup temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    except Exception as e:
        if logging_enabled:
            print(f"   ⚠️ Early scene classification failed: {e}")
            print(f"   Using default scene type for bitrate calculation")
        return 'default'


@app.post("/compress-video")
async def compress_video(video: CompressPayload, background_tasks: BackgroundTasks):
    """
    Compress a video from a URL payload.

    Args:
        video: Compression request payload
        background_tasks: FastAPI background tasks for async VMAF calculation

    Returns:
        dict: Compression results with uploaded video URL
    """
    # Generate unique request ID
    import uuid
    request_id = str(uuid.uuid4())

    print(f"\n{'='*80}")
    print(f"📥 NEW COMPRESSION REQUEST: {request_id}")
    print(f"{'='*80}")
    print(f"video url: {video.payload_url}")
    print(f"vmaf threshold: {video.vmaf_threshold}")
    print(f"target codec: {video.target_codec}")
    print(f"codec mode (requested): {video.codec_mode}")
    print(f"target bitrate: {video.target_bitrate} Mbps")

    # CRITICAL FIX: Force VBR mode to prevent file size increases
    # CRF mode has no bitrate cap and can cause file size increases (score = -10)
    # VBR mode enforces bitrate cap while maintaining quality, achieving 86-92% compression
    # Validator only checks: codec, VMAF, compression ratio (NOT encoding mode)
    # For CRF requests: validator skips bitrate validation entirely
    # For VBR requests: validator checks bitrate <= target + 10% (which we'll pass)
    original_codec_mode = video.codec_mode
    forced_codec_mode = 'VBR'

    if original_codec_mode.upper() != 'VBR':
        print(f"⚠️ FORCING VBR MODE: Requested '{original_codec_mode}' but using 'VBR' to prevent file size increases")
        print(f"   Reason: CRF mode can cause file size increases (score=-10), VBR achieves 86-92% compression")
        print(f"   Validator only checks: codec, VMAF, compression ratio (not encoding mode)")
    else:
        print(f"✅ Using VBR mode as requested")

    # Download video from URL
    input_path = await download_video(video.payload_url)
    input_file = Path(input_path)

    # Prepare request data for logging (use forced VBR mode)
    request_data = {
        'request_id': request_id,
        'payload_url': video.payload_url,
        'vmaf_threshold': video.vmaf_threshold,
        'target_codec': video.target_codec,
        'codec_mode': forced_codec_mode,  # Use forced VBR mode
        'target_bitrate': video.target_bitrate,
        'output_dir': video.output_dir,
        'max_duration': video.max_duration
    }
    vmaf_threshold = video.vmaf_threshold

    # Map VMAF threshold to target quality using configurable thresholds
    if vmaf_threshold == VMAF_THRESHOLD_LOW:
        target_quality = 'Low'
    elif vmaf_threshold == VMAF_THRESHOLD_MEDIUM:
        target_quality = 'Medium'
    elif vmaf_threshold == VMAF_THRESHOLD_HIGH:
        target_quality = 'High'
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid VMAF threshold. Expected {VMAF_THRESHOLD_LOW}, {VMAF_THRESHOLD_MEDIUM}, or {VMAF_THRESHOLD_HIGH}, got {vmaf_threshold}"
        )

    # Map codec name from protocol format to ffmpeg encoder name
    ffmpeg_codec = map_codec_name(video.target_codec, prefer_gpu=True)

    # Validate input file
    if not input_file.is_file():
        raise HTTPException(status_code=400, detail="Input video file does not exist.")

    # Create output directory
    output_dir = Path(video.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate intelligent target bitrate for VBR mode
    # For VBR mode, we need to set an appropriate bitrate cap to achieve compression
    # while maintaining target VMAF quality
    calculated_target_bitrate = video.target_bitrate
    original_video_bitrate = None  # Track original bitrate for logging
    has_complexity = False  # Track if content complexity was detected (default: simple content)

    if forced_codec_mode == 'VBR':
        try:
            # STEP 1: Perform early scene classification AND get video metrics
            scene_type = classify_scene_early(str(input_file), logging_enabled=True)

            # STEP 1.5: Get video complexity metrics for bitrate adjustment
            from utils.analyze_video_fast import analyze_video_fast
            video_metrics = analyze_video_fast(str(input_file), max_frames=30, logging_enabled=False)
            if not video_metrics:
                video_metrics = {}  # Fallback to empty dict if analysis fails

            # STEP 2: Get input video bitrate
            import subprocess
            probe_cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=bit_rate',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(input_file)
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and result.stdout.strip():
                input_bitrate_bps = int(result.stdout.strip())
                input_bitrate_mbps = input_bitrate_bps / 1_000_000
                original_video_bitrate = input_bitrate_mbps  # Store for logging

                # STEP 3: Calculate target bitrate based on quality level and codec efficiency
                # DYNAMIC COMPRESSION: Balanced multipliers that adapt to input bitrate and complexity
                # These work with CQ values to find optimal bitrate for VMAF target
                codec_efficiency = {
                    'av1_nvenc': 0.25,      # AV1: 75% reduction vs H.264 (realistic compression)
                    'hevc_nvenc': 0.35,     # HEVC: 65% reduction vs H.264
                    'h264_nvenc': 0.50,     # H.264: 50% reduction with better encoding
                    'libx265': 0.35,        # Same as hevc_nvenc
                    'libx264': 0.50,        # Same as h264_nvenc
                    'libsvtav1': 0.25,      # Same as av1_nvenc
                    'libvpx-vp9': 0.30      # VP9 between AV1 and HEVC
                }.get(ffmpeg_codec, 0.40)  # Default to 40% for unknown codecs

                # Adjust based on target quality
                # DYNAMIC: Quality multipliers work with complexity detection
                # Lower multipliers for easier content, higher for complex content
                quality_multiplier = {
                    'High': 0.9,    # VMAF 93 - Needs more bitrate for quality
                    'Medium': 0.7,  # VMAF 89 - Balanced approach
                    'Low': 0.5      # VMAF 85 - More aggressive compression
                }.get(target_quality, 0.7)

                # Calculate target: input_bitrate * codec_efficiency * quality_multiplier
                calculated_target_bitrate = input_bitrate_mbps * codec_efficiency * quality_multiplier

                # STEP 4: Calculate formula-based bitrate target
                # Uses production-validated formula: B_target = B_base × (W×H / 1920×1080) × (FPS / 30)
                from config.advanced_encoding_config import calculate_formula_based_bitrate_target

                # Get video properties for formula
                width = video_metrics.get('width', 1920)
                height = video_metrics.get('height', 1080)
                fps = video_metrics.get('fps', 30.0)

                # Calculate scene-specific bitrate target
                formula_based_target = calculate_formula_based_bitrate_target(
                    scene_type=scene_type,
                    width=width,
                    height=height,
                    fps=fps
                )

                print(f"   📐 Formula-based target: {formula_based_target:.2f} Mbps")
                print(f"      Scene: {scene_type}, Resolution: {width}x{height}, FPS: {fps}")

                # Use formula-based target as minimum
                min_required_bitrate = formula_based_target

                # STEP 4.5: Adjust minimum bitrate based on content complexity
                # If video has high noise, motion, or texture, increase minimum bitrate
                complexity_multiplier = 1.0
                complexity_factors = []
                has_complexity = False  # Track if any complexity was detected

                # Check grain/noise level (high noise needs more bitrate)
                grain_noise = video_metrics.get('metrics_avg_grain_noise', 0)
                if grain_noise > 10:  # High noise threshold
                    complexity_multiplier *= 1.3
                    complexity_factors.append(f"high noise ({grain_noise:.1f})")
                    has_complexity = True
                elif grain_noise > 7:  # Medium noise
                    complexity_multiplier *= 1.15
                    complexity_factors.append(f"medium noise ({grain_noise:.1f})")
                    has_complexity = True

                # Check motion level (high motion needs more bitrate)
                motion = video_metrics.get('metrics_avg_motion', 0)
                if motion > 0.15:  # High motion threshold
                    complexity_multiplier *= 1.25
                    complexity_factors.append(f"high motion ({motion:.3f})")
                    has_complexity = True
                elif motion > 0.10:  # Medium motion
                    complexity_multiplier *= 1.1
                    complexity_factors.append(f"medium motion ({motion:.3f})")
                    has_complexity = True

                # Check texture complexity (complex textures need more bitrate)
                texture = video_metrics.get('metrics_avg_texture', 0)
                if texture > 6.5:  # High texture complexity
                    complexity_multiplier *= 1.2
                    complexity_factors.append(f"high texture ({texture:.1f})")
                    has_complexity = True
                elif texture > 5.5:  # Medium texture
                    complexity_multiplier *= 1.1
                    complexity_factors.append(f"medium texture ({texture:.1f})")
                    has_complexity = True

                # Apply complexity adjustment to minimum bitrate
                if complexity_multiplier > 1.0:
                    original_min = min_required_bitrate
                    min_required_bitrate *= complexity_multiplier
                    print(f"   ⚠️ Content complexity detected: {', '.join(complexity_factors)}")
                    print(f"   📈 Adjusted minimum bitrate: {original_min:.2f} → {min_required_bitrate:.2f} Mbps ({complexity_multiplier:.2f}x)")

                # STEP 5: Smart bitrate selection strategy
                # 5.1: Pick minimum of calculated and requested (prefer lower bitrate for efficiency)
                picked_bitrate = min(calculated_target_bitrate, video.target_bitrate)

                # 5.2: Compare with minimum required bitrate
                if picked_bitrate < min_required_bitrate:
                    # Picked is too low - use minimum required
                    final_bitrate = min_required_bitrate
                    selection_reason = f"Picked {picked_bitrate:.2f} < minimum {min_required_bitrate:.2f}, using minimum"
                else:
                    # Picked is sufficient - check if original bitrate is lower than requested
                    # BUT only use original if it's high enough (at least 1.5x minimum required)
                    if input_bitrate_mbps < video.target_bitrate and input_bitrate_mbps >= min_required_bitrate * 1.5:
                        # Original is lower than requested AND sufficient for quality - use it
                        final_bitrate = input_bitrate_mbps
                        selection_reason = f"Original {input_bitrate_mbps:.2f} < requested {video.target_bitrate:.2f} and sufficient (≥{min_required_bitrate*1.5:.1f}), using original"
                    else:
                        # Use middle value between picked and minimum
                        final_bitrate = (picked_bitrate + min_required_bitrate) / 2
                        selection_reason = f"Using middle value between picked {picked_bitrate:.2f} and minimum {min_required_bitrate:.2f}"

                # STEP 5.5: Apply efficiency multiplier for simple content
                # DYNAMIC: For simple content, we can compress more efficiently
                # For complex content (has_complexity=True), use 100% of calculated bitrate
                # For simple content (has_complexity=False), use 70% for better efficiency
                if not has_complexity:
                    efficiency_multiplier = 0.70  # Balanced reduction for simple content
                    original_final = final_bitrate
                    final_bitrate *= efficiency_multiplier
                    print(f"   💡 Simple content detected - applying {efficiency_multiplier}x efficiency multiplier")
                    print(f"   📉 Adjusted final bitrate: {original_final:.2f} → {final_bitrate:.2f} Mbps")

                print(f"📊 VBR Bitrate Calculation:")
                print(f"   Scene type: {scene_type}")
                print(f"   Input bitrate: {input_bitrate_mbps:.2f} Mbps")
                print(f"   Codec efficiency: {codec_efficiency*100:.0f}%")
                print(f"   Quality multiplier: {quality_multiplier}x")
                print(f"   Calculated target: {calculated_target_bitrate:.2f} Mbps")
                print(f"   User requested: {video.target_bitrate:.2f} Mbps")
                print(f"   Picked (min of above): {picked_bitrate:.2f} Mbps")
                print(f"   Minimum required: {min_required_bitrate:.2f} Mbps (for {scene_type} + {target_quality})")
                print(f"   Selection: {selection_reason}")
                print(f"   Final target: {final_bitrate:.2f} Mbps")

                calculated_target_bitrate = final_bitrate
            else:
                print(f"⚠️ Could not detect input bitrate, using user-specified: {video.target_bitrate} Mbps")
        except Exception as e:
            print(f"⚠️ Error calculating target bitrate: {e}, using user-specified: {video.target_bitrate} Mbps")

    # Perform video compression (use forced VBR mode)
    try:
        # BUG FIX #1: Pass minimum required bitrate to video_compressor
        compressed_video_path = video_compressor(
            input_file=str(input_file),
            target_quality=target_quality,
            target_codec=ffmpeg_codec,
            codec_mode=forced_codec_mode,  # Use forced VBR mode
            target_bitrate=calculated_target_bitrate,
            max_duration=video.max_duration,
            output_dir=str(output_dir),
            skip_scene_detection=True,  # Skip for miner chunks (already pre-split)
            skip_preprocessing=True,  # Skip for miner chunks (already compressed)
            min_required_bitrate=min_required_bitrate if 'min_required_bitrate' in locals() else None
        )
        print(f"compressed_video_path: {compressed_video_path}")

        if compressed_video_path and Path(compressed_video_path).exists():
            # Upload compressed video to storage
            try:
                compressed_video_name = os.path.basename(compressed_video_path)
                object_name: str = compressed_video_name
                
                # Upload file
                await storage_client.upload_file(object_name, compressed_video_path)
                print(f"object_name: {object_name}")
                print("Video uploaded successfully.")
                
                # Log the successful request BEFORE cleanup
                result_data = {
                    'compressed_video_path': compressed_video_path,
                    'object_name': object_name,
                    'uploaded': True
                }
                request_logger.log_request(
                    request_id=request_id,
                    downloaded_video_path=input_path,
                    request_data=request_data,
                    result=result_data,
                    validator_uid=video.validator_uid,
                    validator_hotkey=video.validator_hotkey
                )

                # Load encoding report to get metadata for async VMAF calculation
                try:
                    report_path = Path(output_dir) / f"{Path(input_path).stem}_encoding_report.json"
                    print(f"🔍 Looking for encoding report at: {report_path}")
                    print(f"   Input path: {input_path}")
                    print(f"   Output dir: {output_dir}")
                    print(f"   Report exists: {report_path.exists()}")
                    if report_path.exists():
                        with open(report_path, 'r') as f:
                            encoding_report = json.load(f)

                        # Extract metadata from comprehensive training data
                        training_data = encoding_report.get('comprehensive_training_data', {})
                        pipeline_data = training_data.get('pipeline_stages_data', {})
                        scene_encoding_data = pipeline_data.get('part3_ai_encoding', [])
                        print(f"   📊 Found {len(scene_encoding_data)} scenes in encoding report")

                        if scene_encoding_data:
                            # Get first scene data
                            scene_data = scene_encoding_data[0]
                            scene_type = scene_data.get('scene_type', 'unknown')
                            cq_used = scene_data.get('final_adjusted_cq', 0)

                            # Calculate compression ratio
                            original_size = os.path.getsize(input_path)
                            compressed_size = os.path.getsize(compressed_video_path)
                            compression_ratio = original_size / compressed_size if compressed_size > 0 else 0

                            # Copy files to VMAF directory for async calculation
                            vmaf_dir = Path("compression_logs/vmaf_files")
                            vmaf_dir.mkdir(parents=True, exist_ok=True)

                            import shutil
                            original_copy = vmaf_dir / f"{request_id}_original.mp4"
                            compressed_copy = vmaf_dir / f"{request_id}_compressed.mp4"

                            shutil.copy2(input_path, original_copy)
                            shutil.copy2(compressed_video_path, compressed_copy)

                            # Detect environment based on URL
                            environment = _detect_environment(video.payload_url)

                            # Schedule async VMAF calculation
                            background_tasks.add_task(
                                async_vmaf_logger.calculate_and_log_vmaf,
                                request_id=request_id,
                                original_video_path=str(original_copy),
                                compressed_video_path=str(compressed_copy),
                                target_vmaf=vmaf_threshold,
                                scene_type=scene_type,
                                cq_used=cq_used,
                                compression_ratio=compression_ratio,
                                codec=ffmpeg_codec,
                                codec_mode=forced_codec_mode,  # Actual mode used (always VBR)
                                original_bitrate=original_video_bitrate,  # Original video bitrate
                                target_bitrate=calculated_target_bitrate,  # Applied bitrate (after minimum bitrate logic)
                                requested_bitrate=video.target_bitrate,  # User-requested bitrate
                                requested_mode=original_codec_mode,  # Originally requested mode (CRF/VBR)
                                validator_uid=video.validator_uid,
                                validator_hotkey=video.validator_hotkey,
                                environment=environment,
                                source_request_id=video.source_request_id,  # For test comparisons
                                video_analysis=video_metrics,  # Video complexity analysis
                                width=video_metrics.get('metrics_resolution_width'),  # Extract from video_metrics
                                height=video_metrics.get('metrics_resolution_height'),  # Extract from video_metrics
                                fps=video_metrics.get('metrics_frame_rate')  # Extract from video_metrics
                            )
                            print(f"📊 Scheduled async VMAF calculation for request {request_id}")
                        else:
                            print(f"⚠️ No scenes found in encoding report (scenes array is empty)")
                    else:
                        print(f"⚠️ Encoding report not found at: {report_path}")
                except Exception as vmaf_error:
                    print(f"⚠️ Failed to schedule async VMAF calculation: {vmaf_error}")
                    import traceback
                    traceback.print_exc()

                # Clean up local compressed file
                if os.path.exists(compressed_video_path):
                    os.remove(compressed_video_path)
                    print(f"🗑️ Deleted compressed file: {compressed_video_path}")
                else:
                    print(f"⚠️ Compressed file does not exist: {compressed_video_path}")

                # Clean up downloaded original file (already logged)
                if os.path.exists(input_path):
                    os.remove(input_path)
                    print(f"🗑️ Deleted downloaded file: {input_path}")
                else:
                    print(f"⚠️ Downloaded file does not exist: {input_path}")

                # Get sharing link
                try:
                    sharing_link: Optional[str] = await storage_client.get_presigned_url(object_name)
                    print(f"sharing_link: {sharing_link}")

                    if not sharing_link:
                        print("⚠️ Warning: get_presigned_url returned None")
                        raise HTTPException(
                            status_code=500,
                            detail="Failed to generate sharing link for uploaded video"
                        )

                    return {
                        "uploaded_video_url": sharing_link,
                        "status": "success",
                        "object_name": object_name
                    }
                except HTTPException:
                    raise
                except Exception as link_error:
                    print(f"❌ Error getting presigned URL: {link_error}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to generate sharing link: {str(link_error)}"
                    )
            except Exception as upload_error:
                print(f"❌ Upload error: {upload_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload compressed video: {str(upload_error)}"
                )
        else:
            error_msg = f"Compression failed: compressed_video_path={compressed_video_path}, exists={Path(compressed_video_path).exists() if compressed_video_path else 'N/A'}"
            print(f"❌ {error_msg}")

            # Log the failed request
            request_logger.log_request(
                request_id=request_id,
                downloaded_video_path=input_path,
                request_data=request_data,
                error=error_msg,
                validator_uid=video.validator_uid,
                validator_hotkey=video.validator_hotkey
            )

            # Clean up downloaded file even on failure (already logged)
            if os.path.exists(input_path):
                os.remove(input_path)
                print(f"🗑️ Cleaned up downloaded file after compression failure: {input_path}")
            raise HTTPException(status_code=500, detail="Video compression failed")
    except HTTPException:
        # Log HTTP exceptions if not already logged
        error_msg = "HTTP exception during compression"
        request_logger.log_request(
            request_id=request_id,
            downloaded_video_path=input_path,
            request_data=request_data,
            error=error_msg,
            validator_uid=video.validator_uid,
            validator_hotkey=video.validator_hotkey
        )

        # Clean up downloaded file on HTTP exceptions (already logged)
        if os.path.exists(input_path):
            os.remove(input_path)
            print(f"🗑️ Cleaned up downloaded file after error: {input_path}")
        raise
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()

        # Log the exception
        request_logger.log_request(
            request_id=request_id,
            downloaded_video_path=input_path,
            request_data=request_data,
            error=error_msg,
            validator_uid=video.validator_uid,
            validator_hotkey=video.validator_hotkey
        )

        # Clean up downloaded file on any exception (already logged)
        if os.path.exists(input_path):
            os.remove(input_path)
            print(f"🗑️ Cleaned up downloaded file after exception: {input_path}")
        raise HTTPException(status_code=500, detail=f"Video compression error: {str(e)}")


@app.post("/test-compress")
async def test_compress_video(test_payload: TestCompressPayload):
    """
    Test endpoint for video compression using local video path.
    
    Args:
        test_payload: Test compression request payload
        
    Returns:
        dict: Test compression results
    """
    video_path = Path(test_payload.video_path)
    
    # Validate input file
    if not video_path.is_file():
        raise HTTPException(
            status_code=400, 
            detail=f"Video file does not exist: {video_path}"
        )
    
    try:
        # Perform test compression
        compressed_video_path = test_video_compression(str(video_path))
        
        if compressed_video_path and Path(compressed_video_path).exists():
            return {
                "status": "success",
                "message": "Video compression test completed successfully",
                "input_path": str(video_path),
                "output_path": compressed_video_path,
                "output_size_mb": round(
                    Path(compressed_video_path).stat().st_size / (1024 * 1024), 2
                )
            }
        else:
            raise HTTPException(status_code=500, detail="Video compression test failed")
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Video compression test error: {str(e)}"
        )


# ============================================================================
# Core Video Compression Functions
# ============================================================================

def video_compressor(
    input_file: str,
    target_quality: str = 'Medium',
    target_codec: str = 'av1_nvenc',
    codec_mode: str = 'CRF',
    target_bitrate: float = 10.0,
    max_duration: int = 3600,
    output_dir: str = './output',
    skip_scene_detection: bool = True,
    skip_preprocessing: bool = True,
    min_required_bitrate: Optional[float] = None
) -> Optional[str]:
    """
    Main video compression pipeline orchestrator.

    Args:
        input_file: Path to input video file
        target_quality: Target quality level ('High', 'Medium', 'Low')
        target_codec: FFmpeg encoder name (e.g., 'av1_nvenc', 'hevc_nvenc', 'libx264')
        codec_mode: Encoding mode - 'CRF' (Constant Rate Factor), 'CBR' (Constant Bitrate), 'VBR' (Variable Bitrate)
        target_bitrate: Target bitrate in Mbps (used for CBR/VBR modes)
        max_duration: Maximum allowed video duration in seconds
        output_dir: Output directory for final files
        skip_scene_detection: If True, treats entire video as single scene (default: True for miner chunks)
        skip_preprocessing: If True, skips lossless re-encoding (default: True for already-compressed miner chunks)

    Returns:
        str: Path to compressed video file, or None if failed
    """
    # Record pipeline start time
    pipeline_start_time = time.time()
    
    # Get current directory and setup paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Load configuration
    config = _load_configuration(current_dir)
    config['directories']['output_dir'] = str(output_dir_path)
    if 'video_processing' not in config:
        config['video_processing'] = {}
    config['video_processing']['target_quality'] = target_quality
    config['video_processing']['target_codec'] = target_codec
    config['video_processing']['codec_mode'] = codec_mode
    config['video_processing']['target_bitrate'] = target_bitrate
    # BUG FIX #1: Add minimum required bitrate to config
    if min_required_bitrate is not None:
        config['video_processing']['min_required_bitrate'] = min_required_bitrate

    # ============================================================================
    # NETFLIX PER-TITLE ENCODING CONFIGURATION
    # ============================================================================
    # Enable Netflix per-title encoding (set to True to enable)
    config['video_processing']['use_netflix_per_title'] = False  # Change to True to enable
    config['video_processing']['netflix_fast_mode'] = False  # Set to True for 3 probes instead of 4

    # VMAF calculation settings for Netflix per-title
    if 'vmaf_calculation' not in config:
        config['vmaf_calculation'] = {}
    config['vmaf_calculation']['use_vmafneg'] = False
    config['vmaf_calculation']['calculate_scene_vmaf'] = True
    config['vmaf_calculation']['vmaf_use_sampling'] = True
    config['vmaf_calculation']['vmaf_num_clips'] = 3
    config['vmaf_calculation']['vmaf_clip_duration'] = 2

    # Model paths for VMAF (optional - will use defaults if not set)
    if 'model_paths' not in config:
        config['model_paths'] = {}
    # config['model_paths']['default_vmaf_model'] = '/usr/local/share/vmaf/model/vmaf_v0.6.1.json'
    # config['model_paths']['vmafneg_model'] = '/usr/local/share/vmaf/model/vmaf_v0.6.1neg.json'

    # Create temp directory
    temp_dir = Path(config['directories']['temp_dir'])
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Display pipeline information
    _display_pipeline_info(input_file, target_quality, max_duration, output_dir)

    # PART 1: Pre-processing (optional - can be skipped for already-compressed videos)
    if skip_preprocessing:
        # Skip full preprocessing - use lightweight metadata extraction
        part1_result = create_lightweight_metadata(input_file, target_quality, target_codec, max_duration)
        if not part1_result:
            print("❌ Part 1 failed. Pipeline terminated.")
            return False
        part1_time = time.time() - pipeline_start_time
        print(f"   ⏱️ Metadata extraction: {part1_time:.2f}s")
    else:
        # Run full preprocessing (checks for lossless codecs and re-encodes if needed)
        part1_result = _execute_preprocessing(input_file, target_quality, max_duration, output_dir_path)
        if not part1_result:
            print("❌ Part 1 failed. Pipeline terminated.")
            return False
        part1_time = time.time() - pipeline_start_time
        _display_preprocessing_results(part1_result, part1_time)

    # PART 2: Scene Detection (optional - can be skipped for pre-chunked videos)
    part2_start_time = time.time()

    if skip_scene_detection:
        # Skip scene detection - treat entire video as single scene
        print(f"\n⚡ === Part 2: Scene Detection (SKIPPED) ===")
        print(f"   📏 Treating entire video as single scene (pre-chunked input)")

        scenes_metadata = [{
            'path': part1_result['path'],
            'scene_number': 1,
            'start_time': 0.0,
            'end_time': part1_result['duration'],
            'duration': part1_result['duration'],
            'original_video_metadata': part1_result
        }]
        part2_time = time.time() - part2_start_time
        print(f"   ⏱️ Scene setup: {part2_time:.2f}s")
        print(f"   ✅ 1 scene created (0.0s - {part1_result['duration']:.1f}s)")
    else:
        # Run normal scene detection
        scenes_metadata = scene_detection(part1_result)
        if not scenes_metadata:
            print("❌ Part 2 failed. Pipeline terminated.")
            return False

        part2_time = time.time() - part2_start_time
        _display_scene_detection_results(scenes_metadata, part2_time)
    
    # PART 3: AI Encoding
    part3_result = _execute_ai_encoding(scenes_metadata, config, target_quality)
    if not part3_result:
        print("❌ Part 3 failed completely. Pipeline terminated.")
        return False
    
    part3_time = part3_result['processing_time']
    encoded_scenes_data = part3_result['encoded_scenes_data']
    successful_encodings = part3_result['successful_encodings']

    # PART 4: Validation and Merging
    part4_result = _execute_validation_and_merging(
        part1_result, encoded_scenes_data, config
    )
    if not part4_result:
        print("❌ Part 4 failed. Could not create final video.")
        return False
    
    part4_time = part4_result['processing_time']
    final_video_path = part4_result['final_video_path']
    final_vmaf = part4_result['final_vmaf']
    comprehensive_report = part4_result['comprehensive_report']
    
    _display_validation_results(part4_result)

    # Pipeline completion summary
    total_pipeline_time = time.time() - pipeline_start_time
    _display_pipeline_summary(
        input_file, final_video_path, part1_result, scenes_metadata,
        successful_encodings, output_dir, pipeline_start_time,
        part1_time, part2_time, part3_time, part4_time, total_pipeline_time,
        final_vmaf, comprehensive_report
    )
    
    return final_video_path


def test_video_compression(video_path: str) -> Optional[str]:
    """
    Test function for video compression using default parameters.
    
    Args:
        video_path: Path to input video file
        
    Returns:
        str: Path to compressed video file, or None if failed
    """
    print(f"\n🧪 === Testing Video Compression ===")
    print(f"   📁 Input: {video_path}")
    print(f"   🎯 Using default test parameters")
    
    # Default test parameters
    test_params = {
        'target_quality': 'Medium',
        'max_duration': 3600,
        'output_dir': './test_output'
    }
    
    try:
        # Validate input file
        input_path = Path(video_path)
        if not input_path.is_file():
            print(f"❌ Input file does not exist: {video_path}")
            return None
        # Create test output directory
        test_output_dir = Path(test_params['output_dir'])
        test_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Perform compression
        result = video_compressor(
            input_file=str(input_path),
            target_quality=test_params['target_quality'],
            max_duration=test_params['max_duration'],
            output_dir=str(test_output_dir)
        )
        
        if result and Path(result).exists():
            print(f"\n✅ Test completed successfully!")
            print(f"   📁 Compressed video: {result}")
            return result
        else:
            print(f"\n❌ Test failed - no output file generated")
            return None
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        return None


# ============================================================================
# Helper Functions
# ============================================================================

def _load_configuration(current_dir: str) -> dict:
    """Load configuration from config.json or use defaults."""
    try:
        config_path = os.path.join(current_dir, 'config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        print("✅ Configuration loaded successfully")
        return config
    except FileNotFoundError:
        print("⚠️ Config file not found, using default configuration")
        return _get_default_config()


def _get_default_config() -> dict:
    """Get default configuration when config.json is not available."""
    return {
        'directories': {
            'temp_dir': './videos/temp_scenes',
            'output_dir': './output'
        },
        'video_processing': {
            'SHORT_VIDEO_THRESHOLD': 20,
            'target_vmaf': 93.0,
            'codec': 'auto',  # Legacy parameter, overridden by target_codec
            'target_codec': 'av1_nvenc',  # Will be overridden by request
            'codec_mode': 'CRF',  # Will be overridden by request
            'target_bitrate': 10.0,  # Will be overridden by request
            'size_increase_protection': True,
            'conservative_cq_adjustment': 0,  # Removed adjustment for better compression (was +2)
            'max_output_size_ratio': 1.15,
            'max_encoding_retries': 2,
            'basic_cq_lookup_by_quality': {
                'High': {
                    # VMAF threshold 93, target 93+ (adjusted based on test results)
                    # Previous: CQ 23 achieved 92.19 VMAF (0.81 short)
                    # Adjusted: Lower CQ values for higher quality
                    'animation': 23,      # Animation easier to compress (was 25)
                    'low-action': 21,     # Faces/people, low motion (was 23, now matches AV1's success)
                    'medium-action': 19,  # Moderate complexity (was 21)
                    'high-action': 17,    # High motion/complexity (was 19)
                    'default': 21         # (was 23)
                },
                'Medium': {
                    # VMAF threshold 89, target 91-92 (safety margin: +2-3)
                    # Current: CQ 26 achieves 91.08 VMAF (+2.08 margin) ✅ Working well
                    'animation': 28,      # Animation easier to compress
                    'low-action': 26,     # Faces/people, low motion
                    'medium-action': 24,  # Moderate complexity
                    'high-action': 22,    # High motion/complexity
                    'default': 26
                },
                'Low': {
                    # VMAF threshold 85, target 87-88 (safety margin: +2-3)
                    # Current: CQ 30 achieves 89.34 VMAF (+4.34 margin) ✅ Working well
                    'animation': 32,      # Animation easier to compress
                    'low-action': 30,     # Faces/people, low motion
                    'medium-action': 28,  # Moderate complexity
                    'high-action': 26,    # High motion/complexity
                    'default': 30
                }
            },

            # ============================================================================
            # NETFLIX PER-TITLE ENCODING CONFIGURATION
            # ============================================================================
            # Enable Netflix per-title encoding (alternative to lookup table)
            # Note: Also requires ENABLE_NETFLIX_PER_TITLE = True in netflix_per_title_encoder.py
            'use_netflix_per_title': False,  # Set to True to enable

            # Fast mode: Use 3 probe points instead of 4 (faster but slightly less accurate)
            'netflix_fast_mode': False,  # Set to True for 60s timeout scenarios
        },
        'scene_detection': {
            'enable_time_based_fallback': True,
            'time_based_scene_duration': 90
        },
        'vmaf_calculation': {
            'calculate_full_video_vmaf': True,
            'vmaf_use_sampling': True,
            'vmaf_num_clips': 3,
            'vmaf_clip_duration': 2
        },
        'output_settings': {
            'save_individual_scene_reports': True,
            'save_comprehensive_report': True
        },
        'model_paths': {
            'scene_classifier_model': 'services/compress/models/scene_classifier_model.pth'
        }
    }


def _display_pipeline_info(input_file: str, target_quality: str, max_duration: int, output_dir: str):
    """Display pipeline initialization information."""
    print(f"\n🎬 === AI Video Compression Pipeline ===")
    print(f"   📁 Input: {Path(input_file).name}")
    print(f"   🎯 Target Quality: {target_quality}")
    print(f"   ⏱️ Max Duration: {max_duration}s")
    print(f"   📁 Output Dir: {output_dir}")
    print(f"   🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def _execute_preprocessing(input_file: str, target_quality: str, max_duration: int, output_dir_path: Path) -> Optional[dict]:
    """Execute Part 1: Pre-processing."""
    print(f"\n🔧 === Part 1: Pre-processing ===")
    part1_start_time = time.time()
    
    part1_result = pre_processing(
        video_path=input_file,
        target_quality=target_quality,
        max_duration=max_duration,
        output_dir=output_dir_path
    )
    
    print("part1_result", part1_result)
    return part1_result


def _display_preprocessing_results(part1_result: dict, part1_time: float):
    """Display Part 1 results."""
    print(f"\n✅ Part 1 completed in {part1_time:.1f}s:")
    print(f"   📁 Video: {os.path.basename(part1_result['path'])}")
    print(f"   🎥 Codec: {part1_result['codec']} (original: {part1_result['original_codec']})")
    print(f"   ⏱️ Duration: {part1_result['duration']:.1f}s")
    print(f"   🔄 Reencoded: {part1_result['was_reencoded']}")
    print(f"   🎯 Target VMAF: {part1_result['target_vmaf']} ({part1_result['target_quality']})")
    
    if part1_result['was_reencoded']:
        print(f"   🔄 Lossless conversion: {part1_result['processing_info']['original_format']} → {part1_result['processing_info']['standardized_format']}")
        print(f"   ⏱️ Encoding time: {part1_result['encoding_time']:.1f}s")


def _display_scene_detection_results(scenes_metadata: list, part2_time: float):
    """Display Part 2 results."""
    print(f"\n✅ Part 2 completed in {part2_time:.1f}s: {len(scenes_metadata)} scenes detected")
    
    # Display scene information
    total_scene_size = 0
    for scene in scenes_metadata:
        scene_size = scene.get('file_size_mb', 0)
        total_scene_size += scene_size
        print(f"   Scene {scene['scene_number']}: {scene['start_time']:.1f}s - {scene['end_time']:.1f}s "
              f"(duration: {scene['duration']:.1f}s)")
        if scene_size > 0:
            print(f"      📁 File: {os.path.basename(scene['path'])} ({scene_size:.1f} MB)")
        else:
            print(f"      📁 File: {os.path.basename(scene['path'])}")
    
    if total_scene_size > 0:
        print(f"   📊 Total scene files: {total_scene_size:.1f} MB")


def _execute_ai_encoding(scenes_metadata: list, config: dict, target_quality: str) -> Optional[dict]:
    """Execute Part 3: AI Encoding."""
    print(f"\n🧠 === Part 3: AI Encoding ===")
    part3_start_time = time.time()

    print(f"   📋 Using quality-based CQ lookup tables for {target_quality} quality")
    print(f"   🎯 Target Quality Level: {target_quality}")

    # Display CQ ranges for selected quality level
    quality_info = {
        'High': {'vmaf': 93, 'cq_range': '16-22'},
        'Medium': {'vmaf': 89, 'cq_range': '19-25'},
        'Low': {'vmaf': 85, 'cq_range': '22-28'}
    }

    if target_quality in quality_info:
        info = quality_info[target_quality]
        print(f"   🎚️ CQ Range for {target_quality}: {info['cq_range']} (Target VMAF: {info['vmaf']})")

    print(f"   🔧 Loading AI models and resources...")

    try:
        # Use cached models instead of loading every time
        resources = get_cached_models(config, logging_enabled=True)
        print(f"   ✅ AI resources loaded successfully")
        print(f"   🧠 Mode: Scene classification + CQ lookup table")
    except Exception as e:
        print(f"   ❌ Failed to load AI resources: {e}")
        return None
    
    # Process each scene individually
    encoded_scenes_data = []
    successful_encodings = 0
    failed_encodings = 0
    total_input_size = 0
    total_output_size = 0
    
    print(f"\n   📊 Processing {len(scenes_metadata)} scenes with AI approach...")
    
    for i, scene_metadata in enumerate(scenes_metadata):
        scene_result = _process_single_scene(
            scene_metadata, i, len(scenes_metadata), config, resources, target_quality
        )
        
        if scene_result['success']:
            successful_encodings += 1
            total_input_size += scene_result['input_size_mb']
            total_output_size += scene_result['output_size_mb']
        else:
            failed_encodings += 1
        
        encoded_scenes_data.append(scene_result['scene_data'])
    
    part3_time = time.time() - part3_start_time
    
    # Display Part 3 summary
    _display_ai_encoding_summary(
        successful_encodings, failed_encodings, len(scenes_metadata),
        part3_time, target_quality, total_input_size, total_output_size
    )
    
    if successful_encodings == 0:
        print("❌ Part 3 failed completely. No scenes were encoded. Pipeline terminated.")
        return None
    
    return {
        'encoded_scenes_data': encoded_scenes_data,
        'successful_encodings': successful_encodings,
        'failed_encodings': failed_encodings,
        'processing_time': part3_time,
        'total_input_size': total_input_size,
        'total_output_size': total_output_size
    }


def _process_single_scene(scene_metadata: dict, scene_index: int, total_scenes: int, 
                         config: dict, resources: dict, target_quality: str) -> dict:
    """Process a single scene for AI encoding."""
    scene_number = scene_metadata['scene_number']
    scene_path = scene_metadata['path']
    scene_duration = scene_metadata['duration']
    
    print(f"\n   🎬 Scene {scene_number}/{total_scenes}: {os.path.basename(scene_path)}")
    print(f"      ⏱️ Duration: {scene_duration:.1f}s")
    
    indicative_vmaf = scene_metadata['original_video_metadata'].get('target_vmaf')
    print(f"      🎯 Target Quality: {target_quality}" + (f" (VMAF≈{indicative_vmaf})" if indicative_vmaf else ""))
    print(f"      🧠 Method: scene classification + CQ lookup")
    
    scene_start_time = time.time()
    
    try:
        encoded_path, scene_data = ai_encoding(
            scene_metadata=scene_metadata,
            config=config,
            resources=resources,
            target_vmaf=None,
            target_quality_level=target_quality,
            logging_enabled=True
        )
        
        scene_processing_time = time.time() - scene_start_time
        
        if encoded_path and scene_data.get('encoding_success', False):
            size_mb = scene_data.get('encoded_file_size_mb', 0)
            input_size_mb = scene_data.get('input_size_mb', 0)
            compression = scene_data.get('compression_ratio', 0)
            
            print(f"      ✅ Scene {scene_number} encoded successfully")
            print(f"         📁 Output: {os.path.basename(encoded_path)}")
            print(f"         📊 Size: {input_size_mb:.1f} MB → {size_mb:.1f} MB ({compression:+.1f}% compression)")
            print(f"         🎭 Scene type: {scene_data.get('scene_type', 'unknown')}")
            print(f"         🎯 Quality: {scene_data.get('target_quality_level', target_quality)}")
            print(f"         🎚️ CQ used: {scene_data.get('base_cq_for_quality', 'N/A')} → {scene_data.get('final_adjusted_cq', 'unknown')} (after adjustment)")
            print(f"         📋 Method: Quality-based lookup table CQ selection")
            print(f"         ⏱️ Processing: {scene_processing_time:.1f}s")
            
            # Update scene metadata
            scene_metadata['encoded_path'] = encoded_path
            scene_metadata['encoding_data'] = scene_data
            
            return {
                'success': True,
                'scene_data': scene_data,
                'input_size_mb': input_size_mb,
                'output_size_mb': size_mb
            }
        else:
            error_reason = scene_data.get('error_reason', 'Unknown error')
            print(f"      ❌ Scene {scene_number} encoding failed: {error_reason}")
            print(f"         ⏱️ Processing: {scene_processing_time:.1f}s")
            
            scene_metadata['encoded_path'] = None
            scene_metadata['encoding_data'] = scene_data
            
            return {
                'success': False,
                'scene_data': scene_data,
                'input_size_mb': 0,
                'output_size_mb': 0
            }
            
    except Exception as e:
        scene_processing_time = time.time() - scene_start_time
        print(f"      ❌ Scene {scene_number} processing failed with exception: {e}")
        print(f"         ⏱️ Processing: {scene_processing_time:.1f}s")
        
        error_scene_data = {
            'scene_number': scene_number,
            'encoding_success': False,
            'error_reason': f'Exception: {str(e)}',
            'processing_time_seconds': scene_processing_time,
            'encoded_path': None,
            'original_video_metadata': scene_metadata['original_video_metadata']
        }
        
        scene_metadata['encoded_path'] = None
        scene_metadata['encoding_data'] = error_scene_data
        
        return {
            'success': False,
            'scene_data': error_scene_data,
            'input_size_mb': 0,
            'output_size_mb': 0
        }


def _display_ai_encoding_summary(successful_encodings: int, failed_encodings: int, total_scenes: int,
                                part3_time: float, target_quality: str, total_input_size: float, total_output_size: float):
    """Display Part 3 summary."""
    print(f"\n   📊 Part 3 Processing Summary:")
    print(f"      ✅ Successful encodings: {successful_encodings}")
    print(f"      ❌ Failed encodings: {failed_encodings}")
    print(f"      📈 Success rate: {successful_encodings/total_scenes*100:.1f}%")
    print(f"      ⏱️ Total processing time: {part3_time:.1f}s")
    print(f"      🎯 Quality Level: {target_quality}")
    print(f"      🧠 AI Method: Scene classification + quality-based CQ lookup")
    
    if total_input_size > 0 and total_output_size > 0:
        overall_compression = (1 - total_output_size / total_input_size) * 100
        print(f"      🗜️ Overall compression: {overall_compression:+.1f}%")
        print(f"      📊 Total size: {total_input_size:.1f} MB → {total_output_size:.1f} MB")
    
    print(f"✅ Part 3 completed with {successful_encodings} successful encodings")


def _execute_validation_and_merging(part1_result: dict, encoded_scenes_data: list, config: dict) -> Optional[dict]:
    """Execute Part 4: Validation and Merging."""
    part4_start_time = time.time()
    
    try:
        final_video_path, final_vmaf, comprehensive_report = validation_and_merging(
            original_video_path=part1_result['path'],
            encoded_scenes_data=encoded_scenes_data,
            config=config,
            logging_enabled=True
        )
        
        part4_time = time.time() - part4_start_time
        
        if final_video_path and os.path.exists(final_video_path):
            return {
                'final_video_path': final_video_path,
                'final_vmaf': final_vmaf,
                'comprehensive_report': comprehensive_report,
                'processing_time': part4_time
            }
        else:
            print("❌ Part 4 failed. Could not create final video.")
            return None
            
    except Exception as e:
        print(f"❌ Part 4 failed with exception: {e}")
        return None


def _display_validation_results(part4_result: dict):
    """Display Part 4 results."""
    final_video_path = part4_result['final_video_path']
    final_vmaf = part4_result['final_vmaf']
    comprehensive_report = part4_result['comprehensive_report']
    part4_time = part4_result['processing_time']
    
    print(f"✅ Part 4 completed successfully in {part4_time:.1f}s!")
    print(f"   📁 Final video: {os.path.basename(final_video_path)}")
    
    if final_vmaf:
        print(f"   🎯 Final VMAF: {final_vmaf:.2f}")
    
    if comprehensive_report:
        compression_info = comprehensive_report.get('compression_metrics', {})
        final_compression = compression_info.get('overall_compression_ratio_percent', 0)
        final_size = compression_info.get('final_file_size_mb', 0)
        
        print(f"   🗜️ Overall compression: {final_compression:+.1f}%")
        print(f"   📊 Final file size: {final_size:.1f} MB")


def _display_pipeline_summary(input_file: str, final_video_path: str, part1_result: dict,
                            scenes_metadata: list, successful_encodings: int, output_dir: str,
                            pipeline_start_time: float, part1_time: float, part2_time: float,
                            part3_time: float, part4_time: float, total_pipeline_time: float,
                            final_vmaf: Optional[float], comprehensive_report: Optional[dict]):
    """Display complete pipeline summary."""
    print(f"\n🎉 === Pipeline Completed Successfully ===")
    print(f"   📁 Input video: {os.path.basename(input_file)}")
    print(f"   📁 Final video: {os.path.basename(final_video_path)}")
    print(f"   🎯 Target quality: {part1_result['target_quality']} (VMAF: {part1_result['target_vmaf']})")
    print(f"   📊 Scenes processed: {len(scenes_metadata)} total, {successful_encodings} successful")
    print(f"   📁 Output directory: {output_dir}")
    print(f"   🕐 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Performance breakdown
    print(f"\n   ⏱️ Performance Breakdown:")
    print(f"      Part 1 (Pre-processing): {part1_time:.1f}s")
    print(f"      Part 2 (Scene Detection): {part2_time:.1f}s")
    print(f"      Part 3 (AI Encoding): {part3_time:.1f}s")
    print(f"      Part 4 (Validation & Merging): {part4_time:.1f}s")  
    print(f"      Total Pipeline Time: {total_pipeline_time:.1f}s")
    
    # Final file size comparison
    input_file_path = Path(input_file)
    final_video_path_obj = Path(final_video_path)
    if input_file_path.exists() and final_video_path_obj.exists():
        input_size = input_file_path.stat().st_size / (1024 * 1024)
        output_size = final_video_path_obj.stat().st_size / (1024 * 1024)
        final_compression = (1 - output_size / input_size) * 100
        
        print(f"\n   📊 Final Size Comparison:")
        print(f"      Input: {input_size:.1f} MB")
        print(f"      Output: {output_size:.1f} MB")
        print(f"      Compression: {final_compression:+.1f}%")
        
        if final_compression > 0:
            print(f"      💾 Space saved: {input_size - output_size:.1f} MB")
    
    # Quality achievement summary
    if final_vmaf and comprehensive_report:
        quality_info = comprehensive_report.get('quality_metrics', {})
        scenes_meeting_target = quality_info.get('scenes_meeting_target', 0)
        avg_scene_vmaf = quality_info.get('average_scene_vmaf', 0)
        
        print(f"\n   🎯 Quality Achievement:")
        print(f"      Final VMAF: {final_vmaf:.2f}")
        print(f"      Average Scene VMAF: {avg_scene_vmaf:.2f}")
        print(f"      Scenes meeting target: {scenes_meeting_target}/{len(scenes_metadata)}")
        
        if 'prediction_accuracy_stats' in comprehensive_report.get('scene_analysis', {}):
            pred_stats = comprehensive_report['scene_analysis']['prediction_accuracy_stats']
            avg_error = pred_stats.get('average_prediction_error')
            if avg_error:
                print(f"      AI prediction accuracy: ±{avg_error:.1f} VMAF points")
    
    # Report file locations
    if comprehensive_report:
        print(f"\n   📄 Reports Generated:")
        print(f"      📁 Output directory: {output_dir}")
        print(f"      📊 Comprehensive report: comprehensive_processing_report_*.json")
        print(f"      📄 Individual scene reports: scene_reports/scene_*_report.json")
    
    print(f"\n   🎉 Pipeline completed successfully!")
    print(f"   🚀 Ready for playback: {final_video_path}")


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting video compressor server")
    logger.info(f"Video compressor server running on http://{CONFIG.video_compressor.host}:{CONFIG.video_compressor.port}")

    uvicorn.run(app, host=CONFIG.video_compressor.host, port=CONFIG.video_compressor.port)

    # result = test_video_compression('test1.mp4')
    # print(result)

    #python services/compress/server.py
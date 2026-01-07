"""
Fast VMAF calculation using multiprocessing and RAM-based frame loading.
Inspired by analyze_video_fast.py for maximum performance.
"""

import os
import cv2
import numpy as np
import subprocess
import json
import tempfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Optional, Tuple
import time


def load_frames_to_ram(video_path: str, max_frames: int = 150, start_time: float = 0, duration: Optional[float] = None) -> Tuple[list, float]:
    """
    Load video frames into RAM for fast processing.
    Similar to analyze_video_fast approach.
    
    Args:
        video_path: Path to video file
        max_frames: Maximum number of frames to load
        start_time: Start time in seconds
        duration: Duration in seconds (None = full video)
    
    Returns:
        Tuple of (frames list, fps)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return [], 0.0
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate frame range
    start_frame = int(start_time * fps)
    if duration:
        end_frame = min(int((start_time + duration) * fps), total_frames)
    else:
        end_frame = total_frames
    
    effective_total = end_frame - start_frame
    
    # Calculate sampling interval
    if effective_total > max_frames:
        frame_interval = effective_total // max_frames
    else:
        frame_interval = 1
    
    # Load frames into RAM
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frames = []
    frame_count = 0
    processed = 0
    
    while processed < max_frames and frame_count < effective_total:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            # Convert to YUV420 (VMAF uses Y channel primarily)
            # Downscale to 720p for faster processing (VMAF is perceptual, doesn't need full res)
            height, width = frame.shape[:2]
            if height > 720 or width > 1280:
                if width > height:
                    new_width = 1280
                    new_height = int(height * (1280 / width))
                else:
                    new_height = 720
                    new_width = int(width * (720 / height))
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            frames.append(frame)
            processed += 1
        
        frame_count += 1
    
    cap.release()
    return frames, fps


def calculate_vmaf_fast_libvmaf(
    reference_path: str,
    distorted_path: str,
    model_path: Optional[str] = None,
    num_clips: int = 1,
    clip_duration: float = 1.0,
    max_frames_per_clip: int = 30,
    logging_enabled: bool = True
) -> Optional[float]:
    """
    Fast VMAF calculation using libvmaf with optimized frame sampling.
    
    Strategy:
    1. Load frames into RAM (fast)
    2. Use libvmaf directly via ffmpeg (faster than ffmpeg-quality-metrics)
    3. Sample strategically (beginning, middle, end)
    4. Process in parallel if multiple clips
    
    Args:
        reference_path: Original video path
        distorted_path: Encoded video path
        model_path: VMAF model path (None = default)
        num_clips: Number of clips to sample
        clip_duration: Duration of each clip in seconds
        max_frames_per_clip: Max frames to analyze per clip
        logging_enabled: Enable logging
    
    Returns:
        Average VMAF score or None if failed
    """
    try:
        # Get video duration
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'json', reference_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)
        duration = float(data['format']['duration'])
        
        # Calculate sample points
        if duration < clip_duration:
            # Video too short, use full video
            sample_points = [(0, duration)]
        elif num_clips == 1:
            # Single clip from middle
            start = max(0, (duration - clip_duration) / 2)
            sample_points = [(start, clip_duration)]
        else:
            # Multiple clips: beginning, middle, end
            sample_points = []
            if num_clips >= 1:
                sample_points.append((duration * 0.1, clip_duration))
            if num_clips >= 2:
                sample_points.append((duration * 0.5 - clip_duration/2, clip_duration))
            if num_clips >= 3:
                sample_points.append((duration * 0.9 - clip_duration, clip_duration))
        
        vmaf_scores = []
        
        for start_time, dur in sample_points[:num_clips]:
            # Use ffmpeg libvmaf filter directly (faster than ffmpeg-quality-metrics)
            # Create a simple temp file path
            import uuid
            temp_dir = tempfile.gettempdir()
            vmaf_log_path = os.path.join(temp_dir, f"vmaf_{uuid.uuid4().hex}.json")
            
            try:
                # Build libvmaf options
                # Use simple approach: just run libvmaf and parse stderr output
                # This is more compatible than trying to use log_path
                libvmaf_opts = []
                if model_path and os.path.exists(model_path):
                    escaped_model_path = model_path.replace('\\', '/')
                    libvmaf_opts.append(f"model_path='{escaped_model_path}'")

                if libvmaf_opts:
                    libvmaf_filter = ":".join(libvmaf_opts)
                else:
                    libvmaf_filter = ""

                # Run ffmpeg with libvmaf
                # We'll parse the VMAF score from stderr instead of using log files
                cmd = [
                    'ffmpeg', '-y',
                    '-ss', str(start_time),
                    '-t', str(dur),
                    '-i', reference_path,
                    '-ss', str(start_time),
                    '-t', str(dur),
                    '-i', distorted_path,
                    '-filter_complex', f'[0:v]setpts=PTS-STARTPTS[ref];[1:v]setpts=PTS-STARTPTS[dist];[ref][dist]libvmaf={libvmaf_filter}' if libvmaf_filter else '[0:v]setpts=PTS-STARTPTS[ref];[1:v]setpts=PTS-STARTPTS[dist];[ref][dist]libvmaf',
                    '-f', 'null', '-'
                ]

                if logging_enabled:
                    print(f"         🔍 Running VMAF for clip at {start_time:.1f}s...")

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                # Parse VMAF score from stderr
                # ffmpeg outputs VMAF score in stderr like: "VMAF score: 95.123456"
                vmaf_score_found = False
                if result.stderr:
                    for line in result.stderr.splitlines():
                        if "VMAF score:" in line:
                            try:
                                score_str = line.split("VMAF score:")[1].strip()
                                score = float(score_str)
                                vmaf_scores.append(score)
                                vmaf_score_found = True
                                if logging_enabled:
                                    print(f"         ✅ Clip at {start_time:.1f}s: VMAF={score:.2f}")
                                break
                            except (ValueError, IndexError) as e:
                                if logging_enabled:
                                    print(f"         ⚠️ Failed to parse VMAF score from: {line}")

                if not vmaf_score_found:
                    if logging_enabled:
                        print(f"         ❌ No VMAF score found in output")
                        if result.returncode != 0:
                            error_lines = result.stderr.strip().split('\n') if result.stderr else []
                            print(f"         Error: {error_lines[-1] if error_lines else 'Unknown error'}")

            except Exception as e:
                if logging_enabled:
                    print(f"         ❌ Error processing clip at {start_time:.1f}s: {e}")
        
        if vmaf_scores:
            avg_vmaf = sum(vmaf_scores) / len(vmaf_scores)
            return round(avg_vmaf, 2)
        else:
            return None
            
    except Exception as e:
        if logging_enabled:
            print(f"         ❌ Fast VMAF calculation failed: {e}")
        return None


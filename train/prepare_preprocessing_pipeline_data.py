#!/usr/bin/env python3
"""
Prepare training data for preprocessing pipeline (VMAF prediction).

Encodes videos with different CQ values and calculates VMAF scores.
"""

import os
import sys
import argparse
import json
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
import subprocess
import tempfile
import time
import cv2
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.compress.utils.analyze_video_fast import analyze_video_fast
# Note: calculate_vmaf_advanced not used - it uses wrong FFmpeg binary


class PreprocessingPipelineDataPreparer:
    def __init__(self, data_dir, output_dir):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find FFmpeg binaries - may need different ones for encoding vs VMAF
        self.ffmpeg_bin = self.find_ffmpeg_for_encoding()  # For encoding (needs NVENC)
        self.ffmpeg_vmaf_bin = self.find_ffmpeg_with_vmaf()  # For VMAF (needs libvmaf)
        
        # Check VMAF support at initialization
        self.has_vmaf_support = self.check_ffmpeg_vmaf_support()
        if not self.has_vmaf_support:
            print("⚠️  WARNING: FFmpeg does not have libvmaf filter support!")
            print("   VMAF calculation will be skipped. Install libvmaf to enable VMAF training.")
            print("   See train/INSTALL_VMAF.md for instructions.")
        
        # CQ ranges for different codecs
        self.cq_ranges = {
            'av1_nvenc': list(range(10, 64, 3)),  # Sample every 3rd value
            'hevc_nvenc': list(range(0, 52, 3)),
            'h264_nvenc': list(range(0, 52, 3))
        }
    
    def find_ffmpeg_for_encoding(self):
        """Find FFmpeg binary with NVENC support for encoding"""
        ffmpeg_candidates = [
            shutil.which('ffmpeg'),    # PATH version (conda, usually has NVENC)
            '/usr/local/bin/ffmpeg',  # Built version
            '/usr/bin/ffmpeg'          # System version
        ]
        
        for ffmpeg_path in ffmpeg_candidates:
            if not ffmpeg_path or not os.path.exists(ffmpeg_path):
                continue
            
            # Check for NVENC
            try:
                result = subprocess.run(
                    [ffmpeg_path, '-encoders'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                if 'nvenc' in result.stdout.decode('utf-8', errors='ignore').lower():
                    print(f"✅ Using FFmpeg with NVENC for encoding: {ffmpeg_path}")
                    return ffmpeg_path
            except:
                continue
        
        # Fallback
        ffmpeg_path = shutil.which('ffmpeg') or 'ffmpeg'
        print(f"⚠️  Using default FFmpeg for encoding: {ffmpeg_path}")
        return ffmpeg_path
    
    def find_ffmpeg_with_vmaf(self):
        """Find FFmpeg binary with both libvmaf and NVENC support"""
        # Check common locations in order of preference
        ffmpeg_candidates = [
            '/usr/local/bin/ffmpeg',  # Our built version
            shutil.which('ffmpeg'),    # PATH version (might have NVENC)
            '/usr/bin/ffmpeg'          # System version
        ]
        
        for ffmpeg_path in ffmpeg_candidates:
            if not ffmpeg_path or not os.path.exists(ffmpeg_path):
                continue
            
            # Check if this ffmpeg has libvmaf
            has_vmaf = False
            has_nvenc = False
            
            try:
                # Check for libvmaf
                result = subprocess.run(
                    [ffmpeg_path, '-filters'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                output = result.stdout.decode('utf-8', errors='ignore')
                if 'libvmaf' in output:
                    has_vmaf = True
                
                # Check for NVENC
                result = subprocess.run(
                    [ffmpeg_path, '-encoders'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                output = result.stdout.decode('utf-8', errors='ignore')
                if 'nvenc' in output.lower():
                    has_nvenc = True
                
                # Prefer FFmpeg with both, but libvmaf is more critical
                if has_vmaf:
                    if has_nvenc:
                        print(f"✅ Using FFmpeg with libvmaf and NVENC: {ffmpeg_path}")
                    else:
                        print(f"✅ Using FFmpeg with libvmaf: {ffmpeg_path}")
                        print(f"   ⚠️  NVENC not available - encoding may be slower")
                    return ffmpeg_path
            except:
                continue
        
        # Fallback: try to find any ffmpeg with NVENC (if libvmaf not critical)
        for ffmpeg_path in ffmpeg_candidates:
            if not ffmpeg_path or not os.path.exists(ffmpeg_path):
                continue
            try:
                result = subprocess.run(
                    [ffmpeg_path, '-encoders'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                if 'nvenc' in result.stdout.decode('utf-8', errors='ignore').lower():
                    print(f"⚠️  Using FFmpeg with NVENC (no libvmaf): {ffmpeg_path}")
                    return ffmpeg_path
            except:
                continue
        
        # Final fallback
        ffmpeg_path = shutil.which('ffmpeg') or 'ffmpeg'
        print(f"⚠️  Using default FFmpeg: {ffmpeg_path}")
        return ffmpeg_path
        
    def encode_video(self, input_path, output_path, codec, cq_value):
        """Encode video with specific codec and CQ value"""
        try:
            if codec == 'av1_nvenc':
                cmd = [
                    self.ffmpeg_bin, '-y', '-i', str(input_path),
                    '-c:v', 'av1_nvenc',
                    '-cq', str(cq_value),
                    '-preset', 'p6',
                    '-b:v', '0',
                    '-an',  # No audio
                    str(output_path)
                ]
            elif codec == 'hevc_nvenc':
                cmd = [
                    self.ffmpeg_bin, '-y', '-i', str(input_path),
                    '-c:v', 'hevc_nvenc',
                    '-cq', str(cq_value),
                    '-preset', 'p6',
                    '-b:v', '0',
                    '-an',
                    str(output_path)
                ]
            elif codec == 'h264_nvenc':
                cmd = [
                    self.ffmpeg_bin, '-y', '-i', str(input_path),
                    '-c:v', 'h264_nvenc',
                    '-cq', str(cq_value),
                    '-preset', 'p6',
                    '-b:v', '0',
                    '-an',
                    str(output_path)
                ]
            else:
                return False
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300
            )
            
            if result.returncode != 0:
                # Check for common errors (only show for debugging)
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                if 'nvenc' in error_msg.lower() and ('not found' in error_msg.lower() or 'unknown' in error_msg.lower()):
                    # This will be caught and reported at higher level
                    pass
                return False
            
            return output_path.exists()
            
        except Exception as e:
            # Don't print every error to reduce noise
            return False
    
    def check_ffmpeg_vmaf_support(self):
        """Check if FFmpeg has libvmaf filter support"""
        try:
            result = subprocess.run(
                [self.ffmpeg_vmaf_bin, '-filters'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return 'libvmaf' in result.stdout.decode('utf-8', errors='ignore')
        except:
            return False
    
    def validate_video(self, video_path):
        """Validate that a video file can be opened and has valid properties"""
        try:
            # Try to open with OpenCV
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                cap.release()
                return False, "Cannot open video file"
            
            # Check basic properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            cap.release()
            
            if fps <= 0:
                return False, "Invalid frame rate"
            if total_frames <= 0:
                return False, "No frames in video"
            if width <= 0 or height <= 0:
                return False, "Invalid resolution"
            
            # Try to probe with FFmpeg to ensure it's readable
            probe_cmd = [
                self.ffmpeg_bin, '-v', 'error', '-i', str(video_path),
                '-f', 'null', '-'
            ]
            result = subprocess.run(
                probe_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='ignore')[:200]
                return False, f"FFmpeg probe failed: {error_msg}"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation exception: {str(e)}"
    
    def calculate_vmaf(self, reference_path, distorted_path, show_errors=False):
        """Calculate VMAF score using available methods"""
        temp_converted = None
        error_details = None
        try:
            # Check if FFmpeg has libvmaf support
            if not self.check_ffmpeg_vmaf_support():
                return None
            
            # Check if distorted video is AV1 - built FFmpeg can't decode AV1
            # Convert to H.264 for VMAF calculation
            try:
                probe_cmd = [
                    self.ffmpeg_vmaf_bin, '-v', 'error', '-select_streams', 'v:0',
                    '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(distorted_path)
                ]
                result = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                codec = result.stdout.decode('utf-8', errors='ignore').strip().lower()
                
                # If AV1, convert to H.264 for VMAF calculation (built FFmpeg can't decode AV1)
                if codec in ['av01', 'av1']:
                    temp_converted = Path(tempfile.mktemp(suffix='.mp4'))
                    convert_cmd = [
                        self.ffmpeg_bin, '-y', '-i', str(distorted_path),
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '18',
                        '-pix_fmt', 'yuv420p', '-an', str(temp_converted)
                    ]
                    convert_result = subprocess.run(
                        convert_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=300
                    )
                    if convert_result.returncode == 0 and temp_converted.exists():
                        distorted_path_final = temp_converted
                    else:
                        # Conversion failed
                        error_details = convert_result.stderr.decode('utf-8', errors='ignore')[:500]
                        if show_errors:
                            print(f"         ⚠️  AV1→H.264 conversion failed: {error_details}")
                        # Try direct anyway
                        distorted_path_final = distorted_path
                        temp_converted = None
                else:
                    distorted_path_final = distorted_path
            except Exception as e:
                # If probe fails, use original
                if show_errors:
                    print(f"         ⚠️  Codec probe failed: {str(e)}")
                distorted_path_final = distorted_path
            
            # Use FFmpeg's libvmaf filter
            output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            output_file.close()
            
            cmd = [
                self.ffmpeg_vmaf_bin, '-y',
                '-i', str(reference_path),
                '-i', str(distorted_path_final),
                '-filter_complex', '[0:v]setpts=PTS-STARTPTS[ref];[1:v]setpts=PTS-STARTPTS,scale=iw:ih[dist];[ref][dist]libvmaf=log_fmt=json:log_path=' + output_file.name,
                '-f', 'null', '-'
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300
            )
            
            if result.returncode == 0 and os.path.exists(output_file.name):
                try:
                    with open(output_file.name, 'r') as f:
                        vmaf_data = json.load(f)
                        # Extract VMAF score
                        if 'frames' in vmaf_data and len(vmaf_data['frames']) > 0:
                            scores = [f.get('metrics', {}).get('vmaf', 0) for f in vmaf_data['frames']]
                            vmaf_score = sum(scores) / len(scores) if scores else None
                            os.unlink(output_file.name)
                            if vmaf_score is not None:
                                return vmaf_score
                except (json.JSONDecodeError, KeyError) as e:
                    if show_errors:
                        print(f"         ⚠️  VMAF JSON parse error: {str(e)}")
            
            # VMAF calculation failed - capture error details
            if result.returncode != 0:
                error_details = result.stderr.decode('utf-8', errors='ignore')[:500]
                if show_errors:
                    print(f"         ⚠️  VMAF calculation error: {error_details}")
            
            if os.path.exists(output_file.name):
                os.unlink(output_file.name)
            
            return None
            
        except Exception as e:
            if show_errors:
                print(f"         ⚠️  VMAF exception: {str(e)}")
            return None
        finally:
            # Cleanup temp converted file
            if temp_converted and temp_converted.exists():
                temp_converted.unlink()
    
    def prepare_dataset(self, videos_dir, max_videos=None, max_encodings_per_video=10, max_duration=None):
        """Prepare dataset by encoding videos with different CQ values
        
        Args:
            videos_dir: Directory containing video files
            max_videos: Maximum number of videos to process (None = all)
            max_encodings_per_video: Maximum encodings per video
            max_duration: Maximum video duration in seconds (None = no limit, default=600 for 10min)
        """
        print(f"\n📊 Preparing preprocessing pipeline dataset...")
        print(f"   Videos directory: {videos_dir}")
        print(f"   Output directory: {self.output_dir}")
        
        # Default max_duration to 600 seconds (10 minutes) if not specified
        # This prevents extremely long videos from taking too long, but allows most videos
        if max_duration is None:
            max_duration = 600  # 10 minutes
        
        if max_duration > 0:
            print(f"   Max video duration: {max_duration}s (videos longer will be skipped)")
        else:
            print(f"   No duration limit (processing all videos)")
        
        # Find video files
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        video_files = []
        for ext in video_extensions:
            video_files.extend(Path(videos_dir).rglob(f"*{ext}"))
        
        if max_videos:
            video_files = video_files[:max_videos]
        
        print(f"   Found {len(video_files)} video files")
        
        # Prepare dataset
        dataset_rows = []
        temp_dir = Path(tempfile.mkdtemp())
        
        failed_videos = 0
        skipped_videos = 0
        
        for video_idx, video_path in enumerate(tqdm(video_files, desc="Processing videos")):
            # Validate video before processing
            is_valid, error_msg = self.validate_video(video_path)
            if not is_valid:
                skipped_videos += 1
                if video_idx < 10:  # Show details for first 10 failures
                    print(f"   ⚠️  Skipping invalid video: {video_path.name}")
                    print(f"      Reason: {error_msg}")
                continue
            
            # Extract video features
            video_features = analyze_video_fast(
                str(video_path),
                max_frames=150,
                logging_enabled=False
            )
            
            if not video_features:
                skipped_videos += 1
                if video_idx < 10:
                    print(f"   ⚠️  Skipping video (feature extraction failed): {video_path.name}")
                continue
            
            # Check video duration (optional limit for processing time)
            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            cap.release()
            
            if max_duration > 0 and duration > max_duration:
                skipped_videos += 1
                if video_idx < 5:
                    print(f"   ⚠️  Skipping video (too long: {duration:.1f}s > {max_duration}s): {video_path.name}")
                continue
            
            # Encode with different CQ values
            codecs_to_test = ['av1_nvenc', 'hevc_nvenc']  # Focus on most used codecs
            
            # Track if this video had any successful encodings
            video_samples = 0
            show_errors = (video_idx < 5)  # Show detailed errors for first 5 videos
            
            for codec in codecs_to_test:
                cq_values = self.cq_ranges[codec][:max_encodings_per_video]
                
                for cq in cq_values:
                    # Encode video
                    encoded_path = temp_dir / f"{video_path.stem}_{codec}_cq{cq}.mp4"
                    
                    if not self.encode_video(video_path, encoded_path, codec, cq):
                        if show_errors:
                            print(f"      ⚠️  Encoding failed: {codec} CQ={cq}")
                        continue
                    
                    # Calculate VMAF (skip if not supported)
                    vmaf_score = None
                    if self.has_vmaf_support:
                        vmaf_score = self.calculate_vmaf(video_path, encoded_path, show_errors=show_errors)
                    
                    # If VMAF calculation failed and we have support, skip this sample
                    if self.has_vmaf_support and vmaf_score is None:
                        if show_errors:
                            print(f"      ⚠️  VMAF calculation failed: {codec} CQ={cq}")
                        encoded_path.unlink()  # Cleanup
                        continue
                    
                    # Successfully collected a sample
                    video_samples += 1
                    
                    # If no VMAF support, use a placeholder (not recommended but allows training to continue)
                    if not self.has_vmaf_support:
                        # Use a simple quality estimate based on file size ratio
                        original_size = video_path.stat().st_size
                        encoded_size = encoded_path.stat().st_size
                        compression_ratio = encoded_size / original_size if original_size > 0 else 1.0
                        # Estimate VMAF based on compression ratio (rough approximation)
                        # Higher compression = lower quality, but this is very rough
                        vmaf_score = max(20, min(100, 100 - (1 - compression_ratio) * 50))
                        if show_errors:
                            print(f"      ⚠️  Using estimated VMAF {vmaf_score:.2f} (libvmaf not available)")
                    
                    # Create dataset row
                    row = {
                        'video_id': f"{video_path.stem}_{codec}_{cq}",
                        'original_path': str(video_path),
                        'codec': codec,
                        'cq': cq,
                        'vmaf': vmaf_score,
                        'metrics_resolution': f"({video_features.get('metrics_resolution_width', 0)}, {video_features.get('metrics_resolution_height', 0)})",
                        'metrics_frame_rate': video_features.get('metrics_frame_rate', 30),
                        'metrics_avg_motion': video_features.get('metrics_avg_motion', 0),
                        'metrics_avg_edge_density': video_features.get('metrics_avg_edge_density', 0),
                        'metrics_avg_texture': video_features.get('metrics_avg_texture', 0),
                        'metrics_avg_temporal_information': video_features.get('metrics_avg_temporal_information', 0),
                        'metrics_avg_spatial_information': video_features.get('metrics_avg_spatial_information', 0),
                        'metrics_avg_color_complexity': video_features.get('metrics_avg_color_complexity', 0),
                        'metrics_avg_motion_variance': video_features.get('metrics_avg_motion_variance', 0),
                        'metrics_avg_grain_noise': video_features.get('metrics_avg_grain_noise', 0),
                    }
                    
                    dataset_rows.append(row)
                    
                    # Cleanup encoded file
                    encoded_path.unlink()
            
            # Track videos with no successful samples
            if video_samples == 0:
                failed_videos += 1
                if show_errors:
                    print(f"   ⚠️  Video produced no samples: {video_path.name}")
            
            # Progress update
            if (video_idx + 1) % 10 == 0:
                print(f"   Processed {video_idx + 1}/{len(video_files)} videos, {len(dataset_rows)} samples collected")
                if skipped_videos > 0 or failed_videos > 0:
                    print(f"      (Skipped: {skipped_videos}, Failed: {failed_videos})")
        
        # Create DataFrame
        df = pd.DataFrame(dataset_rows)
        
        if len(df) == 0:
            print("❌ No data collected!")
            return None
        
        # Save dataset
        dataset_file = self.output_dir / "vmaf_dataset.csv"
        df.to_csv(dataset_file, index=False)
        
        # Save summary
        summary = {
            'total_videos_processed': len(video_files),
            'videos_skipped': skipped_videos,
            'videos_failed': failed_videos,
            'total_samples': len(df),
            'codec_distribution': df['codec'].value_counts().to_dict(),
            'vmaf_stats': {
                'min': float(df['vmaf'].min()),
                'max': float(df['vmaf'].max()),
                'mean': float(df['vmaf'].mean()),
                'std': float(df['vmaf'].std())
            },
            'cq_ranges': {
                codec: {
                    'min': int(df[df['codec'] == codec]['cq'].min()),
                    'max': int(df[df['codec'] == codec]['cq'].max())
                }
                for codec in df['codec'].unique()
            }
        }
        
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✅ Dataset preparation complete!")
        print(f"   Total videos processed: {len(video_files)}")
        print(f"   Videos skipped: {skipped_videos}")
        print(f"   Videos with no samples: {failed_videos}")
        print(f"   Total samples collected: {len(df)}")
        print(f"   Dataset saved to: {dataset_file}")
        print(f"   Summary saved to: {summary_file}")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        
        return df


def main():
    parser = argparse.ArgumentParser(description="Prepare preprocessing pipeline training data")
    parser.add_argument("--data_dir", type=str, required=True,
                       help="Directory containing video files")
    parser.add_argument("--output_dir", type=str, required=True,
                       help="Output directory for prepared dataset")
    parser.add_argument("--max_videos", type=int, default=None,
                       help="Maximum number of videos to process")
    parser.add_argument("--max_encodings_per_video", type=int, default=10,
                       help="Maximum encodings per video")
    parser.add_argument("--max_duration", type=int, default=600,
                       help="Maximum video duration in seconds (0 = no limit, default=600 for 10min)")
    
    args = parser.parse_args()
    
    preparer = PreprocessingPipelineDataPreparer(args.data_dir, args.output_dir)
    df = preparer.prepare_dataset(
        args.data_dir,
        max_videos=args.max_videos,
        max_encodings_per_video=args.max_encodings_per_video,
        max_duration=args.max_duration if args.max_duration > 0 else None
    )


if __name__ == "__main__":
    main()


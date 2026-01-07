"""
Async VMAF calculation and logging module.

This module calculates VMAF scores AFTER returning results to the validator,
avoiding timeout issues while still collecting quality metrics for analysis.

Uses the Validator method (Netflix VMAF tool with VMAFNEG model) - 10 random frames
"""

import os
import json
import time
import random
import asyncio
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple


class AsyncVMAFLogger:
    """Handles async VMAF calculation and logging after compression completes."""
    
    def __init__(self, log_dir: str = "compression_logs/vmaf"):
        """
        Initialize the async VMAF logger.
        
        Args:
            log_dir: Directory to store VMAF calculation logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    async def calculate_and_log_vmaf(
        self,
        request_id: str,
        original_video_path: str,
        compressed_video_path: str,
        target_vmaf: float,
        scene_type: str,
        cq_used: float,
        compression_ratio: float,
        codec: str,
        codec_mode: str,
        original_bitrate: Optional[float] = None,
        target_bitrate: Optional[float] = None,
        requested_bitrate: Optional[float] = None,
        requested_mode: Optional[str] = None,
        validator_uid: Optional[int] = None,
        validator_hotkey: Optional[str] = None,
        environment: Optional[str] = None,
        source_request_id: Optional[str] = None,
        video_analysis: Optional[Dict[str, Any]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None
    ) -> None:
        """
        Calculate VMAF asynchronously using validator method and log results.

        Uses the Validator method (Netflix VMAF tool with VMAFNEG) - 10 random frames

        This runs in the background after the response is returned to the validator.

        Args:
            request_id: Unique request identifier
            original_video_path: Path to original video
            compressed_video_path: Path to compressed video
            target_vmaf: Target VMAF threshold
            scene_type: Detected scene type
            cq_used: CQ value used for encoding
            compression_ratio: Achieved compression ratio
            codec: Codec used
            codec_mode: Actual codec mode used for encoding (CRF/VBR/CBR)
            original_bitrate: Original video bitrate in Mbps
            target_bitrate: Applied target bitrate after minimum bitrate logic (for VBR/CBR modes)
            requested_bitrate: User-requested bitrate (before minimum bitrate enforcement)
            requested_mode: Originally requested mode (before any forcing to VBR)
            source_request_id: Original production request ID (for test comparisons)
            validator_uid: Validator UID (optional)
            validator_hotkey: Validator hotkey (optional)
            environment: Environment (testing/production) (optional)
            video_analysis: Video complexity analysis data from analyze_video_fast (optional)
            width: Video width in pixels (optional)
            height: Video height in pixels (optional)
            fps: Video frame rate (optional)
        """
        print(f"\n📊 [ASYNC VMAF] Starting VMAF calculation for request {request_id}")
        overall_start = time.time()

        try:
            loop = asyncio.get_event_loop()

            # Validator method (Netflix VMAF tool)
            print(f"   🟢 Validator method (VMAFNEG) - 10 random frames...")
            validator_score = await loop.run_in_executor(
                None,
                self._calculate_vmaf_validator_method,
                original_video_path,
                compressed_video_path,
                request_id
            )

            total_time = time.time() - overall_start

            if validator_score is not None:
                meets_threshold = validator_score >= target_vmaf
                margin = validator_score - target_vmaf

                # Detect actual output bitrate from compressed video
                actual_bitrate = self._get_video_bitrate(compressed_video_path)

                # Convert video_analysis to JSON-serializable format (handle numpy types)
                json_safe_video_analysis = None
                if video_analysis:
                    json_safe_video_analysis = {}
                    for key, value in video_analysis.items():
                        if value is None:
                            json_safe_video_analysis[key] = None
                        elif hasattr(value, 'item'):  # numpy scalar (float32, int64, etc.)
                            json_safe_video_analysis[key] = value.item()
                        elif isinstance(value, (list, tuple)):
                            # Convert list/tuple of numpy types
                            json_safe_video_analysis[key] = [v.item() if hasattr(v, 'item') else v for v in value]
                        else:
                            # Regular Python types (int, float, str, bool)
                            json_safe_video_analysis[key] = value

                # Log results
                log_data = {
                    'request_id': request_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'environment': environment if environment else 'unknown',
                    'validator_uid': validator_uid,
                    'validator_hotkey': validator_hotkey,
                    'vmaf_score': round(validator_score, 2),
                    'target_vmaf': target_vmaf,
                    'meets_threshold': meets_threshold,
                    'margin': round(margin, 2),
                    'scene_type': scene_type,
                    'cq_used': cq_used,
                    'compression_ratio': compression_ratio,
                    'codec': codec,
                    'codec_mode': codec_mode,
                    'requested_mode': requested_mode if requested_mode else codec_mode,
                    'mode_was_forced': requested_mode != codec_mode if requested_mode else False,
                    'original_bitrate': round(original_bitrate, 2) if original_bitrate else None,  # Original video bitrate
                    'requested_bitrate': requested_bitrate,  # User-requested bitrate
                    'applied_bitrate': target_bitrate,  # Applied bitrate (after minimum bitrate logic)
                    'actual_bitrate': round(actual_bitrate, 2) if actual_bitrate else None,  # Actual output bitrate
                    'calculation_time': round(total_time, 2),
                    'original_video': os.path.basename(original_video_path),
                    'compressed_video': os.path.basename(compressed_video_path),
                    # Video properties
                    'width': width,
                    'height': height,
                    'fps': round(float(fps), 2) if fps else None,
                    # Video complexity analysis (JSON-safe)
                    'video_analysis': json_safe_video_analysis
                }

                # Add source_request_id only if provided (for test comparisons)
                if source_request_id:
                    log_data['source_request_id'] = source_request_id

                # Save to JSON log
                log_file = self.log_dir / f"{request_id}_vmaf.json"
                with open(log_file, 'w') as f:
                    json.dump(log_data, f, indent=2)

                # Print summary
                status_emoji = "✅" if meets_threshold else "⚠️"
                mode_display = f"{requested_mode}→{codec_mode}" if requested_mode and requested_mode != codec_mode else codec_mode
                env_display = f"[{environment.upper()}]" if environment else ""
                validator_display = f"Validator UID={validator_uid}" if validator_uid is not None else "No validator info"

                # Format bitrate display
                bitrate_parts = []
                if original_bitrate:
                    bitrate_parts.append(f"Original: {original_bitrate:.2f} Mbps")
                if requested_bitrate:
                    bitrate_parts.append(f"Requested: {requested_bitrate} Mbps")
                if target_bitrate:
                    bitrate_parts.append(f"Applied: {target_bitrate} Mbps")
                if actual_bitrate:
                    bitrate_parts.append(f"Actual: {actual_bitrate:.2f} Mbps")
                bitrate_display = ", ".join(bitrate_parts) if bitrate_parts else "N/A"

                print(f"\n{status_emoji} [ASYNC VMAF] Request {request_id} {env_display}:")
                print(f"   👤 {validator_display}")
                print(f"   📊 VMAF Score: {validator_score:.2f} (Target: {target_vmaf:.2f})")
                print(f"   Margin: {margin:+.2f} points")
                print(f"   Scene: {scene_type}, CQ: {cq_used}")
                print(f"   Mode: {mode_display}")
                print(f"   Bitrate: {bitrate_display}")
                print(f"   Compression: {compression_ratio:.2f}x")
                print(f"   Calculation time: {total_time:.1f}s")
                print(f"   Log saved: {log_file}")

            else:
                print(f"❌ [ASYNC VMAF] VMAF calculation failed for request {request_id}")

        except Exception as e:
            print(f"❌ [ASYNC VMAF] Error calculating VMAF for request {request_id}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up video files after VMAF calculation
            try:
                if os.path.exists(original_video_path):
                    os.remove(original_video_path)
                    print(f"🗑️ [ASYNC VMAF] Cleaned up original copy: {os.path.basename(original_video_path)}")
                if os.path.exists(compressed_video_path):
                    os.remove(compressed_video_path)
                    print(f"🗑️ [ASYNC VMAF] Cleaned up compressed copy: {os.path.basename(compressed_video_path)}")
            except Exception as cleanup_error:
                print(f"⚠️ [ASYNC VMAF] Cleanup error: {cleanup_error}")

    def _calculate_vmaf_validator_method(
        self,
        original_video_path: str,
        compressed_video_path: str,
        request_id: str = None
    ) -> Optional[float]:
        """
        Calculate VMAF using validator's method (Netflix VMAF tool).

        Mimics validator's scoring process:
        1. Get total frame count
        2. Sample 10 random frames
        3. Convert both videos to Y4M (only selected frames)
        4. Run Netflix VMAF tool with VMAFNEG model
        5. Parse harmonic mean from XML output

        Args:
            original_video_path: Path to original video
            compressed_video_path: Path to compressed video
            request_id: Unique request identifier for temp file naming

        Returns:
            VMAF score or None if calculation fails
        """
        ref_y4m_path = None
        dist_y4m_path = None
        xml_output = None

        # Use request_id for unique temp file naming to avoid conflicts
        unique_id = request_id if request_id else f"{os.getpid()}_{int(time.time() * 1000)}"

        try:
            # Step 1: Get frame count
            frame_count = self._get_frame_count(original_video_path)
            if frame_count < 10:
                print(f"   ⚠️ Video has only {frame_count} frames, need at least 10")
                return None

            # Step 2: Sample 10 random frames (same as validator)
            sample_count = min(10, frame_count)
            random_frames = sorted(random.sample(range(frame_count), sample_count))
            print(f"   📋 Sampled {sample_count} frames: {random_frames}")

            # Step 3: Convert to Y4M (only selected frames)
            ref_y4m_path = self._convert_to_y4m(original_video_path, random_frames, "ref", unique_id)
            dist_y4m_path = self._convert_to_y4m(compressed_video_path, random_frames, "dist", unique_id)

            if not ref_y4m_path or not dist_y4m_path:
                print(f"   ❌ Y4M conversion failed")
                return None

            # Step 4: Run Netflix VMAF tool with VMAFNEG model
            xml_output = self.log_dir / f"vmaf_validator_{unique_id}.xml"
            vmaf_score = self._run_vmaf_tool(ref_y4m_path, dist_y4m_path, xml_output, neg_model=True)

            return vmaf_score

        except Exception as e:
            print(f"   ❌ Validator method calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # Cleanup temporary files
            for path in [ref_y4m_path, dist_y4m_path, xml_output]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

    def _get_video_bitrate(self, video_path: str) -> Optional[float]:
        """Get actual video bitrate in Mbps using ffprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=bit_rate',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                bitrate_bps = int(result.stdout.strip())
                return bitrate_bps / 1_000_000  # Convert to Mbps
            return None
        except Exception as e:
            print(f"   ⚠️ Bitrate detection failed: {e}")
            return None

    def _get_frame_count(self, video_path: str) -> int:
        """Get total frame count using ffprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-count_packets',
                '-show_entries', 'stream=nb_read_packets',
                '-of', 'csv=p=0',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return int(result.stdout.strip())
            return 0
        except Exception as e:
            print(f"   ⚠️ Frame count failed: {e}")
            return 0

    def _convert_to_y4m(self, video_path: str, random_frames: list, prefix: str, unique_id: str) -> Optional[str]:
        """Convert MP4 to Y4M with only selected frames - matches validator implementation."""
        try:
            output_path = self.log_dir / f"{prefix}_{unique_id}.y4m"

            # Build select expression for FFmpeg - EXACTLY like validator
            # Use double backslash escaping to match validator's implementation
            select_expr = "+".join([f"eq(n\\,{f})" for f in random_frames])

            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f"select='{select_expr}'",
                '-pix_fmt', 'yuv420p',
                '-vsync', 'vfr',
                str(output_path),
                '-y'
            ]

            # Capture stderr to see errors
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120
            )

            if result.returncode == 0 and os.path.exists(output_path):
                # Verify the file has content
                file_size = os.path.getsize(output_path)
                if file_size > 0:
                    return str(output_path)
                else:
                    print(f"   ⚠️ Y4M conversion failed for {prefix}: empty file")
                    return None
            else:
                print(f"   ⚠️ Y4M conversion failed for {prefix}: returncode={result.returncode}")
                if result.stderr:
                    # Print last line of error
                    error_lines = result.stderr.strip().split('\n')
                    if error_lines:
                        print(f"      Error: {error_lines[-1][:100]}")
                return None

        except Exception as e:
            print(f"   ⚠️ Y4M conversion failed for {prefix}: {e}")
            return None

    def _run_vmaf_tool(
        self,
        ref_y4m_path: str,
        dist_y4m_path: str,
        output_xml: Path,
        neg_model: bool = True
    ) -> Optional[float]:
        """Run Netflix VMAF tool and parse result."""
        try:
            # Use path to downloaded model file instead of built-in version
            # Try multiple possible locations for the VMAF NEG model
            if neg_model:
                model_paths = [
                    "/usr/local/share/vmaf/model/vmaf_v0.6.1neg.json",
                    "/usr/share/vmaf/model/vmaf_v0.6.1neg.json",
                    "./models/vmaf/vmaf_v0.6.1neg.json",
                    "services/compress/models/vmaf/vmaf_v0.6.1neg.json"
                ]

                model_param = None
                for model_path in model_paths:
                    if os.path.exists(model_path):
                        model_param = f"path={model_path}"
                        break

                # Fallback to built-in version if file not found
                if not model_param:
                    print(f"   ⚠️ VMAF NEG model file not found, trying built-in version")
                    model_param = "version=vmaf_v0.6.1neg"
            else:
                # Use built-in standard VMAF model
                model_param = "version=vmaf_v0.6.1"

            cmd = [
                'vmaf',
                '-r', ref_y4m_path,
                '-d', dist_y4m_path,
                '--model', model_param,
                '-out-fmt', 'xml',
                '-o', str(output_xml)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                print(f"   ⚠️ VMAF tool failed: {result.stderr}")
                return None

            if not os.path.exists(output_xml):
                print(f"   ⚠️ VMAF output XML not found")
                return None

            # Parse XML to get harmonic mean
            tree = ET.parse(output_xml)
            root = tree.getroot()

            vmaf_metric = root.find(".//metric[@name='vmaf']")
            if vmaf_metric is None:
                print(f"   ⚠️ VMAF metric not found in XML")
                return None

            harmonic_mean = float(vmaf_metric.attrib['harmonic_mean'])
            return harmonic_mean

        except Exception as e:
            print(f"   ⚠️ VMAF tool execution failed: {e}")
            return None


# Global instance
async_vmaf_logger = AsyncVMAFLogger()


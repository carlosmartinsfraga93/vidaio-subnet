"""
View and analyze async VMAF calculation logs.

This script displays VMAF scores calculated after compression,
helping you analyze quality vs compression tradeoffs.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional


def _detect_environment_from_url(video_url: str) -> str:
    """
    Detect environment based on video URL.

    Args:
        video_url: Video URL from request

    Returns:
        'production' if HTTPS URL, 'testing' if file path or local URL, 'unknown' otherwise
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


def _load_request_metadata(request_id: str, metadata_dir: str = "compression_logs/metadata") -> Optional[Dict]:
    """
    Load request metadata for a given request ID.

    Args:
        request_id: Request ID to look up
        metadata_dir: Directory containing request metadata files

    Returns:
        Request metadata dictionary, or None if not found
    """
    metadata_path = Path(metadata_dir) / f"{request_id}.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            return None
    return None


def _get_environment_for_log(log: Dict, metadata_dir: str = "compression_logs/metadata") -> str:
    """
    Get environment for a VMAF log entry.

    If the log has an 'environment' field, use it.
    Otherwise, look up the request metadata and determine from payload_url.

    Args:
        log: VMAF log dictionary
        metadata_dir: Directory containing request metadata files

    Returns:
        Environment string ('production', 'testing', or 'unknown')
    """
    # First, check if log already has environment field
    if 'environment' in log and log['environment']:
        return log['environment']

    # If not, try to get it from request metadata
    request_id = log.get('request_id')
    if request_id:
        metadata = _load_request_metadata(request_id, metadata_dir)
        if metadata:
            request_data = metadata.get('request_data', {})
            payload_url = request_data.get('payload_url', '')
            if payload_url:
                return _detect_environment_from_url(payload_url)

    return 'unknown'


def convert_utc_to_gmt9(timestamp_str: str) -> str:
    """
    Convert UTC timestamp to GMT+9 (JST).

    Args:
        timestamp_str: ISO format timestamp string (UTC)

    Returns:
        Formatted time string in GMT+9
    """
    try:
        # Parse the ISO format timestamp
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        # If no timezone info, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Convert to GMT+9
        gmt9 = timezone(timedelta(hours=9))
        dt_gmt9 = dt.astimezone(gmt9)

        # Format as MM-DD HH:MM:SS
        return dt_gmt9.strftime('%m-%d %H:%M:%S')
    except Exception as e:
        # Fallback: try to extract first 19 characters
        return timestamp_str[:19] if len(timestamp_str) > 19 else timestamp_str


def load_vmaf_logs(log_dir: str = "compression_logs/vmaf",
                   validator_uid: int = None,
                   validator_hotkey: str = None,
                   environment: str = None) -> List[Dict]:
    """
    Load VMAF logs from the log directory with optional filtering.

    Args:
        log_dir: Directory containing VMAF logs
        validator_uid: Filter by validator UID (optional)
        validator_hotkey: Filter by validator hotkey (optional)
        environment: Filter by environment ('testing', 'production', 'unknown') (optional)

    Returns:
        List of log dictionaries matching the filters
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        print(f"❌ Log directory not found: {log_dir}")
        return []

    logs = []
    for log_file in log_path.glob("*_vmaf.json"):
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)

                # Apply filters
                if validator_uid is not None and log_data.get('validator_uid') != validator_uid:
                    continue

                if validator_hotkey is not None and log_data.get('validator_hotkey') != validator_hotkey:
                    continue

                # For environment filter, check log field or lookup from request metadata
                if environment is not None:
                    log_env = _get_environment_for_log(log_data)
                    if log_env != environment:
                        continue

                logs.append(log_data)
        except Exception as e:
            print(f"⚠️ Error loading {log_file}: {e}")

    return logs


def get_vmaf_score(log: Dict) -> float:
    """Extract VMAF score from log (handles both old and new format)."""
    # New format (single method): vmaf_score
    if 'vmaf_score' in log:
        return log['vmaf_score']
    # Legacy dual-method format: vmaf_scores.validator_method or libvmaf
    if 'vmaf_scores' in log:
        vmaf_scores = log['vmaf_scores']
        return vmaf_scores.get('validator_method') or vmaf_scores.get('libvmaf') or 0
    return 0


def display_vmaf_summary(logs: List[Dict]) -> None:
    """Display summary of VMAF logs."""
    if not logs:
        print("📭 No VMAF logs found")
        return

    print(f"\n📊 VMAF Calculation Summary ({len(logs)} requests) - Times shown in GMT+9")
    print("=" * 100)

    # Sort by timestamp (newest first)
    logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    # Statistics
    total_requests = len(logs)
    passed = sum(1 for log in logs if log.get('meets_threshold', False))
    failed = total_requests - passed

    avg_vmaf = sum(get_vmaf_score(log) for log in logs) / total_requests if total_requests > 0 else 0
    avg_margin = sum(log.get('margin', 0) for log in logs) / total_requests if total_requests > 0 else 0
    avg_compression = sum(log.get('compression_ratio', 0) for log in logs) / total_requests if total_requests > 0 else 0

    # Bitrate statistics
    orig_bitrates = [log.get('original_bitrate') for log in logs if log.get('original_bitrate') is not None]
    req_bitrates = [log.get('requested_bitrate') for log in logs if log.get('requested_bitrate') is not None]
    appl_bitrates = [log.get('applied_bitrate') for log in logs if log.get('applied_bitrate') is not None]
    actual_bitrates = [log.get('actual_bitrate') for log in logs if log.get('actual_bitrate') is not None]

    print(f"\n📈 Overall Statistics:")
    print(f"   Total Requests: {total_requests}")
    print(f"   Passed Threshold: {passed} ({passed/total_requests*100:.1f}%)")
    print(f"   Failed Threshold: {failed} ({failed/total_requests*100:.1f}%)")
    print(f"   Average VMAF: {avg_vmaf:.2f}")
    print(f"   Average Margin: {avg_margin:+.2f} points")
    print(f"   Average Compression: {avg_compression:.2f}x")

    if orig_bitrates or req_bitrates or appl_bitrates or actual_bitrates:
        print(f"\n📊 Bitrate Statistics:")
        if orig_bitrates:
            print(f"   Original Bitrate: Avg {sum(orig_bitrates)/len(orig_bitrates):.2f} Mbps (Min: {min(orig_bitrates):.2f}, Max: {max(orig_bitrates):.2f})")
        if req_bitrates:
            print(f"   Requested Bitrate: Avg {sum(req_bitrates)/len(req_bitrates):.2f} Mbps (Min: {min(req_bitrates):.2f}, Max: {max(req_bitrates):.2f})")
        if appl_bitrates:
            print(f"   Applied Bitrate: Avg {sum(appl_bitrates)/len(appl_bitrates):.2f} Mbps (Min: {min(appl_bitrates):.2f}, Max: {max(appl_bitrates):.2f})")
        if actual_bitrates:
            print(f"   Actual Bitrate: Avg {sum(actual_bitrates)/len(actual_bitrates):.2f} Mbps (Min: {min(actual_bitrates):.2f}, Max: {max(actual_bitrates):.2f})")

        # Check how often applied != requested
        if req_bitrates and appl_bitrates:
            overrides = sum(1 for log in logs
                          if log.get('requested_bitrate') is not None
                          and log.get('applied_bitrate') is not None
                          and abs(log.get('requested_bitrate') - log.get('applied_bitrate')) > 0.1)
            if overrides > 0:
                print(f"   ⚠️ Bitrate Overrides: {overrides}/{len(logs)} requests had applied bitrate different from requested")

    print(f"\n📋 Recent Requests (Times in GMT+9):")
    print("-" * 280)
    # Header line 1: Main categories
    print(f"{'Time (GMT+9)':<20} {'Env':<8} {'Val':<6} {'Encoding':<20} {'Resolution':<12} {'FPS':<6} {'Bitrates (Mbps)':<42} {'VMAF':<24} {'Scene':<18} {'CQ':<6} {'Comp':<8} {'File':<25} {'Status'}")
    # Header line 2: Detailed columns
    print(f"{'':<20} {'':<8} {'':<6} {'Codec':<10} {'Mode':<10} {'':<12} {'':<6} {'Orig':<10} {'Req':<10} {'Appl':<10} {'Actual':<10} {'Score':<8} {'Target':<8} {'Margin':<8} {'':<18} {'':<6} {'':<8} {'':<25} {''}")
    print("-" * 280)

    for log in logs[:20]:  # Show last 20
        timestamp = log.get('timestamp', 'N/A')
        time_str = convert_utc_to_gmt9(timestamp)

        # Environment - get from log or lookup from request metadata
        environment = _get_environment_for_log(log)
        env_display = environment[:7] if environment else 'unk'

        # Validator UID
        validator_uid = log.get('validator_uid')
        val_str = str(validator_uid) if validator_uid is not None else 'N/A'
        val_str = val_str[:5]

        codec = log.get('codec', 'N/A')[:9]

        # Display mode: show "CRF→VBR" if mode was forced, otherwise just the mode
        codec_mode = log.get('codec_mode', 'N/A')
        requested_mode = log.get('requested_mode')
        mode_was_forced = log.get('mode_was_forced', False)

        if mode_was_forced and requested_mode:
            mode_display = f"{requested_mode}→{codec_mode}"[:9]
        else:
            mode_display = codec_mode[:9]

        # Get VMAF score (handles both new single-method and legacy dual-method format)
        vmaf = get_vmaf_score(log)
        vmaf_str = f"{vmaf:.2f}"

        target = log.get('target_vmaf', 0)
        margin = log.get('margin', 0)
        scene = log.get('scene_type', 'unknown')[:16]
        cq = log.get('cq_used')  # Can be None for VBR mode
        comp = log.get('compression_ratio', 0)
        meets = log.get('meets_threshold', False)

        # Get resolution and FPS
        width = log.get('width')
        height = log.get('height')
        fps_val = log.get('fps')

        resolution_str = f"{width}x{height}" if width and height else 'N/A'
        fps_str = f"{fps_val:.1f}" if fps_val is not None else 'N/A'

        # Get bitrate values
        original_bitrate = log.get('original_bitrate')
        requested_bitrate = log.get('requested_bitrate')
        applied_bitrate = log.get('applied_bitrate')  # Applied bitrate (after minimum logic)
        actual_bitrate = log.get('actual_bitrate')

        orig_str = f"{original_bitrate:.1f}" if original_bitrate is not None else 'N/A'
        req_str = f"{requested_bitrate:.1f}" if requested_bitrate is not None else 'N/A'
        appl_str = f"{applied_bitrate:.1f}" if applied_bitrate is not None else 'N/A'
        actual_str = f"{actual_bitrate:.1f}" if actual_bitrate is not None else 'N/A'

        # Get compressed filename
        compressed_file = log.get('compressed_video', 'N/A')
        # Truncate filename if too long
        if len(compressed_file) > 23:
            compressed_file = compressed_file[:20] + "..."

        # Display CQ (handle None for VBR mode)
        cq_str = f"{cq:.1f}" if cq is not None else "N/A"

        status = "✅ PASS" if meets else "❌ FAIL"
        margin_str = f"{margin:+.2f}"

        print(f"{time_str:<20} {env_display:<8} {val_str:<6} {codec:<10} {mode_display:<10} {resolution_str:<12} {fps_str:<6} {orig_str:<10} {req_str:<10} {appl_str:<10} {actual_str:<10} {vmaf_str:<8} {target:<8.2f} {margin_str:<8} {scene:<18} {cq_str:<6} {comp:<8.2f} {compressed_file:<25} {status}")

    if len(logs) > 20:
        print(f"\n... and {len(logs) - 20} more requests")

    # Display video analysis data for recent requests
    print(f"\n📊 Video Complexity Analysis (Recent 20 Requests):")
    print("-" * 150)
    print(f"{'Time (GMT+9)':<20} {'Resolution':<12} {'FPS':<6} {'Grain':<8} {'Motion':<8} {'Texture':<8} {'Temporal':<8} {'Spatial':<8} {'Bitrate Var':<12} {'Scene':<18}")
    print("-" * 150)

    for log in logs[:20]:
        timestamp = log.get('timestamp', 'N/A')
        time_str = convert_utc_to_gmt9(timestamp)

        # Get resolution and FPS
        width = log.get('width')
        height = log.get('height')
        fps_val = log.get('fps')
        resolution_str = f"{width}x{height}" if width and height else 'N/A'
        fps_str = f"{fps_val:.1f}" if fps_val is not None else 'N/A'

        # Get video analysis data
        video_analysis = log.get('video_analysis', {})
        if video_analysis:
            grain = video_analysis.get('metrics_avg_grain_noise', 0)
            motion = video_analysis.get('metrics_avg_motion', 0)
            texture = video_analysis.get('metrics_avg_texture', 0)
            temporal = video_analysis.get('metrics_avg_temporal_complexity', 0)
            spatial = video_analysis.get('metrics_avg_spatial_complexity', 0)
            bitrate_var = video_analysis.get('metrics_avg_bitrate_variability', 0)

            grain_str = f"{grain:.2f}"
            motion_str = f"{motion:.3f}"
            texture_str = f"{texture:.2f}"
            temporal_str = f"{temporal:.2f}"
            spatial_str = f"{spatial:.2f}"
            bitrate_var_str = f"{bitrate_var:.2f}"
        else:
            grain_str = motion_str = texture_str = temporal_str = spatial_str = bitrate_var_str = 'N/A'

        scene = log.get('scene_type', 'unknown')[:16]

        print(f"{time_str:<20} {resolution_str:<12} {fps_str:<6} {grain_str:<8} {motion_str:<8} {texture_str:<8} {temporal_str:<8} {spatial_str:<8} {bitrate_var_str:<12} {scene:<18}")

    print("-" * 150)


def display_by_codec_and_mode(logs: List[Dict]) -> None:
    """Display VMAF statistics grouped by codec and mode."""
    if not logs:
        return

    print(f"\n📊 VMAF by Codec & Mode:")
    print("=" * 80)

    # Group by codec and mode
    by_codec_mode = {}
    for log in logs:
        codec = log.get('codec', 'unknown')
        mode = log.get('codec_mode', 'unknown')
        key = f"{codec} + {mode}"
        if key not in by_codec_mode:
            by_codec_mode[key] = []
        by_codec_mode[key].append(log)

    for key, codec_logs in sorted(by_codec_mode.items()):
        count = len(codec_logs)
        avg_vmaf = sum(get_vmaf_score(log) for log in codec_logs) / count
        avg_target = sum(log.get('target_vmaf', 0) for log in codec_logs) / count

        # Calculate average CQ (handle None values for VBR mode)
        cq_values = [log.get('cq_used') for log in codec_logs if log.get('cq_used') is not None]
        avg_cq = sum(cq_values) / len(cq_values) if cq_values else None

        avg_comp = sum(log.get('compression_ratio', 0) for log in codec_logs) / count
        passed = sum(1 for log in codec_logs if log.get('meets_threshold', False))

        # Calculate average bitrates
        orig_bitrates = [log.get('original_bitrate') for log in codec_logs if log.get('original_bitrate') is not None]
        req_bitrates = [log.get('requested_bitrate') for log in codec_logs if log.get('requested_bitrate') is not None]
        appl_bitrates = [log.get('applied_bitrate') for log in codec_logs if log.get('applied_bitrate') is not None]
        actual_bitrates = [log.get('actual_bitrate') for log in codec_logs if log.get('actual_bitrate') is not None]

        print(f"\n{key} ({count} requests):")
        print(f"   Avg VMAF: {avg_vmaf:.2f} (Target: {avg_target:.2f})")
        print(f"   Avg CQ: {avg_cq:.1f}" if avg_cq is not None else "   Avg CQ: N/A (VBR mode)")
        print(f"   Avg Compression: {avg_comp:.2f}x")
        print(f"   Pass Rate: {passed}/{count} ({passed/count*100:.1f}%)")

        if orig_bitrates or req_bitrates or appl_bitrates or actual_bitrates:
            print(f"   Bitrates:")
            if orig_bitrates:
                print(f"      Original: {sum(orig_bitrates)/len(orig_bitrates):.2f} Mbps")
            if req_bitrates:
                print(f"      Requested: {sum(req_bitrates)/len(req_bitrates):.2f} Mbps")
            if appl_bitrates:
                print(f"      Applied: {sum(appl_bitrates)/len(appl_bitrates):.2f} Mbps")
            if actual_bitrates:
                print(f"      Actual: {sum(actual_bitrates)/len(actual_bitrates):.2f} Mbps")


def display_by_scene_type(logs: List[Dict]) -> None:
    """Display VMAF statistics grouped by scene type."""
    if not logs:
        return

    print(f"\n📊 VMAF by Scene Type:")
    print("=" * 80)

    # Group by scene type
    by_scene = {}
    for log in logs:
        scene = log.get('scene_type', 'unknown')
        if scene not in by_scene:
            by_scene[scene] = []
        by_scene[scene].append(log)

    for scene, scene_logs in sorted(by_scene.items()):
        count = len(scene_logs)
        avg_vmaf = sum(get_vmaf_score(log) for log in scene_logs) / count

        # Calculate average CQ (handle None values for VBR mode)
        cq_values = [log.get('cq_used') for log in scene_logs if log.get('cq_used') is not None]
        avg_cq = sum(cq_values) / len(cq_values) if cq_values else None

        avg_comp = sum(log.get('compression_ratio', 0) for log in scene_logs) / count
        passed = sum(1 for log in scene_logs if log.get('meets_threshold', False))

        # Calculate average bitrates
        orig_bitrates = [log.get('original_bitrate') for log in scene_logs if log.get('original_bitrate') is not None]
        req_bitrates = [log.get('requested_bitrate') for log in scene_logs if log.get('requested_bitrate') is not None]
        appl_bitrates = [log.get('applied_bitrate') for log in scene_logs if log.get('applied_bitrate') is not None]
        actual_bitrates = [log.get('actual_bitrate') for log in scene_logs if log.get('actual_bitrate') is not None]

        print(f"\n{scene} ({count} requests):")
        print(f"   Avg VMAF: {avg_vmaf:.2f}")
        print(f"   Avg CQ: {avg_cq:.1f}" if avg_cq is not None else "   Avg CQ: N/A (VBR mode)")
        print(f"   Avg Compression: {avg_comp:.2f}x")
        print(f"   Pass Rate: {passed}/{count} ({passed/count*100:.1f}%)")

        if orig_bitrates or req_bitrates or appl_bitrates or actual_bitrates:
            print(f"   Bitrates:")
            if orig_bitrates:
                print(f"      Original: {sum(orig_bitrates)/len(orig_bitrates):.2f} Mbps")
            if req_bitrates:
                print(f"      Requested: {sum(req_bitrates)/len(req_bitrates):.2f} Mbps")
            if appl_bitrates:
                print(f"      Applied: {sum(appl_bitrates)/len(appl_bitrates):.2f} Mbps")
            if actual_bitrates:
                print(f"      Actual: {sum(actual_bitrates)/len(actual_bitrates):.2f} Mbps")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description='View and analyze VMAF logs')
    parser.add_argument('--validator-uid', type=int, help='Filter by validator UID')
    parser.add_argument('--validator-hotkey', type=str, help='Filter by validator hotkey')
    parser.add_argument('--env', '--environment', type=str, choices=['testing', 'production', 'unknown'],
                       help='Filter by environment (testing/production/unknown)')

    args = parser.parse_args()

    # Build filter description
    filters = []
    if args.validator_uid is not None:
        filters.append(f"Validator UID={args.validator_uid}")
    if args.validator_hotkey:
        filters.append(f"Validator Hotkey={args.validator_hotkey}")
    if args.env:
        filters.append(f"Environment={args.env}")

    filter_desc = f" (Filters: {', '.join(filters)})" if filters else ""

    print(f"🔍 Loading VMAF logs{filter_desc}...")
    logs = load_vmaf_logs(
        validator_uid=args.validator_uid,
        validator_hotkey=args.validator_hotkey,
        environment=args.env
    )

    if logs:
        display_vmaf_summary(logs)
        display_by_codec_and_mode(logs)
        display_by_scene_type(logs)
    else:
        print("\n📭 No VMAF logs found matching the filters")
        print("\n💡 Tip: VMAF logs will appear here after compression requests are processed")
        print("   Logs are saved to: compression_logs/vmaf/")
        print("\n📖 Usage examples:")
        print("   python view_vmaf_logs.py                              # View all logs")
        print("   python view_vmaf_logs.py --env testing                # View only testing logs")
        print("   python view_vmaf_logs.py --env production             # View only production logs")
        print("   python view_vmaf_logs.py --validator-uid 5            # View logs from validator UID 5")
        print("   python view_vmaf_logs.py --validator-hotkey 0x123...  # View logs from specific validator")


if __name__ == "__main__":
    main()


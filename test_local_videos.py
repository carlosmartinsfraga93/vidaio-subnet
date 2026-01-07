#!/usr/bin/env python3
"""
Test script to test compression service with production videos.

This script:
1. Loads production VMAF logs that match the specified status (pass/fail)
2. Finds the original videos and metadata for those logs
3. Runs compression tests with the same parameters
4. Compares test results with production results
"""

import requests
import json
import os
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
import time
from typing import List, Dict, Optional

# Configuration
SERVICE_URL = "http://localhost:29116/compress-video"
TEST_OUTPUT_DIR = "test_output"
RESULTS_FILE = f"{TEST_OUTPUT_DIR}/test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
VMAF_LOG_DIR = "compression_logs/vmaf"
METADATA_DIR = "compression_logs/metadata"
VIDEOS_DIR = "compression_logs/videos"


def _detect_environment_from_url(video_url: str) -> str:
    """Detect environment based on video URL."""
    if not video_url:
        return 'unknown'

    video_url_lower = video_url.lower()

    if video_url_lower.startswith('https://') or video_url_lower.startswith('http://'):
        return 'production'

    if video_url_lower.startswith('file://') or '/' in video_url or '\\' in video_url:
        return 'testing'

    return 'unknown'


def load_production_vmaf_logs(status_filter: str = 'pass', scene_filter: str = None) -> List[Dict]:
    """
    Load production VMAF logs filtered by status and scene type.

    Args:
        status_filter: 'pass' or 'fail' to filter logs
        scene_filter: Scene type to filter (e.g., 'action', 'sports', 'animation', etc.)

    Returns:
        List of VMAF log dictionaries
    """
    vmaf_dir = Path(VMAF_LOG_DIR)
    if not vmaf_dir.exists():
        print(f"❌ VMAF log directory not found: {VMAF_LOG_DIR}")
        return []

    logs = []
    for log_file in vmaf_dir.glob("*_vmaf.json"):
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)

                # Check if it's a production log
                environment = log_data.get('environment', 'unknown')

                # If environment not in log, check metadata
                if environment == 'unknown' or not environment:
                    request_id = log_data.get('request_id')
                    if request_id:
                        metadata = load_request_metadata(request_id)
                        if metadata:
                            payload_url = metadata.get('request_data', {}).get('payload_url', '')
                            environment = _detect_environment_from_url(payload_url)

                # Only include production logs
                if environment != 'production':
                    continue

                # Filter by status
                meets_threshold = log_data.get('meets_threshold', False)
                if status_filter == 'pass' and not meets_threshold:
                    continue
                if status_filter == 'fail' and meets_threshold:
                    continue

                # Filter by scene type
                if scene_filter is not None:
                    scene_type = log_data.get('scene_type', 'unknown')
                    if scene_type.lower() != scene_filter.lower():
                        continue

                logs.append(log_data)

        except Exception as e:
            print(f"⚠️ Error loading {log_file}: {e}")

    return logs


def load_request_metadata(request_id: str) -> Optional[Dict]:
    """Load request metadata for a given request ID."""
    metadata_path = Path(METADATA_DIR) / f"{request_id}.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            return None
    return None


def check_video_exists(request_id: str) -> Optional[Path]:
    """Check if original video exists for a request ID."""
    video_path = Path(VIDEOS_DIR) / f"{request_id}.mp4"
    if video_path.exists():
        return video_path
    return None


def prepare_test_set(count: int, status_filter: str = 'pass', scene_filter: str = None) -> List[Dict]:
    """
    Prepare a test set of production logs with videos and metadata.

    Args:
        count: Number of test cases to prepare
        status_filter: 'pass' or 'fail' to filter logs
        scene_filter: Scene type to filter (optional)

    Returns:
        List of test case dictionaries with log, metadata, and video path
    """
    filter_desc = f"status: {status_filter}"
    if scene_filter:
        filter_desc += f", scene: {scene_filter}"

    print(f"\n🔍 Loading production VMAF logs ({filter_desc})...")
    all_logs = load_production_vmaf_logs(status_filter, scene_filter)

    if not all_logs:
        filter_msg = f"status '{status_filter}'"
        if scene_filter:
            filter_msg += f" and scene '{scene_filter}'"
        print(f"❌ No production logs found with {filter_msg}")
        return []

    filter_msg = f"status '{status_filter}'"
    if scene_filter:
        filter_msg += f" and scene '{scene_filter}'"
    print(f"✅ Found {len(all_logs)} production logs with {filter_msg}")

    # Shuffle logs to get random selection
    import random
    random.shuffle(all_logs)

    test_set = []
    checked_count = 0
    missing_videos = []
    missing_metadata = []

    print(f"\n🔍 Checking for videos and metadata...")

    for log in all_logs:
        if len(test_set) >= count:
            break

        checked_count += 1
        request_id = log.get('request_id')

        if not request_id:
            continue

        # Check if video exists
        video_path = check_video_exists(request_id)
        if not video_path:
            print(f"   ⚠️ Skipping {request_id}: Video not found")
            missing_videos.append(request_id)
            continue

        # Check if metadata exists
        metadata = load_request_metadata(request_id)
        if not metadata:
            print(f"   ⚠️ Skipping {request_id}: Metadata not found")
            missing_metadata.append(request_id)
            continue

        # Add to test set
        test_set.append({
            'log': log,
            'metadata': metadata,
            'video_path': video_path,
            'request_id': request_id
        })

        print(f"   ✅ Added {request_id} ({len(test_set)}/{count})")

    if len(test_set) < count:
        print(f"\n⚠️ Warning: Only found {len(test_set)} complete test cases out of {count} requested")
        print(f"   (Checked {checked_count} logs)")

        if missing_videos or missing_metadata:
            print(f"\n📊 Missing Resources Summary:")
            if missing_videos:
                print(f"   🎥 Missing Videos: {len(missing_videos)}")
                print(f"      Possible reasons:")
                print(f"      - Video cleanup service (video-deleter) removed old files")
                print(f"      - Manual deletion")
                print(f"      - Storage quota exceeded")
                print(f"      - Videos moved to different location")
                if len(missing_videos) <= 5:
                    print(f"      Request IDs: {', '.join(missing_videos[:5])}")
                else:
                    print(f"      First 5 Request IDs: {', '.join(missing_videos[:5])}")

            if missing_metadata:
                print(f"   📋 Missing Metadata: {len(missing_metadata)}")
                print(f"      Possible reasons:")
                print(f"      - Metadata files not created during compression")
                print(f"      - Metadata cleanup or corruption")
                if len(missing_metadata) <= 5:
                    print(f"      Request IDs: {', '.join(missing_metadata[:5])}")
                else:
                    print(f"      First 5 Request IDs: {', '.join(missing_metadata[:5])}")
    else:
        print(f"\n✅ Test set ready: {len(test_set)} test cases")

    return test_set


def run_compression_test(test_case: Dict, test_num: int, total_tests: int) -> Dict:
    """
    Run a single compression test using production log parameters.

    Args:
        test_case: Test case dictionary with log, metadata, and video_path
        test_num: Current test number
        total_tests: Total number of tests

    Returns:
        Test result dictionary
    """
    prod_log = test_case['log']
    metadata = test_case['metadata']
    video_path = test_case['video_path']
    request_id = test_case['request_id']

    # Safety check: Verify video still exists before running test
    if not video_path.exists():
        print(f"\n{'='*100}")
        print(f"📊 Test {test_num}/{total_tests} - Request ID: {request_id}")
        print(f"{'='*100}")
        print(f"❌ SKIPPED: Video file no longer exists: {video_path}")
        print(f"   This video was present during test set creation but has been deleted.")
        print(f"   Possible reasons:")
        print(f"   - Video cleanup service deleted it")
        print(f"   - Manual deletion")
        print(f"   - Storage issue")
        print(f"{'='*100}")
        return {
            'success': False,
            'request_id': request_id,
            'error': 'Video file not found',
            'skipped': True
        }

    # Extract parameters from metadata
    request_data = metadata.get('request_data', {})
    codec = request_data.get('target_codec', 'hevc')
    mode = request_data.get('codec_mode', 'VBR')
    vmaf_threshold = request_data.get('vmaf_threshold', 89.0)
    bitrate = request_data.get('target_bitrate')

    print(f"\n{'='*100}")
    print(f"📊 Test {test_num}/{total_tests} - Request ID: {request_id}")
    print(f"{'='*100}")
    print(f"🎥 Video: {video_path.name}")
    print(f"📁 Path: {video_path}")
    print(f"📦 Size: {video_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"🎬 Codec: {codec.upper()}")
    print(f"⚙️  Mode: {mode}")
    print(f"📊 Target Bitrate: {bitrate} Mbps" if bitrate else "📊 Target Bitrate: Auto (CRF)")
    print(f"🎯 VMAF Threshold: {vmaf_threshold}")
    print(f"\n📋 Production Results:")
    print(f"   VMAF Score: {prod_log.get('vmaf_score', 'N/A')}")
    print(f"   Compression Ratio: {prod_log.get('compression_ratio', 'N/A'):.2f}x")
    print(f"   Status: {'✅ PASS' if prod_log.get('meets_threshold') else '❌ FAIL'}")
    print(f"{'='*100}")

    # Convert to file:// URL with absolute path
    abs_path = video_path.absolute()
    file_url = f"file://{abs_path}"

    payload = {
        "payload_url": file_url,
        "vmaf_threshold": vmaf_threshold,
        "target_codec": codec,
        "codec_mode": mode,
        "source_request_id": request_id  # Link to production request for comparison
    }

    if bitrate is not None:
        payload["target_bitrate"] = bitrate

    start_time = time.time()

    try:
        print(f"🚀 Sending compression request...")
        response = requests.post(SERVICE_URL, json=payload, timeout=600)
        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ SUCCESS ({elapsed_time:.1f}s)")

            return {
                "success": True,
                "request_id": request_id,
                "video_file": str(video_path),
                "codec": codec,
                "mode": mode,
                "bitrate": bitrate,
                "vmaf_threshold": vmaf_threshold,
                "elapsed_time": elapsed_time,
                "response": result,
                "production_log": prod_log,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            print(f"\n❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")

            return {
                "success": False,
                "request_id": request_id,
                "video_file": str(video_path),
                "codec": codec,
                "mode": mode,
                "bitrate": bitrate,
                "vmaf_threshold": vmaf_threshold,
                "elapsed_time": elapsed_time,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
                "production_log": prod_log,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ EXCEPTION: {str(e)}")

        return {
            "success": False,
            "request_id": request_id,
            "video_file": str(video_path),
            "codec": codec,
            "mode": mode,
            "bitrate": bitrate,
            "vmaf_threshold": vmaf_threshold,
            "elapsed_time": elapsed_time,
            "error": str(e),
            "production_log": prod_log,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

def get_test_vmaf_score(result: Dict) -> Optional[float]:
    """Extract VMAF score from test result."""
    if not result.get('success'):
        return None

    # The test will generate a new VMAF log, we need to wait and load it
    # For now, return None as VMAF is calculated asynchronously
    # In practice, you'd need to wait for the async VMAF calculation
    return None


def convert_utc_to_gmt9(timestamp_str: str) -> str:
    """Convert UTC timestamp to GMT+9."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        gmt9 = timezone(timedelta(hours=9))
        dt_gmt9 = dt.astimezone(gmt9)
        return dt_gmt9.strftime('%m-%d %H:%M:%S')
    except:
        return timestamp_str[:19] if len(timestamp_str) > 19 else timestamp_str


def print_comparison_results(results: List[Dict]):
    """Print comparison results between production and test."""
    print(f"\n{'='*200}")
    print("📊 TEST RESULTS - PRODUCTION vs TEST COMPARISON")
    print(f"{'='*200}")
    print(f"{'ReqID':<15} {'Codec':<10} {'Mode':<8} {'Target':<8} {'Prod VMAF':<12} {'Test VMAF':<12} {'VMAF Diff':<12} {'Prod Comp':<12} {'Test Comp':<12} {'Comp Diff':<12} {'Status':<10}")
    print(f"{'-'*200}")

    for result in results:
        request_id = result.get('request_id', 'N/A')[:13]
        codec = result.get('codec', 'N/A').upper()[:8]
        mode = result.get('mode', 'N/A')[:6]
        target = result.get('vmaf_threshold', 0)

        prod_log = result.get('production_log', {})
        prod_vmaf = prod_log.get('vmaf_score', 0)
        prod_comp = prod_log.get('compression_ratio', 0)

        # Test VMAF will be calculated asynchronously, so we show N/A for now
        test_vmaf = 'N/A'
        test_comp = 'N/A'
        vmaf_diff = 'N/A'
        comp_diff = 'N/A'

        status = "✅ PASS" if result.get('success') else "❌ FAIL"

        print(f"{request_id:<15} {codec:<10} {mode:<8} {target:<8.1f} {prod_vmaf:<12.2f} {test_vmaf:<12} {vmaf_diff:<12} {prod_comp:<12.2f} {test_comp:<12} {comp_diff:<12} {status:<10}")

    print(f"{'-'*200}")
    print(f"\n💡 Note: Test VMAF scores are calculated asynchronously.")
    print(f"   Check compression_logs/vmaf/ for the new test VMAF logs after a few minutes.")


def main():
    parser = argparse.ArgumentParser(description='Test compression service with production videos')
    parser.add_argument('--count', type=int, default=10, help='Number of test cases (default: 10)')
    parser.add_argument('--status', type=str, choices=['pass', 'fail'], default='pass',
                       help='Filter production logs by status (default: pass)')
    parser.add_argument('--scene', type=str, default=None,
                       help='Filter by scene type (e.g., action, sports, animation, etc.)')

    args = parser.parse_args()

    # Create test output directory
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

    print("="*100)
    print("🎬 VIDEO COMPRESSION TEST - PRODUCTION VIDEO TESTING")
    print("="*100)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Service: {SERVICE_URL}")
    print(f"📊 Test Count: {args.count}")
    print(f"🎯 Status Filter: {args.status}")
    if args.scene:
        print(f"🎬 Scene Filter: {args.scene}")
    print(f"📁 Output Directory: {TEST_OUTPUT_DIR}")
    print("="*100)

    # Prepare test set
    test_set = prepare_test_set(args.count, args.status, args.scene)

    if not test_set:
        print("\n❌ Cannot proceed without test cases.")
        return

    total_tests = len(test_set)

    # Confirm before starting
    response = input(f"\n⚠️  This will run {total_tests} compression tests. Continue? (y/n): ")
    if response.lower() != 'y':
        print("❌ Test cancelled.")
        return

    # Run tests
    results = []

    for i, test_case in enumerate(test_set, 1):
        result = run_compression_test(test_case, i, total_tests)
        results.append(result)

        # Save results after each test
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=2)

        # Wait between tests
        if i < total_tests:
            wait_time = 5
            print(f"\n⏳ Waiting {wait_time} seconds before next test...")
            time.sleep(wait_time)

    # Print comparison results
    print_comparison_results(results)

    # Print summary
    print(f"\n{'='*100}")
    print("📊 TEST SUMMARY")
    print(f"{'='*100}")

    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful

    print(f"✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    print(f"📁 Results saved to: {RESULTS_FILE}")

    # Print statistics by codec
    print(f"\n{'='*100}")
    print("📊 STATISTICS BY CODEC")
    print(f"{'='*100}")

    by_codec_stats = {}
    for result in results:
        # Skip results that don't have codec (e.g., skipped tests)
        if 'codec' not in result:
            continue

        codec = result['codec']
        if codec not in by_codec_stats:
            by_codec_stats[codec] = {'total': 0, 'success': 0, 'total_time': 0}
        by_codec_stats[codec]['total'] += 1
        if result['success']:
            by_codec_stats[codec]['success'] += 1
        by_codec_stats[codec]['total_time'] += result.get('elapsed_time', 0)

    for codec in sorted(by_codec_stats.keys()):
        stats = by_codec_stats[codec]
        success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        avg_time = stats['total_time'] / stats['total'] if stats['total'] > 0 else 0
        print(f"\n{codec.upper()}:")
        print(f"   Tests: {stats['total']}")
        print(f"   Success: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        print(f"   Avg Time: {avg_time:.1f}s")

    print(f"\n{'='*100}")
    print(f"🎉 All tests completed!")
    print(f"📁 Full results: {RESULTS_FILE}")
    print(f"📁 VMAF logs will be available in: compression_logs/vmaf/")
    print(f"{'='*100}")

if __name__ == "__main__":
    main()


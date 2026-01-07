#!/usr/bin/env python3
"""
Compare test results with production results after VMAF calculation is complete.

This script:
1. Loads test results JSON file
2. Finds the corresponding test VMAF logs
3. Compares test results with production results
4. Displays detailed comparison table
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

# Configuration
VMAF_LOG_DIR = "compression_logs/vmaf"
TEST_OUTPUT_DIR = "test_output"


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


def find_latest_test_results() -> Optional[str]:
    """Find the latest test results file in test_output directory."""
    test_output_path = Path(TEST_OUTPUT_DIR)
    if not test_output_path.exists():
        return None

    # Find all test_results_*.json files
    result_files = list(test_output_path.glob("test_results_*.json"))
    if not result_files:
        return None

    # Sort by modification time, newest first
    result_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return str(result_files[0])


def load_test_results(results_file: str) -> List[Dict]:
    """Load test results from JSON file."""
    results_path = Path(results_file)
    if not results_path.exists():
        print(f"❌ Test results file not found: {results_file}")
        return []

    try:
        with open(results_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading test results: {e}")
        return []


def find_test_vmaf_log(test_result: Dict) -> Optional[Dict]:
    """
    Find the VMAF log for a test result by matching source_request_id.

    The test passes the production request_id as source_request_id in the payload,
    which gets logged in the VMAF log for easy matching.

    If multiple VMAF logs match (from multiple test runs), returns the LATEST one
    based on the timestamp field in the VMAF log.
    """
    if not test_result.get('success'):
        return None

    prod_request_id = test_result.get('request_id')
    if not prod_request_id:
        return None

    # Search through VMAF logs for matching source_request_id
    vmaf_dir = Path(VMAF_LOG_DIR)
    if not vmaf_dir.exists():
        return None

    matching_logs = []

    for vmaf_log_path in vmaf_dir.glob("*_vmaf.json"):
        try:
            with open(vmaf_log_path, 'r') as f:
                vmaf_log = json.load(f)

            # Check if source_request_id matches the production request_id
            if vmaf_log.get('source_request_id') == prod_request_id:
                matching_logs.append(vmaf_log)

        except Exception as e:
            continue

    # If multiple matches found, return the LATEST one (by timestamp in the log)
    if matching_logs:
        # Sort by timestamp field (ISO format sorts correctly as strings)
        matching_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return matching_logs[0]

    return None


def print_comparison_table(comparisons: List[Dict]):
    """Print detailed comparison table."""
    print(f"\n{'='*280}")
    print("📊 PRODUCTION vs TEST COMPARISON")
    print(f"{'='*280}")

    # Header line 1: Main categories
    print(f"{'Request IDs':<32} {'Encoding':<28} {'Bitrates (Mbps)':<50} {'CQ':<17} {'VMAF':<36} {'Compression':<36} {'Status':<10}")

    # Header line 2: Detailed columns
    print(f"{'Prod ReqID':<15} {'Test ReqID':<15} {'Codec':<10} {'Mode':<8} {'Target':<8} "
          f"{'Orig':<10} {'Req':<10} {'Appl':<10} {'Actual':<10} "
          f"{'Prod':<8} {'Test':<8} "
          f"{'Prod':<12} {'Test':<12} {'Δ':<10} "
          f"{'Prod':<12} {'Test':<12} {'Δ':<10} {'':<10}")
    print(f"{'-'*280}")

    for comp in comparisons:
        prod_req_id = comp['prod_request_id'][:13]
        test_req_id = comp.get('test_request_id', 'N/A')[:13]
        codec = comp['codec'].upper()[:8]
        mode = comp['mode'][:6]
        target = comp['vmaf_threshold']

        # Bitrate values (prefer Test data if available, fallback to Production)
        # Test logs have the new bitrate fields, production logs may not
        test_orig_br = comp.get('test_original_bitrate', 'N/A')
        test_req_br = comp.get('test_requested_bitrate', 'N/A')
        test_appl_br = comp.get('test_applied_bitrate', 'N/A')
        test_actual_br = comp.get('test_actual_bitrate', 'N/A')

        # Use test bitrates if available, otherwise try production
        orig_br = test_orig_br if test_orig_br != 'N/A' else comp.get('prod_original_bitrate', 'N/A')
        req_br = test_req_br if test_req_br != 'N/A' else comp.get('prod_requested_bitrate', 'N/A')
        appl_br = test_appl_br if test_appl_br != 'N/A' else comp.get('prod_applied_bitrate', 'N/A')
        actual_br = test_actual_br if test_actual_br != 'N/A' else comp.get('prod_actual_bitrate', 'N/A')

        orig_str = f"{orig_br:.1f}" if orig_br != 'N/A' else 'N/A'
        req_str = f"{req_br:.1f}" if req_br != 'N/A' else 'N/A'
        appl_str = f"{appl_br:.1f}" if appl_br != 'N/A' else 'N/A'
        actual_str = f"{actual_br:.1f}" if actual_br != 'N/A' else 'N/A'

        # CQ values
        prod_cq = comp.get('prod_cq', 'N/A')
        test_cq = comp.get('test_cq', 'N/A')
        prod_cq_str = f"{prod_cq:.1f}" if prod_cq != 'N/A' else 'N/A'
        test_cq_str = f"{test_cq:.1f}" if test_cq != 'N/A' else 'N/A'

        prod_vmaf = comp['prod_vmaf']
        test_vmaf = comp.get('test_vmaf', 'N/A')

        if test_vmaf != 'N/A':
            vmaf_diff = test_vmaf - prod_vmaf
            vmaf_diff_str = f"{vmaf_diff:+.2f}"
        else:
            vmaf_diff_str = 'N/A'

        prod_comp = comp['prod_compression']
        test_comp = comp.get('test_compression', 'N/A')

        if test_comp != 'N/A':
            comp_diff = test_comp - prod_comp
            comp_diff_str = f"{comp_diff:+.2f}x"
        else:
            comp_diff_str = 'N/A'

        # Status
        if test_vmaf == 'N/A':
            status = "⏳ PENDING"
        elif comp.get('test_success'):
            status = "✅ PASS"
        else:
            status = "❌ FAIL"

        # Format values
        prod_vmaf_str = f"{prod_vmaf:.2f}"
        test_vmaf_str = f"{test_vmaf:.2f}" if test_vmaf != 'N/A' else 'N/A'
        prod_comp_str = f"{prod_comp:.2f}x"
        test_comp_str = f"{test_comp:.2f}x" if test_comp != 'N/A' else 'N/A'

        print(f"{prod_req_id:<15} {test_req_id:<15} {codec:<10} {mode:<8} {target:<8.1f} "
              f"{orig_str:<10} {req_str:<10} {appl_str:<10} {actual_str:<10} "
              f"{prod_cq_str:<8} {test_cq_str:<8} "
              f"{prod_vmaf_str:<12} {test_vmaf_str:<12} {vmaf_diff_str:<10} "
              f"{prod_comp_str:<12} {test_comp_str:<12} {comp_diff_str:<10} {status:<10}")

    print(f"{'-'*280}")


def print_statistics(comparisons: List[Dict]):
    """Print statistics about the comparison."""
    total = len(comparisons)
    completed = sum(1 for c in comparisons if c.get('test_vmaf') != 'N/A')
    pending = total - completed

    print(f"\n{'='*100}")
    print("📊 STATISTICS")
    print(f"{'='*100}")
    print(f"Total Tests: {total}")
    print(f"Completed: {completed}")
    print(f"Pending VMAF: {pending}")

    if completed > 0:
        # Calculate average differences
        vmaf_diffs = [c.get('test_vmaf', 0) - c['prod_vmaf']
                     for c in comparisons if c.get('test_vmaf') != 'N/A']
        comp_diffs = [c.get('test_compression', 0) - c['prod_compression']
                     for c in comparisons if c.get('test_compression') != 'N/A']

        avg_vmaf_diff = sum(vmaf_diffs) / len(vmaf_diffs) if vmaf_diffs else 0
        avg_comp_diff = sum(comp_diffs) / len(comp_diffs) if comp_diffs else 0

        print(f"\nAverage VMAF Difference: {avg_vmaf_diff:+.2f}")
        print(f"Average Compression Difference: {avg_comp_diff:+.2f}x")

        # Better/worse counts
        better_vmaf = sum(1 for d in vmaf_diffs if d > 0)
        worse_vmaf = sum(1 for d in vmaf_diffs if d < 0)
        same_vmaf = sum(1 for d in vmaf_diffs if d == 0)

        better_comp = sum(1 for d in comp_diffs if d > 0)
        worse_comp = sum(1 for d in comp_diffs if d < 0)
        same_comp = sum(1 for d in comp_diffs if d == 0)

        print(f"\nVMAF Comparison:")
        print(f"  Better than production: {better_vmaf}")
        print(f"  Worse than production: {worse_vmaf}")
        print(f"  Same as production: {same_vmaf}")

        print(f"\nCompression Comparison:")
        print(f"  Better than production: {better_comp}")
        print(f"  Worse than production: {worse_comp}")
        print(f"  Same as production: {same_comp}")

        # Bitrate statistics
        print(f"\n{'='*100}")
        print("📊 BITRATE ANALYSIS (Test Results)")
        print(f"{'='*100}")

        # Collect bitrate data (prefer test data, fallback to production)
        orig_bitrates = []
        req_bitrates = []
        appl_bitrates = []
        actual_bitrates = []

        for c in comparisons:
            # Use test bitrates if available, otherwise production
            orig = c.get('test_original_bitrate', c.get('prod_original_bitrate', 'N/A'))
            req = c.get('test_requested_bitrate', c.get('prod_requested_bitrate', 'N/A'))
            appl = c.get('test_applied_bitrate', c.get('prod_applied_bitrate', 'N/A'))
            actual = c.get('test_actual_bitrate', c.get('prod_actual_bitrate', 'N/A'))

            if orig != 'N/A':
                orig_bitrates.append(orig)
            if req != 'N/A':
                req_bitrates.append(req)
            if appl != 'N/A':
                appl_bitrates.append(appl)
            if actual != 'N/A':
                actual_bitrates.append(actual)

        if orig_bitrates:
            print(f"\nOriginal Video Bitrate:")
            print(f"  Average: {sum(orig_bitrates)/len(orig_bitrates):.2f} Mbps")
            print(f"  Min: {min(orig_bitrates):.2f} Mbps")
            print(f"  Max: {max(orig_bitrates):.2f} Mbps")

        if req_bitrates:
            print(f"\nRequested Bitrate:")
            print(f"  Average: {sum(req_bitrates)/len(req_bitrates):.2f} Mbps")
            print(f"  Min: {min(req_bitrates):.2f} Mbps")
            print(f"  Max: {max(req_bitrates):.2f} Mbps")

        if appl_bitrates:
            print(f"\nApplied Bitrate (after minimum logic):")
            print(f"  Average: {sum(appl_bitrates)/len(appl_bitrates):.2f} Mbps")
            print(f"  Min: {min(appl_bitrates):.2f} Mbps")
            print(f"  Max: {max(appl_bitrates):.2f} Mbps")

            # Check how often applied != requested
            overrides = 0
            for c in comparisons:
                test_appl = c.get('test_applied_bitrate', 'N/A')
                test_req = c.get('test_requested_bitrate', 'N/A')
                prod_appl = c.get('prod_applied_bitrate', 'N/A')
                prod_req = c.get('prod_requested_bitrate', 'N/A')

                # Use test data if available, otherwise production
                appl = test_appl if test_appl != 'N/A' else prod_appl
                req = test_req if test_req != 'N/A' else prod_req

                if appl != 'N/A' and req != 'N/A' and abs(appl - req) > 0.01:
                    overrides += 1

            if overrides > 0:
                print(f"  ⚠️ Minimum bitrate overrides: {overrides} times")

        if actual_bitrates:
            print(f"\nActual Output Bitrate:")
            print(f"  Average: {sum(actual_bitrates)/len(actual_bitrates):.2f} Mbps")
            print(f"  Min: {min(actual_bitrates):.2f} Mbps")
            print(f"  Max: {max(actual_bitrates):.2f} Mbps")

            # Bitrate accuracy (actual vs applied)
            if appl_bitrates and len(actual_bitrates) == len(appl_bitrates):
                accuracies = [(actual/applied)*100 for actual, applied in zip(actual_bitrates, appl_bitrates)]
                avg_accuracy = sum(accuracies) / len(accuracies)
                print(f"  Accuracy (actual/applied): {avg_accuracy:.1f}%")


def main():
    parser = argparse.ArgumentParser(description='Compare test results with production results')
    parser.add_argument('results_file', type=str, nargs='?', default=None,
                       help='Test results JSON file (default: latest in test_output/)')
    parser.add_argument('--show-pending', action='store_true',
                       help='Show tests that are still pending VMAF calculation')

    args = parser.parse_args()

    # If no results file specified, find the latest one
    results_file = args.results_file
    if not results_file:
        results_file = find_latest_test_results()
        if not results_file:
            print(f"❌ No test results found in {TEST_OUTPUT_DIR}/")
            print(f"   Please run test_local_videos.py first or specify a results file.")
            return
        print(f"📁 Using latest test results: {results_file}")

    print("="*100)
    print("🔍 COMPARING TEST RESULTS WITH PRODUCTION")
    print("="*100)
    print(f"📁 Results File: {results_file}")
    print("="*100)

    # Load test results
    test_results = load_test_results(results_file)

    if not test_results:
        print("\n❌ No test results found.")
        return

    print(f"\n✅ Loaded {len(test_results)} test results")

    # Build comparison data
    comparisons = []

    for result in test_results:
        prod_log = result.get('production_log', {})

        comparison = {
            'prod_request_id': result.get('request_id', 'N/A'),
            'codec': result.get('codec', 'N/A'),
            'mode': result.get('mode', 'N/A'),
            'bitrate': result.get('bitrate'),
            'vmaf_threshold': result.get('vmaf_threshold', 0),
            'prod_vmaf': prod_log.get('vmaf_score', 0),
            'prod_compression': prod_log.get('compression_ratio', 0),
            'prod_cq': prod_log.get('cq_used', 'N/A'),
            # Production bitrate information
            'prod_original_bitrate': prod_log.get('original_bitrate', 'N/A'),
            'prod_requested_bitrate': prod_log.get('requested_bitrate', 'N/A'),
            'prod_applied_bitrate': prod_log.get('applied_bitrate', 'N/A'),
            'prod_actual_bitrate': prod_log.get('actual_bitrate', 'N/A'),
            'test_success': result.get('success', False),
        }

        # Try to find test VMAF log
        test_vmaf_log = find_test_vmaf_log(result)

        if test_vmaf_log:
            comparison['test_request_id'] = test_vmaf_log.get('request_id', 'N/A')
            comparison['test_vmaf'] = test_vmaf_log.get('vmaf_score', 0)
            comparison['test_compression'] = test_vmaf_log.get('compression_ratio', 0)
            comparison['test_cq'] = test_vmaf_log.get('cq_used', 'N/A')
            # Test bitrate information
            comparison['test_original_bitrate'] = test_vmaf_log.get('original_bitrate', 'N/A')
            comparison['test_requested_bitrate'] = test_vmaf_log.get('requested_bitrate', 'N/A')
            comparison['test_applied_bitrate'] = test_vmaf_log.get('applied_bitrate', 'N/A')
            comparison['test_actual_bitrate'] = test_vmaf_log.get('actual_bitrate', 'N/A')
        else:
            comparison['test_request_id'] = 'N/A'
            comparison['test_vmaf'] = 'N/A'
            comparison['test_compression'] = 'N/A'
            comparison['test_cq'] = 'N/A'
            comparison['test_original_bitrate'] = 'N/A'
            comparison['test_requested_bitrate'] = 'N/A'
            comparison['test_applied_bitrate'] = 'N/A'
            comparison['test_actual_bitrate'] = 'N/A'

        comparisons.append(comparison)

    # Filter if needed
    if not args.show_pending:
        comparisons = [c for c in comparisons if c.get('test_vmaf') != 'N/A']

    if not comparisons:
        print("\n⚠️ No completed test results found.")
        print("   VMAF logs may still be processing. Try again later or use --show-pending flag.")
        return

    # Print comparison table
    print_comparison_table(comparisons)

    # Print statistics
    print_statistics(comparisons)

    print(f"\n{'='*100}")
    print("✅ Comparison complete!")
    print(f"{'='*100}")


if __name__ == "__main__":
    main()


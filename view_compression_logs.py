#!/usr/bin/env python3
"""
View and analyze compression logs.

This script provides a dashboard to monitor compression requests,
view statistics, and analyze performance.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def load_request_index():
    """Load the request index."""
    index_file = Path("compression_logs/request_index.json")
    if not index_file.exists():
        print("❌ No compression logs found!")
        return None
    
    try:
        with open(index_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading request index: {e}")
        return None


def display_statistics(index_data):
    """Display overall statistics."""
    requests = index_data.get('requests', [])
    total = len(requests)
    
    if total == 0:
        print("📊 No requests logged yet.")
        return
    
    successful = sum(1 for r in requests if r['status'] == 'success')
    failed = total - successful
    success_rate = (successful / total * 100) if total > 0 else 0
    
    # Calculate disk usage
    logs_dir = Path("compression_logs")
    videos_dir = logs_dir / "videos"
    results_dir = logs_dir / "results"
    
    videos_size = sum(f.stat().st_size for f in videos_dir.glob("*.mp4")) if videos_dir.exists() else 0
    results_size = sum(f.stat().st_size for f in results_dir.glob("*")) if results_dir.exists() else 0
    total_size = videos_size + results_size
    
    print(f"\n{'='*80}")
    print(f"📊 COMPRESSION STATISTICS")
    print(f"{'='*80}\n")
    print(f"Total Requests:    {total}")
    print(f"✅ Successful:     {successful} ({success_rate:.1f}%)")
    print(f"❌ Failed:         {failed} ({100-success_rate:.1f}%)")
    print(f"\n💾 Disk Usage:")
    print(f"   Videos:         {videos_size / (1024*1024):.2f} MB")
    print(f"   Results:        {results_size / (1024*1024):.2f} MB")
    print(f"   Total:          {total_size / (1024*1024):.2f} MB")
    print(f"\n📅 Last Updated:   {index_data.get('last_updated', 'N/A')}")
    print(f"📦 Max Requests:   {index_data.get('max_requests', 100)}")
    print()


def display_recent_requests(index_data, limit=10):
    """Display recent requests."""
    requests = index_data.get('requests', [])
    recent = requests[-limit:] if len(requests) > limit else requests
    recent.reverse()  # Most recent first
    
    print(f"\n{'='*80}")
    print(f"📋 RECENT REQUESTS (Last {len(recent)})")
    print(f"{'='*80}\n")
    
    for i, req in enumerate(recent, 1):
        status_icon = "✅" if req['status'] == 'success' else "❌"
        timestamp = req.get('timestamp', 'N/A')
        
        # Parse timestamp for better display
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            time_str = timestamp
        
        print(f"{i}. {status_icon} {req['request_id'][:8]}... - {time_str}")
        
        # Load metadata for more details
        metadata_file = Path(req.get('metadata_path', ''))
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    req_data = metadata.get('request_data', {})
                    
                    print(f"   VMAF: {req_data.get('vmaf_threshold', 'N/A')}, "
                          f"Codec: {req_data.get('target_codec', 'N/A')}, "
                          f"Mode: {req_data.get('codec_mode', 'N/A')}")
                    
                    if metadata.get('error'):
                        print(f"   Error: {metadata['error'][:60]}...")
            except Exception as e:
                print(f"   (Could not load metadata: {e})")
        
        print()


def analyze_codec_usage(index_data):
    """Analyze codec usage patterns."""
    metadata_dir = Path("compression_logs/metadata")
    if not metadata_dir.exists():
        return
    
    codec_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
    vmaf_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
    
    for req in index_data.get('requests', []):
        metadata_file = metadata_dir / f"{req['request_id']}.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    req_data = metadata.get('request_data', {})
                    
                    codec = req_data.get('target_codec', 'unknown')
                    vmaf = req_data.get('vmaf_threshold', 'unknown')
                    status = req['status']
                    
                    codec_stats[codec]['total'] += 1
                    vmaf_stats[vmaf]['total'] += 1
                    
                    if status == 'success':
                        codec_stats[codec]['success'] += 1
                        vmaf_stats[vmaf]['success'] += 1
                    else:
                        codec_stats[codec]['failed'] += 1
                        vmaf_stats[vmaf]['failed'] += 1
            except:
                pass
    
    if codec_stats:
        print(f"\n{'='*80}")
        print(f"🎥 CODEC USAGE ANALYSIS")
        print(f"{'='*80}\n")
        
        for codec, stats in sorted(codec_stats.items()):
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"{codec}:")
            print(f"  Total: {stats['total']}, Success: {stats['success']}, "
                  f"Failed: {stats['failed']} ({success_rate:.1f}% success)")
        
        print(f"\n{'='*80}")
        print(f"🎯 VMAF THRESHOLD ANALYSIS")
        print(f"{'='*80}\n")
        
        for vmaf, stats in sorted(vmaf_stats.items()):
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"VMAF {vmaf}:")
            print(f"  Total: {stats['total']}, Success: {stats['success']}, "
                  f"Failed: {stats['failed']} ({success_rate:.1f}% success)")
        print()


def main():
    parser = argparse.ArgumentParser(description="View compression logs and statistics")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--recent", type=int, default=10, help="Number of recent requests to show (default: 10)")
    parser.add_argument("--analyze", action="store_true", help="Analyze codec and VMAF usage")
    parser.add_argument("--all", action="store_true", help="Show all information")
    
    args = parser.parse_args()
    
    # Load index
    index_data = load_request_index()
    if not index_data:
        return
    
    # If no flags, show everything
    if not (args.stats or args.analyze) or args.all:
        display_statistics(index_data)
        display_recent_requests(index_data, limit=args.recent)
        analyze_codec_usage(index_data)
    else:
        if args.stats:
            display_statistics(index_data)
        
        if args.recent:
            display_recent_requests(index_data, limit=args.recent)
        
        if args.analyze:
            analyze_codec_usage(index_data)


if __name__ == "__main__":
    main()


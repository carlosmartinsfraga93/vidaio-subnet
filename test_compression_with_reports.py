#!/usr/bin/env python3
"""
Test compression using tmp folder files and compare with existing reports.
This helps verify fixes before re-registering the miner.
"""
import os
import json
import sys
from pathlib import Path
from datetime import datetime
import subprocess

def find_tmp_files():
    """Find all video files in tmp folder."""
    tmp_dir = Path("tmp")
    if not tmp_dir.exists():
        print("❌ tmp/ directory not found")
        return []
    
    video_files = list(tmp_dir.glob("*.mp4"))
    print(f"📁 Found {len(video_files)} video files in tmp/")
    return video_files

def find_existing_report(video_file):
    """Find existing report for a video file."""
    output_dir = Path("output")
    if not output_dir.exists():
        return None
    
    # Extract UUID from filename (format: uuid.mp4)
    video_name = video_file.stem
    
    # Look for matching report
    report_pattern = f"{video_name}_encoding_report.json"
    report_path = output_dir / report_pattern
    
    if report_path.exists():
        return report_path
    
    # Also check if there's a report with the UUID in the name
    for report_file in output_dir.glob("*_encoding_report.json"):
        if video_name in report_file.name:
            return report_file
    
    return None

def load_report(report_path):
    """Load and parse a report file."""
    try:
        with open(report_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"   ❌ Error loading report: {e}")
        return None

def run_compression_test(video_file, target_vmaf=85.0, target_codec='av1', codec_mode='VBR', target_bitrate=20.0):
    """Run compression test on a video file."""
    print(f"\n{'='*80}")
    print(f"Testing: {video_file.name}")
    print(f"{'='*80}")
    
    # Check if test script exists
    test_script = Path("test_local_compression.py")
    if not test_script.exists():
        print("❌ test_local_compression.py not found")
        return None
    
    # Run compression
    cmd = [
        sys.executable, str(test_script),
        str(video_file),
        "--vmaf", str(target_vmaf),
        "--codec", target_codec,
        "--mode", codec_mode,
        "--bitrate", str(target_bitrate)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"❌ Compression failed:")
            print(result.stderr)
            return None
        
        # Find the generated report
        output_dir = Path("output")
        video_name = video_file.stem
        
        # Find most recent report for this video
        reports = sorted(
            output_dir.glob(f"{video_name}*_encoding_report.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if reports:
            return load_report(reports[0])
        else:
            print("   ⚠️  No report generated")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ Compression timed out (>5 minutes)")
        return None
    except Exception as e:
        print(f"❌ Error running compression: {e}")
        return None

def compare_reports(old_report, new_report, video_name):
    """Compare old and new reports."""
    print(f"\n{'='*80}")
    print(f"Comparison: {video_name}")
    print(f"{'='*80}")
    
    if not old_report:
        print("⚠️  No old report found - this is a new test")
        return
    
    if not new_report:
        print("❌ No new report generated")
        return
    
    # Extract key metrics
    old_quality = old_report.get('quality_metrics', {})
    new_quality = new_report.get('quality_metrics', {})
    
    old_compression = old_report.get('compression_metrics', {})
    new_compression = new_report.get('compression_metrics', {})
    
    # VMAF Comparison (CRITICAL)
    print("\n📊 VMAF Comparison (CRITICAL):")
    old_vmaf = old_quality.get('final_vmaf_score')
    new_vmaf = new_quality.get('final_vmaf_score')
    
    old_vmaf_time = old_quality.get('vmaf_calculation_time', 0)
    new_vmaf_time = new_quality.get('vmaf_calculation_time', 0)
    
    print(f"   Old Report:")
    print(f"      VMAF: {old_vmaf if old_vmaf is not None else 'NULL ❌'}")
    print(f"      Calculation Time: {old_vmaf_time:.2f}s")
    
    print(f"   New Report:")
    print(f"      VMAF: {new_vmaf if new_vmaf is not None else 'NULL ❌'}")
    print(f"      Calculation Time: {new_vmaf_time:.2f}s")
    
    if old_vmaf is None and new_vmaf is not None:
        print(f"   ✅ FIXED! VMAF is now being calculated!")
    elif old_vmaf is None and new_vmaf is None:
        print(f"   ❌ STILL BROKEN: VMAF still NULL")
    elif new_vmaf is not None:
        print(f"   ✅ VMAF calculated: {new_vmaf:.2f}")
        if old_vmaf is not None:
            diff = new_vmaf - old_vmaf
            print(f"   Change: {diff:+.2f}")
    
    # Compression Comparison
    print("\n🗜️  Compression Comparison:")
    old_ratio = old_compression.get('size_ratio', 1.0)
    new_ratio = new_compression.get('size_ratio', 1.0)
    
    old_compression_ratio = 1 / old_ratio if old_ratio > 0 else 0
    new_compression_ratio = 1 / new_ratio if new_ratio > 0 else 0
    
    print(f"   Old Report:")
    print(f"      Size Ratio: {old_ratio:.4f} ({old_compression_ratio:.2f}x compression)")
    
    print(f"   New Report:")
    print(f"      Size Ratio: {new_ratio:.4f} ({new_compression_ratio:.2f}x compression)")
    
    if new_ratio < old_ratio:
        improvement = ((old_ratio - new_ratio) / old_ratio) * 100
        print(f"   ✅ Improved compression by {improvement:.1f}%")
    elif new_ratio > old_ratio:
        print(f"   ⚠️  Compression got worse")
    
    # CQ Comparison
    print("\n🎚️  CQ Values:")
    old_scenes = old_report.get('comprehensive_training_data', {}).get('encoding_optimization_data', [])
    new_scenes = new_report.get('comprehensive_training_data', {}).get('encoding_optimization_data', [])
    
    if old_scenes and new_scenes:
        old_cq = old_scenes[0].get('final_adjusted_cq')
        new_cq = new_scenes[0].get('final_adjusted_cq')
        
        print(f"   Old CQ: {old_cq}")
        print(f"   New CQ: {new_cq}")
        
        if new_cq and old_cq:
            if new_cq > old_cq:
                print(f"   ✅ CQ increased (better compression expected)")
            elif new_cq < old_cq:
                print(f"   ⚠️  CQ decreased")
    
    # Scene VMAF Comparison
    print("\n🎬 Scene VMAF Details:")
    old_part4 = old_report.get('comprehensive_training_data', {}).get('pipeline_stages_data', {}).get('part4_vmaf_calculation', [])
    new_part4 = new_report.get('comprehensive_training_data', {}).get('pipeline_stages_data', {}).get('part4_vmaf_calculation', [])
    
    if old_part4 and new_part4:
        old_scene_vmaf = old_part4[0].get('actual_vmaf')
        new_scene_vmaf = new_part4[0].get('actual_vmaf')
        
        old_status = old_part4[0].get('vmaf_calculation_status')
        new_status = new_part4[0].get('vmaf_calculation_status')
        
        print(f"   Old Scene VMAF: {old_scene_vmaf if old_scene_vmaf is not None else 'NULL'}")
        print(f"   Old Status: {old_status}")
        print(f"   New Scene VMAF: {new_scene_vmaf if new_scene_vmaf is not None else 'NULL'}")
        print(f"   New Status: {new_status}")
        
        if old_scene_vmaf is None and new_scene_vmaf is not None:
            print(f"   ✅ Scene VMAF is now being calculated!")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    fixes = []
    issues = []
    
    if old_vmaf is None and new_vmaf is not None:
        fixes.append("✅ VMAF calculation FIXED")
    elif old_vmaf is None and new_vmaf is None:
        issues.append("❌ VMAF still NULL")
    
    if new_compression_ratio >= 5.0:
        fixes.append("✅ Good compression achieved")
    elif new_compression_ratio < 2.0:
        issues.append("⚠️  Poor compression")
    
    if fixes:
        print("Fixes:")
        for fix in fixes:
            print(f"   {fix}")
    
    if issues:
        print("Issues:")
        for issue in issues:
            print(f"   {issue}")
    
    if not fixes and not issues:
        print("   No significant changes")

def main():
    print("="*80)
    print("COMPRESSION TEST WITH REPORT COMPARISON")
    print("="*80)
    print("\nThis script will:")
    print("1. Find video files in tmp/ folder")
    print("2. Run compression tests on them")
    print("3. Compare results with existing reports")
    print("4. Show what changed (especially VMAF fix)")
    print()
    
    # Find tmp files
    tmp_files = find_tmp_files()
    
    if not tmp_files:
        print("❌ No video files found in tmp/")
        return
    
    # Ask user which files to test
    print("\nAvailable files:")
    for i, f in enumerate(tmp_files, 1):
        existing_report = find_existing_report(f)
        has_report = "✅ (has report)" if existing_report else "❌ (no report)"
        print(f"   {i}. {f.name} {has_report}")
    
    print(f"\n   {len(tmp_files) + 1}. Test all files")
    
    choice = input("\nSelect file number (or 'all' for all): ").strip().lower()
    
    files_to_test = []
    if choice == 'all' or choice == str(len(tmp_files) + 1):
        files_to_test = tmp_files
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tmp_files):
                files_to_test = [tmp_files[idx]]
            else:
                print("❌ Invalid selection")
                return
        except ValueError:
            print("❌ Invalid input")
            return
    
    print(f"\n📋 Testing {len(files_to_test)} file(s)...")
    
    # Test each file
    for video_file in files_to_test:
        # Find existing report
        existing_report_path = find_existing_report(video_file)
        old_report = None
        if existing_report_path:
            print(f"\n📄 Found existing report: {existing_report_path.name}")
            old_report = load_report(existing_report_path)
        
        # Run compression test
        new_report = run_compression_test(
            video_file,
            target_vmaf=85.0,
            target_codec='av1',
            codec_mode='VBR',
            target_bitrate=20.0
        )
        
        # Compare reports
        if old_report or new_report:
            compare_reports(old_report, new_report, video_file.name)
        
        print("\n" + "="*80)
        input("Press Enter to continue to next file (or Ctrl+C to stop)...")
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    main()


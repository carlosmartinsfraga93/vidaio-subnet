#!/usr/bin/env python3
"""
Quick test to verify VMAF fix is working.
Tests one file from tmp folder and shows if VMAF is calculated.
"""
import os
import sys
import json
from pathlib import Path

def main():
    print("="*80)
    print("QUICK VMAF FIX TEST")
    print("="*80)
    print("\nThis will test if VMAF calculation is now working.\n")
    
    # Find tmp files
    tmp_dir = Path("tmp")
    if not tmp_dir.exists():
        print("❌ tmp/ directory not found")
        return
    
    video_files = list(tmp_dir.glob("*.mp4"))
    if not video_files:
        print("❌ No video files found in tmp/")
        return
    
    # Use first file
    test_file = video_files[0]
    print(f"📁 Testing with: {test_file.name}\n")
    
    # Run compression
    print("Running compression test...")
    print("(This may take a few minutes)\n")
    
    cmd = [
        sys.executable, "test_local_compression.py",
        str(test_file),
        "--vmaf", "85.0",
        "--codec", "av1",
        "--mode", "VBR",
        "--bitrate", "20.0"
    ]
    
    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    
    # Check for report
    video_name = test_file.stem
    output_dir = Path("output")
    reports = sorted(
        output_dir.glob(f"{video_name}*_encoding_report.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if reports:
        latest_report = reports[0]
        print(f"\n{'='*80}")
        print("VMAF TEST RESULT")
        print(f"{'='*80}\n")
        
        try:
            with open(latest_report, 'r') as f:
                report = json.load(f)
            
            final_vmaf = report.get('quality_metrics', {}).get('final_vmaf_score')
            vmaf_time = report.get('quality_metrics', {}).get('vmaf_calculation_time', 0)
            
            print(f"Report: {latest_report.name}\n")
            
            if final_vmaf is not None:
                print("✅ SUCCESS! VMAF is being calculated!")
                print(f"   VMAF Score: {final_vmaf:.2f}")
                print(f"   Calculation Time: {vmaf_time:.2f}s")
                print("\n✅ The fix is working! VMAF calculation is functional.")
            else:
                print("❌ FAILED! VMAF is still NULL")
                print(f"   Calculation Time: {vmaf_time:.2f}s")
                print("\n❌ The fix may not be working. Check for errors above.")
            
            # Show scene VMAF too
            part4 = report.get('comprehensive_training_data', {}).get('pipeline_stages_data', {}).get('part4_vmaf_calculation', [])
            if part4:
                scene_vmaf = part4[0].get('actual_vmaf')
                scene_status = part4[0].get('vmaf_calculation_status')
                print(f"\nScene VMAF: {scene_vmaf if scene_vmaf is not None else 'NULL'}")
                print(f"Scene Status: {scene_status}")
            
        except Exception as e:
            print(f"❌ Error reading report: {e}")
    else:
        print("\n❌ No report generated")

if __name__ == "__main__":
    main()


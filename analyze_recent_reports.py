#!/usr/bin/env python3
"""
Analyze recent encoding reports to identify issues.
"""
import json
import os
from pathlib import Path
from datetime import datetime

def analyze_report(report_path):
    """Analyze a single report file."""
    with open(report_path, 'r') as f:
        data = json.load(f)
    
    summary = data.get('processing_summary', {})
    quality = data.get('quality_metrics', {})
    compression = data.get('compression_metrics', {})
    encoding_data = data.get('comprehensive_training_data', {}).get('pipeline_stages_data', {})
    ai_encoding = encoding_data.get('part3_ai_encoding', [{}])[0] if encoding_data.get('part3_ai_encoding') else {}
    
    issues = []
    
    # Check VMAF
    final_vmaf = quality.get('final_vmaf_score')
    if final_vmaf is None:
        issues.append("❌ VMAF is NULL - not calculated")
    elif final_vmaf < 85:
        issues.append(f"⚠️ VMAF too low: {final_vmaf:.2f} (target: 85+)")
    
    # Check compression
    size_ratio = compression.get('size_ratio', 1.0)
    if size_ratio > 1.0:
        issues.append(f"❌ FILE GOT LARGER: {size_ratio:.3f}x (output > input)")
    elif size_ratio > 0.8:
        issues.append(f"⚠️ Poor compression: {size_ratio:.3f}x (target: <0.2 for 5x+)")
    elif size_ratio < 0.2:
        issues.append(f"✅ Good compression: {size_ratio:.3f}x ({1/size_ratio:.1f}x compression)")
    
    # Check CQ
    final_cq = ai_encoding.get('final_adjusted_cq')
    optimal_cq = ai_encoding.get('optimal_cq')
    scene_type = ai_encoding.get('scene_type', 'unknown')
    
    # Check encoding success
    encoding_success = ai_encoding.get('encoding_success', False)
    if not encoding_success:
        issues.append("❌ Encoding failed")
    
    return {
        'timestamp': summary.get('timestamp', 'unknown'),
        'codec': summary.get('final_video_path', '').split('_')[-2] if '_' in summary.get('final_video_path', '') else 'unknown',
        'target_vmaf': quality.get('target_vmaf', 0),
        'final_vmaf': final_vmaf,
        'size_ratio': size_ratio,
        'compression_ratio': 1/size_ratio if size_ratio > 0 else 0,
        'scene_type': scene_type,
        'optimal_cq': optimal_cq,
        'final_cq': final_cq,
        'issues': issues,
        'encoding_success': encoding_success
    }

def main():
    output_dir = Path("output")
    reports = sorted(output_dir.glob("*_encoding_report.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]
    
    print("=" * 80)
    print("RECENT ENCODING REPORTS ANALYSIS")
    print("=" * 80)
    print(f"\nAnalyzing {len(reports)} most recent reports...\n")
    
    all_issues = {
        'vmaf_null': 0,
        'vmaf_low': 0,
        'file_larger': 0,
        'poor_compression': 0,
        'good_compression': 0,
        'encoding_failed': 0
    }
    
    for i, report_path in enumerate(reports, 1):
        print(f"\n{'='*80}")
        print(f"Report {i}: {report_path.name}")
        print(f"{'='*80}")
        
        try:
            result = analyze_report(report_path)
            
            print(f"Timestamp: {result['timestamp']}")
            print(f"Codec: {result['codec']}")
            print(f"Scene Type: {result['scene_type']}")
            print(f"Target VMAF: {result['target_vmaf']}")
            print(f"Final VMAF: {result['final_vmaf'] if result['final_vmaf'] is not None else 'NULL'}")
            print(f"Size Ratio: {result['size_ratio']:.4f} ({result['compression_ratio']:.2f}x compression)")
            print(f"CQ: {result['optimal_cq']} → {result['final_cq']}")
            print(f"Encoding Success: {result['encoding_success']}")
            
            if result['issues']:
                print("\nIssues Found:")
                for issue in result['issues']:
                    print(f"  {issue}")
                    
                    # Count issues
                    if "VMAF is NULL" in issue:
                        all_issues['vmaf_null'] += 1
                    elif "VMAF too low" in issue:
                        all_issues['vmaf_low'] += 1
                    elif "FILE GOT LARGER" in issue:
                        all_issues['file_larger'] += 1
                    elif "Poor compression" in issue:
                        all_issues['poor_compression'] += 1
                    elif "Good compression" in issue:
                        all_issues['good_compression'] += 1
                    elif "Encoding failed" in issue:
                        all_issues['encoding_failed'] += 1
            else:
                print("\n✅ No issues found!")
                
        except Exception as e:
            print(f"❌ Error analyzing report: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Reports with NULL VMAF: {all_issues['vmaf_null']}/{len(reports)}")
    print(f"Reports with low VMAF: {all_issues['vmaf_low']}/{len(reports)}")
    print(f"Reports where file got LARGER: {all_issues['file_larger']}/{len(reports)}")
    print(f"Reports with poor compression: {all_issues['poor_compression']}/{len(reports)}")
    print(f"Reports with good compression: {all_issues['good_compression']}/{len(reports)}")
    print(f"Reports with encoding failures: {all_issues['encoding_failed']}/{len(reports)}")
    
    # Critical issues
    print("\n" + "=" * 80)
    print("CRITICAL ISSUES")
    print("=" * 80)
    if all_issues['vmaf_null'] > 0:
        print(f"❌ CRITICAL: {all_issues['vmaf_null']} reports have NULL VMAF")
        print("   → Validators cannot score without VMAF!")
        print("   → This will cause miner to score 0 and potentially deregister!")
    
    if all_issues['file_larger'] > 0:
        print(f"❌ CRITICAL: {all_issues['file_larger']} reports show files getting LARGER")
        print("   → Compression is failing!")
        print("   → This will cause very low scores!")
    
    if all_issues['poor_compression'] > 0:
        print(f"⚠️  WARNING: {all_issues['poor_compression']} reports have poor compression (<5x)")
        print("   → Need to increase CQ values further")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()


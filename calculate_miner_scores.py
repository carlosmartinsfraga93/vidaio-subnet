#!/usr/bin/env python3
"""
Calculate expected miner scores and incentives based on test results.
"""

import math

def calculate_compression_score(
    vmaf_score: float,
    compression_ratio: float,  # e.g., 7.53 for 7.53x compression
    vmaf_threshold: float,
    compression_weight: float = 0.70,
    quality_weight: float = 0.30,
    soft_threshold_margin: float = 5.0
):
    """
    Calculate compression score using the actual scoring function.
    
    Returns:
        Tuple of (final_score, compression_component, quality_component, reason)
    """
    compression_rate = 1 / compression_ratio  # Convert ratio to rate
    
    # CASE 0: No meaningful compression (>80% of original size)
    if compression_rate >= 0.80:
        return 0.0, 0.0, 0.0, "No meaningful compression"
    
    hard_cutoff = vmaf_threshold - soft_threshold_margin
    
    # CASE 1: Below hard cutoff
    if vmaf_score < hard_cutoff:
        return 0.0, 0.0, 0.0, f"VMAF below hard cutoff ({hard_cutoff})"
    
    # CASE 2: Soft zone (between hard cutoff and threshold)
    if vmaf_score < vmaf_threshold:
        # Quality factor: linear interpolation from 0 to 1
        quality_factor = (vmaf_score - hard_cutoff) / soft_threshold_margin
        
        # Compression component
        if compression_ratio <= 20:
            compression_component = ((compression_ratio - 1) / 19) ** 1.5
        else:
            compression_component = 1.0 + 0.3 * math.log(compression_ratio / 20)
        
        compression_component = min(1.3, compression_component)
        final_score = compression_component * quality_factor
        
        return min(1.0, final_score), compression_component, quality_factor, f"VMAF in soft zone"
    
    # CASE 3: Above threshold (full scoring)
    vmaf_excess = vmaf_score - vmaf_threshold
    max_vmaf_excess = 100 - vmaf_threshold
    quality_component = 0.7 + 0.3 * min(1.0, vmaf_excess / max_vmaf_excess)
    
    # Compression component
    if compression_ratio <= 20:
        compression_component = ((compression_ratio - 1.25) / 18.75) ** 1.2 + 0.025
    else:
        compression_component = 1.0 + 0.3 * math.log(compression_ratio / 20)
    
    compression_component = min(1.3, compression_component)
    
    # Weighted combination: 70% compression + 30% quality
    final_score = (compression_weight * compression_component + 
                  quality_weight * quality_component)
    
    return min(1.0, final_score), compression_component, quality_component, "Above threshold"


# Test results from comparison
test_results = [
    {
        'name': 'Test 1 (AV1, VMAF 85)',
        'vmaf': 97.66,
        'compression_ratio': 5.56,
        'threshold': 85.0
    },
    {
        'name': 'Test 2 (AV1, VMAF 89)',
        'vmaf': 98.02,
        'compression_ratio': 7.42,
        'threshold': 89.0
    },
    {
        'name': 'Test 3 (AV1, VMAF 85)',
        'vmaf': 98.04,
        'compression_ratio': 6.37,
        'threshold': 85.0
    }
]

print("=" * 100)
print("🎯 MINER SCORE CALCULATION - TEST RESULTS")
print("=" * 100)
print()

total_score = 0
for i, result in enumerate(test_results, 1):
    score, comp_comp, qual_comp, reason = calculate_compression_score(
        vmaf_score=result['vmaf'],
        compression_ratio=result['compression_ratio'],
        vmaf_threshold=result['threshold']
    )
    
    total_score += score
    
    print(f"📊 {result['name']}")
    print(f"   VMAF: {result['vmaf']:.2f} (threshold: {result['threshold']:.1f})")
    print(f"   Compression: {result['compression_ratio']:.2f}x")
    print(f"   ├─ Compression Component: {comp_comp:.4f}")
    print(f"   ├─ Quality Component: {qual_comp:.4f}")
    print(f"   └─ Final Score (S_f): {score:.4f}")
    print(f"   Status: {reason}")
    print()

avg_score = total_score / len(test_results)

print("=" * 100)
print(f"📈 AVERAGE SCORE: {avg_score:.4f}")
print("=" * 100)
print()

# Performance tier analysis
print("🏆 PERFORMANCE TIER ANALYSIS")
print("-" * 100)
if avg_score > 0.74:
    print(f"   ✅ EXCELLENT - Qualifies for BONUS (+15% max)")
    print(f"   └─ Score > 0.74 threshold")
elif avg_score > 0.40:
    print(f"   ✅ GOOD - No penalties")
    print(f"   └─ Score between 0.40 and 0.74")
else:
    print(f"   ⚠️ NEEDS IMPROVEMENT - May incur penalties")
    print(f"   └─ Score < 0.40 threshold")
print()

# Incentive estimation
print("💰 ESTIMATED INCENTIVE (per round)")
print("-" * 100)
print(f"   Base Score (S_f): {avg_score:.4f}")
print(f"   Assuming consistent performance over 10 rounds:")
print()

if avg_score > 0.74:
    bonus_count = 10  # All rounds qualify
    bonus_multiplier = 1.0 + (bonus_count / 10) * 0.15
    adjusted_score = avg_score * bonus_multiplier
    print(f"   ✅ Bonus Multiplier: {bonus_multiplier:.4f}x (+{(bonus_multiplier-1)*100:.1f}%)")
    print(f"   ✅ Adjusted Score: {adjusted_score:.4f}")
else:
    print(f"   No bonus (score < 0.74)")
    adjusted_score = avg_score

print()
print(f"   📊 Final Adjusted Score: {adjusted_score:.4f}")
print()

print("=" * 100)
print("📝 NOTES")
print("=" * 100)
print("• Scores are normalized to [0, 1.0] range")
print("• Compression weight: 70%, Quality weight: 30%")
print("• Bonus system: +15% max for consistent S_f > 0.74 (10/10 rounds)")
print("• Penalty system: -20% max for S_f < 0.40, -30% max for VMAF issues")
print("• Actual incentive depends on network emissions and validator scoring")
print("=" * 100)


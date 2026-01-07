"""
Unit tests for Optimal Bitrate Controller (Scene-Aware)
========================================================

Validates the scene-aware score-maximizing formula implementation.
"""

import unittest
from optimal_bitrate_controller import (
    clamp,
    calculate_complexity_score,
    normalize_original_bitrate,
    normalize_scene_type,
    calculate_target_ratio,
    calculate_minimum_bitrate,
    calculate_target_bitrate,
    calculate_initial_cq,
    update_cq_after_encode,
    update_vbr_bitrate_after_encode,
    calculate_vbr_settings,
    should_apply_vbr_ceiling
)


class TestBasicFunctions(unittest.TestCase):
    """Test basic utility functions."""
    
    def test_clamp(self):
        """Test clamp function."""
        self.assertEqual(clamp(0, -5, 10), 0)
        self.assertEqual(clamp(0, 5, 10), 5)
        self.assertEqual(clamp(0, 15, 10), 10)
    
    def test_complexity_score(self):
        """Test complexity score calculation."""
        # Easy content
        c = calculate_complexity_score(grain=0.05, texture=0.05, motion=0.02)
        self.assertAlmostEqual(c, 0.44, places=2)
        
        # Hard content
        c = calculate_complexity_score(grain=0.12, texture=0.12, motion=0.08)
        self.assertAlmostEqual(c, 1.696, places=2)


class TestBitrateCalculations(unittest.TestCase):
    """Test bitrate-related calculations."""
    
    def test_normalize_bitrate_basic(self):
        """Test basic bitrate normalization."""
        # Within range
        self.assertEqual(normalize_original_bitrate(30, 6.0, use_floor=False), 30)
        
        # Below minimum
        self.assertEqual(normalize_original_bitrate(10, 6.0, use_floor=False), 20)
        
        # Above maximum
        self.assertEqual(normalize_original_bitrate(100, 6.0, use_floor=False), 65)
    
    def test_normalize_bitrate_with_floor(self):
        """Test bitrate normalization with content floor."""
        # High complexity should raise floor
        b_norm = normalize_original_bitrate(25, 8.0, use_floor=True)
        self.assertGreater(b_norm, 25)
    
    def test_target_ratio_easy_content(self):
        """Test target ratio for easy content."""
        # C ≤ 6.6 should give ~20x
        ratio = calculate_target_ratio(complexity=6.0)
        self.assertAlmostEqual(ratio, 20.0, places=1)
    
    def test_target_ratio_hard_content(self):
        """Test target ratio for hard content."""
        # C > 6.6 should reduce ratio
        ratio = calculate_target_ratio(complexity=8.0)
        self.assertLess(ratio, 20.0)
        self.assertGreaterEqual(ratio, 15.0)
    
    def test_minimum_bitrate_av1(self):
        """Test minimum bitrate calculation for AV1."""
        b_min = calculate_minimum_bitrate(
            complexity=6.5,
            motion=0.05,
            codec='av1',
            vmaf_threshold=89,
            mode='CRF'
        )
        self.assertGreater(b_min, 0.8)
        self.assertLess(b_min, 10.0)
    
    def test_minimum_bitrate_hevc(self):
        """Test minimum bitrate calculation for HEVC."""
        b_min = calculate_minimum_bitrate(
            complexity=6.5,
            motion=0.05,
            codec='hevc',
            vmaf_threshold=85,
            mode='VBR'
        )
        self.assertGreater(b_min, 0.8)
        self.assertLess(b_min, 10.0)
    
    def test_target_bitrate_calculation(self):
        """Test complete target bitrate calculation."""
        b_target, r_target, b_min = calculate_target_bitrate(
            bitrate_orig=30.0,
            complexity=6.5,
            motion=0.05,
            codec='av1',
            vmaf_threshold=89,
            mode='CRF',
            grain=0.05,
            texture=0.05
        )
        
        # Should aim for high ratio
        self.assertGreaterEqual(r_target, 15.0)
        self.assertLessEqual(r_target, 20.0)
        
        # Target bitrate should respect minimum
        self.assertGreaterEqual(b_target, b_min * 1.05)


class TestCRFMode(unittest.TestCase):
    """Test CRF mode functions."""
    
    def test_initial_cq_av1(self):
        """Test initial CQ calculation for AV1."""
        # Easy content
        cq = calculate_initial_cq(complexity=6.0, codec='av1')
        self.assertGreaterEqual(cq, 20)
        self.assertLessEqual(cq, 38)
        
        # Hard content
        cq_hard = calculate_initial_cq(complexity=8.0, codec='av1')
        self.assertGreater(cq_hard, cq)  # Higher complexity = higher CQ
    
    def test_initial_cq_hevc(self):
        """Test initial CQ calculation for HEVC."""
        cq = calculate_initial_cq(complexity=6.0, codec='hevc')
        self.assertGreaterEqual(cq, 18)
        self.assertLessEqual(cq, 34)
    
    def test_cq_update_emergency(self):
        """Test CQ update in emergency (VMAF below threshold)."""
        new_cq = update_cq_after_encode(
            current_cq=30,
            vmaf_score=87.0,  # Below threshold
            vmaf_threshold=89.0,
            ratio_actual=15.0,
            ratio_target=18.0,
            mode='CRF',
            codec='av1'
        )
        self.assertEqual(new_cq, 26)  # Should decrease by 4
    
    def test_cq_update_push_compression(self):
        """Test CQ update when pushing for more compression."""
        new_cq = update_cq_after_encode(
            current_cq=30,
            vmaf_score=92.0,  # Safe margin
            vmaf_threshold=89.0,
            ratio_actual=12.0,  # Below target
            ratio_target=18.0,
            mode='CRF',
            codec='av1'
        )
        self.assertEqual(new_cq, 32)  # Should increase by 2
    
    def test_cq_update_keep_squeezing(self):
        """Test CQ update when at target with high margin."""
        new_cq = update_cq_after_encode(
            current_cq=30,
            vmaf_score=95.0,  # High margin (95 - 89 = 6)
            vmaf_threshold=89.0,
            ratio_actual=18.0,  # At target
            ratio_target=18.0,
            mode='CRF',
            codec='av1'
        )
        self.assertEqual(new_cq, 31)  # Should increase by 1
    
    def test_vbr_ceiling_trigger(self):
        """Test VBR ceiling guard trigger."""
        # Should trigger: bitrate too high, safe margin
        should_apply = should_apply_vbr_ceiling(
            bitrate_actual=5.0,
            bitrate_target=3.0,
            vmaf_score=92.0,
            vmaf_threshold=89.0,
            mode='CRF'
        )
        self.assertTrue(should_apply)
        
        # Should not trigger: bitrate OK
        should_apply = should_apply_vbr_ceiling(
            bitrate_actual=3.0,
            bitrate_target=3.0,
            vmaf_score=92.0,
            vmaf_threshold=89.0,
            mode='CRF'
        )
        self.assertFalse(should_apply)


class TestVBRMode(unittest.TestCase):
    """Test VBR mode functions."""
    
    def test_vbr_settings(self):
        """Test VBR settings calculation."""
        settings = calculate_vbr_settings(target_bitrate=3.0)
        
        self.assertEqual(settings['b:v'], 3.0)
        self.assertAlmostEqual(settings['maxrate'], 3.15, places=2)
        self.assertAlmostEqual(settings['bufsize'], 7.5, places=2)
    
    def test_vbr_update_emergency(self):
        """Test VBR update in emergency."""
        new_bitrate, new_ratio = update_vbr_bitrate_after_encode(
            current_bitrate=3.0,
            vmaf_score=87.0,  # Below threshold
            vmaf_threshold=89.0,
            ratio_actual=15.0,
            ratio_target=18.0
        )
        
        self.assertAlmostEqual(new_bitrate, 4.05, places=2)  # 3.0 * 1.35
        self.assertEqual(new_ratio, 16.0)  # max(15, 18 - 2)
    
    def test_vbr_update_caution(self):
        """Test VBR update in caution zone."""
        new_bitrate, new_ratio = update_vbr_bitrate_after_encode(
            current_bitrate=3.0,
            vmaf_score=89.5,  # Just above threshold
            vmaf_threshold=89.0,
            ratio_actual=15.0,
            ratio_target=18.0
        )
        
        self.assertAlmostEqual(new_bitrate, 3.45, places=2)  # 3.0 * 1.15
        self.assertEqual(new_ratio, 17.0)  # max(15, 18 - 1)
    
    def test_vbr_update_squeeze(self):
        """Test VBR update when squeezing more."""
        new_bitrate, new_ratio = update_vbr_bitrate_after_encode(
            current_bitrate=3.0,
            vmaf_score=96.0,  # High margin (96 - 89 = 7)
            vmaf_threshold=89.0,
            ratio_actual=18.0,
            ratio_target=18.0
        )
        
        self.assertAlmostEqual(new_bitrate, 2.76, places=2)  # 3.0 * 0.92
        self.assertEqual(new_ratio, 18.0)  # Keep


if __name__ == '__main__':
    unittest.main(verbosity=2)


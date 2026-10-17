"""
Unit tests for luminance analysis and Auto-Contrast visual protection.
"""

import unittest
from PIL import Image
from comic_bubble.contrast import get_luminance, analyze_background_and_adjust

class TestContrast(unittest.TestCase):

    def test_get_luminance(self):
        # Pure white -> 255.0
        self.assertAlmostEqual(get_luminance((255, 255, 255)), 255.0, places=1)
        # Pure black -> 0.0
        self.assertAlmostEqual(get_luminance((0, 0, 0)), 0.0, places=1)
        # Green has highest contribution
        self.assertGreater(get_luminance((0, 255, 0)), get_luminance((255, 0, 0)))
        self.assertGreater(get_luminance((255, 0, 0)), get_luminance((0, 0, 255)))

    def test_dark_background_boost(self):
        # Create dark night background (RGB 40, 40, 50)
        img = Image.new("RGB", (200, 200), (40, 40, 50))
        # Dark text (RGB 35, 35, 45) -> dangerously low contrast!
        text_color = (35, 35, 45, 255)
        rect = (20, 20, 180, 180)

        alpha, halo = analyze_background_and_adjust(
            img, rect, text_color, specified_alpha=0.20, mode="auto"
        )
        # Should automatically boost alpha to >= 0.80 and enable halo
        self.assertGreaterEqual(alpha, 0.80)
        self.assertTrue(halo)

    def test_bright_background_preserves_alpha(self):
        # Create bright sunset background (RGB 250, 240, 230)
        img = Image.new("RGB", (200, 200), (250, 240, 230))
        # Dark text -> high contrast
        text_color = (35, 35, 45, 255)
        rect = (20, 20, 180, 180)

        alpha, halo = analyze_background_and_adjust(
            img, rect, text_color, specified_alpha=0.20, mode="auto"
        )
        self.assertAlmostEqual(alpha, 0.20, places=2)
        self.assertFalse(halo)

if __name__ == "__main__":
    unittest.main()

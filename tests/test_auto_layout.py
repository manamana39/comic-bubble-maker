"""
Unit tests for automatic negative-space background placement.
"""

import unittest
from PIL import Image
from comic_bubble.auto_layout import find_safe_background_center

class TestAutoLayout(unittest.TestCase):

    def test_find_safe_background_center(self):
        # Create an image where center has a busy pattern (character face simulation)
        # and top-left is completely uniform sky (empty negative space)
        img = Image.new("RGB", (400, 400), (80, 140, 220))  # blue sky background
        # Add high-contrast noise in center
        import numpy as np
        arr = np.array(img)
        # Busy center
        arr[150:280, 150:280] = np.random.randint(0, 255, (130, 130, 3), dtype=np.uint8)
        test_img = Image.fromarray(arr)

        cx, cy = find_safe_background_center(test_img, 80, 100)
        # Optimal center should be outside the noisy center region
        self.assertTrue(0.0 <= cx <= 1.0)
        self.assertTrue(0.0 <= cy <= 1.0)
        # It should avoid the center box [0.375..0.70]
        is_outside_busy = (cx < 0.35 or cx > 0.70 or cy < 0.35 or cy > 0.70)
        self.assertTrue(is_outside_busy)

if __name__ == "__main__":
    unittest.main()

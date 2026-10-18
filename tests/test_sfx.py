"""
Unit tests for manga onomatopoeia / SFX rendering.
"""

import unittest
from PIL import Image
from comic_bubble.models import BubbleConfig, SceneConfig
from comic_bubble.engine import render_scene

class TestSFX(unittest.TestCase):

    def test_sfx_rendering(self):
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        img_path = "output/test_sfx_in.png"
        img.save(img_path)

        sfx = BubbleConfig(
            text="ドキッ",
            type="sfx",
            font="bold",
            center=(0.5, 0.5),
            angle=-15.0,
            font_size_ratio=0.15,
            text_color=(200, 30, 30, 255),
            stroke_width=3.0,
            stroke_color=(255, 255, 255, 255)
        )
        scene = SceneConfig(
            image_path=img_path,
            bubbles=[sfx],
            supersample_scale=2
        )
        result = render_scene(scene)
        self.assertEqual(result.size, (200, 200))
        # Center region should contain non-white pixels (the text)
        center_pixel = result.getpixel((100, 100))
        # Text is red or stroke, so it shouldn't be untouched white
        # Check that some text was rendered
        import numpy as np
        arr = np.array(result)
        colored_pixels = np.sum(arr[:, :, 0] < 240)
        self.assertGreater(colored_pixels, 50)

    def test_sfx_presets_structure(self):
        from gui.sfx_palette import SFX_PRESETS
        self.assertIn("💖 恋愛・胸キュン", SFX_PRESETS)
        self.assertIn("🔞 艶音・吐息 (NSFW)", SFX_PRESETS)
        self.assertGreater(len(SFX_PRESETS["💖 恋愛・胸キュン"]), 3)
        for cat, items in SFX_PRESETS.items():
            for item in items:
                self.assertIn("text", item)
                self.assertIn("font", item)
                self.assertIn("angle", item)

    def test_detect_white_bubble_patch(self):
        from comic_bubble.ai_generator import detect_white_bubble_patch
        # 1. Pure white patch (like an empty speech bubble)
        white_img = Image.new("RGB", (300, 300), (255, 255, 255))
        self.assertTrue(detect_white_bubble_patch(white_img, 0.5, 0.5))

        # 2. Dark/textured patch (not an empty speech bubble)
        dark_img = Image.new("RGB", (300, 300), (50, 60, 70))
        self.assertFalse(detect_white_bubble_patch(dark_img, 0.5, 0.5))

if __name__ == "__main__":
    unittest.main()

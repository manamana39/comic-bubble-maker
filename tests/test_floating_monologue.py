"""
Unit tests for borderless floating monologue mode.
Verifies that no bubble polygon or background frame is drawn for monologues.
"""

import unittest
from PIL import Image
from comic_bubble.models import BubbleConfig, SceneConfig
from comic_bubble.engine import render_scene

class TestFloatingMonologue(unittest.TestCase):

    def test_monologue_renders_without_bubble_plate(self):
        # Create an all-blue canvas (RGB 50, 100, 200)
        img = Image.new("RGB", (300, 300), (50, 100, 200))
        img_path = "output/test_canvas.png"
        img.save(img_path)

        monologue = BubbleConfig(
            text="（…心の声）",
            type="monologue",  # Should map to floating
            font="mincho",
            center=(0.5, 0.5),
            text_color=(255, 255, 255, 255),
            bg_color=(255, 0, 0),  # Bright red if filled!
            text_halo=True
        )

        scene = SceneConfig(
            image_path=img_path,
            bubbles=[monologue],
            output_path="output/test_monologue_out.png",
            supersample_scale=2
        )
        result = render_scene(scene)

        # Inspect corner pixels outside text: they MUST NOT be filled with bg_color (red)
        # Because floating monologue draws ZERO bubble plate!
        top_left_pixel = result.getpixel((10, 10))
        self.assertEqual(top_left_pixel, (50, 100, 200))

        # Check a pixel near the text area: it should either be blue or text/halo, but NEVER pure red bubble plate
        for x in range(50, 250, 10):
            for y in range(50, 250, 10):
                px = result.getpixel((x, y))
                # Ensure it's not the red bg_color (255, 0, 0)
                self.assertNotEqual(px, (255, 0, 0))

    def test_monologue_type_alias(self):
        cfg = BubbleConfig.from_dict({"text": "独白", "type": "monologue"})
        self.assertEqual(cfg.type, "floating")
        self.assertEqual(cfg.font, "mincho")

if __name__ == "__main__":
    unittest.main()

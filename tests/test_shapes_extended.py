"""
Unit tests for extended shapes: scream (spiky explosion) and dashed (whisper).
"""

import unittest
from PIL import Image, ImageDraw
from comic_bubble.shapes import generate_scream_polygon, draw_dashed_polygon

class TestShapesExtended(unittest.TestCase):

    def test_scream_polygon_generation(self):
        rect = (50, 50, 250, 250)
        tail = (300, 300)
        poly = generate_scream_polygon(rect, tail=tail, num_spikes=16)
        self.assertEqual(len(poly), 32)
        # Verify that the tail coordinate is integrated as a spike
        has_tail = any(pt[0] == 300.0 and pt[1] == 300.0 for pt in poly)
        self.assertTrue(has_tail)

    def test_draw_dashed_polygon(self):
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        points = [(10, 10), (90, 10), (90, 90), (10, 90)]
        draw_dashed_polygon(draw, points, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=2)
        # Should render pixels without raising exceptions
        self.assertGreater(img.getpixel((50, 50))[3], 0)

if __name__ == "__main__":
    unittest.main()

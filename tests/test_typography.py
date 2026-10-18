"""
Unit tests for typography and vertical layout engine.
"""

import unittest
from PIL import Image, ImageDraw
from comic_bubble.typography import (
    parse_styled_text,
    measure_vertical_styled_text,
    VERTICAL_REPLACEMENTS
)

class TestTypography(unittest.TestCase):

    def test_parse_styled_text_tags(self):
        text = "<big>こんにちは</big>\n<small>世界</small>"
        parsed = parse_styled_text(text)
        self.assertEqual(len(parsed), 2)
        # Line 1: 5 chars at scale 1.3
        self.assertEqual(len(parsed[0]), 5)
        for ch, sc in parsed[0]:
            self.assertAlmostEqual(sc, 1.30, places=2)
        # Line 2: 2 chars at scale 0.72
        self.assertEqual(len(parsed[1]), 2)
        for ch, sc in parsed[1]:
            self.assertAlmostEqual(sc, 0.72, places=2)

    def test_vertical_replacements(self):
        self.assertEqual(VERTICAL_REPLACEMENTS["ー"], "丨")
        self.assertEqual(VERTICAL_REPLACEMENTS["「"], "﹁")
        self.assertEqual(VERTICAL_REPLACEMENTS["」"], "﹂")

    def test_measure_vertical_text(self):
        img = Image.new("RGBA", (500, 500))
        draw = ImageDraw.Draw(img)
        text = "（…似合ってる\n　なんて言える\n　わけないだろ）"
        styled = parse_styled_text(text)
        tw, th, cws, chs, metrics = measure_vertical_styled_text(draw, styled, 30, "mincho")

        self.assertGreater(tw, 0)
        self.assertGreater(th, 0)
        self.assertEqual(len(cws), 3)
        self.assertEqual(len(chs), 3)
        self.assertEqual(len(metrics), 3)

        # Advance should be positive for all characters
        for col in metrics:
            for ch, sc, f, cur_sz, bbox, ink_w, ink_h, adv in col:
                self.assertGreater(adv, 0)

    def test_auto_wrap_japanese_text(self):
        from comic_bubble.typography import auto_wrap_japanese_text
        long_s1 = "それよりこっち！ステンドグラスの向こう側も見てごらんよ"
        wrapped1 = auto_wrap_japanese_text(long_s1)
        lines1 = wrapped1.split("\n")
        self.assertGreaterEqual(len(lines1), 2)
        # Verify kinsoku: no line starts with small kana or punctuation
        for l in lines1:
            self.assertFalse(l.startswith("！"))
            self.assertFalse(l.startswith("っ"))

        long_s2 = "あ、あの…最近図書館の新しい小説が面白いって噂だったんだ"
        wrapped2 = auto_wrap_japanese_text(long_s2)
        lines2 = wrapped2.split("\n")
        self.assertGreaterEqual(len(lines2), 3)

        # Short text should remain unchanged
        short_s = "はい、どうぞ！"
        self.assertEqual(auto_wrap_japanese_text(short_s), short_s)

if __name__ == "__main__":
    unittest.main()

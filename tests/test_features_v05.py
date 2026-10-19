"""
tests.test_features_v05
~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for new v0.5 features:
1. Reading direction (RTL / LTR) in typography and Inspector
2. Multi-language (i18n) switching between Japanese and English
3. Save confirmation flow (confirm_save_if_modified)
"""

import os
import unittest
from PIL import Image
from PySide6.QtWidgets import QApplication

from comic_bubble.models import BubbleConfig, SceneConfig
from comic_bubble.engine import render_scene
from gui.main_window import MainWindow
from gui.i18n import get_current_language, set_current_language, tr


class TestFeaturesV05(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def tearDown(self):
        # Always restore default language to ja
        set_current_language("ja")

    def test_reading_direction_models_and_render(self):
        """Test reading_direction config parameter and multi-line vertical rendering."""
        b_rtl = BubbleConfig(text="1行目\n2行目", reading_direction="rtl")
        self.assertEqual(b_rtl.reading_direction, "rtl")

        b_ltr = BubbleConfig(text="1行目\n2行目", reading_direction="ltr")
        self.assertEqual(b_ltr.reading_direction, "ltr")

        # Serialized dict test
        d_ltr = b_ltr.to_dict()
        self.assertEqual(d_ltr["reading_direction"], "ltr")
        restored = BubbleConfig.from_dict(d_ltr)
        self.assertEqual(restored.reading_direction, "ltr")

        # Render test
        bg = Image.new("RGB", (300, 300), (255, 255, 255))
        scene = SceneConfig(image_path=bg, bubbles=[b_rtl, b_ltr], supersample_scale=2)
        rendered = render_scene(scene)
        self.assertEqual(rendered.size, (300, 300))

    def test_i18n_language_switching(self):
        """Test runtime dynamic switching between Japanese and English."""
        set_current_language("ja")
        self.assertEqual(get_current_language(), "ja")
        self.assertEqual(tr("日本語", "English"), "日本語")

        set_current_language("en")
        self.assertEqual(get_current_language(), "en")
        self.assertEqual(tr("日本語", "English"), "English")

        # MainWindow UI updates on language switch
        win = MainWindow()
        set_current_language("en")
        self.assertIn("Comic Bubble Maker", win.windowTitle())
        self.assertEqual(win.menu_file.title(), "File (&F)")
        self.assertEqual(win.inspector.grp_text.title(), "Dialogue Text")

        set_current_language("ja")
        self.assertEqual(win.menu_file.title(), "ファイル (&F)")
        self.assertEqual(win.inspector.grp_text.title(), "セリフ・テキスト")

    def test_confirm_save_if_modified_when_empty(self):
        """Test confirm_save_if_modified returns True without prompt when no bubbles exist."""
        win = MainWindow()
        self.assertEqual(len(win.canvas.bubble_items), 0)
        self.assertTrue(win.confirm_save_if_modified())


if __name__ == "__main__":
    unittest.main()

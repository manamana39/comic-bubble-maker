"""
Unit and integration tests for PySide6 Comic Bubble Maker GUI.
Runs headlessly via QT_QPA_PLATFORM=offscreen.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure offscreen Qt platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF
from gui.main_window import MainWindow
from comic_bubble.models import BubbleConfig, SceneConfig
from comic_bubble.engine import render_scene

class TestGuiApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_gui_initialization(self):
        """Test window instantiation and widget hierarchy."""
        win = MainWindow()
        self.assertIsNotNone(win)
        self.assertIsNotNone(win.canvas)
        self.assertIsNotNone(win.inspector)
        self.assertTrue(win.windowTitle().startswith("Comic Bubble Maker"))

    def test_gui_load_and_add_bubble(self):
        """Test loading an image, adding a bubble, moving tail, and exporting."""
        win = MainWindow()
        test_img = "input/test_01_infirmary.jpg"
        self.assertTrue(os.path.exists(test_img))

        # 1. Load image
        win.canvas.load_image(test_img)
        self.assertIsNotNone(win.canvas.base_pil_image)
        self.assertIsNotNone(win.canvas.bg_item)

        # 2. Add speech bubble
        item = win.canvas.add_bubble()
        self.assertIsNotNone(item)
        self.assertEqual(len(win.canvas.bubble_items), 1)
        self.assertTrue(item.isSelected())

        # 3. Modify text in inspector
        win.inspector.txt_edit.setPlainText("手動入力テスト！")
        self.assertEqual(item.config.text, "手動入力テスト！")

        # 4. Drag tail handle (orange circle)
        item.tail_handle.setPos(QPointF(80, 120))
        item.on_tail_handle_moved(QPointF(80, 120))
        self.assertIsNotNone(item.config.tail)

        # 4b. Test interactive resize handle drag
        old_size_ratio = item.config.font_size_ratio
        item.on_resize_font_size(0.035, is_final=True)
        self.assertEqual(item.config.font_size_ratio, 0.035)
        # Check that inspector slider synced
        self.assertEqual(win.inspector.slider_size.value(), 35)

        # 5. Add floating monologue
        win._add_monologue_bubble()
        self.assertEqual(len(win.canvas.bubble_items), 2)

        # 6. Add SFX onomatopoeia
        win._add_sfx_bubble()
        self.assertEqual(len(win.canvas.bubble_items), 3)

        # 7. Export test
        out_file = "output/gui_export_test.png"
        configs = win.canvas.get_all_bubble_configs()
        self.assertEqual(len(configs), 3)
        scene = SceneConfig(
            image_path=win.canvas.base_pil_image,
            bubbles=configs,
            supersample_scale=2
        )
        result = render_scene(scene)
        result.save(out_file)
        self.assertTrue(os.path.exists(out_file))
        self.assertGreater(os.path.getsize(out_file), 10000)
        print("GUI integration test passed successfully! Export size:", os.path.getsize(out_file))

if __name__ == "__main__":
    unittest.main()


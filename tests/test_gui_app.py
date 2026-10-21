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
        self.assertEqual(win.splitter.count(), 2)
        self.assertEqual(win.splitter.widget(0), win.canvas)
        self.assertEqual(win.splitter.widget(1), win.inspector)
        self.assertIn("Bubble Maker", win.windowTitle())

    def test_ai_json_parsing_with_nulls(self):
        """Test that _parse_bubbles_json handles null/None fields from Gemini schema without error."""
        from comic_bubble.ai_generator import _parse_bubbles_json, _clean_gemini_model_name
        self.assertEqual(_clean_gemini_model_name("gemini-1.5-flash"), "gemini-3.8-flash")
        self.assertEqual(_clean_gemini_model_name("gemini-3.8-flash (最新・推奨)"), "gemini-3.8-flash")
        sample = {
            "scene_description": "テストシーン",
            "bubbles": [
                {
                    "text": "セリフ",
                    "type": "capsule",
                    "center_x": 0.8,
                    "center_y": 0.2,
                    "has_tail": True,
                    "tail_x": 0.65,
                    "tail_y": 0.3,
                    "font": "kiwi",
                    "angle": None,
                }
            ]
        }
        desc, bubbles = _parse_bubbles_json(sample)
        self.assertEqual(desc, "テストシーン")
        self.assertEqual(len(bubbles), 1)
        self.assertEqual(bubbles[0].angle, 0.0)

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

    def test_dialogs_instantiation(self):
        """Test that AIDialogueDialog and SFXPaletteDialog instantiate without missing imports."""
        from PIL import Image
        from gui.ai_dialog import AIDialogueDialog
        from gui.sfx_palette import SFXPaletteDialog

        dummy_img = Image.new("RGB", (200, 200), (255, 255, 255))
        ai_dlg = AIDialogueDialog(dummy_img)
        self.assertIsNotNone(ai_dlg.chk_nsfw)
        self.assertIsNotNone(ai_dlg.chk_detect_existing)

        sfx_dlg = SFXPaletteDialog()
        self.assertIsNotNone(sfx_dlg)

    def test_sfx_rotation_and_inspector_toggle(self):
        """Test onomatopoeia rotation handle, inspector controls, and panel toggle."""
        win = MainWindow()
        win.canvas.load_image("input/test_01_infirmary.jpg")
        
        # Add SFX bubble
        win._add_sfx_bubble()
        sfx_item = win.canvas.bubble_items[-1]
        self.assertEqual(sfx_item.config.type, "sfx")
        self.assertTrue(sfx_item.isSelected())
        self.assertTrue(sfx_item.rotate_handle.isVisible())
        self.assertFalse(win.inspector.grp_sfx.isHidden())

        # Test preset button
        win.inspector._set_angle_preset(45)
        self.assertEqual(sfx_item.config.angle, 45.0)
        self.assertEqual(win.inspector.spin_angle.value(), 45)
        self.assertEqual(win.inspector.slider_angle.value(), 45)

        # Test on-canvas rotation handle trigger
        sfx_item.on_rotate_angle(-30.0, is_final=True)
        self.assertEqual(sfx_item.config.angle, -30.0)
        win.inspector.sync_from_item()
        self.assertEqual(win.inspector.spin_angle.value(), -30)

        # Test toggle inspector panel action
        self.assertFalse(win.inspector.isHidden())
        win.act_toggle_inspector.setChecked(False)
        self.assertTrue(win.inspector.isHidden())
        win.act_toggle_inspector.setChecked(True)
        self.assertFalse(win.inspector.isHidden())

        # Test duplicate and remove actions
        initial_count = len(win.canvas.bubble_items)
        dup = win.canvas._duplicate_bubble(sfx_item)
        self.assertEqual(len(win.canvas.bubble_items), initial_count + 1)
        self.assertEqual(dup.config.angle, -30.0)

        win.canvas.remove_bubble(dup)
        self.assertEqual(len(win.canvas.bubble_items), initial_count)

    def test_inspector_scroll_and_width(self):
        """Test that the inspector scroll area stays enabled even when no item is selected and fits narrow widths."""
        win = MainWindow()
        win.resize(1000, 500)
        win.show()
        self.app.processEvents()

        # Even with no bubble selected (set_item(None)), scroll area itself must remain enabled
        win.inspector.set_item(None)
        self.assertTrue(win.inspector.isEnabled())
        self.assertTrue(win.inspector.scroll.isEnabled())
        self.assertFalse(win.inspector.container.isEnabled())

        # Container minimum width should be compact (< 280px) so it never clips horizontally
        self.assertLess(win.inspector.container.minimumSizeHint().width(), 280)

        # Vertical scrollbar should have a positive range on a 500px tall window
        vbar = win.inspector.scroll.verticalScrollBar()
        self.assertGreater(vbar.maximum(), 0)
        vbar.setValue(80)
        self.assertEqual(vbar.value(), 80)

    def test_v065_tail_flip_and_spread_alignment(self):
        """Test v0.65beta tail horizontal flip (single & batch) and 2-page spread alignment."""
        win = MainWindow()
        self.assertIn("0.65beta", win.windowTitle())
        win.canvas.load_image("input/test_01_infirmary.jpg")

        # Add left-page bubble (cx=0.25) with tail pointing left (tx=0.15)
        cfg_left = BubbleConfig(
            text="左ページ",
            type="capsule",
            center=(0.25, 0.30),
            tail=(0.15, 0.45),
            tail_anchor=-135.0
        )
        b_left = win.canvas.add_bubble(cfg_left)

        # Add right-page bubble (cx=0.75) with tail pointing right (tx=0.85)
        cfg_right = BubbleConfig(
            text="右ページ",
            type="capsule",
            center=(0.75, 0.30),
            tail=(0.85, 0.45),
            tail_anchor=135.0
        )
        b_right = win.canvas.add_bubble(cfg_right)

        # 1. Single tail flip on b_left: tx should mirror across cx=0.25 -> 0.35
        b_left.flip_tail_horizontal()
        self.assertAlmostEqual(b_left.config.tail[0], 0.35, places=4)
        self.assertAlmostEqual(b_left.config.tail_anchor, 135.0, places=4)

        # 2. Batch flip all tails horizontally
        count = win.canvas.flip_all_tails_horizontal()
        self.assertEqual(count, 2)
        self.assertAlmostEqual(b_left.config.tail[0], 0.15, places=4)
        self.assertAlmostEqual(b_right.config.tail[0], 0.65, places=4)

        # 3. Spread inward alignment: left half (<0.5) points right (>cx), right half (>=0.5) points left (<cx)
        win.canvas.align_tails_for_spread("inward")
        self.assertGreater(b_left.config.tail[0], b_left.config.center[0])
        self.assertLess(b_right.config.tail[0], b_right.config.center[0])

        # 4. Spread outward alignment: left half points left (<cx), right half points right (>cx)
        win.canvas.align_tails_for_spread("outward")
        self.assertLess(b_left.config.tail[0], b_left.config.center[0])
        self.assertGreater(b_right.config.tail[0], b_right.config.center[0])

    def test_v065_patch_bubble_and_text_cleaner(self):
        """Test v0.65beta non-destructive cover patch (type='patch') and text cleaner with undo."""
        from PIL import Image, ImageDraw
        from PySide6.QtCore import QRectF
        from comic_bubble.cleaner import clean_bubble_text_in_region, sample_bubble_paper_color

        # Create synthetic manga image with a speech bubble (black border, white interior, black text pixels inside)
        img = Image.new("RGB", (400, 300), (180, 180, 180))
        draw = ImageDraw.Draw(img)
        # Draw bubble oval with thick black outline and warm-white paper fill
        draw.ellipse([100, 50, 300, 250], fill=(252, 250, 245), outline=(20, 20, 20), width=4)
        # Draw dark "dialogue text" strokes inside the bubble (not touching border)
        draw.rectangle([185, 95, 195, 200], fill=(15, 15, 15))
        draw.rectangle([205, 105, 215, 190], fill=(15, 15, 15))

        # 1. Test paper color sampling
        paper_rgb = sample_bubble_paper_color(img, (140, 80, 260, 220))
        self.assertGreaterEqual(paper_rgb[0], 245)

        # 2. Test clean_bubble_text_in_region preserves outer border and erases interior text
        cleaned_img, detected_rgb = clean_bubble_text_in_region(img, (140, 80, 260, 220))
        # Center where dark text was (190, 150) should now be bright paper color
        px_after = cleaned_img.getpixel((190, 150))
        self.assertGreater(px_after[0], 240)
        # Bubble border at (101, 150) should still be dark
        px_border = cleaned_img.getpixel((101, 150))
        self.assertLess(px_border[0], 50)

        # 3. Test canvas clean_region_and_place_bubble + Ctrl+Z undo
        win = MainWindow()
        win.canvas.load_image_from_pil(img, "synthetic_bubble.png")
        new_item = win.canvas.clean_region_and_place_bubble(QRectF(140, 80, 120, 140))
        self.assertIsNotNone(new_item)
        self.assertEqual(new_item.config.type, "none")
        self.assertEqual(len(win.canvas._image_undo_stack), 1)
        # Verify canvas pixel was cleaned
        self.assertGreater(win.canvas.base_pil_image.getpixel((190, 150))[0], 240)

        # Undo should restore the dark text pixel
        undone = win.canvas.undo_last_clean()
        self.assertTrue(undone)
        self.assertLess(win.canvas.base_pil_image.getpixel((190, 150))[0], 50)

        # 4. Test type="patch" rendering and inspector checkbox toggle
        win.inspector.set_item(new_item)
        win.inspector.chk_cover_old_text.setChecked(True)
        self.assertEqual(new_item.config.type, "patch")
        self.assertEqual(new_item.config.bg_alpha, 1.0)

        # Render full scene with patch bubble
        scene = SceneConfig(
            image_path=win.canvas.base_pil_image,
            bubbles=win.canvas.get_all_bubble_configs(),
            supersample_scale=1
        )
        rendered = render_scene(scene)
        self.assertEqual(rendered.size, (400, 300))

if __name__ == "__main__":
    unittest.main()




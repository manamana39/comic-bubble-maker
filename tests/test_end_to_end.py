"""
End-to-end integration tests for Comic Bubble Engine.
Tests realistic speech bubble + floating monologue compositions.
"""

import os
import unittest
from PIL import Image
from comic_bubble.models import BubbleConfig, SceneConfig
from comic_bubble.engine import render_scene, render_from_file

class TestEndToEnd(unittest.TestCase):

    def setUp(self):
        self.test_img_path = "output/test_e2e_input.png"
        img = Image.new("RGB", (400, 400), (60, 50, 75))
        img.save(self.test_img_path)

    def tearDown(self):
        if os.path.exists(self.test_img_path):
            os.remove(self.test_img_path)

    def test_full_pipeline_speech_and_monologue(self):
        speech = BubbleConfig(
            text="<small>…あのね。</small>\n<big>好きだよ！</big>",
            type="capsule",
            font="kiwi",
            center=(0.3, 0.3),
            tail=(0.4, 0.45)
        )
        monologue = BubbleConfig(
            text="（…言っちゃった…）",
            type="floating",
            font="mincho",
            center=(0.7, 0.6)
        )
        scene = SceneConfig(
            image_path=self.test_img_path,
            bubbles=[speech, monologue],
            output_path="output/test_e2e_output.png",
            supersample_scale=2
        )
        result = render_scene(scene)

        # Output dimensions must exactly match input dimensions
        self.assertEqual(result.size, (400, 400))
        self.assertEqual(result.mode, "RGB")

        # Save and verify file existence
        result.save(scene.output_path)
        self.assertTrue(os.path.exists(scene.output_path))
        self.assertGreater(os.path.getsize(scene.output_path), 0)

if __name__ == "__main__":
    unittest.main()

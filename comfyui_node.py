"""
comfyui_node.py
~~~~~~~~~~~~~~~
Native ComfyUI Custom Node integration.
Drop this repository directly into your ComfyUI/custom_nodes/ folder!
Provides '💬 Manga Speech Bubble & SFX' in the ComfyUI node catalog.
"""

import numpy as np
from PIL import Image
from comic_bubble.models import BubbleConfig, SceneConfig
from comic_bubble.engine import render_scene

class ComicBubbleNode:
    """ComfyUI Node for rendering Japanese manga speech bubbles, monologues, and sound effects."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "text": ("STRING", {"multiline": True, "default": "…べ、別に。\n待ってなんかないし！"}),
                "bubble_type": (["capsule", "cloud", "scream", "whisper", "floating", "box", "sfx"], {"default": "capsule"}),
                "font": (["kiwi", "yomogi", "zenmaru", "ud", "mincho", "bold"], {"default": "kiwi"}),
                "center_x": ("FLOAT", {"default": 0.20, "min": 0.0, "max": 1.0, "step": 0.01}),
                "center_y": ("FLOAT", {"default": 0.20, "min": 0.0, "max": 1.0, "step": 0.01}),
                "has_tail": ("BOOLEAN", {"default": True}),
                "tail_x": ("FLOAT", {"default": 0.32, "min": 0.0, "max": 1.0, "step": 0.01}),
                "tail_y": ("FLOAT", {"default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01}),
                "font_size_ratio": ("FLOAT", {"default": 0.022, "min": 0.010, "max": 0.080, "step": 0.002}),
                "visibility_mode": (["auto", "transparent", "balanced", "solid"], {"default": "auto"}),
                "angle": ("FLOAT", {"default": 0.0, "min": -180.0, "max": 180.0, "step": 1.0}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "apply_bubble"
    CATEGORY = "Comic Bubble"

    def apply_bubble(
        self,
        image,
        text,
        bubble_type,
        font,
        center_x,
        center_y,
        has_tail,
        tail_x,
        tail_y,
        font_size_ratio,
        visibility_mode,
        angle
    ):
        # image is a torch Tensor of shape [batch, height, width, 3] in range [0.0, 1.0]
        # or numpy array if running in standalone test
        try:
            import torch
            is_torch = isinstance(image, torch.Tensor)
        except ImportError:
            is_torch = False

        batch_out = []
        batch_size = image.shape[0]

        for b in range(batch_size):
            if is_torch:
                np_img = (image[b].cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
            else:
                np_img = (image[b] * 255.0).clip(0, 255).astype(np.uint8)

            pil_img = Image.fromarray(np_img)
            tmp_in_path = f"_comfy_tmp_in_{b}.png"
            pil_img.save(tmp_in_path)

            bubble = BubbleConfig(
                text=text.replace("\\n", "\n"),
                type=bubble_type,
                font=font,
                center=(center_x, center_y),
                tail=(tail_x, tail_y) if has_tail else None,
                font_size_ratio=font_size_ratio,
                visibility_mode=visibility_mode,
                angle=angle
            )
            scene = SceneConfig(
                image_path=tmp_in_path,
                bubbles=[bubble],
                supersample_scale=3
            )
            out_pil = render_scene(scene)

            import os
            if os.path.exists(tmp_in_path):
                os.remove(tmp_in_path)

            out_np = np.array(out_pil, dtype=np.float32) / 255.0
            batch_out.append(out_np)

        res_np = np.stack(batch_out, axis=0)
        if is_torch:
            return (torch.from_numpy(res_np),)
        return (res_np,)

NODE_CLASS_MAPPINGS = {
    "ComicBubbleNode": ComicBubbleNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComicBubbleNode": "💬 Manga Speech Bubble & SFX"
}

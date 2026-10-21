"""
comic_bubble.engine
~~~~~~~~~~~~~~~~~~~
High-resolution supersampled rendering pipeline for Comic Bubble Engine.
Supports capsules, clouds, ovals, boxes, screams, whispers, floating monologues, and manga SFX.
"""

import os
from typing import Union, Tuple, Optional, List, Dict, Any
from PIL import Image, ImageDraw

from .effects import has_text_fx, apply_text_fx, composite_centered
from .models import BubbleConfig, SceneConfig
from .typography import parse_styled_text, measure_vertical_styled_text, draw_vertical_measured
from .fonts import get_font
from .shapes import (
    generate_capsule_polygon,
    generate_cloud_polygon,
    generate_oval_bubble_polygon,
    generate_scream_polygon,
    draw_dashed_polygon,
    draw_thought_tail_circles
)
from .contrast import analyze_background_and_adjust
from .auto_layout import find_safe_background_center

def to_pixels(val: Union[int, float], total: int) -> int:
    """Convert relative ratio [0.0..1.0] or pixel coordinate to absolute integer pixels."""
    if isinstance(val, (int, float)) and val <= 1.0:
        return int(val * total)
    return int(val)

def render_scene(scene: SceneConfig) -> Image.Image:
    """
    Render bubbles, floating monologues, and manga sound effects onto the base image.
    Uses 3x supersampling with Lanczos downsampling for crisp, professional anti-aliasing.
    """
    if isinstance(scene.image_path, Image.Image):
        base_img = scene.image_path.convert("RGBA")
    else:
        base_img = Image.open(scene.image_path).convert("RGBA")
    w, h = base_img.size
    scale = scene.supersample_scale

    sw = w * scale
    sh = h * scale
    overlay_hi = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw_hi = ImageDraw.Draw(overlay_hi)

    for item in scene.bubbles:
        text = item.text
        b_type = item.type.lower()
        if b_type == "monologue":
            b_type = "floating"
        elif b_type == "burst":
            b_type = "scream"
        elif b_type == "onomatopoeia":
            b_type = "sfx"

        font_name = item.font
        base_font_size = int(h * item.font_size_ratio * scale)

        border_color = item.border_color
        border_width = int(item.border_width * scale)
        text_color = item.text_color
        text_halo = item.text_halo
        halo_color = item.halo_color

        # Special Mode: Manga Sound Effects / Onomatopoeia (描き文字)
        if b_type == "sfx":
            f = get_font(base_font_size, font_name)
            # Render rotated styled sound effect
            bbox = f.getbbox(text)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad = int(item.stroke_width * scale * 2) + 20
            txt_canvas = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
            txt_draw = ImageDraw.Draw(txt_canvas)

            strk_w = int(item.stroke_width * scale)
            txt_draw.text(
                (pad - bbox[0], pad - bbox[1]),
                text,
                font=f,
                fill=text_color,
                stroke_width=strk_w,
                stroke_fill=item.stroke_color
            )

            if has_text_fx(item):
                txt_canvas = apply_text_fx(txt_canvas, item, scale)

            # Apply rotation angle if specified
            if abs(item.angle) > 0.01:
                txt_canvas = txt_canvas.rotate(-item.angle, resample=Image.Resampling.BICUBIC, expand=True)

            cw, ch = txt_canvas.size
            if item.center is not None and item.center != "auto":
                cx_scaled = to_pixels(item.center[0], w) * scale
                cy_scaled = to_pixels(item.center[1], h) * scale
            else:
                auto_cx, auto_cy = find_safe_background_center(base_img, cw // scale, ch // scale)
                cx_scaled = int(auto_cx * w * scale)
                cy_scaled = int(auto_cy * h * scale)

            overlay_hi.alpha_composite(txt_canvas, (cx_scaled - cw // 2, cy_scaled - ch // 2))
            continue

        # Standard Speech / Monologue Types
        styled_lines = parse_styled_text(text)
        t_w, t_h, col_ws, col_hs, char_metrics = measure_vertical_styled_text(
            draw_hi, styled_lines, base_font_size, font_name
        )

        pad_x = item.padding_ratio_x
        pad_y = item.padding_ratio_y

        num_cols = len(styled_lines)
        # Ratio limiter for 1-column vertical text to prevent gigantic horizontal ballooning
        ratio_mult = 0.58 if num_cols >= 2 else 0.28

        if b_type == "capsule":
            bw = max(int(t_w * (pad_x if pad_x is not None else 2.05)), int(t_h * ratio_mult))
            if num_cols == 1:
                bw = min(bw, int(t_w * 3.4))
            bh = int(t_h * (pad_y if pad_y is not None else 1.34))
        elif b_type == "cloud":
            bw = max(int(t_w * (pad_x if pad_x is not None else 2.25)), int(t_h * (0.60 if num_cols >= 2 else 0.30)))
            if num_cols == 1:
                bw = min(bw, int(t_w * 3.5))
            bh = int(t_h * (pad_y if pad_y is not None else 1.36))
        elif b_type == "scream":
            bw = max(int(t_w * (pad_x if pad_x is not None else 2.30)), int(t_h * (0.68 if num_cols >= 2 else 0.35)))
            if num_cols == 1:
                bw = min(bw, int(t_w * 3.6))
            bh = int(t_h * (pad_y if pad_y is not None else 1.42))
        elif b_type == "whisper":
            bw = max(int(t_w * (pad_x if pad_x is not None else 2.05)), int(t_h * ratio_mult))
            if num_cols == 1:
                bw = min(bw, int(t_w * 3.4))
            bh = int(t_h * (pad_y if pad_y is not None else 1.34))
        elif b_type == "box":
            bw = int(t_w * (pad_x if pad_x is not None else 1.45))
            bh = int(t_h * (pad_y if pad_y is not None else 1.20))
        elif b_type == "patch":
            bw = max(int(t_w * (pad_x if pad_x is not None else 1.55)), int(t_h * (0.45 if num_cols >= 2 else 0.24)))
            bh = int(t_h * (pad_y if pad_y is not None else 1.22))
        elif b_type in ("floating", "none"):
            bw = t_w
            bh = t_h
        else:  # oval
            bw = max(int(t_w * (pad_x if pad_x is not None else 2.15)), int(t_h * (0.60 if num_cols >= 2 else 0.30)))
            if num_cols == 1:
                bw = min(bw, int(t_w * 3.4))
            bh = int(t_h * (pad_y if pad_y is not None else 1.38))

        # Explicit bubble padding overrides the automatic size rules (and their minimum/maximum limits)
        if b_type not in ("floating", "none"):
            if pad_x is not None:
                bw = max(1, int(t_w * pad_x))
            if pad_y is not None:
                bh = max(1, int(t_h * pad_y))

        # Explicit bubble padding overrides the automatic size rules (and their minimum/maximum limits)
        if b_type not in ("floating", "none"):
            if pad_x is not None:
                bw = max(1, int(t_w * pad_x))
            if pad_y is not None:
                bh = max(1, int(t_h * pad_y))

        # Position calculation
        if item.center is not None and item.center != "auto":
            cx_scaled = to_pixels(item.center[0], w) * scale
            cy_scaled = to_pixels(item.center[1], h) * scale
        elif item.box is not None:
            raw_bx1 = to_pixels(item.box[0], w) * scale
            raw_by1 = to_pixels(item.box[1], h) * scale
            raw_bw = to_pixels(item.box[2], w) * scale
            raw_bh = to_pixels(item.box[3], h) * scale
            cx_scaled = raw_bx1 + raw_bw // 2
            cy_scaled = raw_by1 + raw_bh // 2
        else:
            # Intelligent automatic background placement
            auto_cx, auto_cy = find_safe_background_center(base_img, bw // scale, bh // scale)
            cx_scaled = int(auto_cx * w * scale)
            cy_scaled = int(auto_cy * h * scale)

        bx1 = cx_scaled - bw // 2
        by1 = cy_scaled - bh // 2

        # Edge clamping
        margin_edge = int(8 * scale)
        if bx1 < margin_edge:
            bx1 = margin_edge
        if by1 < margin_edge:
            by1 = margin_edge
        if bx1 + bw > sw - margin_edge:
            bx1 = sw - margin_edge - bw
        if by1 + bh > sh - margin_edge:
            by1 = sh - margin_edge - bh

        bx2 = bx1 + bw
        by2 = by1 + bh

        # Tail coordinate
        tail_pt = None
        if item.tail is not None:
            tail_pt = (to_pixels(item.tail[0], w) * scale, to_pixels(item.tail[1], h) * scale)

        rect = (bx1, by1, bx2, by2)
        native_rect = (bx1 // scale, by1 // scale, bx2 // scale, by2 // scale)

        # Auto-Contrast luminance analysis
        if b_type == "patch":
            final_alpha = item.bg_alpha if item.bg_alpha is not None else 1.0
            halo_boost = False
            text_halo = False
        else:
            final_alpha, halo_boost = analyze_background_and_adjust(
                base_img, native_rect, text_color, item.bg_alpha, item.visibility_mode
            )

        fill_color = (item.bg_color[0], item.bg_color[1], item.bg_color[2], int(final_alpha * 255)) if final_alpha > 0 else (0, 0, 0, 0)
        if halo_boost:
            text_halo = True

        # Render Bubble shape
        if b_type == "cloud":
            poly = generate_cloud_polygon(rect, num_bumps=14, bump_ratio=0.13)
            draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)
            if tail_pt:
                draw_thought_tail_circles(draw_hi, rect, tail_pt, border_color, fill_color, border_width)
        elif b_type == "scream":
            poly = generate_scream_polygon(rect, tail_pt, num_spikes=18, depth_ratio=0.30)
            draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)
        elif b_type == "whisper":
            poly = generate_capsule_polygon(rect, tail_pt, anchor_deg=item.tail_anchor)
            draw_dashed_polygon(draw_hi, poly, fill=fill_color, outline=border_color, width=border_width)
        elif b_type == "oval":
            poly = generate_oval_bubble_polygon(rect, tail_pt, anchor_deg=item.tail_anchor)
            draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)
        elif b_type == "box":
            draw_hi.rectangle(rect, fill=fill_color, outline=border_color, width=border_width)
        elif b_type == "patch":
            # Borderless cover patch to blank out existing text inside drawn speech bubbles
            poly = generate_capsule_polygon(rect, None, corner_radius_ratio=0.42)
            draw_hi.polygon(poly, fill=fill_color)
        elif b_type in ("floating", "none"):
            # Borderless floating text
            pass
        else:  # capsule / squircle
            poly = generate_capsule_polygon(rect, tail_pt, anchor_deg=item.tail_anchor)
            draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)

        # Render Vertical Typography
        if has_text_fx(item):
            m = int(20 * scale)
            fx_layer = Image.new("RGBA", (bw + 2 * m, bh + 2 * m), (0, 0, 0, 0))
            draw_vertical_measured(
                ImageDraw.Draw(fx_layer), char_metrics, col_ws, col_hs, t_w, base_font_size,
                (m, m, m + bw, m + bh), text_color,
                text_halo=text_halo, halo_color=halo_color, scale=scale,
                reading_direction=item.reading_direction
            )
            fx_layer = apply_text_fx(fx_layer, item, scale)
            composite_centered(overlay_hi, fx_layer, (bx1 + bx2) // 2, (by1 + by2) // 2)
        else:
            draw_vertical_measured(
                draw_hi,
                char_metrics,
                col_ws,
                col_hs,
                t_w,
                base_font_size,
                rect,
                text_color,
                text_halo=text_halo,
                halo_color=halo_color,
                scale=scale,
                reading_direction=item.reading_direction
            )

    # Downsample overlay with high-quality Lanczos filter
    overlay = overlay_hi.resize((w, h), resample=Image.Resampling.LANCZOS)
    result = Image.alpha_composite(base_img, overlay).convert("RGB")
    return result

def render_from_file(config_path: str, output_path: Optional[str] = None) -> str:
    """Load JSON config, render scene, and save image to output_path."""
    import json
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scene = SceneConfig.from_dict(data)
    if output_path:
        scene.output_path = output_path

    result = render_scene(scene)
    os.makedirs(os.path.dirname(os.path.abspath(scene.output_path)), exist_ok=True)
    result.save(scene.output_path, quality=98)
    return scene.output_path

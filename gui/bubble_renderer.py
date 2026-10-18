"""
gui.bubble_renderer
~~~~~~~~~~~~~~~~~~~
Renders an individual BubbleConfig into a local PIL RGBA image and QPixmap.
Used by the interactive canvas for real-time 60fps manipulation and instant previews.
"""

from typing import Tuple, Optional
from PIL import Image, ImageDraw
from PySide6.QtGui import QImage, QPixmap

from comic_bubble.models import BubbleConfig
from comic_bubble.typography import parse_styled_text, measure_vertical_styled_text, draw_vertical_measured
from comic_bubble.fonts import get_font
from comic_bubble.shapes import (
    generate_capsule_polygon,
    generate_cloud_polygon,
    generate_oval_bubble_polygon,
    generate_scream_polygon,
    draw_dashed_polygon,
    draw_thought_tail_circles
)

def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    """Convert a PIL RGBA image to PySide6 QPixmap."""
    data = pil_img.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_img.width, pil_img.height, pil_img.width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)

def render_single_bubble_local(
    bubble: BubbleConfig,
    img_h: int = 800,
    scale: int = 2,
    tail_local: Optional[Tuple[int, int]] = None
) -> Tuple[Image.Image, Tuple[int, int], Tuple[int, int]]:
    """
    Renders a single bubble in a local coordinate frame centered at (0, 0).
    
    Parameters:
        bubble: BubbleConfig specification
        img_h: Reference image height in pixels for font_size_ratio
        scale: Supersampling scale for crisp rendering
        tail_local: (tx, ty) relative to bubble center (0, 0). If None, uses bubble.tail.

    Returns:
        (image, (offset_x, offset_y), (body_w, body_h))
        offset_x, offset_y: top-left corner relative to (0, 0) in unscaled pixels.
        body_w, body_h: width and height of the bubble body (excluding tail).
    """
    b_type = bubble.type.lower()
    if b_type == "monologue":
        b_type = "floating"
    elif b_type == "burst":
        b_type = "scream"
    elif b_type == "onomatopoeia":
        b_type = "sfx"

    font_name = bubble.font
    base_font_size = int(img_h * bubble.font_size_ratio * scale)
    border_width = int(bubble.border_width * scale)
    border_color = bubble.border_color
    text_color = bubble.text_color
    bg_color = bubble.bg_color

    # Determine background alpha
    if bubble.bg_alpha is not None:
        alpha = int(bubble.bg_alpha * 255)
    elif bubble.visibility_mode == "transparent":
        alpha = 180
    elif bubble.visibility_mode == "solid":
        alpha = 255
    else:  # auto / balanced
        alpha = 235

    fill_color = (bg_color[0], bg_color[1], bg_color[2], alpha) if b_type not in ("floating", "none", "sfx") else (0, 0, 0, 0)

    # 1. SFX Rendering Mode
    if b_type == "sfx":
        f = get_font(base_font_size, font_name)
        bbox = f.getbbox(bubble.text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad = int(bubble.stroke_width * scale * 2) + 20 * scale
        txt_canvas = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
        txt_draw = ImageDraw.Draw(txt_canvas)
        strk_w = int(bubble.stroke_width * scale)

        txt_draw.text(
            (pad - bbox[0], pad - bbox[1]),
            bubble.text,
            font=f,
            fill=text_color,
            stroke_width=strk_w,
            stroke_fill=bubble.stroke_color
        )

        if abs(bubble.angle) > 0.01:
            txt_canvas = txt_canvas.rotate(-bubble.angle, resample=Image.Resampling.BICUBIC, expand=True)

        cw, ch = txt_canvas.size
        cw_unscaled = cw // scale
        ch_unscaled = ch // scale
        result = txt_canvas.resize((cw_unscaled, ch_unscaled), resample=Image.Resampling.LANCZOS)
        return result, (-cw_unscaled // 2, -ch_unscaled // 2), (cw_unscaled, ch_unscaled)

    # 2. Text Measurement
    styled_lines = parse_styled_text(bubble.text)
    # Temporary draw object for measuring text
    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    t_w, t_h, col_ws, col_hs, char_metrics = measure_vertical_styled_text(
        dummy_draw, styled_lines, base_font_size, font_name
    )

    pad_x = bubble.padding_ratio_x
    pad_y = bubble.padding_ratio_y

    if b_type == "capsule":
        bw = max(int(t_w * (pad_x if pad_x is not None else 2.05)), int(t_h * 0.58))
        bh = int(t_h * (pad_y if pad_y is not None else 1.34))
    elif b_type == "cloud":
        bw = max(int(t_w * (pad_x if pad_x is not None else 2.25)), int(t_h * 0.60))
        bh = int(t_h * (pad_y if pad_y is not None else 1.36))
    elif b_type == "scream":
        bw = max(int(t_w * (pad_x if pad_x is not None else 2.30)), int(t_h * 0.68))
        bh = int(t_h * (pad_y if pad_y is not None else 1.42))
    elif b_type == "whisper":
        bw = max(int(t_w * (pad_x if pad_x is not None else 2.05)), int(t_h * 0.58))
        bh = int(t_h * (pad_y if pad_y is not None else 1.34))
    elif b_type == "box":
        bw = int(t_w * (pad_x if pad_x is not None else 1.45))
        bh = int(t_h * (pad_y if pad_y is not None else 1.20))
    elif b_type in ("floating", "none"):
        bw = t_w + 20 * scale
        bh = t_h + 20 * scale
    else:  # oval
        bw = max(int(t_w * (pad_x if pad_x is not None else 2.15)), int(t_h * 0.60))
        bh = int(t_h * (pad_y if pad_y is not None else 1.38))

    body_bx1 = -bw // 2
    body_by1 = -bh // 2
    body_bx2 = body_bx1 + bw
    body_by2 = body_by1 + bh

    # Tail handling (tail_local in scaled coordinates)
    scaled_tail = None
    if tail_local is not None and b_type not in ("floating", "none", "sfx"):
        scaled_tail = (int(tail_local[0] * scale), int(tail_local[1] * scale))

    # Bounding box encompassing body and tail
    min_x = body_bx1
    min_y = body_by1
    max_x = body_bx2
    max_y = body_by2

    if scaled_tail:
        min_x = min(min_x, scaled_tail[0])
        min_y = min(min_y, scaled_tail[1])
        max_x = max(max_x, scaled_tail[0])
        max_y = max(max_y, scaled_tail[1])

    # Add margin for border and blur
    margin = int(16 * scale)
    min_x -= margin
    min_y -= margin
    max_x += margin
    max_y += margin

    canvas_w = max_x - min_x
    canvas_h = max_y - min_y

    hi_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw_hi = ImageDraw.Draw(hi_img)

    # Shift coordinates into canvas space
    offset_x_hi = -min_x
    offset_y_hi = -min_y

    canvas_rect = (
        body_bx1 + offset_x_hi,
        body_by1 + offset_y_hi,
        body_bx2 + offset_x_hi,
        body_by2 + offset_y_hi
    )

    canvas_tail = (scaled_tail[0] + offset_x_hi, scaled_tail[1] + offset_y_hi) if scaled_tail else None

    # Render Bubble Polygon
    if b_type == "cloud":
        poly = generate_cloud_polygon(canvas_rect, num_bumps=14, bump_ratio=0.13)
        draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)
        if canvas_tail:
            draw_thought_tail_circles(draw_hi, canvas_rect, canvas_tail, border_color, fill_color, border_width)
    elif b_type == "scream":
        poly = generate_scream_polygon(canvas_rect, canvas_tail, num_spikes=18, depth_ratio=0.30)
        draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)
    elif b_type == "whisper":
        poly = generate_capsule_polygon(canvas_rect, canvas_tail)
        draw_dashed_polygon(draw_hi, poly, fill=fill_color, outline=border_color, width=border_width)
    elif b_type == "oval":
        poly = generate_oval_bubble_polygon(canvas_rect, canvas_tail)
        draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)
    elif b_type == "box":
        draw_hi.rectangle(canvas_rect, fill=fill_color, outline=border_color, width=border_width)
    elif b_type in ("floating", "none"):
        pass
    else:  # capsule
        poly = generate_capsule_polygon(canvas_rect, canvas_tail)
        draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)

    # Render Vertical Typography
    draw_vertical_measured(
        draw_hi,
        char_metrics,
        col_ws,
        col_hs,
        t_w,
        base_font_size,
        canvas_rect,
        text_color,
        text_halo=bubble.text_halo,
        halo_color=bubble.halo_color,
        scale=scale
    )

    # Downsample with Lanczos
    target_w = max(1, canvas_w // scale)
    target_h = max(1, canvas_h // scale)
    result = hi_img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)

    unscaled_offset_x = min_x // scale
    unscaled_offset_y = min_y // scale
    unscaled_body_w = bw // scale
    unscaled_body_h = bh // scale

    return result, (unscaled_offset_x, unscaled_offset_y), (unscaled_body_w, unscaled_body_h)

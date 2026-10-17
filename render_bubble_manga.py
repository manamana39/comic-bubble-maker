"""
Manga Vertical Bubble Engine (High Precision)
==============================================
日本の商業漫画スタイルの縦書き・タマゴ型楕円吹き出しを極めて美しく描画するエンジン。
- 楕円としっぽを完全シームレスに結合（貫通線ゼロ）
- 縦書き日本語組版（文字間・行間の最適化）
- 3倍スーパーサンプリング（LANCZOS）による超高品位アンチエイリアス
"""

import os
import sys
import json
import math
import argparse
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

# 縦書き用文字変換
VERTICAL_REPLACEMENTS = {
    "ー": "丨",
    "-": "丨",
    "―": "丨",
    "–": "丨",
    "—": "丨",
    "～": "丨",
    "~": "丨",
    "（": "︵",
    "）": "︶",
    "(": "︵",
    ")": "︶",
    "「": "﹁",
    "」": "﹂",
    "『": "﹁",
    "』": "﹂",
    "…": "︰",
    "‥": "︰",
}

# 縦書き時に右上に小さく寄せる文字
SMALL_CHAR_OFFSET = {
    "っ": (0.12, -0.05),
    "ゃ": (0.12, -0.05),
    "ゅ": (0.12, -0.05),
    "ょ": (0.12, -0.05),
    "ぁ": (0.12, -0.05),
    "ぃ": (0.12, -0.05),
    "ぅ": (0.12, -0.05),
    "ぇ": (0.12, -0.05),
    "ぉ": (0.12, -0.05),
    "ッ": (0.12, -0.05),
    "ャ": (0.12, -0.05),
    "ュ": (0.12, -0.05),
    "ョ": (0.12, -0.05),
    "、": (0.22, -0.2),
    "。": (0.22, -0.2),
}

DEFAULT_FONTS = {
    "bold": "C:/Windows/Fonts/YuGothB.ttc",
    "normal": "C:/Windows/Fonts/YuGothM.ttc",
    "meiryo": "C:/Windows/Fonts/meiryob.ttc",
    "mincho": "C:/Windows/Fonts/msmincho.ttc",
}

def get_font(size: int, style: str = "bold", custom_path: str = None) -> ImageFont.FreeTypeFont:
    if custom_path and os.path.exists(custom_path):
        try:
            return ImageFont.truetype(custom_path, size)
        except Exception:
            pass

    font_path = DEFAULT_FONTS.get(style, DEFAULT_FONTS["bold"])
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    return ImageFont.load_default()

def to_pixels(val: float, total: int) -> int:
    if isinstance(val, (int, float)) and val <= 1.0:
        return int(val * total)
    return int(val)

def generate_seamless_bubble_polygon(
    rect: Tuple[int, int, int, int],
    tail: Tuple[int, int] = None,
    num_samples: int = 120
) -> List[Tuple[float, float]]:
    """
    楕円本体としっぽを1つの連続したポリゴンとして生成し、
    枠線の貫通を完全に防ぐ。
    """
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    rx = (x2 - x1) / 2.0
    ry = (y2 - y1) / 2.0

    if not tail:
        # 単純な楕円ポリゴン
        poly = []
        for i in range(num_samples):
            th = i * (2.0 * math.pi / num_samples)
            poly.append((cx + rx * math.cos(th), cy + ry * math.sin(th)))
        return poly

    tx, ty = tail
    tail_angle = math.atan2(ty - cy, tx - cx)
    if tail_angle < 0:
        tail_angle += 2.0 * math.pi

    # しっぽの根元の開き角度
    base_span = 0.22  # ラジアン

    poly = []
    inserted_tail = False

    for i in range(num_samples):
        th = i * (2.0 * math.pi / num_samples)
        
        # 角度差を計算
        diff = (th - tail_angle + math.pi) % (2.0 * math.pi) - math.pi

        if abs(diff) < base_span / 2.0:
            if not inserted_tail:
                # しっぽの始点、先端、終点を挿入
                p1_th = tail_angle - base_span / 2.0
                p2_th = tail_angle + base_span / 2.0
                poly.append((cx + rx * math.cos(p1_th), cy + ry * math.sin(p1_th)))
                poly.append((tx, ty))
                poly.append((cx + rx * math.cos(p2_th), cy + ry * math.sin(p2_th)))
                inserted_tail = True
        else:
            poly.append((cx + rx * math.cos(th), cy + ry * math.sin(th)))

    return poly

def draw_vertical_text(
    draw: ImageDraw.ImageDraw,
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    box: Tuple[int, int, int, int],
    text_color=(0, 0, 0, 255),
    line_spacing_ratio=0.30
):
    """
    縦書き日本語組版（右から左へ配置、美しい行間・文字間）
    """
    x1, y1, x2, y2 = box
    box_w = x2 - x1
    box_h = y2 - y1

    sample_bbox = draw.textbbox((0, 0), "あ", font=font)
    char_h = sample_bbox[3] - sample_bbox[1]
    char_w = sample_bbox[2] - sample_bbox[0]

    # 商業漫画らしい文字間・列間
    char_spacing = int(char_h * 0.05)
    col_spacing = int(char_w * line_spacing_ratio)
    col_width = char_w + col_spacing

    num_cols = len(lines)
    total_text_width = num_cols * char_w + (num_cols - 1) * col_spacing

    # 最右列のX位置
    start_x = x1 + (box_w + total_text_width) // 2 - char_w

    for col_idx, line in enumerate(lines):
        col_x = start_x - col_idx * col_width

        # 文字ごとの送り幅（アドバンス）を決定
        advances = []
        for ch in line:
            if ch in ("っ", "ッ", "ゃ", "ゅ", "ょ", "ぁ", "ぃ", "ぅ", "ぇ", "ぉ", "ャ", "ュ", "ョ", "ァ", "ィ", "ゥ", "ェ", "ォ"):
                advances.append(int(char_h * 0.85))
            elif ch in ("、", "。"):
                advances.append(int(char_h * 0.6))
            else:
                advances.append(char_h)

        total_col_h = sum(advances) + (len(line) - 1) * char_spacing
        cur_y = y1 + (box_h - total_col_h) // 2

        for ch_idx, char in enumerate(line):
            disp_char = VERTICAL_REPLACEMENTS.get(char, char)
            c_bbox = draw.textbbox((0, 0), disp_char, font=font)
            c_w = c_bbox[2] - c_bbox[0]
            c_h = c_bbox[3] - c_bbox[1]

            # 基本位置
            draw_x = col_x + (char_w - c_w) // 2
            draw_y = cur_y

            # 句読点・小書き文字の位置微調整
            if char in ("っ", "ッ", "ゃ", "ゅ", "ょ", "ぁ", "ぃ", "ぅ", "ぇ", "ぉ", "ャ", "ュ", "ョ", "ァ", "ィ", "ゥ", "ェ", "ォ"):
                draw_x += int(char_w * 0.14)
                draw_y += int(char_h * 0.05)
            elif char in ("、", "。"):
                draw_x += int(char_w * 0.25)
                draw_y -= int(char_h * 0.15)
            else:
                draw_y += (char_h - c_h) // 2

            draw.text((draw_x, draw_y), disp_char, font=font, fill=text_color)
            cur_y += advances[ch_idx] + char_spacing

def render_bubbles_high_quality(
    image_path: str,
    bubbles: List[Dict[str, Any]],
    output_path: str,
    scale: int = 3
):
    """
    3倍スーパーサンプリングで商業漫画品質の吹き出しを生成
    """
    base_img = Image.open(image_path).convert("RGBA")
    w, h = base_img.size

    sw = w * scale
    sh = h * scale
    overlay_hi = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw_hi = ImageDraw.Draw(overlay_hi)

    for item in bubbles:
        text = item.get("text", "")
        lines = text.split("\n")
        b_type = item.get("type", "manga")

        box = item.get("box", [0.1, 0.1, 0.35, 0.3])
        bx1 = to_pixels(box[0], w) * scale
        by1 = to_pixels(box[1], h) * scale
        bw = to_pixels(box[2], w) * scale
        bh = to_pixels(box[3], h) * scale
        bx2 = bx1 + bw
        by2 = by1 + bh

        tail = item.get("tail", None)
        tail_pt = None
        if tail:
            tail_pt = (to_pixels(tail[0], w) * scale, to_pixels(tail[1], h) * scale)

        border_width = int(item.get("border_width", 2.6) * scale)

        if b_type == "box":
            raw_bg = item.get("bg_color", (220, 240, 252, 255))
            bg_color = tuple(raw_bg) if isinstance(raw_bg, list) else raw_bg
            draw_hi.rectangle((bx1, by1, bx2, by2), fill=bg_color, outline=(0, 0, 0, 255), width=border_width)
            font_style = item.get("font_style", "mincho")
        else:
            bg_color = (255, 255, 255, 255)
            poly = generate_seamless_bubble_polygon((bx1, by1, bx2, by2), tail_pt)
            draw_hi.polygon(poly, fill=bg_color, outline=(0, 0, 0, 255), width=border_width)
            font_style = item.get("font_style", "bold")

        # フォントサイズ
        font_size = int(h * item.get("font_size_ratio", 0.033) * scale)
        font = get_font(font_size, style=font_style, custom_path=item.get("font_path"))

        # テキストエリアマージン
        pad_x = int(bw * 0.18)
        pad_y = int(bh * 0.14)
        text_box = (bx1 + pad_x, by1 + pad_y, bx2 - pad_x, by2 - pad_y)

        draw_vertical_text(draw_hi, lines, font, text_box, text_color=(0, 0, 0, 255))

    # 超高品位縮小合成
    overlay = overlay_hi.resize((w, h), resample=Image.Resampling.LANCZOS)
    result = Image.alpha_composite(base_img, overlay).convert("RGB")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result.save(output_path, quality=98)
    print(f"[OK] Saved manga bubble image: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Manga Vertical Bubble Renderer")
    parser.add_argument("--config", "-c", type=str, required=True, help="Path to config JSON")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        data = json.load(f)

    render_bubbles_high_quality(
        data["image_path"],
        data.get("bubbles", []),
        data.get("output_path", "output/result.png")
    )

if __name__ == "__main__":
    main()

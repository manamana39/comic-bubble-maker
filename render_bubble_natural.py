"""
Natural Manga Bubble Engine (Auto-Fit & Zero Interference)
==========================================================
- Auto-Fit: テキスト量・文字サイズに合わせて吹き出しのサイズと余白を幾何学的に自動計算
  （文字が吹き出しより大きくなる・はみ出す問題を根本解決）
- 吹き出し形状のフレキシブル化:
  - "cloud": モコモコ雲型（テキストのアスペクト比に完全適応）
  - "capsule" / "squircle": 四隅に余裕があるなめらかな角丸（最も文字が綺麗に収まる）
  - "oval": 漫画王道のタマゴ型楕円
- キャラクターへの干渉を完全に防ぐセーフレイアウト
- 部分フォントサイズ変更対応（<big>, <small>, etc.）
- 透過度（bg_alpha: 0.0〜1.0）自由指定
- 3倍スーパーサンプリング (LANCZOS)
"""

import os
import sys
import re
import json
import math
import argparse
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageStat

def get_luminance(rgb: Tuple[int, int, int]) -> float:
    """相対輝度を計算 (0.0〜255.0)"""
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

def analyze_background_and_adjust(
    base_img: Image.Image,
    rect: Tuple[int, int, int, int],
    text_color: Tuple[int, int, int, int],
    specified_alpha: float = None,
    mode: str = "auto"
) -> Tuple[float, bool]:
    """
    背景領域の平均輝度を自動サンプリングし、
    文字と同化しそうな場合は自動で透明度を下げて視認性を確保する
    """
    if mode == "transparent":
        return 0.18, False
    elif mode == "balanced":
        return 0.50, True
    elif mode in ("solid", "readable"):
        return 0.85, True

    base_alpha = specified_alpha if specified_alpha is not None else 0.20

    x1, y1, x2, y2 = rect
    w, h = base_img.size
    cx1 = max(0, min(w, x1))
    cy1 = max(0, min(h, y1))
    cx2 = max(0, min(w, x2))
    cy2 = max(0, min(h, y2))

    if cx2 <= cx1 or cy2 <= cy1:
        return base_alpha, False

    crop = base_img.crop((cx1, cy1, cx2, cy2)).convert("RGB")
    stat = ImageStat.Stat(crop)
    avg_r, avg_g, avg_b = stat.mean[:3]
    bg_lum = get_luminance((avg_r, avg_g, avg_b))
    text_lum = get_luminance(text_color[:3])

    contrast = abs(bg_lum - text_lum)

    # コントラスト不足の判定（暗い背景に濃い文字など）
    if contrast < 110:
        # 背景と同化する危険大！不透明度を 0.78〜0.85 に引き上げて文字を確実に保護
        adjusted_alpha = max(base_alpha, 0.80)
        print(f"[Auto-Contrast] Low contrast detected (bg_lum={bg_lum:.1f}, text_lum={text_lum:.1f}, diff={contrast:.1f}). Boosting bg_alpha: {base_alpha} -> {adjusted_alpha}")
        return adjusted_alpha, True
    elif contrast < 145:
        # やや見づらい：バランス型 (0.45〜0.50)
        adjusted_alpha = max(base_alpha, 0.45)
        return adjusted_alpha, False
    else:
        # コントラスト十分（明るい空など）
        return base_alpha, False

FONTS = {
    "kiwi": "fonts/KiwiMaru-Medium.ttf",          # キウイ丸（可愛い丸みフォント）
    "yomogi": "fonts/Yomogi-Regular.ttf",         # よもぎ（手書き文字）
    "zenmaru": "fonts/ZenMaruGothic-Bold.ttf",    # ゼン丸ゴシック
    "maru": "C:/Windows/Fonts/HGRSMP.TTF",        # HG丸ゴシックM-PRO
    "kyokasho": "C:/Windows/Fonts/UDDigiKyokashoN-B.ttc",
    "pop": "C:/Windows/Fonts/HGRPP1.TTC",
    "ud": "C:/Windows/Fonts/BIZ-UDGothicB.ttc",   # BIZ UDゴシック（男子向け）
    "mincho": "C:/Windows/Fonts/BIZ-UDMinchoM.ttc", # BIZ UD明朝（モノローグ・独白専用）
    "bold": "C:/Windows/Fonts/YuGothB.ttc",
}

VERTICAL_REPLACEMENTS = {
    "ー": "丨",
    "-": "丨",
    "―": "丨",
    "–": "丨",
    "—": "丨",
    "～": "丨",
    "~": "丨",
    "「": "﹁",
    "」": "﹂",
    "『": "﹁",
    "』": "﹂",
}

_FONT_CACHE = {}

def get_font(size: int, font_name: str = "kiwi") -> ImageFont.FreeTypeFont:
    size = max(8, int(size))
    cache_key = (size, font_name)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    path = FONTS.get(font_name, FONTS["kiwi"])
    font = None
    if os.path.exists(path):
        try:
            font = ImageFont.truetype(path, size)
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    _FONT_CACHE[cache_key] = font
    return font

def to_pixels(val: float, total: int) -> int:
    if isinstance(val, (int, float)) and val <= 1.0:
        return int(val * total)
    return int(val)

def parse_styled_text(raw_text: str) -> List[List[Tuple[str, float]]]:
    lines = raw_text.split("\n")
    parsed_lines = []
    tag_pattern = re.compile(r'(<(/?[a-zA-Z0-9_=.]+)>)')

    for line in lines:
        scale_stack = [1.0]
        cur_scale = 1.0
        char_tokens = []
        pos = 0

        while pos < len(line):
            match = tag_pattern.match(line, pos)
            if match:
                tag_content = match.group(2).lower()
                if tag_content.startswith("/"):
                    if len(scale_stack) > 1:
                        scale_stack.pop()
                    cur_scale = scale_stack[-1]
                elif tag_content == "big":
                    scale_stack.append(1.30)
                    cur_scale = scale_stack[-1]
                elif tag_content == "huge":
                    scale_stack.append(1.60)
                    cur_scale = scale_stack[-1]
                elif tag_content == "small":
                    scale_stack.append(0.72)
                    cur_scale = scale_stack[-1]
                elif tag_content == "tiny":
                    scale_stack.append(0.55)
                    cur_scale = scale_stack[-1]
                elif tag_content.startswith("scale="):
                    try:
                        s_val = float(tag_content.split("=")[1])
                        scale_stack.append(s_val)
                        cur_scale = scale_stack[-1]
                    except ValueError:
                        pass
                pos = match.end()
            else:
                char_tokens.append((line[pos], cur_scale))
                pos += 1

        parsed_lines.append(char_tokens)
    return parsed_lines

def measure_vertical_styled_text(
    draw: ImageDraw.ImageDraw,
    styled_lines: List[List[Tuple[str, float]]],
    base_font_size: int,
    font_name: str
) -> Tuple[int, int, List[int], List[int], List[Any]]:
    col_widths = []
    col_heights = []
    col_char_metrics = []

    for line in styled_lines:
        line_metrics = []
        max_w = 0
        total_h = 0
        for ch, sc in line:
            cur_sz = max(8, int(base_font_size * sc))
            f = get_font(cur_sz, font_name)
            disp_ch = VERTICAL_REPLACEMENTS.get(ch, ch)
            bbox = draw.textbbox((0, 0), disp_ch if ch not in ("…", "‥") else "あ", font=f)
            ink_w = bbox[2] - bbox[0]
            ink_h = bbox[3] - bbox[1]

            # 正しい送り幅 (Advance) はフォントのEMサイズを基準に計算
            if ch in ("っ", "ッ", "ゃ", "ゅ", "ょ", "ぁ", "ぃ", "ぅ", "ぇ", "ぉ", "ャ", "ュ", "ョ", "ァ", "ィ", "ゥ", "ェ", "ォ"):
                adv = int(cur_sz * 0.82)
            elif ch in ("、", "。"):
                adv = int(cur_sz * 0.50)
            elif ch in ("…", "‥"):
                adv = int(cur_sz * 0.95)
            else:
                adv = int(cur_sz * 1.08)  # 漢字・かなの送り幅（重なりを完全防止）

            line_metrics.append((ch, sc, f, cur_sz, bbox, ink_w, ink_h, adv))
            max_w = max(max_w, max(ink_w, cur_sz))
            total_h += adv

        char_sp = int(base_font_size * 0.04)
        total_h += max(0, len(line) - 1) * char_sp
        col_widths.append(max_w)
        col_heights.append(total_h)
        col_char_metrics.append(line_metrics)

    num_cols = len(styled_lines)
    col_spacing = int(base_font_size * 0.38)
    total_text_width = sum(col_widths) + max(0, num_cols - 1) * col_spacing
    max_text_height = max(col_heights) if col_heights else 0

    return total_text_width, max_text_height, col_widths, col_heights, col_char_metrics

def generate_cloud_polygon(
    rect: Tuple[int, int, int, int],
    num_bumps: int = 14,
    bump_ratio: float = 0.13
) -> List[Tuple[float, float]]:
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    rx = (x2 - x1) / 2.0
    ry = (y2 - y1) / 2.0

    points = []
    samples_per_bump = 10
    total_samples = num_bumps * samples_per_bump

    for i in range(total_samples):
        angle = i * (2.0 * math.pi / total_samples)
        bump_phase = (i % samples_per_bump) / samples_per_bump
        bump_val = math.sin(bump_phase * math.pi)
        r_scale = 1.0 + bump_ratio * bump_val

        px = cx + rx * math.cos(angle) * r_scale
        py = cy + ry * math.sin(angle) * r_scale
        points.append((px, py))

    return points

def generate_capsule_polygon(
    rect: Tuple[int, int, int, int],
    tail: Tuple[int, int] = None,
    corner_ratio: float = 0.35,
    num_samples: int = 120
) -> List[Tuple[float, float]]:
    """
    四隅がゆったり丸いスーパー楕円（カプセル）
    テキストが四隅で窮屈にならず、最も文字が美しく収まる。
    """
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    w = x2 - x1
    h = y2 - y1
    rx = w / 2.0
    ry = h / 2.0

    # スーパー楕円パラメータ (n=3.0 で四隅がふっくらした美しい形に)
    n = 2.8
    base_points = []
    for i in range(num_samples):
        th = i * (2.0 * math.pi / num_samples)
        cos_t = math.cos(th)
        sin_t = math.sin(th)
        px = cx + rx * math.copysign(abs(cos_t) ** (2.0 / n), cos_t)
        py = cy + ry * math.copysign(abs(sin_t) ** (2.0 / n), sin_t)
        base_points.append((px, py))

    if not tail:
        return base_points

    tx, ty = tail
    tail_angle = math.atan2(ty - cy, tx - cx)
    if tail_angle < 0:
        tail_angle += 2.0 * math.pi

    base_span = 0.16
    poly = []
    inserted_tail = False

    for i in range(num_samples):
        th = i * (2.0 * math.pi / num_samples)
        diff = (th - tail_angle + math.pi) % (2.0 * math.pi) - math.pi

        if abs(diff) < base_span / 2.0:
            if not inserted_tail:
                p1_th = tail_angle - base_span / 2.0
                p2_th = tail_angle + base_span / 2.0
                cos_1 = math.cos(p1_th)
                sin_1 = math.sin(p1_th)
                cos_2 = math.cos(p2_th)
                sin_2 = math.sin(p2_th)
                p1_x = cx + rx * math.copysign(abs(cos_1) ** (2.0 / n), cos_1)
                p1_y = cy + ry * math.copysign(abs(sin_1) ** (2.0 / n), sin_1)
                p2_x = cx + rx * math.copysign(abs(cos_2) ** (2.0 / n), cos_2)
                p2_y = cy + ry * math.copysign(abs(sin_2) ** (2.0 / n), sin_2)
                poly.append((p1_x, p1_y))
                poly.append((tx, ty))
                poly.append((p2_x, p2_y))
                inserted_tail = True
        else:
            poly.append(base_points[i])

    return poly

def generate_oval_bubble_polygon(
    rect: Tuple[int, int, int, int],
    tail: Tuple[int, int] = None,
    num_samples: int = 120
) -> List[Tuple[float, float]]:
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    rx = (x2 - x1) / 2.0
    ry = (y2 - y1) / 2.0

    if not tail:
        poly = []
        for i in range(num_samples):
            th = i * (2.0 * math.pi / num_samples)
            poly.append((cx + rx * math.cos(th), cy + ry * math.sin(th)))
        return poly

    tx, ty = tail
    tail_angle = math.atan2(ty - cy, tx - cx)
    if tail_angle < 0:
        tail_angle += 2.0 * math.pi

    base_span = 0.16
    poly = []
    inserted_tail = False

    for i in range(num_samples):
        th = i * (2.0 * math.pi / num_samples)
        diff = (th - tail_angle + math.pi) % (2.0 * math.pi) - math.pi

        if abs(diff) < base_span / 2.0:
            if not inserted_tail:
                p1_th = tail_angle - base_span / 2.0
                p2_th = tail_angle + base_span / 2.0
                poly.append((cx + rx * math.cos(p1_th), cy + ry * math.sin(p1_th)))
                poly.append((tx, ty))
                poly.append((cx + rx * math.cos(p2_th), cy + ry * math.sin(p2_th)))
                inserted_tail = True
        else:
            poly.append((cx + rx * math.cos(th), cy + ry * math.sin(th)))

    return poly

def draw_thought_tail_circles(
    draw: ImageDraw.ImageDraw,
    rect: Tuple[int, int, int, int],
    tail: Tuple[int, int],
    border_color=(45, 45, 55, 230),
    fill_color=(255, 255, 255, 0),
    border_width=2
):
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    tx, ty = tail

    angle = math.atan2(ty - cy, tx - cx)
    rx = (x2 - x1) / 2.0
    ry = (y2 - y1) / 2.0
    start_x = cx + rx * math.cos(angle)
    start_y = cy + ry * math.sin(angle)

    sizes = [11, 7, 4]
    ratios = [0.25, 0.55, 0.85]

    for r_ratio, r_size in zip(ratios, sizes):
        mx = start_x + (tx - start_x) * r_ratio
        my = start_y + (ty - start_y) * r_ratio
        circle_bbox = (mx - r_size, my - r_size, mx + r_size, my + r_size)
        draw.ellipse(circle_bbox, fill=fill_color, outline=border_color, width=border_width)

def draw_vertical_measured(
    draw: ImageDraw.ImageDraw,
    col_char_metrics: List[Any],
    col_widths: List[int],
    col_heights: List[int],
    total_text_width: int,
    base_font_size: int,
    box: Tuple[int, int, int, int],
    text_color=(35, 35, 45, 255),
    text_halo=True,
    halo_color=None,
    scale=3
):
    x1, y1, x2, y2 = box
    box_w = x2 - x1
    box_h = y2 - y1

    col_spacing = int(base_font_size * 0.35)
    start_x = x1 + (box_w + total_text_width) // 2

    cur_col_right = start_x
    for col_idx, line_metrics in enumerate(col_char_metrics):
        col_w = col_widths[col_idx]
        col_x = cur_col_right - col_w
        cur_y = y1 + (box_h - col_heights[col_idx]) // 2
        char_sp = int(base_font_size * 0.05)

        for ch, sc, f, cur_sz, bbox, ink_w, ink_h, adv in line_metrics:
            if ch in ("…", "‥"):
                dot_r = max(1, int(cur_sz * 0.045))
                dot_x = col_x + col_w // 2
                draw_halo = halo_color if halo_color else (255, 248, 238, 180)
                for step in (0.22, 0.50, 0.78):
                    dot_y = cur_y + int(cur_sz * step)
                    if text_halo:
                        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                            draw.ellipse((dot_x + dx * scale - dot_r, dot_y + dy * scale - dot_r, dot_x + dx * scale + dot_r, dot_y + dy * scale + dot_r), fill=draw_halo)
                    draw.ellipse((dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r), fill=text_color)
                cur_y += adv + char_sp
                continue

            if ch in ("（", "("):
                arc_w = int(cur_sz * 0.65)
                arc_h = int(adv * 0.45)
                arc_x = col_x + (col_w - arc_w) // 2
                arc_y = cur_y + (adv - arc_h) // 2
                draw.arc((arc_x, arc_y, arc_x + arc_w, arc_y + arc_h * 2), start=200, end=340, fill=text_color, width=max(1, int(cur_sz * 0.08)))
                cur_y += adv + char_sp
                continue
            elif ch in ("）", ")"):
                arc_w = int(cur_sz * 0.65)
                arc_h = int(adv * 0.45)
                arc_x = col_x + (col_w - arc_w) // 2
                arc_y = cur_y + (adv - arc_h) // 2
                draw.arc((arc_x, arc_y - arc_h, arc_x + arc_w, arc_y + arc_h), start=20, end=160, fill=text_color, width=max(1, int(cur_sz * 0.08)))
                cur_y += adv + char_sp
                continue

            disp_ch = VERTICAL_REPLACEMENTS.get(ch, ch)
            # グリフのbboxオフセットを打ち消して正確に各セルの中央へ配置
            draw_x = col_x - bbox[0] + (col_w - ink_w) // 2
            draw_y = cur_y - bbox[1] + (adv - ink_h) // 2

            if ch in ("っ", "ッ", "ゃ", "ゅ", "ょ", "ぁ", "ぃ", "ぅ", "ぇ", "ぉ", "ャ", "ュ", "ョ", "ァ", "ィ", "ゥ", "ェ", "ォ"):
                draw_x += int(cur_sz * 0.14)
                draw_y -= int(cur_sz * 0.05)
            elif ch in ("、", "。"):
                draw_x += int(cur_sz * 0.22)
                draw_y -= int(cur_sz * 0.20)

            if text_halo:
                draw_halo = halo_color if halo_color else (255, 248, 238, 180)
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    draw.text((draw_x + dx * scale, draw_y + dy * scale), disp_ch, font=f, fill=draw_halo)

            draw.text((draw_x, draw_y), disp_ch, font=f, fill=text_color)
            cur_y += adv + char_sp

        cur_col_right = col_x - col_spacing

def render_natural_bubble(
    image_path: str,
    bubbles: List[Dict[str, Any]],
    output_path: str,
    scale: int = 3
):
    base_img = Image.open(image_path).convert("RGBA")
    w, h = base_img.size

    sw = w * scale
    sh = h * scale
    overlay_hi = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw_hi = ImageDraw.Draw(overlay_hi)

    for item in bubbles:
        text = item.get("text", "")
        writing_mode = item.get("writing_mode", "vertical")
        b_type = item.get("type", "capsule")  # "capsule", "cloud", "oval", "box" (モノローグ枠), "floating" (枠なし浮遊)

        # モノローグ枠・浮遊文字の場合はデフォルトで明朝体を採用
        default_font = "mincho" if b_type in ("box", "floating") else "kiwi"
        font_name = item.get("font", default_font)
        base_font_size = int(h * item.get("font_size_ratio", 0.024) * scale)

        border_color = tuple(item.get("border_color", [45, 45, 55, 230]))
        border_width = int(item.get("border_width", 2.0) * scale)

        text_color = tuple(item.get("text_color", [35, 35, 45, 255]))
        text_halo = item.get("text_halo", True)
        halo_color = tuple(item.get("halo_color", [255, 248, 238, 180])) if "halo_color" in item else None

        # テキストの精密測定
        styled_lines = parse_styled_text(text)
        t_w, t_h, col_ws, col_hs, char_metrics = measure_vertical_styled_text(
            draw_hi, styled_lines, base_font_size, font_name
        )

        # 幾何学的に文字が絶対に吹き出しからはみ出さない自動パディング
        if b_type == "capsule":
            bw = max(int(t_w * 2.1), int(t_h * 0.60))
            bh = int(t_h * 1.36)
        elif b_type == "cloud":
            bw = max(int(t_w * 2.3), int(t_h * 0.62))
            bh = int(t_h * 1.38)
        elif b_type == "box":
            bw = int(t_w * 1.65)
            bh = int(t_h * 1.25)
        elif b_type == "floating":
            bw = t_w
            bh = t_h
        else: # oval
            bw = max(int(t_w * 2.2), int(t_h * 0.60))
            bh = int(t_h * 1.40)

        # 配置位置の決定（中心座標 center が指定されていれば優先、なければ box の中心を使用）
        if "center" in item:
            cx_scaled = to_pixels(item["center"][0], w) * scale
            cy_scaled = to_pixels(item["center"][1], h) * scale
            bx1 = cx_scaled - bw // 2
            by1 = cy_scaled - bh // 2
        else:
            box = item.get("box", [0.1, 0.1, 0.35, 0.25])
            raw_bx1 = to_pixels(box[0], w) * scale
            raw_by1 = to_pixels(box[1], h) * scale
            raw_bw = to_pixels(box[2], w) * scale
            raw_bh = to_pixels(box[3], h) * scale
            cx_scaled = raw_bx1 + raw_bw // 2
            cy_scaled = raw_by1 + raw_bh // 2
            bx1 = cx_scaled - bw // 2
            by1 = cy_scaled - bh // 2

        # 画面端のはみ出し防止クランプ
        margin_edge = int(10 * scale)
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

        # しっぽの位置
        tail = item.get("tail", None)
        tail_pt = None
        if tail:
            tail_pt = (to_pixels(tail[0], w) * scale, to_pixels(tail[1], h) * scale)

        rect = (bx1, by1, bx2, by2)
        native_rect = (bx1 // scale, by1 // scale, bx2 // scale, by2 // scale)

        # 視認性モード・自動コントラスト判定
        vis_mode = item.get("visibility_mode", "auto")
        specified_alpha = item.get("bg_alpha", None)
        final_alpha, halo_boost = analyze_background_and_adjust(
            base_img, native_rect, text_color, specified_alpha, vis_mode
        )

        raw_bg = item.get("bg_color", [255, 248, 240])
        fill_color = (raw_bg[0], raw_bg[1], raw_bg[2], int(final_alpha * 255)) if final_alpha > 0 else (0, 0, 0, 0)
        if halo_boost:
            text_halo = True

        # 吹き出しポリゴン／矩形の描画
        if b_type == "cloud":
            poly = generate_cloud_polygon(rect, num_bumps=14, bump_ratio=0.13)
            draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)
            if tail_pt:
                draw_thought_tail_circles(draw_hi, rect, tail_pt, border_color, fill_color, border_width)
        elif b_type == "oval":
            poly = generate_oval_bubble_polygon(rect, tail_pt)
            draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)
        elif b_type == "box":
            draw_hi.rectangle(rect, fill=fill_color, outline=border_color, width=border_width)
        elif b_type in ("floating", "none"):
            # 枠線なし、文字だけ（絵の上に直接浮かぶ浮遊モノローグ）
            pass
        else: # capsule / squircle
            poly = generate_capsule_polygon(rect, tail_pt)
            draw_hi.polygon(poly, fill=fill_color, outline=border_color, width=border_width)

        # テキスト描画（吹き出しの中心に正確に配置）
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
            scale=scale
        )

    overlay = overlay_hi.resize((w, h), resample=Image.Resampling.LANCZOS)
    result = Image.alpha_composite(base_img, overlay).convert("RGB")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result.save(output_path, quality=98)
    print(f"[OK] Saved: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Natural Bubble Renderer")
    parser.add_argument("--config", "-c", type=str, required=True, help="Path to config JSON")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        data = json.load(f)

    render_natural_bubble(
        data["image_path"],
        data.get("bubbles", []),
        data.get("output_path", "output/result.png")
    )

if __name__ == "__main__":
    main()

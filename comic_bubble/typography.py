"""
comic_bubble.typography
~~~~~~~~~~~~~~~~~~~~~~~
Vertical Japanese typesetting engine.
Handles EM-based font advances, micro-kerning, inline scaling tags (<big>, <small>),
vertical punctuation transformations, and mathematical arc glyph rendering.
"""

import re
from typing import List, Tuple, Any, Dict, Optional
from PIL import ImageDraw, ImageFont
from .fonts import get_font

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

def parse_styled_text(raw_text: str) -> List[List[Tuple[str, float]]]:
    """
    Parse inline styling tags such as <big>, <small>, <huge>, <tiny>, or <scale=1.5>.
    Returns a list of lines, where each line contains tuples of (character, scale_factor).
    """
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
    """
    Measure total bounding width and height for vertical Japanese text.
    Uses EM font metrics rather than ink bbox to avoid character overlap.
    """
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

            # Fixed advance metric based on EM box to guarantee zero overlap
            if ch in ("っ", "ッ", "ゃ", "ゅ", "ょ", "ぁ", "ぃ", "ぅ", "ぇ", "ぉ",
                      "ャ", "ュ", "ョ", "ァ", "ィ", "ゥ", "ェ", "ォ"):
                adv = int(cur_sz * 0.82)
            elif ch in ("、", "。"):
                adv = int(cur_sz * 0.50)
            elif ch in ("…", "‥"):
                adv = int(cur_sz * 0.95)
            else:
                adv = int(cur_sz * 1.08)

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

def draw_vertical_measured(
    draw: ImageDraw.ImageDraw,
    col_char_metrics: List[Any],
    col_widths: List[int],
    col_heights: List[int],
    total_text_width: int,
    base_font_size: int,
    box: Tuple[int, int, int, int],
    text_color: Tuple[int, int, int, int] = (35, 35, 45, 255),
    text_halo: bool = True,
    halo_color: Optional[Tuple[int, int, int, int]] = None,
    scale: int = 3
):
    """
    Render vertical Japanese text with precision micro-offsets, glyph alignment,
    halo glow, and mathematical arc bracket rendering.
    """
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
            # Ellipsis: drawn as aligned geometric dots to ensure vertical orientation
            if ch in ("…", "‥"):
                dot_r = max(1, int(cur_sz * 0.045))
                dot_x = col_x + col_w // 2
                draw_halo = halo_color if halo_color else (255, 248, 238, 180)
                for step in (0.22, 0.50, 0.78):
                    dot_y = cur_y + int(cur_sz * step)
                    if text_halo:
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            draw.ellipse(
                                (dot_x + dx * scale - dot_r, dot_y + dy * scale - dot_r,
                                 dot_x + dx * scale + dot_r, dot_y + dy * scale + dot_r),
                                fill=draw_halo
                            )
                    draw.ellipse(
                        (dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r),
                        fill=text_color
                    )
                cur_y += adv + char_sp
                continue

            # Vertical Parentheses: Rendered mathematically as arcs to prevent tofu (□)
            if ch in ("（", "("):
                arc_w = int(cur_sz * 0.65)
                arc_h = int(adv * 0.45)
                arc_x = col_x + (col_w - arc_w) // 2
                arc_y = cur_y + (adv - arc_h) // 2
                arc_bbox = (arc_x, arc_y, arc_x + arc_w, arc_y + arc_h * 2)
                arc_width = max(1, int(cur_sz * 0.08))
                if text_halo:
                    draw_halo = halo_color if halo_color else (255, 248, 238, 180)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        draw.arc(
                            (arc_bbox[0] + dx * scale, arc_bbox[1] + dy * scale,
                             arc_bbox[2] + dx * scale, arc_bbox[3] + dy * scale),
                            start=200, end=340, fill=draw_halo, width=arc_width + 1
                        )
                draw.arc(arc_bbox, start=200, end=340, fill=text_color, width=arc_width)
                cur_y += adv + char_sp
                continue
            elif ch in ("）", ")"):
                arc_w = int(cur_sz * 0.65)
                arc_h = int(adv * 0.45)
                arc_x = col_x + (col_w - arc_w) // 2
                arc_y = cur_y + (adv - arc_h) // 2
                arc_bbox = (arc_x, arc_y - arc_h, arc_x + arc_w, arc_y + arc_h)
                arc_width = max(1, int(cur_sz * 0.08))
                if text_halo:
                    draw_halo = halo_color if halo_color else (255, 248, 238, 180)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        draw.arc(
                            (arc_bbox[0] + dx * scale, arc_bbox[1] + dy * scale,
                             arc_bbox[2] + dx * scale, arc_bbox[3] + dy * scale),
                            start=20, end=160, fill=draw_halo, width=arc_width + 1
                        )
                draw.arc(arc_bbox, start=20, end=160, fill=text_color, width=arc_width)
                cur_y += adv + char_sp
                continue

            disp_ch = VERTICAL_REPLACEMENTS.get(ch, ch)
            # Offset cancellation to align glyph inside its EM cell
            draw_x = col_x - bbox[0] + (col_w - ink_w) // 2
            draw_y = cur_y - bbox[1] + (adv - ink_h) // 2

            # Micro-offsets for Japanese typography
            if ch in ("っ", "ッ", "ゃ", "ゅ", "ょ", "ぁ", "ぃ", "ぅ", "ぇ", "ぉ",
                      "ャ", "ュ", "ョ", "ァ", "ィ", "ゥ", "ェ", "ォ"):
                draw_x += int(cur_sz * 0.14)
                draw_y -= int(cur_sz * 0.05)
            elif ch in ("、", "。"):
                draw_x += int(cur_sz * 0.22)
                draw_y -= int(cur_sz * 0.20)

            # 4-direction halo glow for legibility over complex backgrounds
            if text_halo:
                draw_halo = halo_color if halo_color else (255, 248, 238, 180)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    draw.text(
                        (draw_x + dx * scale, draw_y + dy * scale),
                        disp_ch, font=f, fill=draw_halo
                    )

            draw.text((draw_x, draw_y), disp_ch, font=f, fill=text_color)
            cur_y += adv + char_sp

        cur_col_right = col_x - col_spacing


KINSOKU_HEADS = set("、。，．！？!?）)]｝}」』’\"ー―〜~…‥っッゃゅょぁぃぅぇぉャュョァィゥェォ")

def auto_wrap_japanese_text(text: str, target_chars: int = 9, max_chars: int = 12) -> str:
    """
    Wrap Japanese text into balanced vertical lines (approx 7-12 chars per column).
    Preserves existing newlines and respects inline tags like <big>, <small>.
    Applies Japanese kinsoku shori (prohibits line breaks before punctuation/small kana).
    """
    if not text:
        return text

    existing_lines = text.split("\n")
    # If all lines are already within reasonable manga vertical length, leave as is
    if all(len(re.sub(r'<[^>]+>', '', l)) <= max_chars + 1 for l in existing_lines):
        return text

    wrapped_lines: List[str] = []

    for line in existing_lines:
        clean_len = len(re.sub(r'<[^>]+>', '', line))
        if clean_len <= max_chars + 1:
            wrapped_lines.append(line)
            continue

        p_parts = [p for p in re.split(r'([、。！？!?…~～]+)', line) if p]

        sub_tokens = []
        for p in p_parts:
            if re.match(r'^[、。！？!?…~～]+$', p):
                sub_tokens.append(p)
            else:
                parts2 = [p2 for p2 in re.split(r'((?:って|から|けど|ので|のに|だが|たら|なら|[はがをにへでとのも]))', p) if p2]
                for p2 in parts2:
                    clean_p2 = re.sub(r'<[^>]+>', '', p2)
                    if len(clean_p2) > max_chars:
                        for k in range(0, len(p2), target_chars):
                            chunk = p2[k:k+target_chars]
                            if chunk:
                                sub_tokens.append(chunk)
                    else:
                        sub_tokens.append(p2)

        cur_line = ""
        for tok in sub_tokens:
            cur_clean = len(re.sub(r'<[^>]+>', '', cur_line))
            tok_clean = len(re.sub(r'<[^>]+>', '', tok))

            if not cur_line:
                cur_line = tok
                continue

            if re.match(r'^[、。！？!?…~～]+$', tok) or (tok and tok[0] in KINSOKU_HEADS):
                cur_line += tok
                continue

            if cur_clean + tok_clean <= target_chars:
                cur_line += tok
            elif cur_clean < target_chars and (cur_clean + tok_clean <= max_chars):
                cur_line += tok
            else:
                wrapped_lines.append(cur_line)
                cur_line = tok

        if cur_line:
            if wrapped_lines and len(re.sub(r'<[^>]+>', '', cur_line)) <= 2:
                prev_clean = len(re.sub(r'<[^>]+>', '', wrapped_lines[-1]))
                if prev_clean + len(cur_line) <= max_chars + 3:
                    wrapped_lines[-1] += cur_line
                else:
                    wrapped_lines.append(cur_line)
            else:
                wrapped_lines.append(cur_line)

    return "\n".join(wrapped_lines)


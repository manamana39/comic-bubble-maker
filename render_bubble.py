"""
Comic Bubble Renderer
=====================
ComfyUIなどの画像に対し、設定JSONをもとに適切な吹き出しと台詞を合成するスクリプト。
画像サイズ（解像度）に依存せず、比率 (0.0〜1.0) で指定可能です。
"""

import os
import sys
import json
import math
import argparse
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

# Windows標準フォントの候補
DEFAULT_FONT_CANDIDATES = [
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/YuGothM.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
]

def get_japanese_font(size: int, font_path: str = None) -> ImageFont.FreeTypeFont:
    """利用可能な日本語フォントを取得する"""
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    for candidate in DEFAULT_FONT_CANDIDATES:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                continue

    # フォールバック (デフォルトフォント)
    return ImageFont.load_default()

def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """テキストを指定幅に収まるよう自動折り返しする"""
    lines = []
    # 既存の改行でまず分割
    for paragraph in text.split("\n"):
        current_line = ""
        for char in paragraph:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
            if line_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
    return lines

def to_pixels(val: float, total: int) -> int:
    """0.0〜1.0 の比率、またはピクセル絶対値をピクセル値に変換"""
    if isinstance(val, (int, float)) and val <= 1.0:
        return int(val * total)
    return int(val)

def draw_normal_bubble(
    draw: ImageDraw.ImageDraw,
    rect: Tuple[int, int, int, int],
    tail: Tuple[int, int] = None,
    bg_color=(255, 255, 255, 245),
    border_color=(0, 0, 0, 255),
    border_width=3
):
    """通常の角丸/楕円吹き出しを描画"""
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    radius = min((x2 - x1), (y2 - y1)) // 4

    # しっぽを描画
    if tail:
        tx, ty = tail
        # 吹き出し中心からtail方向のベースポイントを計算
        angle = math.atan2(ty - cy, tx - cx)
        base_w = min(x2 - x1, y2 - y1) * 0.15
        p1 = (cx + math.cos(angle + 0.3) * (x2 - x1) * 0.4, cy + math.sin(angle + 0.3) * (y2 - y1) * 0.4)
        p2 = (cx + math.cos(angle - 0.3) * (x2 - x1) * 0.4, cy + math.sin(angle - 0.3) * (y2 - y1) * 0.4)
        tail_poly = [p1, (tx, ty), p2]
        draw.polygon(tail_poly, fill=bg_color, outline=border_color, width=border_width)

    # 吹き出し本体 (角丸四角形)
    draw.rounded_rectangle(rect, radius=radius, fill=bg_color, outline=border_color, width=border_width)

    # しっぽと本体の境界線を消すため再度本体の内側を少し塗りつぶす
    inner_rect = (x1 + border_width, y1 + border_width, x2 - border_width, y2 - border_width)
    draw.rounded_rectangle(inner_rect, radius=max(1, radius - border_width), fill=bg_color)

def draw_shout_bubble(
    draw: ImageDraw.ImageDraw,
    rect: Tuple[int, int, int, int],
    tail: Tuple[int, int] = None,
    bg_color=(255, 255, 255, 245),
    border_color=(0, 0, 0, 255),
    border_width=4,
    spikes: int = 18
):
    """叫び・強調（ギザギザ爆発）吹き出しを描画"""
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    rx = (x2 - x1) / 2
    ry = (y2 - y1) / 2

    points = []
    for i in range(spikes * 2):
        angle = i * (math.pi / spikes)
        # 偶数は外側、奇数は内側
        r_mult = 1.15 if i % 2 == 0 else 0.85
        px = cx + math.cos(angle) * rx * r_mult
        py = cy + math.sin(angle) * ry * r_mult
        points.append((px, py))

    # しっぽがある場合、一番近いスパイクをtailの位置まで伸ばす
    if tail:
        tx, ty = tail
        best_idx = 0
        min_dist = float("inf")
        for i, pt in enumerate(points):
            dist = (pt[0] - tx) ** 2 + (pt[1] - ty) ** 2
            if dist < min_dist:
                min_dist = dist
                best_idx = i
        points[best_idx] = (tx, ty)

    draw.polygon(points, fill=bg_color, outline=border_color, width=border_width)

def draw_thought_bubble(
    draw: ImageDraw.ImageDraw,
    rect: Tuple[int, int, int, int],
    tail: Tuple[int, int] = None,
    bg_color=(255, 255, 255, 245),
    border_color=(0, 0, 0, 255),
    border_width=3
):
    """モノローグ・思考（雲型）吹き出しを描画"""
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    w = x2 - x1
    h = y2 - y1

    # 雲の小さな丸を円周上に配置
    num_circles = 10
    circles = []
    for i in range(num_circles):
        angle = i * (2 * math.pi / num_circles)
        ox = cx + math.cos(angle) * (w * 0.4)
        oy = cy + math.sin(angle) * (h * 0.4)
        cr = min(w, h) * 0.22
        circles.append((ox - cr, oy - cr, ox + cr, oy + cr))

    # 輪郭線用に少し大きめの丸を描画
    for c in circles:
        draw.ellipse((c[0]-border_width, c[1]-border_width, c[2]+border_width, c[3]+border_width), fill=border_color)
    # 内側を塗りつぶし
    for c in circles:
        draw.ellipse(c, fill=bg_color)
    # 中心部を塗りつぶし
    draw.ellipse((cx - w*0.35, cy - h*0.35, cx + w*0.35, cy + h*0.35), fill=bg_color)

    # 思考のしっぽ（小さな丸が3つ口元に連なる）
    if tail:
        tx, ty = tail
        # 吹き出し下端からtailへ向かって3つの小さな円
        start_x = cx
        start_y = y2
        for step, r in [(0.3, min(w,h)*0.08), (0.6, min(w,h)*0.05), (0.9, min(w,h)*0.03)]:
            mx = start_x + (tx - start_x) * step
            my = start_y + (ty - start_y) * step
            draw.ellipse((mx - r - border_width, my - r - border_width, mx + r + border_width, my + r + border_width), fill=border_color)
            draw.ellipse((mx - r, my - r, mx + r, my + r), fill=bg_color)

def render_bubbles_on_image(image_path: str, bubbles: List[Dict[str, Any]], output_path: str):
    """画像に複数の吹き出しを描画して保存する"""
    base_image = Image.open(image_path).convert("RGBA")
    w, h = base_image.size

    # 吹き出し合成用レイヤー
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for item in bubbles:
        text = item.get("text", "")
        b_type = item.get("type", "normal")  # normal, shout, thought
        
        # 座標の取得 (比率またはピクセル)
        # [x, y, width, height]
        box = item.get("box", [0.1, 0.1, 0.4, 0.25])
        bx1 = to_pixels(box[0], w)
        by1 = to_pixels(box[1], h)
        bw = to_pixels(box[2], w)
        bh = to_pixels(box[3], h)
        bx2 = bx1 + bw
        by2 = by1 + bh

        # しっぽの目標点
        tail = item.get("tail", None)
        tail_pt = None
        if tail:
            tail_pt = (to_pixels(tail[0], w), to_pixels(tail[1], h))

        # スタイル・色設定
        border_width = max(2, int(h * item.get("border_width_ratio", 0.004)))
        bg_color = (255, 255, 255, int(item.get("bg_alpha", 0.95) * 255))
        border_color = (0, 0, 0, 255)
        text_color = (0, 0, 0, 255)

        # 吹き出し形状の描画
        rect = (bx1, by1, bx2, by2)
        if b_type == "shout":
            draw_shout_bubble(draw, rect, tail_pt, bg_color, border_color, border_width)
        elif b_type == "thought":
            draw_thought_bubble(draw, rect, tail_pt, bg_color, border_color, border_width)
        else:
            draw_normal_bubble(draw, rect, tail_pt, bg_color, border_color, border_width)

        # テキストのレンダリング
        font_size = int(h * item.get("font_size_ratio", 0.035))
        font = get_japanese_font(font_size, item.get("font_path"))
        
        # 内側マージン
        padding = int(min(bw, bh) * 0.15)
        max_text_width = max(20, bw - padding * 2)
        
        lines = wrap_text(text, font, max_text_width, draw)
        if not lines:
            continue

        # 行高さと全体高さの計算
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])
        
        line_spacing = int(font_size * 0.25)
        total_text_height = sum(line_heights) + line_spacing * (len(lines) - 1)

        # 吹き出し中心にテキストをセンタリング
        start_y = by1 + (bh - total_text_height) // 2
        cur_y = start_y

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            line_x = bx1 + (bw - line_w) // 2
            draw.text((line_x, cur_y), line, font=font, fill=text_color)
            cur_y += line_heights[i] + line_spacing

    # レイヤーを合成して保存
    result = Image.alpha_composite(base_image, overlay).convert("RGB")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result.save(output_path, quality=95)
    print(f"[OK] Saved generated image to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Comic Bubble Renderer")
    parser.add_argument("--config", "-c", type=str, required=True, help="Path to bubble config JSON")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    with open(args.config, "r", encoding="utf-8") as f:
        data = json.load(f)

    image_path = data.get("image_path")
    output_path = data.get("output_path", "output/result.png")
    bubbles = data.get("bubbles", [])

    if not image_path or not os.path.exists(image_path):
        print(f"Error: Target image not found: {image_path}")
        sys.exit(1)

    render_bubbles_on_image(image_path, bubbles, output_path)

if __name__ == "__main__":
    main()

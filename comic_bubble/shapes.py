"""
comic_bubble.shapes
~~~~~~~~~~~~~~~~~~~
Bubble polygon generation and speech tail geometry.
Supports capsules (squircles), clouds, ovals, boxes, and thought tail bubbles.
"""

import math
from typing import List, Tuple, Optional
from PIL import ImageDraw

def generate_capsule_polygon(
    rect: Tuple[int, int, int, int],
    tail: Optional[Tuple[int, int]] = None,
    corner_radius_ratio: float = 0.38,
    num_corner_points: int = 12
) -> List[Tuple[float, float]]:
    """
    Generate a super-ellipse capsule (squircle) polygon.
    Maximizes internal area while maintaining smooth rounded aesthetics.
    Seamlessly integrates the speech tail directly into the contour.
    """
    x1, y1, x2, y2 = rect
    bw = x2 - x1
    bh = y2 - y1
    r = min(bw, bh) * corner_radius_ratio

    # 4 corner centers
    c_tl = (x1 + r, y1 + r)
    c_tr = (x2 - r, y1 + r)
    c_br = (x2 - r, y2 - r)
    c_bl = (x1 + r, y2 - r)

    base_points = []
    # Top-Right corner: -pi/2 to 0
    for i in range(num_corner_points + 1):
        th = -math.pi / 2.0 + (math.pi / 2.0) * (i / num_corner_points)
        base_points.append((c_tr[0] + r * math.cos(th), c_tr[1] + r * math.sin(th)))
    # Bottom-Right corner: 0 to pi/2
    for i in range(num_corner_points + 1):
        th = 0.0 + (math.pi / 2.0) * (i / num_corner_points)
        base_points.append((c_br[0] + r * math.cos(th), c_br[1] + r * math.sin(th)))
    # Bottom-Left corner: pi/2 to pi
    for i in range(num_corner_points + 1):
        th = math.pi / 2.0 + (math.pi / 2.0) * (i / num_corner_points)
        base_points.append((c_bl[0] + r * math.cos(th), c_bl[1] + r * math.sin(th)))
    # Top-Left corner: pi to 3*pi/2
    for i in range(num_corner_points + 1):
        th = math.pi + (math.pi / 2.0) * (i / num_corner_points)
        base_points.append((c_tl[0] + r * math.cos(th), c_tl[1] + r * math.sin(th)))

    if not tail:
        return base_points

    # Integrate speech tail into the closest perimeter edge
    tx, ty = tail
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    tail_angle = math.atan2(ty - cy, tx - cx)

    angles = []
    for px, py in base_points:
        a = math.atan2(py - cy, px - cx)
        diff = (a - tail_angle + math.pi) % (2.0 * math.pi) - math.pi
        angles.append(diff)

    min_idx = min(range(len(angles)), key=lambda i: abs(angles[i]))
    span = max(3, int(len(base_points) * 0.055))
    i_left = (min_idx - span) % len(base_points)
    i_right = (min_idx + span) % len(base_points)

    poly = []
    inserted = False
    for i, pt in enumerate(base_points):
        if i == min_idx:
            if not inserted:
                poly.append(base_points[i_left])
                poly.append((float(tx), float(ty)))
                poly.append(base_points[i_right])
                inserted = True
        elif (i - min_idx) % len(base_points) > span and (min_idx - i) % len(base_points) > span:
            poly.append(pt)

    return poly if inserted else base_points

def generate_cloud_polygon(
    rect: Tuple[int, int, int, int],
    num_bumps: int = 14,
    bump_ratio: float = 0.13
) -> List[Tuple[float, float]]:
    """Generate a fluffy cloud polygon adapted to the text aspect ratio."""
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

def generate_oval_bubble_polygon(
    rect: Tuple[int, int, int, int],
    tail: Optional[Tuple[int, int]] = None,
    num_points: int = 72
) -> List[Tuple[float, float]]:
    """Generate a classic manga egg/oval bubble polygon."""
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    rx = (x2 - x1) / 2.0
    ry = (y2 - y1) / 2.0

    if not tail:
        return [
            (cx + rx * math.cos(i * 2.0 * math.pi / num_points),
             cy + ry * math.sin(i * 2.0 * math.pi / num_points))
            for i in range(num_points)
        ]

    tx, ty = tail
    tail_angle = math.atan2(ty - cy, tx - cx)
    poly = []
    base_span = 0.32
    inserted_tail = False

    for i in range(num_points):
        th = i * (2.0 * math.pi / num_points)
        diff = (th - tail_angle + math.pi) % (2.0 * math.pi) - math.pi

        if abs(diff) < base_span / 2.0:
            if not inserted_tail:
                p1_th = tail_angle - base_span / 2.0
                p2_th = tail_angle + base_span / 2.0
                poly.append((cx + rx * math.cos(p1_th), cy + ry * math.sin(p1_th)))
                poly.append((float(tx), float(ty)))
                poly.append((cx + rx * math.cos(p2_th), cy + ry * math.sin(p2_th)))
                inserted_tail = True
        else:
            poly.append((cx + rx * math.cos(th), cy + ry * math.sin(th)))

    return poly

def draw_thought_tail_circles(
    draw: ImageDraw.ImageDraw,
    rect: Tuple[int, int, int, int],
    tail: Tuple[int, int],
    border_color: Tuple[int, int, int, int] = (45, 45, 55, 230),
    fill_color: Tuple[int, int, int, int] = (255, 255, 255, 0),
    border_width: int = 2
):
    """Draw trailing thought circles connecting a cloud bubble to a thinker."""
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

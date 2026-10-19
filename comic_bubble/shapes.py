"""
comic_bubble.shapes
~~~~~~~~~~~~~~~~~~~
Bubble polygon generation and speech tail geometry.
Supports capsules (squircles), clouds, ovals, boxes, and thought tail bubbles.
"""

import math
from typing import List, Tuple, Optional
from PIL import ImageDraw

# Tail base width as a ratio of the bubble's short side (smaller = slimmer tail)
TAIL_BASE_RATIO = 0.22

def anchor_to_math_angle(anchor_deg: float) -> float:
    """Convert a tail anchor angle (0=up, clockwise, degrees) to an atan2 angle (y-down coords)."""
    a = math.radians(anchor_deg)
    return math.atan2(-math.cos(a), math.sin(a))

def generate_capsule_polygon(
    rect: Tuple[int, int, int, int],
    tail: Optional[Tuple[int, int]] = None,
    corner_radius_ratio: float = 0.38,
    num_corner_points: int = 12,
    anchor_deg: Optional[float] = None
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
    tail_angle = anchor_to_math_angle(anchor_deg) if anchor_deg is not None else math.atan2(ty - cy, tx - cx)

    angles = []
    for px, py in base_points:
        a = math.atan2(py - cy, px - cx)
        diff = (a - tail_angle + math.pi) % (2.0 * math.pi) - math.pi
        angles.append(diff)

    min_idx = min(range(len(angles)), key=lambda i: abs(angles[i]))

    # Slim tail: base width is a fixed arc length along the outline
    # (independent of tail length), so long tails stay thin.
    n = len(base_points)
    seg = []
    for i in range(n):
        p, q = base_points[i], base_points[(i + 1) % n]
        seg.append(math.hypot(q[0] - p[0], q[1] - p[1]))
    perimeter = sum(seg)
    cum = [0.0]
    for s in seg:
        cum.append(cum[-1] + s)

    def point_at(s: float) -> Tuple[float, float]:
        s %= perimeter
        for i in range(n):
            if s <= cum[i + 1]:
                t = (s - cum[i]) / seg[i] if seg[i] > 0 else 0.0
                p, q = base_points[i], base_points[(i + 1) % n]
                return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
        return base_points[0]

    half_base = max(4.0, min(bw, bh) * TAIL_BASE_RATIO / 2.0)
    s_end = cum[min_idx] + half_base
    open_len = perimeter - 2.0 * half_base

    poly = [point_at(cum[min_idx] - half_base), (float(tx), float(ty)), point_at(s_end)]
    rest = []
    for k in range(n):
        d = (cum[k] - s_end) % perimeter
        if 0.0 < d < open_len:
            rest.append((d, base_points[k]))
    rest.sort(key=lambda e: e[0])
    poly.extend(p for _, p in rest)
    return poly

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
    num_points: int = 72,
    anchor_deg: Optional[float] = None
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
    tail_angle = anchor_to_math_angle(anchor_deg) if anchor_deg is not None else math.atan2(ty - cy, tx - cx)
    poly = []
    base_span = 0.18
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

def generate_scream_polygon(
    rect: Tuple[int, int, int, int],
    tail: Optional[Tuple[int, int]] = None,
    num_spikes: int = 18,
    depth_ratio: float = 0.28
) -> List[Tuple[float, float]]:
    """
    Generate an intense spiky scream / explosion balloon polygon (ウニフラ・叫び吹き出し).
    Creates dramatic starburst spikes with optional directional tail spike.
    """
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    rx = (x2 - x1) / 2.0
    ry = (y2 - y1) / 2.0

    poly = []
    total_pts = num_spikes * 2

    tail_angle = None
    if tail:
        tx, ty = tail
        tail_angle = math.atan2(ty - cy, tx - cx)

    best_spike_idx = None
    best_diff = 999.0

    for i in range(total_pts):
        angle = i * (2.0 * math.pi / total_pts)
        if i % 2 == 1 and tail_angle is not None:
            diff = abs((angle - tail_angle + math.pi) % (2.0 * math.pi) - math.pi)
            if diff < best_diff:
                best_diff = diff
                best_spike_idx = i

    for i in range(total_pts):
        angle = i * (2.0 * math.pi / total_pts)
        if i == best_spike_idx and tail is not None:
            # Directional explosion tail pointing towards character
            poly.append((float(tail[0]), float(tail[1])))
        elif i % 2 == 1:
            r_scale = 1.0 + depth_ratio
            px = cx + rx * math.cos(angle) * r_scale
            py = cy + ry * math.sin(angle) * r_scale
            poly.append((px, py))
        else:
            r_scale = 1.0 - depth_ratio * 0.45
            px = cx + rx * math.cos(angle) * r_scale
            py = cy + ry * math.sin(angle) * r_scale
            poly.append((px, py))

    return poly

def draw_dashed_polygon(
    draw: ImageDraw.ImageDraw,
    points: List[Tuple[float, float]],
    fill: Optional[Tuple[int, int, int, int]] = None,
    outline: Tuple[int, int, int, int] = (50, 50, 50, 255),
    width: int = 2,
    dash_len: int = 14,
    gap_len: int = 9
):
    """
    Draw a polygon with dashed / dotted perimeter (囁き・ヒソヒソ吹き出し).
    """
    if fill:
        draw.polygon(points, fill=fill)
    if not outline or width <= 0:
        return

    num_pts = len(points)
    for i in range(num_pts):
        p1 = points[i]
        p2 = points[(i + 1) % num_pts]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            continue
        ux = dx / dist
        uy = dy / dist

        cur = 0.0
        while cur < dist:
            seg_end = min(cur + dash_len, dist)
            sp1 = (p1[0] + ux * cur, p1[1] + uy * cur)
            sp2 = (p1[0] + ux * seg_end, p1[1] + uy * seg_end)
            draw.line([sp1, sp2], fill=outline, width=width)
            cur += dash_len + gap_len


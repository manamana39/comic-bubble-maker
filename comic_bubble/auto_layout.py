"""
comic_bubble.auto_layout
~~~~~~~~~~~~~~~~~~~~~~~~
Automated bubble placement engine using background edge and detail analysis.
Detects low-frequency negative space (open skies, plain walls, flat floors)
to position bubbles without obscuring detailed character faces and bodies.
"""

from typing import Tuple
import numpy as np
from PIL import Image

def find_safe_background_center(
    base_img: Image.Image,
    target_bw: int,
    target_bh: int,
    preferred_corner: str = "top-left"
) -> Tuple[float, float]:
    """
    Find the optimal (x, y) center coordinate for a bubble by scoring regions
    based on low edge variance (empty background) and avoiding character centers.

    Returns:
        (center_x_ratio, center_y_ratio) in range [0.0..1.0]
    """
    w, h = base_img.size
    grid_sz = 128
    thumb = base_img.resize((grid_sz, grid_sz), Image.Resampling.BILINEAR).convert("L")
    arr = np.array(thumb, dtype=np.float32)

    # Compute gradient magnitude (edge density)
    grad_y = np.abs(arr[1:, :] - arr[:-1, :])
    grad_x = np.abs(arr[:, 1:] - arr[:, :-1])
    edge_map = np.zeros_like(arr)
    edge_map[:-1, :] += grad_y
    edge_map[:, :-1] += grad_x

    # Normalized bubble size on the grid
    gw = max(12, int((target_bw / w) * grid_sz))
    gh = max(16, int((target_bh / h) * grid_sz))

    # Candidate evaluation
    best_score = float("inf")
    best_cx = 0.20
    best_cy = 0.20

    # Step across grid
    for gy in range(8, grid_sz - gh - 8, 4):
        for gx in range(8, grid_sz - gw - 8, 4):
            region_edges = edge_map[gy:gy+gh, gx:gx+gw]
            edge_score = float(np.mean(region_edges))

            # Penalty for being in the dead center (where main character faces usually are)
            norm_cx = (gx + gw / 2.0) / grid_sz
            norm_cy = (gy + gh / 2.0) / grid_sz
            dist_to_center = np.hypot(norm_cx - 0.5, norm_cy - 0.45)
            center_penalty = max(0.0, 1.0 - dist_to_center * 2.0) * 35.0

            total_score = edge_score + center_penalty

            if total_score < best_score:
                best_score = total_score
                best_cx = norm_cx
                best_cy = norm_cy

    return float(best_cx), float(best_cy)

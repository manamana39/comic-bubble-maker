"""
comic_bubble.contrast
~~~~~~~~~~~~~~~~~~~~~
Background luminance sampling and Auto-Contrast visual protection engine.
Automatically ensures text legibility over any background (night skies, complex patterns, bright sunlight).
"""

from typing import Tuple, Optional
from PIL import Image, ImageStat

def get_luminance(rgb: Tuple[int, int, int]) -> float:
    """Calculate perceived relative luminance (Rec. 601, 0.0 to 255.0)."""
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

def analyze_background_and_adjust(
    base_img: Image.Image,
    rect: Tuple[int, int, int, int],
    text_color: Tuple[int, int, int, int],
    specified_alpha: Optional[float] = None,
    mode: str = "auto"
) -> Tuple[float, bool]:
    """
    Sample average background luminance in the bubble's target rectangle.
    If the text color is too close to the background luminance, automatically
    boosts the bubble opacity and halo glow to guarantee text readability.

    Returns:
        (adjusted_alpha, halo_boosted)
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

    # Low contrast threshold: text would blend dangerously into background
    if contrast < 110:
        adjusted_alpha = max(base_alpha, 0.80)
        return adjusted_alpha, True
    elif contrast < 145:
        adjusted_alpha = max(base_alpha, 0.45)
        return adjusted_alpha, False
    else:
        return base_alpha, False

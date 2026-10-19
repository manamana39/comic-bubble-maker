"""
comic_bubble.effects
~~~~~~~~~~~~~~~~~~~~
Text effects shared by the engine (export) and the GUI renderer (preview):
drop shadow and deformation (horizontal/vertical stretch + shear/italic).
"""

import math
from typing import Tuple

from PIL import Image, ImageFilter


def has_text_fx(cfg) -> bool:
    """True if the bubble uses any shadow / deformation effect."""
    return bool(
        cfg.text_shadow
        or abs(cfg.text_scale_x - 1.0) > 1e-3
        or abs(cfg.text_scale_y - 1.0) > 1e-3
        or abs(cfg.text_skew) > 1e-3
    )


def _deform(layer: Image.Image, sx: float, sy: float, skew_deg: float) -> Image.Image:
    """Stretch and shear a transparent text layer around its center (output grows to fit)."""
    k = math.tan(math.radians(max(-60.0, min(60.0, skew_deg))))
    w, h = layer.size
    nw = max(1, int(math.ceil(w * sx + abs(k) * h * sy)))
    nh = max(1, int(math.ceil(h * sy)))
    cx, cy = nw / 2.0, nh / 2.0
    a = 1.0 / sx
    b = -k / sx
    c = w / 2.0 - a * cx - b * cy
    e = 1.0 / sy
    f = h / 2.0 - e * cy
    return layer.transform((nw, nh), Image.Transform.AFFINE, (a, b, c, 0.0, e, f), resample=Image.Resampling.BICUBIC)


def _shadow(layer: Image.Image, color: Tuple[int, ...], offset: float, blur: float) -> Image.Image:
    """Add a blurred drop shadow below the layer (padded symmetrically so the center is preserved)."""
    pad = int(math.ceil(offset * 1.5 + blur * 3.0)) + 2
    w, h = layer.size
    big = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    big.paste(layer, (pad, pad))

    alpha = big.getchannel("A")
    sh_alpha = alpha
    if len(color) > 3:
        sh_alpha = alpha.point(lambda v: v * color[3] // 255)
    shadow = Image.new("RGBA", big.size, (color[0], color[1], color[2], 0))
    shadow.putalpha(sh_alpha)
    d = int(round(offset))
    shifted = Image.new("RGBA", big.size, (0, 0, 0, 0))
    shifted.paste(shadow, (d, d))
    if blur > 0.1:
        shifted = shifted.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(shifted, big)


def apply_text_fx(layer: Image.Image, cfg, scale: int) -> Image.Image:
    """Apply deformation then shadow to a text layer. `scale` is the supersampling factor."""
    out = layer
    if (abs(cfg.text_scale_x - 1.0) > 1e-3 or abs(cfg.text_scale_y - 1.0) > 1e-3
            or abs(cfg.text_skew) > 1e-3):
        out = _deform(out, max(0.2, cfg.text_scale_x), max(0.2, cfg.text_scale_y), cfg.text_skew)
    if cfg.text_shadow:
        out = _shadow(out, cfg.shadow_color, cfg.shadow_offset * scale, cfg.shadow_blur * scale)
    return out


def composite_centered(dst: Image.Image, src: Image.Image, cx: int, cy: int) -> None:
    """Alpha-composite src onto dst centered at (cx, cy), clipping anything outside dst."""
    x0 = cx - src.width // 2
    y0 = cy - src.height // 2
    sx0, sy0 = max(0, -x0), max(0, -y0)
    sx1 = min(src.width, dst.width - x0)
    sy1 = min(src.height, dst.height - y0)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    crop = src.crop((sx0, sy0, sx1, sy1))
    dx, dy = x0 + sx0, y0 + sy0
    region = dst.crop((dx, dy, dx + crop.width, dy + crop.height))
    dst.paste(Image.alpha_composite(region, crop), (dx, dy))

"""
comic_bubble.fonts
~~~~~~~~~~~~~~~~~~
Cross-platform font discovery, resolution, and caching.
Supports Windows, macOS, Linux, and custom local font directories.
"""

import os
import sys
from typing import Dict, Tuple, Optional, List
from PIL import ImageFont

# Well-known font aliases mapped to priority search lists
FONT_CANDIDATES: Dict[str, List[str]] = {
    # Cute rounded fonts (Ideal for girls / cute expressions)
    "kiwi": [
        "fonts/KiwiMaru-Medium.ttf",
        os.path.join(os.path.dirname(__file__), "..", "fonts", "KiwiMaru-Medium.ttf"),
        "C:/Windows/Fonts/HGRSMP.TTF",  # HG丸ゴシックM-PRO
        "C:/Windows/Fonts/UDDigiKyokashoN-B.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ],
    "yomogi": [
        "fonts/Yomogi-Regular.ttf",
        os.path.join(os.path.dirname(__file__), "..", "fonts", "Yomogi-Regular.ttf"),
        "C:/Windows/Fonts/HGRPP1.TTC",  # HG創英ポップ体
        "C:/Windows/Fonts/UDDigiKyokashoN-R.ttc",
    ],
    "zenmaru": [
        "fonts/ZenMaruGothic-Bold.ttf",
        os.path.join(os.path.dirname(__file__), "..", "fonts", "ZenMaruGothic-Bold.ttf"),
        "C:/Windows/Fonts/HGRSMP.TTF",
    ],
    # Serious / Shonen / Boy fonts (Solid UD Gothic)
    "ud": [
        "C:/Windows/Fonts/BIZ-UDGothicB.ttc",
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/meiryob.ttc",
        "fonts/ZenMaruGothic-Bold.ttf",
        "/System/Library/Fonts/Hiragino Sans W6.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ],
    "bold": [
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/BIZ-UDGothicB.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "/System/Library/Fonts/Hiragino Sans W7.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    ],
    # Monologue / Narrative / Inner Thought fonts (Serif / Mincho)
    "mincho": [
        "C:/Windows/Fonts/BIZ-UDMinchoM.ttc",
        "C:/Windows/Fonts/yumin.ttf",
        "C:/Windows/Fonts/msmincho.ttc",
        "/System/Library/Fonts/Hiragino Mincho ProN.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    ],
}

_FONT_CACHE: Dict[Tuple[int, str], ImageFont.FreeTypeFont] = {}

def resolve_font_path(font_name: str) -> Optional[str]:
    """Find the first existing font file for the given font alias or path."""
    # Direct file path check
    if os.path.exists(font_name):
        return font_name

    candidates = FONT_CANDIDATES.get(font_name.lower(), [])
    for path in candidates:
        if os.path.exists(path):
            return path

    # Fallback to any available system font
    fallback_pool = [
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msmincho.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in fallback_pool:
        if os.path.exists(path):
            return path

    return None

def get_font(size: int, font_name: str = "kiwi") -> ImageFont.FreeTypeFont:
    """Retrieve a cached FreeType font object of the requested size."""
    size = max(8, int(size))
    cache_key = (size, font_name)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    resolved_path = resolve_font_path(font_name)
    font = None
    if resolved_path:
        try:
            font = ImageFont.truetype(resolved_path, size)
        except Exception:
            font = None

    if font is None:
        font = ImageFont.load_default()

    _FONT_CACHE[cache_key] = font
    return font

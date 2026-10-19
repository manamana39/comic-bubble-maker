"""
comic_bubble.models
~~~~~~~~~~~~~~~~~~~
Data structures and configuration schemas for the Comic Bubble engine.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Union

@dataclass
class BubbleConfig:
    """Configuration for an individual speech bubble or monologue."""
    text: str
    type: str = "capsule"  # 'capsule', 'cloud', 'whisper', 'scream', 'oval', 'box', 'floating', 'none', 'sfx'
    writing_mode: str = "vertical"  # 'vertical' or 'horizontal'
    font: str = "kiwi"  # 'kiwi', 'yomogi', 'zenmaru', 'mincho', 'ud', 'maru', 'pop', etc.
    center: Optional[Tuple[float, float]] = None  # (x, y) normalized [0.0, 1.0] or pixel
    box: Optional[Tuple[float, float, float, float]] = None  # (x, y, w, h)
    tail: Optional[Tuple[float, float]] = None  # Target point (x, y) for speech tail
    tail_anchor: Optional[float] = None  # Where the tail leaves the bubble: degrees (0=top, clockwise). None = auto (toward tip)
    font_size_ratio: float = 0.022  # Base font size as ratio of image height
    border_width: float = 2.0
    border_color: Tuple[int, int, int, int] = (50, 45, 60, 220)
    text_color: Tuple[int, int, int, int] = (40, 35, 55, 255)
    bg_color: Tuple[int, int, int] = (255, 248, 242)
    bg_alpha: Optional[float] = None  # If None and mode='auto', calculated automatically
    visibility_mode: str = "auto"  # 'auto', 'transparent', 'balanced', 'solid'
    text_halo: bool = True
    halo_color: Optional[Tuple[int, int, int, int]] = None
    padding_ratio_x: Optional[float] = None
    padding_ratio_y: Optional[float] = None
    angle: float = 0.0  # Rotation angle in degrees (primarily for 'sfx' onomatopoeia)
    stroke_width: float = 3.0  # Outer text stroke width (for 'sfx')
    stroke_color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    text_shadow: bool = False  # Drop shadow under the text
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 170)
    shadow_offset: float = 3.0  # Shadow distance in px (diagonal down-right)
    shadow_blur: float = 2.0  # Shadow blur radius in px
    text_scale_x: float = 1.0  # Horizontal text stretch (1.0 = none)
    text_scale_y: float = 1.0  # Vertical text stretch (1.0 = none)
    text_skew: float = 0.0  # Shear / italic angle in degrees
    reading_direction: str = "rtl"  # Column progression: 'rtl' (right-to-left, standard Japanese) or 'ltr' (left-to-right)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BubbleConfig":
        b_type = data.get("type", "capsule").lower()
        if b_type == "monologue":
            # "monologue" defaults to borderless floating text
            b_type = "floating"
        elif b_type == "burst":
            b_type = "scream"
        elif b_type == "onomatopoeia":
            b_type = "sfx"

        default_font = "mincho" if b_type in ("floating", "box") else ("bold" if b_type == "sfx" else "kiwi")
        font = data.get("font", default_font)

        center_raw = data.get("center", None)
        center = None
        if isinstance(center_raw, (list, tuple)):
            center = (float(center_raw[0]), float(center_raw[1]))
        elif isinstance(center_raw, str):
            center = center_raw.lower()  # e.g. "auto"

        box = tuple(data["box"]) if "box" in data and data["box"] is not None else None
        tail = tuple(data["tail"]) if "tail" in data and data["tail"] is not None else None

        border_color = tuple(data.get("border_color", [50, 45, 60, 220]))
        text_color = tuple(data.get("text_color", [40, 35, 55, 255]))
        bg_color = tuple(data.get("bg_color", [255, 248, 242]))
        halo_color = tuple(data["halo_color"]) if "halo_color" in data and data["halo_color"] is not None else None
        stroke_color = tuple(data.get("stroke_color", [255, 255, 255, 255]))

        return cls(
            text=data.get("text", ""),
            type=b_type,
            writing_mode=data.get("writing_mode", "vertical"),
            font=font,
            center=center,
            box=box,
            tail=tail,
            tail_anchor=float(data["tail_anchor"]) if data.get("tail_anchor") is not None else None,
            font_size_ratio=float(data.get("font_size_ratio", 0.022)),
            border_width=float(data.get("border_width", 2.0)),
            border_color=border_color,
            text_color=text_color,
            bg_color=bg_color,
            bg_alpha=float(data["bg_alpha"]) if "bg_alpha" in data and data["bg_alpha"] is not None else None,
            visibility_mode=data.get("visibility_mode", "auto"),
            text_halo=bool(data.get("text_halo", True)),
            halo_color=halo_color,
            padding_ratio_x=float(data["padding_ratio_x"]) if data.get("padding_ratio_x") is not None else None,
            padding_ratio_y=float(data["padding_ratio_y"]) if data.get("padding_ratio_y") is not None else None,
            angle=float(data.get("angle", 0.0)),
            stroke_width=float(data.get("stroke_width", 3.0)),
            stroke_color=stroke_color,
            text_shadow=bool(data.get("text_shadow", False)),
            shadow_color=tuple(data.get("shadow_color", [0, 0, 0, 170])),
            shadow_offset=float(data.get("shadow_offset", 3.0)),
            shadow_blur=float(data.get("shadow_blur", 2.0)),
            text_scale_x=float(data.get("text_scale_x", 1.0)),
            text_scale_y=float(data.get("text_scale_y", 1.0)),
            text_skew=float(data.get("text_skew", 0.0)),
            reading_direction=str(data.get("reading_direction", "rtl")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert BubbleConfig to dictionary representation."""
        import dataclasses
        return dataclasses.asdict(self)

@dataclass
class SceneConfig:
    """Full scene configuration containing base image path and bubble list."""
    image_path: str
    bubbles: List[BubbleConfig] = field(default_factory=list)
    output_path: str = "output/result.png"
    supersample_scale: int = 3

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneConfig":
        raw_bubbles = data.get("bubbles", [])
        bubbles = [BubbleConfig.from_dict(b) if isinstance(b, dict) else b for b in raw_bubbles]
        return cls(
            image_path=data["image_path"],
            bubbles=bubbles,
            output_path=data.get("output_path", "output/result.png"),
            supersample_scale=int(data.get("supersample_scale", 3))
        )

"""
Comic Bubble Engine
~~~~~~~~~~~~~~~~~~~
Intelligent manga speech bubble and floating monologue renderer.
Features Auto-Fit typography, Auto-Contrast visual protection, and zero-interference layout.
"""

__version__ = "1.0.0"

from .models import BubbleConfig, SceneConfig
from .engine import render_scene, render_from_file
from .contrast import analyze_background_and_adjust, get_luminance
from .fonts import get_font, resolve_font_path

__all__ = [
    "render_scene",
    "render_from_file",
    "BubbleConfig",
    "SceneConfig",
    "analyze_background_and_adjust",
    "get_luminance",
    "get_font",
    "resolve_font_path",
]

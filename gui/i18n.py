"""
gui.i18n
~~~~~~~~
Lightweight internationalization (i18n) helper for Comic Bubble Maker.
Provides quick runtime toggling between Japanese ('ja') and English ('en').
"""

from typing import Callable, List
from comic_bubble.config import load_config, save_config

_listeners: List[Callable[[], None]] = []


def get_current_language() -> str:
    """Return the currently configured language ('ja' or 'en')."""
    cfg = load_config()
    return cfg.get("ui_language", "ja")


def set_current_language(lang: str):
    """Set and persist the UI language, then notify all registered listeners."""
    target_lang = "en" if lang == "en" else "ja"
    cfg = load_config()
    cfg["ui_language"] = target_lang
    save_config(cfg)
    for listener in list(_listeners):
        try:
            listener()
        except Exception:
            pass


def register_language_listener(callback: Callable[[], None]):
    """Register a callback to be notified when UI language changes."""
    if callback not in _listeners:
        _listeners.append(callback)


def unregister_language_listener(callback: Callable[[], None]):
    """Unregister a language change callback."""
    if callback in _listeners:
        _listeners.remove(callback)


def tr(ja: str, en: str) -> str:
    """Return either Japanese or English text based on active language."""
    return en if get_current_language() == "en" else ja

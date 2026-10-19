"""
comic_bubble.config
~~~~~~~~~~~~~~~~~~~
Configuration management for AI providers:
- Google Gemini API
- OpenAI-compatible Cloud APIs (OpenAI, DeepSeek, Groq, OpenRouter, etc.)
- Local LLMs (Ollama, LM Studio, LocalAI)
"""

import os
import json
from typing import Dict, Any, Optional

CONFIG_FILE = os.path.expanduser("~/.comic_bubble_config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "active_provider": "gemini",
    "gemini": {
        "api_key": "",
        "model": "gemini-3.8-flash"
    },
    "openai_compatible": {
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini"
    },
    "local_ollama": {
        "api_key": "lm-studio",
        "base_url": "http://localhost:1234/v1",
        "model": "qwen3-vl-8b-nsfw-caption-v4.5"
    },
    "ui_language": "ja"
}


def load_config() -> Dict[str, Any]:
    """Load configuration dictionary from disk, merging with defaults."""
    import copy
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_data = json.load(f)
                # Deep merge top-level keys
                for k, v in user_data.items():
                    if isinstance(v, dict) and k in cfg and isinstance(cfg[k], dict):
                        cfg[k].update(v)
                    else:
                        cfg[k] = v
        except Exception as e:
            print(f"Warning: Failed to read {CONFIG_FILE}: {e}")

    # Auto-migrate deprecated models or label-suffixed strings to gemini-3.8-flash
    g_model = cfg.get("gemini", {}).get("model", "").strip()
    if " " in g_model:
        g_model = g_model.split()[0].strip()
        cfg["gemini"]["model"] = g_model
        save_config(cfg)
    if (
        not g_model
        or g_model.startswith("gemini-1.5")
        or g_model.startswith("gemini-2.0")
        or g_model.startswith("gemini-2.5")
    ):
        cfg["gemini"]["model"] = "gemini-3.8-flash"
        save_config(cfg)

    # Auto-migrate old default Ollama placeholder to LM Studio OpenAI-compatible default
    local_cfg = cfg.get("local_ollama", {})
    if local_cfg.get("base_url") == "http://localhost:11434" and local_cfg.get("model") == "qwen2.5-vl:7b":
        cfg["local_ollama"]["base_url"] = "http://localhost:1234/v1"
        cfg["local_ollama"]["model"] = "qwen3-vl-8b-nsfw-caption-v4.5"
        cfg["local_ollama"].setdefault("api_key", "lm-studio")
        save_config(cfg)

    # Legacy migration: check top-level gemini_api_key
    legacy_key = cfg.get("gemini_api_key", "").strip()
    if legacy_key and not cfg["gemini"]["api_key"]:
        cfg["gemini"]["api_key"] = legacy_key
        save_config(cfg)

    # Fallback to environment variables if keys are empty
    if not cfg["gemini"]["api_key"]:
        env_gemini = os.environ.get("GEMINI_API_KEY", "").strip()
        if env_gemini:
            cfg["gemini"]["api_key"] = env_gemini
            save_config(cfg)

    if not cfg["openai_compatible"]["api_key"]:
        env_openai = os.environ.get("OPENAI_API_KEY", "").strip()
        if env_openai:
            cfg["openai_compatible"]["api_key"] = env_openai

    return cfg


def save_config(cfg: Dict[str, Any]):
    """Save configuration dictionary to ~/.comic_bubble_config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error: Failed to write {CONFIG_FILE}: {e}")

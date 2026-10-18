"""
comic_bubble.ai_generator
~~~~~~~~~~~~~~~~~~~~~~~~~
Multi-provider AI dialogue and bubble generation engine.
Supports:
1. Google Gemini API (gemini-2.0-flash, gemini-1.5-flash)
2. OpenAI-compatible Cloud APIs (OpenAI, DeepSeek, Groq, OpenRouter)
3. Local Vision LLMs via Ollama / LM Studio (Qwen2.5-VL, LLaVA, MiniCPM-V)
"""

import os
import io
import json
import base64
import requests
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image
from pydantic import BaseModel, Field

from .models import BubbleConfig
from .config import load_config, save_config


class AIBubbleItem(BaseModel):
    text: str = Field(
        description="キャラクターのセリフ、心の声、またはオノマトペ。縦書きに最適な自然な改行（\\n）を含む。強調は<big>セリフ</big>、小声は<small>セリフ</small>を使用可能。"
    )
    type: str = Field(
        description="吹き出しの形状: 'capsule' (標準セリフ), 'cloud' (楽しい・自撮り・思考), 'whisper' (囁き・点線), 'scream' (叫び・ツッコミ), 'floating' (枠なし心の声・モノローグ), 'sfx' (オノマトペ・描き文字)"
    )
    center_x: float = Field(
        description="吹き出し中心X座標 (0.0=左端, 1.0=右端)。キャラクターの顔や髪・手足を絶対に隠さない安全な背景の余白領域を指定すること。"
    )
    center_y: float = Field(
        description="吹き出し中心Y座標 (0.0=上端, 1.0=下端)。キャラクターの顔や髪・手足を絶対に隠さない安全な背景の余白領域を指定すること。"
    )
    has_tail: bool = Field(
        description="しっぽの有無。floatingやsfxの場合はFalse、発言セリフの場合はTrue。"
    )
    tail_x: Optional[float] = Field(
        None,
        description="しっぽ先端のX座標 (0.0〜1.0)。発言者の口元または首元へ向け、他のキャラクターの顔を絶対に横切らないこと。"
    )
    tail_y: Optional[float] = Field(
        None,
        description="しっぽ先端のY座標 (0.0〜1.0)。"
    )
    font: str = Field(
        "kiwi",
        description="推奨フォント: 'kiwi' (手書き風), 'zenmaru' (丸ゴシック), 'mincho' (明朝・モノローグ), 'bold' (太字・SFX)"
    )
    angle: Optional[float] = Field(
        0.0,
        description="オノマトペ(sfx)の場合の回転角度 (度数法, 例: -10.0)"
    )


class AISceneResult(BaseModel):
    scene_description: str = Field(description="画像から読み取ったシチュエーションや登場人物の感情・関係性の説明")
    bubbles: List[AIBubbleItem] = Field(description="生成された吹き出し・モノローグ・オノマトペのリスト (通常1〜3個)")


SYSTEM_INSTRUCTION = """あなたはプロの漫画原作者兼レタリング編集者です。
入力されたイラスト画像を詳細に観察し、以下のルールに従って最高に魅力的なセリフ・吹き出しを作成してください。

【セリフ演出のルール】
1. キャラクターの表情、視線、赤面、手の仕草、背景シチュエーションから心情を敏感に読み取ること。
2. 単なるセリフだけでなく、「枠なし浮遊モノローグ（floating: 心の声・独白）」や「オノマトペ（sfx: ドキッ、パシャッ、ヒソ…）」を効果的に組み合わせること。
3. 日本語の漫画表現として自然でエモーショナルな言葉選びにすること。

【レイアウト・Zero Interference の絶対ルール】
1. 【顔被りゼロ】: 吹き出し（center_x, center_y）はキャラクターの顔、髪、目、身体を絶対に隠さない背景の空きスペース（空、窓、壁、カーテンなど）に配置すること。
2. 【しっぽの横切り禁止】: しっぽ（tail_x, tail_y）を発言者に向ける際、他のキャラクターの顔や髪を絶対に横切ってはならない。
3. モノローグ（floating）やオノマトペ（sfx）はしっぽ不要（has_tail: False）。

必ず以下のJSONフォーマットのみで出力してください:
{
  "scene_description": "シーン説明",
  "bubbles": [
    {
      "text": "セリフ内容",
      "type": "capsule",
      "center_x": 0.8,
      "center_y": 0.2,
      "has_tail": true,
      "tail_x": 0.65,
      "tail_y": 0.3,
      "font": "kiwi",
      "angle": 0.0
    }
  ]
}
"""

def _pil_to_base64_jpeg(image: Image.Image, max_dim: int = 1024, quality: int = 85) -> str:
    """Resize image if needed and convert to Base64 JPEG string."""
    img = image.convert("RGB")
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _parse_bubbles_json(data: Dict[str, Any]) -> Tuple[str, List[BubbleConfig]]:
    """Parse raw JSON dict into BubbleConfig list."""
    scene_desc = data.get("scene_description", "")
    raw_bubbles = data.get("bubbles", [])

    bubble_configs: List[BubbleConfig] = []
    for b in raw_bubbles:
        b_type = b.get("type", "capsule").lower()
        cx = float(b.get("center_x", 0.5))
        cy = float(b.get("center_y", 0.3))

        tail = None
        if b.get("has_tail") and b.get("tail_x") is not None and b.get("tail_y") is not None:
            tail = (float(b["tail_x"]), float(b["tail_y"]))

        text_color = (45, 35, 55, 255)
        bg_color = (255, 250, 245)
        text_halo = True
        halo_color = None
        angle = float(b.get("angle", 0.0))

        if b_type == "floating":
            text_color = (255, 255, 255, 255)
            halo_color = (30, 35, 50, 220)
        elif b_type == "sfx":
            text_color = (255, 90, 110, 255)

        cfg = BubbleConfig(
            text=b.get("text", ""),
            type=b_type,
            font=b.get("font", "kiwi"),
            center=(cx, cy),
            tail=tail,
            font_size_ratio=0.045 if b_type == "sfx" else 0.024,
            text_color=text_color,
            bg_color=bg_color,
            text_halo=text_halo,
            halo_color=halo_color,
            angle=angle,
            visibility_mode="auto"
        )
        bubble_configs.append(cfg)

    return scene_desc, bubble_configs


# --- 1. Google Gemini API ---

def generate_with_gemini(
    image: Image.Image,
    api_key: str,
    model_name: str = "gemini-2.0-flash",
    genre_hint: str = "自動"
) -> Tuple[str, List[BubbleConfig]]:
    """Generate dialogue using Google Gemini API."""
    if not api_key:
        raise ValueError("Google Gemini APIキーが設定されていません。")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key.strip())

    prompt = (
        f"このイラストに最適なセリフと吹き出しを考案してください。\n"
        f"作風・シチュエーションの希望: {genre_hint}\n"
        "キャラクターの顔や髪を絶対に隠さない安全な背景座標（0.0〜1.0）を指定してください。"
    )

    rgb_img = image.convert("RGB")

    # Try primary model, fallback to gemini-1.5-flash if needed
    models_to_try = [model_name]
    if model_name != "gemini-1.5-flash":
        models_to_try.append("gemini-1.5-flash")

    last_err = None
    for m in models_to_try:
        try:
            response = client.models.generate_content(
                model=m,
                contents=[rgb_img, prompt],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=AISceneResult,
                    temperature=0.7,
                )
            )
            data = json.loads(response.text)
            return _parse_bubbles_json(data)
        except Exception as e:
            last_err = e
            continue

    raise last_err or RuntimeError("Gemini API call failed.")


def test_gemini_connection(api_key: str, model_name: str = "gemini-2.0-flash") -> str:
    """Test connection to Gemini API by sending a simple ping."""
    from google import genai
    client = genai.Client(api_key=api_key.strip())
    # Try lightweight test prompt
    models_to_try = [model_name, "gemini-1.5-flash"]
    for m in models_to_try:
        try:
            res = client.models.generate_content(model=m, contents="Hello")
            if res and res.text:
                return f"✅ 接続成功！ (モデル: {m})"
        except Exception as e:
            if m == models_to_try[-1]:
                raise e
    return "✅ 接続成功！"


# --- 2. OpenAI-compatible Cloud APIs (DeepSeek, Groq, OpenRouter, OpenAI) ---

def generate_with_openai_compatible(
    image: Image.Image,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model_name: str = "gpt-4o-mini",
    genre_hint: str = "自動"
) -> Tuple[str, List[BubbleConfig]]:
    """Generate dialogue using an OpenAI-compatible REST endpoint."""
    if not api_key:
        raise ValueError("APIキーが設定されていません。")

    base_url = base_url.rstrip("/")
    b64_img = _pil_to_base64_jpeg(image)

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }

    user_prompt = (
        f"このイラストに最適なセリフと吹き出しを考案してください。\n"
        f"作風・シチュエーションの希望: {genre_hint}\n"
        "キャラクターの顔や髪を絶対に隠さない安全な背景座標（0.0〜1.0）を指定して、必ずJSONフォーマットで出力してください。"
    )

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                    }
                ]
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=40)
    if resp.status_code != 200:
        raise RuntimeError(f"API Error ({resp.status_code}): {resp.text}")

    res_json = resp.json()
    content_str = res_json["choices"][0]["message"]["content"]
    data = json.loads(content_str)
    return _parse_bubbles_json(data)


def test_openai_connection(api_key: str, base_url: str = "https://api.openai.com/v1", model_name: str = "gpt-4o-mini") -> str:
    """Test connection to an OpenAI-compatible endpoint."""
    base_url = base_url.rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    if resp.status_code == 200:
        return f"✅ 接続成功！ (エンドポイント: {base_url})"
    raise RuntimeError(f"接続失敗 ({resp.status_code}): {resp.text}")


# --- 3. Local Vision LLMs (Ollama) ---

def generate_with_local_ollama(
    image: Image.Image,
    base_url: str = "http://localhost:11434",
    model_name: str = "qwen2.5-vl:7b",
    genre_hint: str = "自動"
) -> Tuple[str, List[BubbleConfig]]:
    """Generate dialogue using a local Ollama Vision LLM instance."""
    base_url = base_url.rstrip("/")
    b64_img = _pil_to_base64_jpeg(image)

    url = f"{base_url}/api/generate"
    user_prompt = (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"このイラストに最適なセリフと吹き出しを考案してください。\n"
        f"作風・シチュエーションの希望: {genre_hint}\n"
        "キャラクターの顔や髪を絶対に隠さない安全な背景座標（0.0〜1.0）を指定して、必ず指定のJSON形式のみで出力してください。"
    )

    payload = {
        "model": model_name,
        "prompt": user_prompt,
        "images": [b64_img],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.7}
    }

    try:
        resp = requests.post(url, json=payload, timeout=60)
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Ollamaサーバー ({base_url}) に接続できませんでした。\n"
            "Ollamaが起動しているか確認してください (例: 'ollama serve')。"
        )

    if resp.status_code != 200:
        raise RuntimeError(f"Ollama Error ({resp.status_code}): {resp.text}")

    res_json = resp.json()
    resp_text = res_json.get("response", "")
    data = json.loads(resp_text)
    return _parse_bubbles_json(data)


def test_ollama_connection(base_url: str = "http://localhost:11434") -> Tuple[str, List[str]]:
    """Test connection to local Ollama and retrieve installed model tags."""
    base_url = base_url.rstrip("/")
    url = f"{base_url}/api/tags"
    try:
        resp = requests.get(url, timeout=5)
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Ollamaサーバー ({base_url}) に接続できませんでした。")

    if resp.status_code == 200:
        data = resp.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        msg = f"✅ Ollama接続成功！ (検出モデル: {len(models)}個)"
        return msg, models
    raise RuntimeError(f"Ollama応答エラー ({resp.status_code}): {resp.text}")


# --- Universal Dispatcher ---

def generate_scene_dialogue(
    image: Image.Image,
    genre_hint: str = "自動",
    provider_override: Optional[str] = None
) -> Tuple[str, List[BubbleConfig]]:
    """
    Main entry point for AI dialogue generation.
    Reads current configuration and routes request to the active provider.
    """
    cfg = load_config()
    provider = provider_override or cfg.get("active_provider", "gemini")

    if provider == "gemini":
        g_cfg = cfg.get("gemini", {})
        return generate_with_gemini(
            image=image,
            api_key=g_cfg.get("api_key", ""),
            model_name=g_cfg.get("model", "gemini-2.0-flash"),
            genre_hint=genre_hint
        )
    elif provider == "openai_compatible":
        o_cfg = cfg.get("openai_compatible", {})
        return generate_with_openai_compatible(
            image=image,
            api_key=o_cfg.get("api_key", ""),
            base_url=o_cfg.get("base_url", "https://api.openai.com/v1"),
            model_name=o_cfg.get("model", "gpt-4o-mini"),
            genre_hint=genre_hint
        )
    elif provider == "local_ollama":
        l_cfg = cfg.get("local_ollama", {})
        return generate_with_local_ollama(
            image=image,
            base_url=l_cfg.get("base_url", "http://localhost:11434"),
            model_name=l_cfg.get("model", "qwen2.5-vl:7b"),
            genre_hint=genre_hint
        )
    else:
        raise ValueError(f"未知のAIプロバイダー: {provider}")

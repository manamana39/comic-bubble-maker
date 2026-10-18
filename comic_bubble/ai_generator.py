"""
comic_bubble.ai_generator
~~~~~~~~~~~~~~~~~~~~~~~~~
Automatic speech bubble, monologue, and SFX generation using Google Gemini API.
Analyzes scene context, character expressions, relationships, and negative space
to generate natural dialogue and non-interfering bubble placements.
"""

import os
import json
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image
from pydantic import BaseModel, Field

from .models import BubbleConfig

CONFIG_PATH = os.path.expanduser("~/.comic_bubble_config.json")


def get_stored_api_key() -> Optional[str]:
    """Retrieve saved Gemini API key from environment variable or local config file."""
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key.strip()

    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("gemini_api_key", "").strip() or None
        except Exception:
            pass
    return None


def save_stored_api_key(api_key: str):
    """Save Gemini API key to user config file for persistence."""
    data = {}
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data["gemini_api_key"] = api_key.strip()
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Failed to save API key to config:", e)


# Pydantic Schemas for Structured JSON Output
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


def generate_scene_dialogue(
    image: Image.Image,
    api_key: Optional[str] = None,
    genre_hint: str = "自動",
    model_name: str = "gemini-2.5-flash"
) -> Tuple[str, List[BubbleConfig]]:
    """
    Call Gemini API with image and prompt to generate dialogues and bubble configs.
    
    Returns:
        (scene_description, list_of_BubbleConfig)
    """
    key = api_key or get_stored_api_key()
    if not key:
        raise ValueError(
            "Gemini APIキーが設定されていません。\n"
            "アプリの「AI設定」からAPIキーを入力するか、環境変数 GEMINI_API_KEY を設定してください。"
        )

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)

    system_instruction = (
        "あなたはプロの漫画原作者兼レタリング編集者です。\n"
        "入力されたイラスト画像を詳細に観察し、以下のルールに従って最高に魅力的なセリフ・吹き出しを作成してください。\n\n"
        "【セリフ演出のルール】\n"
        "1. キャラクターの表情、視線、赤面、手の仕草、背景シチュエーションから心情を敏感に読み取ること。\n"
        "2. 単なるセリフだけでなく、「枠なし浮遊モノローグ（floating: 心の声・独白）」や「オノマトペ（sfx: ドキッ、パシャッ、ヒソ…）」を効果的に組み合わせること。\n"
        "3. 日本語の漫画表現として自然でエモーショナルな言葉選びにすること。\n\n"
        "【レイアウト・Zero Interference の絶対ルール】\n"
        "1. 【顔被りゼロ】: 吹き出し（center）はキャラクターの顔、髪、目、身体を絶対に隠さない背景の空きスペース（空、窓、壁、カーテンなど）に配置すること。\n"
        "2. 【しっぽの横切り禁止】: しっぽ（tail）を発言者に向ける際、他のキャラクターの顔や髪を絶対に横切ってはならない。\n"
        "3. モノローグ（floating）やオノマトペ（sfx）はしっぽ不要（has_tail: False）。\n"
    )

    prompt = (
        f"このイラストに最適なセリフと吹き出しを考案してください。\n"
        f"シチュエーション・作風の希望: {genre_hint}\n"
        "キャラクターの顔や髪を一切隠さない安全な背景座標（0.0〜1.0）を指定して、構造化JSONで出力してください。"
    )

    # Convert PIL Image to RGB if needed
    rgb_img = image.convert("RGB")

    response = client.models.generate_content(
        model=model_name,
        contents=[rgb_img, prompt],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=AISceneResult,
            temperature=0.7,
        )
    )

    # Parse JSON output
    data = json.loads(response.text)
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

        # Colors & styling defaults based on type
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

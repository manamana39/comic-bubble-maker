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
from .typography import auto_wrap_japanese_text


class AIBubbleItem(BaseModel):
    text: str = Field(
        description="キャラクターのセリフ、心の声、またはオノマトペ。縦書きに最適な自然な改行（\\n）を含む。強調は<big>セリフ</big>、小声は<small>セリフ</small>を使用可能。"
    )
    type: str = Field(
        description="吹き出しの形状: 'capsule' (標準セリフ), 'cloud' (楽しい・自撮り・思考), 'whisper' (囁き・点線), 'scream' (叫び・ツッコミ), 'floating' (枠なし心の声・モノローグ), 'none' (画像内にすでに空の吹き出しやセリフ枠が描かれている場合。枠・背景を描画せず文字のみを既存枠の中に配置), 'sfx' (オノマトペ・描き文字)"
    )
    center_x: float = Field(
        description="吹き出し中心X座標 (0.0=左端, 1.0=右端)。キャラクターの顔や髪・手足を絶対に隠さない安全な背景の余白領域を指定すること。"
    )
    center_y: float = Field(
        description="吹き出し中心Y座標 (0.0=上端, 1.0=下端)。キャラクターの顔や髪・手足を絶対に隠さない安全な背景の余白領域を指定すること。"
    )
    has_tail: bool = Field(
        description="しっぽの有無。floating, none, sfxの場合はFalse、発言セリフの場合はTrue。"
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

【重要: 縦書きの改行ルール（吹き出しの巨大化防止）】
日本の漫画吹き出しは「縦書き」です。改行（\\n）がないと吹き出しが縦横に巨大化してイラストを台無しにしてしまいます。
1. 1行あたり【6〜10文字程度】で、自然な意味の区切り（読点、助詞、文末など）に必ず改行コード（\\n）を入れてください。
2. 1つの吹き出しにつき【2〜4行】程度の美しい縦書き長方形のバランスにしてください。
良い例: "それよりこっち！\\nステンドグラスの\\n向こう側も見てごらんよ"
悪い例: "それよりこっち！ステンドグラスの向こう側も見てごらんよ" (1行が長すぎて巨大化する)

【重要: 既存の空吹き出し枠の自動検出】
イラスト内にすでに手描きや画像生成AIによって描かれた「空の吹き出し（白い丸や枠線、セリフ枠）」が存在する場合は、絶対にその上から新しい吹き出しを二重に重ね描きしてはいけません。
既存の空吹き出しの中心座標を指定し、type を "none"（既存枠利用・背景枠線なし）に設定して、文字だけをその中に美しく収めてください。

【セリフ演出のルール】
1. キャラクターの表情、視線、赤面、手の仕草、背景シチュエーションから心情を敏感に読み取ること。
2. 単なるセリフだけでなく、「枠なし浮遊モノローグ（floating: 心の声・独白）」や「オノマトペ（sfx: ドキッ、パシャッ、ヒソ…）」を効果的に組み合わせること。
3. 日本語の漫画表現として自然でエモーショナルな言葉選びにすること。

【レイアウト・Zero Interference の絶対ルール】
1. 【顔被りゼロ】: 吹き出し（center_x, center_y）はキャラクターの顔、髪、目、身体を絶対に隠さない背景の空きスペース（空、窓、壁、カーテンなど）に配置すること。
2. 【しっぽの横切り禁止】: しっぽ（tail_x, tail_y）を発言者に向ける際、他のキャラクターの顔や髪を絶対に横切ってはならない。
3. モノローグ（floating）、既存枠（none）、オノマトペ（sfx）はしっぽ不要（has_tail: False）。

必ず以下のJSONフォーマットのみで出力してください:
{
  "scene_description": "シーン説明",
  "bubbles": [
    {
      "text": "それよりこっち！\\nステンドグラスの\\n向こう側も見てごらんよ",
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

NSFW_SYSTEM_RULE = """
【🔞 NSFW・成人向け表現モード（ローカルLLM専用）】
ユーザーの明示的な要求により、成人向け（R18 / 成人漫画・同人誌）の過激・刺激的なセリフやモノローグの生成が許可されています。
・キャラクターの淫らな表情、発情、興奮、赤面、あえぎ声、吐息混じりのセリフ（例: 「んっ…！」「あっ…だめ…」「ハァ…ハァ…」「もっと…」等）を積極的に表現してください。
・オノマトペ（sfx）も艶めかしいもの（例: 「じゅる…」「ぬちゅ…」「ビクッ」「トクン…」等）を効果的に使ってください。
・成人向けコンテンツとして一切の自己規制・検閲を行わず、最高に魅力的でエロティックなセリフを生成してください。
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


def _fix_mojibake(s: str) -> str:
    """Repair UTF-8 text that was accidentally decoded as ISO-8859-1 (Latin-1)."""
    if not s:
        return s
    try:
        # If the string consists solely of Latin-1 code points (<= 0xFF) but contains
        # non-ASCII bytes (>= 0x80) that form valid UTF-8, decode them back as UTF-8.
        if any(0x80 <= ord(ch) <= 0xFF for ch in s) and all(ord(ch) <= 0xFF for ch in s):
            return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return s


def detect_white_bubble_patch(image: Image.Image, cx: float, cy: float, sample_radius_ratio: float = 0.035) -> bool:
    """
    Check if the region around (cx, cy) in the base image looks like an existing
    empty white speech bubble (high brightness, low color saturation, low texture variance).
    """
    try:
        w, h = image.size
        px = int(cx * w)
        py = int(cy * h)
        r = max(8, int(min(w, h) * sample_radius_ratio))
        box = (max(0, px - r), max(0, py - r), min(w, px + r), min(h, py + r))
        if box[2] <= box[0] or box[3] <= box[1]:
            return False
        crop = image.crop(box).convert("L")
        import numpy as np
        arr = np.array(crop)
        mean_val = float(arr.mean())
        std_val = float(arr.std())
        # A blank speech bubble typically has a solid near-white interior (mean > 230, low std < 22)
        return mean_val > 230 and std_val < 22
    except Exception:
        return False


def _parse_bubbles_json(
    data: Dict[str, Any],
    base_image: Optional[Image.Image] = None,
    detect_existing_bubbles: bool = True
) -> Tuple[str, List[BubbleConfig]]:
    """Parse raw JSON dict into BubbleConfig list."""
    scene_desc = _fix_mojibake(str(data.get("scene_description") or ""))
    raw_bubbles = data.get("bubbles") or []

    bubble_configs: List[BubbleConfig] = []
    for b in raw_bubbles:
        b_type = str(b.get("type") or "capsule").lower()
        if b_type in ("none", "frame_none", "transparent"):
            b_type = "none"

        cx = float(b.get("center_x") if b.get("center_x") is not None else 0.5)
        cy = float(b.get("center_y") if b.get("center_y") is not None else 0.3)

        # Smart automatic detection: check if image already has a pre-existing white bubble at (cx, cy)
        is_existing_bubble = (b_type == "none")
        if not is_existing_bubble and detect_existing_bubbles and base_image is not None and b_type not in ("floating", "sfx"):
            if detect_white_bubble_patch(base_image, cx, cy):
                b_type = "none"
                is_existing_bubble = True

        tail = None
        if not is_existing_bubble and b_type != "none" and b.get("has_tail") and b.get("tail_x") is not None and b.get("tail_y") is not None:
            tail = (float(b["tail_x"]), float(b["tail_y"]))

        text_color = (45, 35, 55, 255)
        bg_color = (255, 250, 245)
        text_halo = True
        halo_color = None
        angle = float(b.get("angle") if b.get("angle") is not None else 0.0)

        if b_type == "floating":
            text_color = (255, 255, 255, 255)
            halo_color = (30, 35, 50, 220)
        elif b_type == "none":
            # For pre-existing bubbles, crisp dark text with a gentle bright halo to guarantee readability
            text_color = (35, 30, 45, 255)
            halo_color = (255, 255, 255, 200)
        elif b_type == "sfx":
            text_color = (255, 90, 110, 255)

        raw_text = _fix_mojibake(str(b.get("text") or ""))
        final_text = auto_wrap_japanese_text(raw_text) if b_type != "sfx" else raw_text

        cfg = BubbleConfig(
            text=final_text,
            type=b_type,
            font=str(b.get("font") or "kiwi"),
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

def _clean_gemini_model_name(model_name: str) -> str:
    """Normalize model string and replace deprecated 1.5/2.0/2.5 names with gemini-3.8-flash."""
    m = (model_name or "gemini-3.8-flash").strip().split()[0]
    if m.startswith(("gemini-1.5", "gemini-2.0", "gemini-2.5")):
        return "gemini-3.8-flash"
    return m


def generate_with_gemini(
    image: Image.Image,
    api_key: str,
    model_name: str = "gemini-3.8-flash",
    genre_hint: str = "自動",
    nsfw: bool = False,
    detect_existing: bool = True
) -> Tuple[str, List[BubbleConfig]]:
    """Generate dialogue using Google Gemini API."""
    if not api_key:
        raise ValueError("Google Gemini APIキーが設定されていません。")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key.strip())

    nsfw_hint = "（艶やかで少し大人っぽい雰囲気で）" if nsfw else ""
    prompt = (
        f"このイラストに最適なセリフと吹き出しを考案してください。\n"
        f"作風・シチュエーションの希望: {genre_hint} {nsfw_hint}\n"
        "【重要: 縦書き改行】1行あたり6〜10文字程度で自然に「\\n」を入れて2〜4行のバランスにしてください。\n"
        "【既存枠検出】イラスト内に既に空の吹き出し枠がある場合は、type を 'none' にして既存枠内に文字を収めてください。\n"
        "キャラクターの顔や髪を絶対に隠さない安全な背景座標（0.0〜1.0）を指定してください。"
    )

    rgb_img = image.convert("RGB")
    w, h = rgb_img.size
    if max(w, h) > 1280:
        scale = 1280 / max(w, h)
        rgb_img = rgb_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    clean_model = _clean_gemini_model_name(model_name)
    candidate_models = [clean_model, "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
    models_to_try = []
    for m in candidate_models:
        if m and m not in models_to_try:
            models_to_try.append(m)

    first_err = None
    response = None
    for m in models_to_try:
        try:
            response = client.models.generate_content(
                model=m,
                contents=[rgb_img, prompt],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=AISceneResult,
                )
            )
            if response and response.text:
                break
        except Exception as e:
            if first_err is None:
                first_err = e
            continue

    if not response or not response.text:
        raise first_err or RuntimeError("Gemini API call failed.")

    data = json.loads(response.text)
    return _parse_bubbles_json(data, base_image=image, detect_existing_bubbles=detect_existing)


def test_gemini_connection(api_key: str, model_name: str = "gemini-3.8-flash") -> str:
    """Test connection to Gemini API by sending a simple ping."""
    from google import genai
    client = genai.Client(api_key=api_key.strip())
    clean_model = _clean_gemini_model_name(model_name)
    candidate_models = [clean_model, "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
    models_to_try = []
    for m in candidate_models:
        if m and m not in models_to_try:
            models_to_try.append(m)

    first_err = None
    for m in models_to_try:
        try:
            res = client.models.generate_content(model=m, contents="Hello")
            if res and res.text:
                return f"✅ 接続成功！ (モデル: {m})"
        except Exception as e:
            if first_err is None:
                first_err = e
            if m == models_to_try[-1]:
                raise first_err
    return "✅ 接続成功！"


# --- 2. OpenAI-compatible APIs (LM Studio Local, OpenAI, DeepSeek, Groq, OpenRouter) ---

def _is_local_url(url: str) -> bool:
    u = (url or "").lower()
    return any(h in u for h in ("localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10."))


def _normalize_openai_base_url(base_url: str) -> str:
    url = (base_url or "http://localhost:1234/v1").strip().rstrip("/")
    # If user entered http://localhost:1234 without /v1, append /v1 automatically
    if _is_local_url(url) and not url.endswith("/v1") and "/api" not in url:
        url = url + "/v1"
    return url


def _extract_json_dict(raw_text: str) -> Dict[str, Any]:
    """Extract JSON object from LLM output, stripping <think> tags or markdown fences."""
    import re
    text = (raw_text or "").strip()
    # Strip <think>...</think> blocks if present
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Strip markdown code fences
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if match:
            text = match.group(1).strip()
    # Find outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def generate_with_openai_compatible(
    image: Image.Image,
    api_key: str = "",
    base_url: str = "http://localhost:1234/v1",
    model_name: str = "qwen3-vl-8b-nsfw-caption-v4.5",
    genre_hint: str = "自動",
    progress_callback: Optional[ Any ] = None,
    nsfw: bool = False,
    detect_existing: bool = True
) -> Tuple[str, List[BubbleConfig]]:
    """
    Generate dialogue using an OpenAI-compatible REST endpoint (LM Studio or Cloud).
    Uses SSE streaming (stream=True) so long-thinking local VLMs (e.g., 27B reasoning models)
    never hit a total-request read timeout, while reporting live token progress to the GUI.
    """
    is_local = _is_local_url(base_url)
    effective_key = (api_key or "").strip() or ("lm-studio" if is_local else "")
    if not effective_key:
        raise ValueError("APIキーが設定されていません。")

    norm_base_url = _normalize_openai_base_url(base_url)
    b64_img = _pil_to_base64_jpeg(image, max_dim=768 if is_local else 1024)

    url = f"{norm_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {effective_key}",
        "Content-Type": "application/json"
    }

    user_prompt = (
        f"このイラストに最適なセリフと吹き出しを考案してください。\n"
        f"作風・シチュエーションの希望: {genre_hint}\n"
        "【重要: 縦書き改行】1行あたり6〜10文字程度で自然に「\\n」を入れて2〜4行のバランスにしてください。\n"
        "【既存枠検出】イラスト内に既に空の吹き出し枠がある場合は、type を 'none' にして既存枠内に文字を収めてください。\n"
        "キャラクターの顔や髪を絶対に隠さない安全な背景座標（0.0〜1.0）を指定して、必ずJSONフォーマットのみで出力してください。"
    )
    if nsfw:
        user_prompt = "【🔞 NSFW・成人向け表現モード】イラストの艶めかしい感情・情動・あえぎ・吐息・淫靡な雰囲気を引き立てる刺激的なセリフやオノマトペにしてください。\n" + user_prompt

    sys_content = SYSTEM_INSTRUCTION
    if nsfw:
        sys_content = sys_content + "\n\n" + NSFW_SYSTEM_RULE

    clean_model = (model_name or "").split(" (")[0].strip()

    # If local LM Studio has a model already loaded in VRAM and user's config has a different default,
    # check if clean_model is loaded or if we should use the currently loaded VLM to avoid slow model swaps
    if is_local:
        try:
            root_url = norm_base_url[:-3] if norm_base_url.endswith("/v1") else norm_base_url
            r_v0 = requests.get(f"{root_url}/api/v0/models", timeout=3)
            if r_v0.status_code == 200:
                m_list = r_v0.json().get("data", [])
                loaded_vlms = [m["id"] for m in m_list if m.get("state") == "loaded" and m.get("type") == "vlm"]
                all_ids = [m["id"] for m in m_list]
                if loaded_vlms and (not clean_model or clean_model not in all_ids):
                    clean_model = loaded_vlms[0]
        except Exception:
            pass

    messages = [
        {"role": "system", "content": sys_content},
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
    ]

    # LM Studio requires 'json_schema' or 'text' instead of 'json_object'
    json_schema_fmt = {
        "type": "json_schema",
        "json_schema": {
            "name": "scene_result",
            "schema": AISceneResult.model_json_schema()
        }
    }
    format_candidates = (
        [json_schema_fmt, None] if is_local else [{"type": "json_object"}, json_schema_fmt, None]
    )

    # With stream=True, timeout is per-chunk (connect_timeout, inter_token_read_timeout)
    chunk_timeout = (15, 240) if is_local else (15, 60)
    last_err_text = ""

    for fmt in format_candidates:
        payload: Dict[str, Any] = {
            "model": clean_model,
            "messages": messages,
            "temperature": 0.7,
            "stream": True,
        }
        if fmt is not None:
            payload["response_format"] = fmt

        try:
            if progress_callback:
                progress_callback(f"🤖 {clean_model} に画像を送信中...")
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=chunk_timeout
            )
        except requests.exceptions.ConnectionError:
            if is_local:
                raise ConnectionError(
                    f"ローカルLLMサーバー ({norm_base_url}) に接続できませんでした。\n"
                    "LM Studio の Local Server (ポート1234等) が起動しているか確認してください。"
                )
            raise

        resp.encoding = "utf-8"

        if resp.status_code == 200:
            content_parts: List[str] = []
            reasoning_parts: List[str] = []
            reasoning_chunks = 0
            content_chunks = 0

            for raw_bytes in resp.iter_lines(decode_unicode=False):
                if not raw_bytes:
                    continue
                if isinstance(raw_bytes, bytes):
                    line = raw_bytes.decode("utf-8", errors="replace").strip()
                else:
                    line = str(raw_bytes).strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk_json = json.loads(data_str)
                    choices = chunk_json.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    r_piece = delta.get("reasoning_content") or delta.get("reasoning") or ""
                    c_piece = delta.get("content") or ""
                    if r_piece:
                        reasoning_parts.append(r_piece)
                        reasoning_chunks += 1
                        if progress_callback and reasoning_chunks % 12 == 0:
                            progress_callback(
                                f"🧠 AIが思考中 (Thinking)... [{reasoning_chunks} トークン生成中]"
                            )
                    if c_piece:
                        content_parts.append(c_piece)
                        content_chunks += 1
                        if progress_callback and content_chunks % 8 == 1:
                            progress_callback(
                                f"✍️ セリフJSONを生成中... [{content_chunks} トークン]"
                            )
                except Exception:
                    continue

            full_content = "".join(content_parts).strip()
            if not full_content:
                full_content = "".join(reasoning_parts).strip()
            data = _extract_json_dict(full_content)
            return _parse_bubbles_json(data, base_image=image, detect_existing_bubbles=detect_existing)
        elif resp.status_code == 400 and "response_format" in resp.text:
            last_err_text = f"API Error ({resp.status_code}): {resp.text}"
            continue
        else:
            last_err_text = f"API Error ({resp.status_code}): {resp.text}"
            break

    raise RuntimeError(last_err_text or "OpenAI互換APIの呼び出しに失敗しました。")


def test_openai_connection(
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model_name: str = "gpt-4o-mini"
) -> str:
    """Test connection to an OpenAI-compatible endpoint."""
    is_local = _is_local_url(base_url)
    effective_key = (api_key or "").strip() or ("lm-studio" if is_local else "")
    norm_base_url = _normalize_openai_base_url(base_url)
    headers = {
        "Authorization": f"Bearer {effective_key}",
        "Content-Type": "application/json"
    }

    # First check /models if local (fast, doesn't require waiting for full LLM generation)
    if is_local:
        models_url = f"{norm_base_url}/models"
        resp = requests.get(models_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return f"✅ LM Studio / OpenAI互換サーバー接続成功！ (検出モデル: {len(data)}個)"

    url = f"{norm_base_url}/chat/completions"
    clean_model = (model_name or "").split(" (")[0].strip()
    payload = {
        "model": clean_model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code == 200:
        return f"✅ 接続成功！ (エンドポイント: {norm_base_url})"
    raise RuntimeError(f"接続失敗 ({resp.status_code}): {resp.text}")


# --- 3. Local Vision LLMs (LM Studio OpenAI-Compatible / Ollama fallback) ---

def generate_with_local_ollama(
    image: Image.Image,
    base_url: str = "http://localhost:1234/v1",
    model_name: str = "qwen3-vl-8b-nsfw-caption-v4.5",
    genre_hint: str = "自動",
    api_key: str = "lm-studio",
    progress_callback: Optional[Any] = None,
    nsfw: bool = False,
    detect_existing: bool = True
) -> Tuple[str, List[BubbleConfig]]:
    """
    Generate dialogue using a local LLM server.
    Defaults to LM Studio's OpenAI-compatible endpoint (http://localhost:1234/v1).
    """
    return generate_with_openai_compatible(
        image=image,
        api_key=api_key or "lm-studio",
        base_url=base_url,
        model_name=model_name,
        genre_hint=genre_hint,
        progress_callback=progress_callback,
        nsfw=nsfw,
        detect_existing=detect_existing
    )


def test_ollama_connection(base_url: str = "http://localhost:1234/v1", api_key: str = "lm-studio") -> Tuple[str, List[str]]:
    """
    Test connection to local LM Studio (OpenAI-compatible /v1/models or /api/v0/models)
    and retrieve installed models, prioritizing Vision (VLM) and loaded models.
    """
    norm_base_url = _normalize_openai_base_url(base_url)
    root_url = norm_base_url[:-3] if norm_base_url.endswith("/v1") else norm_base_url

    # 1. Try LM Studio rich metadata endpoint (/api/v0/models) to identify VLMs & loaded state
    try:
        resp_v0 = requests.get(f"{root_url}/api/v0/models", timeout=5)
        if resp_v0.status_code == 200:
            raw_models = resp_v0.json().get("data", [])
            vlm_loaded = []
            vlm_other = []
            llm_other = []
            for m in raw_models:
                m_id = m.get("id", "")
                m_type = m.get("type", "")
                m_state = m.get("state", "")
                if not m_id or m_type == "embeddings":
                    continue
                if m_type == "vlm" and m_state == "loaded":
                    vlm_loaded.append(m_id)
                elif m_type == "vlm":
                    vlm_other.append(m_id)
                else:
                    llm_other.append(m_id)
            models = vlm_loaded + vlm_other + llm_other
            vlm_count = len(vlm_loaded) + len(vlm_other)
            msg = f"✅ LM Studio 接続成功！ (画像対応VLM: {vlm_count}個 / 全{len(models)}個)"
            return msg, models
    except Exception:
        pass

    # 2. Standard OpenAI-compatible GET /v1/models
    headers = {"Authorization": f"Bearer {(api_key or 'lm-studio').strip()}"}
    models_url = f"{norm_base_url}/models"
    try:
        resp = requests.get(models_url, headers=headers, timeout=5)
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"LM Studio サーバー ({norm_base_url}) に接続できませんでした。\n"
            "LM Studio の「Developer / Local Server」タブでサーバーが起動しているか確認してください。"
        )

    if resp.status_code == 200:
        data = resp.json()
        models = [
            m.get("id", "")
            for m in data.get("data", [])
            if m.get("id") and "embed" not in m.get("id", "").lower()
        ]
        msg = f"✅ ローカルOpenAI互換サーバー接続成功！ (検出モデル: {len(models)}個)"
        return msg, models

    raise RuntimeError(f"ローカルサーバー応答エラー ({resp.status_code}): {resp.text}")


# --- Universal Dispatcher ---

def generate_scene_dialogue(
    image: Image.Image,
    genre_hint: str = "自動",
    provider_override: Optional[str] = None,
    progress_callback: Optional[Any] = None,
    nsfw: bool = False,
    detect_existing: bool = True
) -> Tuple[str, List[BubbleConfig]]:
    """
    Main entry point for AI dialogue generation.
    Reads current configuration and routes request to the active provider.
    """
    cfg = load_config()
    provider = provider_override or cfg.get("active_provider", "gemini")

    if provider == "gemini":
        g_cfg = cfg.get("gemini", {})
        if progress_callback:
            progress_callback("🤖 Gemini API でイラストの表情・文脈を分析中...")
        return generate_with_gemini(
            image=image,
            api_key=g_cfg.get("api_key", ""),
            model_name=g_cfg.get("model", "gemini-3.8-flash"),
            genre_hint=genre_hint,
            nsfw=nsfw,
            detect_existing=detect_existing
        )
    elif provider == "openai_compatible":
        o_cfg = cfg.get("openai_compatible", {})
        return generate_with_openai_compatible(
            image=image,
            api_key=o_cfg.get("api_key", ""),
            base_url=o_cfg.get("base_url", "https://api.openai.com/v1"),
            model_name=o_cfg.get("model", "gpt-4o-mini"),
            genre_hint=genre_hint,
            progress_callback=progress_callback,
            nsfw=nsfw,
            detect_existing=detect_existing
        )
    elif provider == "local_ollama":
        l_cfg = cfg.get("local_ollama", {})
        return generate_with_local_ollama(
            image=image,
            base_url=l_cfg.get("base_url", "http://localhost:1234/v1"),
            model_name=l_cfg.get("model", "qwen3-vl-8b-nsfw-caption-v4.5"),
            genre_hint=genre_hint,
            api_key=l_cfg.get("api_key", "lm-studio"),
            progress_callback=progress_callback,
            nsfw=nsfw,
            detect_existing=detect_existing
        )
    else:
        raise ValueError(f"未知のAIプロバイダー: {provider}")

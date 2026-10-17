# 💬 Comic Bubble Maker (漫画吹き出し・浮遊モノローグ・オノマトペ合成エンジン)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Verification](https://img.shields.io/badge/Verification-13%20Passed-brightgreen.svg)](output/verification_report.json)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![ComfyUI Ready](https://img.shields.io/badge/ComfyUI-Native%20Node%20Ready-orange.svg)](comfyui_node.py)

ComfyUIやAI生成されたイラスト・漫画画像に対し、**キャラクターへの被りゼロ**・**縦書き組版**・**枠なし浮遊モノローグ**・**漫画オノマトペ**・**叫び＆囁き吹き出し**・**夜景自動コントラスト保護**を備えたプロフェッショナルな漫画吹き出し合成エンジンです。

---

## ✨ 主な特長 (Key Features)

1. **縦書き組版＆文字重なり完全解消 (Vertical Japanese Typography)**
   - インク幅（bbox）ではなくフォントEMサイズ基準の正確な送り幅（Advance）を計算。小文字（「っ」「ょ」）や記号（「…」）の重なりを数理的に完全排除。
   - 縦丸カッコ `（ ）` はUnicode文字未収録による豆腐（□）化を避けるため、数理円弧（`draw.arc`）による直接ベクター描画を実装。
   - `<big>`, `<small>`, `<huge>`, `<tiny>` などのインライン文字拡大縮小タグに対応。

2. **枠なし浮遊モノローグ (`type: "floating"` / `"monologue"`)**
   - 登場人物の「心の声」や情緒的な独白向けに、**吹き出し枠を一切描かず、文字のみを風景に溶け込ませて漂わせる**モードを完備。
   - 夕暮れや夜の街灯に合わせた光彩（Halo）を纏わせることで、背景の美しさを100%残したまま高い可読性を維持。

3. **漫画オノマトペ・描き文字 (`type: "sfx"` / `"onomatopoeia"`)**
   - `ドキッ`, `ドンッ`, `ゴゴゴ…` などの迫力ある擬音・効果音をサポート。
   - 角度回転（`angle: -14.0`）や多重フチ取り（`stroke_width`, `stroke_color`）によるプロ漫画レベルの表現が可能。

4. **多彩な漫画吹き出し形状 (Rich Balloon Geometry)**
   - **通常カプセル (`capsule`)**: 最も文字が綺麗に収まる角丸スーパー楕円。
   - **モコモコ雲型 (`cloud`)**: 感情の高まりや思考表現。
   - **叫び・爆発 (`scream` / `burst`)**: 驚き・激昂・叫び用のウニフラ星型ポリゴンとしっぽ。
   - **囁き・ヒソヒソ (`whisper`)**: 点線・破線による小声表現。
   - **スクエア枠 (`box`)**: 漫画の四角いナレーション・モノローグ枠。

5. **夜景・暗所での自動コントラスト判定 (Auto-Contrast Engine)**
   - 吹き出し配置領域の背景輝度（Rec. 601）をリアルタイムにサンプリング。
   - 夜景や濃い影の上に配置された場合、透明度を `0.20 → 0.80` へ自動引き上げ、文字の埋没を完全に防止。

6. **ネガティブスペース自動探索 (Smart Auto-Placement)**
   - `center: "auto"` を指定すると、輪郭・エッジ密度解析によりキャラクター（顔・身体）を自動検出し、空や背景などの安全な余白領域へ自動配置。

7. **ComfyUI ネイティブカスタムノード対応 (`comfyui_node.py`)**
   - 本リポジトリをそのまま `ComfyUI/custom_nodes/` に配置するだけで、ComfyUIワークフロー内で `💬 Manga Speech Bubble & SFX` ノードとして即座に利用可能。

8. **マルチプラットフォーム・フォントフォールバック**
   - キウイ丸、よもぎ、ゼン丸ゴシックなどの可愛い手書きフォントを自動認識。
   - Windows (BIZ UDゴシック・明朝)、macOS (ヒラギノ)、Linux (Noto Sans/Serif CJK) に自動フォールバック。

---

## 🏗 システム設計 (Architecture)

```mermaid
flowchart TD
    A[入力画像 / JSON設定 / ComfyUI Tensor] --> B[models.py: Scene & Bubble Config]
    B --> C{center is auto?}
    C -- Yes --> D[auto_layout.py: エッジ密度解析 & ネガティブスペース検出]
    C -- No --> E[指定座標を採用]
    D --> F[contrast.py: Auto-Contrast 分析]
    E --> F
    F --> G{背景輝度と文字色の差}
    G -- 暗い背景・夜景 --> H[不透明度を 0.80 に自動ブースト]
    G -- 明るい空・高コントラスト --> I[自然な透明度 0.20 を維持]
    H --> J[typography.py: 縦書きEMメトリクス & 円弧カッコ生成]
    I --> J
    J --> K{吹き出しタイプ}
    K -- capsule / cloud / scream / whisper / box --> L[shapes.py: 幾何学ポリゴン描画]
    K -- floating / monologue --> M[枠なし描画: 文字 + 光彩Halo]
    K -- sfx / onomatopoeia --> N[回転 & 極太フチ取り 描き文字]
    L --> O[engine.py: 3倍スーパーサンプリング合成]
    M --> O
    N --> O
    O --> P[LANCZOS縮小 & RGB出力保存]
```

---

## 🚀 クイックスタート (Quick Start)

### 1. インストール
```bash
git clone https://github.com/your-username/comic-bubble-maker.git
cd comic-bubble-maker
pip install -r requirements.txt
```

### 2. コマンドライン実行 (CLI)

```bash
# JSON設定ファイルから合成
python cli.py --config sample_config.json

# 1行コマンドでの直接実行
python cli.py --image input/sample.jpg --text "…べ、別に。\n待ってなんかないし！" --type capsule --center 0.15,0.18 --tail 0.30,0.32 --output output/result.png

# システムフォントの解決状態を確認
python cli.py --list-fonts

# 自動検証スイートを実行
python cli.py --verify
```

---

## 🧪 CodeX / 自動検証スイート (Autonomous Verification)

CodeXやCI/CD環境からワンクリックで全機能（13のユニットテスト・実画像合成・フォント検出）を検証できます：

```bash
python run_verification.py
```

実行後、構造化された検証レポートが `output/verification_report.json` に出力されます：
```json
{
  "version": "1.0.0",
  "overall_status": "SUCCESS",
  "unit_tests": {
    "tests_run": 13,
    "failures": 0,
    "errors": 0,
    "success": true
  },
  "real_world_verification": {
    "all_passed": true
  }
}
```

---

## 📄 JSON設定リファレンス (Configuration Schema)

```json
{
  "image_path": "input/park_night.jpg",
  "output_path": "output/result.png",
  "supersample_scale": 3,
  "bubbles": [
    {
      "text": "<small>…べ、別に。</small>\n<big>待ってなんか</big>\n<big>ないし…！</big>",
      "type": "capsule",             // "capsule", "cloud", "scream", "whisper", "box"
      "writing_mode": "vertical",     // "vertical"
      "font": "kiwi",                 // "kiwi", "yomogi", "zenmaru", "ud", "mincho", "bold"
      "center": [0.13, 0.14],         // 相対座標 [X, Y] (0.0〜1.0) または "auto"
      "tail": [0.28, 0.28],           // しっぽの先端座標
      "font_size_ratio": 0.021,       // 画像の高さに対する基準フォントサイズ比率
      "border_width": 2.0,            // 枠線の太さ
      "border_color": [45, 40, 60, 220],
      "text_color": [45, 35, 55, 255],
      "bg_color": [255, 248, 242],
      "visibility_mode": "auto",      // ★ "auto" (背景に応じて透明度自動調整)
      "bg_alpha": 0.20,               // 基本透過度
      "text_halo": true,              // 文字周囲の光彩
      "halo_color": [255, 255, 255, 200]
    },
    {
      "text": "（…二人きりなんて、\n　聞いてないよ…っ）",
      "type": "floating",             // ★ 枠なし浮遊モノローグ（吹き出し板なし）
      "writing_mode": "vertical",
      "font": "mincho",               // モノローグ専用の美しい明朝体
      "center": [0.12, 0.46],
      "font_size_ratio": 0.019,
      "text_color": [45, 35, 58, 255],
      "text_halo": true,
      "halo_color": [255, 250, 235, 240]
    },
    {
      "text": "ドキッ",
      "type": "sfx",                  // ★ 漫画オノマトペ・描き文字
      "font": "bold",
      "center": [0.29, 0.60],
      "angle": -14.0,                 // 回転角度
      "font_size_ratio": 0.048,
      "text_color": [235, 65, 85, 255],
      "stroke_width": 3.2,            // 外枠フチ取りの太さ
      "stroke_color": [255, 255, 255, 255]
    }
  ]
}
```

---

## 🎨 ComfyUI 連携ガイド

ComfyUIの `custom_nodes/` ディレクトリに本リポジトリを配置するだけで、UI上に `💬 Manga Speech Bubble & SFX` ノードが追加されます。

```
ComfyUI/
└── custom_nodes/
    └── ComfyUI-Comic-Bubble/   <-- 本リポジトリを配置
        ├── comfyui_node.py
        ├── comic_bubble/
        └── ...
```

---

## 📜 ライセンス (License)

本プロジェクトは [MIT License](LICENSE) の下で公開されています。商用・非商用問わず自由にご利用いただけます。

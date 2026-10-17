# Comic Bubble Maker (ComfyUI 画像吹き出し合成ツール)

ComfyUI等で生成された台詞なし画像に対し、マルチモーダルAIがシチュエーションに応じた「台詞」と「吹き出し」を自動合成し、ユーザーが手軽に微調整できるツールです。

---

## 🌟 特徴

- **どんな解像度・アスペクト比でも対応**: 座標やサイズを「画像比率 (0.0〜1.0)」で計算するため、縦長・横長・高解像度画像でも崩れません。
- **3種類の吹き出しスタイル**:
  - `normal`: 通常の角丸/楕円吹き出し + しっぽ
  - `shout`: 叫び・強調のギザギザ爆発吹き出し
  - `thought`: モノローグ・思考の雲型吹き出し
- **日本語フォント自動対応**: Windows標準フォント（Meiryo, Yu Gothic等）を自動認識。
- **超簡単な修正ワークフロー**:
  - 画像ごとに設定JSONファイルが保存されるため、「セリフの変更」や「位置の微調整」がAntigravityとの会話（またはJSONの数値編集）で一瞬で行えます。

---

## 🚀 使い方 (Antigravity 連携ワークフロー)

### 1. 画像の準備
ComfyUI等で生成した画像を `input/` フォルダに入れます。
（例: `input/my_character.png`）

### 2. Antigravityに依頼する
チャットで以下のように伝えるだけです：
> 「`input/my_character.png` を見て、適切な台詞と吹き出しをつけて！」
> 「ちょっとギャグっぽいセリフでお願い」

Antigravityが直接画像を読み取り、キャラクターの表情・視線・空きスペースを判定して設定JSONを生成＆レンダリングします。

### 3. 微調整する (修正したいとき)
生成された画像を見て、修正したい点があればチャットで伝えるだけです：
> 「右側のセリフを『そんなバカな…』に変えて」
> 「吹き出しをもっと右上に移動して」
> 「叫びのギザギザ吹き出しに変更して」

AntigravityがJSONを更新して再実行し、数秒で修正版画像が仕上がります。

---

## 🛠 手動でのコマンド実行

直接JSONを編集して再レンダリングすることも可能です。

```bash
python render_bubble.py --config sample_config.json
```

### 設定JSONの形式 (`sample_config.json`)
```json
{
  "image_path": "input/sample_test.png",
  "output_path": "output/sample_result.png",
  "bubbles": [
    {
      "text": "セリフをここに書く",
      "type": "normal",               // "normal", "shout", "thought"
      "box": [0.1, 0.1, 0.4, 0.25],   // [x_ratio, y_ratio, width_ratio, height_ratio]
      "tail": [0.25, 0.58],           // しっぽが指す話者の座標 [x_ratio, y_ratio]
      "font_size_ratio": 0.038        // 画像高さに対するフォントサイズ比率
    }
  ]
}
```

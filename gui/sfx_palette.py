"""
gui.sfx_palette
~~~~~~~~~~~~~~~
Manga SFX (Onomatopoeia / 擬音 / 描き文字) preset library palette.
Provides categorized collections of classic Japanese manga sound effects:
1. 💖 恋愛・胸キュン (ドキッ、トクン…、チュッ、ハァ…、ビクッ、カァァ…)
2. 😄 日常・リアクション (パシャッ、チラッ、ギュッ、スッ…、ニコッ、ピクッ)
3. 💥 迫力・コメディ (ガーン！、ビシッ、ええっ!?、ドヤァ、バァン！、ドォン！、ゴゴゴ…)
4. 🔞 艶音・吐息 (NSFW) (あんっ…、ハァ…ハァ…、びくっ、じゅる…、ぬちゅ…、ゾクッ…)
"""

from typing import List, Dict, Any, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QScrollArea, QGridLayout, QFrame,
    QLineEdit, QDoubleSpinBox, QGroupBox
)

from comic_bubble.models import BubbleConfig


SFX_PRESETS: Dict[str, List[Dict[str, Any]]] = {
    "💖 恋愛・胸キュン": [
        {"text": "ドキッ", "font": "bold", "angle": -12.0, "text_color": (255, 80, 120, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.048, "desc": "高鳴る鼓動・ときめき"},
        {"text": "ドキドキ…", "font": "kiwi", "angle": -8.0, "text_color": (255, 95, 140, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.044, "desc": "止まらない鼓動・緊張"},
        {"text": "トクン…", "font": "mincho", "angle": -6.0, "text_color": (240, 105, 145, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.5, "font_size_ratio": 0.042, "desc": "静かな胸のときめき"},
        {"text": "キュン…", "font": "kiwi", "angle": 8.0, "text_color": (255, 105, 165, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.044, "desc": "愛おしさで胸が締め付けられる"},
        {"text": "ズキュン！", "font": "bold", "angle": -14.0, "text_color": (255, 50, 110, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 4.0, "font_size_ratio": 0.050, "desc": "ハートを撃ち抜かれた衝撃"},
        {"text": "チュッ", "font": "zenmaru", "angle": 12.0, "text_color": (255, 75, 110, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.045, "desc": "キス・口づけの音"},
        {"text": "ちゅっ♡", "font": "kiwi", "angle": 10.0, "text_color": (255, 90, 150, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.044, "desc": "可愛いキス・頬へのキス"},
        {"text": "ハァ…", "font": "mincho", "angle": 0.0, "text_color": (190, 110, 220, 255), "stroke_color": (255, 255, 255, 230), "stroke_width": 2.5, "font_size_ratio": 0.040, "desc": "熱い吐息・ため息"},
        {"text": "ビクッ", "font": "bold", "angle": -8.0, "text_color": (255, 120, 60, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.2, "font_size_ratio": 0.046, "desc": "突然の接触や驚き"},
        {"text": "カァァ…", "font": "kiwi", "angle": 6.0, "text_color": (255, 90, 85, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.8, "font_size_ratio": 0.044, "desc": "顔の赤面・照れ"},
        {"text": "ボッ", "font": "bold", "angle": -10.0, "text_color": (255, 70, 70, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.046, "desc": "急激な赤面・羞恥"},
        {"text": "モジモジ…", "font": "yomogi", "angle": -4.0, "text_color": (235, 120, 160, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 2.8, "font_size_ratio": 0.040, "desc": "恥ずかしがる仕草"},
        {"text": "じーっ…", "font": "zenmaru", "angle": 0.0, "text_color": (120, 140, 230, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "熱心に見つめる視線"},
        {"text": "ふわぁ…", "font": "kiwi", "angle": 7.0, "text_color": (255, 140, 185, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 2.8, "font_size_ratio": 0.042, "desc": "恍惚・うっとりした表情"},
        {"text": "トロ〜ン", "font": "kiwi", "angle": -7.0, "text_color": (230, 100, 190, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.043, "desc": "蕩けた瞳・甘い雰囲気"},
        {"text": "ギュウッ", "font": "bold", "angle": 9.0, "text_color": (255, 85, 145, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.046, "desc": "強く抱きしめる"},
    ],
    "😄 日常・リアクション": [
        {"text": "パシャッ", "font": "bold", "angle": -10.0, "text_color": (0, 165, 245, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.045, "desc": "スマホ写真・自撮りシャッター"},
        {"text": "チラッ", "font": "kiwi", "angle": -5.0, "text_color": (100, 130, 220, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "横目で見る・視線"},
        {"text": "ギュッ", "font": "zenmaru", "angle": 8.0, "text_color": (255, 95, 175, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.046, "desc": "抱きしめる・手を握る"},
        {"text": "スッ…", "font": "mincho", "angle": -4.0, "text_color": (90, 100, 130, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.5, "font_size_ratio": 0.040, "desc": "静かに近寄る・手を伸ばす"},
        {"text": "ニコッ", "font": "kiwi", "angle": 4.0, "text_color": (255, 150, 40, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "満面の笑み・微笑み"},
        {"text": "ピクッ", "font": "bold", "angle": -8.0, "text_color": (130, 90, 200, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "気付き・反応"},
        {"text": "パチッ☆", "font": "zenmaru", "angle": 10.0, "text_color": (255, 170, 30, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.2, "font_size_ratio": 0.044, "desc": "ウインク・目が合う"},
        {"text": "くるっ", "font": "kiwi", "angle": -9.0, "text_color": (80, 180, 230, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "振り返る・ターン"},
        {"text": "ひょこっ", "font": "yomogi", "angle": 12.0, "text_color": (110, 195, 110, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "物陰から顔を出す"},
        {"text": "なでなで", "font": "kiwi", "angle": -6.0, "text_color": (255, 140, 100, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "頭を撫でる"},
        {"text": "ぽんぽん", "font": "zenmaru", "angle": 6.0, "text_color": (245, 155, 80, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "肩や頭を軽く叩く"},
        {"text": "ぷいっ", "font": "zenmaru", "angle": -11.0, "text_color": (220, 100, 140, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "そっぽを向く・ツンデレ"},
        {"text": "むぅ…", "font": "kiwi", "angle": 5.0, "text_color": (210, 95, 115, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 2.8, "font_size_ratio": 0.042, "desc": "頬を膨らませる・不満"},
        {"text": "ごくっ…", "font": "mincho", "angle": -6.0, "text_color": (100, 120, 170, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.8, "font_size_ratio": 0.042, "desc": "生唾を飲み込む・緊張"},
        {"text": "コクリ", "font": "zenmaru", "angle": 4.0, "text_color": (90, 150, 210, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 2.8, "font_size_ratio": 0.040, "desc": "静かに頷く"},
        {"text": "パタパタ", "font": "yomogi", "angle": -8.0, "text_color": (120, 180, 150, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "慌ただしく動く・手を振る"},
    ],
    "💥 迫力・コメディ": [
        {"text": "ガーン！", "font": "bold", "angle": 14.0, "text_color": (65, 75, 150, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.8, "font_size_ratio": 0.052, "desc": "ショック・落胆"},
        {"text": "ビシッ", "font": "bold", "angle": -12.0, "text_color": (255, 160, 0, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.048, "desc": "鋭いツッコミ・指差し"},
        {"text": "ええっ!?", "font": "bold", "angle": -10.0, "text_color": (240, 50, 60, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.048, "desc": "驚愕・疑問の叫び"},
        {"text": "ドヤァ", "font": "bold", "angle": 8.0, "text_color": (160, 60, 210, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.046, "desc": "得意気・誇らしげ"},
        {"text": "バァン！", "font": "bold", "angle": -15.0, "text_color": (240, 30, 45, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 4.5, "font_size_ratio": 0.056, "desc": "ドア開閉・登場・爆発"},
        {"text": "ドォン！", "font": "bold", "angle": -12.0, "text_color": (220, 40, 40, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 4.5, "font_size_ratio": 0.056, "desc": "圧倒的なインパクト"},
        {"text": "ゴゴゴ…", "font": "bold", "angle": -6.0, "text_color": (90, 40, 130, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.050, "desc": "重圧・緊迫のプレッシャー"},
        {"text": "ガタッ", "font": "bold", "angle": 11.0, "text_color": (210, 110, 30, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.048, "desc": "椅子から立ち上がる・動揺"},
        {"text": "バッ！", "font": "bold", "angle": -14.0, "text_color": (235, 80, 30, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.8, "font_size_ratio": 0.048, "desc": "素早い動き・飛び出し"},
        {"text": "ギクッ", "font": "bold", "angle": -9.0, "text_color": (70, 110, 200, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.046, "desc": "図星を突かれた動揺"},
        {"text": "ピキッ", "font": "bold", "angle": 12.0, "text_color": (230, 40, 80, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.2, "font_size_ratio": 0.044, "desc": "怒りの血管・イラッ"},
        {"text": "ざわ…ざわ…", "font": "mincho", "angle": -7.0, "text_color": (80, 90, 110, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.8, "font_size_ratio": 0.042, "desc": "不穏な空気・周囲の動揺"},
        {"text": "ズコーッ", "font": "bold", "angle": 15.0, "text_color": (240, 140, 20, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.048, "desc": "ずっこける・拍子抜け"},
        {"text": "しーん…", "font": "mincho", "angle": 0.0, "text_color": (100, 130, 180, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.5, "font_size_ratio": 0.042, "desc": "静まり返る空気"},
        {"text": "キラーン✨", "font": "bold", "angle": -10.0, "text_color": (255, 195, 0, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.046, "desc": "ひらめき・決めポーズ"},
        {"text": "ズシーン", "font": "bold", "angle": 5.0, "text_color": (70, 60, 110, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.8, "font_size_ratio": 0.050, "desc": "重い一言・落ち込み"},
    ],
    "🌙 感情・空気感": [
        {"text": "ふわっ", "font": "kiwi", "angle": -6.0, "text_color": (255, 150, 190, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "柔らかい笑顔・髪が揺れる"},
        {"text": "キラキラ…", "font": "zenmaru", "angle": -8.0, "text_color": (255, 190, 40, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.044, "desc": "眩しい笑顔・輝き"},
        {"text": "しゅん…", "font": "yomogi", "angle": 8.0, "text_color": (110, 135, 195, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 2.8, "font_size_ratio": 0.040, "desc": "元気をなくす・しょんぼり"},
        {"text": "うるうる…", "font": "kiwi", "angle": -5.0, "text_color": (90, 165, 240, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 2.8, "font_size_ratio": 0.042, "desc": "涙目・上目遣い"},
        {"text": "ぽろぽろ", "font": "mincho", "angle": 4.0, "text_color": (80, 150, 230, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.5, "font_size_ratio": 0.042, "desc": "こぼれ落ちる涙"},
        {"text": "ぐすっ", "font": "kiwi", "angle": -7.0, "text_color": (100, 140, 210, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 2.8, "font_size_ratio": 0.040, "desc": "鼻をすする・泣き顔"},
        {"text": "ぽかーん", "font": "yomogi", "angle": 6.0, "text_color": (150, 150, 175, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 2.8, "font_size_ratio": 0.042, "desc": "呆気にとられる"},
        {"text": "ゾワッ", "font": "mincho", "angle": -11.0, "text_color": (110, 70, 170, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.8, "font_size_ratio": 0.044, "desc": "鳥肌・悪寒・畏怖"},
        {"text": "じわっ…", "font": "mincho", "angle": -4.0, "text_color": (220, 110, 150, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.5, "font_size_ratio": 0.040, "desc": "涙や汗が滲む・感動"},
        {"text": "むぎゅっ", "font": "zenmaru", "angle": 9.0, "text_color": (255, 115, 165, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.2, "font_size_ratio": 0.044, "desc": "頬や胸が押し潰れる密着感"},
        {"text": "ぴとっ", "font": "kiwi", "angle": -8.0, "text_color": (255, 130, 175, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.042, "desc": "寄り添う・肌が触れる"},
        {"text": "すやぁ…", "font": "yomogi", "angle": 5.0, "text_color": (140, 175, 235, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 2.8, "font_size_ratio": 0.040, "desc": "心地よい眠り・寝顔"},
    ],
    "🔞 艶音・吐息 (NSFW)": [
        {"text": "あんっ…", "font": "kiwi", "angle": -10.0, "text_color": (255, 70, 130, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.046, "desc": "甘いあえぎ・吐息"},
        {"text": "んっ…♡", "font": "kiwi", "angle": 8.0, "text_color": (255, 85, 145, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.044, "desc": "声を堪える吐息"},
        {"text": "ふぁ…♡", "font": "mincho", "angle": -6.0, "text_color": (245, 95, 155, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.6, "font_size_ratio": 0.042, "desc": "脱力する甘い吐息"},
        {"text": "ハァ…ハァ…", "font": "mincho", "angle": -5.0, "text_color": (230, 75, 140, 255), "stroke_color": (255, 255, 255, 230), "stroke_width": 2.5, "font_size_ratio": 0.042, "desc": "激しい息遣い・興奮"},
        {"text": "びくっ", "font": "zenmaru", "angle": 10.0, "text_color": (255, 100, 160, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.0, "font_size_ratio": 0.044, "desc": "身体の震え・感度"},
        {"text": "びくびくっ", "font": "bold", "angle": -12.0, "text_color": (255, 65, 135, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.2, "font_size_ratio": 0.046, "desc": "連続する痙攣・絶頂"},
        {"text": "ゾクッ…", "font": "mincho", "angle": -12.0, "text_color": (140, 60, 205, 255), "stroke_color": (255, 255, 255, 230), "stroke_width": 2.8, "font_size_ratio": 0.045, "desc": "背筋の快感・ゾクゾク"},
        {"text": "じゅる…", "font": "mincho", "angle": -7.0, "text_color": (190, 60, 150, 255), "stroke_color": (255, 255, 255, 230), "stroke_width": 2.5, "font_size_ratio": 0.042, "desc": "艶めかしい口づけ・唾液音"},
        {"text": "ちゅぷ…", "font": "kiwi", "angle": 7.0, "text_color": (235, 75, 145, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.8, "font_size_ratio": 0.042, "desc": "深いキス・水音"},
        {"text": "んちゅ…", "font": "kiwi", "angle": -8.0, "text_color": (245, 80, 135, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.8, "font_size_ratio": 0.042, "desc": "絡み合う口づけ"},
        {"text": "れろ…", "font": "mincho", "angle": 6.0, "text_color": (220, 65, 135, 255), "stroke_color": (255, 255, 255, 230), "stroke_width": 2.6, "font_size_ratio": 0.042, "desc": "舌遣い・舐める音"},
        {"text": "ぬちゅ…", "font": "kiwi", "angle": 5.0, "text_color": (235, 65, 115, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 3.0, "font_size_ratio": 0.044, "desc": "密着・愛撫の艶音"},
        {"text": "くちゅ…", "font": "mincho", "angle": -9.0, "text_color": (225, 60, 125, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.8, "font_size_ratio": 0.042, "desc": "濡れた粘膜音"},
        {"text": "ぴちゃ…", "font": "mincho", "angle": 8.0, "text_color": (210, 80, 160, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.6, "font_size_ratio": 0.042, "desc": "滴る水音・愛液"},
        {"text": "とろぉ…", "font": "kiwi", "angle": -6.0, "text_color": (240, 90, 170, 255), "stroke_color": (255, 255, 255, 240), "stroke_width": 2.8, "font_size_ratio": 0.044, "desc": "とろける感触・溢れる様子"},
        {"text": "ぷるぷる…", "font": "zenmaru", "angle": 5.0, "text_color": (255, 110, 160, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 2.8, "font_size_ratio": 0.040, "desc": "震える身体・柔肌"},
        {"text": "もみっ…", "font": "bold", "angle": -9.0, "text_color": (255, 85, 130, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.2, "font_size_ratio": 0.044, "desc": "柔らかな感触・愛撫"},
        {"text": "どくん…！", "font": "bold", "angle": -11.0, "text_color": (240, 45, 105, 255), "stroke_color": (255, 255, 255, 255), "stroke_width": 3.5, "font_size_ratio": 0.048, "desc": "高まる脈動・絶頂感"},
    ]
}


class SFXPaletteDialog(QDialog):
    """
    Floating Manga SFX (Onomatopoeia) preset palette.
    Clicking any item creates an editable vector typography SFX item on canvas.
    """
    sfx_picked = Signal(BubbleConfig)

    def __init__(self, parent=None):
        super().__init__(parent)
        total_count = sum(len(v) for v in SFX_PRESETS.values())
        self.setWindowTitle(f"⚡ 漫画オノマトペ・擬音プリセット集（全{total_count}種）")
        self.resize(640, 500)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        lbl_desc = QLabel("⚡ クリックするとキャンバスの中央に高品質な描き文字（SFX）が追加されます（後から回転・色変更も可能）:")
        lbl_desc.setStyleSheet("font-weight: bold; color: #4da6ff;")
        lbl_desc.setWordWrap(True)
        main_layout.addWidget(lbl_desc)

        # Tab widget for categories
        self.tabs = QTabWidget()
        for cat_name, items in SFX_PRESETS.items():
            page = self._create_category_page(items)
            self.tabs.addTab(page, f"{cat_name} ({len(items)})")
        main_layout.addWidget(self.tabs, 1)

        # Quick custom SFX creator
        grp_custom = QGroupBox("✨ 自由入力オノマトペ")
        h_custom = QHBoxLayout(grp_custom)
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText("例: ズキュン、モジモジ、ゴゴゴ…（好きな文字を入力して追加）")
        self.txt_custom.returnPressed.connect(self._add_custom_sfx)
        h_custom.addWidget(self.txt_custom, 1)

        btn_add_custom = QPushButton("＋ キャンバスに追加")
        btn_add_custom.setStyleSheet("background-color: #0078d7; font-weight: bold; padding: 6px 14px;")
        btn_add_custom.clicked.connect(self._add_custom_sfx)
        h_custom.addWidget(btn_add_custom)
        main_layout.addWidget(grp_custom)

        # Close button
        btn_close = QPushButton("閉じる")
        btn_close.clicked.connect(self.accept)
        main_layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignRight)

    def _create_category_page(self, items: List[Dict[str, Any]]) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(8)

        for i, item in enumerate(items):
            btn = QPushButton(f"{item['text']}\n({item['desc']})")
            btn.setToolTip(f"{item['desc']}\nフォント: {item['font']} / 初期角度: {item['angle']}°")
            btn.setMinimumHeight(54)

            # Stylize button based on SFX text color
            r, g, b, a = item["text_color"]
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 13px;
                    font-weight: bold;
                    color: rgb({r}, {g}, {b});
                    background-color: #2b2b35;
                    border: 1px solid #444;
                    border-radius: 6px;
                    padding: 4px 8px;
                }}
                QPushButton:hover {{
                    background-color: #3b3b48;
                    border: 1.5px solid rgb({r}, {g}, {b});
                }}
            """)
            btn.clicked.connect(lambda _, it=item: self._on_item_clicked(it))
            row = i // 3
            col = i % 3
            grid.addWidget(btn, row, col)

        scroll.setWidget(container)
        return scroll

    def _on_item_clicked(self, item_dict: Dict[str, Any]):
        cfg = BubbleConfig(
            text=item_dict["text"],
            type="sfx",
            font=item_dict.get("font", "bold"),
            center=(0.5, 0.5),
            angle=float(item_dict.get("angle", -10.0)),
            font_size_ratio=float(item_dict.get("font_size_ratio", 0.045)),
            text_color=item_dict.get("text_color", (255, 90, 110, 255)),
            stroke_width=float(item_dict.get("stroke_width", 3.5)),
            stroke_color=item_dict.get("stroke_color", (255, 255, 255, 255))
        )
        self.sfx_picked.emit(cfg)

    def _add_custom_sfx(self):
        text = self.txt_custom.text().strip()
        if not text:
            return
        cfg = BubbleConfig(
            text=text,
            type="sfx",
            font="bold",
            center=(0.5, 0.5),
            angle=-10.0,
            font_size_ratio=0.045,
            text_color=(255, 90, 110, 255),
            stroke_width=3.5,
            stroke_color=(255, 255, 255, 255)
        )
        self.sfx_picked.emit(cfg)
        self.txt_custom.clear()

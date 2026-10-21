"""
gui.inspector
~~~~~~~~~~~~~
Sidebar property editor for speech bubbles and monologues.
Provides live two-way synchronization between UI controls and the selected BubbleGraphicsItem.
Supports text flow direction (RTL/LTR), text deformation/shadow effects,
custom padding ratio, SFX palettes, and runtime bilingual (JA/EN) localization.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPlainTextEdit,
    QComboBox, QSlider, QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton,
    QGroupBox, QColorDialog, QScrollArea, QFrame, QSizePolicy
)

from comic_bubble.models import BubbleConfig
from comic_bubble.typography import auto_wrap_japanese_text
from .bubble_item import BubbleGraphicsItem
from .i18n import tr, register_language_listener


class ColorButton(QPushButton):
    """Button showing a color swatch that opens QColorDialog on click."""
    color_changed = Signal(tuple)

    def __init__(self, initial_rgba=(255, 255, 255, 255), parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rgba = initial_rgba
        self.update_swatch()
        self.clicked.connect(self._pick_color)

    def set_rgba(self, rgba):
        self.rgba = rgba
        self.update_swatch()

    def update_swatch(self):
        r, g, b = self.rgba[0], self.rgba[1], self.rgba[2]
        a = self.rgba[3] if len(self.rgba) > 3 else 255
        self.setStyleSheet(
            f"background-color: rgba({r}, {g}, {b}, {a / 255.0:.2f});"
            f"border: 1px solid #777; border-radius: 4px;"
        )

    def _pick_color(self):
        cur = QColor(self.rgba[0], self.rgba[1], self.rgba[2], self.rgba[3] if len(self.rgba) > 3 else 255)
        color = QColorDialog.getColor(cur, self, tr("色を選択", "Select Color"), QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            new_rgba = (color.red(), color.green(), color.blue(), color.alpha())
            self.rgba = new_rgba
            self.update_swatch()
            self.color_changed.emit(new_rgba)


PALETTE_COLORS = [
    (255, 255, 255), (30, 30, 35), (235, 50, 60), (255, 130, 30), (255, 215, 40), (110, 200, 70),
    (40, 190, 200), (50, 110, 235), (140, 80, 220), (255, 110, 180), (150, 90, 50), (150, 150, 155),
]


class PalettePicker(QWidget):
    """Row of quick color swatches plus a custom color button."""
    color_picked = Signal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        for i, (r, g, b) in enumerate(PALETTE_COLORS):
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"#{r:02X}{g:02X}{b:02X}")
            btn.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid #777; border-radius: 3px;")
            btn.clicked.connect(lambda checked=False, c=(r, g, b, 255): self.color_picked.emit(c))
            grid.addWidget(btn, i // 6, i % 6)
        self.btn_custom = ColorButton((255, 255, 255, 255))
        self.btn_custom.setFixedSize(36, 22)
        self.btn_custom.setToolTip(tr("その他の色…", "Custom Color..."))
        self.btn_custom.color_changed.connect(self.color_picked.emit)
        grid.addWidget(self.btn_custom, 0, 6, 2, 1)

    def set_rgba(self, rgba):
        self.btn_custom.set_rgba(rgba)


class BubbleInspectorPanel(QWidget):
    """Inspector panel for adjusting all attributes of the currently selected bubble."""

    bubble_updated = Signal()
    delete_requested = Signal()
    duplicate_requested = Signal()
    flip_all_tails_requested = Signal()
    spread_align_requested = Signal(str)
    sample_paper_color_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item: Optional[BubbleGraphicsItem] = None
        self._block_signals = False

        self.setMinimumWidth(280)
        self.setMaximumWidth(550)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 4, 6)
        main_layout.setSpacing(6)

        # --- 1. Pinned Header & Actions ---
        self.lbl_title = QLabel("💬 吹き出しプロパティ")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.lbl_title.setWordWrap(True)
        main_layout.addWidget(self.lbl_title)

        header_btn_layout = QHBoxLayout()
        header_btn_layout.setSpacing(6)
        self.btn_dup = QPushButton("📋 複製")
        self.btn_dup.setToolTip("選択中の吹き出しを複製 (Ctrl+D)")
        self.btn_dup.clicked.connect(self.duplicate_requested.emit)
        header_btn_layout.addWidget(self.btn_dup)

        self.btn_del = QPushButton("🗑️ 削除")
        self.btn_del.setStyleSheet("color: #ff4d4f;")
        self.btn_del.setToolTip("選択中の吹き出しを削除 (Deleteキー)")
        self.btn_del.clicked.connect(self.delete_requested.emit)
        header_btn_layout.addWidget(self.btn_del)
        main_layout.addLayout(header_btn_layout)

        # Scroll area for scrollable property groups
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.container = QWidget()
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(2, 2, 6, 8)

        # --- 2. Text Input ---
        self.grp_text = QGroupBox("セリフ・テキスト")
        vbox_text = QVBoxLayout(self.grp_text)

        self.txt_edit = QPlainTextEdit()
        self.txt_edit.setPlaceholderText("セリフを入力してください...\n（縦書き自動組版）")
        self.txt_edit.setMinimumWidth(100)
        self.txt_edit.setMinimumHeight(75)
        self.txt_edit.setMaximumHeight(110)
        self.txt_edit.textChanged.connect(self._on_text_changed)
        vbox_text.addWidget(self.txt_edit)

        tag_grid = QGridLayout()
        tag_grid.setSpacing(4)
        self.btn_big = QPushButton("🔍 強調 (大)")
        self.btn_big.setToolTip("選択文字または末尾を大きく強調 (<big>タグ)")
        self.btn_big.clicked.connect(lambda: self._insert_tags("<big>", "</big>"))
        tag_grid.addWidget(self.btn_big, 0, 0)

        self.btn_small = QPushButton("🔉 小声 (小)")
        self.btn_small.setToolTip("選択文字または末尾を小さく (<small>タグ)")
        self.btn_small.clicked.connect(lambda: self._insert_tags("<small>", "</small>"))
        tag_grid.addWidget(self.btn_small, 0, 1)

        self.btn_paren = QPushButton("💬 （心の声）")
        self.btn_paren.setToolTip("括弧で囲んでモノローグ風に")
        self.btn_paren.clicked.connect(lambda: self._insert_tags("（", "）"))
        tag_grid.addWidget(self.btn_paren, 1, 0)

        self.btn_wrap = QPushButton("⏎ 自動改行")
        self.btn_wrap.setToolTip("長い文を縦書きに適したバランスの良い行に自動分割します")
        self.btn_wrap.clicked.connect(self._auto_wrap_text)
        tag_grid.addWidget(self.btn_wrap, 1, 1)
        vbox_text.addLayout(tag_grid)

        self.content_layout.addWidget(self.grp_text)

        # --- 3. Bubble Style ---
        self.grp_style = QGroupBox("吹き出しの形状・フォント")
        vbox_style = QVBoxLayout(self.grp_style)

        # Bubble Shape
        row_type = QHBoxLayout()
        self.lbl_type = QLabel("形状:")
        row_type.addWidget(self.lbl_type)
        self.combo_type = QComboBox()
        self.combo_type.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_type.setMinimumContentsLength(6)
        self.combo_type.addItem("カプセル (標準セリフ)", "capsule")
        self.combo_type.addItem("もこもこ雲 (楽しい・自撮り)", "cloud")
        self.combo_type.addItem("囁き点線 (ヒソヒソ・小声)", "whisper")
        self.combo_type.addItem("叫び/爆発 (ツッコミ・驚き)", "scream")
        self.combo_type.addItem("楕円 (クラシック)", "oval")
        self.combo_type.addItem("角丸四角 (ナレーション)", "box")
        self.combo_type.addItem("枠なし浮遊モノローグ (心の声)", "floating")
        self.combo_type.addItem("既存枠利用 (枠・背景なし)", "none")
        self.combo_type.addItem("既存枠の文字隠し (枠なし・下地塗り)", "patch")
        self.combo_type.addItem("描き文字/オノマトペ (SFX)", "sfx")
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        row_type.addWidget(self.combo_type, 1)
        vbox_style.addLayout(row_type)

        self.chk_hide_frame = QCheckBox("既存枠に合わせる (枠なし)")
        self.chk_hide_frame.setToolTip("イラスト内に既に描かれている吹き出しの中に文字だけを配置したい場合にチェックします。")
        self.chk_hide_frame.toggled.connect(self._on_hide_frame_toggled)
        vbox_style.addWidget(self.chk_hide_frame)

        self.chk_cover_old_text = QCheckBox("元の文字を下地色で隠す")
        self.chk_cover_old_text.setToolTip("既存の吹き出し内に文字が入っている場合、枠線なしで背景色（白など）を塗りつぶして元の文字を隠します。")
        self.chk_cover_old_text.toggled.connect(self._on_cover_old_text_toggled)
        vbox_style.addWidget(self.chk_cover_old_text)

        self.btn_sample_paper = QPushButton("💧 下地色を自動取得")
        self.btn_sample_paper.setToolTip("配置した場所の周囲から元の吹き出しの紙の色（白・クリーム色など）を自動でスポイト取得します。")
        self.btn_sample_paper.clicked.connect(self._on_sample_paper_clicked)
        vbox_style.addWidget(self.btn_sample_paper)

        # Font
        row_font = QHBoxLayout()
        self.lbl_font = QLabel("フォント:")
        row_font.addWidget(self.lbl_font)
        self.combo_font = QComboBox()
        self.combo_font.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_font.setMinimumContentsLength(6)
        self.combo_font.addItem("Kiwi Maru (手書き・表情豊か)", "kiwi")
        self.combo_font.addItem("Zen Maru Gothic (丸ゴシック・標準)", "zenmaru")
        self.combo_font.addItem("Shippori Mincho (明朝・心の声)", "mincho")
        self.combo_font.addItem("Dela Gothic / Bold (太字・SFX)", "bold")
        self.combo_font.addItem("Yomogi (カジュアル手書き)", "yomogi")
        self.combo_font.currentIndexChanged.connect(self._on_font_changed)
        row_font.addWidget(self.combo_font, 1)
        vbox_style.addLayout(row_font)

        # Font Size Ratio
        row_size = QHBoxLayout()
        self.lbl_size = QLabel("文字サイズ:")
        row_size.addWidget(self.lbl_size)
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(10, 90)
        self.slider_size.valueChanged.connect(self._on_size_slider_changed)

        self.spin_size = QDoubleSpinBox()
        self.spin_size.setRange(0.010, 0.090)
        self.spin_size.setSingleStep(0.002)
        self.spin_size.setDecimals(3)
        self.spin_size.setFixedWidth(64)
        self.spin_size.valueChanged.connect(self._on_size_spin_changed)

        row_size.addWidget(self.slider_size, 1)
        row_size.addWidget(self.spin_size)
        vbox_style.addLayout(row_size)

        # Reading Direction (RTL / LTR)
        self.row_direction = QHBoxLayout()
        self.row_direction.setContentsMargins(0, 0, 0, 0)
        self.lbl_direction = QLabel("行の進行:")
        self.row_direction.addWidget(self.lbl_direction)
        self.combo_direction = QComboBox()
        self.combo_direction.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_direction.setMinimumContentsLength(6)
        self.combo_direction.addItem("右から左 (右→左・標準)", "rtl")
        self.combo_direction.addItem("左から右 (左→右)", "ltr")
        self.combo_direction.currentIndexChanged.connect(self._on_direction_changed)
        self.row_direction.addWidget(self.combo_direction, 1)
        self.widget_direction = QWidget()
        self.widget_direction.setLayout(self.row_direction)
        vbox_style.addWidget(self.widget_direction)

        self.content_layout.addWidget(self.grp_style)

        # --- 4. Bubble size (relative to the text) ---
        self.grp_pad = QGroupBox("吹き出しの大きさ（文字に対する余白）")
        vbox_pad = QVBoxLayout(self.grp_pad)
        self.chk_pad_manual = QCheckBox("余白を手動で調整する")
        self.chk_pad_manual.setToolTip("オフ: 自動サイズ / オン: 文字サイズに対する余白倍率を指定")
        self.chk_pad_manual.toggled.connect(self._on_pad_manual_toggled)
        vbox_pad.addWidget(self.chk_pad_manual)

        self.pad_sliders = {}
        self.pad_labels = {}
        self.pad_row_labels = {}
        for key, label in (("padding_ratio_x", "横の余白:"), ("padding_ratio_y", "縦の余白:")):
            row = QHBoxLayout()
            qlbl = QLabel(label)
            self.pad_row_labels[key] = qlbl
            row.addWidget(qlbl)
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(110, 400)
            lbl = QLabel("")
            lbl.setFixedWidth(40)
            sl.valueChanged.connect(lambda v, k=key: self._on_pad_slider(k, v))
            row.addWidget(sl, 1)
            row.addWidget(lbl)
            vbox_pad.addLayout(row)
            self.pad_sliders[key] = sl
            self.pad_labels[key] = lbl
        self.lbl_pad_tip = QLabel("💡 文字を大きく・吹き出しを小さく（ぴったり）したいときは余白を下げます。")
        self.lbl_pad_tip.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_pad_tip.setWordWrap(True)
        vbox_pad.addWidget(self.lbl_pad_tip)
        self.content_layout.addWidget(self.grp_pad)

        # --- 5. SFX Settings (visible only for sfx, placed prominently at top) ---
        self.grp_sfx = QGroupBox("オノマトペ (SFX) 回転・フチ取り")
        vbox_sfx = QVBoxLayout(self.grp_sfx)

        # Rotation slider + spinbox
        row_angle = QHBoxLayout()
        self.lbl_angle = QLabel("回転角度:")
        row_angle.addWidget(self.lbl_angle)
        self.slider_angle = QSlider(Qt.Orientation.Horizontal)
        self.slider_angle.setRange(-180, 180)
        self.slider_angle.valueChanged.connect(self._on_angle_slider_changed)

        self.spin_angle = QSpinBox()
        self.spin_angle.setRange(-180, 180)
        self.spin_angle.setSuffix("°")
        self.spin_angle.setFixedWidth(60)
        self.spin_angle.valueChanged.connect(self._on_angle_spin_changed)

        row_angle.addWidget(self.slider_angle, 1)
        row_angle.addWidget(self.spin_angle)
        vbox_sfx.addLayout(row_angle)

        # Quick preset rotation buttons (2x3 grid)
        grid_presets = QGridLayout()
        grid_presets.setSpacing(4)
        presets = [("-45°", -45), ("-15°", -15), ("0° 水平", 0), ("+15°", 15), ("+45°", 45), ("90° 垂直", 90)]
        for i, (label, deg) in enumerate(presets):
            btn = QPushButton(label)
            btn.setStyleSheet("padding: 3px 2px; font-size: 11px;")
            btn.clicked.connect(lambda checked=False, d=deg: self._set_angle_preset(d))
            grid_presets.addWidget(btn, i // 3, i % 3)
        vbox_sfx.addLayout(grid_presets)

        # Stroke (フチ取り) settings
        row_stroke = QHBoxLayout()
        self.lbl_stroke_w = QLabel("フチ太さ:")
        row_stroke.addWidget(self.lbl_stroke_w)
        self.slider_stroke = QSlider(Qt.Orientation.Horizontal)
        self.slider_stroke.setRange(0, 12)
        self.slider_stroke.setValue(3)
        self.slider_stroke.valueChanged.connect(self._on_stroke_width_changed)
        self.lbl_stroke = QLabel("3px")
        self.lbl_stroke.setFixedWidth(30)
        row_stroke.addWidget(self.slider_stroke, 1)
        row_stroke.addWidget(self.lbl_stroke)

        self.lbl_stroke_col = QLabel("色:")
        row_stroke.addWidget(self.lbl_stroke_col)
        self.btn_stroke_col = ColorButton((255, 255, 255, 255))
        self.btn_stroke_col.color_changed.connect(self._on_stroke_color_changed)
        row_stroke.addWidget(self.btn_stroke_col)
        vbox_sfx.addLayout(row_stroke)

        self.lbl_sfx_pal_text = QLabel("文字色 (パレット):")
        vbox_sfx.addWidget(self.lbl_sfx_pal_text)
        self.palette_text = PalettePicker()
        self.palette_text.color_picked.connect(self._on_text_palette)
        vbox_sfx.addWidget(self.palette_text)

        self.lbl_sfx_pal_stroke = QLabel("フチ色 (パレット):")
        vbox_sfx.addWidget(self.lbl_sfx_pal_stroke)
        self.palette_stroke = PalettePicker()
        self.palette_stroke.color_picked.connect(self._on_stroke_palette)
        vbox_sfx.addWidget(self.palette_stroke)

        self.lbl_sfx_tip = QLabel("💡 キャンバス上の緑のハンドルをドラッグしても自由に回転できます。")
        self.lbl_sfx_tip.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_sfx_tip.setWordWrap(True)
        vbox_sfx.addWidget(self.lbl_sfx_tip)

        self.content_layout.addWidget(self.grp_sfx)

        # --- 6. Text effects: shadow & deformation ---
        self.grp_fx = QGroupBox("文字の効果・変形")
        vbox_fx = QVBoxLayout(self.grp_fx)

        self.chk_shadow = QCheckBox("影をつける")
        self.chk_shadow.toggled.connect(self._on_shadow_toggled)
        vbox_fx.addWidget(self.chk_shadow)

        self.fx_sliders = {}
        self.fx_labels = {}
        self.fx_row_labels = {}

        def add_fx_row(key, label, lo, hi, fmt):
            row = QHBoxLayout()
            qlbl = QLabel(label)
            self.fx_row_labels[key] = qlbl
            row.addWidget(qlbl)
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(lo, hi)
            lbl = QLabel("")
            lbl.setFixedWidth(46)
            sl.valueChanged.connect(lambda v, k=key: self._on_fx_slider(k, v))
            row.addWidget(sl, 1)
            row.addWidget(lbl)
            vbox_fx.addLayout(row)
            self.fx_sliders[key] = sl
            self.fx_labels[key] = (lbl, fmt)
            return row

        row_sd = add_fx_row("shadow_offset", "影の距離:", 0, 20, "{}px")
        row_sb = add_fx_row("shadow_blur", "影のぼかし:", 0, 12, "{}px")
        self.lbl_fx_col = QLabel("色:")
        row_sd.addWidget(self.lbl_fx_col)
        self.btn_shadow_col = ColorButton((0, 0, 0, 170))
        self.btn_shadow_col.color_changed.connect(self._on_shadow_color_changed)
        row_sd.addWidget(self.btn_shadow_col)

        add_fx_row("text_scale_x", "横の伸縮:", 40, 250, "{}%")
        add_fx_row("text_scale_y", "縦の伸縮:", 40, 250, "{}%")
        add_fx_row("text_skew", "傾き(斜体):", -45, 45, "{}°")

        self.btn_fx_reset = QPushButton("↺ 変形をリセット")
        self.btn_fx_reset.clicked.connect(self._on_fx_reset)
        vbox_fx.addWidget(self.btn_fx_reset)
        self.content_layout.addWidget(self.grp_fx)

        # --- 7. Tail Settings ---
        self.grp_tail = QGroupBox("しっぽ（吹き出しの向き）")
        vbox_tail = QVBoxLayout(self.grp_tail)

        self.chk_tail = QCheckBox("しっぽを表示 (口元へ向ける)")
        self.chk_tail.toggled.connect(self._on_tail_toggled)
        vbox_tail.addWidget(self.chk_tail)

        row_tail_flip = QHBoxLayout()
        row_tail_flip.setSpacing(4)
        self.btn_flip_tail = QPushButton("⇄ しっぽ反転")
        self.btn_flip_tail.setStyleSheet("padding: 4px 4px; font-size: 11px;")
        self.btn_flip_tail.setToolTip("選択中の吹き出しのしっぽの向きを左右反転します")
        self.btn_flip_tail.clicked.connect(self._on_flip_single_tail)
        row_tail_flip.addWidget(self.btn_flip_tail)

        self.btn_flip_all_tails = QPushButton("⇄ 全しっぽ反転")
        self.btn_flip_all_tails.setStyleSheet("padding: 4px 4px; font-size: 11px;")
        self.btn_flip_all_tails.setToolTip("キャンバス上のすべての吹き出しのしっぽの向きを一括で左右反転します (Ctrl+Shift+F)")
        self.btn_flip_all_tails.clicked.connect(self.flip_all_tails_requested.emit)
        row_tail_flip.addWidget(self.btn_flip_all_tails)
        vbox_tail.addLayout(row_tail_flip)

        row_spread = QHBoxLayout()
        row_spread.setSpacing(4)
        self.btn_spread_inward = QPushButton("↘↙ 見開き内向")
        self.btn_spread_inward.setStyleSheet("padding: 4px 4px; font-size: 11px;")
        self.btn_spread_inward.setToolTip("見開き用: 左側の吹き出しは右向き(↘)、右側の吹き出しは左向き(↙)に一括整列します")
        self.btn_spread_inward.clicked.connect(lambda: self.spread_align_requested.emit("inward"))
        row_spread.addWidget(self.btn_spread_inward)

        self.btn_spread_outward = QPushButton("↙↘ 見開き外向")
        self.btn_spread_outward.setStyleSheet("padding: 4px 4px; font-size: 11px;")
        self.btn_spread_outward.setToolTip("見開き用: 左側の吹き出しは左向き(↙)、右側の吹き出しは右向き(↘)に一括整列します")
        self.btn_spread_outward.clicked.connect(lambda: self.spread_align_requested.emit("outward"))
        row_spread.addWidget(self.btn_spread_outward)
        vbox_tail.addLayout(row_spread)

        self.lbl_tail_tip = QLabel("💡 オレンジの丸: しっぽの先端（向き・長さ）。水色の四角: しっぽが出る位置。どちらもキャンバス上でドラッグできます。")
        self.lbl_tail_tip.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_tail_tip.setWordWrap(True)
        vbox_tail.addWidget(self.lbl_tail_tip)

        self.btn_anchor_auto = QPushButton("↺ しっぽの出る位置を自動に戻す")
        self.btn_anchor_auto.clicked.connect(self._on_anchor_reset)
        vbox_tail.addWidget(self.btn_anchor_auto)
        self.content_layout.addWidget(self.grp_tail)

        # --- 8. Opacity & Contrast ---
        self.grp_opacity = QGroupBox("透明度 & コントラスト")
        vbox_op = QVBoxLayout(self.grp_opacity)

        self.chk_auto_contrast = QCheckBox("背景に合わせて自動調整")
        self.chk_auto_contrast.setToolTip("背景の明るさに応じて不透明度と光彩を自動最適化 (Auto-Contrast)")
        self.chk_auto_contrast.toggled.connect(self._on_auto_contrast_toggled)
        vbox_op.addWidget(self.chk_auto_contrast)

        row_op = QHBoxLayout()
        self.lbl_opacity_title = QLabel("不透明度:")
        row_op.addWidget(self.lbl_opacity_title)
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.valueChanged.connect(self._on_opacity_changed)
        self.lbl_opacity = QLabel("90%")
        self.lbl_opacity.setFixedWidth(36)
        row_op.addWidget(self.slider_opacity, 1)
        row_op.addWidget(self.lbl_opacity)
        vbox_op.addLayout(row_op)

        self.content_layout.addWidget(self.grp_opacity)

        # --- 9. Colors ---
        self.grp_colors = QGroupBox("カラー設定")
        vbox_col = QVBoxLayout(self.grp_colors)

        grid_col = QGridLayout()
        grid_col.setHorizontalSpacing(10)
        grid_col.setVerticalSpacing(8)

        self.lbl_bg_col = QLabel("背景色:")
        grid_col.addWidget(self.lbl_bg_col, 0, 0)
        self.btn_bg_col = ColorButton()
        self.btn_bg_col.color_changed.connect(self._on_bg_color_changed)
        grid_col.addWidget(self.btn_bg_col, 0, 1)

        self.lbl_text_col = QLabel("文字色:")
        grid_col.addWidget(self.lbl_text_col, 0, 2)
        self.btn_text_col = ColorButton()
        self.btn_text_col.color_changed.connect(self._on_text_color_changed)
        grid_col.addWidget(self.btn_text_col, 0, 3)

        self.lbl_border_col = QLabel("枠線色:")
        grid_col.addWidget(self.lbl_border_col, 1, 0)
        self.btn_border_col = ColorButton()
        self.btn_border_col.color_changed.connect(self._on_border_color_changed)
        grid_col.addWidget(self.btn_border_col, 1, 1)

        self.lbl_halo_col = QLabel("光彩:")
        grid_col.addWidget(self.lbl_halo_col, 1, 2)
        self.btn_halo_col = ColorButton()
        self.btn_halo_col.setToolTip("浮遊モノローグや文字周りの光彩(Halo)カラー")
        self.btn_halo_col.color_changed.connect(self._on_halo_color_changed)
        grid_col.addWidget(self.btn_halo_col, 1, 3)

        grid_col.setColumnStretch(1, 1)
        grid_col.setColumnStretch(3, 1)
        vbox_col.addLayout(grid_col)

        self.row_border_w = QWidget()
        hb = QHBoxLayout(self.row_border_w)
        hb.setContentsMargins(0, 0, 0, 0)
        self.lbl_border_w_title = QLabel("枠の太さ:")
        hb.addWidget(self.lbl_border_w_title)
        self.slider_border_w = QSlider(Qt.Orientation.Horizontal)
        self.slider_border_w.setRange(1, 12)
        self.slider_border_w.valueChanged.connect(self._on_border_width_changed)
        self.lbl_border_w = QLabel("2px")
        self.lbl_border_w.setFixedWidth(34)
        hb.addWidget(self.slider_border_w, 1)
        hb.addWidget(self.lbl_border_w)
        vbox_col.addWidget(self.row_border_w)

        self.content_layout.addWidget(self.grp_colors)
        self.content_layout.addStretch()

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll, 1)

        # Install event filter on wheel-sensitive controls
        for w in (
            self.combo_type, self.combo_font, self.combo_direction,
            self.slider_size, self.spin_size,
            self.slider_angle, self.spin_angle,
            self.slider_stroke, self.slider_opacity, self.slider_border_w,
            *self.pad_sliders.values(),
            *self.fx_sliders.values()
        ):
            w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            w.installEventFilter(self)

        self.set_item(None)
        register_language_listener(self.retranslate_ui)
        self.retranslate_ui()

    def eventFilter(self, obj, event: QEvent) -> bool:
        """Forward mouse wheel events from sliders/comboboxes to the scroll area vertical scrollbar."""
        if event.type() == QEvent.Type.Wheel:
            QApplication.sendEvent(self.scroll.verticalScrollBar(), event)
            return True
        return super().eventFilter(obj, event)

    def sync_from_item(self):
        """Update inspector controls when item properties are changed externally."""
        if not self.current_item or self._block_signals:
            return
        self._block_signals = True
        cfg = self.current_item.config
        self.spin_size.setValue(cfg.font_size_ratio)
        self.slider_size.setValue(int(cfg.font_size_ratio * 1000))
        if hasattr(self, 'slider_angle'):
            ang = int(round(cfg.angle))
            self.slider_angle.setValue(ang)
            self.spin_angle.setValue(ang)
        self._block_signals = False

    def set_item(self, item: Optional[BubbleGraphicsItem]):
        """Bind inspector to the selected item or disable controls if None."""
        if self.current_item and self.current_item != item:
            try:
                self.current_item.changed.disconnect(self.sync_from_item)
            except Exception:
                pass

        self.current_item = item
        if not item:
            self.container.setEnabled(False)
            self.btn_dup.setEnabled(False)
            self.btn_del.setEnabled(False)
            self.lbl_title.setText(tr("💬 吹き出しを選択してください", "💬 Please select a bubble"))
            return

        try:
            item.changed.connect(self.sync_from_item)
        except Exception:
            pass

        self.container.setEnabled(True)
        self.btn_dup.setEnabled(True)
        self.btn_del.setEnabled(True)
        self._block_signals = True

        cfg = item.config
        self.lbl_title.setText(tr("💬 吹き出しプロパティ", "💬 Bubble Properties"))

        # 1. Text
        self.txt_edit.setPlainText(cfg.text)

        # 2. Type
        b_type = cfg.type.lower()
        idx = self.combo_type.findData(b_type)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)
        self.chk_hide_frame.setChecked(b_type in ("none", "patch"))
        self.chk_cover_old_text.setChecked(b_type == "patch")
        self.chk_cover_old_text.setVisible(b_type in ("none", "patch"))
        self.btn_sample_paper.setVisible(b_type == "patch")

        # 3. Font
        f_idx = self.combo_font.findData(cfg.font)
        if f_idx >= 0:
            self.combo_font.setCurrentIndex(f_idx)

        # 4. Font Size & Direction
        self.spin_size.setValue(cfg.font_size_ratio)
        self.slider_size.setValue(int(cfg.font_size_ratio * 1000))
        d_idx = self.combo_direction.findData(getattr(cfg, "reading_direction", "rtl"))
        if d_idx >= 0:
            self.combo_direction.setCurrentIndex(d_idx)
        self.widget_direction.setVisible(b_type != "sfx")

        # 5. SFX Settings
        is_sfx = b_type == "sfx"
        self.grp_sfx.setVisible(is_sfx)
        if is_sfx:
            ang = int(round(cfg.angle))
            self.slider_angle.setValue(ang)
            self.spin_angle.setValue(ang)
            strk = int(cfg.stroke_width)
            self.slider_stroke.setValue(strk)
            self.lbl_stroke.setText(f"{strk}px")
            self.btn_stroke_col.set_rgba(cfg.stroke_color)
            self.palette_text.set_rgba(cfg.text_color)
            self.palette_stroke.set_rgba(cfg.stroke_color)

        # 6. Tail
        has_tail = item.tail_handle.isVisible() and b_type not in ("floating", "none", "patch", "sfx")
        self.chk_tail.setChecked(has_tail)
        self.grp_tail.setVisible(b_type not in ("floating", "none", "patch", "sfx"))

        # 7. Opacity
        self.chk_auto_contrast.setChecked(cfg.visibility_mode == "auto")
        if cfg.bg_alpha is not None:
            op_val = int(cfg.bg_alpha * 100)
        else:
            op_val = 100 if b_type == "patch" else 90
        self.slider_opacity.setValue(op_val)
        self.lbl_opacity.setText(f"{op_val}%")
        self.slider_opacity.setEnabled(cfg.visibility_mode != "auto" or b_type == "patch")

        # 8. Colors & Border
        self.btn_bg_col.set_rgba(cfg.bg_color)
        self.btn_text_col.set_rgba(cfg.text_color)
        self.btn_border_col.set_rgba(cfg.border_color)
        halo_c = cfg.halo_color if cfg.halo_color else (255, 255, 255, 220)
        self.btn_halo_col.set_rgba(halo_c)

        bw_val = max(1, min(12, int(round(cfg.border_width))))
        self.slider_border_w.setValue(bw_val)
        self.lbl_border_w.setText(f"{bw_val}px")
        self.row_border_w.setVisible(b_type not in ("floating", "none", "patch", "sfx"))

        self._load_fx_controls(cfg)
        self.grp_pad.setVisible(b_type not in ("floating", "none", "sfx"))
        self._load_pad_controls(cfg)

        self._block_signals = False

    def _apply_change(self):
        if self._block_signals or not self.current_item:
            return
        self.current_item.update_rendering()
        self.bubble_updated.emit()

    def _insert_tags(self, open_tag: str, close_tag: str):
        cursor = self.txt_edit.textCursor()
        sel = cursor.selectedText()
        if sel:
            cursor.insertText(f"{open_tag}{sel}{close_tag}")
        else:
            cursor.insertText(f"{open_tag}{close_tag}")
            cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, len(close_tag))
            self.txt_edit.setTextCursor(cursor)

    def _auto_wrap_text(self):
        text = self.txt_edit.toPlainText().strip()
        if not text:
            return
        wrapped = auto_wrap_japanese_text(text)
        self.txt_edit.setPlainText(wrapped)

    def _on_text_changed(self):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.text = self.txt_edit.toPlainText()
        self._apply_change()

    def _on_type_changed(self, idx: int):
        if self._block_signals or not self.current_item:
            return
        new_type = self.combo_type.currentData()
        self.current_item.config.type = new_type
        if new_type in ("floating", "none", "patch", "sfx"):
            self.current_item.set_has_tail(False)
            self.chk_tail.setChecked(False)
            self.grp_tail.setVisible(False)
        else:
            self.grp_tail.setVisible(True)

        if new_type == "patch":
            self.current_item.config.bg_alpha = 1.0
            self.current_item.config.text_halo = False
            self.sample_paper_color_requested.emit()
            self.btn_bg_col.set_rgba(self.current_item.config.bg_color)

        self.widget_direction.setVisible(new_type != "sfx")
        self.grp_sfx.setVisible(new_type == "sfx")
        self.row_border_w.setVisible(new_type not in ("floating", "none", "patch", "sfx"))
        self.grp_pad.setVisible(new_type not in ("floating", "none", "sfx"))

        self.chk_hide_frame.blockSignals(True)
        self.chk_hide_frame.setChecked(new_type in ("none", "patch"))
        self.chk_hide_frame.blockSignals(False)

        self.chk_cover_old_text.blockSignals(True)
        self.chk_cover_old_text.setChecked(new_type == "patch")
        self.chk_cover_old_text.setVisible(new_type in ("none", "patch"))
        self.chk_cover_old_text.blockSignals(False)
        self.btn_sample_paper.setVisible(new_type == "patch")

        self._apply_change()

    def _on_hide_frame_toggled(self, checked: bool):
        if self._block_signals or not self.current_item:
            return
        if checked:
            target_type = "patch" if self.chk_cover_old_text.isChecked() else "none"
            idx = self.combo_type.findData(target_type)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)
        else:
            idx = self.combo_type.findData("capsule")
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)

    def _on_cover_old_text_toggled(self, checked: bool):
        if self._block_signals or not self.current_item:
            return
        target_type = "patch" if checked else "none"
        idx = self.combo_type.findData(target_type)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)

    def _on_sample_paper_clicked(self):
        if not self.current_item:
            return
        self.sample_paper_color_requested.emit()
        self.btn_bg_col.set_rgba(self.current_item.config.bg_color)
        self._apply_change()

    def _on_flip_single_tail(self):
        if not self.current_item:
            return
        if not self.current_item.tail_handle.isVisible():
            self.current_item.set_has_tail(True)
            self.chk_tail.blockSignals(True)
            self.chk_tail.setChecked(True)
            self.chk_tail.blockSignals(False)
        self.current_item.flip_tail_horizontal()
        self.bubble_updated.emit()

    def _on_font_changed(self, idx: int):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.font = self.combo_font.currentData()
        self._apply_change()

    def _on_direction_changed(self, idx: int):
        if self._block_signals or not self.current_item:
            return
        dir_val = self.combo_direction.currentData()
        self.current_item.config.reading_direction = dir_val
        self._apply_change()

    def _on_size_slider_changed(self, val: int):
        if self._block_signals or not self.current_item:
            return
        ratio = val / 1000.0
        self._block_signals = True
        self.spin_size.setValue(ratio)
        self._block_signals = False
        self.current_item.config.font_size_ratio = ratio
        self._apply_change()

    def _on_size_spin_changed(self, val: float):
        if self._block_signals or not self.current_item:
            return
        self._block_signals = True
        self.slider_size.setValue(int(val * 1000))
        self._block_signals = False
        self.current_item.config.font_size_ratio = val
        self._apply_change()

    def _on_tail_toggled(self, checked: bool):
        if self._block_signals or not self.current_item:
            return
        self.current_item.set_has_tail(checked)
        self.bubble_updated.emit()

    def _on_anchor_reset(self):
        if self._block_signals or not self.current_item:
            return
        self.current_item.reset_tail_anchor()
        self.bubble_updated.emit()

    def _on_auto_contrast_toggled(self, checked: bool):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.visibility_mode = "auto" if checked else "custom"
        self.slider_opacity.setEnabled(not checked)
        self._apply_change()

    def _on_opacity_changed(self, val: int):
        if self._block_signals or not self.current_item:
            return
        self.lbl_opacity.setText(f"{val}%")
        self.current_item.config.bg_alpha = val / 100.0
        self._apply_change()

    def _on_bg_color_changed(self, rgba):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.bg_color = (rgba[0], rgba[1], rgba[2])
        self._apply_change()

    def _on_text_color_changed(self, rgba):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.text_color = rgba
        self._apply_change()

    def _on_border_color_changed(self, rgba):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.border_color = rgba
        self._apply_change()

    def _on_halo_color_changed(self, rgba):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.halo_color = rgba
        self._apply_change()

    def _on_angle_slider_changed(self, val: int):
        if self._block_signals or not self.current_item:
            return
        self._block_signals = True
        self.spin_angle.setValue(val)
        self._block_signals = False
        self.current_item.config.angle = float(val)
        self._apply_change()

    def _on_angle_spin_changed(self, val: int):
        if self._block_signals or not self.current_item:
            return
        self._block_signals = True
        self.slider_angle.setValue(val)
        self._block_signals = False
        self.current_item.config.angle = float(val)
        self._apply_change()

    def _set_angle_preset(self, deg: int):
        if not self.current_item:
            return
        self._block_signals = True
        self.slider_angle.setValue(deg)
        self.spin_angle.setValue(deg)
        self._block_signals = False
        self.current_item.config.angle = float(deg)
        self._apply_change()

    # --- Padding Ratio Handlers ---
    def _on_pad_manual_toggled(self, checked: bool):
        if self._block_signals or not self.current_item:
            return
        cfg = self.current_item.config
        if checked:
            ts = getattr(cfg, "_text_size", None)
            bw, bh = self.current_item.body_size
            rx = bw / ts[0] if ts and ts[0] > 0 else 1.6
            ry = bh / ts[1] if ts and ts[1] > 0 else 1.3
            cfg.padding_ratio_x = max(1.1, min(4.0, rx))
            cfg.padding_ratio_y = max(1.1, min(4.0, ry))
        else:
            cfg.padding_ratio_x = None
            cfg.padding_ratio_y = None
        self._load_pad_controls(cfg)
        self._apply_change()

    def _on_pad_slider(self, key: str, val: int):
        self.pad_labels[key].setText(f"{val / 100.0:.2f}")
        if self._block_signals or not self.current_item:
            return
        setattr(self.current_item.config, key, val / 100.0)
        self._apply_change()

    def _load_pad_controls(self, cfg):
        prev = self._block_signals
        self._block_signals = True
        manual = cfg.padding_ratio_x is not None or cfg.padding_ratio_y is not None
        self.chk_pad_manual.setChecked(manual)
        ts = getattr(cfg, "_text_size", None)
        bw, bh = self.current_item.body_size if self.current_item else (0, 0)
        auto = {
            "padding_ratio_x": bw / ts[0] if ts and ts[0] > 0 else 1.6,
            "padding_ratio_y": bh / ts[1] if ts and ts[1] > 0 else 1.3,
        }
        for key, sl in self.pad_sliders.items():
            v = getattr(cfg, key)
            if v is None:
                v = auto[key]
            v = max(1.1, min(4.0, v))
            sl.setValue(int(round(v * 100)))
            sl.setEnabled(manual)
            self.pad_labels[key].setText(f"{v:.2f}")
        self._block_signals = prev

    # --- Text Effects & Deform Handlers ---
    def _on_shadow_toggled(self, checked: bool):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.text_shadow = checked
        self._apply_change()

    def _on_shadow_color_changed(self, rgba):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.shadow_color = rgba
        self._apply_change()

    _FX_MAP = {
        "shadow_offset": ("shadow_offset", 1.0),
        "shadow_blur": ("shadow_blur", 1.0),
        "text_scale_x": ("text_scale_x", 100.0),
        "text_scale_y": ("text_scale_y", 100.0),
        "text_skew": ("text_skew", 1.0),
    }

    def _on_fx_slider(self, key: str, val: int):
        lbl, fmt = self.fx_labels[key]
        lbl.setText(fmt.format(val))
        if self._block_signals or not self.current_item:
            return
        attr, div = self._FX_MAP[key]
        setattr(self.current_item.config, attr, val / div)
        self._apply_change()

    def _on_fx_reset(self):
        if not self.current_item:
            return
        cfg = self.current_item.config
        cfg.text_scale_x = cfg.text_scale_y = 1.0
        cfg.text_skew = 0.0
        self._load_fx_controls(cfg)
        self._apply_change()

    def _load_fx_controls(self, cfg):
        prev = self._block_signals
        self._block_signals = True
        self.chk_shadow.setChecked(cfg.text_shadow)
        self.btn_shadow_col.set_rgba(cfg.shadow_color)
        for key, (attr, div) in self._FX_MAP.items():
            v = int(round(getattr(cfg, attr) * div))
            self.fx_sliders[key].setValue(v)
            lbl, fmt = self.fx_labels[key]
            lbl.setText(fmt.format(v))
        self._block_signals = prev

    def _on_border_width_changed(self, val: int):
        self.lbl_border_w.setText(f"{val}px")
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.border_width = float(val)
        self._apply_change()

    def _on_text_palette(self, rgba):
        if not self.current_item:
            return
        self.current_item.config.text_color = rgba
        self.btn_text_col.set_rgba(rgba)
        self.palette_text.set_rgba(rgba)
        self._apply_change()

    def _on_stroke_palette(self, rgba):
        if not self.current_item:
            return
        self.current_item.config.stroke_color = rgba
        self.btn_stroke_col.set_rgba(rgba)
        self.palette_stroke.set_rgba(rgba)
        self._apply_change()

    def _on_stroke_width_changed(self, val: int):
        if self._block_signals or not self.current_item:
            return
        self.lbl_stroke.setText(f"{val}px")
        self.current_item.config.stroke_width = float(val)
        self._apply_change()

    def _on_stroke_color_changed(self, rgba):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.stroke_color = rgba
        self._apply_change()

    def retranslate_ui(self):
        """Update all text in the inspector when UI language changes."""
        if not self.current_item:
            self.lbl_title.setText(tr("💬 吹き出しを選択してください", "💬 Please select a bubble"))
        else:
            self.lbl_title.setText(tr("💬 吹き出しプロパティ", "💬 Bubble Properties"))

        self.btn_dup.setText(tr("📋 複製", "📋 Duplicate"))
        self.btn_dup.setToolTip(tr("選択中の吹き出しを複製 (Ctrl+D)", "Duplicate selected bubble (Ctrl+D)"))
        self.btn_del.setText(tr("🗑️ 削除", "🗑️ Delete"))
        self.btn_del.setToolTip(tr("選択中の吹き出しを削除 (Deleteキー)", "Delete selected bubble (Delete key)"))

        self.grp_text.setTitle(tr("セリフ・テキスト", "Dialogue Text"))
        self.txt_edit.setPlaceholderText(tr("セリフを入力してください...\n（縦書き自動組版）", "Enter dialogue text...\n(Automatic vertical layout)"))
        self.btn_big.setText(tr("🔍 強調 (大)", "🔍 Big"))
        self.btn_big.setToolTip(tr("選択文字または末尾を大きく強調 (<big>タグ)", "Emphasize selected text (<big> tag)"))
        self.btn_small.setText(tr("🔉 小声 (小)", "🔉 Small"))
        self.btn_small.setToolTip(tr("選択文字または末尾を小さく (<small>タグ)", "Make selected text smaller (<small> tag)"))
        self.btn_paren.setText(tr("💬 （心の声）", "💬 (Monologue)"))
        self.btn_paren.setToolTip(tr("括弧で囲んでモノローグ風に", "Surround with parentheses"))
        self.btn_wrap.setText(tr("⏎ 自動改行", "⏎ Auto Wrap"))
        self.btn_wrap.setToolTip(tr("長い文を縦書きに適したバランスの良い行に自動分割します", "Auto-wrap long text into balanced vertical lines"))

        self.grp_style.setTitle(tr("吹き出しの形状・フォント", "Bubble Shape & Font"))
        self.lbl_type.setText(tr("形状:", "Shape:"))
        self.chk_hide_frame.setText(tr("既存枠に合わせる (枠なし)", "Fit to existing frame (no outline)"))
        self.chk_hide_frame.setToolTip(tr("イラスト内に既に描かれている吹き出しの中に文字だけを配置したい場合にチェックします。", "Check if speech bubble is already drawn inside the image."))
        self.chk_cover_old_text.setText(tr("元の文字を下地色で隠す", "Cover old text with fill"))
        self.chk_cover_old_text.setToolTip(tr("既存の吹き出し内に文字が入っている場合、枠線なしで背景色（白など）を塗りつぶして元の文字を隠します。", "Fills a borderless patch using background paper color to hide old dialogue inside an existing bubble."))
        self.btn_sample_paper.setText(tr("💧 下地色を自動取得", "💧 Auto-pick paper color"))
        self.lbl_font.setText(tr("フォント:", "Font:"))
        self.lbl_size.setText(tr("文字サイズ:", "Font Size:"))
        self.lbl_direction.setText(tr("行の進行:", "Text Flow:"))

        type_labels = [
            ("capsule", tr("カプセル (標準セリフ)", "Capsule (Standard Dialogue)")),
            ("cloud", tr("もこもこ雲 (楽しい・自撮り)", "Fluffy Cloud (Joy / Thinking)")),
            ("whisper", tr("囁き点線 (ヒソヒソ・小声)", "Whisper Dotted (Subtle)")),
            ("scream", tr("叫び/爆発 (ツッコミ・驚き)", "Scream / Starburst (Shout)")),
            ("oval", tr("楕円 (クラシック)", "Classic Oval (Egg shape)")),
            ("box", tr("角丸四角 (ナレーション)", "Rounded Box (Narration)")),
            ("floating", tr("枠なし浮遊モノローグ (心の声)", "Floating Monologue (Borderless)")),
            ("none", tr("既存枠利用 (枠・背景なし)", "Use Existing Frame (Text only)")),
            ("patch", tr("既存枠の文字隠し (枠なし・下地塗り)", "Cover Existing Text (Borderless Fill)")),
            ("sfx", tr("描き文字/オノマトペ (SFX)", "Onomatopoeia / SFX")),
        ]
        prev_block = self._block_signals
        self._block_signals = True
        for key, label in type_labels:
            idx = self.combo_type.findData(key)
            if idx >= 0:
                self.combo_type.setItemText(idx, label)

        self.combo_direction.setItemText(0, tr("右から左 (右→左・標準)", "Right to Left (RTL・Standard)"))
        self.combo_direction.setItemText(1, tr("左から右 (左→右)", "Left to Right (LTR)"))
        self._block_signals = prev_block

        self.grp_pad.setTitle(tr("吹き出しの大きさ（文字に対する余白）", "Bubble Size (Padding)"))
        self.chk_pad_manual.setText(tr("余白を手動で調整する", "Adjust padding manually"))
        self.chk_pad_manual.setToolTip(tr("オフ: 自動サイズ / オン: 文字サイズに対する余白倍率を指定", "Off: Auto size / On: Specify padding multiplier"))
        if "padding_ratio_x" in self.pad_row_labels:
            self.pad_row_labels["padding_ratio_x"].setText(tr("横の余白:", "Horizontal:"))
        if "padding_ratio_y" in self.pad_row_labels:
            self.pad_row_labels["padding_ratio_y"].setText(tr("縦の余白:", "Vertical:"))
        self.lbl_pad_tip.setText(tr("💡 文字を大きく・吹き出しを小さく（ぴったり）したいときは余白を下げます。", "💡 Lower padding to make the bubble compact around text."))

        self.grp_sfx.setTitle(tr("オノマトペ (SFX) 回転・フチ取り", "SFX Rotation & Stroke"))
        self.lbl_angle.setText(tr("回転角度:", "Angle:"))
        self.lbl_stroke_w.setText(tr("フチ太さ:", "Stroke Width:"))
        self.lbl_stroke_col.setText(tr("色:", "Color:"))
        self.lbl_sfx_pal_text.setText(tr("文字色 (パレット):", "Text Color (Palette):"))
        self.lbl_sfx_pal_stroke.setText(tr("フチ色 (パレット):", "Stroke Color (Palette):"))
        self.lbl_sfx_tip.setText(tr("💡 キャンバス上の緑のハンドルをドラッグしても自由に回転できます。", "💡 You can also drag the green handle on canvas to rotate."))

        self.grp_fx.setTitle(tr("文字の効果・変形", "Text Effects & Deform"))
        self.chk_shadow.setText(tr("影をつける", "Drop Shadow"))
        if "shadow_offset" in self.fx_row_labels:
            self.fx_row_labels["shadow_offset"].setText(tr("影の距離:", "Offset:"))
        if "shadow_blur" in self.fx_row_labels:
            self.fx_row_labels["shadow_blur"].setText(tr("影のぼかし:", "Blur:"))
        if hasattr(self, "lbl_fx_col"):
            self.lbl_fx_col.setText(tr("色:", "Color:"))
        if "text_scale_x" in self.fx_row_labels:
            self.fx_row_labels["text_scale_x"].setText(tr("横の伸縮:", "Scale X:"))
        if "text_scale_y" in self.fx_row_labels:
            self.fx_row_labels["text_scale_y"].setText(tr("縦の伸縮:", "Scale Y:"))
        if "text_skew" in self.fx_row_labels:
            self.fx_row_labels["text_skew"].setText(tr("傾き(斜体):", "Skew:"))
        self.btn_fx_reset.setText(tr("↺ 変形をリセット", "↺ Reset Deform"))

        self.grp_tail.setTitle(tr("しっぽ（吹き出しの向き）", "Speech Tail"))
        self.chk_tail.setText(tr("しっぽを表示 (口元へ向ける)", "Show Tail (point to mouth)"))
        self.btn_flip_tail.setText(tr("⇄ しっぽ反転", "⇄ Flip Tail"))
        self.btn_flip_all_tails.setText(tr("⇄ 全しっぽ反転", "⇄ Flip All"))
        self.btn_spread_inward.setText(tr("↘↙ 見開き内向", "↘↙ Inward"))
        self.btn_spread_outward.setText(tr("↙↘ 見開き外向", "↙↘ Outward"))
        self.lbl_tail_tip.setText(tr("💡 オレンジの丸: しっぽの先端（向き・長さ）。水色の四角: しっぽが出る位置。どちらもキャンバス上でドラッグできます。",
                                    "💡 Orange circle: tail tip (direction/length). Cyan square: tail origin on bubble outline."))
        self.btn_anchor_auto.setText(tr("↺ しっぽの出る位置を自動に戻す", "↺ Reset Tail Origin to Auto"))

        self.grp_opacity.setTitle(tr("透明度 & コントラスト", "Opacity & Contrast"))
        self.chk_auto_contrast.setText(tr("背景に合わせて自動調整", "Auto-adjust to background"))
        self.chk_auto_contrast.setToolTip(tr("背景の明るさに応じて不透明度と光彩を自動最適化 (Auto-Contrast)", "Optimizes opacity and halo automatically based on background brightness."))
        self.lbl_opacity_title.setText(tr("不透明度:", "Opacity:"))

        self.grp_colors.setTitle(tr("カラー設定", "Color Settings"))
        self.lbl_bg_col.setText(tr("背景色:", "Background:"))
        self.lbl_text_col.setText(tr("文字色:", "Text:"))
        self.lbl_border_col.setText(tr("枠線色:", "Border:"))
        self.lbl_halo_col.setText(tr("光彩:", "Halo:"))
        self.btn_halo_col.setToolTip(tr("浮遊モノローグや文字周りの光彩(Halo)カラー", "Halo glow color around text / monologue"))
        self.lbl_border_w_title.setText(tr("枠の太さ:", "Border Width:"))

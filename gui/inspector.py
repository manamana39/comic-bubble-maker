"""
gui.inspector
~~~~~~~~~~~~~
Sidebar property editor for speech bubbles and monologues.
Provides live two-way synchronization between UI controls and the selected BubbleGraphicsItem.
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
        color = QColorDialog.getColor(cur, self, "色を選択", QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            new_rgba = (color.red(), color.green(), color.blue(), color.alpha())
            self.rgba = new_rgba
            self.update_swatch()
            self.color_changed.emit(new_rgba)


class BubbleInspectorPanel(QWidget):
    """Inspector panel for adjusting all attributes of the currently selected bubble."""

    bubble_updated = Signal()
    delete_requested = Signal()
    duplicate_requested = Signal()

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
        grp_text = QGroupBox("セリフ・テキスト")
        vbox_text = QVBoxLayout(grp_text)

        self.txt_edit = QPlainTextEdit()
        self.txt_edit.setPlaceholderText("セリフを入力してください...\n（縦書き自動組版）")
        self.txt_edit.setMinimumWidth(100)
        self.txt_edit.setMinimumHeight(75)
        self.txt_edit.setMaximumHeight(110)
        self.txt_edit.textChanged.connect(self._on_text_changed)
        vbox_text.addWidget(self.txt_edit)

        # Tag quick insertion buttons (2x2 grid so nothing is ever clipped)
        tag_grid = QGridLayout()
        tag_grid.setSpacing(4)
        btn_big = QPushButton("🔍 強調 (大)")
        btn_big.setToolTip("選択文字または末尾を大きく強調 (<big>タグ)")
        btn_big.clicked.connect(lambda: self._insert_tags("<big>", "</big>"))
        tag_grid.addWidget(btn_big, 0, 0)

        btn_small = QPushButton("🔉 小声 (小)")
        btn_small.setToolTip("選択文字または末尾を小さく (<small>タグ)")
        btn_small.clicked.connect(lambda: self._insert_tags("<small>", "</small>"))
        tag_grid.addWidget(btn_small, 0, 1)

        btn_paren = QPushButton("💬 （心の声）")
        btn_paren.setToolTip("括弧で囲んでモノローグ風に")
        btn_paren.clicked.connect(lambda: self._insert_tags("（", "）"))
        tag_grid.addWidget(btn_paren, 1, 0)

        btn_wrap = QPushButton("⏎ 自動改行")
        btn_wrap.setToolTip("長い文を縦書きに適したバランスの良い行に自動分割します")
        btn_wrap.clicked.connect(self._auto_wrap_text)
        tag_grid.addWidget(btn_wrap, 1, 1)
        vbox_text.addLayout(tag_grid)

        self.content_layout.addWidget(grp_text)

        # --- 3. Bubble Style ---
        grp_style = QGroupBox("吹き出しの形状・フォント")
        vbox_style = QVBoxLayout(grp_style)

        # Bubble Shape
        row_type = QHBoxLayout()
        row_type.addWidget(QLabel("形状:"))
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
        self.combo_type.addItem("描き文字/オノマトペ (SFX)", "sfx")
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        row_type.addWidget(self.combo_type, 1)
        vbox_style.addLayout(row_type)

        self.chk_hide_frame = QCheckBox("既存枠に合わせる (枠なし)")
        self.chk_hide_frame.setToolTip("イラスト内に既に描かれている吹き出しの中に文字だけを配置したい場合にチェックします。")
        self.chk_hide_frame.toggled.connect(self._on_hide_frame_toggled)
        vbox_style.addWidget(self.chk_hide_frame)

        # Font
        row_font = QHBoxLayout()
        row_font.addWidget(QLabel("フォント:"))
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
        row_size.addWidget(QLabel("文字サイズ:"))
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

        self.content_layout.addWidget(grp_style)

        # --- 4. SFX Settings (visible only for sfx, placed prominently at top) ---
        self.grp_sfx = QGroupBox("オノマトペ (SFX) 回転・フチ取り")
        vbox_sfx = QVBoxLayout(self.grp_sfx)

        # Rotation slider + spinbox
        row_angle = QHBoxLayout()
        row_angle.addWidget(QLabel("回転角度:"))
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
        row_stroke.addWidget(QLabel("フチ太さ:"))
        self.slider_stroke = QSlider(Qt.Orientation.Horizontal)
        self.slider_stroke.setRange(0, 12)
        self.slider_stroke.setValue(3)
        self.slider_stroke.valueChanged.connect(self._on_stroke_width_changed)
        self.lbl_stroke = QLabel("3px")
        self.lbl_stroke.setFixedWidth(30)
        row_stroke.addWidget(self.slider_stroke, 1)
        row_stroke.addWidget(self.lbl_stroke)

        row_stroke.addWidget(QLabel("色:"))
        self.btn_stroke_col = ColorButton((255, 255, 255, 255))
        self.btn_stroke_col.color_changed.connect(self._on_stroke_color_changed)
        row_stroke.addWidget(self.btn_stroke_col)
        vbox_sfx.addLayout(row_stroke)

        lbl_sfx_tip = QLabel("💡 キャンバス上の緑のハンドルをドラッグしても自由に回転できます。")
        lbl_sfx_tip.setStyleSheet("color: #888; font-size: 11px;")
        lbl_sfx_tip.setWordWrap(True)
        vbox_sfx.addWidget(lbl_sfx_tip)

        self.content_layout.addWidget(self.grp_sfx)

        # --- 5. Tail Settings ---
        self.grp_tail = QGroupBox("しっぽ（吹き出しの向き）")
        vbox_tail = QVBoxLayout(self.grp_tail)

        self.chk_tail = QCheckBox("しっぽを表示 (口元へ向ける)")
        self.chk_tail.toggled.connect(self._on_tail_toggled)
        vbox_tail.addWidget(self.chk_tail)

        lbl_tail_tip = QLabel("💡 キャンバス上のオレンジのハンドルをドラッグして、向きと長さを調整できます。")
        lbl_tail_tip.setStyleSheet("color: #888; font-size: 11px;")
        lbl_tail_tip.setWordWrap(True)
        vbox_tail.addWidget(lbl_tail_tip)
        self.content_layout.addWidget(self.grp_tail)

        # --- 6. Opacity & Contrast ---
        grp_opacity = QGroupBox("透明度 & コントラスト")
        vbox_op = QVBoxLayout(grp_opacity)

        self.chk_auto_contrast = QCheckBox("背景に合わせて自動調整")
        self.chk_auto_contrast.setToolTip("背景の明るさに応じて不透明度と光彩を自動最適化 (Auto-Contrast)")
        self.chk_auto_contrast.toggled.connect(self._on_auto_contrast_toggled)
        vbox_op.addWidget(self.chk_auto_contrast)

        row_op = QHBoxLayout()
        row_op.addWidget(QLabel("不透明度:"))
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.valueChanged.connect(self._on_opacity_changed)
        self.lbl_opacity = QLabel("90%")
        self.lbl_opacity.setFixedWidth(36)
        row_op.addWidget(self.slider_opacity, 1)
        row_op.addWidget(self.lbl_opacity)
        vbox_op.addLayout(row_op)

        self.content_layout.addWidget(grp_opacity)

        # --- 7. Colors ---
        grp_colors = QGroupBox("カラー設定")
        vbox_col = QVBoxLayout(grp_colors)

        # 4-Column Grid for Colors (never overflows)
        grid_col = QGridLayout()
        grid_col.setHorizontalSpacing(10)
        grid_col.setVerticalSpacing(8)

        # Row 0: 背景色 & 文字色
        grid_col.addWidget(QLabel("背景色:"), 0, 0)
        self.btn_bg_col = ColorButton()
        self.btn_bg_col.color_changed.connect(self._on_bg_color_changed)
        grid_col.addWidget(self.btn_bg_col, 0, 1)

        grid_col.addWidget(QLabel("文字色:"), 0, 2)
        self.btn_text_col = ColorButton()
        self.btn_text_col.color_changed.connect(self._on_text_color_changed)
        grid_col.addWidget(self.btn_text_col, 0, 3)

        # Row 1: 枠線色 & 光彩色
        grid_col.addWidget(QLabel("枠線色:"), 1, 0)
        self.btn_border_col = ColorButton()
        self.btn_border_col.color_changed.connect(self._on_border_color_changed)
        grid_col.addWidget(self.btn_border_col, 1, 1)

        grid_col.addWidget(QLabel("光彩:"), 1, 2)
        self.btn_halo_col = ColorButton()
        self.btn_halo_col.setToolTip("浮遊モノローグや文字周りの光彩(Halo)カラー")
        self.btn_halo_col.color_changed.connect(self._on_halo_color_changed)
        grid_col.addWidget(self.btn_halo_col, 1, 3)

        grid_col.setColumnStretch(1, 1)
        grid_col.setColumnStretch(3, 1)
        vbox_col.addLayout(grid_col)

        self.content_layout.addWidget(grp_colors)
        self.content_layout.addStretch()

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll, 1)

        # Install event filter on wheel-sensitive controls so mouse wheel scrolls the panel smoothly
        for w in (
            self.combo_type, self.combo_font,
            self.slider_size, self.spin_size,
            self.slider_angle, self.spin_angle,
            self.slider_stroke, self.slider_opacity
        ):
            w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            w.installEventFilter(self)

        self.set_item(None)

    def eventFilter(self, obj, event: QEvent) -> bool:
        """Forward mouse wheel events from sliders/comboboxes to the scroll area vertical scrollbar."""
        if event.type() == QEvent.Type.Wheel:
            QApplication.sendEvent(self.scroll.verticalScrollBar(), event)
            return True
        return super().eventFilter(obj, event)

    def sync_from_item(self):
        """Update inspector controls when item properties are changed externally (e.g. resize handles, rotate handle)."""
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
        """Bind inspector to the selected item or disable controls if None (keeping scroll area active)."""
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
            self.lbl_title.setText("💬 吹き出しを選択してください")
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
        self.lbl_title.setText("💬 吹き出しプロパティ")

        # 1. Text
        self.txt_edit.setPlainText(cfg.text)

        # 2. Type
        b_type = cfg.type.lower()
        idx = self.combo_type.findData(b_type)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)
        self.chk_hide_frame.setChecked(b_type == "none")

        # 3. Font
        f_idx = self.combo_font.findData(cfg.font)
        if f_idx >= 0:
            self.combo_font.setCurrentIndex(f_idx)

        # 4. Font Size
        self.spin_size.setValue(cfg.font_size_ratio)
        self.slider_size.setValue(int(cfg.font_size_ratio * 1000))

        # 5. SFX Settings (prominently at top for SFX)
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

        # 6. Tail
        has_tail = item.tail_handle.isVisible() and b_type not in ("floating", "none", "sfx")
        self.chk_tail.setChecked(has_tail)
        self.grp_tail.setVisible(b_type not in ("floating", "none", "sfx"))

        # 7. Opacity
        self.chk_auto_contrast.setChecked(cfg.visibility_mode == "auto")
        if cfg.bg_alpha is not None:
            op_val = int(cfg.bg_alpha * 100)
        else:
            op_val = 90
        self.slider_opacity.setValue(op_val)
        self.lbl_opacity.setText(f"{op_val}%")
        self.slider_opacity.setEnabled(cfg.visibility_mode != "auto")

        # 8. Colors
        self.btn_bg_col.set_rgba(cfg.bg_color)
        self.btn_text_col.set_rgba(cfg.text_color)
        self.btn_border_col.set_rgba(cfg.border_color)
        halo_c = cfg.halo_color if cfg.halo_color else (255, 255, 255, 220)
        self.btn_halo_col.set_rgba(halo_c)

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
            # Move cursor between tags
            cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, len(close_tag))
            self.txt_edit.setTextCursor(cursor)

    def _auto_wrap_text(self):
        cur = self.txt_edit.toPlainText()
        wrapped = auto_wrap_japanese_text(cur)
        if wrapped != cur:
            self.txt_edit.setPlainText(wrapped)
            self._on_text_changed()

    def _on_text_changed(self):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.text = self.txt_edit.toPlainText()
        self._apply_change()

    def _on_type_changed(self):
        if self._block_signals or not self.current_item:
            return
        new_type = self.combo_type.currentData()
        self.current_item.config.type = new_type
        self.grp_tail.setVisible(new_type not in ("floating", "none", "sfx"))
        self.grp_sfx.setVisible(new_type == "sfx")
        self.chk_hide_frame.blockSignals(True)
        self.chk_hide_frame.setChecked(new_type == "none")
        self.chk_hide_frame.blockSignals(False)
        self._apply_change()

    def _on_hide_frame_toggled(self, checked: bool):
        if self._block_signals or not self.current_item:
            return
        if checked:
            cur = self.combo_type.currentData()
            if cur != "none":
                self._prev_shape_type = cur
                idx = self.combo_type.findData("none")
                if idx >= 0:
                    self.combo_type.setCurrentIndex(idx)
        else:
            prev = getattr(self, "_prev_shape_type", "capsule")
            if prev == "none":
                prev = "capsule"
            idx = self.combo_type.findData(prev)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)

    def _on_font_changed(self):
        if self._block_signals or not self.current_item:
            return
        self.current_item.config.font = self.combo_font.currentData()
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

    def _on_angle_changed(self, val: int):
        """Backward compatibility alias."""
        self._on_angle_slider_changed(val)

    def _set_angle_preset(self, deg: int):
        if not self.current_item:
            return
        self._block_signals = True
        self.slider_angle.setValue(deg)
        self.spin_angle.setValue(deg)
        self._block_signals = False
        self.current_item.config.angle = float(deg)
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

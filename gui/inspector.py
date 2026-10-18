"""
gui.inspector
~~~~~~~~~~~~~
Sidebar property editor for speech bubbles and monologues.
Provides live two-way synchronization between UI controls and the selected BubbleGraphicsItem.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QComboBox, QSlider, QDoubleSpinBox, QCheckBox, QPushButton,
    QGroupBox, QColorDialog, QScrollArea, QFrame, QSizePolicy
)

from comic_bubble.models import BubbleConfig
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

        self.setMinimumWidth(300)
        self.setMaximumWidth(400)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)

        # Scroll area for compact sidebar layout
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(4, 4, 4, 4)

        # --- 1. Header & Actions ---
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel("💬 吹き出しプロパティ")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.lbl_title)

        self.btn_dup = QPushButton("複製")
        self.btn_dup.setToolTip("選択中の吹き出しを複製")
        self.btn_dup.clicked.connect(self.duplicate_requested.emit)
        header_layout.addWidget(self.btn_dup)

        self.btn_del = QPushButton("削除")
        self.btn_del.setStyleSheet("color: #ff4d4f;")
        self.btn_del.setToolTip("選択中の吹き出しを削除 (Deleteキー)")
        self.btn_del.clicked.connect(self.delete_requested.emit)
        header_layout.addWidget(self.btn_del)
        self.layout.addLayout(header_layout)

        # --- 2. Text Input ---
        grp_text = QGroupBox("セリフ・テキスト")
        vbox_text = QVBoxLayout(grp_text)

        self.txt_edit = QPlainTextEdit()
        self.txt_edit.setPlaceholderText("セリフを入力してください...\n（縦書き自動組版）")
        self.txt_edit.setMinimumHeight(75)
        self.txt_edit.textChanged.connect(self._on_text_changed)
        vbox_text.addWidget(self.txt_edit)

        # Tag quick insertion buttons
        tag_layout = QHBoxLayout()
        btn_big = QPushButton("<big>強調</big>")
        btn_big.setToolTip("選択文字または末尾を大きく強調")
        btn_big.clicked.connect(lambda: self._insert_tags("<big>", "</big>"))
        tag_layout.addWidget(btn_big)

        btn_small = QPushButton("<small>小声</small>")
        btn_small.setToolTip("選択文字または末尾を小さく")
        btn_small.clicked.connect(lambda: self._insert_tags("<small>", "</small>"))
        tag_layout.addWidget(btn_small)

        btn_paren = QPushButton("（心の声）")
        btn_paren.setToolTip("括弧で囲んでモノローグ風に")
        btn_paren.clicked.connect(lambda: self._insert_tags("（", "）"))
        tag_layout.addWidget(btn_paren)
        vbox_text.addLayout(tag_layout)

        self.layout.addWidget(grp_text)

        # --- 3. Bubble Style ---
        grp_style = QGroupBox("吹き出しの形状・フォント")
        vbox_style = QVBoxLayout(grp_style)

        # Bubble Shape
        row_type = QHBoxLayout()
        row_type.addWidget(QLabel("形状:"))
        self.combo_type = QComboBox()
        self.combo_type.addItem("カプセル (標準セリフ)", "capsule")
        self.combo_type.addItem("もこもこ雲 (楽しい・自撮り)", "cloud")
        self.combo_type.addItem("囁き点線 (ヒソヒソ・小声)", "whisper")
        self.combo_type.addItem("叫び/爆発 (ツッコミ・驚き)", "scream")
        self.combo_type.addItem("楕円 (クラシック)", "oval")
        self.combo_type.addItem("角丸四角 (ナレーション)", "box")
        self.combo_type.addItem("枠なし浮遊モノローグ (心の声)", "floating")
        self.combo_type.addItem("描き文字/オノマトペ (SFX)", "sfx")
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        row_type.addWidget(self.combo_type)
        vbox_style.addLayout(row_type)

        # Font
        row_font = QHBoxLayout()
        row_font.addWidget(QLabel("フォント:"))
        self.combo_font = QComboBox()
        self.combo_font.addItem("Kiwi Maru (手書き・表情豊か)", "kiwi")
        self.combo_font.addItem("Zen Maru Gothic (丸ゴシック・標準)", "zenmaru")
        self.combo_font.addItem("Shippori Mincho (明朝・心の声)", "mincho")
        self.combo_font.addItem("Dela Gothic / Bold (太字・SFX)", "bold")
        self.combo_font.addItem("Yomogi (カジュアル手書き)", "yomogi")
        self.combo_font.currentIndexChanged.connect(self._on_font_changed)
        row_font.addWidget(self.combo_font)
        vbox_style.addLayout(row_font)

        # Font Size Ratio
        row_size = QHBoxLayout()
        row_size.addWidget(QLabel("文字サイズ:"))
        self.spin_size = QDoubleSpinBox()
        self.spin_size.setRange(0.010, 0.090)
        self.spin_size.setSingleStep(0.002)
        self.spin_size.setDecimals(3)
        self.spin_size.valueChanged.connect(self._on_size_spin_changed)

        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(10, 90)
        self.slider_size.valueChanged.connect(self._on_size_slider_changed)

        row_size.addWidget(self.slider_size)
        row_size.addWidget(self.spin_size)
        vbox_style.addLayout(row_size)

        self.layout.addWidget(grp_style)

        # --- 4. Tail Settings ---
        self.grp_tail = QGroupBox("しっぽ（吹き出しの向き）")
        vbox_tail = QVBoxLayout(self.grp_tail)

        self.chk_tail = QCheckBox("しっぽを表示する（キャラの口元へ向ける）")
        self.chk_tail.toggled.connect(self._on_tail_toggled)
        vbox_tail.addWidget(self.chk_tail)

        lbl_tail_tip = QLabel("💡 キャンバス上のオレンジのハンドルをドラッグして、向きと長さを調整できます。")
        lbl_tail_tip.setStyleSheet("color: #888; font-size: 11px;")
        lbl_tail_tip.setWordWrap(True)
        vbox_tail.addWidget(lbl_tail_tip)
        self.layout.addWidget(self.grp_tail)

        # --- 5. Opacity & Contrast ---
        grp_opacity = QGroupBox("透明度 & コントラスト")
        vbox_op = QVBoxLayout(grp_opacity)

        self.chk_auto_contrast = QCheckBox("背景自動解析 (Auto-Contrast)")
        self.chk_auto_contrast.setToolTip("背景の明るさに応じて不透明度と光彩を自動最適化")
        self.chk_auto_contrast.toggled.connect(self._on_auto_contrast_toggled)
        vbox_op.addWidget(self.chk_auto_contrast)

        row_op = QHBoxLayout()
        row_op.addWidget(QLabel("不透明度:"))
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.valueChanged.connect(self._on_opacity_changed)
        self.lbl_opacity = QLabel("90%")
        row_op.addWidget(self.slider_opacity)
        row_op.addWidget(self.lbl_opacity)
        vbox_op.addLayout(row_op)

        self.layout.addWidget(grp_opacity)

        # --- 6. Colors ---
        grp_colors = QGroupBox("カラー設定")
        vbox_col = QVBoxLayout(grp_colors)

        # Background color
        row_bg = QHBoxLayout()
        row_bg.addWidget(QLabel("背景色:"))
        self.btn_bg_col = ColorButton()
        self.btn_bg_col.color_changed.connect(self._on_bg_color_changed)
        row_bg.addWidget(self.btn_bg_col)
        row_bg.addStretch()

        # Text color
        row_bg.addWidget(QLabel("文字色:"))
        self.btn_text_col = ColorButton()
        self.btn_text_col.color_changed.connect(self._on_text_color_changed)
        row_bg.addWidget(self.btn_text_col)
        vbox_col.addLayout(row_bg)

        # Border color
        row_border = QHBoxLayout()
        row_border.addWidget(QLabel("枠線色:"))
        self.btn_border_col = ColorButton()
        self.btn_border_col.color_changed.connect(self._on_border_color_changed)
        row_border.addWidget(self.btn_border_col)
        row_border.addStretch()

        # Halo color
        row_border.addWidget(QLabel("光彩(Halo):"))
        self.btn_halo_col = ColorButton()
        self.btn_halo_col.color_changed.connect(self._on_halo_color_changed)
        row_border.addWidget(self.btn_halo_col)
        vbox_col.addLayout(row_border)

        self.layout.addWidget(grp_colors)

        # --- 7. SFX Settings (visible only for sfx) ---
        self.grp_sfx = QGroupBox("オノマトペ (SFX) 設定")
        vbox_sfx = QVBoxLayout(self.grp_sfx)

        row_angle = QHBoxLayout()
        row_angle.addWidget(QLabel("回転角度:"))
        self.slider_angle = QSlider(Qt.Orientation.Horizontal)
        self.slider_angle.setRange(-180, 180)
        self.slider_angle.valueChanged.connect(self._on_angle_changed)
        self.lbl_angle = QLabel("0°")
        row_angle.addWidget(self.slider_angle)
        row_angle.addWidget(self.lbl_angle)
        vbox_sfx.addLayout(row_angle)

        self.layout.addWidget(self.grp_sfx)
        self.layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.set_item(None)

    def sync_from_item(self):
        """Update inspector controls when item properties are changed externally (e.g. resize handles)."""
        if not self.current_item or self._block_signals:
            return
        self._block_signals = True
        cfg = self.current_item.config
        self.spin_size.setValue(cfg.font_size_ratio)
        self.slider_size.setValue(int(cfg.font_size_ratio * 1000))
        self._block_signals = False

    def set_item(self, item: Optional[BubbleGraphicsItem]):
        """Bind inspector to the selected item or disable if None."""
        if self.current_item and self.current_item != item:
            try:
                self.current_item.changed.disconnect(self.sync_from_item)
            except Exception:
                pass

        self.current_item = item
        if not item:
            self.setEnabled(False)
            self.lbl_title.setText("💬 吹き出しを選択してください")
            return

        try:
            item.changed.connect(self.sync_from_item)
        except Exception:
            pass

        self.setEnabled(True)
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

        # 3. Font
        f_idx = self.combo_font.findData(cfg.font)
        if f_idx >= 0:
            self.combo_font.setCurrentIndex(f_idx)

        # 4. Font Size
        self.spin_size.setValue(cfg.font_size_ratio)
        self.slider_size.setValue(int(cfg.font_size_ratio * 1000))

        # 5. Tail
        has_tail = item.tail_handle.isVisible() and b_type not in ("floating", "none", "sfx")
        self.chk_tail.setChecked(has_tail)
        self.grp_tail.setVisible(b_type not in ("floating", "none", "sfx"))

        # 6. Opacity
        self.chk_auto_contrast.setChecked(cfg.visibility_mode == "auto")
        if cfg.bg_alpha is not None:
            op_val = int(cfg.bg_alpha * 100)
        else:
            op_val = 90
        self.slider_opacity.setValue(op_val)
        self.lbl_opacity.setText(f"{op_val}%")
        self.slider_opacity.setEnabled(cfg.visibility_mode != "auto")

        # 7. Colors
        self.btn_bg_col.set_rgba(cfg.bg_color)
        self.btn_text_col.set_rgba(cfg.text_color)
        self.btn_border_col.set_rgba(cfg.border_color)
        halo_c = cfg.halo_color if cfg.halo_color else (255, 255, 255, 220)
        self.btn_halo_col.set_rgba(halo_c)

        # 8. SFX
        is_sfx = b_type == "sfx"
        self.grp_sfx.setVisible(is_sfx)
        if is_sfx:
            ang = int(cfg.angle)
            self.slider_angle.setValue(ang)
            self.lbl_angle.setText(f"{ang}°")

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
        self._apply_change()

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

    def _on_angle_changed(self, val: int):
        if self._block_signals or not self.current_item:
            return
        self.lbl_angle.setText(f"{val}°")
        self.current_item.config.angle = float(val)
        self._apply_change()

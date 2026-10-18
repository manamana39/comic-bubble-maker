"""
gui.main_window
~~~~~~~~~~~~~~~
Main desktop window for Manga Bubble Maker.
Combines interactive canvas, property inspector sidebar, toolbars,
and high-resolution super-sampled export capabilities.
"""

import os
from typing import Optional
from PIL import Image
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QKeySequence, QIcon, QClipboard, QGuiApplication
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QFileDialog, QMessageBox,
    QStatusBar, QToolBar, QWidget, QHBoxLayout, QLabel
)

from comic_bubble.models import BubbleConfig, SceneConfig
from comic_bubble.engine import render_scene
from comic_bubble.auto_layout import find_safe_background_center

from .canvas import ComicCanvasView
from .inspector import BubbleInspectorPanel


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self, initial_image: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("プロジェクトスピーチバブルメーカー - Speech Bubble Maker")
        self.resize(1280, 820)

        # 1. Canvas View & Inspector
        self.canvas = ComicCanvasView(self)
        self.inspector = BubbleInspectorPanel(self)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.inspector)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        self.setCentralWidget(splitter)

        # 2. Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.lbl_status_info = QLabel("画像を開いてください (Ctrl+O または画像をドラッグ＆ドロップ)")
        self.lbl_status_hint = QLabel("💡 ダブルクリック: 吹き出し追加 | オレンジ点: しっぽ調整 | ホイール: ズーム")
        self.lbl_status_hint.setStyleSheet("color: #777; margin-right: 12px;")
        self.status_bar.addWidget(self.lbl_status_info, 1)
        self.status_bar.addPermanentWidget(self.lbl_status_hint)

        # 3. Actions & Menus
        self._create_actions()
        self._create_menus()
        self._create_toolbar()

        # 4. Signals
        self.canvas.bubble_selected.connect(self.inspector.set_item)
        self.canvas.image_loaded.connect(self._on_image_loaded)
        self.canvas.scene_modified.connect(self._update_status)
        self.inspector.delete_requested.connect(self._delete_selected_bubble)
        self.inspector.duplicate_requested.connect(self._duplicate_selected_bubble)

        # Apply dark modern theme styling
        self._apply_theme()

        # Load initial image if provided
        if initial_image and os.path.isfile(initial_image):
            self.canvas.load_image(initial_image)

    def _apply_theme(self):
        """Clean modern stylesheet for dark-mode desktop elegance."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QToolBar {
                background-color: #333333;
                border-bottom: 1px solid #444444;
                spacing: 6px;
                padding: 4px;
            }
            QToolButton {
                background-color: transparent;
                color: #e0e0e0;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: 500;
            }
            QToolButton:hover {
                background-color: #444444;
            }
            QToolButton:pressed {
                background-color: #555555;
            }
            QGroupBox {
                border: 1px solid #444444;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                color: #e0e0e0;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPlainTextEdit, QComboBox, QDoubleSpinBox {
                background-color: #202020;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px;
            }
            QPlainTextEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #0078d7;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #0078d7;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QStatusBar {
                background-color: #242424;
                color: #aaaaaa;
                border-top: 1px solid #383838;
            }
        """)

    def _create_actions(self):
        # File Actions
        self.act_open = QAction("📂 画像を開く...", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self._open_image_dialog)

        self.act_paste = QAction("📋 クリップボードから貼り付け", self)
        self.act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.act_paste.triggered.connect(self._paste_image_from_clipboard)

        self.act_save = QAction("💾 高解像度で保存 / エクスポート...", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._save_image_dialog)

        self.act_copy_result = QAction("📑 完成画像をクリップボードにコピー", self)
        self.act_copy_result.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.act_copy_result.triggered.connect(self._copy_result_to_clipboard)

        self.act_exit = QAction("終了", self)
        self.act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_exit.triggered.connect(self.close)

        # Bubble Actions
        self.act_add_speech = QAction("💬 吹き出しを追加", self)
        self.act_add_speech.setShortcut(QKeySequence("Ctrl+N"))
        self.act_add_speech.triggered.connect(self._add_speech_bubble)

        self.act_add_monologue = QAction("💭 浮遊モノローグを追加", self)
        self.act_add_monologue.setShortcut(QKeySequence("Ctrl+M"))
        self.act_add_monologue.triggered.connect(self._add_monologue_bubble)

        self.act_add_sfx = QAction("⚡ オノマトペ (SFX) を追加", self)
        self.act_add_sfx.setShortcut(QKeySequence("Ctrl+E"))
        self.act_add_sfx.triggered.connect(self._add_sfx_bubble)

        self.act_ai_dialogue = QAction("✨ AIセリフ自動生成...", self)
        self.act_ai_dialogue.setShortcut(QKeySequence("Ctrl+G"))
        self.act_ai_dialogue.setToolTip("AIがイラストの表情・関係性を読み取り、最適なセリフ・モノローグ・オノマトペを自動配置")
        self.act_ai_dialogue.triggered.connect(self._open_ai_dialogue_generator)

        self.act_ai_settings = QAction("⚙️ AIプロバイダー・APIキー設定...", self)
        self.act_ai_settings.setToolTip("Gemini、よそのクラウドAPI、ローカルLLM(Ollama)の切り替え・設定")
        self.act_ai_settings.triggered.connect(self._open_ai_settings)

        self.act_ai_auto = QAction("🤖 空き領域自動配置 (数理)", self)
        self.act_ai_auto.setToolTip("背景の空きスペースを幾何学的に解析して吹き出しを配置")
        self.act_ai_auto.triggered.connect(self._ai_auto_placement)

        # View Actions
        self.act_fit = QAction("🔍 画面に合わせる", self)
        self.act_fit.setShortcut(QKeySequence("Ctrl+0"))
        self.act_fit.triggered.connect(self.canvas.fit_in_view)

        self.act_zoom_reset = QAction("1:1 等倍表示", self)
        self.act_zoom_reset.setShortcut(QKeySequence("Ctrl+1"))
        self.act_zoom_reset.triggered.connect(self.canvas.reset_zoom)

    def _create_menus(self):
        menubar = self.menuBar()

        # File Menu
        menu_file = menubar.addMenu("ファイル (&F)")
        menu_file.addAction(self.act_open)
        menu_file.addAction(self.act_paste)
        menu_file.addSeparator()
        menu_file.addAction(self.act_save)
        menu_file.addAction(self.act_copy_result)
        menu_file.addSeparator()
        menu_file.addAction(self.act_exit)

        # Edit Menu
        menu_edit = menubar.addMenu("編集 (&E)")
        menu_edit.addAction(self.act_add_speech)
        menu_edit.addAction(self.act_add_monologue)
        menu_edit.addAction(self.act_add_sfx)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_ai_dialogue)
        menu_edit.addAction(self.act_ai_auto)

        # Settings Menu
        menu_settings = menubar.addMenu("設定 (&S)")
        menu_settings.addAction(self.act_ai_settings)

        # View Menu
        menu_view = menubar.addMenu("表示 (&V)")
        menu_view.addAction(self.act_fit)
        menu_view.addAction(self.act_zoom_reset)

        # Help Menu
        menu_help = menubar.addMenu("ヘルプ (&H)")
        act_about = QAction("バージョン情報 (&A)...", self)
        act_about.triggered.connect(self._show_about)
        menu_help.addAction(act_about)

    def _create_toolbar(self):
        tb = QToolBar("メインツールバー", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        tb.addAction(self.act_open)
        tb.addAction(self.act_save)
        tb.addSeparator()
        tb.addAction(self.act_add_speech)
        tb.addAction(self.act_add_monologue)
        tb.addAction(self.act_add_sfx)
        tb.addSeparator()
        tb.addAction(self.act_ai_dialogue)
        tb.addAction(self.act_ai_settings)
        tb.addSeparator()
        tb.addAction(self.act_fit)
        tb.addAction(self.act_zoom_reset)

    # --- Slots & Handlers ---

    def _open_ai_dialogue_generator(self):
        """Open AI dialogue generation dialog."""
        if not self.canvas.base_pil_image:
            QMessageBox.information(self, "画像が必要です", "先にイラスト画像を読み込んでください。")
            return

        from .ai_dialog import AIDialogueDialog
        dlg = AIDialogueDialog(self.canvas.base_pil_image, self)
        if dlg.exec() and dlg.generated_bubbles:
            # Check if user wants to keep or replace existing bubbles
            if self.canvas.bubble_items:
                res = QMessageBox.question(
                    self,
                    "既存の吹き出し",
                    "既に配置されている吹き出しがあります。上書きして置き換えますか？\n（[いいえ]を押すと追加されます）",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if res == QMessageBox.StandardButton.Yes:
                    for it in list(self.canvas.bubble_items):
                        self.canvas.remove_bubble(it)

            for cfg in dlg.generated_bubbles:
                self.canvas.add_bubble(cfg)

            self.status_bar.showMessage(
                f"✨ AIがセリフを生成しました！ ({dlg.scene_description})", 6000
            )

    def _open_ai_settings(self):
        """Open multi-provider AI settings dialog."""
        from .settings_dialog import AISettingsDialog
        dlg = AISettingsDialog(self)
        dlg.exec()

    def _open_image_dialog(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self, "画像ファイルを開く", "", "画像ファイル (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if fpath:
            self.canvas.load_image(fpath)

    def _paste_image_from_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        qimg = clipboard.image()
        if not qimg.isNull():
            # Convert QImage to PIL Image
            import io
            buf = io.BytesIO()
            qimg.save(buf, "PNG")
            buf.seek(0)
            pil_img = Image.open(buf)
            self.canvas.load_image_from_pil(pil_img, "クリップボードの画像")
        else:
            QMessageBox.information(self, "クリップボード", "クリップボードに画像が見つかりませんでした。")

    def _save_image_dialog(self):
        if not self.canvas.base_pil_image:
            QMessageBox.warning(self, "保存エラー", "画像が読み込まれていません。")
            return

        fpath, _ = QFileDialog.getSaveFileName(
            self, "完成画像を保存", "result.png", "PNG画像 (*.png);;JPEG画像 (*.jpg)"
        )
        if not fpath:
            return

        # Render high-resolution super-sampled final output (Lanczos 3x)
        bubbles = self.canvas.get_all_bubble_configs()
        scene = SceneConfig(
            image_path=self.canvas.base_pil_image,
            bubbles=bubbles,
            supersample_scale=3
        )

        res_img = render_scene(scene)
        res_img.save(fpath, quality=98)
        self.status_bar.showMessage(f"画像を保存しました: {fpath}", 5000)
        QMessageBox.information(self, "保存完了", f"高解像度画像を保存しました！\n{fpath}")

    def _copy_result_to_clipboard(self):
        if not self.canvas.base_pil_image:
            return
        bubbles = self.canvas.get_all_bubble_configs()
        scene = SceneConfig(
            image_path=self.canvas.base_pil_image,
            bubbles=bubbles,
            supersample_scale=2
        )
        res_img = render_scene(scene)

        # Copy to QClipboard
        from .bubble_renderer import pil_to_qpixmap
        qpix = pil_to_qpixmap(res_img.convert("RGBA"))
        QGuiApplication.clipboard().setPixmap(qpix)
        self.status_bar.showMessage("完成画像をクリップボードにコピーしました！", 4000)

    def _add_speech_bubble(self):
        if not self.canvas.base_pil_image:
            QMessageBox.information(self, "ヒント", "先に画像を開いてください。")
            return
        cfg = BubbleConfig(
            text="セリフを入力",
            type="capsule",
            font="kiwi",
            center=(0.5, 0.25),
            tail=(0.4, 0.4),
            font_size_ratio=0.024,
            border_color=(50, 45, 65, 220),
            text_color=(45, 35, 55, 255),
            bg_color=(255, 250, 245),
            visibility_mode="auto"
        )
        self.canvas.add_bubble(cfg)

    def _add_monologue_bubble(self):
        if not self.canvas.base_pil_image:
            return
        cfg = BubbleConfig(
            text="（…心の声…）",
            type="floating",
            font="mincho",
            center=(0.2, 0.25),
            font_size_ratio=0.023,
            text_color=(255, 255, 255, 255),
            text_halo=True,
            halo_color=(30, 30, 40, 220)
        )
        self.canvas.add_bubble(cfg)

    def _add_sfx_bubble(self):
        if not self.canvas.base_pil_image:
            return
        cfg = BubbleConfig(
            text="ドキッ",
            type="sfx",
            font="bold",
            center=(0.5, 0.6),
            angle=-10.0,
            font_size_ratio=0.045,
            text_color=(255, 90, 110, 255),
            stroke_width=3.0,
            stroke_color=(255, 255, 255, 255)
        )
        self.canvas.add_bubble(cfg)

    def _ai_auto_placement(self):
        """Intelligently detects safe background areas avoiding character faces."""
        if not self.canvas.base_pil_image:
            return
        w, h = self.canvas.base_pil_image.size
        # Sample safe area
        auto_cx, auto_cy = find_safe_background_center(self.canvas.base_pil_image, int(w * 0.15), int(h * 0.25))
        cfg = BubbleConfig(
            text="自動配置セリフ",
            type="capsule",
            font="kiwi",
            center=(auto_cx, auto_cy),
            tail=(auto_cx + 0.08, auto_cy + 0.12),
            font_size_ratio=0.024,
            visibility_mode="auto"
        )
        item = self.canvas.add_bubble(cfg)
        self.status_bar.showMessage("AIが背景の空きスペースを検出して吹き出しを配置しました！", 4000)

    def _delete_selected_bubble(self):
        if self.canvas.current_selected_bubble:
            self.canvas.remove_bubble(self.canvas.current_selected_bubble)

    def _duplicate_selected_bubble(self):
        cur = self.canvas.current_selected_bubble
        if cur:
            import copy
            new_cfg = copy.deepcopy(cur.config)
            # Offset slightly
            cx = new_cfg.center[0] + 0.04 if new_cfg.center else 0.5
            cy = new_cfg.center[1] + 0.04 if new_cfg.center else 0.5
            new_cfg.center = (cx, cy)
            if new_cfg.tail:
                new_cfg.tail = (new_cfg.tail[0] + 0.04, new_cfg.tail[1] + 0.04)
            self.canvas.add_bubble(new_cfg)

    def _on_image_loaded(self, path: str, w: int, h: int):
        fname = os.path.basename(path)
        self.lbl_status_info.setText(f"画像: {fname} ({w} × {h} px)")

    def _update_status(self):
        cnt = len(self.canvas.bubble_items)
        if self.canvas.base_pil_image:
            w, h = self.canvas.base_pil_image.size
            fname = os.path.basename(self.canvas.base_image_path) if self.canvas.base_image_path else "画像"
            self.lbl_status_info.setText(f"画像: {fname} ({w} × {h} px) | 吹き出し: {cnt}個")

    def _show_about(self):
        QMessageBox.about(
            self,
            "Comic Bubble Maker",
            "<h3>Comic Bubble Maker 2.0</h3>"
            "<p>プロフェッショナルな漫画吹き出し・セリフ作成デスクトップアプリ</p>"
            "<ul>"
            "<li><b>AIフリー完全マニュアル編集</b>: 吹き出しやしっぽをマウスで自由自在に配置</li>"
            "<li><b>縦書き自動組版</b>: 禁則処理、約物回転、小声・強調タグ対応</li>"
            "<li><b>枠なし浮遊モノローグ</b>: 光彩(Halo)で背景に溶け込む演出</li>"
            "<li><b>オノマトペ(SFX)</b>: 描き文字の回転・縁取り</li>"
            "<li><b>超解像3xエクスポート</b>: 印刷・公開品質の滑らかな線画レンダリング</li>"
            "</ul>"
        )

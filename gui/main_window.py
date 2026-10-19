"""
gui.main_window
~~~~~~~~~~~~~~~
Main desktop window for Manga Bubble Maker.
Combines interactive canvas, property inspector sidebar, toolbars,
and high-resolution super-sampled export capabilities.
Supports multi-language UI (JA/EN) and safe-save confirmation before image changes.
"""

import os
from typing import Optional
from PIL import Image
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QIcon, QClipboard, QGuiApplication
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QFileDialog, QMessageBox,
    QStatusBar, QToolBar, QWidget, QHBoxLayout, QLabel, QMenu
)

from comic_bubble.models import BubbleConfig, SceneConfig
from comic_bubble.engine import render_scene
from comic_bubble.auto_layout import find_safe_background_center

from .canvas import ComicCanvasView
from .inspector import BubbleInspectorPanel
from .i18n import tr, get_current_language, set_current_language, register_language_listener


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self, initial_image: Optional[str] = None):
        super().__init__()

        # 1. Canvas View & Inspector
        self.canvas = ComicCanvasView(self)
        self.inspector = BubbleInspectorPanel(self)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.addWidget(self.canvas)
        self.splitter.addWidget(self.inspector)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.setCentralWidget(self.splitter)

        # Adapt initial window size safely to screen working area
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(1200, int(avail.width() * 0.90))
            target_h = min(780, int(avail.height() * 0.88))
            self.resize(target_w, target_h)
            self.move(
                avail.x() + (avail.width() - target_w) // 2,
                avail.y() + (avail.height() - target_h) // 2
            )
        else:
            target_w, target_h = 1100, 720
            self.resize(target_w, target_h)

        self.setMinimumSize(720, 480)
        # Give inspector comfortable 340-420px width
        insp_w = max(330, min(420, int(target_w * 0.28)))
        self.splitter.setSizes([target_w - insp_w, insp_w])

        # 2. Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.lbl_status_info = QLabel("")
        self.lbl_status_hint = QLabel("")
        self.lbl_status_hint.setStyleSheet("color: #888; margin-right: 12px;")
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

        # Register for dynamic language switching and perform initial translation
        register_language_listener(self.retranslate_ui)
        self.retranslate_ui()

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
                spacing: 4px;
                padding: 2px 4px;
            }
            QToolButton {
                background-color: transparent;
                color: #e0e0e0;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 12px;
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
            QPlainTextEdit, QComboBox, QDoubleSpinBox, QSpinBox {
                background-color: #202020;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px;
            }
            QPlainTextEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {
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
            QScrollBar:vertical {
                background: #242424;
                width: 12px;
                margin: 0px;
                border-left: 1px solid #383838;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 28px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #777777;
            }
            QScrollBar:add-line:vertical, QScrollBar:sub-line:vertical {
                height: 0px;
            }
            QScrollBar:add-page:vertical, QScrollBar:sub-page:vertical {
                background: none;
            }
        """)

    def _create_actions(self):
        # File Actions
        self.act_open = QAction("📂 開く", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self._open_image_dialog)

        self.act_paste = QAction("📋 クリップボードから貼り付け", self)
        self.act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.act_paste.triggered.connect(self._paste_image_from_clipboard)

        self.act_save = QAction("💾 保存", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._save_image_dialog)

        self.act_copy_result = QAction("📑 完成画像をクリップボードにコピー", self)
        self.act_copy_result.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.act_copy_result.triggered.connect(self._copy_result_to_clipboard)

        self.act_exit = QAction("終了", self)
        self.act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_exit.triggered.connect(self.close)

        # Bubble Actions
        self.act_add_speech = QAction("💬 吹き出し", self)
        self.act_add_speech.setShortcut(QKeySequence("Ctrl+N"))
        self.act_add_speech.triggered.connect(self._add_speech_bubble)

        self.act_add_monologue = QAction("💭 モノローグ", self)
        self.act_add_monologue.setShortcut(QKeySequence("Ctrl+M"))
        self.act_add_monologue.triggered.connect(self._add_monologue_bubble)

        self.act_add_sfx = QAction("⚡ オノマトペ", self)
        self.act_add_sfx.setShortcut(QKeySequence("Ctrl+E"))
        self.act_add_sfx.triggered.connect(self._add_sfx_bubble)

        self.act_sfx_palette = QAction("🎨 擬音パレット", self)
        self.act_sfx_palette.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self.act_sfx_palette.triggered.connect(self._open_sfx_palette)

        self.act_ai_dialogue = QAction("✨ AIセリフ生成", self)
        self.act_ai_dialogue.setShortcut(QKeySequence("Ctrl+G"))
        self.act_ai_dialogue.triggered.connect(self._open_ai_dialogue_generator)

        self.act_ai_settings = QAction("⚙️ AI設定", self)
        self.act_ai_settings.triggered.connect(self._open_ai_settings)

        self.act_ai_auto = QAction("🤖 空き領域自動配置 (数理)", self)
        self.act_ai_auto.triggered.connect(self._ai_auto_placement)

        # View Actions
        self.act_fit = QAction("🔍 全体表示", self)
        self.act_fit.setShortcut(QKeySequence("Ctrl+0"))
        self.act_fit.triggered.connect(self.canvas.fit_in_view)

        self.act_zoom_reset = QAction("1:1 等倍", self)
        self.act_zoom_reset.setShortcut(QKeySequence("Ctrl+1"))
        self.act_zoom_reset.triggered.connect(self.canvas.reset_zoom)

        self.act_toggle_inspector = QAction("📋 プロパティ", self)
        self.act_toggle_inspector.setCheckable(True)
        self.act_toggle_inspector.setChecked(True)
        self.act_toggle_inspector.setShortcut(QKeySequence("Ctrl+P"))
        self.act_toggle_inspector.toggled.connect(self._toggle_inspector)

        # Help Actions
        self.act_about = QAction("バージョン情報 (&A)...", self)
        self.act_about.triggered.connect(self._show_about)

    def _create_menus(self):
        menubar = self.menuBar()

        # File Menu
        self.menu_file = menubar.addMenu("ファイル (&F)")
        self.menu_file.addAction(self.act_open)
        self.menu_file.addAction(self.act_paste)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_save)
        self.menu_file.addAction(self.act_copy_result)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_exit)

        # Edit Menu
        self.menu_edit = menubar.addMenu("編集 (&E)")
        self.menu_edit.addAction(self.act_add_speech)
        self.menu_edit.addAction(self.act_add_monologue)
        self.menu_edit.addAction(self.act_add_sfx)
        self.menu_edit.addAction(self.act_sfx_palette)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.act_ai_dialogue)
        self.menu_edit.addAction(self.act_ai_auto)

        # Settings Menu
        self.menu_settings = menubar.addMenu("設定 (&S)")
        self.menu_settings.addAction(self.act_ai_settings)
        self.menu_settings.addSeparator()

        # Language Submenu
        self.menu_lang = self.menu_settings.addMenu("言語 / Language")
        self.lang_group = QActionGroup(self)
        self.act_lang_ja = QAction("日本語 (Japanese)", self)
        self.act_lang_ja.setCheckable(True)
        self.act_lang_en = QAction("English", self)
        self.act_lang_en.setCheckable(True)

        self.lang_group.addAction(self.act_lang_ja)
        self.lang_group.addAction(self.act_lang_en)

        cur_lang = get_current_language()
        if cur_lang == "en":
            self.act_lang_en.setChecked(True)
        else:
            self.act_lang_ja.setChecked(True)

        self.act_lang_ja.triggered.connect(lambda: set_current_language("ja"))
        self.act_lang_en.triggered.connect(lambda: set_current_language("en"))

        self.menu_lang.addAction(self.act_lang_ja)
        self.menu_lang.addAction(self.act_lang_en)

        # View Menu
        self.menu_view = menubar.addMenu("表示 (&V)")
        self.menu_view.addAction(self.act_fit)
        self.menu_view.addAction(self.act_zoom_reset)
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.act_toggle_inspector)

        # Help Menu
        self.menu_help = menubar.addMenu("ヘルプ (&H)")
        self.menu_help.addAction(self.act_about)

    def _create_toolbar(self):
        self.toolbar = QToolBar("メインツールバー", self)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.addToolBar(self.toolbar)

        self.toolbar.addAction(self.act_open)
        self.toolbar.addAction(self.act_save)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_add_speech)
        self.toolbar.addAction(self.act_add_monologue)
        self.toolbar.addAction(self.act_add_sfx)
        self.toolbar.addAction(self.act_sfx_palette)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_ai_dialogue)
        self.toolbar.addAction(self.act_ai_settings)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_fit)
        self.toolbar.addAction(self.act_zoom_reset)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_toggle_inspector)

    def _toggle_inspector(self, checked: bool):
        """Show or hide the inspector sidebar panel."""
        self.inspector.setVisible(checked)

    def confirm_save_if_modified(self) -> bool:
        """
        Ask user whether to save changes before replacing or closing current image work.
        Returns:
            True if it is safe to proceed (saved, discarded, or no bubbles).
            False if user cancelled or save failed/aborted.
        """
        if not self.canvas.bubble_items:
            return True

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("保存の確認", "Confirm Save"))
        msg.setText(
            tr(
                "編集中の吹き出しが存在します。新しい画像を読み込む前に現在の画像を保存しますか？",
                "There are speech bubbles currently being edited. Do you want to save before loading a new image?"
            )
        )
        msg.setInformativeText(
            tr(
                "「保存する」を押すと現在の完成画像をファイルに出力します。「破棄」を押すと現在の吹き出しを消去して新しい画像を読み込みます。",
                "Click 'Save' to export your current work to file. Click 'Discard' to discard current bubbles and open the new image."
            )
        )
        msg.setIcon(QMessageBox.Icon.Question)
        btn_save = msg.addButton(tr("保存する (&S)", "Save (&S)"), QMessageBox.ButtonRole.AcceptRole)
        btn_discard = msg.addButton(tr("破棄して続行 (&D)", "Discard & Continue (&D)"), QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = msg.addButton(tr("キャンセル", "Cancel"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_save)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked == btn_save:
            return self._save_image_dialog()
        elif clicked == btn_discard:
            return True
        else:
            return False

    def retranslate_ui(self):
        """Update window title, menu texts, actions, and status bar according to current language."""
        self.setWindowTitle(tr("スピーチバブルメーカー (Comic Bubble Maker) v0.6-beta", "Comic Bubble Maker v0.6-beta"))

        # Menus
        if hasattr(self, "menu_file"):
            self.menu_file.setTitle(tr("ファイル (&F)", "File (&F)"))
        if hasattr(self, "menu_edit"):
            self.menu_edit.setTitle(tr("編集 (&E)", "Edit (&E)"))
        if hasattr(self, "menu_settings"):
            self.menu_settings.setTitle(tr("設定 (&S)", "Settings (&S)"))
        if hasattr(self, "menu_view"):
            self.menu_view.setTitle(tr("表示 (&V)", "View (&V)"))
        if hasattr(self, "menu_help"):
            self.menu_help.setTitle(tr("ヘルプ (&H)", "Help (&H)"))
        if hasattr(self, "menu_lang"):
            self.menu_lang.setTitle(tr("言語 / Language", "Language / 言語"))

        # Language action check states
        cur_lang = get_current_language()
        if hasattr(self, "act_lang_ja"):
            self.act_lang_ja.setChecked(cur_lang == "ja")
        if hasattr(self, "act_lang_en"):
            self.act_lang_en.setChecked(cur_lang == "en")

        # Actions
        if hasattr(self, "act_open"):
            self.act_open.setText(tr("📂 開く", "📂 Open"))
            self.act_open.setToolTip(tr("画像を開く (Ctrl+O)", "Open image (Ctrl+O)"))
        if hasattr(self, "act_paste"):
            self.act_paste.setText(tr("📋 クリップボードから貼り付け", "📋 Paste from Clipboard"))
            self.act_paste.setToolTip(tr("クリップボードから画像を貼り付け (Ctrl+V)", "Paste image from clipboard (Ctrl+V)"))
        if hasattr(self, "act_save"):
            self.act_save.setText(tr("💾 保存", "💾 Save"))
            self.act_save.setToolTip(tr("高解像度で保存 / エクスポート (Ctrl+S)", "Export High-Resolution Image (Ctrl+S)"))
        if hasattr(self, "act_copy_result"):
            self.act_copy_result.setText(tr("📑 完成画像をクリップボードにコピー", "📑 Copy Result to Clipboard"))
            self.act_copy_result.setToolTip(tr("完成画像をクリップボードにコピー (Ctrl+Shift+C)", "Copy rendered image to clipboard (Ctrl+Shift+C)"))
        if hasattr(self, "act_exit"):
            self.act_exit.setText(tr("終了", "Exit"))

        if hasattr(self, "act_add_speech"):
            self.act_add_speech.setText(tr("💬 吹き出し", "💬 Speech Bubble"))
            self.act_add_speech.setToolTip(tr("通常の会話吹き出しを追加 (Ctrl+N)", "Add Standard Speech Bubble (Ctrl+N)"))
        if hasattr(self, "act_add_monologue"):
            self.act_add_monologue.setText(tr("💭 モノローグ", "💭 Monologue"))
            self.act_add_monologue.setToolTip(tr("枠なし浮遊モノローグを追加 (Ctrl+M)", "Add Borderless Monologue (Ctrl+M)"))
        if hasattr(self, "act_add_sfx"):
            self.act_add_sfx.setText(tr("⚡ オノマトペ", "⚡ SFX Text"))
            self.act_add_sfx.setToolTip(tr("漫画の描き文字・擬音を追加 (Ctrl+E)", "Add Manga Sound Effect Text (Ctrl+E)"))
        if hasattr(self, "act_sfx_palette"):
            self.act_sfx_palette.setText(tr("🎨 擬音パレット", "🎨 SFX Palette"))
            self.act_sfx_palette.setToolTip(tr("漫画のオノマトペ・擬音集からワンクリックで追加 (Ctrl+Shift+E)", "Add Manga SFX from Categorized Presets (Ctrl+Shift+E)"))
        if hasattr(self, "act_ai_dialogue"):
            self.act_ai_dialogue.setText(tr("✨ AIセリフ生成", "✨ AI Dialogue"))
            self.act_ai_dialogue.setToolTip(tr("AIがイラストの表情・関係性を読み取り、最適なセリフ・オノマトペを自動配置 (Ctrl+G)", "AI analyzes artwork & generates optimized dialogue (Ctrl+G)"))
        if hasattr(self, "act_ai_settings"):
            self.act_ai_settings.setText(tr("⚙️ AI設定", "⚙️ AI Settings"))
            self.act_ai_settings.setToolTip(tr("Gemini、よそのクラウドAPI、ローカルLLM(Ollama)の切り替え・設定", "Configure Gemini, Cloud APIs, or Local LLM (Ollama)"))
        if hasattr(self, "act_ai_auto"):
            self.act_ai_auto.setText(tr("🤖 空き領域自動配置 (数理)", "🤖 Auto Placement (Geometric)"))
            self.act_ai_auto.setToolTip(tr("背景の空きスペースを幾何学的に解析して吹き出しを配置", "Analyze safe background space and place bubble"))

        if hasattr(self, "act_fit"):
            self.act_fit.setText(tr("🔍 全体表示", "🔍 Fit to View"))
            self.act_fit.setToolTip(tr("画面に合わせる (Ctrl+0)", "Fit in view (Ctrl+0)"))
        if hasattr(self, "act_zoom_reset"):
            self.act_zoom_reset.setText(tr("1:1 等倍", "1:1 100%"))
            self.act_zoom_reset.setToolTip(tr("1:1 等倍表示 (Ctrl+1)", "Reset zoom to 100% (Ctrl+1)"))
        if hasattr(self, "act_toggle_inspector"):
            self.act_toggle_inspector.setText(tr("📋 プロパティ", "📋 Properties"))
            self.act_toggle_inspector.setToolTip(tr("プロパティパネルの表示/非表示 (Ctrl+P)", "Toggle Properties Inspector (Ctrl+P)"))
        if hasattr(self, "act_about"):
            self.act_about.setText(tr("バージョン情報 (&A)...", "About (&A)..."))

        # Status Hint
        if hasattr(self, "lbl_status_hint"):
            self.lbl_status_hint.setText(
                tr(
                    "💡 ダブルクリック: 吹き出し追加 | オレンジ点: しっぽ先端 | 水色四角: しっぽ位置 | ホイール: ズーム",
                    "💡 Double-click: Add bubble | Orange dot: Tail tip | Cyan square: Tail origin | Wheel: Zoom"
                )
            )

        self._update_status()

    # --- Slots & Handlers ---

    def _open_ai_dialogue_generator(self):
        """Open AI dialogue generation dialog."""
        if not self.canvas.base_pil_image:
            QMessageBox.information(
                self,
                tr("画像が必要です", "Image Required"),
                tr("先にイラスト画像を読み込んでください。", "Please load an illustration image first.")
            )
            return

        from .ai_dialog import AIDialogueDialog
        dlg = AIDialogueDialog(self.canvas.base_pil_image, self)
        if dlg.exec() and dlg.generated_bubbles:
            # Check if user wants to keep or replace existing bubbles
            if self.canvas.bubble_items:
                res = QMessageBox.question(
                    self,
                    tr("既存の吹き出し", "Existing Bubbles"),
                    tr("既に配置されている吹き出しがあります。上書きして置き換えますか？\n（[いいえ]を押すと追加されます）",
                       "There are already speech bubbles placed. Replace them?\n(Click [No] to append)"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if res == QMessageBox.StandardButton.Yes:
                    for it in list(self.canvas.bubble_items):
                        self.canvas.remove_bubble(it)

            for cfg in dlg.generated_bubbles:
                self.canvas.add_bubble(cfg)

            self.status_bar.showMessage(
                tr(f"✨ AIがセリフを生成しました！ ({dlg.scene_description})",
                   f"✨ AI generated speech bubbles! ({dlg.scene_description})"),
                6000
            )

    def _open_ai_settings(self):
        """Open multi-provider AI settings dialog."""
        from .settings_dialog import AISettingsDialog
        dlg = AISettingsDialog(self)
        dlg.exec()

    def _open_image_dialog(self):
        if not self.confirm_save_if_modified():
            return
        fpath, _ = QFileDialog.getOpenFileName(
            self,
            tr("画像ファイルを開く", "Open Image File"),
            "",
            tr("画像ファイル (*.png *.jpg *.jpeg *.webp *.bmp)", "Image Files (*.png *.jpg *.jpeg *.webp *.bmp)")
        )
        if fpath:
            self.canvas.load_image(fpath)

    def _paste_image_from_clipboard(self):
        if not self.confirm_save_if_modified():
            return
        clipboard = QGuiApplication.clipboard()
        qimg = clipboard.image()
        if not qimg.isNull():
            import io
            buf = io.BytesIO()
            qimg.save(buf, "PNG")
            buf.seek(0)
            pil_img = Image.open(buf)
            self.canvas.load_image_from_pil(pil_img, tr("クリップボードの画像", "Clipboard Image"))
        else:
            QMessageBox.information(
                self,
                tr("クリップボード", "Clipboard"),
                tr("クリップボードに画像が見つかりませんでした。", "No image found in clipboard.")
            )

    def _save_image_dialog(self) -> bool:
        """Save high-resolution final rendered image. Returns True on success, False if aborted/failed."""
        if not self.canvas.base_pil_image:
            QMessageBox.warning(
                self,
                tr("保存エラー", "Save Error"),
                tr("画像が読み込まれていません。", "No image loaded.")
            )
            return False

        fpath, _ = QFileDialog.getSaveFileName(
            self,
            tr("完成画像を保存", "Save Rendered Image"),
            "result.png",
            tr("PNG画像 (*.png);;JPEG画像 (*.jpg)", "PNG Image (*.png);;JPEG Image (*.jpg)")
        )
        if not fpath:
            return False

        # Render high-resolution super-sampled final output (Lanczos 3x)
        try:
            bubbles = self.canvas.get_all_bubble_configs()
            scene = SceneConfig(
                image_path=self.canvas.base_pil_image,
                bubbles=bubbles,
                supersample_scale=3
            )

            res_img = render_scene(scene)
            res_img.save(fpath, quality=98)
            self.status_bar.showMessage(tr(f"画像を保存しました: {fpath}", f"Saved image: {fpath}"), 5000)
            QMessageBox.information(
                self,
                tr("保存完了", "Save Complete"),
                tr(f"高解像度画像を保存しました！\n{fpath}", f"High-resolution image saved!\n{fpath}")
            )
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("保存失敗", "Save Failed"),
                tr(f"画像の保存中にエラーが発生しました:\n{e}", f"Error occurred while saving image:\n{e}")
            )
            return False

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
        self.status_bar.showMessage(tr("完成画像をクリップボードにコピーしました！", "Rendered image copied to clipboard!"), 4000)

    def _add_speech_bubble(self):
        if not self.canvas.base_pil_image:
            QMessageBox.information(
                self,
                tr("ヒント", "Hint"),
                tr("先に画像を開いてください。", "Please open an image first.")
            )
            return
        cfg = BubbleConfig(
            text=tr("セリフを入力", "Enter dialogue"),
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
            text=tr("（…心の声…）", "(...inner thought...)"),
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
            text=tr("ドキッ", "BA-DUMP"),
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

    def _open_sfx_palette(self):
        """Open categorized Manga SFX preset palette."""
        if not self.canvas.base_pil_image:
            QMessageBox.information(
                self,
                tr("画像が必要です", "Image Required"),
                tr("先にイラスト画像を開いてください。", "Please open an illustration image first.")
            )
            return
        from .sfx_palette import SFXPaletteDialog
        dlg = SFXPaletteDialog(self)
        dlg.sfx_picked.connect(lambda cfg: self.canvas.add_bubble(cfg))
        dlg.exec()

    def _ai_auto_placement(self):
        """Intelligently detects safe background areas avoiding character faces."""
        if not self.canvas.base_pil_image:
            return
        w, h = self.canvas.base_pil_image.size
        auto_cx, auto_cy = find_safe_background_center(self.canvas.base_pil_image, int(w * 0.15), int(h * 0.25))
        cfg = BubbleConfig(
            text=tr("自動配置セリフ", "Auto Dialogue"),
            type="capsule",
            font="kiwi",
            center=(auto_cx, auto_cy),
            tail=(auto_cx + 0.08, auto_cy + 0.12),
            font_size_ratio=0.024,
            visibility_mode="auto"
        )
        item = self.canvas.add_bubble(cfg)
        self.status_bar.showMessage(
            tr("AIが背景の空きスペースを検出して吹き出しを配置しました！",
               "AI detected safe background space and positioned bubble!"),
            4000
        )

    def _delete_selected_bubble(self):
        if self.canvas.current_selected_bubble:
            self.canvas.remove_bubble(self.canvas.current_selected_bubble)

    def _duplicate_selected_bubble(self):
        cur = self.canvas.current_selected_bubble
        if cur:
            import copy
            new_cfg = copy.deepcopy(cur.config)
            cx = new_cfg.center[0] + 0.04 if new_cfg.center else 0.5
            cy = new_cfg.center[1] + 0.04 if new_cfg.center else 0.5
            new_cfg.center = (cx, cy)
            if new_cfg.tail:
                new_cfg.tail = (new_cfg.tail[0] + 0.04, new_cfg.tail[1] + 0.04)
            self.canvas.add_bubble(new_cfg)

    def _on_image_loaded(self, path: str, w: int, h: int):
        fname = os.path.basename(path)
        self.lbl_status_info.setText(tr(f"画像: {fname} ({w} × {h} px)", f"Image: {fname} ({w} × {h} px)"))

    def _update_status(self):
        cnt = len(self.canvas.bubble_items)
        if self.canvas.base_pil_image:
            w, h = self.canvas.base_pil_image.size
            fname = os.path.basename(self.canvas.base_image_path) if self.canvas.base_image_path else tr("画像", "Image")
            self.lbl_status_info.setText(
                tr(f"画像: {fname} ({w} × {h} px) | 吹き出し: {cnt}個",
                   f"Image: {fname} ({w} × {h} px) | Bubbles: {cnt}")
            )
        else:
            self.lbl_status_info.setText(
                tr("画像を開いてください (Ctrl+O または画像をドラッグ＆ドロップ)",
                   "Please open an image (Ctrl+O or drag & drop)")
            )

    def _show_about(self):
        title = tr("Comic Bubble Maker について", "About Comic Bubble Maker")
        body = tr(
            "<h3>Comic Bubble Maker v0.6-beta</h3>"
            "<p>プロフェッショナルな漫画吹き出し・セリフ作成デスクトップアプリ</p>"
            "<ul>"
            "<li><b>AIフリー完全マニュアル編集</b>: 吹き出しやしっぽ（先端・発生位置）をマウスで自由自在に配置</li>"
            "<li><b>縦書き自動組版</b>: 禁則処理、約物回転、左右行進行切り替え(RTL/LTR)、小声・強調タグ対応</li>"
            "<li><b>枠なし浮遊モノローグ</b>: 光彩(Halo)で背景に溶け込む演出</li>"
            "<li><b>オノマトペ(SFX)</b>: 描き文字の回転・縁取り・カラーパレット・ドロップシャドウ</li>"
            "<li><b>超解像3xエクスポート</b>: 印刷・公開品質の滑らかな線画レンダリング</li>"
            "<li><b>バイリンガル対応</b>: 日本語 / English 切り替え可能</li>"
            "</ul>",
            "<h3>Comic Bubble Maker v0.6-beta</h3>"
            "<p>Professional Manga Speech Bubble & Dialogue Editor</p>"
            "<ul>"
            "<li><b>Fully Manual & AI-Assisted</b>: Freely position bubbles and tails (tip & origin anchor) with mouse.</li>"
            "<li><b>Japanese Vertical Typography</b>: Kinsoku-shori, symbol rotation, RTL/LTR flow toggle, whisper tags.</li>"
            "<li><b>Borderless Monologue</b>: Soft halo glow effect that blends seamlessly into artwork.</li>"
            "<li><b>Onomatopoeia (SFX)</b>: Rotate, outline stroke, color palette, and drop shadow.</li>"
            "<li><b>High-Res 3x Super-Sampling Export</b>: Crisp print-grade line art rendering.</li>"
            "<li><b>Bilingual UI</b>: Switch effortlessly between Japanese and English.</li>"
            "</ul>"
        )
        QMessageBox.about(self, title, body)

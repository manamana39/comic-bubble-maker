"""
gui.ai_dialog
~~~~~~~~~~~~~
AI dialogue generation dialog and background QThread worker.
Supports multi-provider dispatch (Gemini, Cloud, Local Ollama).
"""

from typing import Optional, List
from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QProgressBar, QGroupBox, QFrame, QCheckBox
)

from comic_bubble.config import load_config
from comic_bubble.ai_generator import generate_scene_dialogue
from comic_bubble.models import BubbleConfig
from .settings_dialog import AISettingsDialog


class AIGeneratorThread(QThread):
    """Background worker thread for AI generation to keep GUI responsive."""

    finished_success = Signal(str, list)  # scene_desc, bubble_configs
    finished_error = Signal(str)
    progress_update = Signal(str)

    def __init__(self, image: Image.Image, genre_hint: str, nsfw: bool = False, detect_existing: bool = True):
        super().__init__()
        self.image = image
        self.genre_hint = genre_hint
        self.nsfw = nsfw
        self.detect_existing = detect_existing

    def run(self):
        try:
            desc, bubbles = generate_scene_dialogue(
                image=self.image,
                genre_hint=self.genre_hint,
                progress_callback=lambda msg: self.progress_update.emit(msg),
                nsfw=self.nsfw,
                detect_existing=self.detect_existing
            )
            self.finished_success.emit(desc, bubbles)
        except Exception as e:
            self.finished_error.emit(str(e))


class AIDialogueDialog(QDialog):
    """Dialog for launching AI dialogue generation with customizable tone/genre."""

    def __init__(self, current_image: Optional[Image.Image], parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ AIセリフ自動生成")
        self.resize(500, 390)
        self.current_image = current_image

        self.generated_bubbles: Optional[List[BubbleConfig]] = None
        self.scene_description: str = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. Provider Status Banner
        self.grp_provider = QGroupBox("使用するAIエンジン")
        vbox_prov = QVBoxLayout(self.grp_provider)

        row_prov = QHBoxLayout()
        self.lbl_provider_name = QLabel()
        self.lbl_provider_name.setStyleSheet("font-weight: bold; font-size: 13px; color: #4da6ff;")
        row_prov.addWidget(self.lbl_provider_name, 1)

        btn_settings = QPushButton("⚙️ APIキー・設定変更...")
        btn_settings.clicked.connect(self._open_settings)
        row_prov.addWidget(btn_settings)
        vbox_prov.addLayout(row_prov)

        self.lbl_provider_sub = QLabel()
        self.lbl_provider_sub.setStyleSheet("color: #888; font-size: 11px;")
        vbox_prov.addWidget(self.lbl_provider_sub)

        layout.addWidget(self.grp_provider)

        # 2. Genre / Situation Preference
        grp_genre = QGroupBox("作風・シチュエーション")
        vbox_genre = QVBoxLayout(grp_genre)

        self.combo_genre = QComboBox()
        self.combo_genre.addItem("おまかせ (画像の表情・シチュエーションから自動判定)", "自動")
        self.combo_genre.addItem("ツンデレ・赤面 (照れ隠し・強がり)", "ツンデレ・赤面")
        self.combo_genre.addItem("甘々ラブコメ (恋バナ・告白・耳打ち)", "甘々ラブコメ")
        self.combo_genre.addItem("ギャグ・ツッコミ (テンポの良い驚き・ボケとツッコミ)", "ギャグ・ツッコミ")
        self.combo_genre.addItem("青春・日常 (自然な会話・仲良し自撮り)", "青春・日常")
        self.combo_genre.addItem("シリアス・心の声 (エモーショナルな独白)", "シリアス・心の声")
        self.combo_genre.addItem("🔞 エッチ・あえぎ・甘々 (NSFW・吐息・艶音)", "エッチ・あえぎ・甘々 (NSFW)")
        self.combo_genre.currentIndexChanged.connect(self._on_genre_changed)
        vbox_genre.addWidget(self.combo_genre)
        layout.addWidget(grp_genre)

        # 3. Generation Options (Existing Bubble Detection & NSFW)
        grp_opt = QGroupBox("生成オプション")
        vbox_opt = QVBoxLayout(grp_opt)
        vbox_opt.setSpacing(6)

        self.chk_detect_existing = QCheckBox("既存の空吹き出し枠を自動検出して枠描画をOFFにする")
        self.chk_detect_existing.setChecked(True)
        self.chk_detect_existing.setToolTip(
            "イラスト内にすでに描かれている空のフキダシやセリフ枠を検出し、\n"
            "枠を重ね描きせず文字だけを綺麗に既存枠の中へ流し込みます。"
        )
        vbox_opt.addWidget(self.chk_detect_existing)

        self.chk_nsfw = QCheckBox("🔞 NSFW / 大人向け・刺激的なセリフを許可 (ローカルAI限定)")
        self.chk_nsfw.setToolTip(
            "成人漫画・同人誌のシチュエーションに応じたエッチな台詞やあえぎ声・吐息を生成します。\n"
            "※ クラウドGeminiは規約上ブロックされるため、完全ローカルLLM選択時のみ利用可能です。"
        )
        vbox_opt.addWidget(self.chk_nsfw)
        layout.addWidget(grp_opt)

        # 4. Progress Bar & Status
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate spinner
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #4da6ff; font-weight: bold;")
        layout.addWidget(self.lbl_status)

        # 5. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("キャンセル")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_generate = QPushButton("✨ AIで自動生成する")
        self.btn_generate.setStyleSheet("background-color: #0078d7; font-weight: bold; padding: 6px 18px;")
        self.btn_generate.clicked.connect(self._start_generation)
        btn_layout.addWidget(self.btn_generate)

        layout.addLayout(btn_layout)

        self._refresh_provider_info()

    def _on_genre_changed(self, idx: int):
        data = self.combo_genre.currentData()
        if "NSFW" in str(data) and self.chk_nsfw.isEnabled():
            self.chk_nsfw.setChecked(True)

    def _refresh_provider_info(self):
        cfg = load_config()
        provider = cfg.get("active_provider", "gemini")
        if provider == "gemini":
            model = cfg.get("gemini", {}).get("model", "gemini-3.8-flash")
            has_key = bool(cfg.get("gemini", {}).get("api_key"))
            self.lbl_provider_name.setText(f"Google Gemini ({model})")
            status_text = "APIキー設定済み (準備完了)" if has_key else "⚠️ APIキーが未設定です"
            self.lbl_provider_sub.setText(f"クラウド最速・高精度 | {status_text}")
            self.chk_nsfw.setChecked(False)
            self.chk_nsfw.setEnabled(False)
            self.chk_nsfw.setText("🔞 NSFWセリフ (ローカルLLM選択時のみ利用可能)")
        elif provider == "openai_compatible":
            model = cfg.get("openai_compatible", {}).get("model", "gpt-4o-mini")
            base_url = cfg.get("openai_compatible", {}).get("base_url", "OpenAI")
            is_local = any(h in base_url.lower() for h in ("localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10."))
            has_key = bool(cfg.get("openai_compatible", {}).get("api_key")) or is_local
            self.lbl_provider_name.setText(f"OpenAI互換API ({model})")
            status_text = "準備完了 (ローカル)" if is_local else ("APIキー設定済み" if has_key else "⚠️ APIキー未設定")
            self.lbl_provider_sub.setText(f"接続先: {base_url} | {status_text}")
            if is_local:
                self.chk_nsfw.setEnabled(True)
                self.chk_nsfw.setText("🔞 NSFW / 大人向け・刺激的なセリフを許可 (ローカル専用)")
            else:
                self.chk_nsfw.setChecked(False)
                self.chk_nsfw.setEnabled(False)
                self.chk_nsfw.setText("🔞 NSFWセリフ (ローカルLLM選択時のみ利用可能)")
        elif provider == "local_ollama":
            model = cfg.get("local_ollama", {}).get("model", "qwen3-vl-8b-nsfw-caption-v4.5")
            base_url = cfg.get("local_ollama", {}).get("base_url", "http://localhost:1234/v1")
            self.lbl_provider_name.setText(f"完全ローカルLLM / LM Studio ({model})")
            self.lbl_provider_sub.setText(f"OpenAI互換サーバー: {base_url} | オフライン・APIキー不要")
            self.chk_nsfw.setEnabled(True)
            self.chk_nsfw.setText("🔞 NSFW / 大人向け・刺激的なセリフを許可 (ローカルLLM専用)")

    def _open_settings(self):
        dlg = AISettingsDialog(self)
        if dlg.exec():
            self._refresh_provider_info()

    def _start_generation(self):
        cfg = load_config()
        provider = cfg.get("active_provider", "gemini")

        # Validation
        if provider == "gemini" and not cfg.get("gemini", {}).get("api_key"):
            res = QMessageBox.warning(
                self, "APIキーが必要です",
                "Google Gemini APIキーが設定されていません。\n今すぐ設定画面を開きますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.Yes:
                self._open_settings()
            return

        if provider == "openai_compatible":
            o_cfg = cfg.get("openai_compatible", {})
            base_url = o_cfg.get("base_url", "")
            is_local = any(h in base_url.lower() for h in ("localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10."))
            if not o_cfg.get("api_key") and not is_local:
                res = QMessageBox.warning(
                    self, "APIキーが必要です",
                    "APIキーが設定されていません。\n今すぐ設定画面を開きますか？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if res == QMessageBox.StandardButton.Yes:
                    self._open_settings()
                return

        if not self.current_image:
            QMessageBox.warning(self, "画像がありません", "先にイラスト画像を読み込んでください。")
            return

        genre = self.combo_genre.currentText()
        self.btn_generate.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_status.setText("🤖 AIがイラストの表情・文脈を分析中...")

        self.worker = AIGeneratorThread(
            self.current_image,
            genre,
            nsfw=self.chk_nsfw.isChecked(),
            detect_existing=self.chk_detect_existing.isChecked()
        )
        self.worker.progress_update.connect(self.lbl_status.setText)
        self.worker.finished_success.connect(self._on_success)
        self.worker.finished_error.connect(self._on_error)
        self.worker.start()

    def _on_success(self, desc: str, bubbles: list):
        self.generated_bubbles = bubbles
        self.scene_description = desc
        self.accept()

    def _on_error(self, err_msg: str):
        self.progress.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.lbl_status.setText("")
        QMessageBox.critical(self, "AI生成エラー", f"セリフの生成中にエラーが発生しました:\n\n{err_msg}")

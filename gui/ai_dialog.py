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
    QPushButton, QMessageBox, QProgressBar, QGroupBox, QFrame
)

from comic_bubble.config import load_config
from comic_bubble.ai_generator import generate_scene_dialogue
from comic_bubble.models import BubbleConfig
from .settings_dialog import AISettingsDialog


class AIGeneratorThread(QThread):
    """Background worker thread for AI generation to keep GUI responsive."""

    finished_success = Signal(str, list)  # scene_desc, bubble_configs
    finished_error = Signal(str)

    def __init__(self, image: Image.Image, genre_hint: str):
        super().__init__()
        self.image = image
        self.genre_hint = genre_hint

    def run(self):
        try:
            desc, bubbles = generate_scene_dialogue(
                image=self.image,
                genre_hint=self.genre_hint
            )
            self.finished_success.emit(desc, bubbles)
        except Exception as e:
            self.finished_error.emit(str(e))


class AIDialogueDialog(QDialog):
    """Dialog for launching AI dialogue generation with customizable tone/genre."""

    def __init__(self, current_image: Optional[Image.Image], parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ AIセリフ自動生成")
        self.resize(480, 310)
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
        vbox_genre.addWidget(self.combo_genre)
        layout.addWidget(grp_genre)

        # 3. Progress Bar & Status
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate spinner
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #4da6ff; font-weight: bold;")
        layout.addWidget(self.lbl_status)

        # 4. Action Buttons
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

    def _refresh_provider_info(self):
        cfg = load_config()
        provider = cfg.get("active_provider", "gemini")
        if provider == "gemini":
            model = cfg.get("gemini", {}).get("model", "gemini-2.0-flash")
            has_key = bool(cfg.get("gemini", {}).get("api_key"))
            self.lbl_provider_name.setText(f"Google Gemini ({model})")
            status_text = "APIキー設定済み (準備完了)" if has_key else "⚠️ APIキーが未設定です"
            self.lbl_provider_sub.setText(f"クラウド最速・高精度 | {status_text}")
        elif provider == "openai_compatible":
            model = cfg.get("openai_compatible", {}).get("model", "gpt-4o-mini")
            base_url = cfg.get("openai_compatible", {}).get("base_url", "OpenAI")
            has_key = bool(cfg.get("openai_compatible", {}).get("api_key"))
            self.lbl_provider_name.setText(f"クラウドAPI ({model})")
            status_text = "APIキー設定済み" if has_key else "⚠️ APIキー未設定"
            self.lbl_provider_sub.setText(f"接続先: {base_url} | {status_text}")
        elif provider == "local_ollama":
            model = cfg.get("local_ollama", {}).get("model", "qwen2.5-vl:7b")
            base_url = cfg.get("local_ollama", {}).get("base_url", "http://localhost:11434")
            self.lbl_provider_name.setText(f"完全ローカルLLM ({model})")
            self.lbl_provider_sub.setText(f"サーバー: {base_url} | オフライン・通信ゼロ")

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

        if provider == "openai_compatible" and not cfg.get("openai_compatible", {}).get("api_key"):
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

        self.worker = AIGeneratorThread(self.current_image, genre)
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

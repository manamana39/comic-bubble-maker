"""
gui.ai_dialog
~~~~~~~~~~~~~
AI dialogue generation dialog and background QThread worker.
"""

from typing import Optional, List
from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QProgressBar, QGroupBox
)

from comic_bubble.ai_generator import (
    get_stored_api_key, save_stored_api_key, generate_scene_dialogue
)
from comic_bubble.models import BubbleConfig


class AIGeneratorThread(QThread):
    """Background worker thread for Gemini API call to keep GUI responsive."""

    finished_success = Signal(str, list)  # scene_desc, bubble_configs
    finished_error = Signal(str)

    def __init__(self, image: Image.Image, api_key: str, genre_hint: str):
        super().__init__()
        self.image = image
        self.api_key = api_key
        self.genre_hint = genre_hint

    def run(self):
        try:
            desc, bubbles = generate_scene_dialogue(
                image=self.image,
                api_key=self.api_key,
                genre_hint=self.genre_hint
            )
            self.finished_success.emit(desc, bubbles)
        except Exception as e:
            self.finished_error.emit(str(e))


class AIDialogueDialog(QDialog):
    """Dialog for launching AI dialogue generation with customizable tone/genre."""

    def __init__(self, current_image: Optional[Image.Image], parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ AIセリフ自動生成 (Gemini)")
        self.resize(460, 320)
        self.current_image = current_image

        self.generated_bubbles: Optional[List[BubbleConfig]] = None
        self.scene_description: str = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. API Key Group
        grp_key = QGroupBox("Google Gemini API キー")
        vbox_key = QVBoxLayout(grp_key)

        row_key = QHBoxLayout()
        self.txt_key = QLineEdit()
        self.txt_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_key.setPlaceholderText("AIzaSy... (Google AI Studioで取得)")
        saved_key = get_stored_api_key()
        if saved_key:
            self.txt_key.setText(saved_key)
        row_key.addWidget(self.txt_key)

        btn_show_key = QPushButton("表示")
        btn_show_key.setFixedWidth(50)
        btn_show_key.setCheckable(True)
        btn_show_key.toggled.connect(
            lambda chk: self.txt_key.setEchoMode(QLineEdit.EchoMode.Normal if chk else QLineEdit.EchoMode.Password)
        )
        row_key.addWidget(btn_show_key)
        vbox_key.addLayout(row_key)

        lbl_key_tip = QLabel("※ APIキーは端末内（~/.comic_bubble_config.json）に安全に保存されます。")
        lbl_key_tip.setStyleSheet("color: #888; font-size: 11px;")
        vbox_key.addWidget(lbl_key_tip)
        layout.addWidget(grp_key)

        # 2. Genre / Situation Preference
        grp_genre = QGroupBox("セリフの作風・シチュエーション")
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

        # 3. Progress Bar
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
        self.btn_generate.setStyleSheet("background-color: #0078d7; font-weight: bold; padding: 6px 16px;")
        self.btn_generate.clicked.connect(self._start_generation)
        btn_layout.addWidget(self.btn_generate)

        layout.addLayout(btn_layout)

    def _start_generation(self):
        api_key = self.txt_key.text().strip()
        if not api_key:
            QMessageBox.warning(self, "APIキーが必要です", "Google Gemini APIキーを入力してください。\n(Google AI Studioから無料取得できます)")
            return

        if not self.current_image:
            QMessageBox.warning(self, "画像がありません", "先にイラスト画像を読み込んでください。")
            return

        # Save API key for future use
        save_stored_api_key(api_key)

        genre = self.combo_genre.currentText()
        self.btn_generate.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_status.setText("🤖 Geminiがイラストの表情・文脈を分析中...")

        self.worker = AIGeneratorThread(self.current_image, api_key, genre)
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

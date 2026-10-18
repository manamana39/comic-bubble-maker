"""
gui.settings_dialog
~~~~~~~~~~~~~~~~~~~
Multi-provider AI configuration dialog with tabbed interface:
- Google Gemini API
- Other Cloud APIs (OpenAI, DeepSeek, Groq, OpenRouter)
- Local LLMs (Ollama, LM Studio)
"""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTabWidget, QWidget,
    QGroupBox, QFormLayout
)

from comic_bubble.config import load_config, save_config
from comic_bubble.ai_generator import (
    test_gemini_connection, test_openai_connection, test_ollama_connection
)


class AISettingsDialog(QDialog):
    """Full-featured multi-provider AI settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ AIプロバイダー設定")
        self.resize(520, 440)
        self.cfg = load_config()

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # 1. Active Provider Selector
        row_active = QHBoxLayout()
        lbl_active = QLabel("現在使用するAIプロバイダー:")
        lbl_active.setStyleSheet("font-weight: bold; font-size: 13px;")
        row_active.addWidget(lbl_active)

        self.combo_active = QComboBox()
        self.combo_active.addItem("Google Gemini (クラウドAPI・最速・推奨)", "gemini")
        self.combo_active.addItem("よそのクラウド (OpenAI / DeepSeek / Groq)", "openai_compatible")
        self.combo_active.addItem("完全ローカルLLM (Ollama / RTX 5060 Ti)", "local_ollama")

        cur_provider = self.cfg.get("active_provider", "gemini")
        idx = self.combo_active.findData(cur_provider)
        if idx >= 0:
            self.combo_active.setCurrentIndex(idx)
        self.combo_active.currentIndexChanged.connect(self._on_active_provider_changed)
        row_active.addWidget(self.combo_active)
        main_layout.addLayout(row_active)

        # 2. Tabs
        self.tabs = QTabWidget()
        self.tab_gemini = self._create_gemini_tab()
        self.tab_openai = self._create_openai_tab()
        self.tab_ollama = self._create_ollama_tab()

        self.tabs.addTab(self.tab_gemini, "Google Gemini")
        self.tabs.addTab(self.tab_openai, "よそのクラウド (OpenAI互換)")
        self.tabs.addTab(self.tab_ollama, "ローカルLLM (Ollama)")
        main_layout.addWidget(self.tabs)

        # Sync tab selection with active provider
        if cur_provider == "gemini":
            self.tabs.setCurrentIndex(0)
        elif cur_provider == "openai_compatible":
            self.tabs.setCurrentIndex(1)
        elif cur_provider == "local_ollama":
            self.tabs.setCurrentIndex(2)

        # 3. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("キャンセル")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("設定を保存")
        self.btn_save.setStyleSheet("background-color: #0078d7; font-weight: bold; padding: 6px 18px;")
        self.btn_save.clicked.connect(self._save_and_close)
        btn_layout.addWidget(self.btn_save)

        main_layout.addLayout(btn_layout)

    def _on_active_provider_changed(self, index):
        self.tabs.setCurrentIndex(index)

    # --- Tab 1: Google Gemini ---
    def _create_gemini_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        form = QFormLayout()

        # API Key
        row_key = QHBoxLayout()
        self.txt_gemini_key = QLineEdit(self.cfg["gemini"].get("api_key", ""))
        self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_gemini_key.setPlaceholderText("AIzaSy... (Google AI Studio)")
        row_key.addWidget(self.txt_gemini_key)

        btn_show = QPushButton("表示")
        btn_show.setFixedWidth(50)
        btn_show.setCheckable(True)
        btn_show.toggled.connect(
            lambda chk: self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Normal if chk else QLineEdit.EchoMode.Password)
        )
        row_key.addWidget(btn_show)
        form.addRow("APIキー:", row_key)

        # Model
        self.combo_gemini_model = QComboBox()
        self.combo_gemini_model.setEditable(True)
        self.combo_gemini_model.addItem("gemini-2.0-flash", "gemini-2.0-flash")
        self.combo_gemini_model.addItem("gemini-1.5-flash", "gemini-1.5-flash")
        self.combo_gemini_model.addItem("gemini-2.0-pro", "gemini-2.0-pro")
        self.combo_gemini_model.addItem("gemini-1.5-pro", "gemini-1.5-pro")

        saved_model = self.cfg["gemini"].get("model", "gemini-2.0-flash")
        self.combo_gemini_model.setCurrentText(saved_model)
        form.addRow("モデル名:", self.combo_gemini_model)

        layout.addLayout(form)

        # Test Connection Button
        btn_test = QPushButton("Gemini API 接続テスト")
        btn_test.clicked.connect(self._test_gemini)
        layout.addWidget(btn_test)

        lbl_hint = QLabel("💡 Google AI Studio (無料) からAPIキーを発行して貼り付けてください。")
        lbl_hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(lbl_hint)
        layout.addStretch()
        return widget

    def _test_gemini(self):
        key = self.txt_gemini_key.text().strip()
        model = self.combo_gemini_model.currentText().strip()
        if not key:
            QMessageBox.warning(self, "エラー", "Gemini APIキーを入力してください。")
            return
        try:
            msg = test_gemini_connection(key, model)
            QMessageBox.information(self, "接続テスト結果", msg)
        except Exception as e:
            QMessageBox.critical(self, "接続テスト失敗", f"接続エラー:\n{e}")

    # --- Tab 2: OpenAI Compatible ---
    def _create_openai_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        form = QFormLayout()

        # Preset Provider Selector
        self.combo_preset = QComboBox()
        self.combo_preset.addItem("手動設定 / カスタム", "")
        self.combo_preset.addItem("OpenAI (https://api.openai.com/v1)", "https://api.openai.com/v1")
        self.combo_preset.addItem("DeepSeek (https://api.deepseek.com/v1)", "https://api.deepseek.com/v1")
        self.combo_preset.addItem("Groq (https://api.groq.com/openai/v1)", "https://api.groq.com/openai/v1")
        self.combo_preset.addItem("OpenRouter (https://openrouter.ai/api/v1)", "https://openrouter.ai/api/v1")
        self.combo_preset.currentIndexChanged.connect(self._on_preset_changed)
        form.addRow("プリセット:", self.combo_preset)

        # Base URL
        self.txt_openai_url = QLineEdit(self.cfg["openai_compatible"].get("base_url", "https://api.openai.com/v1"))
        self.txt_openai_url.setPlaceholderText("https://api.openai.com/v1")
        form.addRow("ベースURL:", self.txt_openai_url)

        # API Key
        row_key = QHBoxLayout()
        self.txt_openai_key = QLineEdit(self.cfg["openai_compatible"].get("api_key", ""))
        self.txt_openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_openai_key.setPlaceholderText("sk-... または各サービスのAPIキー")
        row_key.addWidget(self.txt_openai_key)

        btn_show = QPushButton("表示")
        btn_show.setFixedWidth(50)
        btn_show.setCheckable(True)
        btn_show.toggled.connect(
            lambda chk: self.txt_openai_key.setEchoMode(QLineEdit.EchoMode.Normal if chk else QLineEdit.EchoMode.Password)
        )
        row_key.addWidget(btn_show)
        form.addRow("APIキー:", row_key)

        # Model Name
        self.combo_openai_model = QComboBox()
        self.combo_openai_model.setEditable(True)
        self.combo_openai_model.addItem("gpt-4o-mini")
        self.combo_openai_model.addItem("gpt-4o")
        self.combo_openai_model.addItem("deepseek-chat")
        self.combo_openai_model.addItem("llama-3.2-11b-vision-preview")
        saved_m = self.cfg["openai_compatible"].get("model", "gpt-4o-mini")
        self.combo_openai_model.setCurrentText(saved_m)
        form.addRow("モデル名:", self.combo_openai_model)

        layout.addLayout(form)

        # Test Button
        btn_test = QPushButton("クラウドAPI 接続テスト")
        btn_test.clicked.connect(self._test_openai)
        layout.addWidget(btn_test)

        lbl_hint = QLabel("💡 画像認識 (Vision) に対応したモデル名を指定してください。")
        lbl_hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(lbl_hint)
        layout.addStretch()
        return widget

    def _on_preset_changed(self, idx):
        url = self.combo_preset.currentData()
        if url:
            self.txt_openai_url.setText(url)
            if "deepseek" in url:
                self.combo_openai_model.setCurrentText("deepseek-chat")
            elif "groq" in url:
                self.combo_openai_model.setCurrentText("llama-3.2-11b-vision-preview")
            elif "openai" in url:
                self.combo_openai_model.setCurrentText("gpt-4o-mini")

    def _test_openai(self):
        url = self.txt_openai_url.text().strip()
        key = self.txt_openai_key.text().strip()
        model = self.combo_openai_model.currentText().strip()
        if not key:
            QMessageBox.warning(self, "エラー", "APIキーを入力してください。")
            return
        try:
            msg = test_openai_connection(key, url, model)
            QMessageBox.information(self, "接続テスト結果", msg)
        except Exception as e:
            QMessageBox.critical(self, "接続テスト失敗", f"接続エラー:\n{e}")

    # --- Tab 3: Local Ollama ---
    def _create_ollama_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        form = QFormLayout()

        # Server URL
        self.txt_ollama_url = QLineEdit(self.cfg["local_ollama"].get("base_url", "http://localhost:11434"))
        self.txt_ollama_url.setPlaceholderText("http://localhost:11434")
        form.addRow("サーバーURL:", self.txt_ollama_url)

        # Model Selector
        self.combo_ollama_model = QComboBox()
        self.combo_ollama_model.setEditable(True)
        self.combo_ollama_model.addItem("qwen2.5-vl:7b")
        self.combo_ollama_model.addItem("qwen2.5-vl:3b")
        self.combo_ollama_model.addItem("minicpm-v")
        self.combo_ollama_model.addItem("llava")
        saved_m = self.cfg["local_ollama"].get("model", "qwen2.5-vl:7b")
        self.combo_ollama_model.setCurrentText(saved_m)
        form.addRow("モデル名:", self.combo_ollama_model)

        layout.addLayout(form)

        # Test and Fetch models Button
        btn_test = QPushButton("🔍 ローカル接続テスト & モデル一覧自動取得")
        btn_test.clicked.connect(self._test_ollama)
        layout.addWidget(btn_test)

        lbl_hint = QLabel("💡 RTX 5060 Ti (16GB) をお持ちのため、'qwen2.5-vl:7b' が高速・完全オフラインで動作します。")
        lbl_hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(lbl_hint)
        layout.addStretch()
        return widget

    def _test_ollama(self):
        url = self.txt_ollama_url.text().strip()
        try:
            msg, models = test_ollama_connection(url)
            if models:
                self.combo_ollama_model.clear()
                for m in models:
                    self.combo_ollama_model.addItem(m)
                QMessageBox.information(
                    self, "接続テスト成功",
                    f"{msg}\nインストール済みモデルをリストに反映しました:\n" + ", ".join(models)
                )
            else:
                QMessageBox.information(self, "接続テスト成功", f"{msg}\n(モデルがまだダウンロードされていません。例: 'ollama run qwen2.5-vl:7b')")
        except Exception as e:
            QMessageBox.critical(self, "Ollama接続失敗", f"{e}")

    # --- Save & Apply ---
    def _save_and_close(self):
        active_provider = self.combo_active.currentData()
        self.cfg["active_provider"] = active_provider

        # Gemini
        self.cfg["gemini"]["api_key"] = self.txt_gemini_key.text().strip()
        self.cfg["gemini"]["model"] = self.combo_gemini_model.currentText().strip()

        # OpenAI
        self.cfg["openai_compatible"]["api_key"] = self.txt_openai_key.text().strip()
        self.cfg["openai_compatible"]["base_url"] = self.txt_openai_url.text().strip()
        self.cfg["openai_compatible"]["model"] = self.combo_openai_model.currentText().strip()

        # Ollama
        self.cfg["local_ollama"]["base_url"] = self.txt_ollama_url.text().strip()
        self.cfg["local_ollama"]["model"] = self.combo_ollama_model.currentText().strip()

        save_config(self.cfg)
        QMessageBox.information(self, "保存完了", "AI設定を正常に保存しました！")
        self.accept()

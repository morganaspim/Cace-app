from __future__ import annotations

try:
    from PySide6.QtWidgets import (
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QVBoxLayout,
    )
except ImportError as exc:  # pragma: no cover - imported only by GUI builds
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc

from cace_studio.ai.local import KNOWN_LOCAL_PROVIDERS, create_local_provider, detect_local_providers
from cace_studio.ai.provider import LocalAIError
from cace_studio.core.settings import AI_MODES


class LocalAISettingsDialog(QDialog):
    """No-code local-AI provider/model configuration.

    This dialog configures optional assistant behavior only. It has no access to
    CACE verification records, certificates, or proof-ledger promotion.
    """

    def __init__(self, settings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Configure Local AI")
        self.resize(560, 260)

        self.provider = QComboBox()
        for provider_id in ("ollama", "lm-studio", "llama-cpp", "openai-compatible"):
            self.provider.addItem(KNOWN_LOCAL_PROVIDERS[provider_id][0], provider_id)
        index = self.provider.findData(settings.ai_provider)
        self.provider.setCurrentIndex(index if index >= 0 else 0)

        self.endpoint = QLineEdit(settings.ai_endpoint)
        self.model = QComboBox()
        self.model.setEditable(True)
        if settings.ai_model:
            self.model.addItem(settings.ai_model)
            self.model.setCurrentText(settings.ai_model)

        self.mode = QComboBox()
        for mode in AI_MODES:
            self.mode.addItem(mode.title(), mode)
        mode_index = self.mode.findData(settings.assistant_mode)
        self.mode.setCurrentIndex(mode_index if mode_index >= 0 else self.mode.findData("researcher"))

        self.status = QLabel("AI is optional and never counts as verification evidence.")
        self.status.setWordWrap(True)

        detect = QPushButton("Auto-detect local AI")
        detect.clicked.connect(self._detect)
        test = QPushButton("Test connection")
        test.clicked.connect(self._test)
        buttons_row = QHBoxLayout()
        buttons_row.addWidget(detect)
        buttons_row.addWidget(test)
        buttons_row.addStretch()

        form = QFormLayout()
        form.addRow("Provider", self.provider)
        form.addRow("Endpoint", self.endpoint)
        form.addRow("Model", self.model)
        form.addRow("Assistant mode", self.mode)

        dialog_buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons_row)
        layout.addWidget(self.status)
        layout.addWidget(dialog_buttons)

        self.provider.currentIndexChanged.connect(self._provider_changed)

    def _current_provider_id(self) -> str:
        return str(self.provider.currentData())

    def _provider_changed(self) -> None:
        provider_id = self._current_provider_id()
        _, default_endpoint = KNOWN_LOCAL_PROVIDERS[provider_id]
        known_defaults = {value[1] for value in KNOWN_LOCAL_PROVIDERS.values()}
        if not self.endpoint.text().strip() or self.endpoint.text().strip() in known_defaults:
            self.endpoint.setText(default_endpoint)
        self.model.clear()

    def _set_models(self, models: tuple[str, ...], preferred: str = "") -> None:
        current = preferred or self.model.currentText().strip()
        self.model.clear()
        self.model.addItems(list(models))
        if current:
            self.model.setCurrentText(current)
        elif models:
            self.model.setCurrentIndex(0)

    def _detect(self) -> None:
        self.status.setText("Checking known loopback endpoints…")
        results = detect_local_providers(timeout=0.6)
        healthy = [item for item in results if item.healthy]
        if not healthy:
            self.status.setText("No known local provider responded. Start Ollama, LM Studio, or llama.cpp, or enter a local OpenAI-compatible endpoint manually.")
            return
        found = healthy[0]
        index = self.provider.findData(found.provider_id)
        if index >= 0:
            self.provider.setCurrentIndex(index)
        self.endpoint.setText(found.endpoint)
        self._set_models(found.models, self.settings.ai_model)
        names = ", ".join(item.name for item in healthy)
        self.status.setText(f"Detected: {names}. Selected {found.name}.")

    def _test(self) -> None:
        provider_id = self._current_provider_id()
        endpoint = self.endpoint.text().strip()
        model = self.model.currentText().strip()
        try:
            provider = create_local_provider(provider_id, endpoint, model, timeout=2.0)
        except LocalAIError as exc:
            self.status.setText(f"Invalid local endpoint: {exc}")
            return
        health = provider.health()
        if health.healthy:
            self._set_models(health.models, model)
            self.status.setText(f"Connected to {health.name}. {len(health.models)} model(s) reported.")
        else:
            self.status.setText(f"Connection failed: {health.detail}")

    def accept(self) -> None:
        provider_id = self._current_provider_id()
        endpoint = self.endpoint.text().strip()
        model = self.model.currentText().strip()
        try:
            provider = create_local_provider(provider_id, endpoint, model, timeout=2.0)
        except LocalAIError as exc:
            self.status.setText(f"Cannot save local AI settings: {exc}")
            return

        self.settings.ai_provider = provider_id
        self.settings.ai_endpoint = provider.endpoint
        self.settings.ai_model = model
        self.settings.assistant_mode = str(self.mode.currentData())
        self.settings.save()
        super().accept()

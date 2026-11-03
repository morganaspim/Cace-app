from __future__ import annotations

try:
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget
except ImportError as exc:  # pragma: no cover - GUI-only module
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc

from cace_studio.ai import AICapabilityPolicy, LocalAIError, create_local_provider


_MODE_GUIDANCE = {
    "hints": "Give concise hints and questions; avoid doing the whole task unless explicitly asked.",
    "teacher": "Explain concepts step by step and distinguish assumptions from conclusions.",
    "researcher": "Help design rigorous scientific experiments and identify evidence limits and open obligations.",
    "autonomous": "Propose complete research workflows, but require user review before any repository or experiment mutation.",
}


class _WorkerSignals(QObject):
    finished = Signal(str)
    failed = Signal(str)


class _ChatWorker(QRunnable):
    def __init__(self, provider, messages) -> None:
        super().__init__()
        self.provider = provider
        self.messages = messages
        self.signals = _WorkerSignals()

    def run(self) -> None:  # pragma: no cover - exercised through GUI integration
        try:
            text = self.provider.chat(self.messages)
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(text)


class LocalAIAssistantWidget(QWidget):
    """Optional local assistant panel with no verification privileges."""

    def __init__(self, settings, configure_callback, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.configure_callback = configure_callback
        self.history: list[dict[str, str]] = []
        self.pool = QThreadPool.globalInstance()

        self.status = QLabel()
        self.status.setWordWrap(True)
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("Local AI conversation. Assistant output is never verification evidence.")
        self.prompt = QLineEdit()
        self.prompt.setPlaceholderText("Ask the local CACE assistant…")
        self.prompt.returnPressed.connect(self.send)
        self.send_button = QPushButton("Ask")
        self.send_button.clicked.connect(self.send)
        configure = QPushButton("Configure")
        configure.clicked.connect(self.configure_callback)

        row = QHBoxLayout()
        row.addWidget(self.prompt)
        row.addWidget(self.send_button)
        row.addWidget(configure)
        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.transcript)
        layout.addLayout(row)
        self.refresh()

    def refresh(self) -> None:
        if not self.settings.ai_enabled:
            self.status.setText("AI is OFF. CACE execution and verification are unaffected.")
            self.send_button.setEnabled(False)
            return
        model = self.settings.ai_model or "no model selected"
        tier_note = (
            "superintelligence-class tier ALLOWED"
            if self.settings.allow_superintelligence_class_ai
            else "superintelligence-class tier BLOCKED"
        )
        self.status.setText(
            f"AI ON — {self.settings.ai_provider} / {model} / mode={self.settings.assistant_mode}. "
            f"{tier_note}. Assistant text is not verification evidence."
        )
        self.send_button.setEnabled(bool(self.settings.ai_model))

    def _system_message(self) -> str:
        guidance = _MODE_GUIDANCE.get(self.settings.assistant_mode, _MODE_GUIDANCE["researcher"])
        return (
            "You are the optional local assistant inside CACE Studio. "
            "Never describe your own output as mathematical proof, formal verification, a certificate, or executed evidence. "
            "Preserve explicit assumptions and distinguish numerical, symbolic, interval and formal evidence. "
            "Do not claim that simulations solve famous open problems. "
            + guidance
        )

    def _provider_allowed(self, provider) -> bool:
        decision = AICapabilityPolicy.from_settings(self.settings).admit(
            provider.capability_manifest()
        )
        if decision.allowed:
            return True
        self.transcript.append(
            "[system] AI capability gate denied this provider: " + "; ".join(decision.reasons)
        )
        return False

    def ask_context(self, text: str, *, label: str = "context") -> bool:
        text = str(text).strip()
        if not text:
            return False
        if not self.settings.ai_enabled:
            self.transcript.append(f"[{label}] Local AI is disabled; context was not sent.")
            return False
        if not self.settings.ai_model:
            self.transcript.append(f"[{label}] Choose a local model before sending context.")
            return False
        try:
            provider = create_local_provider(
                self.settings.ai_provider,
                self.settings.ai_endpoint,
                self.settings.ai_model,
                timeout=60.0,
            )
        except LocalAIError as exc:
            self.transcript.append(f"[{label}] {exc}")
            return False
        if not self._provider_allowed(provider):
            return False
        self.transcript.append(f"[{label}] structured CACE context submitted")
        self.history.append({"role": "user", "content": text})
        messages = [{"role": "system", "content": self._system_message()}] + self.history[-20:]
        worker = _ChatWorker(provider, messages)
        worker.signals.finished.connect(self._finished)
        worker.signals.failed.connect(self._failed)
        self.send_button.setEnabled(False)
        self.status.setText(f"Local AI is analyzing {label} context…")
        self.pool.start(worker)
        return True

    def send(self) -> None:
        text = self.prompt.text().strip()
        if not text:
            return
        if not self.settings.ai_enabled:
            self.transcript.append("[system] AI is disabled.")
            return
        if not self.settings.ai_model:
            self.transcript.append("[system] Choose a local model in Configure Local AI first.")
            return
        try:
            provider = create_local_provider(
                self.settings.ai_provider,
                self.settings.ai_endpoint,
                self.settings.ai_model,
                timeout=60.0,
            )
        except LocalAIError as exc:
            self.transcript.append(f"[system] {exc}")
            return
        if not self._provider_allowed(provider):
            return

        self.prompt.clear()
        self.transcript.append(f"[you] {text}")
        self.history.append({"role": "user", "content": text})
        messages = [{"role": "system", "content": self._system_message()}] + self.history[-20:]
        worker = _ChatWorker(provider, messages)
        worker.signals.finished.connect(self._finished)
        worker.signals.failed.connect(self._failed)
        self.send_button.setEnabled(False)
        self.status.setText("Local AI is generating…")
        self.pool.start(worker)

    def _finished(self, text: str) -> None:
        self.history.append({"role": "assistant", "content": text})
        self.transcript.append(f"[assistant] {text}")
        self.refresh()

    def _failed(self, error: str) -> None:
        self.transcript.append(f"[system] Local AI request failed: {error}")
        self.refresh()

from __future__ import annotations

try:
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget
except ImportError as exc:  # pragma: no cover - GUI-only module
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc

from cace_studio.ai import LocalAIError, create_local_provider
from cace_studio.ai.corpus import build_local_index
from cace_studio.ai.hybrid import GrowthEngine


_MODE_GUIDANCE = {
    "hints": "Give concise hints and questions; avoid doing the whole task unless explicitly asked.",
    "teacher": "Explain concepts step by step and distinguish assumptions from conclusions.",
    "researcher": "Help design rigorous scientific experiments and identify evidence limits and open obligations.",
    "general": "Be generally useful: route to the cheapest relevant capability, connect useful domains, and make assumptions explicit.",
    "autonomous": "Propose complete research workflows, but require user review before any repository or experiment mutation.",
}


class _WorkerSignals(QObject):
    finished = Signal(str)
    failed = Signal(str)


class _GrowSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class _GrowWorker(QRunnable):
    def __init__(
        self,
        engine,
        query: str,
        cycle: int,
        chaos: float,
        budget: int,
        max_group_size: int,
        embedding_provider=None,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.query = query
        self.cycle = cycle
        self.chaos = chaos
        self.budget = budget
        self.max_group_size = max_group_size
        self.embedding_provider = embedding_provider
        self.signals = _GrowSignals()

    def run(self) -> None:  # pragma: no cover - exercised through GUI integration
        try:
            engine = self.engine or GrowthEngine(build_local_index())
            result = engine.grow(
                self.query,
                cycle=self.cycle,
                chaos=self.chaos,
                group_budget=self.budget,
                max_group_size=self.max_group_size,
                embedding_provider=self.embedding_provider,
            )
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit((engine, result))


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

    def __init__(self, settings, configure_callback, parent=None, context_provider=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.configure_callback = configure_callback
        self.context_provider = context_provider
        self.history: list[dict[str, str]] = []
        self.pool = QThreadPool.globalInstance()
        self._growth_engine = None
        self._growth_cycle = 0
        self._growth_context = ""

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
        self.grow_button = QPushButton("Grow")
        self.grow_button.setToolTip(
            "Explore bounded local concept combinations and semantic random walks. "
            "Grow never mutates scientific data, proof evidence, or model weights."
        )
        self.grow_button.clicked.connect(self.grow)
        self.general_button = QPushButton("Generally Useful")
        self.general_button.setToolTip("Switch the assistant to broad low-cost routing mode.")
        self.general_button.clicked.connect(self.set_generally_useful)
        configure = QPushButton("Configure")
        configure.clicked.connect(self.configure_callback)

        row = QHBoxLayout()
        row.addWidget(self.prompt)
        row.addWidget(self.send_button)
        row.addWidget(self.grow_button)
        row.addWidget(self.general_button)
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
            self.grow_button.setEnabled(True)
            return
        model = self.settings.ai_model or "no model selected"
        self.status.setText(
            f"AI ON — {self.settings.ai_provider} / {model} / mode={self.settings.assistant_mode}. "
            "Assistant text is not verification evidence."
        )
        self.send_button.setEnabled(bool(self.settings.ai_model))
        self.grow_button.setEnabled(True)
        self.general_button.setText(
            "Generally Useful ✓" if self.settings.assistant_mode == "general" else "Generally Useful"
        )

    def _system_message(self) -> str:
        guidance = _MODE_GUIDANCE.get(self.settings.assistant_mode, _MODE_GUIDANCE["researcher"])
        return (
            "You are the optional local assistant inside CACE Studio. "
            "Never describe your own output as mathematical proof, formal verification, a certificate, or executed evidence. "
            "Preserve explicit assumptions and distinguish numerical, symbolic, interval and formal evidence. "
            "Do not claim that simulations solve famous open problems. "
            + guidance
        )

    def _live_context(self) -> str:
        if self.context_provider is None:
            return ""
        try:
            text = str(self.context_provider() or "")
        except Exception as exc:
            return f"Live experiment context unavailable: {type(exc).__name__}: {exc}"
        return text[:6000]

    def set_generally_useful(self) -> None:
        self.settings.assistant_mode = "general"
        self.settings.save()
        self.transcript.append(
            "[system] Generally Useful mode enabled. The assistant will favor cheap routing and cross-domain usefulness."
        )
        self.refresh()

    def grow(self) -> None:
        query = self.prompt.text().strip()
        if not query:
            query = (
                self.history[-1]["content"]
                if self.history and self.history[-1].get("role") == "user"
                else "Find useful low-cost cross-module research connections in CACE."
            )
        self.grow_button.setEnabled(False)
        self.status.setText("Grow is exploring the local CACE corpus…")
        live_context = self._live_context()
        growth_query = query if not live_context else query + "\n\nCURRENT CACE EXPERIMENT:\n" + live_context
        embedding_provider = None
        if self.settings.ai_embedding_model:
            try:
                embedding_provider = create_local_provider(
                    self.settings.ai_provider,
                    self.settings.ai_endpoint,
                    self.settings.ai_embedding_model,
                    timeout=60.0,
                )
            except LocalAIError as exc:
                self.transcript.append(
                    f"[grow] Embedding model disabled for this cycle: {exc}"
                )
        worker = _GrowWorker(
            self._growth_engine,
            growth_query,
            self._growth_cycle,
            float(self.settings.ai_growth_chaos),
            int(self.settings.ai_growth_budget),
            int(self.settings.ai_growth_max_group_size),
            embedding_provider,
        )
        worker.signals.finished.connect(self._grow_finished)
        worker.signals.failed.connect(self._grow_failed)
        self.pool.start(worker)

    def _grow_finished(self, payload) -> None:
        engine, result = payload
        self._growth_engine = engine
        self._growth_cycle += 1
        self._growth_context = result.context_text()
        routes = ", ".join(route.expert_id for route in result.routes) or "general"
        top_sources = []
        for ranked in result.retrieved[:4]:
            if ranked.fragment.source not in top_sources:
                top_sources.append(ranked.fragment.source)
        self.transcript.append(
            "[grow] "
            f"cycle={self._growth_cycle} seed={result.seed} chaos={result.chaos:.2f} "
            f"routes={routes}; retrieved={len(result.retrieved)}; groups={len(result.groups)}; "
            f"neural_rerank={'on' if result.neural_rerank_used else 'off'}. "
            f"Top local sources: {', '.join(top_sources) or 'none'}."
        )
        if result.groups:
            best = result.groups[0]
            self.transcript.append(
                "[grow] Best combination: "
                + " + ".join(best.fragment_ids)
                + f" (score={best.score:.3f}, novelty={best.novelty:.3f})."
            )
        self.transcript.append(
            "[grow] Context is ready for the next Ask. Nothing was promoted, trained, or written to verification state."
        )
        self.refresh()

    def _grow_failed(self, error: str) -> None:
        self.transcript.append(f"[system] Grow failed: {error}")
        self.refresh()

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

        self.prompt.clear()
        self.transcript.append(f"[you] {text}")
        self.history.append({"role": "user", "content": text})
        messages = [{"role": "system", "content": self._system_message()}]
        live_context = self._live_context()
        if live_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "READ-ONLY CURRENT EXPERIMENT CONTEXT. "
                        "Do not claim this is verification evidence and do not assume permission to mutate it.\n"
                        + live_context
                    ),
                }
            )
        if self._growth_context:
            messages.append({"role": "system", "content": self._growth_context})
        messages += self.history[-20:]
        self._growth_context = ""
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

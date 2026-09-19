from __future__ import annotations

import os
from pathlib import Path

try:
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
    from PySide6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - GUI-only module
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc

from cace_studio.ai import HybridLocalAI, LocalAIError, create_local_provider


_MODE_GUIDANCE = {
    "hints": "Give concise hints and questions; avoid doing the whole task unless explicitly asked.",
    "teacher": "Explain concepts step by step and distinguish assumptions from conclusions.",
    "researcher": "Help design rigorous scientific experiments and identify evidence limits and open obligations.",
    "autonomous": "Propose complete research workflows, but require user review before any repository or experiment mutation.",
}


def _default_ai_state_dir() -> Path:
    override = os.environ.get("CACE_AI_STATE_DIR")
    return Path(override).expanduser() if override else Path.home() / ".cace" / "ai"


class _WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class _PlanWorker(QRunnable):
    def __init__(self, engine: HybridLocalAI, text: str, generally_useful: bool) -> None:
        super().__init__()
        self.engine = engine
        self.text = text
        self.generally_useful = generally_useful
        self.signals = _WorkerSignals()

    def run(self) -> None:  # pragma: no cover - GUI integration
        try:
            suggestions = self.engine.suggest(
                self.text,
                generally_useful=self.generally_useful,
                top_k=8,
                max_group=9,
            )
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(suggestions)


class _HybridChatWorker(QRunnable):
    def __init__(
        self,
        engine: HybridLocalAI,
        provider,
        messages,
        text: str,
        generally_useful: bool,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.provider = provider
        self.messages = messages
        self.text = text
        self.generally_useful = generally_useful
        self.signals = _WorkerSignals()

    def run(self) -> None:  # pragma: no cover - GUI integration
        try:
            suggestions = self.engine.suggest(
                self.text,
                generally_useful=self.generally_useful,
                top_k=8,
                max_group=9,
            )
            planner_context = self.engine.prompt_context(
                suggestions,
                generally_useful=self.generally_useful,
            )
            messages = list(self.messages)
            if messages and messages[0].get("role") == "system":
                messages.insert(
                    1,
                    {
                        "role": "system",
                        "content": planner_context,
                    },
                )
            else:
                messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": planner_context,
                    },
                )
            answer = self.provider.chat(messages)
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(
                {
                    "answer": answer,
                    "suggestions": suggestions,
                }
            )


class LocalAIAssistantWidget(QWidget):
    """Optional local hybrid assistant panel with no verification privileges."""

    def __init__(self, settings, configure_callback, registry, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.configure_callback = configure_callback
        self.history: list[dict[str, str]] = []
        self.last_plan_task = ""
        self.last_suggestions = []
        self.pool = QThreadPool.globalInstance()
        self.hybrid = HybridLocalAI(
            registry,
            state_dir=_default_ai_state_dir(),
            sketch_dim=128,
            hidden_dim=32,
            seed=0,
        )

        self.status = QLabel()
        self.status.setWordWrap(True)
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText(
            "Local hybrid AI conversation. Assistant/planner output is never verification evidence."
        )

        self.prompt = QLineEdit()
        self.prompt.setPlaceholderText("Ask the local CACE assistant…")
        self.prompt.returnPressed.connect(self.send)

        self.send_button = QPushButton("Ask")
        self.send_button.clicked.connect(self.send)

        self.plan_button = QPushButton("Plan")
        self.plan_button.setToolTip(
            "Run the cheap local mathematical/neural combination planner without calling the LLM."
        )
        self.plan_button.clicked.connect(self.plan)

        self.general_button = QPushButton()
        self.general_button.setCheckable(True)
        self.general_button.setChecked(bool(self.settings.ai_generally_useful))
        self.general_button.setToolTip(
            "OFF: rank combinations for the current prompt. ON: rank broadly reusable combinations across CACE."
        )
        self.general_button.toggled.connect(self._toggle_generally_useful)

        self.useful_button = QPushButton("Top Suggestion Useful")
        self.useful_button.setToolTip(
            "Train the local ranker that the most recent top planner combination was useful."
        )
        self.useful_button.clicked.connect(lambda: self._record_top_feedback(1.0))

        self.not_useful_button = QPushButton("Top Suggestion Not Useful")
        self.not_useful_button.setToolTip(
            "Train the local ranker that the most recent top planner combination was not useful."
        )
        self.not_useful_button.clicked.connect(lambda: self._record_top_feedback(0.0))

        configure = QPushButton("Configure")
        configure.clicked.connect(self.configure_callback)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self.general_button)
        mode_row.addWidget(self.useful_button)
        mode_row.addWidget(self.not_useful_button)
        mode_row.addStretch()

        row = QHBoxLayout()
        row.addWidget(self.prompt)
        row.addWidget(self.plan_button)
        row.addWidget(self.send_button)
        row.addWidget(configure)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addLayout(mode_row)
        layout.addWidget(self.transcript)
        layout.addLayout(row)
        self.refresh()

    def refresh(self) -> None:
        general = bool(self.settings.ai_generally_useful)
        self.general_button.blockSignals(True)
        self.general_button.setChecked(general)
        self.general_button.setText(
            "Generally Useful: ON" if general else "Generally Useful: OFF"
        )
        self.general_button.blockSignals(False)

        if not self.settings.ai_enabled:
            self.status.setText(
                "AI is OFF. CACE execution and verification are unaffected."
            )
            self.send_button.setEnabled(False)
            self.plan_button.setEnabled(False)
            self.general_button.setEnabled(False)
            self.useful_button.setEnabled(False)
            self.not_useful_button.setEnabled(False)
            return

        model = self.settings.ai_model or "no model selected"
        planning_mode = "generally useful" if general else "task-focused"
        self.status.setText(
            f"AI ON — {self.settings.ai_provider} / {model} / "
            f"assistant={self.settings.assistant_mode} / planner={planning_mode}. "
            "AI output is not verification evidence."
        )
        self.general_button.setEnabled(True)
        self.plan_button.setEnabled(True)
        self.send_button.setEnabled(bool(self.settings.ai_model))
        have_feedback_target = bool(self.last_suggestions)
        self.useful_button.setEnabled(have_feedback_target)
        self.not_useful_button.setEnabled(have_feedback_target)

    def _toggle_generally_useful(self, checked: bool) -> None:
        self.settings.ai_generally_useful = bool(checked)
        self.settings.save()
        self.refresh()
        self.transcript.append(
            "[system] Planner switched to generally useful cross-workflow ranking."
            if checked
            else "[system] Planner switched to current-task-focused ranking."
        )

    def _record_top_feedback(self, target: float) -> None:
        if not self.last_suggestions:
            self.transcript.append("[system] No planner suggestion is available for feedback yet.")
            return
        suggestion = self.last_suggestions[0]
        try:
            loss = self.hybrid.record_feedback(
                task_text=self.last_plan_task,
                suggestion=suggestion,
                target=float(target),
                evidence_kind="experimental",
                measured_cost=0.0,
                metadata={
                    "source": "manual-ui-feedback",
                    "generally_useful": bool(self.settings.ai_generally_useful),
                },
            )
        except Exception as exc:
            self.transcript.append(
                f"[system] Could not record local planner feedback: {type(exc).__name__}: {exc}"
            )
            return
        label = "useful" if target >= 0.5 else "not useful"
        self.transcript.append(
            f"[learning] Recorded top combination as {label}; local ranker update loss={loss:.4f}."
        )

    def _system_message(self) -> str:
        guidance = _MODE_GUIDANCE.get(
            self.settings.assistant_mode,
            _MODE_GUIDANCE["researcher"],
        )
        planning_guidance = (
            "Prefer combinations with broad reuse across many CACE research/proof workflows, "
            "not merely relevance to the immediate question."
            if self.settings.ai_generally_useful
            else
            "Prefer combinations that directly address the current user task."
        )
        return (
            "You are the optional local assistant inside CACE Studio. "
            "Never describe your own output as mathematical proof, formal verification, "
            "a certificate, or executed evidence. Preserve explicit assumptions and distinguish "
            "numerical, symbolic, interval and formal evidence. "
            "Do not claim that simulations solve famous open problems. "
            "The cheap-math planner context is advisory ranking metadata, not proof. "
            + planning_guidance
            + " "
            + guidance
        )

    @staticmethod
    def _format_suggestions(suggestions) -> str:
        if not suggestions:
            return "No candidate combinations."
        lines = []
        for index, suggestion in enumerate(suggestions, start=1):
            lines.append(
                f"{index}. {' + '.join(suggestion.member_ids)} "
                f"[score={suggestion.score:.3f}, proof={suggestion.proof_strength:.2f}, "
                f"cost={suggestion.structural_cost:.2f}]"
            )
        return "\n".join(lines)

    def plan(self) -> None:
        if not self.settings.ai_enabled:
            self.transcript.append("[system] AI is disabled.")
            return
        text = self.prompt.text().strip()
        if not text:
            if self.settings.ai_generally_useful:
                text = "general reusable CACE mathematical, scientific, proof, and experiment tooling"
            else:
                self.transcript.append("[system] Enter a task to run task-focused planning.")
                return

        self.last_plan_task = text
        self.plan_button.setEnabled(False)
        self.send_button.setEnabled(False)
        self.status.setText("Cheap local planner is ranking 1–9+ combinations…")
        worker = _PlanWorker(
            self.hybrid,
            text,
            bool(self.settings.ai_generally_useful),
        )
        worker.signals.finished.connect(self._plan_finished)
        worker.signals.failed.connect(self._failed)
        self.pool.start(worker)

    def _plan_finished(self, suggestions) -> None:
        self.last_suggestions = list(suggestions)
        label = "generally useful" if self.settings.ai_generally_useful else "task-focused"
        self.transcript.append(
            f"[planner:{label}]\n{self._format_suggestions(suggestions)}"
        )
        self.refresh()

    def send(self) -> None:
        text = self.prompt.text().strip()
        if not text:
            return
        if not self.settings.ai_enabled:
            self.transcript.append("[system] AI is disabled.")
            return
        if not self.settings.ai_model:
            self.transcript.append(
                "[system] Choose a local model in Configure Local AI first, or use Plan without an LLM."
            )
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

        self.last_plan_task = text
        self.prompt.clear()
        self.transcript.append(f"[you] {text}")
        self.history.append({"role": "user", "content": text})
        messages = [
            {"role": "system", "content": self._system_message()}
        ] + self.history[-20:]

        worker = _HybridChatWorker(
            self.hybrid,
            provider,
            messages,
            text,
            bool(self.settings.ai_generally_useful),
        )
        worker.signals.finished.connect(self._finished)
        worker.signals.failed.connect(self._failed)
        self.send_button.setEnabled(False)
        self.plan_button.setEnabled(False)
        self.status.setText("Local hybrid AI is planning and generating…")
        self.pool.start(worker)

    def _finished(self, payload) -> None:
        text = str(payload["answer"])
        suggestions = payload.get("suggestions", ())
        self.last_suggestions = list(suggestions)
        self.history.append({"role": "assistant", "content": text})
        self.transcript.append(
            "[planner context]\n" + self._format_suggestions(suggestions)
        )
        self.transcript.append(f"[assistant] {text}")
        self.refresh()

    def _failed(self, error: str) -> None:
        self.transcript.append(f"[system] Local hybrid AI failed: {error}")
        self.refresh()

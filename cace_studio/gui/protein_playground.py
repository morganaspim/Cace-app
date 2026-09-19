from __future__ import annotations

try:
    from PySide6.QtWidgets import (
        QComboBox,
        QLabel,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc


class ProteinPlaygroundWidget(QWidget):
    """GUI bridge for read-only heartbeat analysis of protein run outputs."""

    def __init__(self, sources_callback, play_callback, parent=None) -> None:
        super().__init__(parent)
        self.sources_callback = sources_callback
        self.play_callback = play_callback
        self.notice = QLabel(
            "Protein Play analyzes an existing CACE protein-structure output. "
            "It does not reproduce AlphaFold, mutate the source structure, or create "
            "verification/clinical evidence."
        )
        self.notice.setWordWrap(True)

        self.sources = QComboBox()
        self.sources.currentIndexChanged.connect(self._selection_changed)

        self.refresh_button = QPushButton("Refresh Protein Outputs")
        self.refresh_button.clicked.connect(self.refresh_sources)
        self.play_button = QPushButton("▶ Play Selected Protein with Local AI")
        self.play_button.clicked.connect(self.play_selected)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(160)

        layout = QVBoxLayout(self)
        layout.addWidget(self.notice)
        layout.addWidget(self.sources)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.details)
        self.refresh_sources()

    def refresh_sources(self) -> None:
        current = self.sources.currentData()
        self.sources.blockSignals(True)
        self.sources.clear()
        try:
            values = tuple(self.sources_callback())
        except Exception as exc:
            values = ()
            self.details.setPlainText(
                f"Protein output discovery failed: {type(exc).__name__}: {exc}"
            )
        for node_id, view in values:
            mean = view.mean_confidence
            confidence = "n/a" if mean is None else f"{mean:.1f}"
            self.sources.addItem(
                f"{node_id} · {view.residue_count} residues · confidence {confidence}",
                node_id,
            )
        if current:
            index = self.sources.findData(current)
            if index >= 0:
                self.sources.setCurrentIndex(index)
        self.sources.blockSignals(False)
        self.play_button.setEnabled(self.sources.count() > 0)
        if self.sources.count() == 0:
            self.details.setPlainText(
                "No protein structure output is attached to the current run.\n\n"
                "After the molecular-science modules are installed, place an "
                "AlphaFold-Compatible PDB Import or protein fold-search node on the canvas, "
                "execute the graph, then refresh this panel."
            )
        else:
            if self.sources.currentIndex() < 0:
                self.sources.setCurrentIndex(0)
            self._selection_changed()

    def _selected(self):
        node_id = self.sources.currentData()
        if not node_id:
            return None
        for candidate_id, view in self.sources_callback():
            if candidate_id == node_id:
                return candidate_id, view
        return None

    def _selection_changed(self, *args) -> None:
        selected = self._selected()
        if selected is None:
            return
        node_id, view = selected
        mean = view.mean_confidence
        self.details.setPlainText(
            f"Canvas node: {node_id}\n"
            f"Residues: {view.residue_count}\n"
            f"Method: {view.method}\n"
            f"Source: {view.source}\n"
            f"License: {view.license_id}\n"
            f"Attribution: {view.attribution or 'none supplied'}\n"
            f"Mean imported confidence: {'n/a' if mean is None else f'{mean:.2f}'}\n"
            f"Semantic hash: {view.semantic_sha256}\n\n"
            "Play is read-only. Residue heartbeat attention is orchestration metadata only."
        )

    def play_selected(self) -> None:
        selected = self._selected()
        if selected is None:
            return
        node_id, view = selected
        try:
            accepted, step = self.play_callback(node_id)
        except Exception as exc:
            self.details.append(f"\nPlay failed: {type(exc).__name__}: {exc}")
            return
        self.details.append(
            f"\nProtein Play cycle {step.cycle}\n"
            + "\n".join(f"- {reason}" for reason in step.focus_reasons)
        )
        self.details.append(
            "\nContext sent to the configured local AI."
            if accepted
            else "\nHeartbeat analysis completed locally; enable/configure Local AI for model analysis."
        )

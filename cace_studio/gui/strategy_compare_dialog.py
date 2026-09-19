from __future__ import annotations

try:
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
    from PySide6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
    )
except ImportError as exc:  # pragma: no cover - GUI-only module
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc

from cace_studio.ai.strategy_compare import (
    StrategyComparison,
    compare_proposal_strategies,
)


class _CompareSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class StrategyCompareWorker(QRunnable):
    def __init__(self, registry, proposals, *, seed: int, gpu_enabled: bool) -> None:
        super().__init__()
        self.registry = registry
        self.proposals = proposals
        self.seed = int(seed)
        self.gpu_enabled = bool(gpu_enabled)
        self.signals = _CompareSignals()

    def run(self) -> None:  # pragma: no cover - exercised through GUI integration
        try:
            comparison = compare_proposal_strategies(
                self.registry,
                self.proposals,
                seed=self.seed,
                gpu_enabled=self.gpu_enabled,
            )
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(comparison)


class StrategyComparisonDialog(QDialog):
    """Neutral side-by-side strategy run summary.

    No winner is selected automatically. The user may choose a row merely to
    return that strategy to the proposal preview for further inspection.
    """

    def __init__(self, comparison: StrategyComparison, parent=None) -> None:
        super().__init__(parent)
        self.comparison = comparison
        self.inspect_strategy: str | None = None
        self.setWindowTitle("Compare Proposal Strategy Results")
        self.resize(1080, 680)

        header = QLabel(
            f"Same seed for all runnable strategies: {comparison.seed}. "
            f"GPU policy: {'ON' if comparison.gpu_enabled else 'OFF'}. "
            "Runtime is one local wall-clock sample and is not a benchmark verdict."
        )
        header.setWordWrap(True)

        trust = QLabel(
            "Comparison is descriptive only: no strategy is automatically ranked, "
            "kept, promoted, or built. Verification records retain their original meaning."
        )
        trust.setWordWrap(True)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                "Strategy",
                "Runnable",
                "Completed",
                "Nodes",
                "Edges",
                "Unresolved",
                "Runtime (s)",
                "PASS",
                "FAIL",
                "NOT RUN",
                "Novelty",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._selection_changed)

        for summary in comparison.summaries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                summary.strategy.title(),
                "yes" if summary.runnable else "no",
                "yes" if summary.completed else "no",
                str(summary.node_count),
                str(summary.edge_count),
                str(summary.unresolved_required_inputs),
                (
                    f"{summary.runtime_seconds:.6f}"
                    if summary.runtime_seconds is not None
                    else "—"
                ),
                str(summary.verifier_pass),
                str(summary.verifier_fail),
                str(summary.verifier_not_run),
                f"{summary.novelty_fraction:.3f}",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(256, summary.strategy)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

        self.details = QTextEdit()
        self.details.setReadOnly(True)

        self.inspect_button = QPushButton("Inspect Selected in Proposal Preview")
        self.inspect_button.setEnabled(False)
        self.inspect_button.clicked.connect(self._inspect_selected)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)

        actions = QHBoxLayout()
        actions.addWidget(self.inspect_button)
        actions.addStretch()
        actions.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(header)
        layout.addWidget(trust)
        layout.addWidget(self.table)
        layout.addWidget(self.details)
        layout.addLayout(actions)

        if self.table.rowCount():
            self.table.selectRow(0)

    def _selected_summary(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        strategy = str(self.table.item(rows[0].row(), 0).data(256))
        return next(
            (
                summary
                for summary in self.comparison.summaries
                if summary.strategy == strategy
            ),
            None,
        )

    def _selection_changed(self) -> None:
        summary = self._selected_summary()
        self.inspect_button.setEnabled(summary is not None)
        if summary is None:
            self.details.clear()
            return

        lines = [
            f"Strategy: {summary.strategy.title()}",
            f"Runnable: {summary.runnable}",
            f"Run attempted: {summary.run_attempted}",
            f"Completed: {summary.completed}",
            f"Seed: {summary.seed}",
            f"Nodes completed: {summary.completed_node_count}/{summary.node_count}",
            (
                f"Runtime: {summary.runtime_seconds:.6f} s"
                if summary.runtime_seconds is not None
                else "Runtime: not run"
            ),
            (
                "Verification records: "
                f"PASS={summary.verifier_pass}, FAIL={summary.verifier_fail}, "
                f"NOT-RUN={summary.verifier_not_run}, total={summary.verifier_record_count}"
            ),
            f"all_verifiers_passed property: {summary.all_verifiers_passed}",
            f"Novel modules: {', '.join(summary.novel_modules) or 'none'}",
            f"Novelty fraction: {summary.novelty_fraction:.3f}",
        ]
        if summary.skipped_modules:
            lines.append(
                "Skipped modules: " + ", ".join(summary.skipped_modules)
            )
        if summary.error:
            lines.append("Error / not-runnable reason: " + summary.error)
        if summary.semantic_experiment_sha256:
            lines.append(
                "Semantic graph SHA-256: " + summary.semantic_experiment_sha256
            )
        if summary.full_experiment_sha256:
            lines.append(
                "Full graph SHA-256: " + summary.full_experiment_sha256
            )

        lines.append("")
        lines.append("Output summaries:")
        if summary.output_summaries:
            for output in summary.output_summaries:
                lines.extend(
                    [
                        f"- {output.module_id} ({output.node_id})",
                        f"  output hash: {output.output_hash}",
                        f"  fields: {', '.join(output.fields) or 'none'}",
                        f"  {output.summary}",
                    ]
                )
        else:
            lines.append("- none")

        self.details.setPlainText("\n".join(lines))

    def _inspect_selected(self) -> None:
        summary = self._selected_summary()
        if summary is None:
            return
        self.inspect_strategy = summary.strategy
        self.accept()

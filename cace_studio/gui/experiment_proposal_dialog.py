from __future__ import annotations

try:
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QPen
    from PySide6.QtWidgets import (
        QComboBox,
        QDialog,
        QGraphicsRectItem,
        QGraphicsScene,
        QGraphicsSimpleTextItem,
        QGraphicsView,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
    )
except ImportError as exc:  # pragma: no cover - GUI-only module
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc

from cace_studio.ai.experiment_proposal import (
    PROPOSAL_STRATEGIES,
    ExperimentGraphProposal,
    ProposalStrategy,
)


_STRATEGY_LABELS = {
    "minimal": "Minimal — lowest compute",
    "balanced": "Balanced — best connected",
    "exploratory": "Exploratory — bounded novelty",
}


class ExperimentProposalDialog(QDialog):
    """Read-only multi-strategy preview. No canvas mutation happens here."""

    def __init__(
        self,
        proposals: dict[ProposalStrategy, ExperimentGraphProposal],
        parent=None,
        *,
        initial_strategy: ProposalStrategy = "balanced",
    ) -> None:
        super().__init__(parent)
        self.proposals = {
            strategy: proposals[strategy]
            for strategy in PROPOSAL_STRATEGIES
            if strategy in proposals
        }
        if not self.proposals:
            raise ValueError("proposal dialog requires at least one strategy")
        if initial_strategy not in self.proposals:
            initial_strategy = next(iter(self.proposals))
        self._selected_strategy: ProposalStrategy = initial_strategy

        self.setWindowTitle("Proposed Experiment — Choose Strategy Before Building")
        self.resize(980, 700)

        self.strategy = QComboBox()
        for strategy in PROPOSAL_STRATEGIES:
            if strategy in self.proposals:
                self.strategy.addItem(_STRATEGY_LABELS[strategy], strategy)
        initial_index = self.strategy.findData(initial_strategy)
        self.strategy.setCurrentIndex(max(0, initial_index))
        self.strategy.currentIndexChanged.connect(self._strategy_changed)

        self.comparison = QLabel()
        self.comparison.setWordWrap(True)

        self.status = QLabel()
        self.status.setWordWrap(True)

        trust = QLabel(
            "Preview only — switching strategies and opening this dialog do not mutate "
            "the experiment. Only Approve & Build installs the currently selected graph."
        )
        trust.setWordWrap(True)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setMinimumHeight(350)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(190)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.approve = QPushButton("Approve & Build")
        self.approve.clicked.connect(self.accept)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(cancel)
        actions.addWidget(self.approve)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose a proposal strategy:"))
        layout.addWidget(self.strategy)
        layout.addWidget(self.comparison)
        layout.addWidget(self.status)
        layout.addWidget(trust)
        layout.addWidget(self.view)
        layout.addWidget(self.details)
        layout.addLayout(actions)

        self._refresh_strategy()

    @property
    def selected_strategy(self) -> ProposalStrategy:
        return self._selected_strategy

    @property
    def selected_proposal(self) -> ExperimentGraphProposal:
        return self.proposals[self._selected_strategy]

    def _strategy_changed(self, _index: int = -1) -> None:
        strategy = str(self.strategy.currentData())
        if strategy in self.proposals:
            self._selected_strategy = strategy  # type: ignore[assignment]
        self._refresh_strategy()

    def _refresh_strategy(self) -> None:
        proposal = self.selected_proposal
        self.comparison.setText(self._comparison_text())
        self.status.setText(self._status_text(proposal))
        self.approve.setText(
            "Approve Partial & Build"
            if proposal.unresolved_required_inputs
            else "Approve & Build"
        )
        self.approve.setEnabled(not proposal.is_empty)
        self._draw_proposal(proposal)
        self.details.setPlainText(self._details_text(proposal))

    def _comparison_text(self) -> str:
        parts = []
        for strategy in PROPOSAL_STRATEGIES:
            proposal = self.proposals.get(strategy)
            if proposal is None:
                continue
            readiness = "ready" if proposal.is_execution_ready else (
                "empty" if proposal.is_empty else "partial"
            )
            parts.append(
                f"{strategy.title()}: {len(proposal.nodes)} nodes · "
                f"{len(proposal.edges)} edges · "
                f"{len(proposal.unresolved_required_inputs)} unresolved · {readiness}"
            )
        return "   |   ".join(parts)

    @staticmethod
    def _status_text(proposal: ExperimentGraphProposal) -> str:
        if proposal.is_empty:
            return (
                f"{proposal.strategy.title()} proposal has no valid registered modules available."
            )
        if proposal.is_execution_ready:
            return (
                f"{proposal.strategy.title()} proposal is execution-ready: all required inputs "
                "were satisfied by exact compatible type/unit connections."
            )
        return (
            f"{proposal.strategy.title()} proposal is partial: "
            f"{len(proposal.unresolved_required_inputs)} required input(s) remain unresolved. "
            "You may still build it and complete the graph manually."
        )

    def _draw_proposal(self, proposal: ExperimentGraphProposal) -> None:
        self.scene.clear()
        node_items = {}
        for node in proposal.nodes:
            x, y = node.position
            rect = QGraphicsRectItem(x, y, 190, 92)
            rect.setPen(QPen(self.palette().text().color(), 1.5))
            self.scene.addItem(rect)
            title = QGraphicsSimpleTextItem(node.name)
            title.setPos(x + 8, y + 10)
            self.scene.addItem(title)
            meta = QGraphicsSimpleTextItem(f"{node.proposal_id} · {node.category}")
            meta.setPos(x + 8, y + 34)
            self.scene.addItem(meta)
            module_id = QGraphicsSimpleTextItem(node.module_id)
            module_id.setPos(x + 8, y + 56)
            self.scene.addItem(module_id)
            node_items[node.proposal_id] = rect

        for edge in proposal.edges:
            source = node_items.get(edge.source_node)
            target = node_items.get(edge.target_node)
            if source is None or target is None:
                continue
            a = source.sceneBoundingRect()
            b = target.sceneBoundingRect()
            self.scene.addLine(
                a.right(),
                a.center().y(),
                b.left(),
                b.center().y(),
                QPen(self.palette().highlight().color(), 2),
            )

        rect = self.scene.itemsBoundingRect()
        if rect.isNull():
            rect = QRectF(0, 0, 600, 320)
        self.scene.setSceneRect(rect.adjusted(-30, -30, 30, 30))
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    @staticmethod
    def _details_text(proposal: ExperimentGraphProposal) -> str:
        lines = [
            f"Strategy: {_STRATEGY_LABELS[proposal.strategy]}",
            proposal.rationale,
            "",
        ]
        if proposal.description:
            lines.append("Proposed experiment:")
            lines.append("  " + proposal.description.replace("\n", "\n  "))
            lines.append("")

        lines.append(f"Nodes ({len(proposal.nodes)}):")
        for node in proposal.nodes:
            lines.append(f"  {node.proposal_id}: {node.module_id} ({node.name})")

        lines.append("")
        lines.append(f"Compatible edges ({len(proposal.edges)}):")
        if proposal.edges:
            for edge in proposal.edges:
                lines.append(
                    f"  {edge.source_node}.{edge.source_port} -> "
                    f"{edge.target_node}.{edge.target_port}"
                )
        else:
            lines.append("  none")

        lines.append("")
        lines.append(
            f"Unresolved required inputs ({len(proposal.unresolved_required_inputs)}):"
        )
        if proposal.unresolved_required_inputs:
            for item in proposal.unresolved_required_inputs:
                unit = item.unit if item.unit is not None else "<unspecified>"
                lines.append(
                    f"  {item.node_id}.{item.port_name}: "
                    f"type={item.type_name}, unit={unit}"
                )
        else:
            lines.append("  none")

        if proposal.skipped_modules:
            lines.append("")
            lines.append("Skipped unknown modules:")
            lines.extend(f"  {module_id}" for module_id in proposal.skipped_modules)

        return "\n".join(lines)

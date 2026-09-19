from __future__ import annotations

try:
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QPen
    from PySide6.QtWidgets import (
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

from cace_studio.ai.experiment_proposal import ExperimentGraphProposal


class ExperimentProposalDialog(QDialog):
    """Read-only proposal preview. No canvas mutation happens in this dialog."""

    def __init__(self, proposal: ExperimentGraphProposal, parent=None) -> None:
        super().__init__(parent)
        self.proposal = proposal
        self.setWindowTitle("Proposed Experiment — Review Before Building")
        self.resize(900, 640)

        status = QLabel()
        status.setWordWrap(True)
        if proposal.is_empty:
            status.setText("No valid registered modules are available to build.")
        elif proposal.is_execution_ready:
            status.setText(
                "Execution-ready proposal: all required inputs were satisfied by "
                "exact compatible type/unit connections."
            )
        else:
            status.setText(
                f"Partial proposal: {len(proposal.unresolved_required_inputs)} required "
                "input(s) remain unresolved. You may still build it and complete the graph manually."
            )

        trust = QLabel(
            "Preview only — opening this dialog does not mutate the experiment. "
            "Only Approve & Build changes the canvas."
        )
        trust.setWordWrap(True)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setMinimumHeight(340)
        self._draw_proposal()

        details = QTextEdit()
        details.setReadOnly(True)
        details.setMaximumHeight(170)
        details.setPlainText(self._details_text())

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        approve = QPushButton(
            "Approve Partial & Build" if proposal.unresolved_required_inputs else "Approve & Build"
        )
        approve.setEnabled(not proposal.is_empty)
        approve.clicked.connect(self.accept)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(cancel)
        actions.addWidget(approve)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Research Idea proposal: {proposal.title}"))
        layout.addWidget(status)
        layout.addWidget(trust)
        layout.addWidget(self.view)
        layout.addWidget(details)
        layout.addLayout(actions)

    def _draw_proposal(self) -> None:
        self.scene.clear()
        node_items = {}
        for node in self.proposal.nodes:
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

        for edge in self.proposal.edges:
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

    def _details_text(self) -> str:
        lines = [self.proposal.rationale, ""]
        lines.append(f"Nodes ({len(self.proposal.nodes)}):")
        for node in self.proposal.nodes:
            lines.append(f"  {node.proposal_id}: {node.module_id} ({node.name})")

        lines.append("")
        lines.append(f"Compatible edges ({len(self.proposal.edges)}):")
        if self.proposal.edges:
            for edge in self.proposal.edges:
                lines.append(
                    f"  {edge.source_node}.{edge.source_port} -> "
                    f"{edge.target_node}.{edge.target_port}"
                )
        else:
            lines.append("  none")

        lines.append("")
        lines.append(
            f"Unresolved required inputs ({len(self.proposal.unresolved_required_inputs)}):"
        )
        if self.proposal.unresolved_required_inputs:
            for item in self.proposal.unresolved_required_inputs:
                unit = item.unit if item.unit is not None else "<unspecified>"
                lines.append(
                    f"  {item.node_id}.{item.port_name}: "
                    f"type={item.type_name}, unit={unit}"
                )
        else:
            lines.append("  none")

        if self.proposal.skipped_modules:
            lines.append("")
            lines.append("Skipped unknown modules:")
            lines.extend(f"  {module_id}" for module_id in self.proposal.skipped_modules)

        return "\n".join(lines)

from __future__ import annotations

try:
    from PySide6.QtWidgets import (
        QLabel,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - GUI-only module
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc

from cace_studio.core.proof_explorer import ProofClaimView, ProofExplorer


class ProofExplorerWidget(QWidget):
    """Read-only view of canonical qualification and runtime proof evidence."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.explorer = ProofExplorer()
        self.title = QLabel(
            "Canonical claim status. Declared capability, release qualification, "
            "and runtime evidence are independent."
        )
        self.title.setWordWrap(True)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Claim / evidence", "Status"])
        self.tree.setAlternatingRowColors(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.tree)
        self.show_all_claims()

    @staticmethod
    def _child(parent: QTreeWidgetItem, label: str, value: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([label, value])
        parent.addChild(item)
        return item

    def _append_claim(self, view: ProofClaimView) -> QTreeWidgetItem:
        root = QTreeWidgetItem([view.claim_id, view.qualification_state])
        self.tree.addTopLevelItem(root)
        self._child(root, "Statement", view.statement)
        self._child(root, "Scope", view.scope)
        self._child(root, "Declared evidence ceiling", view.evidence_ceiling)
        self._child(root, "Registry status", view.registry_status)
        self._child(root, "Ledger release", view.ledger_release or "none")
        self._child(root, "Ledger status", view.ledger_status or "none")
        self._child(
            root,
            "Current-head qualified",
            "YES" if view.current_head_qualified else "NO",
        )
        self._child(root, "Attested commit", view.attested_commit or "none")
        self._child(root, "Proof artifact SHA-256", view.proof_artifact_sha256 or "none")
        self._child(
            root,
            "Workflow run",
            str(view.workflow_run_id) if view.workflow_run_id is not None else "none",
        )

        checks = self._child(root, "Qualification checks", str(len(view.checks)))
        for check in view.checks:
            self._child(checks, "check", check)

        blockers = self._child(root, "Blockers / reasons", str(len(view.blockers)))
        for blocker in view.blockers:
            self._child(blockers, "blocker", blocker)

        nonclaims = self._child(root, "Explicit nonclaims", str(len(view.nonclaims)))
        for nonclaim in view.nonclaims:
            self._child(nonclaims, "nonclaim", nonclaim)

        runtime = self._child(root, "Runtime verification records", str(len(view.runtime_evidence)))
        for record in view.runtime_evidence:
            evidence = self._child(
                runtime,
                f"{record.kind}: {record.verifier}",
                record.state.upper(),
            )
            self._child(evidence, "Claim text", record.claim)
            self._child(evidence, "Method", record.method)
            self._child(evidence, "Record SHA-256", record.artifact_sha256)
            self._child(
                evidence,
                "Canonical claim_id binding",
                "YES" if record.canonical_claim_bound else "NO",
            )
        return root

    def show_all_claims(self) -> None:
        self.tree.clear()
        for view in self.explorer.all_claims():
            self._append_claim(view)
        self.tree.expandToDepth(0)

    def show_module(
        self,
        module_id: str,
        *,
        formal_artifact: str | None = None,
        runtime_records=(),
    ) -> None:
        self.tree.clear()
        view = self.explorer.for_module(
            module_id,
            formal_artifact=formal_artifact,
            runtime_records=runtime_records,
        )
        if view is None:
            root = QTreeWidgetItem([module_id, "NO CANONICAL CLAIM"])
            self.tree.addTopLevelItem(root)
            self._child(
                root,
                "Status",
                "Module has no claim binding in the canonical registry.",
            )
            return
        root = self._append_claim(view)
        root.setExpanded(True)

from __future__ import annotations

from PySide6.QtCore import Qt

from .main_window import MainWindow
from .proof_explorer import ProofExplorerWidget


class StudioMainWindow(MainWindow):
    """CACE Studio shell with canonical Proof Explorer integration.

    The explorer is strictly read-only. It mirrors canonical claim/ledger state
    plus runtime verification records; it cannot promote evidence or mutate the
    proof ledger.
    """

    def __init__(self, registry, settings):
        super().__init__(registry, settings)
        self.proof_explorer = ProofExplorerWidget(self)
        self.proof_explorer_dock = self._dock(
            "Proof Explorer",
            self.proof_explorer,
            Qt.RightDockWidgetArea,
        )
        self.proof_explorer.show_all_claims()

    def _selected_module_context(self):
        if not self.selected_node_id:
            return None
        node = next(
            (item for item in self.experiment.nodes if item.id == self.selected_node_id),
            None,
        )
        if node is None:
            return None
        module = self.registry.create(node.module_id)
        return node, module

    def _refresh_proof_explorer(self) -> None:
        if not hasattr(self, "proof_explorer"):
            return
        context = self._selected_module_context()
        if context is None:
            self.proof_explorer.show_all_claims()
            return
        node, module = context
        records = ()
        if self.last_result is not None:
            records = tuple(self.last_result.verification.get(node.id, ()))
        self.proof_explorer.show_module(
            node.module_id,
            formal_artifact=module.proof_status.formal_artifact,
            runtime_records=records,
        )

    def _show_node_verification(self, node_id):
        super()._show_node_verification(node_id)
        self._refresh_proof_explorer()

    def _invalidate_run_evidence(self, reason: str):
        super()._invalidate_run_evidence(reason)
        self._refresh_proof_explorer()

    def new_file(self):
        super().new_file()
        self._refresh_proof_explorer()

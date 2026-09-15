from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

from cace_studio.core.graph_edit import (
    GraphFragment,
    align_node_positions,
    copy_graph_fragment,
    paste_graph_fragment,
)

from .main_window import MainWindow
from .proof_explorer import ProofExplorerWidget


class StudioMainWindow(MainWindow):
    """CACE Studio shell with Proof Explorer and production graph-edit tools.

    Proof Explorer is strictly read-only. It mirrors canonical claim/ledger state
    plus runtime verification records; it cannot promote evidence or mutate the
    proof ledger.

    Copy/paste is an internal CACE graph-fragment clipboard rather than an OS
    text clipboard. Graph edits flow through the existing history/autosave and
    stale-evidence invalidation mechanisms.
    """

    def __init__(self, registry, settings):
        super().__init__(registry, settings)
        self._graph_clipboard: GraphFragment | None = None
        self._paste_generation = 0
        self._install_graph_edit_actions()

        self.proof_explorer = ProofExplorerWidget(self)
        self.proof_explorer_dock = self._dock(
            "Proof Explorer",
            self.proof_explorer,
            Qt.RightDockWidgetArea,
        )
        self.proof_explorer.show_all_claims()

    def _menu_named(self, title: str):
        target = title.replace("&", "")
        for action in self.menuBar().actions():
            if action.text().replace("&", "") == target:
                return action.menu()
        return None

    def _install_graph_edit_actions(self) -> None:
        edit_menu = self._menu_named("Edit")
        if edit_menu is not None:
            edit_menu.addSeparator()
            self._action(edit_menu, "Copy Selection", self.copy_selection, QKeySequence.Copy)
            self._action(edit_menu, "Paste", self.paste_selection, QKeySequence.Paste)

        arrange_menu = self.menuBar().addMenu("Arrange")
        self._action(
            arrange_menu,
            "Align Left",
            lambda: self._align_selection(axis="x", strategy="min", label="left"),
        )
        self._action(
            arrange_menu,
            "Align Top",
            lambda: self._align_selection(axis="y", strategy="min", label="top"),
        )
        self._action(
            arrange_menu,
            "Align Vertical Column",
            lambda: self._align_selection(axis="x", strategy="mean", label="vertical column"),
        )
        self._action(
            arrange_menu,
            "Align Horizontal Row",
            lambda: self._align_selection(axis="y", strategy="mean", label="horizontal row"),
        )

    def _reselect_nodes(self, node_ids) -> None:
        selected = set(node_ids)
        self.scene.clearSelection()
        for item in self.scene.items():
            if getattr(item, "node_id", None) in selected:
                item.setSelected(True)

    def copy_selection(self) -> None:
        self._sync_positions()
        selected = self.canvas.selected_node_ids()
        if not selected:
            self.console.append("Copy selection: no nodes selected.")
            return
        try:
            self._graph_clipboard = copy_graph_fragment(self.experiment, selected)
        except Exception as exc:
            self.console.append(f"Copy selection failed: {type(exc).__name__}: {exc}")
            return
        self._paste_generation = 0
        edge_count = len(self._graph_clipboard.edges)
        self.console.append(
            f"Copied {len(self._graph_clipboard.nodes)} node(s) and {edge_count} internal edge(s)."
        )

    def paste_selection(self) -> None:
        if self._graph_clipboard is None:
            self.console.append("Paste: graph clipboard is empty.")
            return

        self._record_history()
        self._paste_generation += 1
        offset = (30.0 * self._paste_generation, 30.0 * self._paste_generation)
        try:
            new_ids = paste_graph_fragment(
                self.experiment,
                self._graph_clipboard,
                offset=offset,
            )
            self._restore_experiment(
                self.experiment,
                log_message=f"Pasted {len(new_ids)} node(s).",
            )
            self._reselect_nodes(new_ids)
            self._sync_history_actions()
            self._autosave_tick()
        except Exception as exc:
            # The core paste helper validates before mutation; restoration is not
            # necessary for its validation failures. Keep the prior history entry
            # so the user can still undo if a future visual restore path fails.
            self.console.append(f"Paste failed: {type(exc).__name__}: {exc}")

    def _align_selection(self, *, axis: str, strategy: str, label: str) -> None:
        selected = self.canvas.selected_node_ids()
        if len(selected) < 2:
            self.console.append(f"Align {label}: select at least two nodes.")
            return
        self._record_history()
        try:
            align_node_positions(
                self.experiment,
                selected,
                axis=axis,
                strategy=strategy,
            )
            self._restore_experiment(
                self.experiment,
                log_message=f"Aligned {len(selected)} node(s): {label}.",
            )
            self._reselect_nodes(selected)
            self._sync_history_actions()
            self._autosave_tick()
        except Exception as exc:
            self.console.append(f"Align {label} failed: {type(exc).__name__}: {exc}")

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
        self._graph_clipboard = None
        self._paste_generation = 0
        self._refresh_proof_explorer()

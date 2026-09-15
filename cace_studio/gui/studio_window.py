from __future__ import annotations

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QKeySequence

from cace_studio.core.execution_control import ExecutionControl
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph_edit import (
    GraphFragment,
    align_node_positions,
    copy_graph_fragment,
    paste_graph_fragment,
)
from cace_studio.core.reproducibility import experiment_fingerprint

from .execution_worker import ExecutionWorker
from .main_window import MainWindow
from .proof_explorer import ProofExplorerWidget


class StudioMainWindow(MainWindow):
    """CACE Studio shell with Proof Explorer and production graph-edit tools.

    Proof Explorer is strictly read-only. It mirrors canonical claim/ledger state
    plus runtime verification records; it cannot promote evidence or mutate the
    proof ledger.

    Execution runs against an immutable experiment snapshot in a worker thread.
    Pause/cancel are cooperative at module boundaries; arbitrary scientific
    modules are never forcefully interrupted inside their execute method.
    """

    def __init__(self, registry, settings):
        super().__init__(registry, settings)
        self._graph_clipboard: GraphFragment | None = None
        self._paste_generation = 0

        self._execution_pool = QThreadPool.globalInstance()
        self._execution_control: ExecutionControl | None = None
        self._execution_worker: ExecutionWorker | None = None

        self._install_graph_edit_actions()
        self._install_scoped_run_action()

        self.proof_explorer = ProofExplorerWidget(self)
        self.proof_explorer_dock = self._dock(
            "Proof Explorer",
            self.proof_explorer,
            Qt.RightDockWidgetArea,
        )
        self.proof_explorer.show_all_claims()
        self._sync_execution_actions()

    def _menu_named(self, title: str):
        target = title.replace("&", "")
        for action in self.menuBar().actions():
            if action.text().replace("&", "") == target:
                return action.menu()
        return None

    def _run_action_named(self, title: str):
        menu = self._menu_named("Run")
        if menu is None:
            return None
        target = title.replace("&", "")
        for action in menu.actions():
            if action.text().replace("&", "") == target:
                return action
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

    def _install_scoped_run_action(self) -> None:
        run_menu = self._menu_named("Run")
        if run_menu is None:
            return
        run_menu.addSeparator()
        self.selected_run_action = self._action(
            run_menu,
            "Execute + Verify Selected + Upstream",
            self.run_selected_upstream,
            "Ctrl+Shift+R",
        )
        run_menu.addSeparator()
        self.pause_run_action = self._action(
            run_menu,
            "Pause Active Run",
            self.pause_execution,
        )
        self.resume_run_action = self._action(
            run_menu,
            "Resume Active Run",
            self.resume_execution,
        )
        self.cancel_run_action = self._action(
            run_menu,
            "Cancel Active Run",
            self.cancel_execution,
        )

    def _sync_execution_actions(self) -> None:
        if not hasattr(self, "pause_run_action"):
            return
        active = self._execution_control is not None
        paused = bool(active and self._execution_control.paused)
        cancelled = bool(active and self._execution_control.cancelled)
        full_action = self._run_action_named("Execute + Verify Graph")
        if full_action is not None:
            full_action.setEnabled(not active)
        self.selected_run_action.setEnabled(not active)
        self.pause_run_action.setEnabled(active and not paused and not cancelled)
        self.resume_run_action.setEnabled(active and paused and not cancelled)
        self.cancel_run_action.setEnabled(active and not cancelled)

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

        self._sync_positions()
        before = self.history.snapshot(self.experiment)
        trial = self.history.snapshot(self.experiment)
        next_generation = self._paste_generation + 1
        offset = (30.0 * next_generation, 30.0 * next_generation)
        try:
            new_ids = paste_graph_fragment(
                trial,
                self._graph_clipboard,
                offset=offset,
            )
        except Exception as exc:
            self.console.append(f"Paste failed before mutation: {type(exc).__name__}: {exc}")
            return

        self._record_history(sync_positions=False)
        try:
            self._restore_experiment(
                trial,
                log_message=f"Pasted {len(new_ids)} node(s).",
            )
        except Exception as exc:
            try:
                self._restore_experiment(before, log_message="Paste rolled back after restore failure.")
            except Exception as rollback_exc:
                self.console.append(
                    f"Paste rollback failed: {type(rollback_exc).__name__}: {rollback_exc}"
                )
            self.console.append(f"Paste failed: {type(exc).__name__}: {exc}")
            return

        self._paste_generation = next_generation
        self._reselect_nodes(new_ids)
        self._sync_history_actions()
        self._autosave_tick()

    def _align_selection(self, *, axis: str, strategy: str, label: str) -> None:
        selected = self.canvas.selected_node_ids()
        if len(selected) < 2:
            self.console.append(f"Align {label}: select at least two nodes.")
            return

        self._sync_positions()
        before = self.history.snapshot(self.experiment)
        trial = self.history.snapshot(self.experiment)
        try:
            align_node_positions(
                trial,
                selected,
                axis=axis,
                strategy=strategy,
            )
        except Exception as exc:
            self.console.append(f"Align {label} failed before mutation: {type(exc).__name__}: {exc}")
            return

        self._record_history(sync_positions=False)
        try:
            self._restore_experiment(
                trial,
                log_message=f"Aligned {len(selected)} node(s): {label}.",
            )
        except Exception as exc:
            try:
                self._restore_experiment(before, log_message=f"Align {label} rolled back.")
            except Exception as rollback_exc:
                self.console.append(
                    f"Align rollback failed: {type(rollback_exc).__name__}: {rollback_exc}"
                )
            self.console.append(f"Align {label} failed: {type(exc).__name__}: {exc}")
            return

        self._reselect_nodes(selected)
        self._sync_history_actions()
        self._autosave_tick()

    def run_graph(self) -> None:
        self._start_execution("full", ())

    def run_selected_upstream(self) -> None:
        selected = tuple(sorted(self.canvas.selected_node_ids()))
        if not selected:
            self.console.append("Selected + Upstream run: select at least one target node.")
            return
        self._start_execution("selected-upstream", selected)

    def _start_execution(self, scope_kind: str, targets: tuple[str, ...]) -> None:
        if self._execution_control is not None:
            self.console.append("A graph execution is already active.")
            return

        self._sync_positions()
        snapshot = self.history.snapshot(self.experiment)
        control = ExecutionControl()
        executor = GraphExecutor(self.registry, gpu_enabled=self.settings.gpu_enabled)

        if scope_kind == "full":
            execute = lambda: executor.run(snapshot, control=control)
        elif scope_kind == "selected-upstream":
            execute = lambda: executor.run_selected_upstream(
                snapshot,
                targets,
                control=control,
            )
        else:
            self.console.append(f"Unknown execution scope: {scope_kind}")
            return

        # A newly started execution invalidates any previously attached runtime
        # evidence immediately. The new result is attached only if its source
        # semantic graph still matches when the worker finishes.
        self.last_result = None
        self.verification.setPlainText(
            "Execution active. No current run evidence is attached until this run finishes."
        )
        self._refresh_proof_explorer()

        worker = ExecutionWorker(execute)
        worker.signals.finished.connect(self._execution_finished)
        worker.signals.failed.connect(self._execution_failed)
        self._execution_control = control
        self._execution_worker = worker
        self._sync_execution_actions()
        if targets:
            self.console.append(
                f"Execution started: scope={scope_kind}, targets={targets}. "
                "Pause/cancel take effect at module boundaries."
            )
        else:
            self.console.append(
                "Execution started: scope=full. Pause/cancel take effect at module boundaries."
            )
        self._execution_pool.start(worker)

    def pause_execution(self) -> None:
        if self._execution_control is None:
            self.console.append("Pause: no active run.")
            return
        if self._execution_control.pause():
            self.console.append("Pause requested; it takes effect at the next module boundary.")
        self._sync_execution_actions()

    def resume_execution(self) -> None:
        if self._execution_control is None:
            self.console.append("Resume: no active run.")
            return
        if self._execution_control.resume():
            self.console.append("Execution resumed.")
        self._sync_execution_actions()

    def cancel_execution(self) -> None:
        if self._execution_control is None:
            self.console.append("Cancel: no active run.")
            return
        if self._execution_control.cancel():
            self.console.append("Cancellation requested; it takes effect at the next module boundary.")
        self._sync_execution_actions()

    def _execution_finished(self, result) -> None:
        try:
            self._sync_positions()
            current_semantic = experiment_fingerprint(self.experiment, include_layout=False)
            source_matches = current_semantic == result.source_semantic_experiment_sha256

            if not source_matches:
                self.verification.setPlainText(
                    "Run finished for an earlier semantic graph snapshot and was not attached."
                )
                self.console.append(
                    f"Run {result.run_id} finished for an earlier graph snapshot and was not "
                    "attached because the semantic graph changed during execution."
                )
                return

            self.last_result = result
            if not result.completed:
                status = f"INCOMPLETE ({result.interruption_reason or 'interrupted'})"
            else:
                status = "PASS" if result.all_verifiers_passed else "VERIFICATION FAILURE"
            self.console.append(
                f"Run {result.run_id}: {status} | scope={result.run_scope} | "
                f"targets={result.scope_target_node_ids} | included={result.scope_included_node_ids}"
            )
            self.console.append(f"  scope_sha256={result.execution_scope_sha256}")
            for certificate in result.certificates:
                output = result.outputs[certificate.node_id]
                self.console.append(
                    f"  {certificate.node_id}: device={certificate.actual_device}/{certificate.backend}, "
                    f"evidence={certificate.evidence or ('none',)}, output={output}"
                )
            if self.selected_node_id:
                self._show_node_verification(self.selected_node_id)
            else:
                if result.completed:
                    self.verification.setPlainText(
                        "Run completed. Select a node to inspect its verification records."
                    )
                else:
                    self.verification.setPlainText(
                        "Run is incomplete. Select an executed node to inspect partial records; "
                        "incomplete runs never satisfy all_verifiers_passed."
                    )
                self._refresh_proof_explorer()
        finally:
            self._execution_control = None
            self._execution_worker = None
            self._sync_execution_actions()

    def _execution_failed(self, error: str) -> None:
        self.console.append(f"Run failed: {error}")
        self.verification.setPlainText("Run failed; no current runtime evidence is attached.")
        self._execution_control = None
        self._execution_worker = None
        self._sync_execution_actions()
        self._refresh_proof_explorer()

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

    def closeEvent(self, event):
        if self._execution_control is not None:
            self._execution_control.cancel()
        super().closeEvent(event)

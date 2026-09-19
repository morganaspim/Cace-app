from __future__ import annotations

from hashlib import sha256
import json

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QFormLayout, QInputDialog

from cace_studio.ai.heartbeat_context import build_heartbeat_context_packet
from cace_studio.core.execution_control import ExecutionControl
from cace_studio.core.heartbeat import AIHeartbeatUpdate, CanvasHeartbeatEngine
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph_edit import (
    GraphFragment,
    align_node_positions,
    copy_graph_fragment,
    paste_graph_fragment,
)
from cace_studio.core.graph_groups import (
    create_group,
    group_node_ids,
    remove_nodes_from_groups,
)
from cace_studio.core.reproducibility import experiment_fingerprint

from .execution_worker import ExecutionWorker
from .group_overlay import GroupOverlayManager
from .main_window import MainWindow
from .minimap import MiniMapView
from .proof_explorer import ProofExplorerWidget
from .open_problems_toolkit import OpenProblemsToolkitWidget


class StudioMainWindow(MainWindow):
    """CACE Studio shell with proof, grouping and controlled execution tools.

    Proof Explorer is strictly read-only. Group overlays are presentation-only
    views of persisted experiment group membership. Execution runs against an
    immutable snapshot in a worker thread; pause/cancel are cooperative at
    module boundaries rather than unsafe thread interruption inside modules.
    """

    def __init__(self, registry, settings):
        super().__init__(registry, settings)
        self._graph_clipboard: GraphFragment | None = None
        self._paste_generation = 0
        self._open_problem_heartbeat = CanvasHeartbeatEngine()

        self._execution_pool = QThreadPool.globalInstance()
        self._execution_control: ExecutionControl | None = None
        self._execution_worker: ExecutionWorker | None = None

        self._group_overlays = GroupOverlayManager(
            self.scene,
            on_selected=self._group_selected,
        )
        self._group_overlays.sync(self.experiment.groups)

        self._install_graph_edit_actions()
        self._install_group_actions()
        self._install_scoped_run_action()

        self.minimap = MiniMapView(self.scene, self.canvas, self)
        self.minimap_dock = self._dock(
            "Minimap",
            self.minimap,
            Qt.LeftDockWidgetArea,
        )

        self.proof_explorer = ProofExplorerWidget(self)
        self.proof_explorer_dock = self._dock(
            "Proof Explorer",
            self.proof_explorer,
            Qt.RightDockWidgetArea,
        )
        self.proof_explorer.show_all_claims()
        self._install_open_problems_toolkit()
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

    def _install_group_actions(self) -> None:
        group_menu = self.menuBar().addMenu("Group")
        self._action(
            group_menu,
            "Create Group from Selection",
            self.create_group_from_selection,
            "Ctrl+G",
        )
        self._action(
            group_menu,
            "Ungroup Selected Nodes",
            self.ungroup_selection,
            "Ctrl+Shift+G",
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

    def _install_open_problems_toolkit(self) -> None:
        self.open_problems_toolkit = OpenProblemsToolkitWidget(
            self.import_open_problem,
            self.play_open_problem,
            self,
        )
        self.open_problems_dock = self._dock(
            "Open Problems Toolkit",
            self.open_problems_toolkit,
            Qt.RightDockWidgetArea,
        )
        self.open_problems_dock.hide()
        research_menu = self._menu_named("Research")
        if research_menu is None:
            research_menu = self.menuBar().addMenu("Research")
        self._action(
            research_menu,
            "Open Problems Toolkit",
            self.show_open_problems_toolkit,
        )

    def show_open_problems_toolkit(self) -> None:
        self.open_problems_dock.show()
        self.open_problems_dock.raise_()

    def _open_problem_node(self, problem_id: str):
        return next(
            (
                node
                for node in self.experiment.nodes
                if node.module_id == "research.open_problem"
                and node.params.get("problem_id") == problem_id
            ),
            None,
        )

    def import_open_problem(self, problem):
        existing = self._open_problem_node(problem.problem_id)
        if existing is not None:
            self._reselect_nodes((existing.id,))
            self.console.append(
                f"Open problem already on canvas: {problem.title} ({problem.problem_id})."
            )
            return existing.id

        pos = self.canvas.mapToScene(self.canvas.viewport().rect().center())
        item = self.canvas.add_module("research.open_problem", pos)
        node = next(node for node in self.experiment.nodes if node.id == item.node_id)
        node.params = problem.to_module_params()
        item.setToolTip(
            f"{problem.title}\nStatus: {problem.status}\n"
            f"Authority: {problem.authority}\nLast verified: {problem.last_verified}"
        )
        self._autosave_tick()
        self._reselect_nodes((node.id,))
        self.console.append(
            f"Imported {problem.title!r} to canvas as {node.id}. "
            "This is a research object, not verification evidence."
        )
        return node.id

    @staticmethod
    def _heartbeat_semantic_hash(node) -> str:
        payload = json.dumps(
            {
                "module_id": node.module_id,
                "params": node.params,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=repr,
        ).encode("utf-8")
        return sha256(payload).hexdigest()

    def play_open_problem(self, problem) -> None:
        node_id = self.import_open_problem(problem)
        previous = self._open_problem_heartbeat.frame
        semantic_hashes = {
            node.id: self._heartbeat_semantic_hash(node)
            for node in self.experiment.nodes
        }
        verification = (
            dict(self.last_result.verification)
            if self.last_result is not None
            else {}
        )
        frame = self._open_problem_heartbeat.advance(
            self.experiment,
            semantic_hashes=semantic_hashes,
            verification=verification,
            ai_updates=(
                AIHeartbeatUpdate(
                    node_id,
                    interest_delta=0.9,
                    note=f"Play open problem: {problem.problem_id}",
                ),
            ),
        )
        self.canvas.apply_heartbeat_frame(frame)
        packet = build_heartbeat_context_packet(
            self.experiment,
            frame,
            previous,
            max_nodes=64,
        )
        context = problem.play_context() + "\n\n" + packet.to_prompt_text()
        accepted = self.assistant.ask_context(
            context,
            label="open-problem-play",
        )
        self.console.append(
            f"Play heartbeat applied to {problem.title!r}. "
            + (
                "Structured context sent to the configured local AI."
                if accepted
                else "Local AI is not configured/enabled; heartbeat exploration still ran locally."
            )
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

    def _group_selected(self, group_id: str) -> None:
        try:
            node_ids = group_node_ids(self.experiment, group_id)
        except KeyError:
            return
        self._reselect_nodes(node_ids)
        first_id = node_ids[0] if node_ids else None
        if first_id is not None:
            for item in self.scene.items():
                if getattr(item, "node_id", None) == first_id:
                    self._selected(item)
                    break
        self.console.append(
            f"Selected group {group_id}: {len(node_ids)} node(s). "
            "Use Selected + Upstream to execute this named subgraph target set."
        )

    def create_group_from_selection(self) -> None:
        selected = tuple(sorted(self.canvas.selected_node_ids()))
        if not selected:
            self.console.append("Create group: select at least one node.")
            return
        name, accepted = QInputDialog.getText(self, "Create Group", "Group name:")
        if not accepted:
            return
        self._sync_positions()
        try:
            self._record_history(sync_positions=False)
            group = create_group(self.experiment, selected, name=name)
        except Exception as exc:
            # If creation failed after the history snapshot, discard the no-op
            # undo entry by restoring the previous snapshot through undo.
            previous = self.history.undo(self.experiment)
            if previous is not None:
                self.experiment = previous
            self._sync_history_actions()
            self.console.append(f"Create group failed: {type(exc).__name__}: {exc}")
            return
        self._group_overlays.sync(self.experiment.groups)
        self._sync_history_actions()
        self._autosave_tick()
        self.console.append(
            f"Created group {group.name!r} ({group.id}) with {len(group.node_ids)} node(s). "
            "Grouping is presentation metadata and does not invalidate run evidence."
        )

    def ungroup_selection(self) -> None:
        selected = tuple(sorted(self.canvas.selected_node_ids()))
        if not selected:
            self.console.append("Ungroup: select grouped nodes first.")
            return
        trial = self.history.snapshot(self.experiment)
        changed = remove_nodes_from_groups(trial, selected)
        if not changed:
            self.console.append("Ungroup: selected nodes are not grouped.")
            return
        self._record_history()
        self.experiment = trial
        self._group_overlays.sync(self.experiment.groups)
        self._sync_history_actions()
        self._autosave_tick()
        self.console.append(
            f"Updated/removed group(s): {', '.join(changed)}. "
            "Scientific run evidence remains attached because graph semantics did not change."
        )

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
            f"Copied {len(self._graph_clipboard.nodes)} node(s) and {edge_count} internal edge(s). "
            "Pasted nodes are intentionally ungrouped."
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

    def _selected(self, item):
        super()._selected(item)
        for row, spec in enumerate(item.module.parameters, start=1):
            label_item = self.form.itemAt(row, QFormLayout.LabelRole)
            field_item = self.form.itemAt(row, QFormLayout.FieldRole)
            label = label_item.widget() if label_item is not None else None
            field = field_item.widget() if field_item is not None else None
            if label is not None and spec.unit:
                label.setText(f"{spec.name} [{spec.unit}]")
            if field is not None:
                details = spec.description.strip()
                if spec.unit:
                    details = (details + "\n" if details else "") + f"Unit: {spec.unit}"
                if details:
                    field.setToolTip(details)

    def _node_moved(self, item, old_pos, new_pos):
        super()._node_moved(item, old_pos, new_pos)
        self._group_overlays.refresh()
        self.minimap.schedule_refresh()

    def _delete_requested(self, node_ids, edge_keys):
        super()._delete_requested(node_ids, edge_keys)
        changed_groups = remove_nodes_from_groups(self.experiment, node_ids)
        if changed_groups:
            self._group_overlays.sync(self.experiment.groups)
            self._autosave_tick()
            self.console.append(
                "Pruned deleted node(s) from group(s): " + ", ".join(changed_groups)
            )

    def _restore_experiment(self, experiment, *, log_message=None):
        if hasattr(self, "_group_overlays"):
            self._group_overlays.clear()
        super()._restore_experiment(experiment, log_message=log_message)
        if hasattr(self, "_group_overlays"):
            self._group_overlays.sync(self.experiment.groups)
        if hasattr(self, "minimap"):
            self.minimap.schedule_refresh()

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
        if hasattr(self, "_group_overlays"):
            self._group_overlays.clear()
        super().new_file()
        self._graph_clipboard = None
        self._paste_generation = 0
        self._group_overlays.sync(self.experiment.groups)
        self.minimap.schedule_refresh()
        self._refresh_proof_explorer()

    def closeEvent(self, event):
        if self._execution_control is not None:
            self._execution_control.cancel()
        super().closeEvent(event)

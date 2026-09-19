from __future__ import annotations

from hashlib import sha256
import json
from uuid import uuid4

from PySide6.QtCore import QPointF, QThreadPool, QTimer, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QFormLayout, QInputDialog

from cace_studio.core.execution_control import ExecutionControl
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph_edit import (
    GraphFragment,
    align_node_positions,
    copy_graph_fragment,
    paste_graph_fragment,
)
from cace_studio.ai.heartbeat_context import build_heartbeat_context_packet
from cace_studio.ai.protein_play import (
    ProteinHeartbeatPlayEngine,
    discover_protein_outputs,
)
from cace_studio.core.compute_economy import ComputeCreditEconomy, sample_host_headroom
from cace_studio.core.graph import Node
from cace_studio.core.heartbeat import AIHeartbeatUpdate, CanvasHeartbeatEngine
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
from .open_problems import OpenProblemsWidget
from .protein_playground import ProteinPlaygroundWidget


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
        self._install_research_controls()
        self._sync_execution_actions()

    def _install_research_controls(self) -> None:
        self._canvas_heartbeat = CanvasHeartbeatEngine()
        self._compute_economy = ComputeCreditEconomy()
        self.open_problems = OpenProblemsWidget(
            self._import_open_problem,
            self._play_open_problem,
            self,
        )
        self.open_problems_dock = self._dock(
            "Open Problems",
            self.open_problems,
            Qt.LeftDockWidgetArea,
        )
        self._protein_play_engines = {}
        self.protein_playground = ProteinPlaygroundWidget(
            self._protein_sources,
            self._play_protein,
            self._import_alphafold_api,
            self,
        )
        self.protein_playground_dock = self._dock(
            "Protein Playground",
            self.protein_playground,
            Qt.RightDockWidgetArea,
        )
        self._economy_timer = QTimer(self)
        self._economy_timer.setInterval(2_000)
        self._economy_timer.timeout.connect(self._economy_tick)
        self._economy_timer.start()
        self._economy_tick()

    def _protein_sources(self):
        return discover_protein_outputs(self.last_result)

    def _import_alphafold_api(self, accession: str) -> str:
        accession = str(accession).strip()
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")
        if not 2 <= len(accession) <= 64 or any(char not in allowed for char in accession):
            raise ValueError("UniProt accession must be a simple canonical identifier")
        if not self.registry.contains("protein.alphafold_api_import"):
            raise RuntimeError(
                "This build does not yet contain the molecular-science AlphaFold DB API "
                "module. Integrate the molecular/materials science module branch first."
            )
        if self._execution_control is not None:
            raise RuntimeError("wait for the active graph execution to finish before importing")

        self._record_history()
        node_id = f"alphafold_{uuid4().hex[:8]}"
        position = (
            80.0 + 35.0 * (len(self.experiment.nodes) % 8),
            110.0 + 25.0 * (len(self.experiment.nodes) % 5),
        )
        item = self.canvas.add_module(
            "protein.alphafold_api_import",
            QPointF(*position),
            notify=False,
            node_id=node_id,
        )
        self.experiment.nodes.append(
            Node(
                id=node_id,
                module_id="protein.alphafold_api_import",
                params={
                    "uniprot_accession": accession,
                    "prediction_index": 0,
                    "timeout_seconds": 15.0,
                },
                position=position,
            )
        )
        self._invalidate_run_evidence("AlphaFold DB API protein source imported")
        self._autosave_tick()
        self.minimap.schedule_refresh()
        self.scene.clearSelection()
        item.setSelected(True)
        self._selected(item)
        self.console.append(
            f"AlphaFold DB API import requested for {accession} as {node_id}. "
            "Starting Selected + Upstream execution; retrieved data retain source/license attribution."
        )
        self.run_selected_upstream()
        return node_id

    def _play_protein(self, node_id: str):
        sources = dict(self._protein_sources())
        view = sources.get(node_id)
        if view is None:
            raise ValueError(
                "protein output is not present in the currently attached run"
            )
        cached = self._protein_play_engines.get(node_id)
        if cached is None or cached.view.semantic_sha256 != view.semantic_sha256:
            cached = ProteinHeartbeatPlayEngine(view, seed=0)
            self._protein_play_engines[node_id] = cached
        step = cached.step()

        previous = self._canvas_heartbeat.frame
        verification = (
            dict(self.last_result.verification)
            if self.last_result is not None
            else {}
        )
        frame = self._canvas_heartbeat.advance(
            self.experiment,
            semantic_hashes=self._semantic_hashes(),
            verification=verification,
            inputs_ready_nodes=tuple(node.id for node in self.experiment.nodes),
            ai_updates=(
                AIHeartbeatUpdate(
                    node_id,
                    0.8,
                    "user requested Protein Play",
                ),
            ),
        )
        self.canvas.apply_heartbeat_frame(frame)
        canvas_packet = build_heartbeat_context_packet(
            self.experiment,
            frame,
            previous,
            max_nodes=64,
        )
        wallet = self._compute_economy.wallets.get(node_id)
        credits = wallet.credits if wallet is not None else 0.0
        context = "\n\n".join(
            (
                step.context,
                "SOURCE CANVAS HEARTBEAT",
                canvas_packet.to_prompt_text(),
                (
                    f"Internal research compute credits for the source node: {credits:.2f}. "
                    "Autonomous follow-up experiments should use bounded compute bids."
                ),
            )
        )
        accepted = self.assistant.ask_context(context, label="protein-play")
        self.console.append(
            f"Protein Play: node {node_id}; residue and canvas heartbeat attention updated. "
            "The source structure was not mutated and AI output is non-evidentiary."
        )
        return accepted, step

    def _semantic_hashes(self) -> dict[str, str]:
        hashes = {}
        for node in self.experiment.nodes:
            payload = json.dumps(
                {"module_id": node.module_id, "params": node.params},
                sort_keys=True,
                separators=(",", ":"),
                default=repr,
            )
            hashes[node.id] = sha256(payload.encode("utf-8")).hexdigest()
        return hashes

    def _economy_tick(self) -> None:
        tick = self._compute_economy.tick(
            (node.id for node in self.experiment.nodes),
            sample_host_headroom(),
        )
        self.canvas.apply_compute_wallets(tick.wallet_credits)
        self.economy_status.setText(
            f"Heartbeat economy: treasury={tick.treasury:.2f} internal credits; "
            f"last mint={tick.minted:.2f}. Credits are non-monetary and non-evidentiary."
        )

    def _import_open_problem(self, problem) -> str:
        for node in self.experiment.nodes:
            if (
                node.module_id == "research.open_problem"
                and node.params.get("problem_id") == problem.problem_id
            ):
                return node.id
        self._record_history()
        node_id = f"problem_{uuid4().hex[:8]}"
        position = (60.0 + 30.0 * (len(self.experiment.nodes) % 8), 60.0)
        item = self.canvas.add_module(
            "research.open_problem",
            QPointF(*position),
            notify=False,
            node_id=node_id,
        )
        self.experiment.nodes.append(
            Node(
                id=node_id,
                module_id="research.open_problem",
                params=problem.to_module_params(),
                position=position,
            )
        )
        self._invalidate_run_evidence("open problem imported")
        self._autosave_tick()
        self.minimap.schedule_refresh()
        self.scene.clearSelection()
        item.setSelected(True)
        self._selected(item)
        return node_id

    def _play_open_problem(self, problem) -> bool:
        node_id = self._import_open_problem(problem)
        previous = self._canvas_heartbeat.frame
        verification = (
            dict(self.last_result.verification)
            if self.last_result is not None
            else {}
        )
        frame = self._canvas_heartbeat.advance(
            self.experiment,
            semantic_hashes=self._semantic_hashes(),
            verification=verification,
            inputs_ready_nodes=tuple(node.id for node in self.experiment.nodes),
            ai_updates=(
                AIHeartbeatUpdate(
                    node_id,
                    0.8,
                    f"user requested Play for {problem.problem_id}",
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
        wallet = self._compute_economy.wallets.get(node_id)
        credits = wallet.credits if wallet is not None else 0.0
        context = "\n\n".join(
            (
                problem.ai_context(),
                packet.to_prompt_text(),
                (
                    f"Internal research compute credits for this node: {credits:.2f}. "
                    "User-triggered Play is allowed independently; autonomous follow-up "
                    "experiments should bid against the spare-compute economy."
                ),
            )
        )
        accepted = self.assistant.ask_context(context, label="open-problem-play")
        self.console.append(
            f"Open Problem Play: {problem.title}; heartbeat attention raised on {node_id}. "
            "This is research navigation only and cannot mark the problem solved."
        )
        return accepted

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
            if hasattr(self, "protein_playground"):
                self.protein_playground.refresh_sources()
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
        if hasattr(self, "_protein_play_engines"):
            self._protein_play_engines.clear()
        if hasattr(self, "protein_playground"):
            self.protein_playground.refresh_sources()
        self._group_overlays.sync(self.experiment.groups)
        self.minimap.schedule_refresh()
        self._refresh_proof_explorer()

    def closeEvent(self, event):
        if self._execution_control is not None:
            self._execution_control.cancel()
        super().closeEvent(event)

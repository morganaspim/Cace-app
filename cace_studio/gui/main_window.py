from __future__ import annotations

try:
    from PySide6.QtCore import QPointF, QTimer, Qt
    from PySide6.QtGui import QAction, QKeySequence
    from PySide6.QtWidgets import (
        QDockWidget,
        QFileDialog,
        QFormLayout,
        QGraphicsScene,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as e:
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from e

from cace_studio import __version__
from cace_studio.core.autosave import autosave_exists, read_autosave, write_autosave
from cace_studio.core.device import DeviceManager
from cace_studio.core.edit_history import ExperimentHistory
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.report import save_run_report
from cace_studio.core.serialization import load_experiment, save_experiment
from .ai_assistant import LocalAIAssistantWidget
from .ai_settings_dialog import LocalAISettingsDialog
from .node_canvas import CanvasView, ModuleLibrary


class MainWindow(QMainWindow):
    def __init__(self, registry, settings):
        super().__init__()
        self.registry = registry
        self.settings = settings
        self.experiment = Experiment(name="Untitled")
        self.history = ExperimentHistory(limit=100)
        self.last_result = None
        self.selected_node_id = None
        self.setWindowTitle(f"CACE Studio — Verified Research Environment {__version__}")
        self.resize(1380, 860)
        self.scene = QGraphicsScene(self)
        self.canvas = CanvasView(
            self.scene,
            registry,
            on_node_created=self._node_created,
            on_edge_created=self._edge_created,
            on_selected=self._selected,
            on_node_moved=self._node_moved,
            on_delete_requested=self._delete_requested,
        )
        self.setCentralWidget(self.canvas)
        self._make_actions()
        self._make_library()
        self._make_properties()
        self._make_proof()
        self._make_verification()
        self._make_console()
        self._make_controls()
        self._make_assistant()
        self._sync_controls()
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(30_000)
        self.autosave_timer.timeout.connect(self._autosave_tick)
        self.autosave_timer.start()

    def _dock(self, title, widget, area):
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _action(self, menu, label, callback, shortcut=None):
        action = QAction(label, self)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        menu.addAction(action)
        return action

    def _make_actions(self):
        file_menu = self.menuBar().addMenu("File")
        self._action(file_menu, "New", self.new_file, QKeySequence.New)
        self._action(file_menu, "Open", self.open_file, QKeySequence.Open)
        self._action(file_menu, "Save As", self.save_file, QKeySequence.SaveAs)
        file_menu.addSeparator()
        self._action(file_menu, "Recover Autosave", self.recover_autosave)
        self._action(file_menu, "Export Last Run Report", self.export_report)

        edit_menu = self.menuBar().addMenu("Edit")
        self.undo_action = self._action(edit_menu, "Undo", self.undo, QKeySequence.Undo)
        self.redo_action = self._action(edit_menu, "Redo", self.redo, QKeySequence.Redo)
        edit_menu.addSeparator()
        self._action(edit_menu, "Delete Selection", self.canvas.request_delete_selected, "Delete")
        self._action(edit_menu, "Select All Nodes", self.canvas.select_all_nodes, QKeySequence.SelectAll)

        view_menu = self.menuBar().addMenu("View")
        self._action(view_menu, "Fit Graph", self.canvas.fit_all, "F")
        self._action(view_menu, "Reset Zoom", self.canvas.reset_zoom, "Ctrl+0")

        run_menu = self.menuBar().addMenu("Run")
        self._action(run_menu, "Execute + Verify Graph", self.run_graph, "Ctrl+R")

        ai_menu = self.menuBar().addMenu("AI")
        self._action(ai_menu, "Configure Local AI", self._configure_ai)
        self._sync_history_actions()

    def _make_library(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(4, 4, 4, 4)
        self.library_search = QLineEdit()
        self.library_search.setPlaceholderText("Search modules…")
        self.library = ModuleLibrary(self.registry)
        self.library_search.textChanged.connect(self.library.filter_text)
        layout.addWidget(self.library_search)
        layout.addWidget(self.library)
        self._dock("Module Library", wrapper, Qt.LeftDockWidgetArea)

    def _make_properties(self):
        self.prop = QWidget()
        self.form = QFormLayout(self.prop)
        self.form.addRow(QLabel("Select a node to edit parameters."))
        self._dock("Properties", self.prop, Qt.RightDockWidgetArea)

    def _make_proof(self):
        self.proof = QTextEdit()
        self.proof.setReadOnly(True)
        self.proof.setPlainText("Proof Status\n\nSelect a node.")
        self._dock("Proof / Capability", self.proof, Qt.RightDockWidgetArea)

    def _make_verification(self):
        self.verification = QTextEdit()
        self.verification.setReadOnly(True)
        self.verification.setPlainText("No run yet.")
        self._dock("Run Verification", self.verification, Qt.RightDockWidgetArea)

    def _make_console(self):
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlainText(
            "Drag modules onto the canvas. Click an output port, then an input port, to connect them.\n"
            "Ctrl+wheel zooms; drag on empty space for multi-select; Delete removes the selection.\n"
        )
        self._dock("Console", self.console, Qt.BottomDockWidgetArea)

    def _make_controls(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.ai_status = QLabel()
        self.ai_button = QPushButton()
        self.ai_button.clicked.connect(self._toggle_ai)
        self.ai_configure_button = QPushButton("Configure Local AI")
        self.ai_configure_button.clicked.connect(self._configure_ai)
        self.gpu_status = QLabel()
        self.gpu_button = QPushButton()
        self.gpu_button.clicked.connect(self._toggle_gpu)
        layout.addWidget(QLabel("Independent execution controls"))
        layout.addWidget(self.ai_status)
        layout.addWidget(self.ai_button)
        layout.addWidget(self.ai_configure_button)
        layout.addSpacing(12)
        layout.addWidget(self.gpu_status)
        layout.addWidget(self.gpu_button)
        layout.addStretch()
        self._dock("Controls", widget, Qt.LeftDockWidgetArea)

    def _assistant_context(self) -> str:
        lines = [
            f"Experiment: {self.experiment.name}",
            f"Nodes: {len(self.experiment.nodes)}",
            f"Edges: {len(self.experiment.edges)}",
        ]
        for node in self.experiment.nodes[:40]:
            marker = " [SELECTED]" if node.id == self.selected_node_id else ""
            params = repr(node.params)
            if len(params) > 800:
                params = params[:797] + "..."
            lines.append(
                f"- node {node.id}{marker}: module={node.module_id}; params={params}"
            )
        if len(self.experiment.nodes) > 40:
            lines.append(f"- ... {len(self.experiment.nodes) - 40} more node(s) omitted")

        for edge in self.experiment.edges[:60]:
            lines.append(
                f"- edge {edge.source_node}.{edge.source_port} -> "
                f"{edge.target_node}.{edge.target_port}"
            )
        if len(self.experiment.edges) > 60:
            lines.append(f"- ... {len(self.experiment.edges) - 60} more edge(s) omitted")

        if self.last_result is None:
            lines.append("Current attached run evidence: none")
        else:
            completed = getattr(self.last_result, "completed", True)
            lines.append(
                "Current attached run: "
                f"id={getattr(self.last_result, 'run_id', 'unknown')}; "
                f"completed={completed}; "
                f"all_verifiers_passed={getattr(self.last_result, 'all_verifiers_passed', False)}"
            )
        lines.append(
            "This is a read-only convenience snapshot. It is not proof or verification evidence."
        )
        return "\n".join(lines)

    def _make_assistant(self):
        self.assistant = LocalAIAssistantWidget(
            self.settings,
            self._configure_ai,
            parent=self,
            context_provider=self._assistant_context,
        )
        self.assistant_dock = self._dock("Local AI Assistant", self.assistant, Qt.RightDockWidgetArea)

    def _configure_ai(self):
        dialog = LocalAISettingsDialog(self.settings, self)
        dialog.exec()
        self._sync_controls()

    def _toggle_ai(self):
        self.settings.ai_enabled = not self.settings.ai_enabled
        self.settings.save()
        self._sync_controls()
        self.console.append(
            "AI assistant enabled. AI output is not verification evidence."
            if self.settings.ai_enabled
            else "AI assistant disabled. Execution and verification remain available."
        )

    def _toggle_gpu(self):
        self.settings.gpu_enabled = not self.settings.gpu_enabled
        self.settings.save()
        self._sync_controls()
        self.console.append(f"GPU policy {'enabled' if self.settings.gpu_enabled else 'disabled'}.")

    def _sync_controls(self):
        self.ai_status.setText("AI: ENABLED" if self.settings.ai_enabled else "AI: DISABLED")
        self.ai_button.setText("Turn AI Off" if self.settings.ai_enabled else "Turn AI On")
        available = DeviceManager.gpu_available()
        self.gpu_status.setText(
            f"GPU policy: {'ON' if self.settings.gpu_enabled else 'OFF'} | "
            f"CUDA/CuPy available: {'YES' if available else 'NO'}"
        )
        self.gpu_button.setText("Turn GPU Off" if self.settings.gpu_enabled else "Turn GPU On")
        if hasattr(self, "assistant"):
            self.assistant.refresh()
            self.assistant_dock.setVisible(self.settings.ai_enabled)

    def _sync_history_actions(self):
        if hasattr(self, "undo_action"):
            self.undo_action.setEnabled(self.history.can_undo)
            self.redo_action.setEnabled(self.history.can_redo)

    def _record_history(self, *, sync_positions=True):
        if sync_positions:
            self._sync_positions()
        self.history.record(self.experiment)
        self._sync_history_actions()

    def _invalidate_run_evidence(self, reason: str):
        if self.last_result is not None:
            self.last_result = None
            self.verification.setPlainText(
                "Graph changed since the previous run. Execute + Verify Graph again."
            )
            self.console.append(f"Previous run evidence detached from edited graph: {reason}.")

    def _node_created(self, item):
        self._record_history()
        pos = item.pos()
        self.experiment.nodes.append(
            Node(item.node_id, item.module.metadata.module_id, {}, (pos.x(), pos.y()))
        )
        self._invalidate_run_evidence("node added")
        self._autosave_tick()

    def _edge_created(self, source, target):
        self._record_history()
        self.experiment.edges.append(
            Edge(source.node.node_id, source.port_name, target.node.node_id, target.port_name)
        )
        self._invalidate_run_evidence("connection added")
        self._autosave_tick()

    def _node_moved(self, item, old_pos, new_pos):
        self._record_history(sync_positions=False)
        self._sync_positions()
        self._autosave_tick()

    def _delete_requested(self, node_ids, edge_keys):
        self._record_history()
        self.experiment.edges = [
            edge
            for edge in self.experiment.edges
            if (
                edge.source_node,
                edge.source_port,
                edge.target_node,
                edge.target_port,
            )
            not in edge_keys
            and edge.source_node not in node_ids
            and edge.target_node not in node_ids
        ]
        self.experiment.nodes = [node for node in self.experiment.nodes if node.id not in node_ids]
        self.canvas.remove_items(set(node_ids), set(edge_keys))
        if self.selected_node_id in node_ids:
            self.selected_node_id = None
            self._clear_form()
            self.form.addRow(QLabel("Select a node to edit parameters."))
            self.proof.setPlainText("Proof Status\n\nSelect a node.")
        self._invalidate_run_evidence("selection deleted")
        self._autosave_tick()

    def _clear_form(self):
        while self.form.rowCount():
            self.form.removeRow(0)

    def _parse(self, text, type_name):
        if type_name == "number":
            return float(text)
        if type_name == "integer":
            return int(text)
        if type_name == "bool":
            return text.strip().lower() in {"1", "true", "yes", "on"}
        return text

    def _selected(self, item):
        self.selected_node_id = item.node_id
        self._clear_form()
        self.form.addRow("Module", QLabel(item.module.metadata.name))
        node = next(n for n in self.experiment.nodes if n.id == item.node_id)
        for spec in item.module.parameters:
            edit = QLineEdit(str(node.params.get(spec.name, spec.default)))

            def update(n=node, s=spec, field=edit):
                try:
                    value = self._parse(field.text(), s.type_name)
                except ValueError:
                    return
                old_value = n.params.get(s.name, s.default)
                if value == old_value:
                    return
                self._record_history()
                n.params[s.name] = value
                self._invalidate_run_evidence(f"parameter {s.name} changed")
                self._autosave_tick()

            edit.editingFinished.connect(update)
            self.form.addRow(spec.name, edit)
        proof_status = item.module.proof_status
        assumptions = "; ".join(item.module.metadata.assumptions) or "none declared"
        self.proof.setPlainText(
            f"{item.module.metadata.name}\n"
            f"Maturity: {item.module.metadata.maturity.value}\n"
            f"Declared verification capabilities: {', '.join(sorted(e.value for e in proof_status.evidence)) or 'none'}\n"
            f"GPU-capable: {item.module.supports_gpu}\n"
            f"Assumptions: {assumptions}\n"
            f"Unit tests: {proof_status.unit_tests}\n"
            f"Property tests: {proof_status.property_tests}\n"
            f"Formal artifact: {proof_status.formal_artifact or 'none'}\n"
            f"Limitations: {', '.join(proof_status.limitations) or 'none declared'}\n\n"
            "Important: capabilities are not run evidence. See Run Verification after execution."
        )
        self._show_node_verification(item.node_id)

    def _show_node_verification(self, node_id):
        if not self.last_result or node_id not in self.last_result.verification:
            self.verification.setPlainText("No verification record for this node yet.")
            return
        records = self.last_result.verification[node_id]
        certificate = next((c for c in self.last_result.certificates if c.node_id == node_id), None)
        lines = []
        if certificate:
            lines += [
                f"Device requested: {certificate.requested_device}",
                f"Device used: {certificate.actual_device} ({certificate.backend})",
                f"Certified evidence from this run: {', '.join(certificate.evidence) or 'none'}",
                "",
            ]
        if not records:
            lines.append("Module generated no verification evidence for this run.")
        for record in records:
            lines += [
                f"[{record.state.value.upper()}] {record.kind.value}",
                record.claim,
                f"Verifier: {record.verifier}",
                f"Method: {record.method}",
                f"Metrics: {record.metrics}",
                "",
            ]
        self.verification.setPlainText("\n".join(lines))

    def _sync_positions(self):
        items = {
            getattr(item, "node_id", None): item
            for item in self.scene.items()
            if hasattr(item, "node_id")
        }
        for node in self.experiment.nodes:
            if node.id in items:
                pos = items[node.id].pos()
                node.position = (pos.x(), pos.y())

    def _restore_experiment(self, experiment: Experiment, *, log_message: str | None = None):
        self.experiment = ExperimentHistory.snapshot(experiment)
        self.canvas.clear_graph()
        items = {}
        for node in self.experiment.nodes:
            item = self.canvas.add_module(
                node.module_id,
                QPointF(*node.position),
                notify=False,
                node_id=node.id,
            )
            items[node.id] = item
        for edge in self.experiment.edges:
            source = items[edge.source_node].output_ports[edge.source_port]
            target = items[edge.target_node].input_ports[edge.target_port]
            created = self.canvas.connect_ports(source, target, notify=False)
            if created is None:
                raise ValueError(
                    f"could not restore edge {edge.source_node}.{edge.source_port} -> "
                    f"{edge.target_node}.{edge.target_port}"
                )
        self.selected_node_id = None
        self._clear_form()
        self.form.addRow(QLabel("Select a node to edit parameters."))
        self.proof.setPlainText("Proof Status\n\nSelect a node.")
        self._invalidate_run_evidence("experiment state restored")
        if log_message:
            self.console.append(log_message)

    def undo(self):
        self._sync_positions()
        previous = self.history.undo(self.experiment)
        if previous is None:
            return
        self._restore_experiment(previous, log_message="Undo")
        self._sync_history_actions()
        self._autosave_tick()

    def redo(self):
        self._sync_positions()
        following = self.history.redo(self.experiment)
        if following is None:
            return
        self._restore_experiment(following, log_message="Redo")
        self._sync_history_actions()
        self._autosave_tick()

    def run_graph(self):
        try:
            self._sync_positions()
            self.last_result = GraphExecutor(
                self.registry, gpu_enabled=self.settings.gpu_enabled
            ).run(self.experiment)
            status = "PASS" if self.last_result.all_verifiers_passed else "VERIFICATION FAILURE"
            self.console.append(f"Run {self.last_result.run_id}: {status}")
            for certificate in self.last_result.certificates:
                output = self.last_result.outputs[certificate.node_id]
                self.console.append(
                    f"  {certificate.node_id}: device={certificate.actual_device}/{certificate.backend}, "
                    f"evidence={certificate.evidence or ('none',)}, output={output}"
                )
            if self.selected_node_id:
                self._show_node_verification(self.selected_node_id)
        except Exception as exc:
            self.console.append(f"Run failed: {type(exc).__name__}: {exc}")

    def export_report(self):
        if not self.last_result:
            self.console.append("No completed run to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export run report", "run-report.json", "JSON (*.json)"
        )
        if path:
            save_run_report(self.last_result, self.experiment.name, path)
            self.console.append(f"Exported run report {path}")

    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save experiment", "experiment.cace", "CACE Experiment (*.cace)"
        )
        if path:
            self._sync_positions()
            save_experiment(self.experiment, path)
            self.console.append(f"Saved {path}")

    def new_file(self):
        self.canvas.clear_graph()
        self.experiment = Experiment(name="Untitled")
        self.history.clear()
        self._sync_history_actions()
        self.last_result = None
        self.selected_node_id = None
        self.verification.setPlainText("No run yet.")
        self.console.append("New experiment")
        self._autosave_tick()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open experiment", "", "CACE Experiment (*.cace)"
        )
        if not path:
            return
        loaded = load_experiment(path)
        self.history.clear()
        self._restore_experiment(loaded, log_message=f"Opened {path}")
        self._sync_history_actions()
        self._autosave_tick()

    def _autosave_tick(self):
        try:
            self._sync_positions()
            write_autosave(self.experiment)
        except Exception as exc:
            if hasattr(self, "console"):
                self.console.append(f"Autosave failed: {type(exc).__name__}: {exc}")

    def recover_autosave(self):
        if not autosave_exists():
            self.console.append("No autosave is available.")
            return
        try:
            recovered = read_autosave()
        except Exception as exc:
            self.console.append(f"Autosave recovery failed: {type(exc).__name__}: {exc}")
            return
        self.history.clear()
        self._restore_experiment(recovered, log_message="Recovered autosaved experiment.")
        self._sync_history_actions()

    def closeEvent(self, event):
        self._autosave_tick()
        super().closeEvent(event)

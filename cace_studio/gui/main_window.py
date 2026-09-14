from __future__ import annotations
try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (QMainWindow,QWidget,QDockWidget,QGraphicsScene,QTextEdit,QFormLayout,
        QLabel,QPushButton,QVBoxLayout,QLineEdit,QFileDialog)
except ImportError as e:
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from e
from .node_canvas import CanvasView,ModuleLibrary
from cace_studio.core.graph import Experiment,Node,Edge
from cace_studio.core.serialization import save_experiment,load_experiment
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.device import DeviceManager
from cace_studio.core.report import save_run_report

class MainWindow(QMainWindow):
    def __init__(self,registry,settings):
        super().__init__(); self.registry=registry; self.settings=settings; self.experiment=Experiment(name="Untitled"); self.last_result=None; self.selected_node_id=None
        self.setWindowTitle("CACE Studio — Verified Research Environment v0.2"); self.resize(1380,860)
        self.scene=QGraphicsScene(self); self.canvas=CanvasView(self.scene,registry,self._node_created,self._edge_created,self._selected); self.setCentralWidget(self.canvas)
        self._make_actions(); self._make_library(); self._make_properties(); self._make_proof(); self._make_verification(); self._make_console(); self._make_controls()

    def _dock(self,title,widget,area):
        d=QDockWidget(title,self); d.setWidget(widget); self.addDockWidget(area,d); return d
    def _make_actions(self):
        file=self.menuBar().addMenu("File")
        for label,fn in [("New",self.new_file),("Open",self.open_file),("Save As",self.save_file),("Export Last Run Report",self.export_report)]:
            a=QAction(label,self); a.triggered.connect(fn); file.addAction(a)
        run=self.menuBar().addMenu("Run"); a=QAction("Execute + Verify Graph",self); a.triggered.connect(self.run_graph); run.addAction(a)
    def _make_library(self): self.library=ModuleLibrary(self.registry); self._dock("Module Library",self.library,Qt.LeftDockWidgetArea)
    def _make_properties(self):
        self.prop=QWidget(); self.form=QFormLayout(self.prop); self.form.addRow(QLabel("Select a node to edit parameters.")); self._dock("Properties",self.prop,Qt.RightDockWidgetArea)
    def _make_proof(self):
        self.proof=QTextEdit(); self.proof.setReadOnly(True); self.proof.setPlainText("Proof Status\n\nSelect a node."); self._dock("Proof / Capability",self.proof,Qt.RightDockWidgetArea)
    def _make_verification(self):
        self.verification=QTextEdit(); self.verification.setReadOnly(True); self.verification.setPlainText("No run yet."); self._dock("Run Verification",self.verification,Qt.RightDockWidgetArea)
    def _make_console(self):
        self.console=QTextEdit(); self.console.setReadOnly(True); self.console.setPlainText("Drag modules onto the canvas. Click an output port, then an input port, to connect them.\n")
        self._dock("Console",self.console,Qt.BottomDockWidgetArea)
    def _make_controls(self):
        w=QWidget(); lay=QVBoxLayout(w); self.ai_status=QLabel(); self.ai_button=QPushButton(); self.ai_button.clicked.connect(self._toggle_ai)
        self.gpu_status=QLabel(); self.gpu_button=QPushButton(); self.gpu_button.clicked.connect(self._toggle_gpu)
        lay.addWidget(QLabel("Independent execution controls")); lay.addWidget(self.ai_status); lay.addWidget(self.ai_button); lay.addSpacing(12); lay.addWidget(self.gpu_status); lay.addWidget(self.gpu_button); lay.addStretch()
        self._dock("Controls",w,Qt.LeftDockWidgetArea); self._sync_controls()
    def _toggle_ai(self): self.settings.ai_enabled=not self.settings.ai_enabled; self._sync_controls()
    def _toggle_gpu(self): self.settings.gpu_enabled=not self.settings.gpu_enabled; self._sync_controls(); self.console.append(f"GPU policy {'enabled' if self.settings.gpu_enabled else 'disabled'}.")
    def _sync_controls(self):
        self.ai_status.setText("AI: ENABLED" if self.settings.ai_enabled else "AI: DISABLED"); self.ai_button.setText("Turn AI Off" if self.settings.ai_enabled else "Turn AI On")
        avail=DeviceManager.gpu_available(); self.gpu_status.setText(f"GPU policy: {'ON' if self.settings.gpu_enabled else 'OFF'} | CUDA/CuPy available: {'YES' if avail else 'NO'}")
        self.gpu_button.setText("Turn GPU Off" if self.settings.gpu_enabled else "Turn GPU On")
    def _node_created(self,item):
        p=item.pos(); self.experiment.nodes.append(Node(item.node_id,item.module.metadata.module_id,{},(p.x(),p.y())))
    def _edge_created(self,source,target): self.experiment.edges.append(Edge(source.node.node_id,source.port_name,target.node.node_id,target.port_name))
    def _clear_form(self):
        while self.form.rowCount(): self.form.removeRow(0)
    def _parse(self,text,type_name):
        if type_name=="number": return float(text)
        if type_name=="integer": return int(text)
        if type_name=="bool": return text.strip().lower() in {"1","true","yes","on"}
        return text
    def _selected(self,item):
        self.selected_node_id=item.node_id; self._clear_form(); self.form.addRow("Module",QLabel(item.module.metadata.name)); node=next(n for n in self.experiment.nodes if n.id==item.node_id)
        for spec in item.module.parameters:
            edit=QLineEdit(str(node.params.get(spec.name,spec.default)))
            def update(value,n=node,s=spec):
                try: n.params[s.name]=self._parse(value,s.type_name)
                except ValueError: return
            edit.textChanged.connect(update); self.form.addRow(spec.name,edit)
        ps=item.module.proof_status; assumptions='; '.join(item.module.metadata.assumptions) or 'none declared'
        self.proof.setPlainText(f"{item.module.metadata.name}\nMaturity: {item.module.metadata.maturity.value}\nDeclared verification capabilities: {', '.join(sorted(e.value for e in ps.evidence)) or 'none'}\nGPU-capable: {item.module.supports_gpu}\nAssumptions: {assumptions}\nUnit tests: {ps.unit_tests}\nProperty tests: {ps.property_tests}\nFormal artifact: {ps.formal_artifact or 'none'}\nLimitations: {', '.join(ps.limitations) or 'none declared'}\n\nImportant: capabilities are not run evidence. See Run Verification after execution.")
        self._show_node_verification(item.node_id)
    def _show_node_verification(self,node_id):
        if not self.last_result or node_id not in self.last_result.verification: self.verification.setPlainText("No verification record for this node yet."); return
        records=self.last_result.verification[node_id]; cert=next((c for c in self.last_result.certificates if c.node_id==node_id),None); lines=[]
        if cert: lines += [f"Device requested: {cert.requested_device}",f"Device used: {cert.actual_device} ({cert.backend})",f"Certified evidence from this run: {', '.join(cert.evidence) or 'none'}",""]
        if not records: lines.append("Module generated no verification evidence for this run.")
        for r in records:
            lines += [f"[{r.state.value.upper()}] {r.kind.value}",r.claim,f"Verifier: {r.verifier}",f"Method: {r.method}",f"Metrics: {r.metrics}",""]
        self.verification.setPlainText("\n".join(lines))
    def _sync_positions(self):
        items={getattr(i,'node_id',None):i for i in self.scene.items() if hasattr(i,'node_id')}
        for n in self.experiment.nodes:
            if n.id in items:
                p=items[n.id].pos(); n.position=(p.x(),p.y())
    def run_graph(self):
        try:
            self._sync_positions(); self.last_result=GraphExecutor(self.registry,gpu_enabled=self.settings.gpu_enabled).run(self.experiment)
            status="PASS" if self.last_result.all_verifiers_passed else "VERIFICATION FAILURE"
            self.console.append(f"Run {self.last_result.run_id}: {status}")
            for cert in self.last_result.certificates:
                out=self.last_result.outputs[cert.node_id]; self.console.append(f"  {cert.node_id}: device={cert.actual_device}/{cert.backend}, evidence={cert.evidence or ('none',)}, output={out}")
            if self.selected_node_id: self._show_node_verification(self.selected_node_id)
        except Exception as e: self.console.append(f"Run failed: {type(e).__name__}: {e}")
    def export_report(self):
        if not self.last_result: self.console.append("No completed run to export."); return
        path,_=QFileDialog.getSaveFileName(self,"Export run report","run-report.json","JSON (*.json)")
        if path: save_run_report(self.last_result,self.experiment.name,path); self.console.append(f"Exported run report {path}")
    def save_file(self):
        path,_=QFileDialog.getSaveFileName(self,"Save experiment","experiment.cace","CACE Experiment (*.cace)")
        if path: self._sync_positions(); save_experiment(self.experiment,path); self.console.append(f"Saved {path}")
    def new_file(self):
        self.scene.clear(); self.canvas.edge_items.clear(); self.experiment=Experiment(name="Untitled"); self.last_result=None; self.console.append("New experiment")
    def open_file(self):
        path,_=QFileDialog.getOpenFileName(self,"Open experiment","","CACE Experiment (*.cace)")
        if not path: return
        self.new_file(); self.experiment=load_experiment(path); items={}
        for n in self.experiment.nodes:
            from PySide6.QtCore import QPointF
            item=self.canvas.add_module(n.module_id,QPointF(*n.position),notify=False); item.node_id=n.id; items[n.id]=item
        loaded=self.experiment; loaded_edges=list(self.experiment.edges); self.experiment.edges=[]
        for e in loaded_edges:
            self.canvas.pending_output=items[e.source_node].output_ports[e.source_port]; self.canvas.port_clicked(items[e.target_node].input_ports[e.target_port])
        self.experiment.edges=loaded_edges; self.experiment=loaded; self.console.append(f"Opened {path}")

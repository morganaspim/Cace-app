from __future__ import annotations
from dataclasses import dataclass
from uuid import uuid4
from PySide6.QtCore import Qt, QMimeData, QPointF
from PySide6.QtGui import QBrush, QPen, QDrag
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem,
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsView, QListWidget)

MIME_MODULE = "application/x-cace-module"

class ModuleLibrary(QListWidget):
    def __init__(self, registry, parent=None):
        super().__init__(parent); self.registry = registry; self.setDragEnabled(True)
        for cls in sorted(registry.classes(), key=lambda c:(c.metadata.category,c.metadata.name)):
            item_text = f"{cls.metadata.category} / {cls.metadata.name}"
            self.addItem(item_text); self.item(self.count()-1).setData(Qt.UserRole, cls.metadata.module_id)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item: return
        mime = QMimeData(); mime.setData(MIME_MODULE, item.data(Qt.UserRole).encode())
        drag = QDrag(self); drag.setMimeData(mime); drag.exec(Qt.CopyAction)

class PortItem(QGraphicsEllipseItem):
    R = 5
    def __init__(self, node, port_name: str, is_output: bool, y: float):
        x = node.W - self.R if is_output else -self.R
        super().__init__(x, y-self.R, self.R*2, self.R*2, node)
        self.node = node; self.port_name = port_name; self.is_output = is_output
        self.setBrush(QBrush(Qt.white)); self.setPen(QPen(Qt.black)); self.setZValue(3)
        self.setToolTip(("Output: " if is_output else "Input: ") + port_name)

    def mousePressEvent(self, event):
        view = self.scene().views()[0]
        if hasattr(view, "port_clicked"): view.port_clicked(self)
        event.accept()

class NodeItem(QGraphicsRectItem):
    W = 180
    def __init__(self, node_id, module, on_selected=None):
        h = max(82, 44 + 20*max(len(module.inputs), len(module.outputs), 1))
        super().__init__(0,0,self.W,h); self.node_id=node_id; self.module=module; self.on_selected=on_selected
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        title=QGraphicsSimpleTextItem(module.metadata.name, self); title.setPos(10,8)
        meta=QGraphicsSimpleTextItem(f"{module.metadata.category} · {module.metadata.maturity.value}", self); meta.setPos(10,26)
        self.input_ports={}; self.output_ports={}
        for i,p in enumerate(module.inputs):
            y=52+i*18; port=PortItem(self,p.name,False,y); self.input_ports[p.name]=port
            t=QGraphicsSimpleTextItem(p.name,self); t.setPos(8,y-8)
        for i,p in enumerate(module.outputs):
            y=52+i*18; port=PortItem(self,p.name,True,y); self.output_ports[p.name]=port
            t=QGraphicsSimpleTextItem(p.name,self); t.setPos(self.W-10-t.boundingRect().width(),y-8)

    def mousePressEvent(self,event):
        super().mousePressEvent(event)
        if self.on_selected: self.on_selected(self)

class EdgeItem(QGraphicsLineItem):
    def __init__(self, source: PortItem, target: PortItem):
        super().__init__(); self.source=source; self.target=target; self.setZValue(-1); self.setPen(QPen(Qt.black,2)); self.refresh()
    def refresh(self):
        a=self.source.scenePos(); b=self.target.scenePos(); self.setLine(a.x()+5,a.y()+5,b.x()+5,b.y()+5)

class CanvasView(QGraphicsView):
    def __init__(self, scene, registry, on_node_created=None, on_edge_created=None, on_selected=None, parent=None):
        super().__init__(scene,parent); self.registry=registry; self.on_node_created=on_node_created; self.on_edge_created=on_edge_created; self.on_selected=on_selected
        self.setAcceptDrops(True); self.pending_output=None; self.edge_items=[]

    def dragEnterEvent(self,event):
        if event.mimeData().hasFormat(MIME_MODULE): event.acceptProposedAction()
        else: super().dragEnterEvent(event)
    def dragMoveEvent(self,event):
        if event.mimeData().hasFormat(MIME_MODULE): event.acceptProposedAction()
        else: super().dragMoveEvent(event)
    def dropEvent(self,event):
        if not event.mimeData().hasFormat(MIME_MODULE): return super().dropEvent(event)
        module_id=bytes(event.mimeData().data(MIME_MODULE)).decode(); pos=self.mapToScene(event.position().toPoint())
        self.add_module(module_id,pos); event.acceptProposedAction()

    def add_module(self,module_id,pos, notify=True):
        module=self.registry.create(module_id); node_id=f"n_{uuid4().hex[:8]}"; item=NodeItem(node_id,module,self.on_selected); item.setPos(pos); self.scene().addItem(item)
        if notify and self.on_node_created: self.on_node_created(item)
        return item

    def port_clicked(self, port: PortItem):
        if port.is_output:
            self.pending_output=port; return
        if self.pending_output is None: return
        source=self.pending_output; self.pending_output=None
        if source.node is port.node: return
        st={p.name:p.type_name for p in source.node.module.outputs}[source.port_name]
        tt={p.name:p.type_name for p in port.node.module.inputs}[port.port_name]
        if st!="any" and tt!="any" and st!=tt: return
        edge=EdgeItem(source,port); self.scene().addItem(edge); self.edge_items.append(edge)
        if self.on_edge_created: self.on_edge_created(source,port)

    def drawForeground(self,painter,rect):
        for edge in self.edge_items: edge.refresh()
        super().drawForeground(painter,rect)

from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import QMimeData, QPointF, Qt
from PySide6.QtGui import QBrush, QDrag, QKeyEvent, QPen, QWheelEvent
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QListWidget,
)

MIME_MODULE = "application/x-cace-module"


class ModuleLibrary(QListWidget):
    def __init__(self, registry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.setDragEnabled(True)
        for cls in sorted(registry.classes(), key=lambda c: (c.metadata.category, c.metadata.name)):
            item_text = f"{cls.metadata.category} / {cls.metadata.name}"
            self.addItem(item_text)
            self.item(self.count() - 1).setData(Qt.UserRole, cls.metadata.module_id)

    def filter_text(self, text: str) -> None:
        needle = text.strip().casefold()
        for index in range(self.count()):
            item = self.item(index)
            haystack = f"{item.text()} {item.data(Qt.UserRole)}".casefold()
            item.setHidden(bool(needle) and needle not in haystack)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
        mime = QMimeData()
        mime.setData(MIME_MODULE, item.data(Qt.UserRole).encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)


class PortItem(QGraphicsEllipseItem):
    R = 5

    def __init__(self, node, port_name: str, is_output: bool, y: float):
        x = node.W - self.R if is_output else -self.R
        super().__init__(x, y - self.R, self.R * 2, self.R * 2, node)
        self.node = node
        self.port_name = port_name
        self.is_output = is_output
        self.setBrush(QBrush(Qt.white))
        self.setPen(QPen(Qt.black))
        self.setZValue(3)
        self.setToolTip(("Output: " if is_output else "Input: ") + port_name)

    def mousePressEvent(self, event):
        view = self.scene().views()[0]
        if hasattr(view, "port_clicked"):
            view.port_clicked(self)
        event.accept()


class NodeItem(QGraphicsRectItem):
    W = 180

    def __init__(self, node_id, module, on_selected=None, on_moved=None):
        height = max(82, 44 + 20 * max(len(module.inputs), len(module.outputs), 1))
        super().__init__(0, 0, self.W, height)
        self.node_id = node_id
        self.module = module
        self.on_selected = on_selected
        self.on_moved = on_moved
        self._drag_start_pos = QPointF()
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        title = QGraphicsSimpleTextItem(module.metadata.name, self)
        title.setPos(10, 8)
        meta = QGraphicsSimpleTextItem(
            f"{module.metadata.category} · {module.metadata.maturity.value}", self
        )
        meta.setPos(10, 26)
        self.input_ports = {}
        self.output_ports = {}
        for index, port_spec in enumerate(module.inputs):
            y = 52 + index * 18
            port = PortItem(self, port_spec.name, False, y)
            self.input_ports[port_spec.name] = port
            label = QGraphicsSimpleTextItem(port_spec.name, self)
            label.setPos(8, y - 8)
        for index, port_spec in enumerate(module.outputs):
            y = 52 + index * 18
            port = PortItem(self, port_spec.name, True, y)
            self.output_ports[port_spec.name] = port
            label = QGraphicsSimpleTextItem(port_spec.name, self)
            label.setPos(self.W - 10 - label.boundingRect().width(), y - 8)

    def mousePressEvent(self, event):
        self._drag_start_pos = QPointF(self.pos())
        super().mousePressEvent(event)
        if self.on_selected:
            self.on_selected(self)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.on_moved and self.pos() != self._drag_start_pos:
            self.on_moved(self, self._drag_start_pos, QPointF(self.pos()))


class EdgeItem(QGraphicsLineItem):
    def __init__(self, source: PortItem, target: PortItem):
        super().__init__()
        self.source = source
        self.target = target
        self.setZValue(-1)
        self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.refresh()

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (
            self.source.node.node_id,
            self.source.port_name,
            self.target.node.node_id,
            self.target.port_name,
        )

    def refresh(self):
        a = self.source.scenePos()
        b = self.target.scenePos()
        self.setLine(a.x() + 5, a.y() + 5, b.x() + 5, b.y() + 5)


class CanvasView(QGraphicsView):
    def __init__(
        self,
        scene,
        registry,
        on_node_created=None,
        on_edge_created=None,
        on_selected=None,
        on_node_moved=None,
        on_delete_requested=None,
        parent=None,
    ):
        super().__init__(scene, parent)
        self.registry = registry
        self.on_node_created = on_node_created
        self.on_edge_created = on_edge_created
        self.on_selected = on_selected
        self.on_node_moved = on_node_moved
        self.on_delete_requested = on_delete_requested
        self.setAcceptDrops(True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.pending_output = None
        self.edge_items: list[EdgeItem] = []

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_MODULE):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_MODULE):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(MIME_MODULE):
            return super().dropEvent(event)
        module_id = bytes(event.mimeData().data(MIME_MODULE)).decode()
        pos = self.mapToScene(event.position().toPoint())
        self.add_module(module_id, pos)
        event.acceptProposedAction()

    def add_module(self, module_id, pos, notify=True, node_id=None):
        module = self.registry.create(module_id)
        node_id = node_id or f"n_{uuid4().hex[:8]}"
        item = NodeItem(
            node_id,
            module,
            on_selected=self.on_selected,
            on_moved=self.on_node_moved,
        )
        item.setPos(pos)
        self.scene().addItem(item)
        if notify and self.on_node_created:
            self.on_node_created(item)
        return item

    def connect_ports(self, source: PortItem, target: PortItem, notify=True) -> EdgeItem | None:
        if not source.is_output or target.is_output or source.node is target.node:
            return None
        source_type = {p.name: p.type_name for p in source.node.module.outputs}[source.port_name]
        target_type = {p.name: p.type_name for p in target.node.module.inputs}[target.port_name]
        if source_type != "any" and target_type != "any" and source_type != target_type:
            return None
        key = (
            source.node.node_id,
            source.port_name,
            target.node.node_id,
            target.port_name,
        )
        if any(edge.key == key for edge in self.edge_items):
            return None
        if any(
            edge.target.node.node_id == target.node.node_id
            and edge.target.port_name == target.port_name
            for edge in self.edge_items
        ):
            return None
        edge = EdgeItem(source, target)
        self.scene().addItem(edge)
        self.edge_items.append(edge)
        if notify and self.on_edge_created:
            self.on_edge_created(source, target)
        return edge

    def port_clicked(self, port: PortItem):
        if port.is_output:
            self.pending_output = port
            return
        if self.pending_output is None:
            return
        source = self.pending_output
        self.pending_output = None
        self.connect_ports(source, port)

    def clear_graph(self) -> None:
        self.pending_output = None
        self.edge_items.clear()
        self.scene().clear()

    def selected_node_ids(self) -> set[str]:
        return {
            item.node_id
            for item in self.scene().selectedItems()
            if isinstance(item, NodeItem)
        }

    def selected_edge_keys(self) -> set[tuple[str, str, str, str]]:
        return {
            item.key
            for item in self.scene().selectedItems()
            if isinstance(item, EdgeItem)
        }

    def request_delete_selected(self) -> None:
        node_ids = self.selected_node_ids()
        edge_keys = self.selected_edge_keys()
        if not node_ids and not edge_keys:
            return
        edge_keys |= {
            edge.key
            for edge in self.edge_items
            if edge.source.node.node_id in node_ids or edge.target.node.node_id in node_ids
        }
        if self.on_delete_requested:
            self.on_delete_requested(node_ids, edge_keys)

    def remove_items(
        self,
        node_ids: set[str],
        edge_keys: set[tuple[str, str, str, str]],
    ) -> None:
        for edge in list(self.edge_items):
            if edge.key in edge_keys:
                self.scene().removeItem(edge)
                self.edge_items.remove(edge)
        for item in list(self.scene().items()):
            if isinstance(item, NodeItem) and item.node_id in node_ids:
                self.scene().removeItem(item)
        self.pending_output = None

    def select_all_nodes(self) -> None:
        for item in self.scene().items():
            if isinstance(item, NodeItem):
                item.setSelected(True)

    def fit_all(self) -> None:
        rect = self.scene().itemsBoundingRect()
        if not rect.isNull():
            self.fitInView(rect.adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio)

    def reset_zoom(self) -> None:
        self.resetTransform()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.request_delete_selected()
            event.accept()
            return
        if event.key() == Qt.Key_Escape:
            self.pending_output = None
            self.scene().clearSelection()
            event.accept()
            return
        super().keyPressEvent(event)

    def drawForeground(self, painter, rect):
        for edge in self.edge_items:
            edge.refresh()
        super().drawForeground(painter, rect)

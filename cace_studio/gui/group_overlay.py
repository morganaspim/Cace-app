from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsSimpleTextItem


class GroupOverlayItem(QGraphicsRectItem):
    """Presentation-only scene box for one persisted experiment group."""

    def __init__(self, group, on_selected=None) -> None:
        super().__init__()
        self.group_id = group.id
        self.group_name = group.name
        self.node_ids = tuple(group.node_ids)
        self.on_selected = on_selected
        self.setZValue(-3)
        pen = QPen(Qt.darkGray, 1, Qt.DashLine)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.NoBrush))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.label = QGraphicsSimpleTextItem(group.name, self)
        self.label.setZValue(1)

    def set_group_rect(self, rect) -> None:
        self.setRect(rect)
        self.label.setPos(rect.left() + 8, rect.top() + 4)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if self.on_selected:
            self.on_selected(self.group_id)
        event.accept()


class GroupOverlayManager:
    """Keep presentation overlays synchronized with Experiment.groups."""

    def __init__(self, scene, *, on_selected=None) -> None:
        self.scene = scene
        self.on_selected = on_selected
        self.items: dict[str, GroupOverlayItem] = {}

    def clear(self) -> None:
        for item in list(self.items.values()):
            # QGraphicsScene.clear() may already have deleted the wrapped C++
            # object during graph restoration. Treat that as already-cleared.
            try:
                if item.scene() is self.scene:
                    self.scene.removeItem(item)
            except RuntimeError:
                pass
        self.items.clear()

    def _node_items(self) -> dict[str, object]:
        return {
            item.node_id: item
            for item in self.scene.items()
            if hasattr(item, "node_id")
        }

    def sync(self, groups) -> None:
        self.clear()
        for group in groups:
            item = GroupOverlayItem(group, on_selected=self.on_selected)
            self.scene.addItem(item)
            self.items[group.id] = item
        self.refresh()

    def refresh(self) -> None:
        node_items = self._node_items()
        for item in list(self.items.values()):
            try:
                members = [
                    node_items[node_id]
                    for node_id in item.node_ids
                    if node_id in node_items
                ]
                if not members:
                    item.setVisible(False)
                    continue
                rect = members[0].sceneBoundingRect()
                for member in members[1:]:
                    rect = rect.united(member.sceneBoundingRect())
                item.setVisible(True)
                item.set_group_rect(rect.adjusted(-18, -28, 18, 18))
            except RuntimeError:
                # A restore/new operation may destroy scene items between Qt
                # events; the next sync recreates authoritative overlays.
                continue

    def selected_group_ids(self) -> tuple[str, ...]:
        selected: list[str] = []
        for group_id, item in self.items.items():
            try:
                if item.isSelected():
                    selected.append(group_id)
            except RuntimeError:
                continue
        return tuple(sorted(selected))

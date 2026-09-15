from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QGraphicsView


class MiniMapView(QGraphicsView):
    """Read-only overview of the live experiment scene.

    Clicking recenters the primary canvas. The minimap shares the same graphics
    scene, so it introduces no second graph state or execution semantics.
    """

    def __init__(self, scene, primary_view, parent=None) -> None:
        super().__init__(scene, parent)
        self.primary_view = primary_view
        self.setInteractive(False)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumHeight(160)
        self._refresh_pending = False
        scene.changed.connect(self.schedule_refresh)
        self.schedule_refresh()

    def schedule_refresh(self, *_) -> None:
        if self._refresh_pending:
            return
        self._refresh_pending = True
        QTimer.singleShot(0, self.refresh)

    def refresh(self) -> None:
        self._refresh_pending = False
        rect = self.scene().itemsBoundingRect()
        if rect.isNull():
            self.resetTransform()
            return
        self.fitInView(rect.adjusted(-30, -30, 30, 30), Qt.KeepAspectRatio)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.schedule_refresh()

    def mousePressEvent(self, event) -> None:
        scene_pos = self.mapToScene(event.position().toPoint())
        self.primary_view.centerOn(scene_pos)
        event.accept()

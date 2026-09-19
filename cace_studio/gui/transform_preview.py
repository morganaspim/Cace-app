from __future__ import annotations

from hashlib import sha256
import math
from typing import Iterable, Sequence

try:
    from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QVariantAnimation, Qt
    from PySide6.QtGui import QBrush, QPainter, QPainterPath, QPen
    from PySide6.QtWidgets import (
        QGraphicsEllipseItem,
        QGraphicsLineItem,
        QGraphicsPathItem,
        QGraphicsScene,
        QGraphicsView,
        QLabel,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - GUI-only module
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc


def _as_points(values: Iterable[Sequence[float]]) -> tuple[tuple[float, float], ...]:
    points = []
    for value in values:
        if len(value) < 2:
            raise ValueError("animation points require at least two coordinates")
        x = float(value[0])
        y = float(value[1])
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("animation points must be finite")
        points.append((x, y))
    if not points:
        raise ValueError("animation requires at least one point")
    return tuple(points)


class CoordinateTransformPreview(QWidget):
    """Animated 2D coordinate preview.

    Scientific transform animations are driven by explicit module payloads.
    AI activity mode uses deterministic pseudo-coordinates and is labeled as
    decorative so it cannot be mistaken for measured/scientific geometry.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.caption = QLabel(
            "Transform Preview — presentation only; verification uses the original outputs."
        )
        self.caption.setWordWrap(True)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setMinimumHeight(260)

        layout = QVBoxLayout(self)
        layout.addWidget(self.caption)
        layout.addWidget(self.view)

        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(900)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._animation.valueChanged.connect(self._on_progress)

        self._source: tuple[tuple[float, float], ...] = ()
        self._target: tuple[tuple[float, float], ...] = ()
        self._point_items: list[QGraphicsEllipseItem] = []
        self._path_item: QGraphicsPathItem | None = None
        self._map_bounds = (-1.0, 1.0, -1.0, 1.0)
        self._closed = False

        self._draw_empty()

    def _draw_empty(self) -> None:
        self.scene.clear()
        self._point_items = []
        self._path_item = None
        self.scene.setSceneRect(QRectF(0, 0, 520, 320))
        self._draw_axes()

    def _draw_axes(self) -> None:
        rect = self.scene.sceneRect()
        pen = QPen(self.palette().mid().color())
        self.scene.addLine(rect.left(), rect.center().y(), rect.right(), rect.center().y(), pen)
        self.scene.addLine(rect.center().x(), rect.top(), rect.center().x(), rect.bottom(), pen)

    def _set_bounds(
        self,
        source: Sequence[tuple[float, float]],
        target: Sequence[tuple[float, float]],
    ) -> None:
        xs = [p[0] for p in source] + [p[0] for p in target]
        ys = [p[1] for p in source] + [p[1] for p in target]
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        if math.isclose(xmin, xmax):
            xmin -= 1.0
            xmax += 1.0
        if math.isclose(ymin, ymax):
            ymin -= 1.0
            ymax += 1.0
        xpad = 0.08 * (xmax - xmin)
        ypad = 0.08 * (ymax - ymin)
        self._map_bounds = (xmin - xpad, xmax + xpad, ymin - ypad, ymax + ypad)

    def _map_point(self, point: tuple[float, float]) -> QPointF:
        xmin, xmax, ymin, ymax = self._map_bounds
        rect = self.scene.sceneRect().adjusted(24, 18, -24, -18)
        x = rect.left() + (point[0] - xmin) / (xmax - xmin) * rect.width()
        y = rect.bottom() - (point[1] - ymin) / (ymax - ymin) * rect.height()
        return QPointF(x, y)

    @staticmethod
    def _interpolate(
        source: tuple[float, float],
        target: tuple[float, float],
        t: float,
    ) -> tuple[float, float]:
        return (
            source[0] + (target[0] - source[0]) * t,
            source[1] + (target[1] - source[1]) * t,
        )

    def animate_transform(
        self,
        source: Iterable[Sequence[float]],
        target: Iterable[Sequence[float]],
        *,
        title: str = "Coordinate transform",
        closed: bool = False,
        duration_ms: int = 900,
    ) -> None:
        source_points = _as_points(source)
        target_points = _as_points(target)
        if len(source_points) != len(target_points):
            raise ValueError("source and target animation point counts must match")

        self._animation.stop()
        self.scene.clear()
        self.scene.setSceneRect(QRectF(0, 0, 520, 320))
        self._source = source_points
        self._target = target_points
        self._closed = bool(closed)
        self._set_bounds(source_points, target_points)
        self._draw_axes()

        self._path_item = QGraphicsPathItem()
        self._path_item.setPen(QPen(self.palette().highlight().color(), 2))
        self.scene.addItem(self._path_item)

        self._point_items = []
        for point in source_points:
            mapped = self._map_point(point)
            item = QGraphicsEllipseItem(-3.5, -3.5, 7, 7)
            item.setBrush(QBrush(self.palette().highlight()))
            item.setPen(QPen(self.palette().highlight().color()))
            item.setPos(mapped)
            self.scene.addItem(item)
            self._point_items.append(item)

        self.caption.setText(
            f"{title} — animated preview only; exact outputs and verification are unchanged."
        )
        self._animation.setDuration(max(120, int(duration_ms)))
        self._on_progress(0.0)
        self._animation.start()

    def _on_progress(self, value) -> None:
        if not self._source or not self._target:
            return
        t = float(value)
        mapped_points = []
        for item, source, target in zip(self._point_items, self._source, self._target):
            point = self._interpolate(source, target, t)
            mapped = self._map_point(point)
            item.setPos(mapped)
            mapped_points.append(mapped)

        if self._path_item is not None and mapped_points:
            path = QPainterPath(mapped_points[0])
            for point in mapped_points[1:]:
                path.lineTo(point)
            if self._closed and len(mapped_points) > 2:
                path.lineTo(mapped_points[0])
            self._path_item.setPath(path)

    @staticmethod
    def _pseudo_point(label: str, axis: int) -> float:
        digest = sha256(f"{axis}:{label}".encode("utf-8")).digest()
        raw = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
        return 2.0 * raw - 1.0

    def animate_ai_walk(self, labels: Sequence[str], *, title: str = "AI working") -> None:
        clean = tuple(str(label) for label in labels if str(label))
        if not clean:
            clean = ("retrieve", "route", "combine", "evaluate")
        source = []
        target = []
        for index, label in enumerate(clean[:20]):
            angle = 2.0 * math.pi * index / max(1, len(clean))
            source.append((0.28 * math.cos(angle), 0.28 * math.sin(angle)))
            target.append(
                (
                    self._pseudo_point(label, 0),
                    self._pseudo_point(label, 1),
                )
            )
        self.animate_transform(
            source,
            target,
            title=(
                f"{title} — decorative semantic activity map; "
                "these are not scientific coordinates"
            ),
            closed=False,
            duration_ms=720,
        )

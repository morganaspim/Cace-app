from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .reproducibility import sha256_identity


_VIEW_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "ops" / "coordinate_views.json"


class GeometricAnimationError(ValueError):
    pass


@dataclass(frozen=True)
class GeometricPoint:
    coordinates: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.coordinates:
            raise ValueError("geometric point must contain at least one coordinate")
        for value in self.coordinates:
            if not isinstance(value, (int, float)):
                raise TypeError("geometric point coordinates must be numeric")

    def to_dict(self) -> dict[str, Any]:
        return {"coordinates": [float(value) for value in self.coordinates]}


@dataclass(frozen=True)
class GeometricActionEvent:
    event_id: str
    sequence: int
    action: str
    points: tuple[GeometricPoint, ...] = ()
    matrix: tuple[tuple[float, ...], ...] = ()
    translation: tuple[float, ...] = ()
    labels: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    source: str = "local-ai"
    duration_ms: int = 700
    easing: str = "ease-in-out"
    evidence_authority: bool = field(default=False, init=False)
    proof_effect: str = field(default="none", init=False)
    promotion_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not self.event_id or self.event_id != self.event_id.strip():
            raise ValueError("event_id must be non-empty canonical text")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        allowed_actions = {
            "select_point",
            "select_region",
            "highlight_relation",
            "translate",
            "rotate",
            "reflect",
            "affine_transform",
            "rotor_transform",
            "group_action",
            "random_walk_step",
            "morph",
        }
        if self.action not in allowed_actions:
            raise ValueError(f"unsupported geometric action: {self.action}")
        if self.duration_ms < 0 or self.duration_ms > 60_000:
            raise ValueError("duration_ms out of range")
        if not self.source:
            raise ValueError("source must be non-empty")
        if self.matrix:
            width = len(self.matrix[0])
            if width == 0 or any(len(row) != width for row in self.matrix):
                raise ValueError("matrix rows must have equal non-zero width")
        if self.translation and self.points:
            dim = len(self.points[0].coordinates)
            if len(self.translation) != dim:
                raise ValueError("translation dimension must match point dimension")

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "schema": "cace-geometric-action-semantic-v1",
            "event_id": self.event_id,
            "sequence": self.sequence,
            "action": self.action,
            "points": [point.to_dict() for point in self.points],
            "matrix": [list(row) for row in self.matrix],
            "translation": list(self.translation),
            "labels": list(self.labels),
            "metadata": dict(self.metadata),
            "source": self.source,
            "evidence_authority": False,
            "proof_effect": "none",
            "promotion_authority": False,
        }

    def semantic_sha256(self) -> str:
        return sha256_identity(self.semantic_payload())


class CoordinateViewRegistry:
    """Presentation-only coordinate-view registry.

    It deliberately does not perform scientific coordinate transforms. It routes
    canonical geometry to renderer contracts. Any transform that changes the
    mathematical experiment must be an explicit CACE module instead.
    """

    def __init__(self, path: str | Path = _VIEW_REGISTRY_PATH) -> None:
        self.path = Path(path)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema") != "cace-coordinate-view-registry-v1":
            raise GeometricAnimationError("unsupported coordinate-view registry")
        views = payload.get("views")
        if not isinstance(views, list):
            raise GeometricAnimationError("coordinate views must be an array")
        self._raw = payload
        self._views: dict[str, dict[str, Any]] = {}
        for item in views:
            if not isinstance(item, dict):
                raise GeometricAnimationError("coordinate view entry must be object")
            view_id = item.get("view_id")
            if not isinstance(view_id, str) or not view_id:
                raise GeometricAnimationError("coordinate view requires view_id")
            if view_id in self._views:
                raise GeometricAnimationError(f"duplicate coordinate view: {view_id}")
            dimension = item.get("dimension")
            if dimension != "any" and dimension not in {2, 3}:
                raise GeometricAnimationError(
                    f"coordinate view dimension must be 2, 3, or any: {view_id}"
                )
            self._views[view_id] = item

    @property
    def registry_sha256(self) -> str:
        return sha256_identity(self._raw)

    def view_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._views))

    def descriptor(self, view_id: str) -> dict[str, Any]:
        try:
            return dict(self._views[view_id])
        except KeyError as exc:
            raise GeometricAnimationError(f"unknown coordinate view: {view_id}") from exc

    def render_event(
        self,
        event: GeometricActionEvent,
        *,
        view_id: str,
    ) -> dict[str, Any]:
        descriptor = self.descriptor(view_id)
        view_dimension = descriptor["dimension"]
        if view_dimension != "any":
            for point in event.points:
                if len(point.coordinates) != view_dimension:
                    raise GeometricAnimationError(
                        f"event point dimension does not match view {view_id}"
                    )

        return {
            "schema": "cace-geometric-animation-event-v1",
            "event_id": event.event_id,
            "sequence": event.sequence,
            "action": event.action,
            "semantic_sha256": event.semantic_sha256(),
            "coordinate_view_id": view_id,
            "projection": descriptor["projection"],
            "view_family": descriptor["family"],
            "renderer_status": descriptor["renderer_status"],
            "canonical_points": [
                [float(value) for value in point.coordinates]
                for point in event.points
            ],
            "matrix": [list(row) for row in event.matrix],
            "translation": list(event.translation),
            "labels": list(event.labels),
            "metadata": dict(event.metadata),
            "duration_ms": event.duration_ms,
            "easing": event.easing,
            "presentation_only": True,
            "evidence_authority": False,
            "proof_effect": "none",
            "promotion_authority": False,
        }


def animation_stream(
    events: Sequence[GeometricActionEvent],
    *,
    view_id: str,
    registry: CoordinateViewRegistry | None = None,
) -> list[dict[str, Any]]:
    resolved = registry or CoordinateViewRegistry()
    previous = -1
    output: list[dict[str, Any]] = []
    for event in events:
        if event.sequence <= previous:
            raise GeometricAnimationError(
                "geometric animation event sequence must be strictly increasing"
            )
        previous = event.sequence
        output.append(resolved.render_event(event, view_id=view_id))
    return output

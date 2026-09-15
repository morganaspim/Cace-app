from __future__ import annotations

from copy import deepcopy

from .graph import Experiment


class ExperimentHistory:
    """Bounded snapshot history for GUI edits.

    Snapshots are ordinary Experiment values; history never changes execution or
    verification semantics.
    """

    def __init__(self, limit: int = 100) -> None:
        if limit < 1:
            raise ValueError("history limit must be positive")
        self.limit = limit
        self._undo: list[Experiment] = []
        self._redo: list[Experiment] = []

    @staticmethod
    def snapshot(experiment: Experiment) -> Experiment:
        return deepcopy(experiment)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def record(self, experiment: Experiment) -> None:
        self._undo.append(self.snapshot(experiment))
        if len(self._undo) > self.limit:
            del self._undo[: len(self._undo) - self.limit]
        self._redo.clear()

    def undo(self, current: Experiment) -> Experiment | None:
        if not self._undo:
            return None
        self._redo.append(self.snapshot(current))
        return self._undo.pop()

    def redo(self, current: Experiment) -> Experiment | None:
        if not self._redo:
            return None
        self._undo.append(self.snapshot(current))
        return self._redo.pop()

from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Callable

class TheoremStatus(str, Enum):
    MACHINE_CHECKED = 'machine-checked'
    REVIEWED_ASSUMED = 'reviewed-assumed'
    COMPUTATIONAL = 'computationally-discharged'
    OBLIGATION = 'obligation-only'

@dataclass(frozen=True)
class TheoremContract:
    theorem_id: str
    statement: str
    status: TheoremStatus
    assumptions: tuple[str, ...]
    evidence_kind: str
    checker: str | None = None
    artifact: str | None = None
    matcher: Callable[[dict[str, Any]], tuple[bool, list[str]]] | None = None

    def match(self, facts: dict[str, Any]) -> tuple[bool, list[str]]:
        if self.matcher is None:
            return False, ['theorem has no executable assumption matcher']
        return self.matcher(facts)

    def describe(self) -> dict[str, Any]:
        d = asdict(self); d.pop('matcher', None); return d

class TheoremRegistry:
    def __init__(self): self._items: dict[str, TheoremContract] = {}
    def register(self, theorem: TheoremContract) -> None:
        if theorem.theorem_id in self._items: raise ValueError(f'duplicate theorem id: {theorem.theorem_id}')
        self._items[theorem.theorem_id] = theorem
    def get(self, theorem_id: str) -> TheoremContract:
        if theorem_id not in self._items: raise KeyError(theorem_id)
        return self._items[theorem_id]
    def contains(self, theorem_id: str) -> bool: return theorem_id in self._items
    def list(self): return [self._items[k] for k in sorted(self._items)]

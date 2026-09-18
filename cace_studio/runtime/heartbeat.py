from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable

from .hashing import stable_hash


class HeartbeatMode(str, Enum):
    PERIODIC = "PERIODIC"
    EVENT = "EVENT"
    CONDITIONAL = "CONDITIONAL"
    BATCH = "BATCH"
    ON_DEMAND = "ON_DEMAND"


class CellState(str, Enum):
    UNKNOWN = "UNKNOWN"
    READY = "READY"
    RUNNING = "RUNNING"
    PASS = "PASS"
    QUALIFIED = "QUALIFIED"
    STALE = "STALE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    FAILED_NO_PROGRESS = "FAILED_NO_PROGRESS"
    KERNEL_PROVED = "KERNEL_PROVED"


_TERMINAL_VALID = {CellState.PASS, CellState.QUALIFIED, CellState.KERNEL_PROVED}


@dataclass(frozen=True)
class HeartbeatPolicy:
    mode: HeartbeatMode = HeartbeatMode.EVENT
    period_ticks: int | None = None
    batch_size: int | None = None
    condition_name: str | None = None
    stale_after_ticks: int | None = None

    def __post_init__(self) -> None:
        if self.mode is HeartbeatMode.PERIODIC:
            if self.period_ticks is None or self.period_ticks <= 0:
                raise ValueError("PERIODIC heartbeat requires positive period_ticks")
        if self.mode is HeartbeatMode.BATCH:
            if self.batch_size is None or self.batch_size <= 0:
                raise ValueError("BATCH heartbeat requires positive batch_size")
        if self.mode is HeartbeatMode.CONDITIONAL and not self.condition_name:
            raise ValueError("CONDITIONAL heartbeat requires condition_name")
        if self.stale_after_ticks is not None and self.stale_after_ticks <= 0:
            raise ValueError("stale_after_ticks must be positive")


@dataclass(frozen=True)
class HeartbeatEdge:
    source: str
    target: str
    transform_hash: str = "identity"
    unit_mapping: str = "identity"
    coordinate_mapping: str = "display-independent"
    evidence_policy: str = "no-promotion"
    error_bound: float | None = None
    stale_after_ticks: int | None = None
    backpressure_limit: int | None = None

    def __post_init__(self) -> None:
        if not self.source or not self.target or self.source == self.target:
            raise ValueError("edge requires distinct non-empty source and target")
        if self.error_bound is not None and self.error_bound < 0:
            raise ValueError("error_bound must be non-negative")
        if self.stale_after_ticks is not None and self.stale_after_ticks <= 0:
            raise ValueError("stale_after_ticks must be positive")
        if self.backpressure_limit is not None and self.backpressure_limit <= 0:
            raise ValueError("backpressure_limit must be positive")


@dataclass
class HeartbeatCell:
    cell_id: str
    policy: HeartbeatPolicy
    state: CellState = CellState.UNKNOWN
    generation: int = 0
    last_tick: int | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    evidence_ceiling: str = "ENGINEERING"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PropagationResult:
    source: str
    changed: bool
    stale_cells: tuple[str, ...]
    suppressed_by_equal_hash: bool


class HeartbeatScheduler:
    """Conway-inspired, multi-rate CACE execution control plane.

    The scheduler decides when a VALID computation may run. It never upgrades
    mathematical evidence. `evidence_ceiling` and edge evidence policy are
    descriptive guards only; formal status comes from the separate Lean path.
    """

    def __init__(
        self,
        *,
        master_seed: str,
        hash_algorithm: str = "sha256",
        max_propagation_generation: int = 10_000,
    ) -> None:
        if not master_seed:
            raise ValueError("master_seed must be non-empty")
        if max_propagation_generation <= 0:
            raise ValueError("max_propagation_generation must be positive")
        self.master_seed = master_seed
        self.hash_algorithm = hash_algorithm
        self.max_propagation_generation = max_propagation_generation
        self.cells: dict[str, HeartbeatCell] = {}
        self.edges: list[HeartbeatEdge] = []
        self._outgoing: dict[str, list[HeartbeatEdge]] = defaultdict(list)
        self._incoming: dict[str, list[HeartbeatEdge]] = defaultdict(list)
        self._event_queue: deque[str] = deque()
        self._batch_counts: dict[str, int] = defaultdict(int)

    def add_cell(self, cell: HeartbeatCell) -> None:
        if not cell.cell_id or cell.cell_id in self.cells:
            raise ValueError(f"duplicate/empty heartbeat cell id: {cell.cell_id!r}")
        self.cells[cell.cell_id] = cell

    def add_edge(self, edge: HeartbeatEdge) -> None:
        if edge.source not in self.cells or edge.target not in self.cells:
            raise ValueError("heartbeat edge references unknown cell")
        if any(e.source == edge.source and e.target == edge.target for e in self.edges):
            raise ValueError("duplicate heartbeat edge")
        self.edges.append(edge)
        self._outgoing[edge.source].append(edge)
        self._incoming[edge.target].append(edge)

    def assert_acyclic(self) -> None:
        indegree = {cell_id: len(self._incoming[cell_id]) for cell_id in self.cells}
        queue = deque(sorted(cell_id for cell_id, degree in indegree.items() if degree == 0))
        seen = 0
        while queue:
            current = queue.popleft()
            seen += 1
            for edge in sorted(self._outgoing[current], key=lambda item: item.target):
                indegree[edge.target] -= 1
                if indegree[edge.target] == 0:
                    queue.append(edge.target)
        if seen != len(self.cells):
            raise ValueError("heartbeat dependency graph contains a cycle")

    def seed_for(self, cell_id: str, *, generation: int, input_hash: str = "") -> str:
        if cell_id not in self.cells:
            raise KeyError(cell_id)
        payload = {
            "schema": "cace-cell-seed-v1",
            "master_seed": self.master_seed,
            "cell_id": cell_id,
            "generation": generation,
            "input_hash": input_hash,
        }
        return stable_hash(payload, algorithm=self.hash_algorithm)

    def set_state(self, cell_id: str, state: CellState, *, tick: int | None = None) -> None:
        cell = self.cells[cell_id]
        cell.state = state
        if tick is not None:
            cell.last_tick = tick

    def dependencies_valid(self, cell_id: str) -> bool:
        return all(self.cells[edge.source].state in _TERMINAL_VALID for edge in self._incoming[cell_id])

    def note_event(self, source_cell_id: str) -> None:
        if source_cell_id not in self.cells:
            raise KeyError(source_cell_id)
        self._event_queue.append(source_cell_id)
        for edge in self._outgoing[source_cell_id]:
            target = self.cells[edge.target]
            if target.policy.mode is HeartbeatMode.BATCH:
                self._batch_counts[target.cell_id] += 1

    def mark_output(
        self,
        cell_id: str,
        value: Any,
        *,
        tick: int,
        evidence_state: CellState = CellState.PASS,
    ) -> PropagationResult:
        cell = self.cells[cell_id]
        new_hash = stable_hash(value, algorithm=self.hash_algorithm)
        old_hash = cell.output_hash
        cell.output_hash = new_hash
        cell.last_tick = tick
        cell.state = evidence_state

        if old_hash == new_hash:
            return PropagationResult(cell_id, False, (), True)

        cell.generation += 1
        if cell.generation > self.max_propagation_generation:
            cell.state = CellState.FAILED_NO_PROGRESS
            raise RuntimeError("maximum heartbeat propagation generation exceeded")

        stale = self._mark_downstream_stale(cell_id)
        self.note_event(cell_id)
        return PropagationResult(cell_id, True, stale, False)

    def _mark_downstream_stale(self, source: str) -> tuple[str, ...]:
        queue = deque(edge.target for edge in self._outgoing[source])
        visited: set[str] = set()
        while queue:
            cell_id = queue.popleft()
            if cell_id in visited:
                continue
            visited.add(cell_id)
            target = self.cells[cell_id]
            if target.state not in {CellState.RUNNING, CellState.FAILED}:
                target.state = CellState.STALE
            queue.extend(edge.target for edge in self._outgoing[cell_id])
        return tuple(sorted(visited))

    def due_cells(
        self,
        *,
        tick: int,
        conditions: dict[str, bool] | None = None,
        on_demand_authorizations: Iterable[str] = (),
    ) -> tuple[str, ...]:
        if tick < 0:
            raise ValueError("tick must be non-negative")
        conditions = conditions or {}
        authorized = set(on_demand_authorizations)
        event_sources = set(self._event_queue)
        self._event_queue.clear()

        candidates: list[str] = []
        for cell_id, cell in sorted(self.cells.items()):
            policy = cell.policy
            due = False
            if policy.mode is HeartbeatMode.PERIODIC:
                due = tick % int(policy.period_ticks or 1) == 0
            elif policy.mode is HeartbeatMode.EVENT:
                due = any(edge.source in event_sources for edge in self._incoming[cell_id])
            elif policy.mode is HeartbeatMode.CONDITIONAL:
                due = bool(conditions.get(policy.condition_name or "", False))
            elif policy.mode is HeartbeatMode.BATCH:
                due = self._batch_counts[cell_id] >= int(policy.batch_size or 1)
            elif policy.mode is HeartbeatMode.ON_DEMAND:
                due = cell_id in authorized

            if due and self.dependencies_valid(cell_id):
                candidates.append(cell_id)
                if policy.mode is HeartbeatMode.BATCH:
                    self._batch_counts[cell_id] = 0
        return tuple(candidates)

    def mark_stale_by_timeout(self, *, tick: int) -> tuple[str, ...]:
        stale: list[str] = []
        for cell_id, cell in self.cells.items():
            timeout = cell.policy.stale_after_ticks
            if timeout is None or cell.last_tick is None:
                continue
            if tick - cell.last_tick >= timeout and cell.state in _TERMINAL_VALID:
                cell.state = CellState.STALE
                stale.append(cell_id)
        return tuple(sorted(stale))

    @classmethod
    def from_experiment(
        cls,
        experiment: Any,
        *,
        master_seed: str,
        default_policy: HeartbeatPolicy | None = None,
        hash_algorithm: str = "sha256",
    ) -> "HeartbeatScheduler":
        """Create one runtime heartbeat cell per canvas graph node.

        Canvas position is intentionally ignored; only graph dependency identity is
        imported. This is the bridge from the visual canvas to the control plane.
        """
        scheduler = cls(master_seed=master_seed, hash_algorithm=hash_algorithm)
        policy = default_policy or HeartbeatPolicy(HeartbeatMode.EVENT)
        for node in experiment.nodes:
            scheduler.add_cell(HeartbeatCell(cell_id=node.id, policy=policy, state=CellState.READY))
        seen: set[tuple[str, str]] = set()
        for edge in experiment.edges:
            key = (edge.source_node, edge.target_node)
            if key in seen:
                continue
            seen.add(key)
            scheduler.add_edge(HeartbeatEdge(source=edge.source_node, target=edge.target_node))
        return scheduler

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any, Iterable, Mapping, Sequence

from .graph import Experiment
from .verification import VerificationRecord, VerificationState


class HeartbeatState(str, Enum):
    DORMANT = "dormant"
    READY = "ready"
    ACTIVE = "active"
    WAITING = "waiting"
    BLOCKED = "blocked"
    STALE = "stale"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    RESEARCH_INTEREST = "research-interest"


@dataclass(frozen=True)
class AIHeartbeatUpdate:
    """Non-authoritative AI attention update.

    This intentionally has no verification/state mutation field.
    """

    node_id: str
    interest_delta: float = 0.0
    note: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.node_id, str) or not self.node_id.strip():
            raise ValueError("AI heartbeat node_id must be non-empty")
        if not isfinite(float(self.interest_delta)):
            raise ValueError("AI heartbeat interest_delta must be finite")


@dataclass(frozen=True)
class NodeHeartbeat:
    node_id: str
    state: HeartbeatState
    tick: int
    semantic_hash: str = ""
    research_interest: float = 0.0
    inputs_ready: bool = False
    outputs_ready: bool = False
    error_family: str = ""
    verification_summary: str = "not-run"

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "tick": self.tick,
            "semantic_hash": self.semantic_hash,
            "research_interest": self.research_interest,
            "inputs_ready": self.inputs_ready,
            "outputs_ready": self.outputs_ready,
            "error_family": self.error_family,
            "verification_summary": self.verification_summary,
        }


@dataclass(frozen=True)
class HeartbeatDeltaItem:
    node_id: str
    previous_state: str | None
    state: str
    semantic_hash_changed: bool
    interest_delta: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "previous_state": self.previous_state,
            "state": self.state,
            "semantic_hash_changed": self.semantic_hash_changed,
            "interest_delta": self.interest_delta,
        }


@dataclass(frozen=True)
class HeartbeatDelta:
    from_tick: int | None
    to_tick: int
    changed: tuple[HeartbeatDeltaItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_tick": self.from_tick,
            "to_tick": self.to_tick,
            "changed": [item.to_dict() for item in self.changed],
        }


@dataclass(frozen=True)
class HeartbeatFrame:
    tick: int
    nodes: tuple[NodeHeartbeat, ...]

    def by_id(self) -> dict[str, NodeHeartbeat]:
        return {node.node_id: node for node in self.nodes}

    def delta(self, previous: "HeartbeatFrame | None" = None) -> HeartbeatDelta:
        current = self.by_id()
        prior = previous.by_id() if previous is not None else {}
        changed: list[HeartbeatDeltaItem] = []
        for node_id in sorted(set(current) | set(prior)):
            now = current.get(node_id)
            before = prior.get(node_id)
            if now is None:
                continue
            hash_changed = before is not None and before.semantic_hash != now.semantic_hash
            interest_delta = now.research_interest - (
                before.research_interest if before is not None else 0.0
            )
            state_changed = before is None or before.state is not now.state
            if state_changed or hash_changed or abs(interest_delta) > 1e-12:
                changed.append(
                    HeartbeatDeltaItem(
                        node_id=node_id,
                        previous_state=before.state.value if before is not None else None,
                        state=now.state.value,
                        semantic_hash_changed=hash_changed,
                        interest_delta=interest_delta,
                    )
                )
        return HeartbeatDelta(
            from_tick=previous.tick if previous is not None else None,
            to_tick=self.tick,
            changed=tuple(changed),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cace.canvas-heartbeat.v1",
            "role": "coordination/visualization metadata only; never verification evidence",
            "tick": self.tick,
            "nodes": [node.to_dict() for node in self.nodes],
        }


def _verification_summary(records: Sequence[VerificationRecord]) -> tuple[str, bool, bool]:
    """Return summary, all-pass, any-fail.

    NOT_RUN is never promoted to pass.
    """
    if not records:
        return "not-run", False, False
    any_fail = any(record.state is VerificationState.FAIL for record in records)
    all_pass = bool(records) and all(
        record.state is VerificationState.PASS for record in records
    )
    if any_fail:
        return "fail", False, True
    if all_pass:
        return "pass", True, False
    return "not-run", False, False


def _dependencies(experiment: Experiment) -> dict[str, set[str]]:
    node_ids = {node.id for node in experiment.nodes}
    deps = {node_id: set() for node_id in node_ids}
    for edge in experiment.edges:
        if edge.source_node in node_ids and edge.target_node in node_ids:
            deps[edge.target_node].add(edge.source_node)
    return deps


class CanvasHeartbeatEngine:
    """Deterministic dependency-aware heartbeat for canvas/AI coordination.

    VERIFIED can only be derived from supplied CACE VerificationRecord objects.
    AIHeartbeatUpdate can change research-interest metadata only.
    """

    def __init__(self) -> None:
        self._frame: HeartbeatFrame | None = None

    @property
    def frame(self) -> HeartbeatFrame | None:
        return self._frame

    def advance(
        self,
        experiment: Experiment,
        *,
        semantic_hashes: Mapping[str, str] | None = None,
        verification: Mapping[str, Sequence[VerificationRecord]] | None = None,
        active_nodes: Iterable[str] = (),
        verifying_nodes: Iterable[str] = (),
        inputs_ready_nodes: Iterable[str] | None = None,
        outputs_ready_nodes: Iterable[str] = (),
        error_families: Mapping[str, str] | None = None,
        ai_updates: Sequence[AIHeartbeatUpdate] = (),
    ) -> HeartbeatFrame:
        semantic_hashes = dict(semantic_hashes or {})
        verification = dict(verification or {})
        error_families = dict(error_families or {})
        node_ids = {node.id for node in experiment.nodes}
        active = set(active_nodes)
        verifying = set(verifying_nodes)
        outputs_ready = set(outputs_ready_nodes)
        inputs_ready = (
            None if inputs_ready_nodes is None else set(inputs_ready_nodes)
        )

        unknown_sets = {
            "active_nodes": active - node_ids,
            "verifying_nodes": verifying - node_ids,
            "outputs_ready_nodes": outputs_ready - node_ids,
        }
        if inputs_ready is not None:
            unknown_sets["inputs_ready_nodes"] = inputs_ready - node_ids
        unknown_sets["semantic_hashes"] = set(semantic_hashes) - node_ids
        unknown_sets["verification"] = set(verification) - node_ids
        unknown_sets["error_families"] = set(error_families) - node_ids
        bad = {name: sorted(values) for name, values in unknown_sets.items() if values}
        if bad:
            raise ValueError(f"heartbeat inputs reference unknown nodes: {bad}")

        previous = self._frame.by_id() if self._frame is not None else {}
        tick = 0 if self._frame is None else self._frame.tick + 1
        deps = _dependencies(experiment)

        interest = {
            node_id: previous.get(
                node_id,
                NodeHeartbeat(node_id, HeartbeatState.DORMANT, tick),
            ).research_interest
            for node_id in node_ids
        }
        for update in ai_updates:
            if update.node_id not in node_ids:
                raise ValueError(
                    f"AI heartbeat update references unknown node: {update.node_id}"
                )
            interest[update.node_id] = min(
                1.0,
                max(0.0, interest[update.node_id] + float(update.interest_delta)),
            )

        state: dict[str, HeartbeatState] = {}
        summaries: dict[str, str] = {}
        changed_hash: set[str] = set()

        for node_id in node_ids:
            records = tuple(verification.get(node_id, ()))
            if any(not isinstance(record, VerificationRecord) for record in records):
                raise TypeError(
                    "heartbeat verification inputs must be VerificationRecord objects"
                )
            summary, all_pass, any_fail = _verification_summary(records)
            summaries[node_id] = summary

            current_hash = semantic_hashes.get(node_id, "")
            old = previous.get(node_id)
            if old is not None and old.semantic_hash != current_hash:
                changed_hash.add(node_id)

            if node_id in changed_hash:
                state[node_id] = HeartbeatState.STALE
            elif any_fail:
                state[node_id] = HeartbeatState.FAILED
            elif all_pass:
                state[node_id] = HeartbeatState.VERIFIED
            elif node_id in verifying:
                state[node_id] = HeartbeatState.VERIFYING
            elif node_id in active:
                state[node_id] = HeartbeatState.ACTIVE
            else:
                ready_here = (
                    node_id in inputs_ready
                    if inputs_ready is not None
                    else not deps[node_id]
                )
                state[node_id] = (
                    HeartbeatState.READY if ready_here else HeartbeatState.WAITING
                )

        for _ in range(max(1, len(node_ids) + 1)):
            changed = False
            for node_id in sorted(node_ids):
                if state[node_id] in {HeartbeatState.FAILED, HeartbeatState.STALE}:
                    continue
                parent_states = [state[parent] for parent in deps[node_id]]
                next_state = state[node_id]
                if any(parent is HeartbeatState.STALE for parent in parent_states):
                    next_state = HeartbeatState.STALE
                elif any(
                    parent in {HeartbeatState.FAILED, HeartbeatState.BLOCKED}
                    for parent in parent_states
                ):
                    next_state = HeartbeatState.BLOCKED
                elif (
                    next_state in {HeartbeatState.WAITING, HeartbeatState.DORMANT}
                    and deps[node_id]
                    and all(parent is HeartbeatState.VERIFIED for parent in parent_states)
                ):
                    ready_here = (
                        True if inputs_ready is None else node_id in inputs_ready
                    )
                    if ready_here:
                        next_state = HeartbeatState.READY
                if next_state is not state[node_id]:
                    state[node_id] = next_state
                    changed = True
            if not changed:
                break

        nodes = []
        for node in sorted(experiment.nodes, key=lambda item: item.id):
            node_id = node.id
            nodes.append(
                NodeHeartbeat(
                    node_id=node_id,
                    state=state[node_id],
                    tick=tick,
                    semantic_hash=semantic_hashes.get(node_id, ""),
                    research_interest=interest[node_id],
                    inputs_ready=(
                        node_id in inputs_ready
                        if inputs_ready is not None
                        else (not deps[node_id] or all(
                            state[parent] is HeartbeatState.VERIFIED
                            for parent in deps[node_id]
                        ))
                    ),
                    outputs_ready=node_id in outputs_ready,
                    error_family=str(error_families.get(node_id, "")),
                    verification_summary=summaries[node_id],
                )
            )

        self._frame = HeartbeatFrame(tick=tick, nodes=tuple(nodes))
        return self._frame

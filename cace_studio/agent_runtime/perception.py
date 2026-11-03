from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Callable, Iterable, Mapping

from cace_studio.core.executor import RunResult
from cace_studio.core.graph import Experiment
from cace_studio.core.reproducibility import experiment_fingerprint, sha256_identity
from cace_studio.core.verification import VerificationRecord, VerificationState


class AgentNetworkMode(str, Enum):
    LOCAL_ZERO_CONTACT = "LOCAL_ZERO_CONTACT"
    HYBRID = "HYBRID"
    GENERAL_AGENT = "GENERAL_AGENT"


class CanonicalEvidenceState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class PerceptionHeartbeatState(str, Enum):
    DORMANT = "DORMANT"
    READY = "READY"
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    STALE = "STALE"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    RESEARCH_INTEREST = "RESEARCH_INTEREST"


class ResidualTrend(str, Enum):
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    WORSENING = "WORSENING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class NodePerception:
    node_id: str
    semantic_hash: str
    heartbeat_state: PerceptionHeartbeatState
    changed: bool
    residual_norm: float | None
    residual_trend: ResidualTrend
    convergence_progress: float | None
    resource_pressure: float
    research_interest: float
    blocker_refs: tuple[str, ...]
    canonical_evidence_state: CanonicalEvidenceState
    artifact_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "semantic_hash": self.semantic_hash,
            "heartbeat_state": self.heartbeat_state.value,
            "changed": self.changed,
            "residual_norm": self.residual_norm,
            "residual_trend": self.residual_trend.value,
            "convergence_progress": self.convergence_progress,
            "resource_pressure": self.resource_pressure,
            "research_interest": self.research_interest,
            "blocker_refs": list(self.blocker_refs),
            "canonical_evidence_state": self.canonical_evidence_state.value,
            "artifact_refs": list(self.artifact_refs),
        }


@dataclass(frozen=True)
class AgentPerceptionPacket:
    run_id: str
    experiment_id: str
    monotonic_seq: int
    semantic_graph_hash: str
    emitted_at: str
    network_mode: AgentNetworkMode
    nodes: tuple[NodePerception, ...]
    evidence_authority: bool = False

    def __post_init__(self) -> None:
        if not self.run_id or not self.experiment_id:
            raise ValueError("perception run_id and experiment_id must be non-empty")
        if self.monotonic_seq < 0:
            raise ValueError("perception monotonic_seq must be non-negative")
        if self.evidence_authority:
            raise ValueError("agent perception cannot have evidence authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "cace-agent-perception-v1",
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "monotonic_seq": self.monotonic_seq,
            "semantic_graph_hash": self.semantic_graph_hash,
            "emitted_at": self.emitted_at,
            "network_mode": self.network_mode.value,
            "nodes": [node.to_dict() for node in self.nodes],
            "evidence_authority": False,
        }

    def by_id(self) -> dict[str, NodePerception]:
        return {node.node_id: node for node in self.nodes}


def _finite_unit_interval(value: float, *, name: str) -> float:
    result = float(value)
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be finite and in [0,1]")
    return result


def _residual_value(value: float | None, *, node_id: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not isfinite(result) or result < 0.0:
        raise ValueError(f"residual_norm for {node_id!r} must be finite and non-negative")
    return result


def _node_semantic_hash(experiment: Experiment, node_id: str) -> str:
    nodes = experiment.node_map()
    node = nodes[node_id]
    incident = []
    for edge in experiment.edges:
        if edge.source_node == node_id or edge.target_node == node_id:
            incident.append(
                {
                    "source_node": edge.source_node,
                    "source_port": edge.source_port,
                    "target_node": edge.target_node,
                    "target_port": edge.target_port,
                }
            )
    incident.sort(
        key=lambda item: (
            item["source_node"],
            item["source_port"],
            item["target_node"],
            item["target_port"],
        )
    )
    return sha256_identity(
        {
            "node_id": node.id,
            "module_id": node.module_id,
            "params": node.params,
            "incident_edges": incident,
        }
    )


def _canonical_evidence_state(
    records: Iterable[VerificationRecord], *, stale: bool
) -> CanonicalEvidenceState:
    if stale:
        return CanonicalEvidenceState.STALE
    values = tuple(records)
    if any(not isinstance(record, VerificationRecord) for record in values):
        raise TypeError("perception verification inputs must be VerificationRecord objects")
    if not values:
        return CanonicalEvidenceState.NOT_RUN
    if any(record.state is VerificationState.FAIL for record in values):
        return CanonicalEvidenceState.FAIL
    if all(record.state is VerificationState.PASS for record in values):
        return CanonicalEvidenceState.PASS
    return CanonicalEvidenceState.NOT_RUN


def _residual_trend(current: float | None, previous: float | None) -> ResidualTrend:
    if current is None or previous is None:
        return ResidualTrend.UNKNOWN
    tolerance = max(1e-12, abs(previous) * 1e-9)
    if current < previous - tolerance:
        return ResidualTrend.IMPROVING
    if current > previous + tolerance:
        return ResidualTrend.WORSENING
    return ResidualTrend.STABLE


class AgentPerceptionTracker:
    """Build schema-compatible, non-evidentiary local-agent perception packets.

    Canonical evidence state is derived only from real ``VerificationRecord``
    objects carried by a real ``RunResult``. The tracker may summarize or mark
    those records stale, but it has no mechanism for creating verification.
    """

    def __init__(
        self,
        *,
        network_mode: AgentNetworkMode = AgentNetworkMode.LOCAL_ZERO_CONTACT,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.network_mode = network_mode
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._next_seq = 0
        self._previous: AgentPerceptionPacket | None = None

    @property
    def previous(self) -> AgentPerceptionPacket | None:
        return self._previous

    def snapshot(
        self,
        experiment: Experiment,
        *,
        run_result: RunResult | None = None,
        active_node_ids: Iterable[str] = (),
        verifying_node_ids: Iterable[str] = (),
        residual_norms: Mapping[str, float | None] | None = None,
        convergence_progress: Mapping[str, float | None] | None = None,
        resource_pressure: Mapping[str, float] | None = None,
        research_interest: Mapping[str, float] | None = None,
    ) -> AgentPerceptionPacket:
        if not isinstance(experiment, Experiment):
            raise TypeError("perception experiment must be an Experiment")
        if run_result is not None and not isinstance(run_result, RunResult):
            raise TypeError("perception run_result must be a RunResult")

        node_ids = {node.id for node in experiment.nodes}
        if len(node_ids) != len(experiment.nodes):
            raise ValueError("perception experiment contains duplicate node ids")

        active = set(active_node_ids)
        verifying = set(verifying_node_ids)
        residuals = dict(residual_norms or {})
        progress = dict(convergence_progress or {})
        pressure = dict(resource_pressure or {})
        interest = dict(research_interest or {})
        referenced = {
            "active_node_ids": active,
            "verifying_node_ids": verifying,
            "residual_norms": set(residuals),
            "convergence_progress": set(progress),
            "resource_pressure": set(pressure),
            "research_interest": set(interest),
        }
        if run_result is not None:
            referenced["run_result.verification"] = set(run_result.verification)
            referenced["run_result.outputs"] = set(run_result.outputs)
        unknown = {
            name: sorted(values - node_ids)
            for name, values in referenced.items()
            if values - node_ids
        }
        if unknown:
            raise ValueError(f"perception inputs reference unknown nodes: {unknown}")

        semantic_graph_hash = experiment_fingerprint(experiment, include_layout=False)
        run_source_hash = ""
        if run_result is not None:
            run_source_hash = (
                run_result.source_semantic_experiment_sha256
                or run_result.semantic_experiment_sha256
            )
        run_stale = bool(run_result is not None and run_source_hash != semantic_graph_hash)

        semantic_hashes = {
            node_id: _node_semantic_hash(experiment, node_id)
            for node_id in sorted(node_ids)
        }
        evidence = {
            node_id: _canonical_evidence_state(
                run_result.verification.get(node_id, ()) if run_result is not None else (),
                stale=run_stale,
            )
            for node_id in sorted(node_ids)
        }

        upstream: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
        for edge in experiment.edges:
            if edge.source_node not in node_ids or edge.target_node not in node_ids:
                raise ValueError("perception experiment edge references missing node")
            upstream[edge.target_node].add(edge.source_node)

        previous = self._previous.by_id() if self._previous is not None else {}
        nodes: list[NodePerception] = []
        for node_id in sorted(node_ids):
            residual = _residual_value(residuals.get(node_id), node_id=node_id)
            previous_residual = (
                previous[node_id].residual_norm if node_id in previous else None
            )
            convergence = progress.get(node_id)
            if convergence is not None:
                convergence = _finite_unit_interval(
                    convergence, name=f"convergence_progress[{node_id!r}]"
                )
            node_pressure = _finite_unit_interval(
                pressure.get(node_id, 0.0), name=f"resource_pressure[{node_id!r}]"
            )
            node_interest = _finite_unit_interval(
                interest.get(node_id, 0.0), name=f"research_interest[{node_id!r}]"
            )
            blockers = tuple(
                sorted(
                    parent
                    for parent in upstream[node_id]
                    if evidence[parent]
                    in {CanonicalEvidenceState.FAIL, CanonicalEvidenceState.STALE}
                )
            )
            canonical = evidence[node_id]
            if canonical is CanonicalEvidenceState.STALE:
                heartbeat = PerceptionHeartbeatState.STALE
            elif canonical is CanonicalEvidenceState.FAIL:
                heartbeat = PerceptionHeartbeatState.FAILED
            elif node_id in verifying:
                heartbeat = PerceptionHeartbeatState.VERIFYING
            elif node_id in active:
                heartbeat = PerceptionHeartbeatState.ACTIVE
            elif canonical is CanonicalEvidenceState.PASS:
                heartbeat = PerceptionHeartbeatState.VERIFIED
            elif blockers:
                heartbeat = PerceptionHeartbeatState.BLOCKED
            else:
                heartbeat = PerceptionHeartbeatState.DORMANT

            old = previous.get(node_id)
            changed = old is None or old.semantic_hash != semantic_hashes[node_id]
            nodes.append(
                NodePerception(
                    node_id=node_id,
                    semantic_hash=semantic_hashes[node_id],
                    heartbeat_state=heartbeat,
                    changed=changed,
                    residual_norm=residual,
                    residual_trend=_residual_trend(residual, previous_residual),
                    convergence_progress=convergence,
                    resource_pressure=node_pressure,
                    research_interest=node_interest,
                    blocker_refs=blockers,
                    canonical_evidence_state=canonical,
                )
            )

        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError("perception clock must return a timezone-aware datetime")
        packet = AgentPerceptionPacket(
            run_id=run_result.run_id if run_result is not None else "NOT_RUN",
            experiment_id=semantic_graph_hash,
            monotonic_seq=self._next_seq,
            semantic_graph_hash=semantic_graph_hash,
            emitted_at=now.isoformat(),
            network_mode=self.network_mode,
            nodes=tuple(nodes),
        )
        self._previous = packet
        self._next_seq += 1
        return packet

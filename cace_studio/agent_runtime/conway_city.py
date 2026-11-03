from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Iterable

from cace_studio.core.reproducibility import sha256_identity

from .perception import (
    AgentNetworkMode,
    AgentPerceptionPacket,
    PerceptionHeartbeatState,
)


class ConwayCityError(ValueError):
    pass


def _unit(value: float, name: str) -> float:
    out = float(value)
    if not isfinite(out) or not 0.0 <= out <= 1.0:
        raise ConwayCityError(f"{name} must be finite and in [0,1]")
    return out


@dataclass(frozen=True)
class WorkspaceResourceState:
    compute_supply: float
    compute_demand: float
    bandwidth_pressure: float = 0.0
    latency_pressure: float = 0.0
    cache_pressure: float = 0.0
    uncertainty_budget_pressure: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "compute_supply",
            "compute_demand",
            "bandwidth_pressure",
            "latency_pressure",
            "cache_pressure",
            "uncertainty_budget_pressure",
        ):
            _unit(getattr(self, name), name)

    @property
    def spare_compute(self) -> float:
        return max(0.0, self.compute_supply - self.compute_demand)

    @property
    def unmet_compute(self) -> float:
        return max(0.0, self.compute_demand - self.compute_supply)

    def to_dict(self) -> dict[str, float]:
        return {
            "compute_supply": float(self.compute_supply),
            "compute_demand": float(self.compute_demand),
            "spare_compute": self.spare_compute,
            "unmet_compute": self.unmet_compute,
            "bandwidth_pressure": float(self.bandwidth_pressure),
            "latency_pressure": float(self.latency_pressure),
            "cache_pressure": float(self.cache_pressure),
            "uncertainty_budget_pressure": float(self.uncertainty_budget_pressure),
        }


@dataclass(frozen=True)
class WorkspaceHeartbeatEnvelope:
    workspace_id: str
    collaboration_link_id: str
    perception: AgentPerceptionPacket
    resources: WorkspaceResourceState
    member_role: str = "editor"

    def __post_init__(self) -> None:
        if not self.workspace_id or not self.collaboration_link_id:
            raise ConwayCityError("workspace_id and collaboration_link_id are required")
        if self.member_role not in {"viewer", "editor", "owner"}:
            raise ConwayCityError("unsupported collaboration role")
        if self.perception.network_mode is AgentNetworkMode.LOCAL_ZERO_CONTACT:
            raise ConwayCityError(
                "federated heartbeat requires an explicitly connected network mode"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "collaboration_link_id": self.collaboration_link_id,
            "member_role": self.member_role,
            "perception": self.perception.to_dict(),
            "resources": self.resources.to_dict(),
            "evidence_authority": False,
            "proof_effect": "none",
            "promotion_authority": False,
        }


@dataclass
class _CityCell:
    envelope: WorkspaceHeartbeatEnvelope
    scheduler_credits: float = 0.0


@dataclass
class ConwayEconomicCity:
    """Federated heartbeat/resource visualization for explicitly linked workspaces.

    Scheduler credits are non-monetary internal simulation units. They may be used
    to prioritize valid work, never to buy evidence, proof status, permissions,
    subscriptions, cryptocurrency, or external resources.
    """

    collaboration_link_id: str
    member_workspace_ids: frozenset[str]
    max_scheduler_credits: float = 100.0
    spare_compute_credit_rate: float = 5.0
    _cells: dict[str, _CityCell] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.collaboration_link_id:
            raise ConwayCityError("collaboration_link_id must be non-empty")
        if len(self.member_workspace_ids) < 2:
            raise ConwayCityError("Conway city requires at least two linked workspaces")
        if any(not workspace_id for workspace_id in self.member_workspace_ids):
            raise ConwayCityError("workspace ids must be non-empty")
        if self.max_scheduler_credits <= 0 or self.spare_compute_credit_rate < 0:
            raise ConwayCityError("invalid scheduler credit configuration")

    def ingest(self, envelope: WorkspaceHeartbeatEnvelope) -> None:
        if envelope.collaboration_link_id != self.collaboration_link_id:
            raise ConwayCityError("heartbeat belongs to a different collaboration link")
        if envelope.workspace_id not in self.member_workspace_ids:
            raise ConwayCityError("workspace is not a member of this collaboration link")

        current = self._cells.get(envelope.workspace_id)
        if (
            current is not None
            and envelope.perception.monotonic_seq
            <= current.envelope.perception.monotonic_seq
        ):
            raise ConwayCityError("workspace heartbeat sequence must increase")

        credits = current.scheduler_credits if current is not None else 0.0
        credits = min(
            self.max_scheduler_credits,
            credits + envelope.resources.spare_compute * self.spare_compute_credit_rate,
        )
        self._cells[envelope.workspace_id] = _CityCell(
            envelope=envelope,
            scheduler_credits=credits,
        )

    @property
    def active(self) -> bool:
        return len(self._cells) >= 2

    @staticmethod
    def _dominant_heartbeat(packet: AgentPerceptionPacket) -> str:
        priority = (
            PerceptionHeartbeatState.FAILED,
            PerceptionHeartbeatState.STALE,
            PerceptionHeartbeatState.BLOCKED,
            PerceptionHeartbeatState.VERIFYING,
            PerceptionHeartbeatState.ACTIVE,
            PerceptionHeartbeatState.RESEARCH_INTEREST,
            PerceptionHeartbeatState.WAITING,
            PerceptionHeartbeatState.READY,
            PerceptionHeartbeatState.VERIFIED,
            PerceptionHeartbeatState.DORMANT,
        )
        states = {node.heartbeat_state for node in packet.nodes}
        for state in priority:
            if state in states:
                return state.value
        return PerceptionHeartbeatState.DORMANT.value

    def snapshot(self) -> dict[str, Any]:
        cells = []
        total_unmet = 0.0
        for workspace_id in sorted(self._cells):
            cell = self._cells[workspace_id]
            envelope = cell.envelope
            total_unmet += envelope.resources.unmet_compute
            cells.append(
                {
                    "workspace_id": workspace_id,
                    "heartbeat_state": self._dominant_heartbeat(envelope.perception),
                    "semantic_graph_hash": envelope.perception.semantic_graph_hash,
                    "monotonic_seq": envelope.perception.monotonic_seq,
                    "research_interest": max(
                        (node.research_interest for node in envelope.perception.nodes),
                        default=0.0,
                    ),
                    "resources": envelope.resources.to_dict(),
                    "scheduler_credits": cell.scheduler_credits,
                    "scheduler_credits_are_money": False,
                    "canonical_evidence_mirrored_only": True,
                }
            )

        roads = []
        connected = sorted(self._cells)
        for index, left in enumerate(connected):
            for right in connected[index + 1 :]:
                roads.append(
                    {
                        "a": left,
                        "b": right,
                        "kind": "collaboration-heartbeat-link",
                    }
                )

        schedule = sorted(
            (
                {
                    "workspace_id": workspace_id,
                    "unmet_compute": cell.envelope.resources.unmet_compute,
                    "resource_pressure": max(
                        (
                            node.resource_pressure
                            for node in cell.envelope.perception.nodes
                        ),
                        default=0.0,
                    ),
                    "research_interest": max(
                        (
                            node.research_interest
                            for node in cell.envelope.perception.nodes
                        ),
                        default=0.0,
                    ),
                    "scheduler_credits": cell.scheduler_credits,
                }
                for workspace_id, cell in self._cells.items()
            ),
            key=lambda item: (
                -item["unmet_compute"],
                -item["resource_pressure"],
                -item["research_interest"],
                -item["scheduler_credits"],
                item["workspace_id"],
            ),
        )

        payload = {
            "schema": "cace-conway-economic-city-v1",
            "collaboration_link_id": self.collaboration_link_id,
            "active": self.active,
            "connected_workspace_count": len(self._cells),
            "cells": cells,
            "roads": roads,
            "scheduler_recommendation": schedule,
            "total_unmet_compute": total_unmet,
            "economy_scope": (
                "internal non-monetary compute/resource scheduling simulation only"
            ),
            "real_money_or_crypto_authority": False,
            "evidence_authority": False,
            "proof_effect": "none",
            "promotion_authority": False,
        }
        payload["city_sha256"] = sha256_identity(payload)
        return payload

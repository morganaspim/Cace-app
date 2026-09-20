from __future__ import annotations

from cace_studio.agent_runtime.conway_city import (
    ConwayEconomicCity,
    ConwayCityError,
    WorkspaceHeartbeatEnvelope,
    WorkspaceResourceState,
)
from cace_studio.agent_runtime.perception import (
    AgentNetworkMode,
    AgentPerceptionPacket,
    CanonicalEvidenceState,
    NodePerception,
    PerceptionHeartbeatState,
    ResidualTrend,
)


def _packet(workspace: str, seq: int, *, state=PerceptionHeartbeatState.ACTIVE):
    node = NodePerception(
        node_id="n1",
        semantic_hash=("a" if workspace == "w1" else "b") * 64,
        heartbeat_state=state,
        changed=False,
        residual_norm=None,
        residual_trend=ResidualTrend.UNKNOWN,
        convergence_progress=None,
        resource_pressure=0.6,
        research_interest=0.7,
        blocker_refs=(),
        canonical_evidence_state=CanonicalEvidenceState.NOT_RUN,
    )
    return AgentPerceptionPacket(
        run_id=f"run-{workspace}",
        experiment_id=f"exp-{workspace}",
        monotonic_seq=seq,
        semantic_graph_hash=("c" if workspace == "w1" else "d") * 64,
        emitted_at="2026-09-20T00:00:00+00:00",
        network_mode=AgentNetworkMode.HYBRID,
        nodes=(node,),
    )


def test_city_activates_only_after_two_linked_workspace_heartbeats():
    city = ConwayEconomicCity(
        collaboration_link_id="link-1",
        member_workspace_ids=frozenset({"w1", "w2"}),
    )
    city.ingest(
        WorkspaceHeartbeatEnvelope(
            workspace_id="w1",
            collaboration_link_id="link-1",
            perception=_packet("w1", 1),
            resources=WorkspaceResourceState(
                compute_supply=0.9,
                compute_demand=0.3,
            ),
        )
    )
    assert city.snapshot()["active"] is False

    city.ingest(
        WorkspaceHeartbeatEnvelope(
            workspace_id="w2",
            collaboration_link_id="link-1",
            perception=_packet("w2", 1),
            resources=WorkspaceResourceState(
                compute_supply=0.2,
                compute_demand=0.8,
                latency_pressure=0.4,
            ),
        )
    )
    snapshot = city.snapshot()
    assert snapshot["active"] is True
    assert snapshot["connected_workspace_count"] == 2
    assert snapshot["roads"] == [
        {"a": "w1", "b": "w2", "kind": "collaboration-heartbeat-link"}
    ]
    assert snapshot["scheduler_recommendation"][0]["workspace_id"] == "w2"
    assert snapshot["real_money_or_crypto_authority"] is False
    assert snapshot["proof_effect"] == "none"


def test_spare_compute_mints_only_bounded_non_monetary_scheduler_credits():
    city = ConwayEconomicCity(
        collaboration_link_id="link-1",
        member_workspace_ids=frozenset({"w1", "w2"}),
        max_scheduler_credits=10.0,
        spare_compute_credit_rate=5.0,
    )
    for seq in range(1, 10):
        city.ingest(
            WorkspaceHeartbeatEnvelope(
                workspace_id="w1",
                collaboration_link_id="link-1",
                perception=_packet("w1", seq),
                resources=WorkspaceResourceState(
                    compute_supply=1.0,
                    compute_demand=0.0,
                ),
            )
        )
    credits = city.snapshot()["cells"][0]["scheduler_credits"]
    assert credits == 10.0
    assert city.snapshot()["cells"][0]["scheduler_credits_are_money"] is False


def test_city_rejects_unlinked_or_replayed_heartbeats():
    city = ConwayEconomicCity(
        collaboration_link_id="link-1",
        member_workspace_ids=frozenset({"w1", "w2"}),
    )
    envelope = WorkspaceHeartbeatEnvelope(
        workspace_id="w1",
        collaboration_link_id="link-1",
        perception=_packet("w1", 1),
        resources=WorkspaceResourceState(compute_supply=0.5, compute_demand=0.5),
    )
    city.ingest(envelope)

    try:
        city.ingest(envelope)
    except ConwayCityError as exc:
        assert "sequence" in str(exc)
    else:
        raise AssertionError("replayed heartbeat must fail")

    try:
        city.ingest(
            WorkspaceHeartbeatEnvelope(
                workspace_id="w3",
                collaboration_link_id="link-1",
                perception=_packet("w2", 2),
                resources=WorkspaceResourceState(
                    compute_supply=0.5,
                    compute_demand=0.5,
                ),
            )
        )
    except ConwayCityError as exc:
        assert "member" in str(exc)
    else:
        raise AssertionError("unlinked workspace must fail")

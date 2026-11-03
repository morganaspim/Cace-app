from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cace_studio.agent_runtime import AgentController, AgentDecision, ToolBus
from cace_studio.agent_runtime.perception import (
    AgentNetworkMode,
    AgentPerceptionTracker,
    CanonicalEvidenceState,
    PerceptionHeartbeatState,
    ResidualTrend,
)
from cace_studio.core.executor import RunResult
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.reproducibility import experiment_fingerprint
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState


def _record(state: VerificationState) -> VerificationRecord:
    return VerificationRecord(
        verifier="test",
        kind=EvidenceKind.NUMERICAL,
        claim="test claim",
        state=state,
        method="test",
    )


def _experiment() -> Experiment:
    return Experiment(
        name="Perception",
        nodes=[Node("a", "source", {"scale": 1}), Node("b", "sink")],
        edges=[Edge("a", "out", "b", "in")],
    )


def _run(experiment: Experiment) -> RunResult:
    semantic = experiment_fingerprint(experiment, include_layout=False)
    full = experiment_fingerprint(experiment, include_layout=True)
    return RunResult(
        run_id="run-1",
        outputs={"a": {"out": 1}, "b": {"out": 2}},
        certificates=[],
        verification={
            "a": [_record(VerificationState.PASS)],
            "b": [_record(VerificationState.FAIL)],
        },
        semantic_experiment_sha256=semantic,
        full_experiment_sha256=full,
        source_semantic_experiment_sha256=semantic,
        source_full_experiment_sha256=full,
        scope_included_node_ids=("a", "b"),
    )


def test_perception_packet_uses_canonical_verification_records_only() -> None:
    experiment = _experiment()
    tracker = AgentPerceptionTracker(
        clock=lambda: datetime(2026, 9, 20, tzinfo=timezone.utc)
    )
    packet = tracker.snapshot(experiment, run_result=_run(experiment))
    payload = packet.to_dict()
    assert payload["schema_version"] == "cace-agent-perception-v1"
    assert payload["network_mode"] == "LOCAL_ZERO_CONTACT"
    assert payload["evidence_authority"] is False
    by_id = packet.by_id()
    assert by_id["a"].canonical_evidence_state is CanonicalEvidenceState.PASS
    assert by_id["a"].heartbeat_state is PerceptionHeartbeatState.VERIFIED
    assert by_id["b"].canonical_evidence_state is CanonicalEvidenceState.FAIL
    assert by_id["b"].heartbeat_state is PerceptionHeartbeatState.FAILED


def test_perception_marks_whole_run_stale_when_source_graph_drifted() -> None:
    original = _experiment()
    run = _run(original)
    changed = _experiment()
    changed.node_map()["a"].params["scale"] = 2
    tracker = AgentPerceptionTracker()
    packet = tracker.snapshot(changed, run_result=run)
    assert all(
        node.canonical_evidence_state is CanonicalEvidenceState.STALE
        for node in packet.nodes
    )
    assert all(node.heartbeat_state is PerceptionHeartbeatState.STALE for node in packet.nodes)


def test_perception_tracks_semantic_change_and_residual_trend() -> None:
    experiment = _experiment()
    tracker = AgentPerceptionTracker()
    first = tracker.snapshot(experiment, residual_norms={"a": 4.0})
    second = tracker.snapshot(experiment, residual_norms={"a": 2.0})
    assert first.monotonic_seq == 0
    assert second.monotonic_seq == 1
    assert first.by_id()["a"].changed is True
    assert second.by_id()["a"].changed is False
    assert second.by_id()["a"].residual_trend is ResidualTrend.IMPROVING

    experiment.node_map()["a"].params["scale"] = 3
    third = tracker.snapshot(experiment, residual_norms={"a": 2.0})
    assert third.by_id()["a"].changed is True


def test_perception_rejects_fabricated_verification_objects() -> None:
    experiment = _experiment()
    run = _run(experiment)
    run.verification["a"] = [{"state": "pass"}]  # type: ignore[list-item]
    tracker = AgentPerceptionTracker()
    with pytest.raises(TypeError, match="VerificationRecord"):
        tracker.snapshot(experiment, run_result=run)


def test_perception_reports_blockers_without_promoting_downstream_evidence() -> None:
    experiment = _experiment()
    run = _run(experiment)
    run.verification["a"] = [_record(VerificationState.FAIL)]
    run.verification["b"] = []
    packet = AgentPerceptionTracker().snapshot(experiment, run_result=run)
    b = packet.by_id()["b"]
    assert b.blocker_refs == ("a",)
    assert b.heartbeat_state is PerceptionHeartbeatState.BLOCKED
    assert b.canonical_evidence_state is CanonicalEvidenceState.NOT_RUN


class CapturePlanner:
    def __init__(self) -> None:
        self.perception = None

    def decide(self, context):
        self.perception = context.perception
        return AgentDecision.finish("done")


def test_controller_passes_current_perception_to_planner() -> None:
    experiment = _experiment()
    tracker = AgentPerceptionTracker(network_mode=AgentNetworkMode.LOCAL_ZERO_CONTACT)
    planner = CapturePlanner()
    controller = AgentController(
        ToolBus(),
        perception_provider=lambda: tracker.snapshot(experiment).to_dict(),
    )
    report = controller.run("inspect experiment", planner)
    assert report.status == "finished"
    assert planner.perception is not None
    assert planner.perception["schema_version"] == "cace-agent-perception-v1"
    assert planner.perception["evidence_authority"] is False


def test_controller_aborts_if_configured_perception_provider_fails() -> None:
    planner = CapturePlanner()

    def fail():
        raise ValueError("bad sensor")

    controller = AgentController(ToolBus(), perception_provider=fail)
    report = controller.run("inspect experiment", planner)
    assert report.status == "aborted"
    assert "perception failure" in report.message
    assert planner.perception is None

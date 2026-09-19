from __future__ import annotations

import pytest

from cace_studio.ai.heartbeat_context import build_heartbeat_context_packet
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.heartbeat import (
    AIHeartbeatUpdate,
    CanvasHeartbeatEngine,
    HeartbeatState,
)
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState


def _experiment():
    return Experiment(
        name="Heartbeat",
        nodes=[
            Node("a", "source"),
            Node("b", "middle"),
            Node("c", "sink"),
        ],
        edges=[
            Edge("a", "out", "b", "in"),
            Edge("b", "out", "c", "in"),
        ],
    )


def _record(state: VerificationState):
    return VerificationRecord(
        verifier="test",
        kind=EvidenceKind.NUMERICAL,
        claim="test claim",
        state=state,
        method="unit-test",
    )


def test_dependency_heartbeat_advances_ready_state_after_verified_parent():
    engine = CanvasHeartbeatEngine()
    experiment = _experiment()
    frame0 = engine.advance(
        experiment,
        semantic_hashes={"a": "ha", "b": "hb", "c": "hc"},
    )
    assert frame0.by_id()["a"].state is HeartbeatState.READY
    assert frame0.by_id()["b"].state is HeartbeatState.WAITING
    assert frame0.by_id()["c"].state is HeartbeatState.WAITING

    frame1 = engine.advance(
        experiment,
        semantic_hashes={"a": "ha", "b": "hb", "c": "hc"},
        verification={"a": (_record(VerificationState.PASS),)},
    )
    assert frame1.by_id()["a"].state is HeartbeatState.VERIFIED
    assert frame1.by_id()["b"].state is HeartbeatState.READY
    assert frame1.by_id()["c"].state is HeartbeatState.WAITING


def test_not_run_never_becomes_verified():
    engine = CanvasHeartbeatEngine()
    frame = engine.advance(
        _experiment(),
        semantic_hashes={"a": "ha", "b": "hb", "c": "hc"},
        verification={"a": (_record(VerificationState.NOT_RUN),)},
    )
    assert frame.by_id()["a"].state is not HeartbeatState.VERIFIED
    assert frame.by_id()["a"].verification_summary == "not-run"


def test_semantic_hash_change_marks_node_and_dependents_stale():
    engine = CanvasHeartbeatEngine()
    experiment = _experiment()
    first = engine.advance(
        experiment,
        semantic_hashes={"a": "ha", "b": "hb", "c": "hc"},
        verification={
            "a": (_record(VerificationState.PASS),),
            "b": (_record(VerificationState.PASS),),
        },
    )
    second = engine.advance(
        experiment,
        semantic_hashes={"a": "ha2", "b": "hb", "c": "hc"},
        verification={
            "a": (_record(VerificationState.PASS),),
            "b": (_record(VerificationState.PASS),),
        },
    )
    assert first.by_id()["a"].state is HeartbeatState.VERIFIED
    assert second.by_id()["a"].state is HeartbeatState.STALE
    assert second.by_id()["b"].state is HeartbeatState.STALE
    assert second.by_id()["c"].state is HeartbeatState.STALE


def test_failed_dependency_blocks_downstream_chain():
    engine = CanvasHeartbeatEngine()
    frame = engine.advance(
        _experiment(),
        semantic_hashes={"a": "ha", "b": "hb", "c": "hc"},
        verification={"a": (_record(VerificationState.FAIL),)},
    )
    assert frame.by_id()["a"].state is HeartbeatState.FAILED
    assert frame.by_id()["b"].state is HeartbeatState.BLOCKED
    assert frame.by_id()["c"].state is HeartbeatState.BLOCKED


def test_ai_update_changes_interest_only_not_verification():
    engine = CanvasHeartbeatEngine()
    frame = engine.advance(
        _experiment(),
        semantic_hashes={"a": "ha", "b": "hb", "c": "hc"},
        ai_updates=(AIHeartbeatUpdate("a", 0.8, "inspect this node"),),
    )
    node = frame.by_id()["a"]
    assert node.research_interest == 0.8
    assert node.state is HeartbeatState.READY
    assert node.verification_summary == "not-run"


def test_heartbeat_context_exposes_delta_without_mutation_authority():
    engine = CanvasHeartbeatEngine()
    experiment = _experiment()
    first = engine.advance(
        experiment,
        semantic_hashes={"a": "ha", "b": "hb", "c": "hc"},
    )
    second = engine.advance(
        experiment,
        semantic_hashes={"a": "ha", "b": "hb", "c": "hc"},
        ai_updates=(AIHeartbeatUpdate("b", 0.5),),
    )
    packet = build_heartbeat_context_packet(experiment, second, first)
    payload = packet.to_dict()
    assert payload["schema"] == "cace.ai-heartbeat-context.v1"
    assert [item["node_id"] for item in payload["changed_nodes"]] == ["b"]
    assert "never verification evidence" in packet.to_prompt_text()
    assert "PASS" not in payload


def test_ai_update_schema_has_no_verification_authority_field():
    with pytest.raises(TypeError):
        AIHeartbeatUpdate("a", 0.2, state="verified")


def test_fake_verification_objects_are_rejected():
    engine = CanvasHeartbeatEngine()
    with pytest.raises(TypeError):
        engine.advance(
            _experiment(),
            semantic_hashes={"a": "ha", "b": "hb", "c": "hc"},
            verification={"a": ({"state": "pass"},)},
        )

"""Host-owned capability gates for snapshot reading, written before implementation."""
from __future__ import annotations

from dataclasses import dataclass
import pytest

from cace_studio.ai.snapshot_broker import SnapshotBroker
from cace_studio.ai.host_snapshot_authority import (
    HostSnapshotAuthority, DatasetRight, SourceDescriptor, AccessDenied,
    HostQuery, AuthorizedObservation, authorized_tool_for_snapshot,
)
from cace_studio.ai.investigation import EngineeringSpec, Investigator, Outcome, PlanState


@pytest.fixture
def sample():
    rows = [
        {"family": "independent-a", "type": "synthetic", "reading": 0.5, "optional": None},
        {"family": "independent-b", "type": "synthetic", "reading": 0.7},
        {"family": "independent-b", "type": "synthetic", "reading": 0.9},
        {"family": "independent-c", "type": "reported", "reading": 2.1},
    ]
    b = SnapshotBroker({"signals": rows},
                       {"signals": ("family", "type", "reading", "optional")},
                       max_output=8, min_group=2)
    time = {"now": 2000.0}
    rights = {
        "session-1": (DatasetRight("signals", frozenset({"select", "count", "group_count"}),
                                   frozenset({"family", "type", "reading"}),
                                   frozenset({"type"}), max_rows=2),),
        "session-2": (),
    }
    sources = {"signals": SourceDescriptor("local-example-1", "synthetic", "demo-family")}
    auth = HostSnapshotAuthority(b, rights=rights, sources=sources, clock=lambda: time["now"])
    return b, auth, time


def make_query(**changes):
    data = dict(dataset="signals", operation="select", fields=("family", "reading"),
                where={"type": "synthetic"}, limit=2)
    data.update(changes)
    return HostQuery(**data)


def test_missing_field_does_not_match_explicit_null(sample):
    broker, _, _ = sample
    # A row without 'optional' is not evidence of an explicit optional=None.
    assert broker.count("signals", where={"optional": None}) == 1


def test_host_issues_exact_query_receipt_with_provenance(sample):
    _, auth, _ = sample
    token = auth.issue("session-1", make_query(), ttl_seconds=30)
    result = auth.consume("session-1", token)
    assert isinstance(result, AuthorizedObservation)
    assert len(result.value) == 2
    assert result.source.source_kind == "synthetic"
    assert result.source.source_id == "local-example-1"
    assert len(result.snapshot_sha256) == 64
    assert len(result.query_sha256) == 64
    assert result.status == "ADVISORY_SNAPSHOT_ONLY"
    assert result.proof_status == "NOT_RUN"
    assert result.evidence_authority is False
    assert result.permission_authority == "TRUSTED_HOST_BOUNDARY_REQUIRED"


def test_model_declared_permission_cannot_issue_host_capability(sample):
    _, auth, _ = sample
    with pytest.raises(AccessDenied):
        auth.issue("session-2", make_query())
    with pytest.raises(AccessDenied):
        auth.issue("unregistered", make_query())
    # The model-controlled EngineeringSpec is irrelevant to host authorization.
    spec = EngineeringSpec("Read more", "ai", ("Do not leak",),
                           permissions=("project_dataset_read",))
    assert "project_dataset_read" in spec.permissions
    with pytest.raises(AccessDenied):
        auth.issue("session-2", make_query())


def test_session_is_bound_and_token_cannot_replay_or_be_forged(sample):
    _, auth, _ = sample
    token = auth.issue("session-1", make_query())
    with pytest.raises(AccessDenied): auth.consume("session-2", token)
    with pytest.raises(AccessDenied): auth.consume("session-1", token + "x")
    assert auth.consume("session-1", token).value
    with pytest.raises(AccessDenied): auth.consume("session-1", token)


def test_expiry_and_revocation_fail_closed(sample):
    _, auth, clock = sample
    token = auth.issue("session-1", make_query(), ttl_seconds=5)
    clock["now"] += 5.1
    with pytest.raises(AccessDenied): auth.consume("session-1", token)
    t2 = auth.issue("session-1", make_query(), ttl_seconds=10)
    auth.revoke_session("session-1")
    with pytest.raises(AccessDenied): auth.consume("session-1", t2)
    with pytest.raises(AccessDenied): auth.issue("session-1", make_query())


def test_illegal_dataset_fields_filters_and_aggregation_rejected(sample):
    _, auth, _ = sample
    cases = (
        make_query(dataset="secret"),
        make_query(fields=("optional",)),
        make_query(where={"optional": None}),
        make_query(limit=3),
        make_query(operation="shell"),
        make_query(operation="group_count", fields=("reading",)),
    )
    for query in cases:
        with pytest.raises(AccessDenied): auth.issue("session-1", query)


def test_immutable_query_not_overridden_by_model_context(sample):
    _, auth, _ = sample
    token = auth.issue("session-1", make_query())
    tool = authorized_tool_for_snapshot(auth, session_id="session-1", token=token,
                                        tool_id="fixed-query", capability="fixed_snapshot")
    # Context cannot override pre-signed query; adapter rejects any keys.
    with pytest.raises(AccessDenied): tool.handler({"where": {"type": "reported"}})
    observation = tool.handler({})
    assert observation.source.source_kind == "synthetic"
    assert len(observation.value) == 2


def test_real_authorized_tool_is_still_not_formal_proof(sample):
    _, auth, _ = sample
    token = auth.issue("session-1", make_query())
    tool = authorized_tool_for_snapshot(auth, session_id="session-1", token=token,
                                        tool_id="fixed-query", capability="fixed_snapshot")
    agent = Investigator()
    agent.register(tool)
    spec = EngineeringSpec("Inspect source", "ai", ("Observe a source",),
                           permissions=("project_dataset_read",))
    plan = agent.plan(spec, ("fixed_snapshot",))
    assert plan.state == PlanState.READY
    result = agent.execute(plan, {})
    assert result.outcome == Outcome.COMPLETED_ADVISORY
    assert result.proof_status == "NOT_RUN"


def test_unauthorized_model_plan_cannot_select_tool(sample):
    _, auth, _ = sample
    token = auth.issue("session-1", make_query())
    tool = authorized_tool_for_snapshot(auth, session_id="session-1", token=token,
                                        tool_id="fixed-query", capability="fixed_snapshot")
    agent = Investigator()
    agent.register(tool)
    spec = EngineeringSpec("Try absent permission", "ai", ("Permission required",), permissions=())
    plan = agent.plan(spec, ("fixed_snapshot",))
    assert plan.state == PlanState.BLOCKED


def test_token_quota_and_clock_failures(sample):
    _, auth, clock = sample
    # Strict ttl and bounded issuance prevent unbounded token accumulation.
    with pytest.raises(AccessDenied): auth.issue("session-1", make_query(), ttl_seconds=1000)
    with pytest.raises(AccessDenied): auth.issue("session-1", make_query(), ttl_seconds=-1)
    clock["now"] = float("nan")
    with pytest.raises(AccessDenied): auth.issue("session-1", make_query())


def test_cross_dataset_source_descriptor_missing_rejected(sample):
    broker, _, _ = sample
    with pytest.raises(AccessDenied):
        HostSnapshotAuthority(broker, rights={"session-1": (DatasetRight(
            "signals", frozenset({"count"}), frozenset(), frozenset()),)}, sources={})


def test_query_reconfiguration_after_issue_is_ignored(sample):
    _, auth, _ = sample
    where = {"type": "synthetic"}
    query = make_query(where=where)
    token = auth.issue("session-1", query)
    where["type"] = "reported"
    assert len(auth.consume("session-1", token).value) == 2


def test_pending_capability_quota_is_enforced(sample):
    broker, _, clock = sample
    rights = {"s": (DatasetRight("signals", frozenset({"select"}),
                                 frozenset({"family"}), frozenset({"type"}), max_rows=1),)}
    authority = HostSnapshotAuthority(broker, rights=rights,
                 sources={"signals": SourceDescriptor("demo", "synthetic", "demo")},
                 max_pending_per_session=1, clock=lambda: clock["now"])
    q = HostQuery("signals", "select", ("family",), {"type": "synthetic"}, 1)
    first = authority.issue("s", q)
    with pytest.raises(AccessDenied): authority.issue("s", q)
    authority.consume("s", first)
    assert authority.issue("s", q)


def test_aggregate_allowed_only_for_host_approved_group_field(sample):
    _, auth, _ = sample
    query = HostQuery("signals", "group_count", fields=("type",), where={})
    observation = auth.consume("session-1", auth.issue("session-1", query))
    assert observation.operation == "group_count"
    assert observation.value == {"synthetic": 3}
    assert observation.evidence_authority is False


def test_snapshot_mutation_after_issuance_is_detected(sample):
    broker, auth, _ = sample
    token = auth.issue("session-1", make_query())
    # Only a trusted host can mutate this private table. A changed source
    # identity must invalidate a previously issued capability.
    broker._data["signals"] = broker._data["signals"][1:]
    with pytest.raises(AccessDenied): auth.consume("session-1", token)
    with pytest.raises(AccessDenied): auth.consume("session-1", token)

def test_non_mapping_empty_filter_must_not_expand_to_unfiltered_query(sample):
    _, auth, _ = sample
    with pytest.raises(AccessDenied):
        auth.issue("session-1", make_query(where=[]))

def test_malformed_fields_and_operation_rejected_without_typeerror(sample):
    _, auth, _ = sample
    for query in (make_query(fields=(["family"],)),
                  make_query(operation=["select"])):
        with pytest.raises(AccessDenied):
            auth.issue("session-1", query)

from __future__ import annotations

import importlib.util
from pathlib import Path

P = Path(__file__).parents[1] / "scripts" / "validate_collaboration_lifecycle.py"
spec = importlib.util.spec_from_file_location("lifecycle", P)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

H = "a" * 40


def r(i, t, sender="chatgpt", target="all-agents", head=H, **extra):
    value = {
        "record_id": i,
        "record_type": t,
        "sender": sender,
        "target": target,
        "head_sha": head,
    }
    value.update(extra)
    return value


def test_single_lease_valid():
    assert m.validate([r("task:1", "TASK_LEASE")]) == []


def test_two_live_leases_same_owner_rejected():
    errors = m.validate(
        [r("task:1", "TASK_LEASE"), r("task:2", "TASK_LEASE")]
    )
    assert any("multiple live lease chains" in error for error in errors)


def test_direct_cross_owner_replacement_requires_handoff():
    errors = m.validate(
        [
            r("task:1", "TASK_LEASE"),
            r("task:2", "TASK_LEASE", sender="gemini", supersedes="task:1"),
        ]
    )
    assert any("owner change requires HANDOFF" in error for error in errors)


def test_same_owner_lease_refresh_valid():
    records = [
        r("task:1", "TASK_LEASE"),
        r("task:2", "TASK_LEASE", supersedes="task:1"),
    ]
    assert m.validate(records) == []


def test_valid_handoff_transfers_live_owner_to_target():
    records = [
        r("task:1", "TASK_LEASE"),
        r(
            "handoff:1",
            "HANDOFF",
            sender="chatgpt",
            target="gemini",
            supersedes="task:1",
        ),
    ]
    assert m.validate(records) == []
    _, by_id, index = m._index_records(records)
    errors = []
    superseders = m._valid_supersessions(records, by_id, index, errors)
    live = m.live_leases(records, superseders)[H]
    assert errors == []
    assert len(live) == 1
    assert m.lease_owner(live[0]) == "gemini"


def test_handoff_sender_must_own_prior_lease():
    errors = m.validate(
        [
            r("task:1", "TASK_LEASE"),
            r(
                "handoff:1",
                "HANDOFF",
                sender="gemini",
                target="local-ai",
                supersedes="task:1",
            ),
        ]
    )
    assert any("HANDOFF sender must be current owner" in error for error in errors)


def test_handoff_target_must_change_owner():
    errors = m.validate(
        [
            r("task:1", "TASK_LEASE"),
            r(
                "handoff:1",
                "HANDOFF",
                sender="chatgpt",
                target="chatgpt",
                supersedes="task:1",
            ),
        ]
    )
    assert any("HANDOFF target must change owner" in error for error in errors)


def test_target_owner_can_refresh_lease_after_handoff():
    records = [
        r("task:1", "TASK_LEASE"),
        r(
            "handoff:1",
            "HANDOFF",
            sender="chatgpt",
            target="gemini",
            supersedes="task:1",
        ),
        r(
            "task:2",
            "TASK_LEASE",
            sender="gemini",
            target="all-agents",
            supersedes="handoff:1",
        ),
    ]
    assert m.validate(records) == []


def test_second_superseder_same_prior_rejected():
    errors = m.validate(
        [
            r("task:1", "TASK_LEASE"),
            r("task:2", "TASK_LEASE", supersedes="task:1"),
            r("task:3", "TASK_LEASE", supersedes="task:1"),
        ]
    )
    assert any("already superseded" in error for error in errors)


def test_review_cannot_hide_conflicting_lease():
    errors = m.validate(
        [
            r("task:1", "TASK_LEASE"),
            r("review:1", "REVIEW", supersedes="task:1"),
            r("task:2", "TASK_LEASE", sender="gemini"),
        ]
    )
    assert any("only TASK_LEASE/HANDOFF" in error for error in errors)
    assert any("multiple live lease chains" in error for error in errors)


def test_cross_head_supersession_rejected():
    errors = m.validate(
        [
            r("task:1", "TASK_LEASE"),
            r(
                "task:2",
                "TASK_LEASE",
                head="b" * 40,
                supersedes="task:1",
            ),
        ]
    )
    assert any("cross-head supersession forbidden" in error for error in errors)


def test_unknown_supersession_rejected():
    errors = m.validate(
        [r("task:2", "TASK_LEASE", supersedes="missing")]
    )
    assert any("supersedes unknown" in error for error in errors)


def test_decision_without_lease_rejected():
    errors = m.validate([r("decision:1", "DECISION")])
    assert any("DECISION requires an earlier lease" in error for error in errors)


def test_close_without_decision_rejected():
    errors = m.validate(
        [r("task:1", "TASK_LEASE"), r("closed:1", "CLOSED")]
    )
    assert any("CLOSED requires an earlier DECISION" in error for error in errors)


def test_valid_lifecycle():
    records = [
        r("task:1", "TASK_LEASE"),
        r("proposal:1", "PROPOSAL"),
        r("review:1", "REVIEW"),
        r("decision:1", "DECISION"),
        r("closed:1", "CLOSED"),
    ]
    assert m.validate(records) == []


def test_reference_shape_rejected():
    errors = m.validate(
        [r("task:1", "TASK_LEASE", evidence_refs=[""])]
    )
    assert any("evidence_refs must" in error for error in errors)


def test_exact_head_authorization_succeeds():
    records = [r("task:1", "TASK_LEASE")]
    assert m.validate_authorization(records, H, "chatgpt") == []


def test_stale_head_authorization_rejected():
    records = [r("task:1", "TASK_LEASE")]
    errors = m.validate_authorization(records, "b" * 40, "chatgpt")
    assert any("requires exactly one live task lease/handoff" in error for error in errors)


def test_wrong_actor_authorization_rejected():
    records = [r("task:1", "TASK_LEASE")]
    errors = m.validate_authorization(records, H, "gemini")
    assert any("is not live owner" in error for error in errors)


def test_invalid_authorization_sha_rejected():
    records = [r("task:1", "TASK_LEASE")]
    errors = m.validate_authorization(records, "ABC", "chatgpt")
    assert any("exact lowercase 40-hex SHA" in error for error in errors)

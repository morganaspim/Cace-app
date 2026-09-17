from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "validate_collaboration_lifecycle.py"
spec = importlib.util.spec_from_file_location("validate_collaboration_lifecycle", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HEAD = "a" * 40


def rec(rid, kind, sender="chatgpt", **extra):
    value = {"record_id": rid, "record_type": kind, "sender": sender, "head_sha": HEAD}
    value.update(extra)
    return value


def test_single_lease_is_valid():
    assert mod.validate([rec("task:1", "TASK_LEASE")]) == []


def test_conflicting_live_owners_rejected():
    errors = mod.validate([rec("task:1", "TASK_LEASE"), rec("task:2", "TASK_LEASE", sender="gemini")])
    assert any("conflicting live TASK_LEASE owners" in error for error in errors)


def test_explicit_supersession_allows_owner_change():
    records = [rec("task:1", "TASK_LEASE"), rec("task:2", "TASK_LEASE", sender="gemini", supersedes="task:1")]
    assert mod.validate(records) == []


def test_unknown_superseded_record_rejected():
    errors = mod.validate([rec("task:2", "TASK_LEASE", supersedes="missing")])
    assert any("supersedes unknown record" in error for error in errors)


def test_handoff_requires_prior_lease_or_handoff():
    errors = mod.validate([rec("review:1", "REVIEW"), rec("handoff:1", "HANDOFF", supersedes="review:1")])
    assert any("HANDOFF must supersede TASK_LEASE or HANDOFF" in error for error in errors)


def test_reference_shape_rejected():
    errors = mod.validate([rec("task:1", "TASK_LEASE", evidence_refs=[""])])
    assert any("evidence_refs must be a list of nonempty strings" in error for error in errors)

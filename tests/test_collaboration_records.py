from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "verify_collaboration_records.py"
spec = importlib.util.spec_from_file_location("verify_collaboration_records", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HEAD = "a" * 40


def record(**updates):
    value = {
        "schema_version": "cace-collaboration-v1",
        "record_id": "task:00000001",
        "record_type": "TASK_LEASE",
        "sender": "chatgpt",
        "target": "gemini",
        "head_sha": HEAD,
        "evidence_class": "AI_PROPOSAL",
        "created_at": "2026-09-17T00:00:00Z",
        "payload": {"task": "review"},
        "content_sha256": "0" * 64,
    }
    value.update(updates)
    value["content_sha256"] = mod.digest(value)
    return value


def test_valid_record():
    assert mod.validate(record(), expected_head=HEAD) == []


def test_hash_detects_mutation():
    value = record()
    value["payload"]["task"] = "changed after hashing"
    assert "content_sha256 mismatch" in mod.validate(value)


def test_stale_head_rejected():
    errors = mod.validate(record(), expected_head="b" * 40)
    assert any(error.startswith("stale head:") for error in errors)


def test_proved_requires_evidence_reference():
    errors = mod.validate(record(evidence_class="PROVED"))
    assert "PROVED requires at least one evidence_ref" in errors


def test_proved_with_evidence_reference_is_structurally_valid():
    value = record(evidence_class="PROVED", evidence_refs=["qualification/run-44/kernel-audit"])
    assert mod.validate(value, expected_head=HEAD) == []


def test_unknown_field_rejected():
    value = record()
    value["unexpected"] = True
    value["content_sha256"] = mod.digest(value)
    assert any(error.startswith("unknown fields:") for error in mod.validate(value))

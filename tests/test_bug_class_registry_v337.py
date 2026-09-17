from __future__ import annotations

import copy
import json

import scripts.check_bug_sweep as bug_sweep


def _check() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    summary: dict[str, int] = {}
    bug_sweep._check_bug_class_registry(errors, summary)
    return errors, summary


def test_registered_bug_classes_are_guarded_content_addressed_and_live():
    errors, summary = _check()
    assert errors == []
    assert summary["bug_classes_checked"] >= 2
    assert summary["bug_classes_guarded"] == summary["bug_classes_checked"]
    assert summary["bug_class_refs_checked"] >= 7


def test_bug_class_record_mutation_without_rehashing_fails_closed(tmp_path, monkeypatch):
    raw = json.loads(bug_sweep.BUG_CLASS_REGISTRY.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(raw)
    mutated["classes"][0]["root_cause"] += " silently mutated"
    path = tmp_path / "bug_classes.json"
    path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(bug_sweep, "BUG_CLASS_REGISTRY", path)

    errors, _ = _check()
    assert any("fingerprint mismatch" in error for error in errors)


def test_rehashed_record_with_deleted_guard_hook_still_fails_closed(tmp_path, monkeypatch):
    raw = json.loads(bug_sweep.BUG_CLASS_REGISTRY.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(raw)
    item = mutated["classes"][0]
    item["guard_refs"][0]["contains"] = "THIS_GUARD_DOES_NOT_EXIST"
    item["fingerprint_sha256"] = bug_sweep._canonical_bug_class_digest(item)
    path = tmp_path / "bug_classes.json"
    path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(bug_sweep, "BUG_CLASS_REGISTRY", path)

    errors, _ = _check()
    assert any("no longer contains required hook" in error for error in errors)


def test_non_guarded_bug_class_blocks_ci_even_with_valid_fingerprint(tmp_path, monkeypatch):
    raw = json.loads(bug_sweep.BUG_CLASS_REGISTRY.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(raw)
    item = mutated["classes"][0]
    item["status"] = "OPEN"
    item["fingerprint_sha256"] = bug_sweep._canonical_bug_class_digest(item)
    path = tmp_path / "bug_classes.json"
    path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(bug_sweep, "BUG_CLASS_REGISTRY", path)

    errors, _ = _check()
    assert any("status must be GUARDED" in error for error in errors)

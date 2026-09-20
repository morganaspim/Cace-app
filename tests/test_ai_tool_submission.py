from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "validate_ai_tool_submission.py"
spec = importlib.util.spec_from_file_location("validate_ai_tool_submission", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def packet():
    p = {
        "schema_version": "cace-ai-tool-submission-v1",
        "submission_id": "tool:rmk.test.0001",
        "head_sha": "a" * 40,
        "agent": "gemini",
        "track": "A",
        "tool": {
            "semantic_id": "math.exact.test_tool",
            "title": "Exact test tool",
            "purpose": "Exercise the submission contract.",
            "assumptions": ["integer inputs"],
            "failure_modes": ["overflow rejected"],
            "target_evidence": "FORMAL",
        },
        "cpp": {
            "headers": ["cpp/include/cace/math/test.hpp"],
            "sources": [],
            "tests": ["cpp/tests/math/test.cpp"],
            "bindings": [],
        },
        "formal": {
            "proof_state": "DRAFT",
            "lean_files": ["formal/cace_formal/CACEFormal/TestTool.lean"],
            "theorem_names": ["CACEFormal.testTool_correct"],
            "source_to_formal_refs": ["FSL-0", "FSL-1"],
        },
        "verification": {
            "unit_tests": ["cace_test_tool"],
            "property_tests": ["integer identity"],
            "adversarial_tests": ["overflow rejected"],
            "exact_or_certificate_checks": ["exact equality checker"],
        },
        "unresolved_obligations": ["canonical qualification not run"],
        "recommended_next_gate": "LEAN_QUARANTINE",
        "promotion_authority": False,
        "packet_sha256": "0" * 64,
    }
    p["packet_sha256"] = mod.canonical_digest(p)
    return p

def test_valid_submission_packet():
    assert mod.validate(packet()) == []

def test_self_promotion_is_impossible():
    p = packet()
    p["promotion_authority"] = True
    p["packet_sha256"] = mod.canonical_digest(p)
    assert "promotion_authority must be false" in mod.validate(p)

def test_formal_pass_is_not_legal_submission_state():
    p = packet()
    p["formal"]["proof_state"] = "FORMAL_PASS"
    p["packet_sha256"] = mod.canonical_digest(p)
    assert any("intentionally not legal" in e for e in mod.validate(p))

def test_packet_hash_detects_mutation():
    p = packet()
    p["tool"]["purpose"] = "mutated"
    assert "packet_sha256 mismatch" in mod.validate(p)

def test_unknown_top_level_field_rejected():
    p = packet()
    p["formal_pass"] = True
    p["packet_sha256"] = mod.canonical_digest(p)
    assert any(e.startswith("unknown fields:") for e in mod.validate(p))

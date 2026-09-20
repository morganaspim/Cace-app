from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _assert_common_manifest(manifest: dict) -> None:
    assert manifest["schema"] == "cace-external-builder-connection-v1"
    authority = manifest["authority"]
    for key in (
        "scientific",
        "proof",
        "verification",
        "claim_promotion",
        "security_truth",
    ):
        assert authority[key] is False

    policy = manifest["branch_policy"]
    assert policy["registry"] == "BRANCH_LIFECYCLE.json"
    assert policy["writable_statuses"] == ["ACTIVE"]
    assert policy["main"] == "READ_ONLY_INTEGRATION"
    assert policy["force_push"] is False
    assert policy["merge_pull_request"] is False
    assert policy["delete_branch"] is False

    lifecycle = _load("BRANCH_LIFECYCLE.json")
    snapshot = policy["current_snapshot"]
    current = lifecycle["explicit_branches"][snapshot["branch"]]
    assert current["status"] == "ACTIVE"
    assert snapshot["status"] == "ACTIVE"
    assert lifecycle["explicit_branches"]["main"]["status"] == "INTEGRATION"

    for path in manifest["startup_read_order"]:
        assert (ROOT / path).exists(), f"startup file does not exist: {path}"


def test_base44_connection_is_narrow_and_non_authoritative() -> None:
    manifest = _load("BASE44_CONNECTION_MANIFEST.json")
    _assert_common_manifest(manifest)

    assert manifest["provider"] == "Base44"
    assert manifest["repository_permissions"]["direct_write_allow"] == [
        "base44/**"
    ]

    denied = set(manifest["repository_permissions"]["direct_write_deny"])
    for path in (
        "web/**",
        "webapp/**",
        "api/**",
        "cace_studio/**",
        "cpp/**",
        "formal/**",
        "schema/**",
        "security/**",
        ".github/**",
        "tests/**",
        "BRANCH_LIFECYCLE.json",
    ):
        assert path in denied

    forbidden = set(manifest["explicitly_do_not_build"])
    assert "scientific execution engine" in forbidden
    assert "Lean or any proof engine" in forbidden
    assert "high-frequency event bus" in forbidden
    assert "alternate React/CACE interface" in forbidden

    credits = manifest["credit_policy"]
    assert credits["source"] == "ops/base44_free_tier_budget.json"
    assert credits["never_silently_buy_credits"] is True
    assert credits["high_frequency_use_forbidden"] is True


def test_gemini_connection_owns_interface_not_science() -> None:
    manifest = _load("GEMINI_CONNECTION_MANIFEST.json")
    _assert_common_manifest(manifest)

    assert manifest["provider"] == "Google AI Studio Build Mode / Antigravity"
    assert set(manifest["repository_permissions"]["direct_write_allow"]) == {
        "webapp/**",
        "gemini/**",
    }
    assert (
        manifest["repository_permissions"]["legacy_frontend"]["permission"]
        == "READ_ONLY_UNTIL_REACT_FEATURE_PARITY_AND_EXPLICIT_MIGRATION_APPROVAL"
    )

    denied = set(manifest["repository_permissions"]["direct_write_deny"])
    for path in (
        "cace_studio/core/**",
        "cace_studio/modules/**",
        "cace_studio/agent_runtime/**",
        "cpp/**",
        "formal/**",
        "security/**",
        ".github/**",
        "BRANCH_LIFECYCLE.json",
    ):
        assert path in denied

    assert "api/index.py" in manifest["repository_permissions"]["propose_only"]
    assert "schema/**" in manifest["repository_permissions"]["propose_only"]

    forbidden = set(manifest["must_not_build"])
    assert "second GraphExecutor" in forbidden
    assert "scientific solver/runtime in JS/TS/Node" in forbidden
    assert "proof engine" in forbidden
    assert "client-side formal PASS" in forbidden

    batch_ids = [item["id"] for item in manifest["build_program"]]
    assert batch_ids == [f"GWEB-{index}" for index in range(1, 12)]

    exception = manifest["branch_policy"][
        "controlled_proof_submission_exception"
    ]
    assert exception["pattern"] == "submission/proof/<submission-id>"
    assert exception["after_initial_commit"] == "FROZEN"


def test_connection_schema_and_entrypoints_are_present() -> None:
    assert (ROOT / "schema/cace-external-builder-connection.schema.json").is_file()
    assert (ROOT / "BASE44.md").is_file()
    assert (ROOT / "GEMINI.md").is_file()
    assert (ROOT / "base44/README.md").is_file()

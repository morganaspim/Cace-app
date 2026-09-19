from __future__ import annotations

import subprocess

from cace_studio.core.claim_registry import ClaimRegistry
from cace_studio.core.proof_ledger import ProofLedger
from cace_studio.core.qualification_drift import (
    audit_current_qualifications,
    classify_qualification_sensitive,
    is_qualification_sensitive,
)


def _git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def _commit_all(repo, message):
    subprocess.check_call(["git", "add", "-A"], cwd=repo)
    subprocess.check_call(["git", "commit", "-m", message], cwd=repo)
    return _git(repo, "rev-parse", "HEAD")


def _qualified_pair(commit):
    digest = "a" * 64
    contract_id = "unit.proof.v1"
    contract_digest = "b" * 64
    registry = ClaimRegistry.from_mapping(
        {
            "schema_version": 1,
            "policy": "fail-closed",
            "claims": [
                {
                    "claim_id": "unit.claim",
                    "module_ids": ["unit.module"],
                    "statement": "unit",
                    "scope": "unit",
                    "evidence_ceiling": "formally-verified",
                    "proof_contract_id": contract_id,
                    "qualification": {
                        "status": "PASS",
                        "current_head_qualified": True,
                        "attested_commit": commit,
                        "proof_artifact_sha256": digest,
                        "reason": "",
                    },
                    "nonclaims": [],
                }
            ],
        }
    )
    ledger = ProofLedger.from_mapping(
        {
            "schema_version": 1,
            "policy": "fail-closed",
            "entries": [
                {
                    "release": "unit",
                    "claim_ids": ["unit.claim"],
                    "status": "PASS",
                    "current_head_qualified": True,
                    "commit": commit,
                    "proof_artifact_sha256": digest,
                    "proof_contract_id": contract_id,
                    "proof_contract_sha256": contract_digest,
                    "workflow_run_id": 1,
                    "checks": ["pinned-build", "axiom-audit"],
                    "blockers": [],
                }
            ],
        }
    )
    return registry, ledger


def test_sensitive_path_classifier_is_conservative_but_allows_provenance_only_updates():
    assert not is_qualification_sensitive("docs/CLAIMS.md")
    assert not is_qualification_sensitive("cace_studio/data/claim_registry.json")
    assert not is_qualification_sensitive("cace_studio/data/proof_ledger.json")

    for path in (
        "formal/cace_formal/CACEFormal/X.lean",
        "cace_studio/core/formal_gate.py",
        "cace_studio/modules/formal_v330.py",
        "cace_studio/modules/formal_hypothesis_bridges.py",
        "cace_studio/data/proof_contracts.json",
        "schema/proof-contracts.schema.json",
        "scripts/build_continuum_attestation.py",
        "scripts/export_v330_environment_metadata.py",
        "scripts/finalize_qualification_diagnostics.py",
        "scripts/promote_v330_qualification.py",
        "scripts/verify_v330_qualification_bundle.py",
        "scripts/verify_v330_qualification_source_binding.py",
        "tests/test_continuum_attestation_v337.py",
        "tests/test_export_v330_environment_metadata.py",
        "tests/test_lean_theorem_metadata_v336.py",
        "tests/test_qualification_bundle_verifier_v338.py",
        "tests/test_qualification_diagnostics_v337.py",
        "tests/test_qualification_overlay_v337.py",
        "tests/test_qualification_promotion_v339.py",
        "tests/test_qualification_source_binding_v339.py",
        "tests/test_zero_boundary_trace_bridge_v343.py",
        ".github/workflows/cace-formal-v330.yml",
        ".github/workflows/cace-formal-v336-theorem-metadata.yml",
    ):
        assert is_qualification_sensitive(path), path

    assert classify_qualification_sensitive(
        [
            "docs/CLAIMS.md",
            "cace_studio/data/proof_ledger.json",
            "cace_studio/core/executor.py",
            "cace_studio/data/proof_contracts.json",
            "scripts/verify_v330_qualification_source_binding.py",
        ]
    ) == (
        "cace_studio/core/executor.py",
        "cace_studio/data/proof_contracts.json",
        "scripts/verify_v330_qualification_source_binding.py",
    )


def test_proof_contract_change_is_never_treated_as_provenance_only():
    sensitive = classify_qualification_sensitive(
        [
            "cace_studio/data/claim_registry.json",
            "cace_studio/data/proof_ledger.json",
            "cace_studio/data/proof_contracts.json",
        ]
    )
    assert sensitive == ("cace_studio/data/proof_contracts.json",)


def test_promotion_implementation_change_always_requires_requalification():
    assert classify_qualification_sensitive(
        ["scripts/promote_v330_qualification.py", "cace_studio/data/proof_ledger.json"]
    ) == ("scripts/promote_v330_qualification.py",)


def test_overlay_oracle_change_always_requires_requalification():
    assert classify_qualification_sensitive(
        ["tests/test_qualification_overlay_v337.py"]
    ) == ("tests/test_qualification_overlay_v337.py",)


def test_zero_trace_bridge_guard_change_always_requires_requalification():
    assert classify_qualification_sensitive(
        [
            "tests/test_zero_boundary_trace_bridge_v343.py",
            "cace_studio/data/proof_ledger.json",
        ]
    ) == ("tests/test_zero_boundary_trace_bridge_v343.py",)


def test_git_drift_audit_allows_provenance_commit_but_rejects_sensitive_descendant(tmp_path):
    subprocess.check_call(["git", "init"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.email", "cace-test@example.invalid"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.name", "CACE Test"], cwd=tmp_path)

    (tmp_path / "formal").mkdir()
    (tmp_path / "formal" / "proof.lean").write_text("theorem x : True := by trivial\n", encoding="utf-8")
    (tmp_path / "cace_studio" / "data").mkdir(parents=True)
    (tmp_path / "cace_studio" / "data" / "proof_ledger.json").write_text("{}\n", encoding="utf-8")
    attested = _commit_all(tmp_path, "attested")

    registry, ledger = _qualified_pair(attested)

    (tmp_path / "cace_studio" / "data" / "proof_ledger.json").write_text(
        '{"promotion": true}\n', encoding="utf-8"
    )
    _commit_all(tmp_path, "provenance-only")
    allowed = audit_current_qualifications(
        tmp_path, registry=registry, ledger=ledger
    )[0]
    assert allowed.passed is True
    assert allowed.sensitive_paths == ()

    (tmp_path / "cace_studio" / "core").mkdir(parents=True)
    (tmp_path / "cace_studio" / "core" / "executor.py").write_text(
        "# sensitive change\n", encoding="utf-8"
    )
    _commit_all(tmp_path, "sensitive")
    rejected = audit_current_qualifications(
        tmp_path, registry=registry, ledger=ledger
    )[0]
    assert rejected.passed is False
    assert rejected.sensitive_paths == ("cace_studio/core/executor.py",)



def test_canonical_qualification_checkout_has_complete_ancestry():
    workflow = (
        __import__("pathlib").Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "cace-formal-v336-theorem-metadata.yml"
    ).read_text(encoding="utf-8")
    assert "Checkout exact event commit with bounded initial history" in workflow
    assert "fetch-depth: 64" in workflow
    assert "Ensure attested qualification ancestry is locally complete" in workflow
    assert "git merge-base --is-ancestor" in workflow
    assert "git fetch --no-tags --deepen=256 origin" in workflow
    assert "git fetch --no-tags --unshallow origin" in workflow



def test_canonical_qualification_prunes_only_owned_cache_acceleration_before_disk_gate():
    workflow = (
        __import__("pathlib").Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "cace-formal-v336-theorem-metadata.yml"
    ).read_text(encoding="utf-8")
    assert "min_free_kb=$((5 * 1024 * 1024))" in workflow
    assert "canonical-qualification-prune.lock" in workflow
    assert "kept_ancestors < 2" in workflow
    assert '[[ "$name" =~ ^[0-9a-f]{40}$ ]]' in workflow
    assert '-O "$candidate"' in workflow
    assert 'rm -rf -- "$candidate"' in workflow
    assert "at least 5 GiB free after safe cache pruning" in workflow
    assert "at least 5 GiB free after source staging" in workflow

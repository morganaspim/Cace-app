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
    assert is_qualification_sensitive("formal/cace_formal/CACEFormal/X.lean")
    assert is_qualification_sensitive("cace_studio/core/formal_gate.py")
    assert is_qualification_sensitive("cace_studio/modules/formal_v330.py")
    assert is_qualification_sensitive(".github/workflows/cace-formal-v330.yml")
    assert is_qualification_sensitive(
        ".github/workflows/cace-formal-v336-theorem-metadata.yml"
    )
    assert is_qualification_sensitive("scripts/verify_continuum_qualification_bundle.py")
    assert is_qualification_sensitive("tests/test_independent_qualification_verifier_v338.py")
    assert classify_qualification_sensitive(
        [
            "docs/CLAIMS.md",
            "cace_studio/data/proof_ledger.json",
            "cace_studio/core/executor.py",
            "scripts/verify_continuum_qualification_bundle.py",
        ]
    ) == (
        "cace_studio/core/executor.py",
        "scripts/verify_continuum_qualification_bundle.py",
    )


def test_git_drift_audit_allows_provenance_commit_but_rejects_sensitive_descendant(tmp_path):
    subprocess.check_call(["git", "init"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.email", "cace-test@example.invalid"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.name", "CACE Test"], cwd=tmp_path)

    (tmp_path / "formal").mkdir()
    (tmp_path / "formal" / "proof.lean").write_text(
        "theorem x : True := by trivial\n", encoding="utf-8"
    )
    (tmp_path / "cace_studio" / "data").mkdir(parents=True)
    (tmp_path / "cace_studio" / "data" / "proof_ledger.json").write_text(
        "{}\n", encoding="utf-8"
    )
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

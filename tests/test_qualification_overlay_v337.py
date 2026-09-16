from __future__ import annotations

import hashlib
import json

import pytest

from cace_studio.cli import main as cli_main
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.proof_explorer import ProofExplorer
from cace_studio.core.qualification_attestation import (
    QualificationAttestationError,
    verify_qualification_attestation_bytes,
)


COMMIT = "1" * 40


def _contract():
    contract = ProofContractRegistry.load_default().for_claim(
        "cace.v330.continuum-proof-strengthening"
    )
    assert contract is not None
    return contract


def _payload(*, commit: str = COMMIT) -> dict:
    contract = _contract()
    return {
        "attestation_schema": "cace-continuum-qualification-attestation-v2",
        "status": "PASS",
        "claim_id": contract.claim_id,
        "proof_contract_id": contract.contract_id,
        "proof_contract_sha256": contract.contract_sha256,
        "git_commit": commit,
        "formal_system": contract.formal_system,
        "build_target": contract.build_target,
        "lean_version": "Lean (version 4.32.1)",
        "lean_toolchain": "leanprover/lean4:v4.32.1",
        "mathlib_commit": contract.dependency_pins["mathlib_commit"],
        "audited_source_files": list(contract.audited_source_files),
        "audited_source_bundle_sha256": "2" * 64,
        "endpoint_theorems": list(contract.endpoint_theorems),
        "endpoint_count": len(contract.endpoint_theorems),
        "allowed_axioms": list(contract.allowed_axioms),
        "lake_manifest_sha256": "3" * 64,
        "kernel_axiom_audit_sha256": "4" * 64,
        "lean_environment_metadata_sha256": "5" * 64,
        "lean_environment_identity_sha256": "6" * 64,
        "qualification_checks": list(contract.required_checks),
        "qualification_system": "github-actions",
        "qualification_run_id": "12345",
        "workflow_run_id": 12345,
        "workflow_run_attempt": 1,
        "runner_name": "cace-oci-a1",
        "runner_arch": "ARM64",
        "current_head_required": True,
        "cache_policy": "cache is acceleration-only and never qualification evidence",
        "nonclaims": list(contract.nonclaims),
    }


def _bytes(payload: dict | None = None) -> bytes:
    value = _payload() if payload is None else payload
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _verify(data: bytes, *, commit: str = COMMIT):
    return verify_qualification_attestation_bytes(
        data,
        expected_git_commit=commit,
        expected_artifact_sha256=hashlib.sha256(data).hexdigest(),
    )


def test_default_explorer_remains_fail_closed_without_external_artifact():
    view = ProofExplorer().claim_view("cace.v330.continuum-proof-strengthening")
    assert view.current_head_qualified is False
    assert view.qualification_state == "UNQUALIFIED"
    assert view.qualification_source == "canonical-static"


def test_verified_external_artifact_upgrades_read_only_view_without_mutating_static_truth():
    data = _bytes()
    qualification = _verify(data)
    view = ProofExplorer(qualifications=(qualification,)).claim_view(
        "cace.v330.continuum-proof-strengthening"
    )

    assert view.current_head_qualified is True
    assert view.qualification_state == "QUALIFIED"
    assert view.qualification_source == "external-attestation"
    assert view.attested_commit == COMMIT
    assert view.proof_artifact_sha256 == hashlib.sha256(data).hexdigest()
    assert view.qualification_system == "github-actions"
    assert view.qualification_run_id == "12345"
    assert view.workflow_run_id == 12345
    assert view.checks == _contract().required_checks

    # Source-truth files remain a fail-closed baseline, avoiding commit self-reference.
    assert view.registry_status == "NOT_RUN"
    assert view.ledger_status == "NOT_RUN"
    assert view.blockers == ()


def test_artifact_digest_is_mandatory_external_trust_anchor():
    data = _bytes()
    with pytest.raises(QualificationAttestationError, match="trust anchor"):
        verify_qualification_attestation_bytes(
            data,
            expected_git_commit=COMMIT,
            expected_artifact_sha256="0" * 64,
        )


def test_exact_head_mismatch_fails_closed():
    data = _bytes()
    with pytest.raises(QualificationAttestationError, match="expected current Git commit"):
        verify_qualification_attestation_bytes(
            data,
            expected_git_commit="7" * 40,
            expected_artifact_sha256=hashlib.sha256(data).hexdigest(),
        )


def test_contract_endpoint_or_check_drift_fails_closed():
    for field in ("endpoint_theorems", "qualification_checks"):
        payload = _payload()
        payload[field] = payload[field][:-1]
        data = _bytes(payload)
        with pytest.raises(QualificationAttestationError):
            _verify(data)


def test_unknown_attestation_fields_fail_closed():
    payload = _payload()
    payload["future_unreviewed_field"] = True
    data = _bytes(payload)
    with pytest.raises(QualificationAttestationError, match="keys mismatch"):
        _verify(data)


def test_duplicate_external_qualification_for_same_claim_is_rejected():
    qualification = _verify(_bytes())
    with pytest.raises(ValueError, match="duplicate external qualification"):
        ProofExplorer(qualifications=(qualification, qualification))


def test_cli_can_render_verified_external_qualification(tmp_path, capsys):
    data = _bytes()
    digest = hashlib.sha256(data).hexdigest()
    artifact = tmp_path / "qualification.json"
    artifact.write_bytes(data)

    code = cli_main(
        [
            "proofs",
            "show",
            "cace.v330.continuum-proof-strengthening",
            "--qualification-attestation",
            str(artifact),
            "--qualification-sha256",
            digest,
            "--current-head",
            COMMIT,
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    rendered = json.loads(captured.out)
    assert rendered["proof"]["qualification_state"] == "QUALIFIED"
    assert rendered["proof"]["qualification_source"] == "external-attestation"
    assert rendered["proof"]["current_head_qualified"] is True


def test_cli_rejects_partial_external_qualification_arguments(tmp_path, capsys):
    artifact = tmp_path / "qualification.json"
    artifact.write_bytes(_bytes())
    code = cli_main(
        [
            "proofs",
            "show",
            "cace.v330.continuum-proof-strengthening",
            "--qualification-attestation",
            str(artifact),
        ]
    )
    captured = capsys.readouterr()
    assert code == 2
    error = json.loads(captured.err)
    assert "requires --qualification-attestation" in error["error"]

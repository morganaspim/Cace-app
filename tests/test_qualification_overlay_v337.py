from __future__ import annotations

from dataclasses import replace
import hashlib
import json

import pytest

from cace_studio.cli import main as cli_main
from cace_studio.core.claim_registry import ClaimRegistry
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.proof_explorer import ProofExplorer
from cace_studio.core.proof_ledger import ProofLedger
from cace_studio.core.qualification_attestation import (
    CACHE_POLICY,
    QualificationAttestationError,
    verify_qualification_attestation_bytes,
)


COMMIT = "1" * 40
CLAIM_ID = "cace.v330.continuum-proof-strengthening"


def _contract():
    contract = ProofContractRegistry.load_default().for_claim(CLAIM_ID)
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
        "lean_toolchain": contract.dependency_pins["lean_toolchain"],
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
        "cache_policy": CACHE_POLICY,
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


def _unqualified_explorer(*, qualifications=()) -> ProofExplorer:
    default_registry = ClaimRegistry.load_default()
    default_ledger = ProofLedger.load_default()
    claim = default_registry.by_id(CLAIM_ID)
    entry = default_ledger.for_claim(CLAIM_ID)
    contract = _contract()
    assert claim is not None and entry is not None

    unqualified_claim = replace(
        claim,
        qualification_status="NOT_RUN",
        current_head_qualified=False,
        attested_commit=None,
        proof_artifact_sha256=None,
        reason="",
    )
    unqualified_entry = replace(
        entry,
        status="NOT_RUN",
        current_head_qualified=False,
        commit=None,
        proof_artifact_sha256=None,
        proof_contract_id=contract.contract_id,
        proof_contract_sha256=contract.contract_sha256,
        qualification_system=None,
        qualification_run_id=None,
        workflow_run_id=None,
        checks=(),
        blockers=(),
    )
    registry = ClaimRegistry(
        schema_version=default_registry.schema_version,
        policy=default_registry.policy,
        claims=(unqualified_claim,),
        registry_sha256="synthetic-unqualified-registry",
    )
    ledger = ProofLedger(
        schema_version=default_ledger.schema_version,
        policy=default_ledger.policy,
        entries=(unqualified_entry,),
        ledger_sha256="synthetic-unqualified-ledger",
    )
    return ProofExplorer(
        registry=registry,
        ledger=ledger,
        qualifications=qualifications,
    )


def test_default_explorer_tracks_canonical_qualification_state():
    registry = ClaimRegistry.load_default()
    ledger = ProofLedger.load_default()
    claim = registry.by_id(CLAIM_ID)
    entry = ledger.for_claim(CLAIM_ID)
    contract = _contract()
    assert claim is not None and entry is not None

    view = ProofExplorer().claim_view(CLAIM_ID)
    assert claim.current_head_qualified == entry.current_head_qualified
    assert claim.qualification_status == entry.status
    assert claim.attested_commit == entry.commit
    assert claim.proof_artifact_sha256 == entry.proof_artifact_sha256

    static_evidence_matches_current_contract = bool(
        entry.proof_contract_id == contract.contract_id
        and entry.proof_contract_sha256 == contract.contract_sha256
        and set(contract.required_checks).issubset(entry.checks)
    )

    if claim.current_head_qualified and static_evidence_matches_current_contract:
        assert claim.qualification_status == "PASS"
        assert view.current_head_qualified is True
        assert view.qualification_state == "QUALIFIED"
        assert view.qualification_source == "canonical-static"
        assert view.attested_commit == claim.attested_commit
        assert view.proof_artifact_sha256 == claim.proof_artifact_sha256
        assert view.blockers == ()
    elif claim.current_head_qualified:
        assert claim.qualification_status == "PASS"
        assert view.current_head_qualified is False
        assert view.qualification_state == "CONFLICT"
        assert view.qualification_source == "conflict"
        assert any(
            "proof-contract" in blocker.lower() or "contract-required checks" in blocker.lower()
            for blocker in view.blockers
        )
    else:
        assert view.current_head_qualified is False
        assert view.qualification_state == "UNQUALIFIED"
        assert view.qualification_source == "canonical-static"


def test_verified_external_artifact_upgrades_synthetic_unqualified_view_without_mutating_truth():
    data = _bytes()
    qualification = _verify(data)
    view = _unqualified_explorer(qualifications=(qualification,)).claim_view(CLAIM_ID)

    assert view.current_head_qualified is True
    assert view.qualification_state == "QUALIFIED"
    assert view.qualification_source == "external-attestation"
    assert view.attested_commit == COMMIT
    assert view.proof_artifact_sha256 == hashlib.sha256(data).hexdigest()
    assert view.qualification_system == "github-actions"
    assert view.qualification_run_id == "12345"
    assert view.workflow_run_id == 12345
    assert view.checks == _contract().required_checks

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


def test_toolchain_dependency_or_axiom_drift_fails_closed():
    mutations = {
        "lean_toolchain": "leanprover/lean4:v4.31.0",
        "mathlib_commit": "7" * 40,
        "allowed_axioms": [*_contract().allowed_axioms, "CACE.fakeAxiom"],
    }
    for field, value in mutations.items():
        payload = _payload()
        payload[field] = value
        data = _bytes(payload)
        with pytest.raises(QualificationAttestationError):
            _verify(data)


def test_cache_policy_downgrade_fails_closed():
    payload = _payload()
    payload["cache_policy"] = "cached qualification may be inherited"
    data = _bytes(payload)
    with pytest.raises(QualificationAttestationError, match="cache_policy"):
        _verify(data)


def test_status_and_current_head_requirement_cannot_be_downgraded():
    for field, value in (("status", "NOT_RUN"), ("current_head_required", False)):
        payload = _payload()
        payload[field] = value
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


def test_cli_rendering_matches_canonical_plus_external_qualification_state(tmp_path, capsys):
    data = _bytes()
    digest = hashlib.sha256(data).hexdigest()
    qualification = _verify(data)
    expected = ProofExplorer(qualifications=(qualification,)).claim_view(CLAIM_ID)
    artifact = tmp_path / "qualification.json"
    artifact.write_bytes(data)

    code = cli_main(
        [
            "proofs",
            "show",
            CLAIM_ID,
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
    proof = rendered["proof"]
    assert proof["qualification_state"] == expected.qualification_state
    assert proof["qualification_source"] == expected.qualification_source
    assert proof["current_head_qualified"] is expected.current_head_qualified
    assert proof["attested_commit"] == expected.attested_commit
    assert proof["proof_artifact_sha256"] == expected.proof_artifact_sha256


def test_cli_rejects_partial_external_qualification_arguments(tmp_path, capsys):
    artifact = tmp_path / "qualification.json"
    artifact.write_bytes(_bytes())
    code = cli_main(
        [
            "proofs",
            "show",
            CLAIM_ID,
            "--qualification-attestation",
            str(artifact),
        ]
    )
    captured = capsys.readouterr()
    assert code == 2
    error = json.loads(captured.err)
    assert "requires --qualification-attestation" in error["error"]

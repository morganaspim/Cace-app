from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.qualification_attestation import CACHE_POLICY

SCRIPT = Path(__file__).parents[1] / "scripts" / "build_continuum_attestation.py"
spec = importlib.util.spec_from_file_location("continuum_attestation", SCRIPT)
att = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(att)


def contract():
    value = ProofContractRegistry.load_default().for_claim(att.CLAIM_ID)
    assert value is not None
    return value


def test_build_attestation_binds_contract_exact_head_and_all_artifact_hashes():
    c = contract()
    payload = att.build_attestation(
        contract=c,
        git_commit="1" * 40,
        lean_version="Lean 4.32.1",
        lean_toolchain=c.dependency_pins["lean_toolchain"],
        mathlib_commit=c.dependency_pins["mathlib_commit"],
        source_bundle_sha256="2" * 64,
        lake_manifest_sha256="3" * 64,
        kernel_axiom_audit_sha256="4" * 64,
        lean_environment_metadata_sha256="5" * 64,
        lean_environment_identity_sha256="6" * 64,
        qualification_system="github-actions",
        qualification_run_id="12345",
        workflow_run_id=12345,
        workflow_run_attempt=2,
        runner_name="cace-oci-a1",
        runner_arch="ARM64",
    )
    assert payload["attestation_schema"] == att.ATTESTATION_SCHEMA
    assert payload["status"] == "PASS"
    assert payload["claim_id"] == c.claim_id
    assert payload["proof_contract_id"] == c.contract_id
    assert payload["proof_contract_sha256"] == c.contract_sha256
    assert payload["git_commit"] == "1" * 40
    assert payload["lean_toolchain"] == c.dependency_pins["lean_toolchain"]
    assert payload["endpoint_count"] == len(c.endpoint_theorems)
    assert payload["qualification_checks"] == list(c.required_checks)
    assert payload["kernel_axiom_audit_sha256"] == "4" * 64
    assert payload["lean_environment_metadata_sha256"] == "5" * 64
    assert payload["lean_environment_identity_sha256"] == "6" * 64
    assert payload["cache_policy"] == CACHE_POLICY == att.CACHE_POLICY
    assert payload["current_head_required"] is True


def test_attestation_rejects_wrong_toolchain_mathlib_or_malformed_hashes():
    c = contract()
    kwargs = dict(
        contract=c,
        git_commit="1" * 40,
        lean_version="Lean 4.32.1",
        lean_toolchain=c.dependency_pins["lean_toolchain"],
        mathlib_commit=c.dependency_pins["mathlib_commit"],
        source_bundle_sha256="2" * 64,
        lake_manifest_sha256="3" * 64,
        kernel_axiom_audit_sha256="4" * 64,
        lean_environment_metadata_sha256="5" * 64,
        lean_environment_identity_sha256="6" * 64,
        qualification_system="github-actions",
        qualification_run_id="12345",
        workflow_run_id=12345,
        workflow_run_attempt=1,
        runner_name="cace-oci-a1",
        runner_arch="ARM64",
    )
    with pytest.raises(att.AttestationError, match="Lean toolchain"):
        att.build_attestation(**{**kwargs, "lean_toolchain": "leanprover/lean4:v4.31.0"})
    with pytest.raises(att.AttestationError, match="Mathlib"):
        att.build_attestation(**{**kwargs, "mathlib_commit": "7" * 40})
    with pytest.raises(att.AttestationError, match="source_bundle_sha256"):
        att.build_attestation(**{**kwargs, "source_bundle_sha256": "bad"})
    with pytest.raises(att.AttestationError, match="run id"):
        att.build_attestation(**{**kwargs, "workflow_run_id": 0})


def test_axiom_audit_requires_exact_contract_endpoint_set_and_whitelist():
    c = contract()
    payload = {
        "format": "cace.lean-theorem-metadata",
        "theorem_count": len(c.endpoint_theorems),
        "theorems": [{"name": name, "axioms": []} for name in c.endpoint_theorems],
    }
    att.validate_axiom_audit(
        payload,
        endpoint_theorems=c.endpoint_theorems,
        allowed_axioms=c.allowed_axioms,
    )

    missing = {**payload, "theorems": payload["theorems"][:-1]}
    with pytest.raises(att.AttestationError, match="endpoint set"):
        att.validate_axiom_audit(
            missing,
            endpoint_theorems=c.endpoint_theorems,
            allowed_axioms=c.allowed_axioms,
        )

    forbidden = {
        **payload,
        "theorems": [
            {"name": c.endpoint_theorems[0], "axioms": ["CACE.fakeAxiom"]},
            *payload["theorems"][1:],
        ],
    }
    with pytest.raises(att.AttestationError, match="non-whitelisted"):
        att.validate_axiom_audit(
            forbidden,
            endpoint_theorems=c.endpoint_theorems,
            allowed_axioms=c.allowed_axioms,
        )


def test_environment_metadata_requires_exact_contract_and_audit_binding():
    c = contract()
    base = {
        "artifact_schema": "cace-lean-theorem-metadata-v3",
        "metadata_state": "LEAN_GENERATED",
        "claim_id": c.claim_id,
        "proof_contract_id": c.contract_id,
        "proof_contract_sha256": c.contract_sha256,
        "git_commit": "1" * 40,
        "mathlib_commit": c.dependency_pins["mathlib_commit"],
        "kernel_axiom_audit_sha256": "4" * 64,
        "kernel_axiom_audit_theorem_count": len(c.endpoint_theorems),
        "endpoint_count": len(c.endpoint_theorems),
        "identity_sha256": "9" * 64,
        "endpoints": [{"theorem": name} for name in c.endpoint_theorems],
    }
    att.validate_environment_metadata(
        base,
        contract=c,
        git_commit="1" * 40,
        mathlib_commit=c.dependency_pins["mathlib_commit"],
        axiom_audit_sha256="4" * 64,
    )

    with pytest.raises(att.AttestationError, match="proof_contract_sha256"):
        att.validate_environment_metadata(
            {**base, "proof_contract_sha256": "8" * 64},
            contract=c,
            git_commit="1" * 40,
            mathlib_commit=c.dependency_pins["mathlib_commit"],
            axiom_audit_sha256="4" * 64,
        )

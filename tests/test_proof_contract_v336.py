from __future__ import annotations

from copy import deepcopy

import pytest

from cace_studio.core.proof_contract import ProofContract, ProofContractRegistry

# Final exact-SHA regression trigger for Rank-4 endpoint qualification.

EXPECTED_CONTINUUM_V3_HASH = "2931b00e08e07004f8fa14b65932f084630575f8b4c8dcc2d2b602894caba33c"


def _contract_mapping() -> dict:
    return {
        "contract_id": "proof.test.v1",
        "claim_id": "claim.test",
        "formal_system": "lean4",
        "build_target": "Test.Audit",
        "toolchain_file": "formal/test/lean-toolchain",
        "dependency_pins": {
            "lean_toolchain": "leanprover/lean4:v4.32.1",
            "mathlib_commit": "1" * 40,
        },
        "endpoint_theorems": ["Test.endpoint"],
        "audited_source_files": ["Test/Audit.lean"],
        "allowed_axioms": ["propext"],
        "required_checks": ["lean-build", "kernel-axiom-audit"],
        "nonclaims": ["Not a broader theorem."],
        "theorem_dependency_metadata": {
            "state": "NOT_GENERATED",
            "note": "No theorem dependency graph has been generated.",
        },
    }


def test_default_continuum_contract_v3_is_single_source_for_all_38_audited_endpoints():
    registry = ProofContractRegistry.load_default()
    contract = registry.for_claim("cace.v330.continuum-proof-strengthening")
    assert contract is not None
    assert contract.contract_id == "cace.proof.v330.continuum-proof-strengthening.v3"
    assert len(contract.endpoint_theorems) == 38
    assert len(contract.audited_source_files) == 12
    assert contract.build_target == "CACEFormal.V330AxiomAudit"
    assert contract.dependency_pins["lean_toolchain"] == "leanprover/lean4:v4.32.1"
    assert contract.dependency_pins["mathlib_commit"] == "520045ab14e26149ee970e2e617ca04b09bde5d6"
    assert contract.theorem_dependency_metadata_state == "LEAN_GENERATED"
    assert "Lean.Environment" in contract.theorem_dependency_metadata_note
    assert "lean-environment-theorem-metadata" in contract.required_checks
    assert "CACEFormal.Continuum.continuumPragerSynge_of_weakGreen" in contract.endpoint_theorems
    assert "CACEFormal.Continuum.inH1_of_besselRiesz_reconstruction" in contract.endpoint_theorems
    assert "CACEFormal.Continuum.inH1_of_inL2_weakPartial_inL2" in contract.endpoint_theorems
    assert "CACEFormal.Continuum.inH1_of_mem_H1DistributionalGraphSubmodule" in contract.endpoint_theorems
    assert "CACEFormal.Continuum.inH1_iff_exists_distributionalGraphRepresentative" in contract.endpoint_theorems
    assert "CACEFormal/WeakGreenFunctional.lean" in contract.audited_source_files
    assert "CACEFormal/H1GraphConverse.lean" in contract.audited_source_files
    assert contract.contract_sha256 == EXPECTED_CONTINUUM_V3_HASH


def test_contract_hash_changes_when_scope_changes():
    raw = _contract_mapping()
    first = ProofContract.from_mapping(raw)
    changed = deepcopy(raw)
    changed["endpoint_theorems"].append("Test.secondEndpoint")
    second = ProofContract.from_mapping(changed)
    assert first.contract_sha256 != second.contract_sha256


def test_contract_hash_changes_when_toolchain_pin_changes():
    raw = _contract_mapping()
    first = ProofContract.from_mapping(raw)
    changed = deepcopy(raw)
    changed["dependency_pins"]["lean_toolchain"] = "leanprover/lean4:v4.31.0"
    second = ProofContract.from_mapping(changed)
    assert first.contract_sha256 != second.contract_sha256


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("endpoint_theorems", []),
        ("endpoint_theorems", ["not_fully_qualified"]),
        ("audited_source_files", ["../escape.lean"]),
        ("audited_source_files", ["Test/not-lean.txt"]),
        ("required_checks", []),
        ("theorem_dependency_metadata", {"state": "INFERRED", "note": "bad"}),
    ],
)
def test_contract_rejects_incomplete_or_invented_scope(field, value):
    raw = _contract_mapping()
    raw[field] = value
    with pytest.raises(ValueError):
        ProofContract.from_mapping(raw)


def test_registry_rejects_multiple_contracts_for_same_claim():
    first = _contract_mapping()
    second = deepcopy(first)
    second["contract_id"] = "proof.test.v2"
    with pytest.raises(ValueError, match="multiple proof contracts"):
        ProofContractRegistry.from_mapping(
            {"schema_version": 1, "policy": "fail-closed", "contracts": [first, second]}
        )


def test_dependency_graph_state_is_explicit_and_never_inferred():
    contract = ProofContract.from_mapping(_contract_mapping())
    assert contract.theorem_dependency_metadata_state == "NOT_GENERATED"
    assert "No theorem dependency graph" in contract.theorem_dependency_metadata_note

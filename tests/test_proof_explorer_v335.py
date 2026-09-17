from __future__ import annotations

from cace_studio.core.claim_registry import ClaimRegistry
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.proof_explorer import ProofExplorer
from cace_studio.core.proof_ledger import ProofLedger
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState


COMMIT = "1" * 40
HASH = "a" * 64
CONTRACT_ID = "proof.test.v1"


def _contracts() -> ProofContractRegistry:
    return ProofContractRegistry.from_mapping(
        {
            "schema_version": 1,
            "policy": "fail-closed",
            "contracts": [
                {
                    "contract_id": CONTRACT_ID,
                    "claim_id": "claim.test",
                    "formal_system": "lean4",
                    "build_target": "Test.Audit",
                    "toolchain_file": "formal/test/lean-toolchain",
                    "dependency_pins": {"mathlib_commit": "1" * 40},
                    "endpoint_theorems": ["Test.endpoint"],
                    "audited_source_files": ["Test/Audit.lean"],
                    "allowed_axioms": ["propext"],
                    "required_checks": ["pinned-build", "axiom-audit"],
                    "nonclaims": ["Contract is not a broader theorem."],
                    "theorem_dependency_metadata": {
                        "state": "NOT_GENERATED",
                        "note": "No theorem-to-theorem dependencies were generated.",
                    },
                }
            ],
        }
    )


def _registry(*, qualified: bool, proof_hash: str = HASH) -> ClaimRegistry:
    return ClaimRegistry.from_mapping(
        {
            "schema_version": 1,
            "policy": "fail-closed",
            "claims": [
                {
                    "claim_id": "claim.test",
                    "module_ids": ["module.test"],
                    "statement": "Test statement.",
                    "scope": "Synthetic test scope.",
                    "evidence_ceiling": "formally-verified",
                    "proof_contract_id": CONTRACT_ID,
                    "qualification": {
                        "status": "PASS" if qualified else "NOT_RUN",
                        "current_head_qualified": qualified,
                        "attested_commit": COMMIT if qualified else None,
                        "proof_artifact_sha256": proof_hash if qualified else None,
                        "reason": "" if qualified else "Not yet qualified.",
                    },
                    "nonclaims": ["Not a broader theorem."],
                }
            ],
        }
    )


def _ledger(
    contracts: ProofContractRegistry,
    *,
    qualified: bool,
    proof_hash: str = HASH,
    contract_hash: str | None = None,
) -> ProofLedger:
    contract = contracts.for_claim("claim.test")
    contract_hash = contract.contract_sha256 if contract_hash is None else contract_hash
    return ProofLedger.from_mapping(
        {
            "schema_version": 1,
            "policy": "fail-closed",
            "entries": [
                {
                    "release": "test",
                    "claim_ids": ["claim.test"],
                    "status": "PASS" if qualified else "NOT_RUN",
                    "current_head_qualified": qualified,
                    "commit": COMMIT if qualified else None,
                    "proof_artifact_sha256": proof_hash if qualified else None,
                    "proof_contract_id": CONTRACT_ID,
                    "proof_contract_sha256": contract_hash,
                    "qualification_system": "portable-test" if qualified else None,
                    "qualification_run_id": "run-1" if qualified else None,
                    "workflow_run_id": None,
                    "checks": ["pinned-build", "axiom-audit"] if qualified else [],
                    "blockers": [] if qualified else ["Build not accepted."],
                }
            ],
        }
    )


def _explorer(*, qualified: bool, proof_hash: str = HASH, contract_hash: str | None = None):
    contracts = _contracts()
    return ProofExplorer(
        _registry(qualified=qualified, proof_hash=proof_hash),
        _ledger(
            contracts,
            qualified=qualified,
            proof_hash=proof_hash,
            contract_hash=contract_hash,
        ),
        contracts,
    )


def test_exact_claim_contract_ledger_match_is_qualified():
    view = _explorer(qualified=True).claim_view("claim.test")
    assert view.qualification_state == "QUALIFIED"
    assert view.current_head_qualified is True
    assert view.proof_contract_id == CONTRACT_ID
    assert view.proof_contract_build_target == "Test.Audit"
    assert view.endpoint_theorems == ("Test.endpoint",)
    assert view.theorem_dependency_metadata_state == "NOT_GENERATED"
    assert view.attested_commit == COMMIT
    assert view.proof_artifact_sha256 == HASH
    assert view.blockers == ()


def test_unqualified_state_preserves_blockers_without_promotion():
    view = _explorer(qualified=False).claim_view("claim.test")
    assert view.qualification_state == "UNQUALIFIED"
    assert view.current_head_qualified is False
    assert "Build not accepted." in view.blockers
    assert "Not yet qualified." in view.blockers


def test_mismatched_artifact_is_conflict_even_if_registry_and_ledger_say_pass():
    contracts = _contracts()
    view = ProofExplorer(
        _registry(qualified=True, proof_hash="a" * 64),
        _ledger(contracts, qualified=True, proof_hash="b" * 64),
        contracts,
    ).claim_view("claim.test")
    assert view.qualification_state == "CONFLICT"
    assert any("artifact SHA-256" in blocker for blocker in view.blockers)


def test_mismatched_contract_hash_is_conflict():
    view = _explorer(qualified=True, contract_hash="f" * 64).claim_view("claim.test")
    assert view.qualification_state == "CONFLICT"
    assert any("proof-contract SHA-256" in blocker for blocker in view.blockers)


def test_runtime_record_does_not_become_release_qualification():
    record = VerificationRecord(
        verifier="synthetic",
        kind=EvidenceKind.FORMAL,
        claim="Synthetic runtime check.",
        state=VerificationState.PASS,
        method="test",
        metrics={"claim_id": "claim.test"},
    )
    explorer = _explorer(qualified=False)
    view = explorer.claim_view("claim.test", [record])
    assert view.current_head_qualified is False
    assert view.runtime_evidence[0].canonical_claim_bound is True


def test_unbound_runtime_record_is_explicit():
    record = VerificationRecord(
        verifier="synthetic",
        kind=EvidenceKind.NUMERICAL,
        claim="Numerical check.",
        state=VerificationState.PASS,
        method="test",
        metrics={},
    )
    view = _explorer(qualified=False).claim_view("claim.test", [record])
    assert view.runtime_evidence[0].canonical_claim_bound is False


def test_module_resolution_uses_registry_then_formal_artifact_fallback():
    explorer = _explorer(qualified=False)
    direct = explorer.for_module("module.test")
    fallback = explorer.for_module("module.other", formal_artifact="claim.test")
    missing = explorer.for_module("module.other", formal_artifact="unknown")
    assert direct is not None and direct.claim_id == "claim.test"
    assert fallback is not None and fallback.claim_id == "claim.test"
    assert missing is None


def test_default_v330_exposes_authoritative_contract_and_canonical_qualification_state():
    claim_id = "cace.v330.continuum-proof-strengthening"
    registry = ClaimRegistry.load_default()
    ledger = ProofLedger.load_default()
    claim = registry.by_id(claim_id)
    ledger_entry = ledger.for_claim(claim_id)
    contract = ProofContractRegistry.load_default().for_claim(claim_id)
    assert claim is not None
    assert ledger_entry is not None
    assert contract is not None

    assert claim.current_head_qualified == ledger_entry.current_head_qualified
    assert claim.attested_commit == ledger_entry.commit
    assert claim.proof_artifact_sha256 == ledger_entry.proof_artifact_sha256

    view = ProofExplorer().claim_view(claim_id)
    assert view.current_head_qualified is claim.current_head_qualified
    assert view.qualification_state == (
        "QUALIFIED" if claim.current_head_qualified else "UNQUALIFIED"
    )
    assert view.attested_commit == claim.attested_commit
    assert view.proof_artifact_sha256 == claim.proof_artifact_sha256
    assert view.proof_contract_id == contract.contract_id
    assert view.proof_contract_sha256 == contract.contract_sha256
    assert view.proof_contract_build_target == contract.build_target
    assert view.endpoint_theorems == contract.endpoint_theorems
    assert view.audited_source_files == contract.audited_source_files
    assert view.allowed_axioms == contract.allowed_axioms
    assert view.required_checks == contract.required_checks
    assert view.theorem_dependency_metadata_state == contract.theorem_dependency_metadata_state
    assert view.theorem_dependency_metadata_note == contract.theorem_dependency_metadata_note

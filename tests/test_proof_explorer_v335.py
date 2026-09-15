from __future__ import annotations

from cace_studio.core.claim_registry import ClaimRegistry
from cace_studio.core.proof_explorer import ProofExplorer
from cace_studio.core.proof_ledger import ProofLedger
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState


COMMIT = "1" * 40
HASH = "a" * 64


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


def _ledger(*, qualified: bool, proof_hash: str = HASH) -> ProofLedger:
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
                    "workflow_run_id": 123 if qualified else None,
                    "checks": ["pinned build", "axiom audit"] if qualified else [],
                    "blockers": [] if qualified else ["Build not accepted."],
                }
            ],
        }
    )


def test_exact_registry_ledger_match_is_qualified():
    view = ProofExplorer(_registry(qualified=True), _ledger(qualified=True)).claim_view(
        "claim.test"
    )
    assert view.qualification_state == "QUALIFIED"
    assert view.current_head_qualified is True
    assert view.attested_commit == COMMIT
    assert view.proof_artifact_sha256 == HASH
    assert view.blockers == ()


def test_unqualified_state_preserves_blockers_without_promotion():
    view = ProofExplorer(_registry(qualified=False), _ledger(qualified=False)).claim_view(
        "claim.test"
    )
    assert view.qualification_state == "UNQUALIFIED"
    assert view.current_head_qualified is False
    assert "Build not accepted." in view.blockers
    assert "Not yet qualified." in view.blockers


def test_mismatched_artifact_is_conflict_even_if_both_sources_say_pass():
    view = ProofExplorer(
        _registry(qualified=True, proof_hash="a" * 64),
        _ledger(qualified=True, proof_hash="b" * 64),
    ).claim_view("claim.test")
    assert view.qualification_state == "CONFLICT"
    assert view.current_head_qualified is False
    assert any("artifact SHA-256" in blocker for blocker in view.blockers)


def test_runtime_record_does_not_become_release_qualification():
    record = VerificationRecord(
        verifier="synthetic",
        kind=EvidenceKind.FORMAL,
        claim="Synthetic runtime check.",
        state=VerificationState.PASS,
        method="test",
        metrics={"claim_id": "claim.test"},
    )
    view = ProofExplorer(_registry(qualified=False), _ledger(qualified=False)).claim_view(
        "claim.test", [record]
    )
    assert view.current_head_qualified is False
    assert len(view.runtime_evidence) == 1
    assert view.runtime_evidence[0].state == "pass"
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
    view = ProofExplorer(_registry(qualified=False), _ledger(qualified=False)).claim_view(
        "claim.test", [record]
    )
    assert view.runtime_evidence[0].canonical_claim_bound is False


def test_module_resolution_uses_registry_then_formal_artifact_fallback():
    explorer = ProofExplorer(_registry(qualified=False), _ledger(qualified=False))
    direct = explorer.for_module("module.test")
    fallback = explorer.for_module("module.other", formal_artifact="claim.test")
    missing = explorer.for_module("module.other", formal_artifact="unknown")
    assert direct is not None and direct.claim_id == "claim.test"
    assert fallback is not None and fallback.claim_id == "claim.test"
    assert missing is None


def test_default_catalog_keeps_current_v330_unqualified():
    explorer = ProofExplorer()
    view = explorer.claim_view("cace.v330.continuum-proof-strengthening")
    assert view.current_head_qualified is False
    assert view.qualification_state == "UNQUALIFIED"

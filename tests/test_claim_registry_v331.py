from copy import deepcopy

import pytest

from cace_studio.core.claim_registry import ClaimRegistry
from cace_studio.core.formal_gate import enforce_formal_claim_qualification
from cace_studio.core.proof_ledger import ProofLedger
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState


def rec(kind=EvidenceKind.FORMAL, state=VerificationState.PASS):
    return VerificationRecord(
        verifier="unit",
        kind=kind,
        claim="unit claim",
        state=state,
        method="unit-method",
    )


def qualified_claim_mapping():
    return {
        "schema_version": 1,
        "policy": "fail-closed",
        "claims": [
            {
                "claim_id": "unit.claim",
                "module_ids": ["unit.module"],
                "statement": "unit statement",
                "scope": "unit",
                "evidence_ceiling": "formally-verified",
                "qualification": {
                    "status": "PASS",
                    "current_head_qualified": True,
                    "attested_commit": "b" * 40,
                    "proof_artifact_sha256": "a" * 64,
                    "reason": "",
                },
                "nonclaims": [],
            }
        ],
    }


def qualified_ledger_mapping():
    return {
        "schema_version": 1,
        "policy": "fail-closed",
        "entries": [
            {
                "release": "unit",
                "claim_ids": ["unit.claim"],
                "status": "PASS",
                "current_head_qualified": True,
                "commit": "b" * 40,
                "proof_artifact_sha256": "a" * 64,
                "workflow_run_id": 1,
                "checks": ["pinned-build", "axiom-audit"],
                "blockers": [],
            }
        ],
    }


def test_default_registry_and_ledger_load_fail_closed():
    registry = ClaimRegistry.load_default()
    ledger = ProofLedger.load_default()
    assert registry.schema_version == 1
    assert ledger.schema_version == 1
    historical = registry.by_id("cace.v322.concrete-mesh-prager-synge")
    assert historical is not None
    assert historical.current_head_qualified is False
    entry = ledger.for_claim(historical.claim_id)
    assert entry is not None
    assert entry.status == "HISTORICAL_PASS"
    assert entry.current_head_qualified is False


def test_unknown_formal_pass_is_downgraded():
    out = enforce_formal_claim_qualification("unregistered.module", [rec()])
    assert out[0].state is VerificationState.NOT_RUN
    assert out[0].metrics["formal_gate_reason"] == "claim-registry-entry-missing"


def test_historical_formal_pass_is_not_inherited_by_current_head():
    out = enforce_formal_claim_qualification(
        "formal322.concrete_mesh_certificate_prager_synge", [rec()]
    )
    assert out[0].state is VerificationState.NOT_RUN
    assert "proof-ledger-current-head-qualification-missing" in out[0].metrics[
        "formal_gate_blockers"
    ]


def test_nonformal_and_existing_fail_states_are_not_upgraded():
    numerical = enforce_formal_claim_qualification(
        "unregistered.module", [rec(EvidenceKind.NUMERICAL)]
    )[0]
    failure = enforce_formal_claim_qualification(
        "unregistered.module", [rec(EvidenceKind.FORMAL, VerificationState.FAIL)]
    )[0]
    assert numerical.state is VerificationState.PASS
    assert failure.state is VerificationState.FAIL


def test_matching_current_head_registry_and_ledger_preserve_formal_pass():
    registry = ClaimRegistry.from_mapping(qualified_claim_mapping())
    ledger = ProofLedger.from_mapping(qualified_ledger_mapping())
    out = enforce_formal_claim_qualification(
        "unit.module", [rec()], registry=registry, ledger=ledger
    )[0]
    assert out.state is VerificationState.PASS
    assert out.metrics["formal_gate"] == "PASS"
    assert out.metrics["claim_id"] == "unit.claim"
    assert out.metrics["proof_artifact_sha256"] == "a" * 64
    assert out.metrics["workflow_run_id"] == 1


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("qualification", "status"), "NOT_RUN"),
        (("qualification", "attested_commit"), None),
        (("qualification", "attested_commit"), "b" * 39),
        (("qualification", "proof_artifact_sha256"), None),
        (("qualification", "proof_artifact_sha256"), "a" * 63),
        (("evidence_ceiling",), "symbolic"),
    ],
)
def test_current_head_claim_rejects_incomplete_or_nonformal_qualification(path, value):
    raw = qualified_claim_mapping()
    target = raw["claims"][0]
    if len(path) == 1:
        target[path[0]] = value
    else:
        target[path[0]][path[1]] = value
    with pytest.raises(ValueError):
        ClaimRegistry.from_mapping(raw)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "NOT_RUN"),
        ("commit", None),
        ("proof_artifact_sha256", None),
        ("workflow_run_id", None),
        ("workflow_run_id", 0),
        ("checks", []),
        ("blockers", ["open-obligation"]),
    ],
)
def test_current_head_ledger_rejects_incomplete_provenance(field, value):
    raw = qualified_ledger_mapping()
    raw["entries"][0][field] = value
    with pytest.raises(ValueError):
        ProofLedger.from_mapping(raw)

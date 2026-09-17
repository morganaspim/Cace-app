from copy import deepcopy
from pathlib import Path

import pytest

from cace_studio.core.claim_registry import ClaimRegistry
from cace_studio.core.formal_gate import enforce_formal_claim_qualification
from cace_studio.core.proof_contract import (
    ProofContractRegistry,
    executable_source_bundle_sha256,
)
from cace_studio.core.proof_ledger import ProofLedger
from cace_studio.core.qualification_drift import audit_current_qualifications
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState


CONTRACT_ID = "unit.proof.v1"
ROOT = Path(__file__).resolve().parents[1]


def rec(kind=EvidenceKind.FORMAL, state=VerificationState.PASS):
    return VerificationRecord(
        verifier="unit",
        kind=kind,
        claim="unit claim",
        state=state,
        method="unit-method",
    )


def qualified_contracts(source_root=None) -> ProofContractRegistry:
    contract = {
        "contract_id": CONTRACT_ID,
        "claim_id": "unit.claim",
        "formal_system": "lean4",
        "build_target": "Unit.Audit",
        "toolchain_file": "formal/unit/lean-toolchain",
        "dependency_pins": {"mathlib_commit": "1" * 40},
        "endpoint_theorems": ["Unit.endpoint"],
        "audited_source_files": ["Unit/Audit.lean"],
        "allowed_axioms": ["propext"],
        "required_checks": ["pinned-build", "axiom-audit"],
        "nonclaims": ["Not a broader theorem."],
        "theorem_dependency_metadata": {
            "state": "NOT_GENERATED",
            "note": "No theorem-to-theorem dependency data generated.",
        },
    }
    if source_root is not None:
        source = source_root / "unit_runtime.py"
        if not source.exists():
            source.write_text("VALUE = 1\n", encoding="utf-8")
        contract["executable_bindings"] = [
            {
                "module_id": "unit.module",
                "source_files": ["unit_runtime.py"],
                "source_bundle_sha256": executable_source_bundle_sha256(
                    source_root, ["unit_runtime.py"]
                ),
            }
        ]
    return ProofContractRegistry.from_mapping(
        {
            "schema_version": 1,
            "policy": "fail-closed",
            "contracts": [contract],
        }
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
                "proof_contract_id": CONTRACT_ID,
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


def qualified_ledger_mapping(contract_sha256: str):
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
                "proof_contract_id": CONTRACT_ID,
                "proof_contract_sha256": contract_sha256,
                "qualification_system": "portable-local",
                "qualification_run_id": "unit-run-1",
                "workflow_run_id": None,
                "checks": ["pinned-build", "axiom-audit"],
                "blockers": [],
            }
        ],
    }


def test_default_registry_ledger_and_contract_load_fail_closed():
    registry = ClaimRegistry.load_default()
    ledger = ProofLedger.load_default()
    contracts = ProofContractRegistry.load_default()
    assert registry.schema_version == ledger.schema_version == contracts.schema_version == 1
    historical = registry.by_id("cace.v322.concrete-mesh-prager-synge")
    assert historical is not None and historical.current_head_qualified is False
    entry = ledger.for_claim(historical.claim_id)
    assert entry is not None and entry.status == "HISTORICAL_PASS"
    assert entry.qualification_system == "github-actions"
    v330 = registry.by_id("cace.v330.continuum-proof-strengthening")
    contract = contracts.for_claim("cace.v330.continuum-proof-strengthening")
    current_entry = ledger.for_claim("cace.v330.continuum-proof-strengthening")
    assert v330 is not None and contract is not None and current_entry is not None
    assert v330.proof_contract_id == contract.contract_id

    if current_entry.proof_contract_sha256 == contract.contract_sha256:
        return

    # A proof-contract transition is allowed only while Git drift independently
    # proves that the old qualification is stale. This avoids the bootstrap
    # deadlock where a new contract could never reach the qualification workflow,
    # while still rejecting an unexplained ledger/contract mismatch on a clean tree.
    drift = next(
        item
        for item in audit_current_qualifications(ROOT, registry=registry, ledger=ledger)
        if item.claim_id == v330.claim_id
    )
    assert drift.passed is False
    assert "cace_studio/data/proof_contracts.json" in drift.sensitive_paths


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


def test_matching_claim_contract_executable_and_portable_ledger_preserve_formal_pass(tmp_path):
    contracts = qualified_contracts(tmp_path)
    contract = contracts.for_claim("unit.claim")
    registry = ClaimRegistry.from_mapping(qualified_claim_mapping())
    ledger = ProofLedger.from_mapping(qualified_ledger_mapping(contract.contract_sha256))
    out = enforce_formal_claim_qualification(
        "unit.module",
        [rec()],
        registry=registry,
        ledger=ledger,
        contracts=contracts,
        source_root=tmp_path,
    )[0]
    assert out.state is VerificationState.PASS
    assert out.metrics["formal_gate"] == "PASS"
    assert out.metrics["proof_contract_id"] == CONTRACT_ID
    assert out.metrics["proof_contract_sha256"] == contract.contract_sha256
    assert out.metrics["qualification_system"] == "portable-local"
    assert out.metrics["executable_binding_module_id"] == "unit.module"
    assert (
        out.metrics["executable_source_bundle_sha256_current"]
        == out.metrics["executable_source_bundle_sha256_expected"]
    )
    assert "workflow_run_id" not in out.metrics


def test_formal_pass_without_executable_binding_is_downgraded():
    contracts = qualified_contracts()
    contract = contracts.for_claim("unit.claim")
    registry = ClaimRegistry.from_mapping(qualified_claim_mapping())
    ledger = ProofLedger.from_mapping(qualified_ledger_mapping(contract.contract_sha256))
    out = enforce_formal_claim_qualification(
        "unit.module", [rec()], registry=registry, ledger=ledger, contracts=contracts
    )[0]
    assert out.state is VerificationState.NOT_RUN
    assert "proof-contract-executable-binding-missing" in out.metrics["formal_gate_blockers"]


def test_bound_executable_byte_mutation_downgrades_formal_pass(tmp_path):
    contracts = qualified_contracts(tmp_path)
    contract = contracts.for_claim("unit.claim")
    registry = ClaimRegistry.from_mapping(qualified_claim_mapping())
    ledger = ProofLedger.from_mapping(qualified_ledger_mapping(contract.contract_sha256))
    (tmp_path / "unit_runtime.py").write_text("VALUE = 2\n", encoding="utf-8")

    out = enforce_formal_claim_qualification(
        "unit.module",
        [rec()],
        registry=registry,
        ledger=ledger,
        contracts=contracts,
        source_root=tmp_path,
    )[0]
    assert out.state is VerificationState.NOT_RUN
    assert "executable-source-bundle-hash-mismatch" in out.metrics["formal_gate_blockers"]
    assert (
        out.metrics["executable_source_bundle_sha256_current"]
        != out.metrics["executable_source_bundle_sha256_expected"]
    )


def test_unrelated_file_mutation_does_not_invalidate_bound_executable(tmp_path):
    contracts = qualified_contracts(tmp_path)
    contract = contracts.for_claim("unit.claim")
    registry = ClaimRegistry.from_mapping(qualified_claim_mapping())
    ledger = ProofLedger.from_mapping(qualified_ledger_mapping(contract.contract_sha256))
    unrelated = tmp_path / "unrelated.py"
    unrelated.write_text("VALUE = 1\n", encoding="utf-8")
    unrelated.write_text("VALUE = 2\n", encoding="utf-8")

    out = enforce_formal_claim_qualification(
        "unit.module",
        [rec()],
        registry=registry,
        ledger=ledger,
        contracts=contracts,
        source_root=tmp_path,
    )[0]
    assert out.state is VerificationState.PASS


def test_missing_bound_executable_source_downgrades_formal_pass(tmp_path):
    contracts = qualified_contracts(tmp_path)
    contract = contracts.for_claim("unit.claim")
    registry = ClaimRegistry.from_mapping(qualified_claim_mapping())
    ledger = ProofLedger.from_mapping(qualified_ledger_mapping(contract.contract_sha256))
    (tmp_path / "unit_runtime.py").unlink()

    out = enforce_formal_claim_qualification(
        "unit.module",
        [rec()],
        registry=registry,
        ledger=ledger,
        contracts=contracts,
        source_root=tmp_path,
    )[0]
    assert out.state is VerificationState.NOT_RUN
    assert "executable-source-missing:unit_runtime.py" in out.metrics["formal_gate_blockers"]


def test_contract_hash_drift_downgrades_formal_pass():
    contracts = qualified_contracts()
    contract = contracts.for_claim("unit.claim")
    registry = ClaimRegistry.from_mapping(qualified_claim_mapping())
    raw = qualified_ledger_mapping("f" * 64)
    ledger = ProofLedger.from_mapping(raw)
    out = enforce_formal_claim_qualification(
        "unit.module", [rec()], registry=registry, ledger=ledger, contracts=contracts
    )[0]
    assert out.state is VerificationState.NOT_RUN
    assert "proof-contract-hash-mismatch" in out.metrics["formal_gate_blockers"]


def test_missing_contract_required_check_downgrades_formal_pass():
    contracts = qualified_contracts()
    contract = contracts.for_claim("unit.claim")
    registry = ClaimRegistry.from_mapping(qualified_claim_mapping())
    raw = qualified_ledger_mapping(contract.contract_sha256)
    raw["entries"][0]["checks"] = ["pinned-build"]
    ledger = ProofLedger.from_mapping(raw)
    out = enforce_formal_claim_qualification(
        "unit.module", [rec()], registry=registry, ledger=ledger, contracts=contracts
    )[0]
    assert out.state is VerificationState.NOT_RUN
    assert any(
        blocker.startswith("proof-contract-required-checks-missing:")
        for blocker in out.metrics["formal_gate_blockers"]
    )


def test_legacy_github_workflow_id_is_upgraded_to_generic_provenance():
    contract = qualified_contracts().for_claim("unit.claim")
    raw = qualified_ledger_mapping(contract.contract_sha256)
    entry = raw["entries"][0]
    entry.pop("qualification_system")
    entry.pop("qualification_run_id")
    entry["workflow_run_id"] = 123
    ledger = ProofLedger.from_mapping(raw)
    parsed = ledger.entries[0]
    assert parsed.qualification_system == "github-actions"
    assert parsed.qualification_run_id == "123"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("qualification", "status"), "NOT_RUN"),
        (("qualification", "attested_commit"), None),
        (("qualification", "proof_artifact_sha256"), None),
        (("evidence_ceiling",), "symbolic"),
        (("proof_contract_id",), None),
    ],
)
def test_current_head_claim_rejects_incomplete_qualification(path, value):
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
        ("proof_contract_id", None),
        ("proof_contract_sha256", None),
        ("qualification_system", None),
        ("qualification_run_id", None),
        ("checks", []),
        ("blockers", ["open-obligation"]),
    ],
)
def test_current_head_ledger_rejects_incomplete_provenance(field, value):
    contract = qualified_contracts().for_claim("unit.claim")
    raw = qualified_ledger_mapping(contract.contract_sha256)
    raw["entries"][0][field] = value
    with pytest.raises(ValueError):
        ProofLedger.from_mapping(raw)


def test_github_actions_current_head_still_requires_positive_workflow_run_id():
    contract = qualified_contracts().for_claim("unit.claim")
    raw = qualified_ledger_mapping(contract.contract_sha256)
    entry = raw["entries"][0]
    entry["qualification_system"] = "github-actions"
    entry["qualification_run_id"] = "gha-1"
    entry["workflow_run_id"] = None
    with pytest.raises(ValueError, match="workflow_run_id"):
        ProofLedger.from_mapping(raw)

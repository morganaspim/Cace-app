from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

from cace_studio.core.module import ExecutionContext
from cace_studio.core.proof_contract import (
    ExecutableBindingError,
    ProofContract,
    ProofContractRegistry,
    executable_source_bundle_sha256,
)
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationState
from cace_studio.modules.formal_v330 import (
    DEFAULT_THEOREM,
    FormalV330QualifiedTheoremEndpoint,
    MODULE_ID,
)


EXPECTED_CONTINUUM_V3_HASH = "d1d34295f6c9821af0330435af781e4f28c263076259b0b0075e4c9580ee8e8d"
EXPECTED_FORMAL330_BUNDLE = "3515625ff1da523f0925c1f342670d84df6fd4d1ac73aa09aa7cae1374cafab0"
EXPECTED_HYPOTHESIS_BRIDGE_BUNDLE = "b4b8fd30eba2c99cc911486e866e80c16efda76316dce69a7ace853bf95b027c"
ROOT = Path(__file__).parents[1]
SOURCE_BINDING_SCRIPT = ROOT / "scripts" / "verify_v330_qualification_source_binding.py"
AXIOM_AUDIT_SCRIPT = ROOT / "scripts" / "audit_v330_axioms.py"
THEOREM_METADATA_SOURCE = ROOT / "formal" / "cace_formal" / "CACEFormal" / "V330TheoremMetadata.lean"


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


def _source_binding_verifier():
    spec = importlib.util.spec_from_file_location("source_binding_verifier_v340", SOURCE_BINDING_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _axiom_audit_module():
    spec = importlib.util.spec_from_file_location("axiom_audit_v330", AXIOM_AUDIT_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v330_axiom_audit_uses_contract_canonical_environment_theorem_names():
    audit = _axiom_audit_module()
    contract = ProofContractRegistry.load_default().for_claim(
        "cace.v330.continuum-proof-strengthening"
    )
    assert contract is not None

    raw = "\n".join(
        f"{audit.METADATA_SENTINEL}{audit.json.dumps({'theorem': theorem}, sort_keys=True)}"
        for theorem in contract.endpoint_theorems
    )
    assert audit.validate_environment_metadata_theorems(
        raw, contract.endpoint_theorems
    ) == set(contract.endpoint_theorems)

    mismatched = list(contract.endpoint_theorems)
    mismatched[0] = mismatched[0].rsplit(".", 1)[-1]
    bad_raw = "\n".join(
        f"{audit.METADATA_SENTINEL}{audit.json.dumps({'theorem': theorem}, sort_keys=True)}"
        for theorem in mismatched
    )
    with pytest.raises(ValueError, match="theorem set differs from proof contract"):
        audit.validate_environment_metadata_theorems(bad_raw, contract.endpoint_theorems)


def test_v330_environment_metadata_exporter_exactly_matches_proof_contract_endpoints():
    contract = ProofContractRegistry.load_default().for_claim(
        "cace.v330.continuum-proof-strengthening"
    )
    assert contract is not None
    source = THEOREM_METADATA_SOURCE.read_text(encoding="utf-8")
    exported = tuple(
        line.strip()[2:].removesuffix(",")
        for line in source.splitlines()
        if line.strip().startswith("``CACEFormal.")
    )
    assert exported == contract.endpoint_theorems


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
    assert "independent-source-bound-verification" in contract.required_checks
    assert "executable-source-binding" in contract.required_checks
    assert "CACEFormal.Continuum.continuumPragerSynge_of_weakGreen" in contract.endpoint_theorems
    assert "CACEFormal.Continuum.hasZeroBoundaryTrace_zero" in contract.endpoint_theorems
    assert "CACEFormal.Continuum.inH1_of_mem_H1DistributionalGraphSubmodule" in contract.endpoint_theorems
    assert "CACEFormal.Continuum.inH1_iff_exists_distributionalGraphRepresentative" in contract.endpoint_theorems
    assert "CACEFormal/WeakGreenFunctional.lean" in contract.audited_source_files
    assert "CACEFormal/H1GraphConverse.lean" in contract.audited_source_files
    assert any("executable binding certifies theorem-endpoint membership" in item for item in contract.nonclaims)
    assert any("hasZeroBoundaryTrace_zero endpoint discharges only" in item for item in contract.nonclaims)
    assert len(contract.executable_bindings) == 3

    binding = contract.executable_binding_for_module(MODULE_ID)
    assert binding is not None
    assert binding.source_files == ("cace_studio/modules/formal_v330.py",)
    assert binding.source_bundle_sha256 == EXPECTED_FORMAL330_BUNDLE
    assert binding.current_source_bundle_sha256(ROOT) == EXPECTED_FORMAL330_BUNDLE

    for bridge_module_id in (
        "formal_bridge.resolve_prager_synge_zero_trace",
        "formal_bridge.zero_boundary_trace_zero",
    ):
        bridge_binding = contract.executable_binding_for_module(bridge_module_id)
        assert bridge_binding is not None
        assert bridge_binding.source_files == (
            "cace_studio/modules/formal_hypothesis_bridges.py",
        )
        assert bridge_binding.source_bundle_sha256 == EXPECTED_HYPOTHESIS_BRIDGE_BUNDLE
        assert bridge_binding.current_source_bundle_sha256(ROOT) == EXPECTED_HYPOTHESIS_BRIDGE_BUNDLE

    assert contract.contract_sha256 == EXPECTED_CONTINUUM_V3_HASH


def test_formal330_bridge_emits_formal_candidate_only_for_canonical_endpoint():
    module = FormalV330QualifiedTheoremEndpoint()
    ctx = ExecutionContext(run_id="unit", seed=0)

    params = module.resolved_params({})
    assert params["theorem_name"] == DEFAULT_THEOREM
    outputs = module.execute({}, params, ctx)
    record = module.verify({}, params, outputs, ctx)[0]
    assert record.kind is EvidenceKind.FORMAL
    assert record.state is VerificationState.PASS
    assert outputs["result"]["endpoint_member"] is True
    assert "does not establish that runtime PDE data satisfy" in record.notes[0]

    bad_params = module.resolved_params({"theorem_name": "CACEFormal.Continuum.not_a_theorem"})
    bad_outputs = module.execute({}, bad_params, ctx)
    bad_record = module.verify({}, bad_params, bad_outputs, ctx)[0]
    assert bad_outputs["result"]["endpoint_member"] is False
    assert bad_record.state is VerificationState.FAIL


def test_independent_verifier_rehashes_executable_bindings_and_detects_drift(tmp_path):
    verifier = _source_binding_verifier()
    runtime = tmp_path / "runtime.py"
    runtime.write_text("VALUE = 1\n", encoding="utf-8")
    digest = verifier.executable_source_bundle_sha256(tmp_path, ("runtime.py",))
    contract = {
        "required_checks": ["executable-source-binding"],
        "executable_bindings": [
            {
                "module_id": "unit.module",
                "source_files": ["runtime.py"],
                "source_bundle_sha256": digest,
            }
        ],
    }
    report = verifier.verify_executable_bindings(contract, repo_root=tmp_path)
    assert report == [
        {
            "module_id": "unit.module",
            "source_files": ["runtime.py"],
            "source_bundle_sha256": digest,
        }
    ]

    runtime.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(verifier.SourceBindingVerificationError, match="executable source bundle"):
        verifier.verify_executable_bindings(contract, repo_root=tmp_path)


def test_independent_verifier_rejects_binding_without_required_check(tmp_path):
    verifier = _source_binding_verifier()
    runtime = tmp_path / "runtime.py"
    runtime.write_text("VALUE = 1\n", encoding="utf-8")
    digest = verifier.executable_source_bundle_sha256(tmp_path, ("runtime.py",))
    contract = {
        "required_checks": ["lean-build"],
        "executable_bindings": [
            {
                "module_id": "unit.module",
                "source_files": ["runtime.py"],
                "source_bundle_sha256": digest,
            }
        ],
    }
    with pytest.raises(verifier.SourceBindingVerificationError, match="without executable-source-binding"):
        verifier.verify_executable_bindings(contract, repo_root=tmp_path)


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


def test_empty_executable_binding_layer_preserves_existing_contract_identity():
    raw = _contract_mapping()
    explicit_empty = deepcopy(raw)
    explicit_empty["executable_bindings"] = []
    assert ProofContract.from_mapping(raw).contract_sha256 == ProofContract.from_mapping(
        explicit_empty
    ).contract_sha256


def test_executable_binding_is_content_addressed_and_detects_byte_drift(tmp_path):
    source = tmp_path / "unit_runtime.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    digest = executable_source_bundle_sha256(tmp_path, ["unit_runtime.py"])

    raw = _contract_mapping()
    raw["executable_bindings"] = [
        {
            "module_id": "unit.module",
            "source_files": ["unit_runtime.py"],
            "source_bundle_sha256": digest,
        }
    ]
    contract = ProofContract.from_mapping(raw)
    binding = contract.executable_binding_for_module("unit.module")
    assert binding is not None
    assert binding.current_source_bundle_sha256(tmp_path) == digest
    assert contract.contract_sha256 != ProofContract.from_mapping(_contract_mapping()).contract_sha256

    source.write_text("VALUE = 2\n", encoding="utf-8")
    assert binding.current_source_bundle_sha256(tmp_path) != digest


def test_executable_bundle_rejects_missing_or_escaping_source(tmp_path):
    with pytest.raises(ExecutableBindingError, match="executable-source-missing"):
        executable_source_bundle_sha256(tmp_path, ["missing.py"])

    raw = _contract_mapping()
    raw["executable_bindings"] = [
        {
            "module_id": "unit.module",
            "source_files": ["../escape.py"],
            "source_bundle_sha256": "a" * 64,
        }
    ]
    with pytest.raises(ValueError, match="safe relative path"):
        ProofContract.from_mapping(raw)


def test_executable_binding_rejects_duplicate_module_id():
    raw = _contract_mapping()
    binding = {
        "module_id": "unit.module",
        "source_files": ["unit_runtime.py"],
        "source_bundle_sha256": "a" * 64,
    }
    raw["executable_bindings"] = [binding, deepcopy(binding)]
    with pytest.raises(ValueError, match="repeat a module_id"):
        ProofContract.from_mapping(raw)


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

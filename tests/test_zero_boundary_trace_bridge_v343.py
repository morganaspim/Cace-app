from __future__ import annotations

from copy import deepcopy
import json

from cace_studio.app import build_registry
from cace_studio.core.module import ExecutionContext
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.proof_ledger import ProofLedger
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationState
from cace_studio.modules.fem_continuum import (
    PragerSyngeHypothesisInventoryAdapter,
    PRAGER_SYNG_THEOREM,
)
from cace_studio.modules.formal_v330 import FormalV330QualifiedTheoremEndpoint
import cace_studio.modules.formal_hypothesis_bridges as bridges
from cace_studio.modules.formal_hypothesis_bridges import (
    ResolvePragerSyngeZeroTrace,
    ZeroBoundaryTraceZeroBridge,
    ZERO_TRACE_THEOREM,
)

CLAIM_ID = "cace.v330.continuum-proof-strengthening"
EXPECTED_CONTRACT_SHA256 = "d1d34295f6c9821af0330435af781e4f28c263076259b0b0075e4c9580ee8e8d"


def _endpoint(theorem_name: str) -> dict:
    module = FormalV330QualifiedTheoremEndpoint()
    params = module.resolved_params({"theorem_name": theorem_name})
    return dict(module.execute({}, params, ExecutionContext(run_id="bridge-endpoint"))["result"])


def _prager_packet() -> dict:
    module = PragerSyngeHypothesisInventoryAdapter()
    inputs = {
        "theorem_endpoint": _endpoint(PRAGER_SYNG_THEOREM),
        "e_grad": [1.0, 0.0],
        "e_flux": [0.0, 1.0],
    }
    params = module.resolved_params({})
    outputs = module.execute(inputs, params, ExecutionContext(run_id="prager-packet"))
    record = module.verify(inputs, params, outputs, ExecutionContext(run_id="prager-packet"))[0]
    assert record.state is VerificationState.PASS
    return dict(outputs["hypothesis_packet"])


def _bridge_output(vector) -> tuple[dict, VerificationState]:
    module = ZeroBoundaryTraceZeroBridge()
    inputs = {
        "theorem_endpoint": _endpoint(ZERO_TRACE_THEOREM),
        "vector": vector,
    }
    params = module.resolved_params({})
    ctx = ExecutionContext(run_id="zero-bridge")
    outputs = module.execute(inputs, params, ctx)
    record = module.verify(inputs, params, outputs, ctx)[0]
    return dict(outputs["bridge_certificate"]), record.state


def _resolved(packet: dict, certificate: dict) -> tuple[dict, VerificationState]:
    module = ResolvePragerSyngeZeroTrace()
    inputs = {
        "hypothesis_packet": packet,
        "bridge_certificate": certificate,
    }
    params = module.resolved_params({})
    ctx = ExecutionContext(run_id="resolve-zero-trace")
    outputs = module.execute(inputs, params, ctx)
    record = module.verify(inputs, params, outputs, ctx)[0]
    return dict(outputs["hypothesis_packet"]), record.state


def _digest_without(payload: dict, field: str) -> str:
    copy = json.loads(json.dumps(payload))
    embedded = copy.pop(field)
    assert bridges._canonical_sha256(copy) == embedded
    return embedded


def _synthetic_pass_anchor() -> dict:
    contract = ProofContractRegistry.load_default().for_claim(CLAIM_ID)
    assert contract is not None
    return {
        "state": "pass",
        "formal_gate": "PASS",
        "formal_gate_reason": None,
        "claim_id": CLAIM_ID,
        "proof_contract_id": contract.contract_id,
        "proof_contract_sha256": contract.contract_sha256,
        "attested_commit": "f" * 40,
        "proof_artifact_sha256": "a" * 64,
        "qualification_system": "github-actions",
        "qualification_run_id": "unit-qualified-run",
        "workflow_run_id": 1,
        "executable_source_bundle_sha256_expected": "b" * 64,
        "executable_source_bundle_sha256_current": "b" * 64,
    }


def test_v343_contract_adds_exact_zero_trace_endpoint_and_changes_identity():
    contract = ProofContractRegistry.load_default().for_claim(CLAIM_ID)
    assert contract is not None
    assert len(contract.endpoint_theorems) == 38
    assert ZERO_TRACE_THEOREM in contract.endpoint_theorems
    assert contract.contract_sha256 == EXPECTED_CONTRACT_SHA256
    assert any("hasZeroBoundaryTrace_zero endpoint discharges only" in item for item in contract.nonclaims)


def test_bridge_modules_are_registered_and_never_advertise_formal_evidence():
    registry = build_registry()
    for module_id in (
        "formal_bridge.zero_boundary_trace_zero",
        "formal_bridge.resolve_prager_synge_zero_trace",
    ):
        assert registry.contains(module_id)
        module = registry.create(module_id)
        assert EvidenceKind.FORMAL not in module.proof_status.evidence
        assert EvidenceKind.SYMBOLIC in module.proof_status.evidence


def test_canonical_qualification_anchor_tracks_contract_transition_fail_closed():
    contract = ProofContractRegistry.load_default().for_claim(CLAIM_ID)
    ledger = ProofLedger.load_default().for_claim(CLAIM_ID)
    assert contract is not None and ledger is not None
    anchor = bridges._qualification_anchor()
    if ledger.proof_contract_sha256 == contract.contract_sha256:
        assert anchor["state"] == "pass"
        assert anchor["formal_gate"] == "PASS"
        assert anchor["proof_contract_sha256"] == contract.contract_sha256
    else:
        assert anchor["state"] == "not-qualified"
        assert anchor["formal_gate"] == "NOT_RUN"
        assert ledger.proof_contract_sha256 != contract.contract_sha256


def test_exact_zero_bridge_is_pass_only_when_current_contract_is_qualified():
    certificate, state = _bridge_output([0.0, -0.0, 0.0])
    anchor = bridges._qualification_anchor()
    assert certificate["endpoint_descriptor_valid"] is True
    assert certificate["runtime_representation_exact_zero"] is True
    assert certificate["formal_instantiation"] == {"v": "0"}
    assert certificate["qualification_anchor"] == anchor
    assert _digest_without(certificate, "certificate_sha256")
    if anchor["state"] == "pass":
        assert certificate["state"] == "pass"
        assert state is VerificationState.PASS
    else:
        assert certificate["state"] == "not-qualified"
        assert state is VerificationState.NOT_RUN


def test_near_zero_is_not_zero_and_fails_without_tolerance(monkeypatch):
    monkeypatch.setattr(bridges, "_qualification_anchor", _synthetic_pass_anchor)
    certificate, state = _bridge_output([0.0, 1e-300, 0.0])
    assert certificate["runtime_representation_exact_zero"] is False
    assert certificate["formal_instantiation"] is None
    assert certificate["state"] == "fail"
    assert state is VerificationState.FAIL


def test_spoofed_endpoint_descriptor_fails_even_for_exact_zero(monkeypatch):
    monkeypatch.setattr(bridges, "_qualification_anchor", _synthetic_pass_anchor)
    endpoint = _endpoint(ZERO_TRACE_THEOREM)
    endpoint["proof_contract_sha256"] = "0" * 64
    module = ZeroBoundaryTraceZeroBridge()
    inputs = {"theorem_endpoint": endpoint, "vector": [0.0, 0.0]}
    params = module.resolved_params({})
    ctx = ExecutionContext(run_id="spoofed-zero-bridge")
    outputs = module.execute(inputs, params, ctx)
    record = module.verify(inputs, params, outputs, ctx)[0]
    certificate = outputs["bridge_certificate"]
    assert certificate["endpoint_descriptor_valid"] is False
    assert certificate["state"] == "fail"
    assert record.state is VerificationState.FAIL


def test_qualified_zero_bridge_resolves_exactly_hv_and_never_runtime_ready(monkeypatch):
    monkeypatch.setattr(bridges, "_qualification_anchor", _synthetic_pass_anchor)
    packet = _prager_packet()
    certificate, bridge_state = _bridge_output([0.0, 0.0])
    assert bridge_state is VerificationState.PASS
    resolved, resolver_state = _resolved(packet, certificate)
    assert resolver_state is VerificationState.PASS
    assert resolved["resolution_status"] == "applied"
    assert resolved["runtime_instantiations"] == {"v": "0"}
    assert resolved["runtime_ready"] is False
    assert resolved["formal_instantiation"] is False
    assert set(resolved["unresolved_hypotheses"]) == {
        "bounded-green-pairing",
        "green-smooth-core",
        "weak-green-cross-term-identity",
    }
    hypotheses = {item["id"]: item for item in resolved["theorem_explicit_hypotheses"]}
    assert hypotheses["zero-boundary-trace"]["state"] == "pass"
    assert hypotheses["zero-boundary-trace"]["bridge_theorem_name"] == ZERO_TRACE_THEOREM
    assert hypotheses["zero-boundary-trace"]["formal_instantiation"] == {"v": "0"}
    assert hypotheses["bounded-green-pairing"]["state"] == "unresolved"
    assert hypotheses["green-smooth-core"]["state"] == "unresolved"
    assert hypotheses["weak-green-cross-term-identity"]["state"] == "unresolved"
    assert resolved["applied_bridge_certificates"] == [certificate["certificate_sha256"]]
    assert resolved["packet_sha256"] != packet["packet_sha256"]
    assert _digest_without(resolved, "packet_sha256")


def test_real_transition_state_never_resolves_hv_before_current_qualification():
    packet = _prager_packet()
    certificate, bridge_state = _bridge_output([0.0, 0.0])
    resolved, resolver_state = _resolved(packet, certificate)
    anchor = bridges._qualification_anchor()
    if anchor["state"] == "pass":
        assert bridge_state is VerificationState.PASS
        assert resolver_state is VerificationState.PASS
        assert resolved["resolution_status"] == "applied"
        assert "zero-boundary-trace" not in resolved["unresolved_hypotheses"]
    else:
        assert bridge_state is VerificationState.NOT_RUN
        assert resolver_state is VerificationState.NOT_RUN
        assert resolved["resolution_status"] == "rejected"
        assert set(resolved["unresolved_hypotheses"]) == {
            "bounded-green-pairing",
            "green-smooth-core",
            "zero-boundary-trace",
            "weak-green-cross-term-identity",
        }


def test_tampered_bridge_certificate_is_rejected_even_with_qualified_anchor(monkeypatch):
    monkeypatch.setattr(bridges, "_qualification_anchor", _synthetic_pass_anchor)
    packet = _prager_packet()
    certificate, state = _bridge_output([0.0, 0.0])
    assert state is VerificationState.PASS
    tampered = deepcopy(certificate)
    tampered["runtime_representation"]["coordinates"][0] = 1.0
    resolved, resolver_state = _resolved(packet, tampered)
    assert resolver_state is VerificationState.FAIL
    assert resolved["bridge_structural_valid"] is False
    assert resolved["resolution_status"] == "rejected"
    assert "zero-boundary-trace" in resolved["unresolved_hypotheses"]


def test_tampered_prager_packet_is_rejected_even_with_valid_bridge(monkeypatch):
    monkeypatch.setattr(bridges, "_qualification_anchor", _synthetic_pass_anchor)
    packet = _prager_packet()
    certificate, state = _bridge_output([0.0, 0.0])
    assert state is VerificationState.PASS
    tampered = deepcopy(packet)
    tampered["theorem_explicit_hypotheses"][0]["state"] = "pass"
    resolved, resolver_state = _resolved(tampered, certificate)
    assert resolver_state is VerificationState.FAIL
    assert resolved["base_packet_valid"] is False
    assert resolved["resolution_status"] == "rejected"

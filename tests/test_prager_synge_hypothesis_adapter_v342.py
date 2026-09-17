from __future__ import annotations

import hashlib
import json

from cace_studio.app import build_registry
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationState
from cace_studio.modules.fem_continuum import (
    HYPOTHESIS_PACKET_SCHEMA,
    PRAGER_SYNG_THEOREM,
    RIEZ_CLAIM_ID,
)

ADAPTER_ID = "fem_cont.prager_synge_hypothesis_adapter"
FORMAL_ENDPOINT_ID = "formal330.qualified_theorem_endpoint"
EXPECTED_UNRESOLVED = {
    "bounded-green-pairing",
    "green-smooth-core",
    "zero-boundary-trace",
    "weak-green-cross-term-identity",
}


def _canonical_hash_without_embedded_digest(packet: dict) -> str:
    payload = dict(packet)
    embedded = payload.pop("packet_sha256")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    assert digest == embedded
    return digest


def _current_endpoint_descriptor() -> dict:
    contract = ProofContractRegistry.load_default().for_claim(RIEZ_CLAIM_ID)
    assert contract is not None
    assert PRAGER_SYNG_THEOREM in contract.endpoint_theorems
    return {
        "claim_id": RIEZ_CLAIM_ID,
        "theorem_name": PRAGER_SYNG_THEOREM,
        "endpoint_member": True,
        "proof_contract_id": contract.contract_id,
        "proof_contract_sha256": contract.contract_sha256,
        "scope_note": "test descriptor",
    }


def test_prager_synge_adapter_registered_and_never_declares_formal_evidence():
    registry = build_registry()
    assert registry.contains(ADAPTER_ID)
    module = registry.create(ADAPTER_ID)
    assert EvidenceKind.SYMBOLIC in module.proof_status.evidence
    assert EvidenceKind.INTERVAL in module.proof_status.evidence
    assert EvidenceKind.FORMAL not in module.proof_status.evidence


def test_orthogonal_numeric_vectors_do_not_discharge_abstract_prager_synge_hypotheses():
    experiment = Experiment(
        name="rank9-prager-synge-obligation-inventory",
        nodes=[
            Node("formal", FORMAL_ENDPOINT_ID, {"theorem_name": PRAGER_SYNG_THEOREM}),
            Node("adapter", ADAPTER_ID),
        ],
        edges=[Edge("formal", "result", "adapter", "theorem_endpoint")],
    )
    result = GraphExecutor(build_registry()).run(
        experiment,
        external_inputs={
            "adapter": {
                "e_grad": [1.0, 0.0],
                "e_flux": [0.0, 2.0],
            }
        },
    )

    formal_records = result.verification["formal"]
    assert any(
        record.kind is EvidenceKind.FORMAL and record.state is VerificationState.PASS
        for record in formal_records
    )

    adapter_records = result.verification["adapter"]
    assert len(adapter_records) == 2
    assert all(record.kind is not EvidenceKind.FORMAL for record in adapter_records)
    assert all(record.state is VerificationState.PASS for record in adapter_records)

    packet = result.outputs["adapter"]["hypothesis_packet"]
    assert packet["schema"] == HYPOTHESIS_PACKET_SCHEMA
    assert packet["theorem_name"] == PRAGER_SYNG_THEOREM
    assert packet["runtime_ready"] is False
    assert packet["formal_instantiation"] is False
    assert set(packet["unresolved_hypotheses"]) == EXPECTED_UNRESOLVED
    assert len(_canonical_hash_without_embedded_digest(packet)) == 64

    explicit = {item["id"]: item for item in packet["theorem_explicit_hypotheses"]}
    assert set(explicit) == EXPECTED_UNRESOLVED
    assert all(item["state"] == "unresolved" for item in explicit.values())

    diagnostics = packet["runtime_diagnostics"]
    assert diagnostics["zero_gap_numerically_consistent"] is True
    gap_lo, gap_hi = diagnostics["hypercircle_gap_interval"]
    assert gap_lo <= 0.0 <= gap_hi
    assert "does not discharge hcross" in diagnostics["interpretation"]
    assert result.all_verifiers_passed


def test_nonorthogonal_diagnostic_is_reported_without_changing_theorem_readiness():
    experiment = Experiment(
        name="rank9-prager-synge-nonorthogonal-diagnostic",
        nodes=[Node("adapter", ADAPTER_ID)],
    )
    result = GraphExecutor(build_registry()).run(
        experiment,
        external_inputs={
            "adapter": {
                "theorem_endpoint": _current_endpoint_descriptor(),
                "e_grad": [1.0, 0.0],
                "e_flux": [1.0, 0.0],
            }
        },
    )
    packet = result.outputs["adapter"]["hypothesis_packet"]
    assert packet["runtime_ready"] is False
    assert packet["formal_instantiation"] is False
    assert set(packet["unresolved_hypotheses"]) == EXPECTED_UNRESOLVED
    assert packet["runtime_diagnostics"]["zero_gap_numerically_consistent"] is False
    assert all(record.state is VerificationState.PASS for record in result.verification["adapter"])


def test_spoofed_prager_synge_endpoint_descriptor_fails_inventory_verifier():
    descriptor = _current_endpoint_descriptor()
    descriptor["proof_contract_sha256"] = "0" * 64
    experiment = Experiment(
        name="rank9-prager-synge-spoof-rejection",
        nodes=[Node("adapter", ADAPTER_ID)],
    )
    result = GraphExecutor(build_registry()).run(
        experiment,
        external_inputs={
            "adapter": {
                "theorem_endpoint": descriptor,
                "e_grad": [1.0, 0.0],
                "e_flux": [0.0, 1.0],
            }
        },
    )
    packet = result.outputs["adapter"]["hypothesis_packet"]
    runtime = {item["id"]: item for item in packet["runtime_representation_obligations"]}
    assert runtime["canonical-endpoint-descriptor"]["state"] == "fail"
    assert packet["runtime_ready"] is False
    assert result.verification["adapter"][0].state is VerificationState.FAIL
    assert result.verification["adapter"][1].state is VerificationState.PASS
    assert not result.all_verifiers_passed


def test_prager_synge_packet_is_content_addressed_to_concrete_diagnostics():
    registry = build_registry()
    module = registry.create(ADAPTER_ID)
    descriptor = _current_endpoint_descriptor()
    from cace_studio.core.module import ExecutionContext

    ctx = ExecutionContext(run_id="unit", seed=0)
    first_inputs = {
        "theorem_endpoint": descriptor,
        "e_grad": [1.0, 0.0],
        "e_flux": [0.0, 1.0],
    }
    second_inputs = {
        "theorem_endpoint": descriptor,
        "e_grad": [1.0, 0.0],
        "e_flux": [1.0, 0.0],
    }
    module.validate(first_inputs, {})
    module.validate(second_inputs, {})
    first = module.execute(first_inputs, {}, ctx)["hypothesis_packet"]
    second = module.execute(second_inputs, {}, ctx)["hypothesis_packet"]
    assert first["packet_sha256"] != second["packet_sha256"]
    assert _canonical_hash_without_embedded_digest(first) == first["packet_sha256"]
    assert _canonical_hash_without_embedded_digest(second) == second["packet_sha256"]

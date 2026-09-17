from __future__ import annotations

import hashlib
import json
import math

from cace_studio.app import build_registry
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationState
from cace_studio.modules.fem_continuum import (
    HYPOTHESIS_PACKET_SCHEMA,
    RIEZ_CLAIM_ID,
    RIEZ_THEOREM,
)

ADAPTER_ID = "fem_cont.h1_riesz_hypothesis_adapter"
FORMAL_ENDPOINT_ID = "formal330.qualified_theorem_endpoint"


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
    assert RIEZ_THEOREM in contract.endpoint_theorems
    return {
        "claim_id": RIEZ_CLAIM_ID,
        "theorem_name": RIEZ_THEOREM,
        "endpoint_member": True,
        "proof_contract_id": contract.contract_id,
        "proof_contract_sha256": contract.contract_sha256,
        "scope_note": "test descriptor",
    }


def test_rank9_adapter_is_registered_without_minting_formal_evidence():
    registry = build_registry()
    assert registry.contains(ADAPTER_ID)
    module = registry.create(ADAPTER_ID)
    assert EvidenceKind.INTERVAL in module.proof_status.evidence
    assert EvidenceKind.SYMBOLIC in module.proof_status.evidence
    assert EvidenceKind.FORMAL not in module.proof_status.evidence


def test_qualified_endpoint_to_hypothesis_adapter_pipeline_passes_fail_closed_chain():
    registry = build_registry()
    experiment = Experiment(
        name="rank9-riesz-runtime-bridge",
        nodes=[
            Node("formal", FORMAL_ENDPOINT_ID, {"theorem_name": RIEZ_THEOREM}),
            Node("adapter", ADAPTER_ID, {"index": 1}),
        ],
        edges=[Edge("formal", "result", "adapter", "theorem_endpoint")],
    )
    result = GraphExecutor(registry).run(
        experiment,
        external_inputs={"adapter": {"vector": [3.0, 4.0]}},
    )

    formal_records = result.verification["formal"]
    assert any(
        record.kind is EvidenceKind.FORMAL and record.state is VerificationState.PASS
        for record in formal_records
    )

    adapter_records = result.verification["adapter"]
    assert adapter_records
    assert all(record.kind is not EvidenceKind.FORMAL for record in adapter_records)
    assert adapter_records[0].state is VerificationState.PASS

    packet = result.outputs["adapter"]["hypothesis_packet"]
    assert packet["schema"] == HYPOTHESIS_PACKET_SCHEMA
    assert packet["claim_id"] == RIEZ_CLAIM_ID
    assert packet["theorem_name"] == RIEZ_THEOREM
    assert packet["theorem_explicit_hypotheses"] == []
    assert packet["runtime_ready"] is True
    assert packet["formal_instantiation"] is False
    assert packet["formal_provenance_source"].startswith("upstream verification record")
    assert len(_canonical_hash_without_embedded_digest(packet)) == 64

    obligations = {item["id"]: item for item in packet["runtime_representation_obligations"]}
    assert all(item["state"] == "pass" for item in obligations.values())
    interval = obligations["riesz-symbol-bound-cross-check"]["norm_interval"]
    nominal = 4.0 / math.sqrt(26.0)
    assert interval[0] <= nominal <= interval[1] <= 1.0
    assert result.all_verifiers_passed


def test_spoofed_contract_descriptor_is_rejected_and_cannot_become_formal():
    descriptor = _current_endpoint_descriptor()
    descriptor["proof_contract_sha256"] = "0" * 64
    experiment = Experiment(
        name="rank9-spoof-rejection",
        nodes=[Node("adapter", ADAPTER_ID, {"index": 0})],
    )
    result = GraphExecutor(build_registry()).run(
        experiment,
        external_inputs={
            "adapter": {
                "theorem_endpoint": descriptor,
                "vector": [1.0, 2.0],
            }
        },
    )
    packet = result.outputs["adapter"]["hypothesis_packet"]
    assert packet["runtime_ready"] is False
    obligations = {item["id"]: item for item in packet["runtime_representation_obligations"]}
    assert obligations["canonical-endpoint-descriptor"]["state"] == "fail"
    assert result.verification["adapter"][0].state is VerificationState.FAIL
    assert result.verification["adapter"][0].kind is EvidenceKind.INTERVAL
    assert not result.all_verifiers_passed


def test_out_of_range_fin_index_is_explicitly_failed_not_silently_clamped():
    experiment = Experiment(
        name="rank9-fin-index-rejection",
        nodes=[Node("adapter", ADAPTER_ID, {"index": 3})],
    )
    result = GraphExecutor(build_registry()).run(
        experiment,
        external_inputs={
            "adapter": {
                "theorem_endpoint": _current_endpoint_descriptor(),
                "vector": [1.0, 2.0],
            }
        },
    )
    packet = result.outputs["adapter"]["hypothesis_packet"]
    obligations = {item["id"]: item for item in packet["runtime_representation_obligations"]}
    assert packet["runtime_ready"] is False
    assert obligations["fin-index-range"]["state"] == "fail"
    assert obligations["riesz-symbol-bound-cross-check"]["state"] == "not-run"
    assert obligations["riesz-symbol-bound-cross-check"]["norm_interval"] is None
    assert result.verification["adapter"][0].state is VerificationState.FAIL

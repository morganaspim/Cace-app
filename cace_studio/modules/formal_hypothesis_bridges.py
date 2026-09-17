from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from cace_studio.core.formal_gate import enforce_formal_claim_qualification
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.types import EvidenceKind, Maturity, ModuleMetadata, PortSpec, ProofStatus
from cace_studio.core.verification import VerificationRecord, VerificationState

CLAIM_ID = "cace.v330.continuum-proof-strengthening"
FORMAL_ENDPOINT_MODULE_ID = "formal330.qualified_theorem_endpoint"
ZERO_TRACE_THEOREM = "CACEFormal.Continuum.hasZeroBoundaryTrace_zero"
PRAGER_SYNG_THEOREM = "CACEFormal.Continuum.continuumPragerSynge_of_weakGreen"
BRIDGE_SCHEMA = "cace-formal-hypothesis-bridge-v1"
PACKET_SCHEMA = "cace-runtime-formal-hypothesis-packet-v1"


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _current_contract():
    return ProofContractRegistry.load_default().for_claim(CLAIM_ID)


def _canonical_endpoint(endpoint: Any, theorem_name: str) -> bool:
    contract = _current_contract()
    return bool(
        isinstance(endpoint, dict)
        and contract is not None
        and endpoint.get("claim_id") == CLAIM_ID
        and endpoint.get("theorem_name") == theorem_name
        and endpoint.get("endpoint_member") is True
        and endpoint.get("proof_contract_id") == contract.contract_id
        and endpoint.get("proof_contract_sha256") == contract.contract_sha256
        and theorem_name in contract.endpoint_theorems
    )


def _qualification_anchor() -> dict[str, Any]:
    probe = VerificationRecord(
        "formal-hypothesis-bridge-qualification-probe",
        EvidenceKind.FORMAL,
        "probe the canonical current qualification used by formal hypothesis bridges",
        VerificationState.PASS,
        "canonical formal-gate probe",
        {},
    )
    gated = enforce_formal_claim_qualification(FORMAL_ENDPOINT_MODULE_ID, [probe])[0]
    metrics = gated.metrics
    return {
        "state": "pass" if gated.state is VerificationState.PASS else "not-qualified",
        "formal_gate": metrics.get("formal_gate"),
        "formal_gate_reason": metrics.get("formal_gate_reason"),
        "claim_id": metrics.get("claim_id"),
        "proof_contract_id": metrics.get("proof_contract_id"),
        "proof_contract_sha256": metrics.get("proof_contract_sha256"),
        "attested_commit": metrics.get("attested_commit"),
        "proof_artifact_sha256": metrics.get("proof_artifact_sha256"),
        "qualification_system": metrics.get("qualification_system"),
        "qualification_run_id": metrics.get("qualification_run_id"),
        "workflow_run_id": metrics.get("workflow_run_id"),
        "executable_source_bundle_sha256_expected": metrics.get(
            "executable_source_bundle_sha256_expected"
        ),
        "executable_source_bundle_sha256_current": metrics.get(
            "executable_source_bundle_sha256_current"
        ),
    }


def _vector_manifest(vector: np.ndarray) -> dict[str, Any]:
    canonical = [float(value) for value in vector.tolist()]
    return {
        "representation": "finite-real-coordinate-vector",
        "dimension": int(vector.size),
        "coordinates": canonical,
        "sha256": _canonical_sha256(canonical),
    }


class ZeroBoundaryTraceZeroBridge(Module):
    metadata = ModuleMetadata(
        "formal_bridge.zero_boundary_trace_zero",
        "Zero Boundary Trace: Zero-Field Bridge",
        "3.43.0",
        "Formal Runtime Bridge",
        "Bind an exactly-zero concrete runtime vector to the qualified Lean endpoint HasZeroBoundaryTrace G 0 for arbitrary bounded Green pairings.",
        Maturity.BETA,
        assumptions=(
            "the theorem endpoint descriptor identifies the current canonical hasZeroBoundaryTrace_zero endpoint",
            "the supplied coordinate vector is the complete runtime representation of the theorem test field v",
        ),
    )
    inputs = (
        PortSpec("theorem_endpoint", "object"),
        PortSpec("vector", "array"),
    )
    outputs = (PortSpec("bridge_certificate", "formal_hypothesis_bridge_certificate"),)
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        regression_tests=True,
        documentation=True,
        limitations=[
            "This bridge certifies only the exact zero test field v = 0.",
            "It does not certify sampled boundary values, approximate zeros, or arbitrary nonzero fields.",
            "The bridge itself does not emit FORMAL evidence; it requires the canonical formal gate to confirm current qualified proof provenance.",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        vector = np.asarray(inputs["vector"], dtype=float)
        if vector.ndim != 1 or vector.size == 0:
            raise ValidationError("zero-boundary bridge requires a non-empty one-dimensional vector")
        if not np.all(np.isfinite(vector)):
            raise ValidationError("zero-boundary bridge vector coordinates must be finite")

    def _certificate(self, inputs):
        endpoint = inputs["theorem_endpoint"]
        vector = np.asarray(inputs["vector"], dtype=float)
        contract = _current_contract()
        endpoint_ok = _canonical_endpoint(endpoint, ZERO_TRACE_THEOREM)
        exact_zero = bool(np.all(vector == 0.0))
        qualification = _qualification_anchor()
        if not endpoint_ok or not exact_zero:
            state = "fail"
        elif qualification["state"] != "pass":
            state = "not-qualified"
        else:
            state = "pass"
        certificate = {
            "schema": BRIDGE_SCHEMA,
            "claim_id": CLAIM_ID,
            "premise_id": "zero-boundary-trace",
            "lean_interface": "hv : HasZeroBoundaryTrace G v",
            "bridge_theorem_name": ZERO_TRACE_THEOREM,
            "proof_contract_id": contract.contract_id if contract else None,
            "proof_contract_sha256": contract.contract_sha256 if contract else None,
            "endpoint_descriptor_valid": endpoint_ok,
            "qualification_anchor": qualification,
            "runtime_representation": _vector_manifest(vector),
            "formal_instantiation": {"v": "0"} if exact_zero else None,
            "runtime_representation_exact_zero": exact_zero,
            "state": state,
            "formal_provenance_source": "canonical formal gate over claim registry, proof contract, proof ledger, and executable-source binding",
            "scope_note": "PASS binds only an exact zero runtime representation to the currently qualified theorem HasZeroBoundaryTrace G 0; no nonzero trace statement is inferred.",
        }
        certificate["certificate_sha256"] = _canonical_sha256(certificate)
        return certificate

    def execute(self, inputs, params, ctx):
        return {"bridge_certificate": self._certificate(inputs)}

    def verify(self, inputs, params, outputs, ctx):
        expected = self._certificate(inputs)
        actual = outputs.get("bridge_certificate")
        consistent = isinstance(actual, dict) and actual == expected
        if consistent and expected["state"] == "pass":
            state = VerificationState.PASS
        elif consistent and expected["state"] == "not-qualified":
            state = VerificationState.NOT_RUN
        else:
            state = VerificationState.FAIL
        return [
            VerificationRecord(
                "zero-boundary-trace-zero-runtime-bridge",
                EvidenceKind.SYMBOLIC,
                "an exact zero runtime test-field representation is bound to the currently qualified hasZeroBoundaryTrace_zero theorem endpoint",
                state,
                "exact coordinate equality to zero plus canonical endpoint matching and canonical formal-gate qualification",
                {
                    "bridge_theorem_name": ZERO_TRACE_THEOREM,
                    "state": expected["state"],
                    "runtime_representation_exact_zero": expected["runtime_representation_exact_zero"],
                    "qualification_anchor": expected["qualification_anchor"],
                    "certificate_sha256": expected["certificate_sha256"],
                    "output_consistent": consistent,
                },
                notes=(
                    "Before the new proof contract is requalified and promoted, an otherwise valid exact-zero bridge remains NOT_RUN.",
                    "No tolerance is used: near-zero values fail this bridge.",
                ),
            )
        ]


class ResolvePragerSyngeZeroTrace(Module):
    metadata = ModuleMetadata(
        "formal_bridge.resolve_prager_synge_zero_trace",
        "Resolve Prager-Synge Zero-Trace Premise",
        "3.43.0",
        "Formal Runtime Bridge",
        "Apply a valid zero-field boundary-trace bridge certificate to a Prager-Synge hypothesis packet while leaving all other theorem premises unchanged and fail-closed.",
        Maturity.BETA,
    )
    inputs = (
        PortSpec("hypothesis_packet", "formal_hypothesis_packet"),
        PortSpec("bridge_certificate", "formal_hypothesis_bridge_certificate"),
    )
    outputs = (PortSpec("hypothesis_packet", "formal_hypothesis_packet"),)
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        regression_tests=True,
        documentation=True,
        limitations=[
            "This resolver discharges only hv via the exact v = 0 bridge.",
            "BoundedGreenPairing, GreenSmoothCore, and hcross remain independent obligations.",
            "The resolved packet is not a Lean term and does not itself emit FORMAL evidence.",
        ],
    )

    @staticmethod
    def _resolved_packet(inputs):
        packet = inputs["hypothesis_packet"]
        bridge = inputs["bridge_certificate"]
        contract = _current_contract()
        current_qualification = _qualification_anchor()
        base_ok = bool(
            isinstance(packet, dict)
            and packet.get("schema") == PACKET_SCHEMA
            and packet.get("claim_id") == CLAIM_ID
            and packet.get("theorem_name") == PRAGER_SYNG_THEOREM
            and contract is not None
            and packet.get("proof_contract_id") == contract.contract_id
            and packet.get("proof_contract_sha256") == contract.contract_sha256
        )
        bridge_ok = bool(
            isinstance(bridge, dict)
            and bridge.get("schema") == BRIDGE_SCHEMA
            and bridge.get("claim_id") == CLAIM_ID
            and bridge.get("premise_id") == "zero-boundary-trace"
            and bridge.get("bridge_theorem_name") == ZERO_TRACE_THEOREM
            and bridge.get("proof_contract_id") == (contract.contract_id if contract else None)
            and bridge.get("proof_contract_sha256") == (contract.contract_sha256 if contract else None)
            and bridge.get("endpoint_descriptor_valid") is True
            and bridge.get("qualification_anchor") == current_qualification
            and current_qualification.get("state") == "pass"
            and bridge.get("runtime_representation_exact_zero") is True
            and bridge.get("formal_instantiation") == {"v": "0"}
            and bridge.get("state") == "pass"
        )
        result = json.loads(json.dumps(packet)) if isinstance(packet, dict) else {}
        hypotheses = result.get("theorem_explicit_hypotheses")
        target_count = 0
        if isinstance(hypotheses, list):
            for item in hypotheses:
                if isinstance(item, dict) and item.get("id") == "zero-boundary-trace":
                    target_count += 1
                    if base_ok and bridge_ok and item.get("state") == "unresolved":
                        item["state"] = "pass"
                        item["resolution_method"] = "qualified-zero-field-bridge"
                        item["bridge_theorem_name"] = ZERO_TRACE_THEOREM
                        item["bridge_certificate_sha256"] = bridge.get("certificate_sha256")
                        item["formal_instantiation"] = {"v": "0"}
        resolution_applied = bool(base_ok and bridge_ok and target_count == 1)
        unresolved = [
            item.get("id")
            for item in result.get("theorem_explicit_hypotheses", [])
            if isinstance(item, dict) and item.get("state") == "unresolved"
        ]
        result["unresolved_hypotheses"] = unresolved
        result["runtime_ready"] = bool(
            resolution_applied
            and not unresolved
            and all(
                item.get("state") == "pass"
                for item in result.get("runtime_representation_obligations", [])
                if isinstance(item, dict)
            )
        )
        result["formal_instantiation"] = False
        result["runtime_instantiations"] = {"v": "0"} if resolution_applied else {}
        result["applied_bridge_certificates"] = (
            [bridge.get("certificate_sha256")] if resolution_applied else []
        )
        result["resolution_status"] = "applied" if resolution_applied else "rejected"
        result["qualification_anchor"] = current_qualification
        result.pop("packet_sha256", None)
        result["packet_sha256"] = _canonical_sha256(result)
        return result

    def execute(self, inputs, params, ctx):
        return {"hypothesis_packet": self._resolved_packet(inputs)}

    def verify(self, inputs, params, outputs, ctx):
        expected = self._resolved_packet(inputs)
        actual = outputs.get("hypothesis_packet")
        consistent = isinstance(actual, dict) and actual == expected
        hypotheses = {
            item.get("id"): item
            for item in expected.get("theorem_explicit_hypotheses", [])
            if isinstance(item, dict)
        }
        hv = hypotheses.get("zero-boundary-trace", {})
        unresolved = set(expected.get("unresolved_hypotheses", []))
        correct_remaining = unresolved == {
            "bounded-green-pairing",
            "green-smooth-core",
            "weak-green-cross-term-identity",
        }
        if expected.get("qualification_anchor", {}).get("state") != "pass":
            state = VerificationState.NOT_RUN if consistent else VerificationState.FAIL
        else:
            passed = bool(
                consistent
                and expected.get("resolution_status") == "applied"
                and hv.get("state") == "pass"
                and hv.get("bridge_theorem_name") == ZERO_TRACE_THEOREM
                and correct_remaining
                and expected.get("runtime_ready") is False
                and expected.get("formal_instantiation") is False
            )
            state = VerificationState.PASS if passed else VerificationState.FAIL
        return [
            VerificationRecord(
                "prager-synge-zero-trace-premise-resolution",
                EvidenceKind.SYMBOLIC,
                "the zero-boundary-trace premise is resolved through the qualified v = 0 bridge while the remaining independent theorem premises stay unresolved",
                state,
                "content-addressed bridge-certificate validation, canonical formal-gate qualification, and exact single-premise substitution",
                {
                    "resolution_status": expected.get("resolution_status"),
                    "unresolved_hypotheses": expected.get("unresolved_hypotheses"),
                    "runtime_instantiations": expected.get("runtime_instantiations"),
                    "qualification_anchor": expected.get("qualification_anchor"),
                    "packet_sha256": expected.get("packet_sha256"),
                    "output_consistent": consistent,
                },
                notes=(
                    "Resolving hv does not resolve G, C, or hcross.",
                    "runtime_ready remains false until every independent premise has a valid bridge.",
                ),
            )
        ]


def register_formal_hypothesis_bridges(registry):
    for cls in (ZeroBoundaryTraceZeroBridge, ResolvePragerSyngeZeroTrace):
        registry.register(cls)

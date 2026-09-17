from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import numpy as np

from cace_studio.core.module import Module, ValidationError
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.types import EvidenceKind, Maturity, ModuleMetadata, PortSpec, ProofStatus
from cace_studio.core.verification import VerificationRecord, VerificationState

CLAIM_ID = "cace.v330.continuum-proof-strengthening"
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
            "the theorem endpoint descriptor comes from formal330.qualified_theorem_endpoint",
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
            "The bridge itself does not emit FORMAL evidence; formal proof provenance comes from the upstream qualified endpoint record.",
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
        manifest = _vector_manifest(vector)
        certificate = {
            "schema": BRIDGE_SCHEMA,
            "claim_id": CLAIM_ID,
            "premise_id": "zero-boundary-trace",
            "lean_interface": "hv : HasZeroBoundaryTrace G v",
            "bridge_theorem_name": ZERO_TRACE_THEOREM,
            "proof_contract_id": contract.contract_id if contract else None,
            "proof_contract_sha256": contract.contract_sha256 if contract else None,
            "endpoint_descriptor_valid": endpoint_ok,
            "runtime_representation": manifest,
            "formal_instantiation": {"v": "0"} if exact_zero else None,
            "runtime_representation_exact_zero": exact_zero,
            "state": "pass" if endpoint_ok and exact_zero else "fail",
            "formal_provenance_source": "upstream verification record for formal330.qualified_theorem_endpoint",
            "scope_note": "PASS binds only an exact zero runtime representation to the qualified theorem HasZeroBoundaryTrace G 0; no nonzero trace statement is inferred.",
        }
        certificate["certificate_sha256"] = _canonical_sha256(certificate)
        return certificate

    def execute(self, inputs, params, ctx):
        return {"bridge_certificate": self._certificate(inputs)}

    def verify(self, inputs, params, outputs, ctx):
        expected = self._certificate(inputs)
        actual = outputs.get("bridge_certificate")
        consistent = isinstance(actual, dict) and actual == expected
        passed = bool(consistent and expected["state"] == "pass")
        return [
            VerificationRecord(
                "zero-boundary-trace-zero-runtime-bridge",
                EvidenceKind.SYMBOLIC,
                "an exact zero runtime test-field representation is bound to the qualified hasZeroBoundaryTrace_zero theorem endpoint",
                VerificationState.PASS if passed else VerificationState.FAIL,
                "exact coordinate equality to zero plus canonical theorem/claim/proof-contract identity matching",
                {
                    "bridge_theorem_name": ZERO_TRACE_THEOREM,
                    "state": expected["state"],
                    "runtime_representation_exact_zero": expected["runtime_representation_exact_zero"],
                    "certificate_sha256": expected["certificate_sha256"],
                    "output_consistent": consistent,
                },
                notes=(
                    "Formal proof provenance is separate and must be supplied by the upstream formal endpoint verification record.",
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
        passed = bool(
            consistent
            and expected.get("resolution_status") == "applied"
            and hv.get("state") == "pass"
            and hv.get("bridge_theorem_name") == ZERO_TRACE_THEOREM
            and correct_remaining
            and expected.get("runtime_ready") is False
            and expected.get("formal_instantiation") is False
        )
        return [
            VerificationRecord(
                "prager-synge-zero-trace-premise-resolution",
                EvidenceKind.SYMBOLIC,
                "the zero-boundary-trace premise is resolved through the qualified v = 0 bridge while the remaining independent theorem premises stay unresolved",
                VerificationState.PASS if passed else VerificationState.FAIL,
                "content-addressed bridge-certificate validation and exact single-premise substitution",
                {
                    "resolution_status": expected.get("resolution_status"),
                    "unresolved_hypotheses": expected.get("unresolved_hypotheses"),
                    "runtime_instantiations": expected.get("runtime_instantiations"),
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

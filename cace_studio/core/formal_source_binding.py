from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from cace_studio.core.formal_runtime_packet import (
    PACKET_SCHEMA,
    lean_source_sha256,
    verify_p1_rt0_runtime_packet,
)

SOURCE_BINDING_SCHEMA = "cace.formal-source-binding.v1"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_without(payload: Mapping[str, Any], field: str) -> str:
    clean = deepcopy(dict(payload))
    clean.pop(field, None)
    return hashlib.sha256(_canonical_json(clean)).hexdigest()


def create_formal_source_binding(
    packet: Mapping[str, Any],
    lean_source: str,
    *,
    mesh_definition_name: str,
    binding_prefix: str,
) -> dict[str, Any]:
    packet_check = verify_p1_rt0_runtime_packet(packet)
    if not packet_check["passed"]:
        raise ValueError("cannot bind invalid runtime packet")
    if not isinstance(lean_source, str) or not lean_source.strip():
        raise ValueError("lean_source must be non-empty text")

    expected_snippets = (
        f"def {mesh_definition_name} : MeshCertificate where",
        f"def {binding_prefix}P1",
        f"def {binding_prefix}RT0",
        f'def {binding_prefix}PacketSha256 : String := "{packet["packet_sha256"]}"',
        f'def {binding_prefix}MeshCertificateSha256 : String := "{packet["mesh_certificate"]["sha256"]}"',
    )
    missing = [snippet for snippet in expected_snippets if snippet not in lean_source]
    if missing:
        raise ValueError(
            "generated Lean source missing expected binding symbols: " + "; ".join(missing)
        )

    binding: dict[str, Any] = {
        "schema": SOURCE_BINDING_SCHEMA,
        "runtime_packet_schema": PACKET_SCHEMA,
        "packet_sha256": packet["packet_sha256"],
        "mesh_certificate_sha256": packet["mesh_certificate"]["sha256"],
        "lean_source_sha256": lean_source_sha256(lean_source),
        "generated_symbols": {
            "mesh": mesh_definition_name,
            "p1": f"{binding_prefix}P1",
            "rt0": f"{binding_prefix}RT0",
            "packet_sha256": f"{binding_prefix}PacketSha256",
            "mesh_certificate_sha256": f"{binding_prefix}MeshCertificateSha256",
        },
        "fsl_status": {
            "FSL-0": "PASS_EXACT_RUNTIME_PACKET",
            "FSL-1": "PASS_EXACT_RATIONAL_POLICY",
            "FSL-2": "GENERATED_NOT_BUILT",
            "FSL-3": "GENERATED_NOT_BUILT",
            "FSL-4": "GENERATED_NOT_BUILT",
            "FSL-5": "UNRESOLVED",
            "FSL-6": "UNRESOLVED",
            "FSL-7": "UNRESOLVED",
            "FSL-8": "UNRESOLVED",
            "FSL-9": "UNRESOLVED",
            "FSL-10": "UNRESOLVED",
            "FSL-11": "UNRESOLVED",
            "FSL-12": "UNRESOLVED",
            "FSL-13": "UNRESOLVED",
        },
        "formal_claim": False,
        "lean_build_state": "NOT_RUN",
        "qualification_state": "NOT_RUN",
        "scope_note": (
            "This binding proves deterministic packet/source identity only. "
            "Generated MeshCertificate/P1Affine/RT0Affine source must still compile "
            "under the pinned Lean gate before FSL-2/FSL-3/FSL-4 can advance."
        ),
    }
    binding["binding_sha256"] = _sha256_without(binding, "binding_sha256")
    return binding


def verify_formal_source_binding(
    binding: Mapping[str, Any],
    packet: Mapping[str, Any],
    lean_source: str,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(binding, Mapping):
        return {"passed": False, "errors": ["binding must be a mapping"]}
    packet_check = verify_p1_rt0_runtime_packet(packet)
    if not packet_check["passed"]:
        errors.append("runtime packet failed exact regeneration")
        return {"passed": False, "errors": errors}

    if binding.get("schema") != SOURCE_BINDING_SCHEMA:
        errors.append("unsupported source-binding schema")
    if binding.get("runtime_packet_schema") != PACKET_SCHEMA:
        errors.append("runtime packet schema mismatch")
    if binding.get("packet_sha256") != packet.get("packet_sha256"):
        errors.append("packet SHA-256 mismatch")
    if binding.get("mesh_certificate_sha256") != packet["mesh_certificate"].get("sha256"):
        errors.append("mesh certificate SHA-256 mismatch")
    if binding.get("lean_source_sha256") != lean_source_sha256(lean_source):
        errors.append("Lean source SHA-256 mismatch")

    symbols = binding.get("generated_symbols")
    if not isinstance(symbols, Mapping):
        errors.append("missing generated_symbols")
    else:
        mesh_name = symbols.get("mesh")
        p1_name = symbols.get("p1")
        rt0_name = symbols.get("rt0")
        packet_hash_name = symbols.get("packet_sha256")
        mesh_hash_name = symbols.get("mesh_certificate_sha256")
        expected_source_snippets = (
            f"def {mesh_name} : MeshCertificate where",
            f"def {p1_name}",
            f"def {rt0_name}",
            f'def {packet_hash_name} : String := "{packet["packet_sha256"]}"',
            f'def {mesh_hash_name} : String := "{packet["mesh_certificate"]["sha256"]}"',
        )
        for snippet in expected_source_snippets:
            if snippet not in lean_source:
                errors.append(f"generated symbol/source mismatch: {snippet}")

    if binding.get("formal_claim") is not False:
        errors.append("generated source binding must not claim formal verification")
    if binding.get("lean_build_state") != "NOT_RUN":
        errors.append("unbuilt source binding must retain Lean build state NOT_RUN")
    if binding.get("qualification_state") != "NOT_RUN":
        errors.append("unqualified source binding must retain qualification state NOT_RUN")
    statuses = binding.get("fsl_status")
    if not isinstance(statuses, Mapping):
        errors.append("missing fsl_status")
    else:
        if statuses.get("FSL-0") != "PASS_EXACT_RUNTIME_PACKET":
            errors.append("FSL-0 status is not canonical")
        if statuses.get("FSL-1") != "PASS_EXACT_RATIONAL_POLICY":
            errors.append("FSL-1 status is not canonical")
        for key in ("FSL-2", "FSL-3", "FSL-4"):
            if statuses.get(key) != "GENERATED_NOT_BUILT":
                errors.append(f"{key} must remain GENERATED_NOT_BUILT before Lean")
        for number in range(5, 14):
            key = f"FSL-{number}"
            if statuses.get(key) != "UNRESOLVED":
                errors.append(f"{key} must remain UNRESOLVED in this batch")
    if binding.get("binding_sha256") != _sha256_without(binding, "binding_sha256"):
        errors.append("binding SHA-256 does not match payload")

    return {
        "passed": not errors,
        "errors": errors,
        "binding_sha256": binding.get("binding_sha256"),
        "packet_sha256": packet.get("packet_sha256"),
        "lean_source_sha256": lean_source_sha256(lean_source),
    }

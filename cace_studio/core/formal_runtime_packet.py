from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from cace_studio.core.mesh_certificate import (
    generate_mesh_certificate,
    render_lean_mesh_certificate,
    verify_mesh_certificate,
)

PACKET_SCHEMA = "cace.formal-runtime-p1rt0-packet.v1"
NUMERIC_POLICY = "exact-rational-only"
P1_FIELDS = ("c", "gx", "gy")
RT0_FIELDS = ("cx", "cy", "radial")


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


def _q(value: Any) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("boolean is not an exact rational value")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"invalid exact rational {value!r}") from exc
    if isinstance(value, float):
        raise ValueError(
            "binary floats are intentionally rejected for formal runtime binding; "
            "use an integer or exact rational string such as '3/7'"
        )
    raise ValueError(
        "formal runtime binding accepts only integers, rational strings, or Fraction values"
    )


def _qstr(value: Any) -> str:
    q = _q(value)
    return str(q.numerator) if q.denominator == 1 else f"{q.numerator}/{q.denominator}"


def _normalize_source_identity(source_identity: Mapping[str, Any] | None) -> dict[str, str | None]:
    raw = dict(source_identity or {})
    allowed = {"module_id", "module_version"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown source identity fields: {unknown}")

    def normalize(name: str) -> str | None:
        value = raw.get(name)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"{name} must be a non-empty canonical string or null")
        return value

    return {
        "module_id": normalize("module_id"),
        "module_version": normalize("module_version"),
    }


def _normalize_coeff_record(
    value: Any,
    fields: tuple[str, ...],
    *,
    family: str,
    cell: int,
) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{family} cell {cell} must be a mapping with fields {list(fields)}")
    keys = set(value)
    expected = set(fields)
    missing = sorted(expected - keys)
    extra = sorted(keys - expected)
    if missing or extra:
        raise ValueError(
            f"{family} cell {cell} coefficient fields mismatch; "
            f"missing={missing}, extra={extra}"
        )
    return {field: _qstr(value[field]) for field in fields}


def build_p1_rt0_runtime_packet(
    mesh: Mapping[str, Any],
    p1_cells: Sequence[Mapping[str, Any]],
    rt0_cells: Sequence[Mapping[str, Any]],
    *,
    source_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical FSL-0/FSL-1 runtime packet.

    Geometry and coefficients are exact rationals only. Binary floats are
    deliberately rejected rather than silently promoted to exact real claims.
    """
    if not isinstance(mesh, Mapping):
        raise ValueError("mesh must be a mapping")
    mesh_certificate = generate_mesh_certificate(
        mesh.get("vertices", []),
        mesh.get("triangles", []),
        mesh.get("boundary_labels", {}),
    )
    triangle_count = int(mesh_certificate["counts"]["triangles"])

    if isinstance(p1_cells, (str, bytes)) or not isinstance(p1_cells, Sequence):
        raise ValueError("p1_cells must be a sequence of coefficient mappings")
    if isinstance(rt0_cells, (str, bytes)) or not isinstance(rt0_cells, Sequence):
        raise ValueError("rt0_cells must be a sequence of coefficient mappings")
    if len(p1_cells) != triangle_count:
        raise ValueError(
            f"p1_cells length {len(p1_cells)} does not match triangle count {triangle_count}"
        )
    if len(rt0_cells) != triangle_count:
        raise ValueError(
            f"rt0_cells length {len(rt0_cells)} does not match triangle count {triangle_count}"
        )

    normalized_p1 = [
        _normalize_coeff_record(item, P1_FIELDS, family="P1", cell=i)
        for i, item in enumerate(p1_cells)
    ]
    normalized_rt0 = [
        _normalize_coeff_record(item, RT0_FIELDS, family="RT0", cell=i)
        for i, item in enumerate(rt0_cells)
    ]

    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "numeric_policy": {
            "id": NUMERIC_POLICY,
            "accepted_runtime_values": [
                "integer",
                "canonical rational string",
                "fractions.Fraction",
            ],
            "binary_float_policy": "rejected",
            "lean_real_interpretation": "exact rational coercion into Real",
        },
        "source_identity": _normalize_source_identity(source_identity),
        "mesh_certificate": mesh_certificate,
        "p1_basis": {
            "lean_type": "CACEFormal.P1Affine",
            "coefficient_order": list(P1_FIELDS),
            "semantic_form": "c + gx*x + gy*y",
        },
        "rt0_basis": {
            "lean_type": "CACEFormal.RT0Affine",
            "coefficient_order": list(RT0_FIELDS),
            "semantic_form": "(cx + radial*x, cy + radial*y)",
        },
        "p1_cells": normalized_p1,
        "rt0_cells": normalized_rt0,
        "fsl_scope": {
            "implemented": ["FSL-0", "FSL-1"],
            "generated_not_built": ["FSL-2", "FSL-3", "FSL-4"],
            "not_established": [
                "FSL-5",
                "FSL-6",
                "FSL-7",
                "FSL-8",
                "FSL-9",
                "FSL-10",
                "FSL-11",
                "FSL-12",
                "FSL-13",
            ],
        },
        "nonclaims": [
            "This packet is exact runtime/source identity, not a Lean proof.",
            "Generated Lean source is not formally verified until the pinned Lean gate passes.",
            "Discrete P1/RT0 binding does not establish continuum H1/H(div) membership.",
            "No finite-element pairing is identified with continuum volumePairing by this packet.",
        ],
    }
    packet["packet_sha256"] = _sha256_without(packet, "packet_sha256")
    return packet


def verify_p1_rt0_runtime_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(packet, Mapping):
        return {
            "passed": False,
            "errors": ["packet must be a mapping"],
            "checker": "exact-regeneration",
        }
    supplied = deepcopy(dict(packet))
    if supplied.get("schema") != PACKET_SCHEMA:
        errors.append(f"unsupported schema {supplied.get('schema')!r}")

    mesh_certificate = supplied.get("mesh_certificate")
    if not isinstance(mesh_certificate, Mapping):
        errors.append("missing mesh_certificate")
        return {"passed": False, "errors": errors, "checker": "exact-regeneration"}

    mesh_check = verify_mesh_certificate(mesh_certificate)
    if not mesh_check["passed"]:
        errors.extend(f"mesh: {item}" for item in mesh_check["errors"])
        return {"passed": False, "errors": errors, "checker": "exact-regeneration"}

    source = mesh_certificate.get("source", {})
    try:
        expected = build_p1_rt0_runtime_packet(
            {
                "vertices": source.get("vertices", []),
                "triangles": source.get("triangles", []),
                "boundary_labels": source.get("boundary_labels", {}),
            },
            supplied.get("p1_cells", []),
            supplied.get("rt0_cells", []),
            source_identity=supplied.get("source_identity", {}),
        )
    except Exception as exc:
        errors.append(f"packet regeneration failed: {exc}")
        return {"passed": False, "errors": errors, "checker": "exact-regeneration"}

    if supplied.get("numeric_policy") != expected["numeric_policy"]:
        errors.append("numeric_policy differs from canonical exact-rational policy")
    if supplied.get("p1_basis") != expected["p1_basis"]:
        errors.append("p1_basis differs from canonical P1 coefficient convention")
    if supplied.get("rt0_basis") != expected["rt0_basis"]:
        errors.append("rt0_basis differs from canonical RT0 coefficient convention")
    if supplied.get("fsl_scope") != expected["fsl_scope"]:
        errors.append("fsl_scope differs from canonical fail-closed scope")
    if supplied.get("nonclaims") != expected["nonclaims"]:
        errors.append("nonclaims differ from canonical packet")
    if supplied.get("packet_sha256") != _sha256_without(supplied, "packet_sha256"):
        errors.append("packet_sha256 does not match packet payload")
    if supplied != expected:
        errors.append("packet differs from deterministic exact regeneration")

    return {
        "passed": not errors,
        "errors": errors,
        "checker": "exact-regeneration",
        "packet_sha256": expected["packet_sha256"],
        "mesh_certificate_sha256": expected["mesh_certificate"]["sha256"],
        "triangle_count": expected["mesh_certificate"]["counts"]["triangles"],
        "numeric_policy": NUMERIC_POLICY,
    }


def _lean_real(text: str) -> str:
    q = Fraction(text)
    if q.denominator == 1:
        return f"({q.numerator} : ℝ)"
    return f"(({q.numerator} : ℝ) / {q.denominator})"


def _lean_identifier(value: str, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"{field} must be a simple Lean identifier")
    return value


def _emit_cell_function(
    *,
    name: str,
    mesh_definition_name: str,
    lean_type: str,
    rows: Sequence[str],
) -> list[str]:
    lines = [
        f"def {name} (K : Fin {mesh_definition_name}.triangleCount) : {lean_type} :=",
        "  match K.val with",
    ]
    for i, row in enumerate(rows[:-1]):
        lines.append(f"  | {i} => {row}")
    lines.append(f"  | _ => {rows[-1]}")
    lines.append("")
    return lines


def render_lean_p1_rt0_binding(
    packet: Mapping[str, Any],
    *,
    mesh_definition_name: str = "runtimeMesh",
    binding_prefix: str = "runtimeP1RT0",
) -> str:
    """Render exact FSL-2/FSL-3/FSL-4 Lean source.

    Rendering creates source only. It does not claim that Lean compiled it or
    that the resulting definitions are canonically qualified.
    """
    check = verify_p1_rt0_runtime_packet(packet)
    if not check["passed"]:
        raise ValueError("cannot render invalid runtime packet: " + "; ".join(check["errors"]))
    mesh_definition_name = _lean_identifier(mesh_definition_name, "mesh_definition_name")
    binding_prefix = _lean_identifier(binding_prefix, "binding_prefix")

    mesh_source = render_lean_mesh_certificate(
        packet["mesh_certificate"],
        mesh_definition_name,
    )
    mesh_source = mesh_source.replace(
        "import CACEFormal.MeshCertificate",
        "import CACEFormal.MeshCertificate\nimport CACEFormal.P1RT0Element",
        1,
    )

    p1_rows = [
        "⟨"
        + ", ".join(_lean_real(cell[field]) for field in P1_FIELDS)
        + "⟩"
        for cell in packet["p1_cells"]
    ]
    rt0_rows = [
        "⟨"
        + ", ".join(_lean_real(cell[field]) for field in RT0_FIELDS)
        + "⟩"
        for cell in packet["rt0_cells"]
    ]

    extra: list[str] = [
        "",
        "namespace CACEFormal.Generated",
        "",
        "open CACEFormal",
        "",
        f'def {binding_prefix}PacketSha256 : String := "{packet["packet_sha256"]}"',
        f'def {binding_prefix}MeshCertificateSha256 : String := "{packet["mesh_certificate"]["sha256"]}"',
        "",
    ]
    extra.extend(
        _emit_cell_function(
            name=f"{binding_prefix}P1",
            mesh_definition_name=mesh_definition_name,
            lean_type="P1Affine",
            rows=p1_rows,
        )
    )
    extra.extend(
        _emit_cell_function(
            name=f"{binding_prefix}RT0",
            mesh_definition_name=mesh_definition_name,
            lean_type="RT0Affine",
            rows=rt0_rows,
        )
    )
    extra.extend(
        [
            f"theorem {binding_prefix}TriangleCount : {mesh_definition_name}.triangleCount = {len(p1_rows)} := rfl",
            "",
            "end CACEFormal.Generated",
            "",
        ]
    )
    return mesh_source.rstrip() + "\n" + "\n".join(extra)


def lean_source_sha256(source: str) -> str:
    if not isinstance(source, str):
        raise TypeError("source must be text")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()

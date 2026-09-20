from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from typing import Any, Mapping

from cace_studio.core.formal_runtime_packet import verify_p1_rt0_runtime_packet

SCHEMA = "cace.p1rt0-exact-assembly-semantics.v1"


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
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise ValueError("boolean is not an exact rational")
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        return Fraction(value)
    raise ValueError(f"non-exact rational value {value!r}")


def _qstr(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _p1_eval(v: Mapping[str, str], p: tuple[Fraction, Fraction]) -> Fraction:
    x, y = p
    return _q(v["c"]) + _q(v["gx"]) * x + _q(v["gy"]) * y


def _rt0_eval(q: Mapping[str, str], p: tuple[Fraction, Fraction]) -> tuple[Fraction, Fraction]:
    x, y = p
    r = _q(q["radial"])
    return (_q(q["cx"]) + r * x, _q(q["cy"]) + r * y)


def _rt0_divergence(q: Mapping[str, str]) -> Fraction:
    return 2 * _q(q["radial"])


def _dot_grad(
    q: Mapping[str, str],
    v: Mapping[str, str],
    p: tuple[Fraction, Fraction],
) -> Fraction:
    qx, qy = _rt0_eval(q, p)
    return qx * _q(v["gx"]) + qy * _q(v["gy"])


def _det(points: tuple[tuple[Fraction, Fraction], ...]) -> Fraction:
    (x0, y0), (x1, y1), (x2, y2) = points
    return (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)


def _cell_pairing(
    points: tuple[tuple[Fraction, Fraction], ...],
    v: Mapping[str, str],
    q: Mapping[str, str],
) -> Fraction:
    det = _det(points)
    return det / 6 * sum((_dot_grad(q, v, p) for p in points), Fraction(0))


def _cell_divergence(
    points: tuple[tuple[Fraction, Fraction], ...],
    v: Mapping[str, str],
    q: Mapping[str, str],
) -> Fraction:
    det = _det(points)
    return -(det / 6 * _rt0_divergence(q) * sum((_p1_eval(v, p) for p in points), Fraction(0)))


def _edge_pairing(
    a: tuple[Fraction, Fraction],
    b: tuple[Fraction, Fraction],
    v: Mapping[str, str],
    q: Mapping[str, str],
) -> Fraction:
    ax, ay = a
    bx, by = b
    nx = by - ay
    ny = -(bx - ax)

    def flux(p: tuple[Fraction, Fraction]) -> Fraction:
        qx, qy = _rt0_eval(q, p)
        return qx * nx + qy * ny

    va = _p1_eval(v, a)
    vb = _p1_eval(v, b)
    ga = flux(a)
    gb = flux(b)
    return (2 * va * ga + va * gb + vb * ga + 2 * vb * gb) / 6


def _local_face_pairing(
    points: tuple[tuple[Fraction, Fraction], ...],
    v: Mapping[str, str],
    q: Mapping[str, str],
    slot: int,
) -> Fraction:
    if slot == 0:
        return _edge_pairing(points[0], points[1], v, q)
    if slot == 1:
        return _edge_pairing(points[1], points[2], v, q)
    if slot == 2:
        return _edge_pairing(points[2], points[0], v, q)
    raise ValueError(f"invalid local face slot {slot}")


def _cell_face_pairing(
    points: tuple[tuple[Fraction, Fraction], ...],
    v: Mapping[str, str],
    q: Mapping[str, str],
) -> Fraction:
    return sum((_local_face_pairing(points, v, q, s) for s in range(3)), Fraction(0))


def exact_p1_rt0_assembly_semantics(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate the exact finite P1/RT0 assembly premises mirrored by Lean.

    This checker is exact/symbolic evidence only. It does not create a Lean
    theorem, FORMAL evidence, H1/H(div) membership, or continuum linkage.
    """
    packet_check = verify_p1_rt0_runtime_packet(packet)
    if not packet_check["passed"]:
        raise ValueError("runtime packet failed exact regeneration")

    mesh = packet["mesh_certificate"]
    source = mesh["source"]
    points = [(_q(p[0]), _q(p[1])) for p in source["vertices"]]
    triangles = [tuple(int(i) for i in tri) for tri in source["triangles"]]
    p1_cells = packet["p1_cells"]
    rt0_cells = packet["rt0_cells"]

    cell_rows: list[dict[str, Any]] = []
    local_green_all = True
    assembly_equilibrium_all = True

    for k, tri in enumerate(triangles):
        tri_points = tuple(points[i] for i in tri)
        v = p1_cells[k]
        q = rt0_cells[k]
        cp = _cell_pairing(tri_points, v, q)
        cd = _cell_divergence(tri_points, v, q)
        cf = _cell_face_pairing(tri_points, v, q)
        residual = cp - (cd + cf)
        div_q = _rt0_divergence(q)
        local_green = residual == 0
        assembly_equilibrium = cd == 0
        local_green_all = local_green_all and local_green
        assembly_equilibrium_all = assembly_equilibrium_all and assembly_equilibrium
        cell_rows.append(
            {
                "cell": k,
                "signed_jacobian": _qstr(_det(tri_points)),
                "rt0_divergence": _qstr(div_q),
                "cell_pairing": _qstr(cp),
                "cell_divergence": _qstr(cd),
                "cell_face_pairing": _qstr(cf),
                "local_green_residual": _qstr(residual),
                "local_green_identity": local_green,
                "assembly_equilibrium_premise": assembly_equilibrium,
            }
        )

    boundary_rows: list[dict[str, Any]] = []
    boundary_all = True
    for edge in mesh["edges"]:
        if edge["kind"] != "boundary":
            continue
        owner = edge["owner"]
        k = int(owner["cell"])
        slot = int(owner["slot"])
        tri_points = tuple(points[i] for i in triangles[k])
        value = _local_face_pairing(tri_points, p1_cells[k], rt0_cells[k], slot)
        zero = value == 0
        boundary_all = boundary_all and zero
        boundary_rows.append(
            {
                "edge": int(edge["id"]),
                "cell": k,
                "slot": slot,
                "label": edge["label"],
                "local_face_pairing": _qstr(value),
                "boundary_admissibility_premise": zero,
            }
        )

    interior_rows: list[dict[str, Any]] = []
    interior_all = True
    for edge in mesh["edges"]:
        if edge["kind"] != "interior":
            continue
        owners = edge["owners"]
        left = owners[0]
        right = owners[1]
        lk, ls = int(left["cell"]), int(left["slot"])
        rk, rs = int(right["cell"]), int(right["slot"])
        left_points = tuple(points[i] for i in triangles[lk])
        right_points = tuple(points[i] for i in triangles[rk])
        lv = _local_face_pairing(left_points, p1_cells[lk], rt0_cells[lk], ls)
        rv = _local_face_pairing(right_points, p1_cells[rk], rt0_cells[rk], rs)
        total = lv + rv
        zero = total == 0
        interior_all = interior_all and zero
        interior_rows.append(
            {
                "edge": int(edge["id"]),
                "left": {"cell": lk, "slot": ls, "local_face_pairing": _qstr(lv)},
                "right": {"cell": rk, "slot": rs, "local_face_pairing": _qstr(rv)},
                "cancellation_sum": _qstr(total),
                "interior_cancellation_premise": zero,
            }
        )

    global_pairing = sum((_q(row["cell_pairing"]) for row in cell_rows), Fraction(0))
    global_divergence = sum((_q(row["cell_divergence"]) for row in cell_rows), Fraction(0))
    boundary_sum = sum((_q(row["local_face_pairing"]) for row in boundary_rows), Fraction(0))
    interior_sum = sum((_q(row["cancellation_sum"]) for row in interior_rows), Fraction(0))
    global_green_residual = global_pairing - (global_divergence + interior_sum + boundary_sum)
    global_green = global_green_residual == 0

    admissibility = assembly_equilibrium_all and boundary_all and interior_all
    orthogonality = local_green_all and global_green and admissibility and global_pairing == 0

    certificate: dict[str, Any] = {
        "schema": SCHEMA,
        "packet_sha256": packet["packet_sha256"],
        "mesh_certificate_sha256": mesh["sha256"],
        "evidence_kind": "symbolic-exact",
        "arithmetic": "fractions.Fraction",
        "cells": cell_rows,
        "boundary_edges": boundary_rows,
        "interior_edges": interior_rows,
        "summary": {
            "local_green_all": local_green_all,
            "assembly_equilibrium_all": assembly_equilibrium_all,
            "boundary_admissibility_all": boundary_all,
            "interior_cancellation_all": interior_all,
            "global_green_identity": global_green,
            "global_pairing": _qstr(global_pairing),
            "global_green_residual": _qstr(global_green_residual),
            "discrete_assembly_admissible": admissibility,
            "exact_orthogonality_derived": orthogonality,
        },
        "fsl_status": {
            "FSL-5": "EXACT_CHECK_PASS" if local_green_all else "EXACT_CHECK_FAIL",
            "FSL-6": "EXACT_CHECK_PASS" if admissibility and global_green else "EXACT_CHECK_FAIL",
            "FSL-7": "UNRESOLVED",
            "FSL-8": "UNRESOLVED",
            "FSL-9": "UNRESOLVED",
            "FSL-10": "UNRESOLVED",
            "FSL-11": "UNRESOLVED",
            "FSL-12": "UNRESOLVED",
            "FSL-13": "UNRESOLVED",
        },
        "formal_claim": False,
        "scope_note": (
            "Exact arithmetic mirrors finite P1/RT0 definitions and assembly premises only. "
            "The checker does not replace Lean compilation/qualification and does not establish "
            "continuum H1/H(div), normal-trace, volumePairing, or Prager-Synge hypotheses."
        ),
    }
    certificate["certificate_sha256"] = _sha256_without(certificate, "certificate_sha256")
    return certificate


def verify_exact_p1_rt0_assembly_semantics(
    packet: Mapping[str, Any],
    certificate: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(certificate, Mapping):
        return {"passed": False, "errors": ["certificate must be a mapping"]}
    try:
        expected = exact_p1_rt0_assembly_semantics(packet)
    except Exception as exc:
        return {"passed": False, "errors": [f"regeneration failed: {exc}"]}

    supplied = deepcopy(dict(certificate))
    if supplied.get("schema") != SCHEMA:
        errors.append("unsupported exact assembly semantics schema")
    if supplied.get("packet_sha256") != packet.get("packet_sha256"):
        errors.append("packet SHA-256 mismatch")
    if supplied.get("formal_claim") is not False:
        errors.append("exact checker certificate must not claim formal verification")
    if supplied.get("certificate_sha256") != _sha256_without(supplied, "certificate_sha256"):
        errors.append("certificate SHA-256 does not match payload")
    if supplied != expected:
        errors.append("certificate differs from deterministic exact regeneration")
    return {
        "passed": not errors,
        "errors": errors,
        "certificate_sha256": expected["certificate_sha256"],
        "summary": expected["summary"],
    }

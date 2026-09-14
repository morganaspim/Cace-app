from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "cace.mesh-certificate.v1"


def _q(value: Any) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("boolean is not an exact rational coordinate")
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"invalid exact rational {value!r}") from exc
    raise ValueError(
        "exact mesh coordinates must be integers or rational strings such as '3/7'; "
        "binary floats are intentionally rejected"
    )


def _strict_vertex_id(value: Any, *, cell: int, slot: int) -> int:
    """Accept only genuine integer vertex ids; never coerce floats/strings/bools."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"triangle {cell} vertex id at slot {slot} must be an integer, got {value!r}"
        )
    return value


def _qstr(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _certificate_hash(payload: Mapping[str, Any]) -> str:
    clean = deepcopy(dict(payload))
    clean.pop("sha256", None)
    return hashlib.sha256(_canonical_json(clean)).hexdigest()


def _edge_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _edge_text(edge: tuple[int, int]) -> str:
    return f"{edge[0]}-{edge[1]}"


def _normalize_boundary_labels(labels: Mapping[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for raw_key, raw_value in labels.items():
        if not isinstance(raw_key, str) or not re.fullmatch(r"\d+-\d+", raw_key):
            raise ValueError(
                f"invalid boundary label key {raw_key!r}; expected canonical vertex pair text such as '0-1'"
            )
        a_text, b_text = raw_key.split("-", 1)
        key = _edge_text(_edge_key(int(a_text), int(b_text)))
        value = str(raw_value)
        if not value:
            raise ValueError(f"boundary edge {key} has an empty label")
        if key in normalized and normalized[key] != value:
            raise ValueError(f"conflicting labels supplied for boundary edge {key}")
        normalized[key] = value
    return normalized


def generate_mesh_certificate(
    vertices: Sequence[Sequence[Any]],
    triangles: Sequence[Sequence[int]],
    boundary_labels: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Generate a deterministic exact certificate for an oriented triangular 2D mesh.

    Triangles must be counter-clockwise. Every canonical edge must have one
    (boundary) or two (interior) owners. For an interior edge the two local edge
    orientations must be opposite. The result is JSON-safe and contains no
    floating-point geometry.
    """
    labels = _normalize_boundary_labels(dict(boundary_labels or {}))
    if not vertices:
        raise ValueError("mesh has no vertices")
    if not triangles:
        raise ValueError("mesh has no triangles")

    points: list[tuple[Fraction, Fraction]] = []
    for i, p in enumerate(vertices):
        if len(p) != 2:
            raise ValueError(f"vertex {i} must have exactly two coordinates")
        points.append((_q(p[0]), _q(p[1])))

    tri_data: list[tuple[int, int, int]] = []
    jacobians: list[Fraction] = []
    occurrences: dict[tuple[int, int], list[dict[str, Any]]] = {}

    for cell, raw in enumerate(triangles):
        if len(raw) != 3:
            raise ValueError(f"triangle {cell} must have exactly three vertex ids")
        a, b, c = (
            _strict_vertex_id(raw[0], cell=cell, slot=0),
            _strict_vertex_id(raw[1], cell=cell, slot=1),
            _strict_vertex_id(raw[2], cell=cell, slot=2),
        )
        if len({a, b, c}) != 3:
            raise ValueError(f"triangle {cell} repeats a vertex")
        for v in (a, b, c):
            if v < 0 or v >= len(points):
                raise ValueError(f"triangle {cell} references out-of-range vertex {v}")

        ax, ay = points[a]
        bx, by = points[b]
        cx, cy = points[c]
        det = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if det <= 0:
            raise ValueError(
                f"triangle {cell} has non-positive signed Jacobian {_qstr(det)}; "
                "triangles must be strictly counter-clockwise"
            )
        tri_data.append((a, b, c))
        jacobians.append(det)

        for slot, (u, v) in enumerate(((a, b), (b, c), (c, a))):
            key = _edge_key(u, v)
            sign = "pos" if (u, v) == key else "neg"
            occurrences.setdefault(key, []).append(
                {"cell": cell, "slot": slot, "sign": sign}
            )

    sorted_edges = sorted(occurrences)
    edge_id = {edge: i for i, edge in enumerate(sorted_edges)}
    local_edges: list[list[dict[str, Any]]] = [[{} for _ in range(3)] for _ in tri_data]
    edge_records: list[dict[str, Any]] = []
    interior_count = 0
    boundary_count = 0
    boundary_keys: set[str] = set()

    for edge in sorted_edges:
        owners = occurrences[edge]
        gid = edge_id[edge]
        if len(owners) not in (1, 2):
            raise ValueError(
                f"non-manifold edge {_edge_text(edge)} has {len(owners)} owners; expected one or two"
            )
        for owner in owners:
            local_edges[owner["cell"]][owner["slot"]] = {
                "edge": gid,
                "sign": owner["sign"],
            }

        if len(owners) == 2:
            if owners[0]["sign"] == owners[1]["sign"]:
                raise ValueError(
                    f"interior edge {_edge_text(edge)} has aligned local orientations"
                )
            edge_records.append(
                {
                    "id": gid,
                    "vertices": [edge[0], edge[1]],
                    "kind": "interior",
                    "owners": owners,
                }
            )
            interior_count += 1
        else:
            key_text = _edge_text(edge)
            boundary_keys.add(key_text)
            label = labels.get(key_text, "boundary")
            edge_records.append(
                {
                    "id": gid,
                    "vertices": [edge[0], edge[1]],
                    "kind": "boundary",
                    "owner": owners[0],
                    "label": label,
                }
            )
            boundary_count += 1

    invalid_label_edges = sorted(set(labels) - boundary_keys)
    if invalid_label_edges:
        raise ValueError(
            "boundary labels reference non-boundary or absent edges: "
            + ", ".join(invalid_label_edges)
        )

    normalized_vertices = [[_qstr(x), _qstr(y)] for x, y in points]
    normalized_triangles = [list(t) for t in tri_data]

    cert: dict[str, Any] = {
        "schema": SCHEMA,
        "exact_arithmetic": "fractions.Fraction",
        "counts": {
            "vertices": len(points),
            "triangles": len(tri_data),
            "edges": len(sorted_edges),
            "interior_edges": interior_count,
            "boundary_edges": boundary_count,
        },
        "source": {
            "vertices": normalized_vertices,
            "triangles": normalized_triangles,
            "boundary_labels": labels,
        },
        "signed_jacobians": [_qstr(x) for x in jacobians],
        "local_edges": local_edges,
        "edges": edge_records,
        "claims": [
            "all triangle signed Jacobians are computed exactly from source vertices and are positive",
            "global edge ids and endpoint ordering are canonical and deterministic",
            "every local edge occurrence is tied to its triangle endpoints and global edge orientation",
            "each interior edge has exactly two oppositely oriented local owners",
            "each boundary edge has exactly one local owner and a nonempty boundary label",
        ],
        "nonclaims": [
            "This Python certificate is not by itself a Lean proof.",
            "Continuum H1/H(div) trace theory is outside this certificate.",
        ],
    }
    cert["sha256"] = _certificate_hash(cert)
    return cert


def verify_mesh_certificate(certificate: Mapping[str, Any]) -> dict[str, Any]:
    """Independently reconstruct and compare a mesh certificate using exact arithmetic."""
    errors: list[str] = []
    cert = deepcopy(dict(certificate))
    if cert.get("schema") != SCHEMA:
        errors.append(f"unsupported schema {cert.get('schema')!r}")
    source = cert.get("source")
    if not isinstance(source, dict):
        errors.append("missing source mesh")
        return {"passed": False, "errors": errors, "checker": "exact-regeneration"}

    try:
        expected = generate_mesh_certificate(
            source.get("vertices", []),
            source.get("triangles", []),
            source.get("boundary_labels", {}),
        )
    except Exception as exc:
        errors.append(f"source regeneration failed: {exc}")
        return {"passed": False, "errors": errors, "checker": "exact-regeneration"}

    supplied_hash = cert.get("sha256")
    actual_hash = _certificate_hash(cert)
    if supplied_hash != actual_hash:
        errors.append("certificate sha256 does not match its payload")
    if cert != expected:
        errors.append("certificate differs from deterministic exact regeneration")

    return {
        "passed": not errors,
        "errors": errors,
        "checker": "exact-regeneration",
        "arithmetic": "fractions.Fraction",
        "sha256": expected["sha256"],
        "counts": expected["counts"],
    }


def _lean_q(text: str) -> str:
    q = Fraction(text)
    if q.denominator == 1:
        return f"({q.numerator} : ℚ)"
    return f"({q.numerator} : ℚ) / {q.denominator}"


def _lean_string(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def render_lean_mesh_certificate(
    certificate: Mapping[str, Any], definition_name: str = "generatedMeshCertificate"
) -> str:
    """Render a closed, geometry-linked Lean witness against `CACEFormal.MeshCertificate`.

    The returned source is intended for the pinned Lean CI gate. Rendering does
    not claim that CI has run; callers must report Lean status separately.
    """
    check = verify_mesh_certificate(certificate)
    if not check["passed"]:
        raise ValueError("cannot render an invalid certificate: " + "; ".join(check["errors"]))
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", definition_name):
        raise ValueError("definition_name must be a simple Lean identifier")

    cert = dict(certificate)
    source = cert["source"]
    nvert = cert["counts"]["vertices"]
    ntri = cert["counts"]["triangles"]
    nedge = cert["counts"]["edges"]
    interior = [e for e in cert["edges"] if e["kind"] == "interior"]
    boundary = [e for e in cert["edges"] if e["kind"] == "boundary"]

    prefix = definition_name
    lines: list[str] = [
        "import Mathlib",
        "import CACEFormal.MeshCertificate",
        "",
        "namespace CACEFormal.Generated",
        "",
        "open CACEFormal",
        "",
    ]

    def emit_fin_function(name: str, n: int, ret: str, values: Sequence[str]) -> None:
        lines.append(f"def {name} (i : Fin {n}) : {ret} :=")
        if n == 0:
            lines.append("  exact Fin.elim0 i")
            lines.append("")
            return
        lines.append("  match i.val with")
        for i, value in enumerate(values[:-1]):
            lines.append(f"  | {i} => {value}")
        lines.append(f"  | _ => {values[-1]}")
        lines.append("")

    def emit_fin3_function(name: str, n: int, ret: str, rows: Sequence[Sequence[str]]) -> None:
        lines.append(f"def {name} (K : Fin {n}) (s : Fin 3) : {ret} :=")
        lines.append("  match K.val, s.val with")
        for k, row in enumerate(rows):
            for s, value in enumerate(row):
                if k == n - 1 and s == 2:
                    lines.append(f"  | _, _ => {value}")
                elif s == 2:
                    lines.append(f"  | {k}, _ => {value}")
                else:
                    lines.append(f"  | {k}, {s} => {value}")
        lines.append("")

    emit_fin_function(
        prefix + "VertexX", nvert, "ℚ", [_lean_q(v[0]) for v in source["vertices"]]
    )
    emit_fin_function(
        prefix + "VertexY", nvert, "ℚ", [_lean_q(v[1]) for v in source["vertices"]]
    )
    emit_fin3_function(
        prefix + "TriangleVertex",
        ntri,
        f"Fin {nvert}",
        [[str(v) for v in tri] for tri in source["triangles"]],
    )
    emit_fin_function(
        prefix + "SignedJacobian", ntri, "ℚ", [_lean_q(x) for x in cert["signed_jacobians"]]
    )
    emit_fin_function(
        prefix + "EdgeVertexLo", nedge, f"Fin {nvert}", [str(e["vertices"][0]) for e in cert["edges"]]
    )
    emit_fin_function(
        prefix + "EdgeVertexHi", nedge, f"Fin {nvert}", [str(e["vertices"][1]) for e in cert["edges"]]
    )
    emit_fin3_function(
        prefix + "LocalEdge",
        ntri,
        f"Fin {nedge}",
        [[str(item["edge"]) for item in row] for row in cert["local_edges"]],
    )
    emit_fin3_function(
        prefix + "LocalSign",
        ntri,
        "OrientationSign",
        [[".pos" if item["sign"] == "pos" else ".neg" for item in row] for row in cert["local_edges"]],
    )

    emit_fin_function(prefix + "InteriorEdge", len(interior), f"Fin {nedge}", [str(e["id"]) for e in interior])
    emit_fin_function(prefix + "InteriorLeftCell", len(interior), f"Fin {ntri}", [str(e["owners"][0]["cell"]) for e in interior])
    emit_fin_function(prefix + "InteriorLeftSlot", len(interior), "Fin 3", [str(e["owners"][0]["slot"]) for e in interior])
    emit_fin_function(prefix + "InteriorRightCell", len(interior), f"Fin {ntri}", [str(e["owners"][1]["cell"]) for e in interior])
    emit_fin_function(prefix + "InteriorRightSlot", len(interior), "Fin 3", [str(e["owners"][1]["slot"]) for e in interior])
    emit_fin_function(prefix + "BoundaryEdge", len(boundary), f"Fin {nedge}", [str(e["id"]) for e in boundary])
    emit_fin_function(prefix + "BoundaryCell", len(boundary), f"Fin {ntri}", [str(e["owner"]["cell"]) for e in boundary])
    emit_fin_function(prefix + "BoundarySlot", len(boundary), "Fin 3", [str(e["owner"]["slot"]) for e in boundary])
    emit_fin_function(prefix + "BoundaryLabel", len(boundary), "String", [_lean_string(e["label"]) for e in boundary])

    owner_values: list[str] = []
    interior_index = {e["id"]: i for i, e in enumerate(interior)}
    boundary_index = {e["id"]: i for i, e in enumerate(boundary)}
    for gid in range(nedge):
        if gid in interior_index:
            owner_values.append(f"Sum.inl {interior_index[gid]}")
        else:
            owner_values.append(f"Sum.inr {boundary_index[gid]}")
    emit_fin_function(
        prefix + "EdgeOwner",
        nedge,
        f"Sum (Fin {len(interior)}) (Fin {len(boundary)})",
        owner_values,
    )

    local_complete_defs = ", ".join(
        [
            prefix + "LocalEdge",
            prefix + "EdgeOwner",
            prefix + "InteriorLeftCell",
            prefix + "InteriorLeftSlot",
            prefix + "InteriorRightCell",
            prefix + "InteriorRightSlot",
            prefix + "BoundaryCell",
            prefix + "BoundarySlot",
        ]
    )

    lines.extend(
        [
            f"def {definition_name} : MeshCertificate where",
            f"  vertexCount := {nvert}",
            f"  triangleCount := {ntri}",
            f"  edgeCount := {nedge}",
            f"  interiorEdgeCount := {len(interior)}",
            f"  boundaryEdgeCount := {len(boundary)}",
            f"  vertexX := {prefix}VertexX",
            f"  vertexY := {prefix}VertexY",
            f"  triangleVertex := {prefix}TriangleVertex",
            "  triangle_v01_ne := by",
            f"    intro K; fin_cases K <;> simp [{prefix}TriangleVertex]",
            "  triangle_v12_ne := by",
            f"    intro K; fin_cases K <;> simp [{prefix}TriangleVertex]",
            "  triangle_v20_ne := by",
            f"    intro K; fin_cases K <;> simp [{prefix}TriangleVertex]",
            f"  signedJacobian := {prefix}SignedJacobian",
            "  signedJacobian_formula := by",
            "    intro K",
            f"    fin_cases K <;> norm_num [{prefix}SignedJacobian, {prefix}VertexX, {prefix}VertexY, {prefix}TriangleVertex]",
            "  signedJacobian_pos := by",
            "    intro K",
            f"    fin_cases K <;> norm_num [{prefix}SignedJacobian]",
            f"  edgeVertexLo := {prefix}EdgeVertexLo",
            f"  edgeVertexHi := {prefix}EdgeVertexHi",
            "  edge_vertices_canonical := by",
            f"    intro e; fin_cases e <;> norm_num [{prefix}EdgeVertexLo, {prefix}EdgeVertexHi]",
            f"  localEdge := {prefix}LocalEdge",
            f"  localSign := {prefix}LocalSign",
            "  local_edge_geometry := by",
            "    intro K s; fin_cases K <;> fin_cases s <;> rfl",
            f"  interiorEdge := {prefix}InteriorEdge",
            f"  interiorLeftCell := {prefix}InteriorLeftCell",
            f"  interiorLeftSlot := {prefix}InteriorLeftSlot",
            f"  interiorRightCell := {prefix}InteriorRightCell",
            f"  interiorRightSlot := {prefix}InteriorRightSlot",
            "  interior_cells_distinct := by",
            f"    intro i; fin_cases i <;> simp [{prefix}InteriorLeftCell, {prefix}InteriorRightCell]",
            "  interior_left_edge := by",
            "    intro i; fin_cases i <;> rfl",
            "  interior_right_edge := by",
            "    intro i; fin_cases i <;> rfl",
            "  interior_signs_opposite := by",
            "    intro i; fin_cases i <;> rfl",
            f"  boundaryEdge := {prefix}BoundaryEdge",
            f"  boundaryCell := {prefix}BoundaryCell",
            f"  boundarySlot := {prefix}BoundarySlot",
            f"  boundaryLabel := {prefix}BoundaryLabel",
            "  boundary_label_nonempty := by",
            f"    intro b; fin_cases b <;> simp [{prefix}BoundaryLabel]",
            "  boundary_edge_matches := by",
            "    intro b; fin_cases b <;> rfl",
            f"  edgeOwner := {prefix}EdgeOwner",
            "  interior_owned := by",
            "    intro i; fin_cases i <;> rfl",
            "  boundary_owned := by",
            "    intro b; fin_cases b <;> rfl",
            "  local_edge_complete := by",
            f"    intro K s; fin_cases K <;> fin_cases s <;> simp [{local_complete_defs}]",
            "",
            "end CACEFormal.Generated",
            "",
        ]
    )
    return "\n".join(lines)


def verification_chain(
    certificate: Mapping[str, Any], *, lean_ci_status: str = "NOT_RUN", commit: str | None = None
) -> dict[str, Any]:
    check = verify_mesh_certificate(certificate)
    return {
        "certificate_generated": "PASS",
        "python_exact_checker": "PASS" if check["passed"] else "FAIL",
        "lean_theorem_instantiated": "GENERATED_NOT_BUILT",
        "lean_ci_build": lean_ci_status,
        "commit": commit,
        "certificate_sha256": certificate.get("sha256"),
        "formal_claim": lean_ci_status == "PASS",
        "note": (
            "A generated Lean source is not labeled formally verified until the pinned CI build passes."
        ),
    }

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from .formal_runtime_packet import ExactRational, FormalRuntimePacket


class FormalSourceBindingError(ValueError):
    pass


def lean_rational(value: ExactRational) -> str:
    n, d = value.numerator, value.denominator
    if d == 1:
        return f"({n} : ℚ)"
    if n < 0:
        return f"(-{abs(n)} / {d} : ℚ)"
    return f"({n} / {d} : ℚ)"


def _lean_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _source_sha256(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _render_fin_match(name: str, count: int, return_type: str, values: list[str]) -> str:
    if count != len(values):
        raise FormalSourceBindingError(f"{name}: count/value mismatch")
    if count == 0:
        return f"def {name} (i : Fin 0) : {return_type} := Fin.elim0 i\n"
    if count == 1:
        return f"def {name} (_i : Fin 1) : {return_type} := {values[0]}\n"
    lines = [f"def {name} (i : Fin {count}) : {return_type} :=", "  match i.val with"]
    for idx, value in enumerate(values[:-1]):
        lines.append(f"  | {idx} => {value}")
    lines.append(f"  | _ => {values[-1]}")
    return "\n".join(lines) + "\n"


def _render_pair_match(
    name: str,
    outer_count: int,
    inner_count: int,
    outer_name: str,
    inner_name: str,
    outer_type: str,
    inner_type: str,
    return_type: str,
    rows: list[list[str]],
) -> str:
    if len(rows) != outer_count or any(len(row) != inner_count for row in rows):
        raise FormalSourceBindingError(f"{name}: pair-match shape mismatch")
    if outer_count == 0:
        return (
            f"def {name} ({outer_name} : {outer_type}) "
            f"(_{inner_name} : {inner_type}) : {return_type} := Fin.elim0 {outer_name}\n"
        )
    flat = [(o, i, rows[o][i]) for o in range(outer_count) for i in range(inner_count)]
    lines = [
        f"def {name} ({outer_name} : {outer_type}) ({inner_name} : {inner_type}) : {return_type} :=",
        f"  match {outer_name}.val, {inner_name}.val with",
    ]
    for o, i, value in flat[:-1]:
        lines.append(f"  | {o}, {i} => {value}")
    _, _, last = flat[-1]
    lines.append(f"  | _, _ => {last}")
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class GeneratedLeanBinding:
    schema: str
    packet_sha256: str
    namespace: str
    definition_name: str
    source_sha256: str
    source: str
    state: str = "generated-unqualified"

    def verify(self) -> bool:
        return (
            self.state == "generated-unqualified"
            and self.source_sha256 == _source_sha256(self.source)
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "packet_sha256": self.packet_sha256,
            "namespace": self.namespace,
            "definition_name": self.definition_name,
            "source_sha256": self.source_sha256,
            "state": self.state,
        }


def p1_affine_binding(packet: FormalRuntimePacket, cell: int) -> dict[str, Any]:
    if cell < 0 or cell >= len(packet.p1_cells):
        raise FormalSourceBindingError("P1 cell index out of range")
    p = packet.p1_cells[cell]
    expression = (
        "({ c := "
        + lean_rational(p.c)
        + ", gx := "
        + lean_rational(p.gx)
        + ", gy := "
        + lean_rational(p.gy)
        + " } : P1Affine)"
    )
    return {
        "schema": "cace-p1-affine-lean-binding-v1",
        "packet_sha256": packet.packet_sha256,
        "cell": cell,
        "lean_type": "CACEFormal.P1Affine",
        "coefficients": p.to_mapping(),
        "lean_expression": expression,
        "state": "exact-representation",
    }


def rt0_affine_binding(packet: FormalRuntimePacket, cell: int) -> dict[str, Any]:
    if cell < 0 or cell >= len(packet.rt0_cells):
        raise FormalSourceBindingError("RT0 cell index out of range")
    q = packet.rt0_cells[cell]
    expression = (
        "({ cx := "
        + lean_rational(q.cx)
        + ", cy := "
        + lean_rational(q.cy)
        + ", radial := "
        + lean_rational(q.radial)
        + " } : RT0Affine)"
    )
    return {
        "schema": "cace-rt0-affine-lean-binding-v1",
        "packet_sha256": packet.packet_sha256,
        "cell": cell,
        "lean_type": "CACEFormal.RT0Affine",
        "coefficients": q.to_mapping(),
        "lean_expression": expression,
        "state": "exact-representation",
    }


def render_mesh_certificate_lean(
    packet: FormalRuntimePacket,
    *,
    namespace: str = "CACEFormal.Generated.RuntimeBinding",
    definition_name: str = "runtimeMesh",
) -> GeneratedLeanBinding:
    if not packet.verify_hash():
        raise FormalSourceBindingError("packet hash is invalid")
    if not namespace or not all(part.isidentifier() for part in namespace.split(".")):
        raise FormalSourceBindingError("namespace must be dot-separated identifiers")
    if not definition_name.isidentifier():
        raise FormalSourceBindingError("definition_name must be an identifier")

    prefix = definition_name
    vertex_count = len(packet.vertices)
    triangle_count = len(packet.triangles)
    edge_count = len(packet.edges)
    interior_count = len(packet.interior_edges)
    boundary_count = len(packet.boundary_edges)

    pieces: list[str] = [
        "import Mathlib",
        "import CACEFormal.MeshCertificate",
        "",
        f"namespace {namespace}",
        "",
        "open CACEFormal",
        "",
        f"/- CACE runtime packet SHA-256: {packet.packet_sha256}",
        "   Generated source is a candidate exact binding only.",
        "   It is not canonical formal evidence until compiled, audited, contracted, and qualified. -/",
        "",
    ]

    pieces.append(
        _render_fin_match(
            f"{prefix}VertexX",
            vertex_count,
            "ℚ",
            [lean_rational(v.x) for v in packet.vertices],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}VertexY",
            vertex_count,
            "ℚ",
            [lean_rational(v.y) for v in packet.vertices],
        )
    )
    pieces.append(
        _render_pair_match(
            f"{prefix}TriangleVertex",
            triangle_count,
            3,
            "K",
            "s",
            f"Fin {triangle_count}",
            "Fin 3",
            f"Fin {vertex_count}",
            [[str(value) for value in tri] for tri in packet.triangles],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}SignedJacobian",
            triangle_count,
            "ℚ",
            [lean_rational(v) for v in packet.signed_jacobians],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}EdgeVertexLo",
            edge_count,
            f"Fin {vertex_count}",
            [str(edge[0]) for edge in packet.edges],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}EdgeVertexHi",
            edge_count,
            f"Fin {vertex_count}",
            [str(edge[1]) for edge in packet.edges],
        )
    )
    pieces.append(
        _render_pair_match(
            f"{prefix}LocalEdge",
            triangle_count,
            3,
            "K",
            "s",
            f"Fin {triangle_count}",
            "Fin 3",
            f"Fin {edge_count}",
            [[str(v) for v in row] for row in packet.local_edges],
        )
    )
    pieces.append(
        _render_pair_match(
            f"{prefix}LocalSign",
            triangle_count,
            3,
            "K",
            "s",
            f"Fin {triangle_count}",
            "Fin 3",
            "OrientationSign",
            [[f".{v}" for v in row] for row in packet.local_signs],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}InteriorEdge",
            interior_count,
            f"Fin {edge_count}",
            [str(item["edge"]) for item in packet.interior_edges],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}InteriorLeftCell",
            interior_count,
            f"Fin {triangle_count}",
            [str(item["left_cell"]) for item in packet.interior_edges],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}InteriorLeftSlot",
            interior_count,
            "Fin 3",
            [str(item["left_slot"]) for item in packet.interior_edges],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}InteriorRightCell",
            interior_count,
            f"Fin {triangle_count}",
            [str(item["right_cell"]) for item in packet.interior_edges],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}InteriorRightSlot",
            interior_count,
            "Fin 3",
            [str(item["right_slot"]) for item in packet.interior_edges],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}BoundaryEdge",
            boundary_count,
            f"Fin {edge_count}",
            [str(item["edge"]) for item in packet.boundary_edges],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}BoundaryCell",
            boundary_count,
            f"Fin {triangle_count}",
            [str(item["cell"]) for item in packet.boundary_edges],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}BoundarySlot",
            boundary_count,
            "Fin 3",
            [str(item["slot"]) for item in packet.boundary_edges],
        )
    )
    pieces.append(
        _render_fin_match(
            f"{prefix}BoundaryLabel",
            boundary_count,
            "String",
            [_lean_string(item["label"]) for item in packet.boundary_edges],
        )
    )

    edge_owner_values = [""] * edge_count
    for idx, item in enumerate(packet.interior_edges):
        edge_owner_values[item["edge"]] = f"Sum.inl {idx}"
    for idx, item in enumerate(packet.boundary_edges):
        edge_owner_values[item["edge"]] = f"Sum.inr {idx}"
    if any(not item for item in edge_owner_values):
        raise FormalSourceBindingError("edge ownership is incomplete")
    pieces.append(
        _render_fin_match(
            f"{prefix}EdgeOwner",
            edge_count,
            f"Sum (Fin {interior_count}) (Fin {boundary_count})",
            edge_owner_values,
        )
    )

    pieces.extend(
        [
            f"def {definition_name} : MeshCertificate where",
            f"  vertexCount := {vertex_count}",
            f"  triangleCount := {triangle_count}",
            f"  edgeCount := {edge_count}",
            f"  interiorEdgeCount := {interior_count}",
            f"  boundaryEdgeCount := {boundary_count}",
            f"  vertexX := {prefix}VertexX",
            f"  vertexY := {prefix}VertexY",
            f"  triangleVertex := {prefix}TriangleVertex",
            "  triangle_v01_ne := by native_decide",
            "  triangle_v12_ne := by native_decide",
            "  triangle_v20_ne := by native_decide",
            f"  signedJacobian := {prefix}SignedJacobian",
            "  signedJacobian_formula := by native_decide",
            "  signedJacobian_pos := by native_decide",
            f"  edgeVertexLo := {prefix}EdgeVertexLo",
            f"  edgeVertexHi := {prefix}EdgeVertexHi",
            "  edge_vertices_canonical := by native_decide",
            f"  localEdge := {prefix}LocalEdge",
            f"  localSign := {prefix}LocalSign",
            "  local_edge_geometry := by native_decide",
            f"  interiorEdge := {prefix}InteriorEdge",
            f"  interiorLeftCell := {prefix}InteriorLeftCell",
            f"  interiorLeftSlot := {prefix}InteriorLeftSlot",
            f"  interiorRightCell := {prefix}InteriorRightCell",
            f"  interiorRightSlot := {prefix}InteriorRightSlot",
            "  interior_cells_distinct := by native_decide",
            "  interior_left_edge := by native_decide",
            "  interior_right_edge := by native_decide",
            "  interior_signs_opposite := by native_decide",
            f"  boundaryEdge := {prefix}BoundaryEdge",
            f"  boundaryCell := {prefix}BoundaryCell",
            f"  boundarySlot := {prefix}BoundarySlot",
            f"  boundaryLabel := {prefix}BoundaryLabel",
            "  boundary_label_nonempty := by native_decide",
            "  boundary_edge_matches := by native_decide",
            f"  edgeOwner := {prefix}EdgeOwner",
            "  interior_owned := by native_decide",
            "  boundary_owned := by native_decide",
            "  local_edge_complete := by native_decide",
            "",
            f"end {namespace}",
            "",
        ]
    )
    source = "\n".join(pieces)
    return GeneratedLeanBinding(
        schema="cace-generated-mesh-certificate-binding-v1",
        packet_sha256=packet.packet_sha256,
        namespace=namespace,
        definition_name=definition_name,
        source_sha256=_source_sha256(source),
        source=source,
    )

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from typing import Any, Mapping, Sequence

PACKET_SCHEMA = "cace-p1-rt0-formal-runtime-packet-v1"
NUMERIC_POLICY = "exact-rational-v1"


class FormalRuntimePacketError(ValueError):
    """Raised when runtime data cannot be represented by the exact FSL-0..4 policy."""


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, order=True)
class ExactRational:
    numerator: int
    denominator: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.numerator, bool) or isinstance(self.denominator, bool):
            raise FormalRuntimePacketError("booleans are not exact-rational coordinates")
        if not isinstance(self.numerator, int) or not isinstance(self.denominator, int):
            raise FormalRuntimePacketError("exact rationals require integer numerator/denominator")
        if self.denominator == 0:
            raise FormalRuntimePacketError("exact rational denominator cannot be zero")
        value = Fraction(self.numerator, self.denominator)
        object.__setattr__(self, "numerator", value.numerator)
        object.__setattr__(self, "denominator", value.denominator)

    @classmethod
    def parse(cls, value: Any) -> "ExactRational":
        if isinstance(value, cls):
            return value
        if isinstance(value, bool):
            raise FormalRuntimePacketError("booleans are not exact-rational values")
        if isinstance(value, int):
            return cls(value, 1)
        if isinstance(value, Fraction):
            return cls(value.numerator, value.denominator)
        if isinstance(value, str):
            try:
                parsed = Fraction(value)
            except (ValueError, ZeroDivisionError) as exc:
                raise FormalRuntimePacketError(f"invalid exact-rational string: {value!r}") from exc
            return cls(parsed.numerator, parsed.denominator)
        if isinstance(value, Mapping):
            if set(value) != {"numerator", "denominator"}:
                raise FormalRuntimePacketError(
                    "exact-rational mappings require exactly numerator and denominator"
                )
            return cls(value["numerator"], value["denominator"])
        if isinstance(value, float):
            raise FormalRuntimePacketError(
                "floating-point values are forbidden by exact-rational-v1; "
                "supply an int, Fraction, rational string, or numerator/denominator mapping"
            )
        raise FormalRuntimePacketError(
            f"unsupported exact-rational value type: {type(value).__name__}"
        )

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    def to_mapping(self) -> dict[str, int]:
        return {"numerator": self.numerator, "denominator": self.denominator}


@dataclass(frozen=True)
class ExactVertex2:
    x: ExactRational
    y: ExactRational

    @classmethod
    def parse(cls, value: Sequence[Any] | Mapping[str, Any]) -> "ExactVertex2":
        if isinstance(value, Mapping):
            if set(value) != {"x", "y"}:
                raise FormalRuntimePacketError("vertex mappings require exactly x and y")
            return cls(ExactRational.parse(value["x"]), ExactRational.parse(value["y"]))
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 2:
            return cls(ExactRational.parse(value[0]), ExactRational.parse(value[1]))
        raise FormalRuntimePacketError("vertices require an (x, y) sequence or {x, y} mapping")

    def to_mapping(self) -> dict[str, dict[str, int]]:
        return {"x": self.x.to_mapping(), "y": self.y.to_mapping()}


@dataclass(frozen=True)
class P1AffineData:
    c: ExactRational
    gx: ExactRational
    gy: ExactRational

    @classmethod
    def parse(cls, value: Sequence[Any] | Mapping[str, Any]) -> "P1AffineData":
        if isinstance(value, Mapping):
            if set(value) != {"c", "gx", "gy"}:
                raise FormalRuntimePacketError("P1 mappings require exactly c, gx, gy")
            return cls(*(ExactRational.parse(value[k]) for k in ("c", "gx", "gy")))
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 3:
            return cls(*(ExactRational.parse(item) for item in value))
        raise FormalRuntimePacketError("P1 data require (c, gx, gy)")

    def to_mapping(self) -> dict[str, dict[str, int]]:
        return {name: getattr(self, name).to_mapping() for name in ("c", "gx", "gy")}


@dataclass(frozen=True)
class RT0AffineData:
    cx: ExactRational
    cy: ExactRational
    radial: ExactRational

    @classmethod
    def parse(cls, value: Sequence[Any] | Mapping[str, Any]) -> "RT0AffineData":
        if isinstance(value, Mapping):
            if set(value) != {"cx", "cy", "radial"}:
                raise FormalRuntimePacketError("RT0 mappings require exactly cx, cy, radial")
            return cls(*(ExactRational.parse(value[k]) for k in ("cx", "cy", "radial")))
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 3:
            return cls(*(ExactRational.parse(item) for item in value))
        raise FormalRuntimePacketError("RT0 data require (cx, cy, radial)")

    def to_mapping(self) -> dict[str, dict[str, int]]:
        return {name: getattr(self, name).to_mapping() for name in ("cx", "cy", "radial")}


def _signed_jacobian(
    vertices: tuple[ExactVertex2, ...], triangle: tuple[int, int, int]
) -> ExactRational:
    p0, p1, p2 = (vertices[i] for i in triangle)
    det = (
        (p1.x.fraction - p0.x.fraction) * (p2.y.fraction - p0.y.fraction)
        - (p1.y.fraction - p0.y.fraction) * (p2.x.fraction - p0.x.fraction)
    )
    return ExactRational(det.numerator, det.denominator)


def _edge_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _local_directed_edges(triangle: tuple[int, int, int]) -> tuple[tuple[int, int], ...]:
    a, b, c = triangle
    return ((a, b), (b, c), (c, a))


@dataclass(frozen=True)
class FormalRuntimePacket:
    source_module: str
    source_version: str
    vertices: tuple[ExactVertex2, ...]
    triangles: tuple[tuple[int, int, int], ...]
    p1_cells: tuple[P1AffineData, ...]
    rt0_cells: tuple[RT0AffineData, ...]
    edges: tuple[tuple[int, int], ...]
    local_edges: tuple[tuple[int, int, int], ...]
    local_signs: tuple[tuple[str, str, str], ...]
    signed_jacobians: tuple[ExactRational, ...]
    interior_edges: tuple[dict[str, int], ...]
    boundary_edges: tuple[dict[str, Any], ...]
    packet_sha256: str

    def unsigned_mapping(self) -> dict[str, Any]:
        return {
            "schema": PACKET_SCHEMA,
            "numeric_policy": NUMERIC_POLICY,
            "source": {
                "module": self.source_module,
                "version": self.source_version,
            },
            "vertices": [v.to_mapping() for v in self.vertices],
            "triangles": [list(t) for t in self.triangles],
            "p1_cells": [p.to_mapping() for p in self.p1_cells],
            "rt0_cells": [q.to_mapping() for q in self.rt0_cells],
            "topology": {
                "edges": [list(edge) for edge in self.edges],
                "local_edges": [list(row) for row in self.local_edges],
                "local_signs": [list(row) for row in self.local_signs],
                "signed_jacobians": [j.to_mapping() for j in self.signed_jacobians],
                "interior_edges": [dict(item) for item in self.interior_edges],
                "boundary_edges": [dict(item) for item in self.boundary_edges],
            },
        }

    def to_mapping(self) -> dict[str, Any]:
        result = self.unsigned_mapping()
        result["packet_sha256"] = self.packet_sha256
        return result

    def verify_hash(self) -> bool:
        return self.packet_sha256 == _canonical_sha256(self.unsigned_mapping())

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "FormalRuntimePacket":
        if raw.get("schema") != PACKET_SCHEMA:
            raise FormalRuntimePacketError("unsupported formal runtime packet schema")
        if raw.get("numeric_policy") != NUMERIC_POLICY:
            raise FormalRuntimePacketError("unsupported formal runtime packet numeric policy")
        source = raw.get("source")
        topology = raw.get("topology")
        if not isinstance(source, Mapping) or not isinstance(topology, Mapping):
            raise FormalRuntimePacketError("packet source/topology must be mappings")
        packet = build_p1_rt0_packet(
            vertices=raw.get("vertices", ()),
            triangles=raw.get("triangles", ()),
            p1_cells=raw.get("p1_cells", ()),
            rt0_cells=raw.get("rt0_cells", ()),
            source_module=source.get("module"),
            source_version=source.get("version"),
            boundary_labels={
                tuple(item["vertices"]): item["label"]
                for item in topology.get("boundary_edges", ())
            },
        )
        expected = raw.get("packet_sha256")
        if not isinstance(expected, str) or expected != packet.packet_sha256:
            raise FormalRuntimePacketError("runtime packet SHA-256 mismatch")
        if packet.to_mapping() != dict(raw):
            raise FormalRuntimePacketError(
                "runtime packet topology/content is not canonical for its mathematical data"
            )
        return packet


def build_p1_rt0_packet(
    *,
    vertices: Sequence[Sequence[Any] | Mapping[str, Any]],
    triangles: Sequence[Sequence[int]],
    p1_cells: Sequence[Sequence[Any] | Mapping[str, Any]],
    rt0_cells: Sequence[Sequence[Any] | Mapping[str, Any]],
    source_module: str,
    source_version: str,
    boundary_labels: Mapping[tuple[int, int], str] | None = None,
) -> FormalRuntimePacket:
    if not isinstance(source_module, str) or not source_module.strip():
        raise FormalRuntimePacketError("source_module must be a non-empty string")
    if not isinstance(source_version, str) or not source_version.strip():
        raise FormalRuntimePacketError("source_version must be a non-empty string")

    exact_vertices = tuple(ExactVertex2.parse(v) for v in vertices)
    if len(exact_vertices) < 3:
        raise FormalRuntimePacketError("a triangular mesh requires at least three vertices")

    exact_triangles: list[tuple[int, int, int]] = []
    for raw in triangles:
        if (
            not isinstance(raw, Sequence)
            or isinstance(raw, (str, bytes))
            or len(raw) != 3
            or any(isinstance(i, bool) or not isinstance(i, int) for i in raw)
        ):
            raise FormalRuntimePacketError("each triangle requires exactly three integer vertex ids")
        tri = tuple(raw)
        if len(set(tri)) != 3:
            raise FormalRuntimePacketError("triangle vertices must be pairwise distinct")
        if any(i < 0 or i >= len(exact_vertices) for i in tri):
            raise FormalRuntimePacketError("triangle vertex id is out of range")
        exact_triangles.append(tri)
    triangles_tuple = tuple(exact_triangles)
    if not triangles_tuple:
        raise FormalRuntimePacketError("formal runtime packet requires at least one triangle")

    p1 = tuple(P1AffineData.parse(value) for value in p1_cells)
    rt0 = tuple(RT0AffineData.parse(value) for value in rt0_cells)
    if len(p1) != len(triangles_tuple) or len(rt0) != len(triangles_tuple):
        raise FormalRuntimePacketError(
            "P1 and RT0 cell arrays must each have exactly one entry per triangle"
        )

    jacobians = tuple(_signed_jacobian(exact_vertices, tri) for tri in triangles_tuple)
    if any(j.fraction <= 0 for j in jacobians):
        raise FormalRuntimePacketError(
            "all triangles must be strictly positively oriented for MeshCertificate binding"
        )

    occurrences: dict[tuple[int, int], list[tuple[int, int, str]]] = {}
    for cell, tri in enumerate(triangles_tuple):
        for slot, (u, v) in enumerate(_local_directed_edges(tri)):
            edge = _edge_key(u, v)
            sign = "pos" if (u, v) == edge else "neg"
            occurrences.setdefault(edge, []).append((cell, slot, sign))

    if any(len(owners) not in (1, 2) for owners in occurrences.values()):
        raise FormalRuntimePacketError(
            "every canonical global edge must have exactly one boundary owner or two interior owners"
        )

    edges = tuple(sorted(occurrences))
    edge_id = {edge: i for i, edge in enumerate(edges)}
    local_edges_rows: list[tuple[int, int, int]] = []
    local_sign_rows: list[tuple[str, str, str]] = []
    for tri in triangles_tuple:
        local = _local_directed_edges(tri)
        local_edges_rows.append(tuple(edge_id[_edge_key(*edge)] for edge in local))
        local_sign_rows.append(
            tuple("pos" if edge == _edge_key(*edge) else "neg" for edge in local)
        )

    supplied_labels = boundary_labels or {}
    normalized_labels: dict[tuple[int, int], str] = {}
    for key, label in supplied_labels.items():
        if (
            not isinstance(key, tuple)
            or len(key) != 2
            or any(isinstance(i, bool) or not isinstance(i, int) for i in key)
        ):
            raise FormalRuntimePacketError("boundary label keys must be integer vertex-id pairs")
        canonical = _edge_key(key[0], key[1])
        if canonical != key:
            raise FormalRuntimePacketError(
                "boundary label keys must use canonical ascending vertex order"
            )
        if not isinstance(label, str) or not label:
            raise FormalRuntimePacketError("boundary labels must be non-empty strings")
        normalized_labels[canonical] = label

    interior: list[dict[str, int]] = []
    boundary: list[dict[str, Any]] = []
    for edge in edges:
        owners = occurrences[edge]
        eid = edge_id[edge]
        if len(owners) == 2:
            (lc, ls, lsign), (rc, rs, rsign) = owners
            if lsign == rsign:
                raise FormalRuntimePacketError(
                    "interior edge local orientations must be opposite"
                )
            interior.append(
                {
                    "edge": eid,
                    "left_cell": lc,
                    "left_slot": ls,
                    "right_cell": rc,
                    "right_slot": rs,
                }
            )
        else:
            cell, slot, _ = owners[0]
            boundary.append(
                {
                    "edge": eid,
                    "cell": cell,
                    "slot": slot,
                    "vertices": list(edge),
                    "label": normalized_labels.get(edge, f"boundary-{eid}"),
                }
            )

    unexpected = set(normalized_labels) - {tuple(item["vertices"]) for item in boundary}
    if unexpected:
        raise FormalRuntimePacketError(
            f"boundary labels supplied for non-boundary edges: {sorted(unexpected)!r}"
        )

    provisional = FormalRuntimePacket(
        source_module=source_module.strip(),
        source_version=source_version.strip(),
        vertices=exact_vertices,
        triangles=triangles_tuple,
        p1_cells=p1,
        rt0_cells=rt0,
        edges=edges,
        local_edges=tuple(local_edges_rows),
        local_signs=tuple(local_sign_rows),
        signed_jacobians=jacobians,
        interior_edges=tuple(interior),
        boundary_edges=tuple(boundary),
        packet_sha256="",
    )
    digest = _canonical_sha256(provisional.unsigned_mapping())
    return FormalRuntimePacket(**{**provisional.__dict__, "packet_sha256": digest})

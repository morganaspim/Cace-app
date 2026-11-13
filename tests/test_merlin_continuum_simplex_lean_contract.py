from __future__ import annotations

import json
from collections import Counter
from itertools import permutations, product
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "formal" / "cace_formal" / "CACEFormal" / "ContinuumSimplexCore.lean"
GUARDRAILS = ROOT / "formal" / "cace_formal" / "proof_guardrails.json"
AGGREGATE = ROOT / "formal" / "cace_formal" / "CACEFormal.lean"


def test_continuum_simplex_core_is_explicitly_quarantined() -> None:
    config = json.loads(GUARDRAILS.read_text(encoding="utf-8"))
    assert "CACEFormal.ContinuumSimplexCore" in config["quarantined_root_imports"]
    assert "CACEFormal.ContinuumSimplexCore" not in config["allowed_root_imports"]
    assert "import CACEFormal.ContinuumSimplexCore" not in AGGREGATE.read_text(
        encoding="utf-8"
    )


def test_continuum_simplex_core_contains_required_definitions_and_no_holes() -> None:
    source = MODULE.read_text(encoding="utf-8")
    required = (
        "abbrev PairState := ℝ × ℝ",
        "structure PairedContinuumTriangle",
        "def EndpointGluing",
        "map_preserves_endpoint_gluing",
        "mapEdges_preserves_endpoint_gluing",
        "mapEdges_preserves_continuity",
        "map_preserves_continuity",
        "theorem comp_assoc",
        "theorem id_comp",
        "theorem comp_id",
        "def triangleLoop",
        "theorem pair_channels_reconstruct",
        "def orientedEdgeBoundary",
        "def orientedTriangleBoundarySquared",
        "theorem oriented_triangle_boundary_squared_zero",
        "def orientedFaceBoundary",
        "def orientedTetrahedronBoundarySquared",
        "theorem oriented_tetrahedron_boundary_squared_zero",
    )
    for declaration in required:
        assert declaration in source, declaration

    lowered = source.lower()
    assert "sorry" not in lowered
    assert "admit" not in lowered
    assert "axiom " not in lowered



def _oriented_face_boundary(a: int, b: int, c: int) -> Counter[tuple[int, int]]:
    """Reference 1-chain for [a,b,c] = [b,c] - [a,c] + [a,b]."""
    result: Counter[tuple[int, int]] = Counter()
    result[(b, c)] += 1
    result[(a, c)] -= 1
    result[(a, b)] += 1
    return result


def _oriented_tetrahedron_boundary_squared(
    a: int, b: int, c: int, d: int
) -> Counter[tuple[int, int]]:
    """Expand [b,c,d] - [a,c,d] + [a,b,d] - [a,b,c] to edges."""
    result: Counter[tuple[int, int]] = Counter()
    signed_faces = (
        (1, (b, c, d)),
        (-1, (a, c, d)),
        (1, (a, b, d)),
        (-1, (a, b, c)),
    )
    for sign, (x, y, z) in signed_faces:
        for edge, coefficient in _oriented_face_boundary(x, y, z).items():
            result[edge] += sign * coefficient
    return result


def test_tetrahedron_boundary_cancellation_for_permutations_and_degenerate_labels() -> None:
    # All 24 orientations of four distinct vertices.
    for vertices in permutations(range(4)):
        assert not any(_oriented_tetrahedron_boundary_squared(*vertices).values())

    # Repeated labels exercise degeneracies and coincident ordered edges.
    for vertices in product(range(3), repeat=4):
        assert not any(_oriented_tetrahedron_boundary_squared(*vertices).values())

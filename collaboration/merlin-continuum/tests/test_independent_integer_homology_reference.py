from __future__ import annotations

"""Independent pure-Python reference checks for the six-vertex RP2 model.

This intentionally does not import or port the C++ Smith-normal-form or
simplicial-homology implementation. It constructs boundary matrices directly,
collapses a spanning tree to obtain an H1 presentation, and uses exact
integer determinants/determinantal divisors on small matrices.
"""

from itertools import combinations
from math import gcd
import json
import os
import platform
from pathlib import Path


FACETS = (
    (0, 1, 2), (0, 1, 3), (0, 2, 4), (0, 3, 5), (0, 4, 5),
    (1, 2, 5), (1, 3, 4), (1, 4, 5), (2, 3, 4), (2, 3, 5),
)


def bareiss_determinant(matrix: list[list[int]]) -> int:
    """Fraction-free determinant with exact integer arithmetic."""
    if not matrix:
        return 1
    values = [row[:] for row in matrix]
    size = len(values)
    if any(len(row) != size for row in values):
        raise ValueError("determinant requires a square matrix")
    sign = 1
    previous_pivot = 1
    for pivot_index in range(size - 1):
        pivot_row = next(
            (row for row in range(pivot_index, size)
             if values[row][pivot_index] != 0),
            None,
        )
        if pivot_row is None:
            return 0
        if pivot_row != pivot_index:
            values[pivot_index], values[pivot_row] = (
                values[pivot_row], values[pivot_index]
            )
            sign = -sign
        pivot = values[pivot_index][pivot_index]
        for row in range(pivot_index + 1, size):
            for column in range(pivot_index + 1, size):
                numerator = (
                    values[row][column] * pivot
                    - values[row][pivot_index] * values[pivot_index][column]
                )
                if numerator % previous_pivot:
                    raise ArithmeticError("Bareiss exact-division invariant failed")
                values[row][column] = numerator // previous_pivot
        for row in range(pivot_index + 1, size):
            values[row][pivot_index] = 0
        previous_pivot = pivot
    return sign * values[-1][-1]


def determinantal_invariants(matrix: list[list[int]]) -> list[int]:
    """Compute Smith factors from gcds of all minors; intended for small matrices."""
    if not matrix or not matrix[0]:
        return []
    rows, columns = len(matrix), len(matrix[0])
    if any(len(row) != columns for row in matrix):
        raise ValueError("matrix must be rectangular")
    factors: list[int] = []
    previous_divisor = 1
    for order in range(1, min(rows, columns) + 1):
        divisor = 0
        for row_ids in combinations(range(rows), order):
            for column_ids in combinations(range(columns), order):
                minor = [
                    [matrix[row][column] for column in column_ids]
                    for row in row_ids
                ]
                divisor = gcd(divisor, abs(bareiss_determinant(minor)))
        if divisor == 0:
            break
        if divisor % previous_divisor:
            raise AssertionError("determinantal divisors do not form a divisibility chain")
        factors.append(divisor // previous_divisor)
        previous_divisor = divisor
    return factors


def elementary_unimodular_transform(matrix: list[list[int]]) -> list[list[int]]:
    result = [row[:] for row in matrix]
    rows, columns = len(result), len(result[0])
    if rows > 1:
        result[0], result[-1] = result[-1], result[0]
        result[1] = [a + 2 * b for a, b in zip(result[1], result[0])]
    if columns > 1:
        for row in result:
            row[0], row[-1] = row[-1], row[0]
        for row in result:
            row[1] -= row[0]
    return result


def test_small_integer_snf_fixtures_and_unimodular_equivalence() -> None:
    fixtures = (
        ([[2, 4], [6, 8]], [2, 4]),
        ([[0, 2], [3, 0]], [1, 6]),
        ([[4, 6], [3, 9]], [1, 18]),
        ([[0, 0], [0, 6]], [6]),
        ([[-2, 4, 0], [6, -8, 2]], [2, 2]),
    )
    for matrix, expected in fixtures:
        factors = determinantal_invariants(matrix)
        assert factors == expected
        assert all(factors[index + 1] % factors[index] == 0
                   for index in range(len(factors) - 1))
        assert determinantal_invariants(elementary_unimodular_transform(matrix)) == factors



def _rank_mod2(matrix: list[list[int]]) -> int:
    if not matrix:
        return 0
    values = [[entry & 1 for entry in row] for row in matrix]
    row_count, column_count = len(values), len(values[0])
    pivot_row = 0
    for column in range(column_count):
        selected = next(
            (row for row in range(pivot_row, row_count) if values[row][column]),
            None,
        )
        if selected is None:
            continue
        values[pivot_row], values[selected] = values[selected], values[pivot_row]
        for row in range(pivot_row + 1, row_count):
            if values[row][column]:
                values[row] = [
                    left ^ right
                    for left, right in zip(values[row], values[pivot_row])
                ]
        pivot_row += 1
        if pivot_row == row_count:
            break
    return pivot_row


def _boundary_matrices():
    vertices = tuple(range(6))
    edges = tuple(combinations(vertices, 2))
    edge_index = {edge: index for index, edge in enumerate(edges)}
    d1 = [[0 for _ in edges] for _ in vertices]
    for column, (a, b) in enumerate(edges):
        d1[a][column] = -1
        d1[b][column] = 1

    d2 = [[0 for _ in FACETS] for _ in edges]
    for column, (a, b, c) in enumerate(FACETS):
        d2[edge_index[(b, c)]][column] += 1
        d2[edge_index[(a, c)]][column] -= 1
        d2[edge_index[(a, b)]][column] += 1
    return vertices, edges, d1, d2


def _multiply(left: list[list[int]], right: list[list[int]]) -> list[list[int]]:
    return [
        [sum(left[row][k] * right[k][column] for k in range(len(right)))
         for column in range(len(right[0]))]
        for row in range(len(left))
    ]


def _rp2_h1_presentation(edges: tuple[tuple[int, int], ...]) -> list[list[int]]:
    # Collapse the explicit spanning tree {0-i | i=1..5}. Its five edges
    # generate no H1 generators; each triangle boundary becomes a relation
    # among the ten remaining edge generators.
    tree_edges = {(0, vertex) for vertex in range(1, 6)}
    generators = [edge for edge in edges if edge not in tree_edges]
    generator_index = {edge: index for index, edge in enumerate(generators)}
    presentation = [[0 for _ in FACETS] for _ in generators]
    for face_index, (a, b, c) in enumerate(FACETS):
        for edge, coefficient in (
            ((b, c), 1), ((a, c), -1), ((a, b), 1)
        ):
            if edge not in tree_edges:
                presentation[generator_index[edge]][face_index] += coefficient
    return presentation



def test_emit_independent_reference_receipt() -> None:
    vertices, edges, d1, d2 = _boundary_matrices()
    presentation = _rp2_h1_presentation(edges)
    full_determinant = bareiss_determinant(presentation)
    unit_minor = [
        [value for column, value in enumerate(row) if column != 0]
        for row_index, row in enumerate(presentation) if row_index != 2
    ]
    rp2_mod2 = {
        "b0": len(vertices) - _rank_mod2([[x & 1 for x in row] for row in d1]),
        "b1": len(edges)
              - _rank_mod2([[x & 1 for x in row] for row in d1])
              - _rank_mod2([[x & 1 for x in row] for row in d2]),
        "b2": len(FACETS) - _rank_mod2([[x & 1 for x in row] for row in d2]),
    }
    fixtures = (
        [[2, 4], [6, 8]],
        [[0, 2], [3, 0]],
        [[4, 6], [3, 9]],
        [[0, 0], [0, 6]],
        [[-2, 4, 0], [6, -8, 2]],
    )
    binding = json.loads(
        (Path(__file__).resolve().parents[1] / "SOURCE_BINDING.json").read_text()
    )
    receipt = {
        "schema": "merlin-cace-oci-independent-reference-v1",
        "source_repository": binding["source_repository"],
        "source_commit": binding["source_commit"],
        "runner": {
            "name": os.environ.get("RUNNER_NAME", "unknown"),
            "os": os.environ.get("RUNNER_OS", platform.system()),
            "arch": os.environ.get("RUNNER_ARCH", platform.machine()),
            "platform": platform.platform(),
        },
        "workflow": {
            "repository": os.environ.get("GITHUB_REPOSITORY", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
            "job": os.environ.get("GITHUB_JOB", ""),
            "workflow_sha": os.environ.get("GITHUB_WORKFLOW_SHA", ""),
        },
        "implementation": "pure-python-bareiss-determinants-and-tree-collapse",
        "rp2": {
            "vertices": len(vertices),
            "edges": len(edges),
            "triangles": len(FACETS),
            "euler_characteristic": len(vertices) - len(edges) + len(FACETS),
            "integral_homology": {"H0": "Z", "H1": "Z/2", "H2": "0"},
            "mod2_betti": rp2_mod2,
            "tree_collapsed_presentation_determinant": full_determinant,
            "unit_9x9_minor_determinant": bareiss_determinant(unit_minor),
            "smith_invariant_factors": [1] * 9 + [abs(full_determinant)],
        },
        "snf_fixtures": [
            {"matrix": matrix, "invariant_factors": determinantal_invariants(matrix)}
            for matrix in fixtures
        ],
    }
    assert receipt["rp2"]["mod2_betti"] == {"b0": 1, "b1": 1, "b2": 1}
    assert receipt["rp2"]["smith_invariant_factors"] == [1] * 9 + [2]
    artifact_dir_name = os.environ.get("CACE_ARTIFACT_DIR")
    runner_temp = os.environ.get("RUNNER_TEMP")
    if artifact_dir_name and runner_temp:
        output_dir = Path(runner_temp) / artifact_dir_name
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        (output_dir / "merlin-continuum-independent-reference-receipt.json").write_bytes(
            payload + b"\\n"
        )


def test_six_vertex_triangulated_rp2_integral_homology() -> None:
    vertices, edges, d1, d2 = _boundary_matrices()
    assert len(vertices) == 6
    assert len(edges) == 15
    assert len(FACETS) == 10
    assert len({tuple(sorted(face)) for face in FACETS}) == 10
    assert all(sum(1 for face in FACETS if set(edge).issubset(face)) == 2
               for edge in edges)
    for vertex in vertices:
        link_edges = [
            tuple(sorted(set(face) - {vertex}))
            for face in FACETS if vertex in face
        ]
        link_degrees = {other: 0 for edge in link_edges for other in edge}
        for left, right in link_edges:
            link_degrees[left] += 1
            link_degrees[right] += 1
        assert link_degrees and all(degree == 2 for degree in link_degrees.values())
    assert _multiply(d1, d2) == [[0 for _ in FACETS] for _ in vertices]
    assert len(vertices) - len(edges) + len(FACETS) == 1

    # Over F2, the non-orientable surface has a mod-2 fundamental class:
    # b0=b1=b2=1. This is deliberately distinct from integral H2=0.
    d1_mod2 = [[value & 1 for value in row] for row in d1]
    d2_mod2 = [[value & 1 for value in row] for row in d2]
    rank_d1 = _rank_mod2(d1_mod2)
    rank_d2 = _rank_mod2(d2_mod2)
    assert (len(vertices) - rank_d1, len(edges) - rank_d1 - rank_d2,
            len(FACETS) - rank_d2) == (1, 1, 1)

    # The star at vertex 0 is a spanning tree, so the 1-skeleton is connected:
    # H0(RP2; Z) = Z. The reduced 10x10 relation matrix presents H1.
    presentation = _rp2_h1_presentation(edges)
    assert len(presentation) == 10 and all(len(row) == 10 for row in presentation)
    assert bareiss_determinant(presentation) == -2

    # A unit 9x9 minor proves the first nine determinantal divisors are 1:
    # the selected submatrix is unimodular, so all its exterior powers have
    # integral inverses. The full determinant then gives final factor 2.
    unit_minor = [
        [value for column, value in enumerate(row) if column != 0]
        for row_index, row in enumerate(presentation) if row_index != 2
    ]
    assert bareiss_determinant(unit_minor) == -1
    assert [1] * 9 + [2] == [1, 1, 1, 1, 1, 1, 1, 1, 1, 2]

    full_determinant = bareiss_determinant(presentation)
    unit_minor_determinant = bareiss_determinant(unit_minor)
    factors_from_minor_witness = [1] * 9 + [abs(full_determinant)]
    assert abs(unit_minor_determinant) == 1
    assert factors_from_minor_witness == [1] * 9 + [2]

    # The relation matrix is nonsingular, so the simplicial boundary map
    # d2 is injective and H2=0. Together: H0=Z, H1=Z/2, H2=0.

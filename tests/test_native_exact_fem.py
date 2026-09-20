from __future__ import annotations

import pytest

from cace_studio.core.native_runtime import NativeRuntime


def square_center_inputs():
    vertices = [
        ("0", "0"),
        ("1", "0"),
        ("1", "1"),
        ("0", "1"),
        ("1/2", "1/2"),
    ]
    triangles = [
        (0, 1, 4),
        (1, 2, 4),
        (2, 3, 4),
        (3, 0, 4),
    ]
    p1 = [
        ("0", "0", "2"),
        ("2", "-2", "0"),
        ("2", "0", "-2"),
        ("0", "2", "0"),
    ]
    rt0 = [("1", "0", "0")] * 4
    return vertices, triangles, p1, rt0


def native_or_skip() -> NativeRuntime:
    runtime = NativeRuntime()
    if not runtime.status.available:
        pytest.skip(runtime.status.reason)
    if not hasattr(runtime.lib, "cace_exact_mesh_create"):
        pytest.skip("native library predates exact-FEM C ABI")
    return runtime


def test_native_exact_fem_matches_formal_square_center_fixture():
    runtime = native_or_skip()
    result = runtime.exact_fem_evaluate(*square_center_inputs())

    assert result["backend"] == "cpp20-cabi-exact-fem"
    assert result["counts"] == {
        "vertices": 5,
        "triangles": 4,
        "edges": 8,
        "interior_edges": 4,
        "boundary_edges": 4,
    }
    assert result["signed_jacobians"] == ["1/2"] * 4
    assert [cell["cell_pairing"] for cell in result["cell_values"]] == [
        "0",
        "-1/2",
        "0",
        "1/2",
    ]
    assert result["assembly"] == {
        "all_local_green": True,
        "orthogonality_sum_zero": True,
        "equilibrium_failures": 0,
        "boundary_failures": 0,
        "interior_failures": 0,
        "ready_for_lean_assembly": True,
    }
    assert result["formal_state"] == "generated-inputs-unqualified"
    assert "canonical qualification" in result["scope_note"]


def test_native_exact_fem_rejects_binary_float_before_native_call():
    runtime = native_or_skip()
    vertices, triangles, p1, rt0 = square_center_inputs()
    vertices[4] = (0.5, "1/2")
    with pytest.raises(ValueError, match="binary floats"):
        runtime.exact_fem_evaluate(vertices, triangles, p1, rt0)


def test_native_exact_fem_changed_flux_fails_admissibility_without_changing_green_algebra():
    runtime = native_or_skip()
    vertices, triangles, p1, rt0 = square_center_inputs()
    changed = list(rt0)
    changed[0] = ("1", "0", "1")
    result = runtime.exact_fem_evaluate(vertices, triangles, p1, changed)

    assert result["assembly"]["all_local_green"] is True
    assert result["assembly"]["ready_for_lean_assembly"] is False
    assert (
        result["assembly"]["equilibrium_failures"]
        + result["assembly"]["boundary_failures"]
        + result["assembly"]["interior_failures"]
    ) > 0


@pytest.mark.parametrize("bad_id", [0.0, "0", False, 1.5])
def test_native_exact_fem_rejects_coercible_triangle_ids(bad_id):
    runtime = native_or_skip()
    vertices, triangles, p1, rt0 = square_center_inputs()
    triangles[0] = (bad_id, 1, 4)
    with pytest.raises(ValueError, match="genuine integers"):
        runtime.exact_fem_evaluate(vertices, triangles, p1, rt0)

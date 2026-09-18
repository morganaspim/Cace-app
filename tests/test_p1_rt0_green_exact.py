from fractions import Fraction

from cace_studio.core.p1_rt0_green_exact import (
    build_exact_green_artifact,
    check_exact_discrete_green,
)
from cace_studio.modules.flux_v126_130_common import (
    center_square_mesh,
    exact_p1_poisson_center_square,
    reconstruct_equilibrated_flux,
)


def _fixture():
    points, triangles, values, _ = exact_p1_poisson_center_square(1)
    rec = reconstruct_equilibrated_flux(points, triangles, 1)
    assert rec["pass"]
    return build_exact_green_artifact(
        points, triangles, values, rec["global_edge_flux_dofs"]
    )


def test_exact_p1_rt0_green_identity_and_interior_cancellation():
    result = check_exact_discrete_green(_fixture())
    assert result["passed"], result["errors"]
    assert result["assembled_green_residual"] == "0"
    assert result["interior_edge_residual"] == "0"
    assert all(v == "0" for v in result["interior_edge_terms"].values())
    assert result["evidence_class"].startswith("rigorous exact computation")


def test_checker_detects_broken_shared_flux_dimension():
    artifact = _fixture()
    artifact["global_edge_flux_dofs"] = artifact["global_edge_flux_dofs"][:-1]
    result = check_exact_discrete_green(artifact)
    assert not result["passed"]
    assert "global RT0 edge-DOF dimension invalid" in result["errors"]


def test_checker_detects_non_ccw_cell():
    artifact = _fixture()
    artifact["triangles"][0] = list(reversed(artifact["triangles"][0]))
    result = check_exact_discrete_green(artifact)
    assert not result["passed"]
    assert any("topology invalid" in e for e in result["errors"])


def test_green_identity_is_not_boundary_zero_assumption():
    # Constant v=1 deliberately has nonzero boundary trace. The local/global
    # Green identity must still hold; boundary terms are computed, not discarded.
    points, triangles = center_square_mesh()
    rec = reconstruct_equilibrated_flux(points, triangles, 1)
    artifact = build_exact_green_artifact(
        points, triangles, [Fraction(1)] * len(points), rec["global_edge_flux_dofs"]
    )
    result = check_exact_discrete_green(artifact)
    assert result["passed"], result["errors"]
    assert result["global_boundary_pairing"] != "0"
    assert result["assembled_green_residual"] == "0"

from __future__ import annotations

import copy

import pytest

from cace_studio.app import build_registry
from cace_studio.core.mesh_certificate import (
    generate_mesh_certificate,
    render_lean_mesh_certificate,
    verify_mesh_certificate,
)


def square_center_mesh():
    return {
        "vertices": [["0", "0"], ["1", "0"], ["1", "1"], ["0", "1"], ["1/2", "1/2"]],
        "triangles": [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]],
        "boundary_labels": {
            "0-1": "bottom",
            "1-2": "right",
            "2-3": "top",
            "0-3": "left",
        },
    }


def test_general_mesh_certificate_exact_roundtrip():
    mesh = square_center_mesh()
    cert = generate_mesh_certificate(
        mesh["vertices"], mesh["triangles"], mesh["boundary_labels"]
    )
    check = verify_mesh_certificate(cert)
    assert check["passed"] is True
    assert cert["counts"] == {
        "vertices": 5,
        "triangles": 4,
        "edges": 8,
        "interior_edges": 4,
        "boundary_edges": 4,
    }
    assert cert["signed_jacobians"] == ["1/2"] * 4
    assert cert["edges"][0]["vertices"] == [0, 1]


def test_reversed_triangle_orientation_is_rejected():
    mesh = square_center_mesh()
    mesh["triangles"][0] = [1, 0, 4]
    with pytest.raises(ValueError, match="non-positive signed Jacobian"):
        generate_mesh_certificate(
            mesh["vertices"], mesh["triangles"], mesh["boundary_labels"]
        )


def test_float_geometry_is_rejected_instead_of_silently_rounded():
    mesh = square_center_mesh()
    mesh["vertices"][4] = [0.5, 0.5]
    with pytest.raises(ValueError, match="binary floats are intentionally rejected"):
        generate_mesh_certificate(
            mesh["vertices"], mesh["triangles"], mesh["boundary_labels"]
        )


def test_tampered_certificate_is_rejected():
    mesh = square_center_mesh()
    cert = generate_mesh_certificate(
        mesh["vertices"], mesh["triangles"], mesh["boundary_labels"]
    )
    bad = copy.deepcopy(cert)
    bad["local_edges"][0][0]["edge"] = 7
    check = verify_mesh_certificate(bad)
    assert check["passed"] is False
    assert any("sha256" in e or "differs" in e for e in check["errors"])


def test_nonmanifold_edge_is_rejected():
    vertices = [["0", "0"], ["1", "0"], ["0", "1"], ["1", "1"], ["1/2", "-1"]]
    triangles = [[0, 1, 2], [1, 0, 4], [0, 1, 3]]
    with pytest.raises(ValueError, match="non-manifold edge"):
        generate_mesh_certificate(vertices, triangles)


def test_empty_boundary_label_is_rejected():
    mesh = square_center_mesh()
    mesh["boundary_labels"]["0-1"] = ""
    with pytest.raises(ValueError, match="empty label"):
        generate_mesh_certificate(
            mesh["vertices"], mesh["triangles"], mesh["boundary_labels"]
        )


def test_label_on_interior_edge_is_rejected():
    mesh = square_center_mesh()
    mesh["boundary_labels"]["1-4"] = "not-boundary"
    with pytest.raises(ValueError, match="non-boundary or absent"):
        generate_mesh_certificate(
            mesh["vertices"], mesh["triangles"], mesh["boundary_labels"]
        )


def test_lean_renderer_emits_closed_geometry_linked_meshcertificate_source():
    mesh = square_center_mesh()
    cert = generate_mesh_certificate(
        mesh["vertices"], mesh["triangles"], mesh["boundary_labels"]
    )
    source = render_lean_mesh_certificate(cert, "testGeneratedMesh")
    assert "def testGeneratedMesh : MeshCertificate where" in source
    assert "vertexCount := 5" in source
    assert "signedJacobian_formula" in source
    assert "edge_vertices_canonical" in source
    assert "local_edge_geometry" in source
    assert "interior_cells_distinct" in source
    assert "boundary_label_nonempty" in source
    assert "local_edge_complete" in source
    assert "interior_signs_opposite" in source
    assert "signedJacobian_pos" in source
    assert "sorry" not in source
    assert "admit" not in source


def test_studio_registry_exposes_verified_baseline_and_generator():
    registry = build_registry()
    assert registry.contains("formal322.concrete_mesh_certificate_prager_synge")
    assert registry.contains("formal325.mesh_certificate_generator")

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction

import pytest

from cace_studio.core.formal_runtime_packet import (
    FormalRuntimePacket,
    FormalRuntimePacketError,
    build_p1_rt0_packet,
)
from cace_studio.core.formal_source_binding import (
    lean_rational,
    p1_affine_binding,
    render_mesh_certificate_lean,
    rt0_affine_binding,
)


def _square_center_packet(**overrides):
    kwargs = {
        "vertices": [
            (0, 0),
            (1, 0),
            (1, 1),
            (0, 1),
            (Fraction(1, 2), Fraction(1, 2)),
        ],
        "triangles": [
            (0, 1, 4),
            (1, 2, 4),
            (2, 3, 4),
            (3, 0, 4),
        ],
        "p1_cells": [
            (0, 0, 2),
            (0, -2, 0),
            (0, 0, -2),
            (0, 2, 0),
        ],
        "rt0_cells": [(1, 0, 0)] * 4,
        "source_module": "unit.square_center",
        "source_version": "1.0.0",
        "boundary_labels": {
            (0, 1): "bottom",
            (1, 2): "right",
            (2, 3): "top",
            (0, 3): "left",
        },
    }
    kwargs.update(overrides)
    return build_p1_rt0_packet(**kwargs)


def test_packet_is_deterministic_content_addressed_and_roundtrips():
    first = _square_center_packet()
    second = _square_center_packet()
    assert first.packet_sha256 == second.packet_sha256
    assert first.to_mapping() == second.to_mapping()
    assert first.verify_hash()
    assert FormalRuntimePacket.from_mapping(first.to_mapping()) == first


def test_one_coefficient_change_changes_packet_identity():
    first = _square_center_packet()
    changed_cells = [(0, 0, 2), (0, -2, 0), (0, 0, -2), ("1/3", 2, 0)]
    changed = _square_center_packet(p1_cells=changed_cells)
    assert changed.packet_sha256 != first.packet_sha256


def test_float_input_is_rejected_instead_of_silently_becoming_exact_real():
    vertices = [(0.0, 0), (1, 0), (1, 1), (0, 1), ("1/2", "1/2")]
    with pytest.raises(FormalRuntimePacketError, match="floating-point values are forbidden"):
        _square_center_packet(vertices=vertices)


def test_clockwise_or_degenerate_triangle_is_rejected():
    kwargs = {
        "vertices": [(0, 0), (1, 0), (0, 1)],
        "triangles": [(0, 2, 1)],
        "p1_cells": [(0, 1, 1)],
        "rt0_cells": [(0, 0, 0)],
        "source_module": "unit.bad",
        "source_version": "1",
    }
    with pytest.raises(FormalRuntimePacketError, match="positively oriented"):
        build_p1_rt0_packet(**kwargs)


def test_nonmanifold_edge_is_rejected():
    kwargs = {
        "vertices": [(0, 0), (1, 0), (0, 1), (1, -1), (2, 1)],
        "triangles": [(0, 1, 2), (1, 0, 3), (0, 1, 4)],
        "p1_cells": [(0, 0, 0)] * 3,
        "rt0_cells": [(0, 0, 0)] * 3,
        "source_module": "unit.nonmanifold",
        "source_version": "1",
    }
    with pytest.raises(FormalRuntimePacketError, match="one boundary owner or two interior owners"):
        build_p1_rt0_packet(**kwargs)


def test_square_center_topology_matches_general_mesh_certificate_conventions():
    packet = _square_center_packet()
    assert len(packet.vertices) == 5
    assert len(packet.triangles) == 4
    assert len(packet.edges) == 8
    assert len(packet.interior_edges) == 4
    assert len(packet.boundary_edges) == 4
    assert all(j.fraction == Fraction(1, 2) for j in packet.signed_jacobians)
    assert set(packet.local_signs[3]) == {"pos", "neg"}


def test_tampered_packet_or_noncanonical_topology_is_rejected():
    packet = _square_center_packet()
    raw = packet.to_mapping()
    tampered = deepcopy(raw)
    tampered["p1_cells"][0]["gx"]["numerator"] = 99
    with pytest.raises(FormalRuntimePacketError, match="SHA-256 mismatch"):
        FormalRuntimePacket.from_mapping(tampered)

    topology_tamper = deepcopy(raw)
    topology_tamper["topology"]["local_edges"][0][0] = 7
    with pytest.raises(FormalRuntimePacketError, match="topology/content is not canonical"):
        FormalRuntimePacket.from_mapping(topology_tamper)


def test_exact_p1_and_rt0_bindings_preserve_coefficient_order_and_packet_identity():
    packet = _square_center_packet(
        p1_cells=[("1/2", "-2/3", "5/7")] * 4,
        rt0_cells=[("-1/3", "4/5", "-6/11")] * 4,
    )
    p1 = p1_affine_binding(packet, 0)
    rt0 = rt0_affine_binding(packet, 0)
    assert p1["packet_sha256"] == packet.packet_sha256
    assert rt0["packet_sha256"] == packet.packet_sha256
    assert p1["lean_type"] == "CACEFormal.P1Affine"
    assert rt0["lean_type"] == "CACEFormal.RT0Affine"
    assert "gx := (-2 / 3 : ℚ)" in p1["lean_expression"]
    assert "radial := (-6 / 11 : ℚ)" in rt0["lean_expression"]
    assert lean_rational(packet.p1_cells[0].c) == "(1 / 2 : ℚ)"


def test_generated_mesh_binding_is_content_addressed_and_explicitly_unqualified():
    packet = _square_center_packet()
    binding = render_mesh_certificate_lean(packet, definition_name="unitMesh")
    assert binding.verify()
    assert binding.state == "generated-unqualified"
    assert binding.packet_sha256 == packet.packet_sha256
    assert f"CACE runtime packet SHA-256: {packet.packet_sha256}" in binding.source
    assert "def unitMesh : MeshCertificate where" in binding.source
    assert "signedJacobian_formula := by native_decide" in binding.source
    assert "local_edge_complete := by native_decide" in binding.source
    assert "It is not canonical formal evidence" in binding.source


def test_generated_binding_changes_when_mathematical_packet_changes():
    first = render_mesh_certificate_lean(_square_center_packet(), definition_name="unitMesh")
    changed = render_mesh_certificate_lean(
        _square_center_packet(rt0_cells=[(2, 0, 0)] * 4),
        definition_name="unitMesh",
    )
    assert first.packet_sha256 != changed.packet_sha256
    assert first.source_sha256 != changed.source_sha256


def test_boundary_labels_must_reference_actual_canonical_boundary_edges():
    labels = {
        (0, 1): "bottom",
        (1, 2): "right",
        (2, 3): "top",
        (0, 3): "left",
        (1, 4): "not-boundary",
    }
    with pytest.raises(FormalRuntimePacketError, match="non-boundary edges"):
        _square_center_packet(boundary_labels=labels)

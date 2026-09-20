from __future__ import annotations

import copy

import pytest

from cace_studio.app import build_registry
from cace_studio.core.formal_runtime_packet import (
    build_p1_rt0_runtime_packet,
    render_lean_p1_rt0_binding,
    verify_p1_rt0_runtime_packet,
)
from cace_studio.core.formal_source_binding import (
    create_formal_source_binding,
    verify_formal_source_binding,
)
from cace_studio.core.module import ExecutionContext
from cace_studio.core.verification import VerificationState


def runtime_fixture():
    mesh = {
        "vertices": [["0", "0"], ["1", "0"], ["1", "1"], ["0", "1"], ["1/2", "1/2"]],
        "triangles": [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]],
        "boundary_labels": {
            "0-1": "bottom",
            "1-2": "right",
            "2-3": "top",
            "0-3": "left",
        },
    }
    p1 = [
        {"c": "0", "gx": "1", "gy": "0"},
        {"c": "1", "gx": "0", "gy": "1"},
        {"c": "2", "gx": "-1", "gy": "0"},
        {"c": "1", "gx": "0", "gy": "-1"},
    ]
    rt0 = [
        {"cx": "0", "cy": "0", "radial": "1/2"},
        {"cx": "1", "cy": "0", "radial": "1/3"},
        {"cx": "0", "cy": "1", "radial": "-1/4"},
        {"cx": "-1", "cy": "0", "radial": "2"},
    ]
    return {"mesh": mesh, "p1_cells": p1, "rt0_cells": rt0}


def build_packet():
    data = runtime_fixture()
    return build_p1_rt0_runtime_packet(
        data["mesh"],
        data["p1_cells"],
        data["rt0_cells"],
        source_identity={"module_id": "test.fixture", "module_version": "1"},
    )


def test_packet_is_deterministic_and_exact():
    first = build_packet()
    second = build_packet()
    assert first == second
    assert verify_p1_rt0_runtime_packet(first)["passed"] is True
    assert first["numeric_policy"]["binary_float_policy"] == "rejected"
    assert first["p1_cells"][0] == {"c": "0", "gx": "1", "gy": "0"}
    assert first["rt0_cells"][0]["radial"] == "1/2"


def test_coefficient_change_changes_packet_identity():
    data = runtime_fixture()
    first = build_p1_rt0_runtime_packet(data["mesh"], data["p1_cells"], data["rt0_cells"])
    changed = copy.deepcopy(data)
    changed["p1_cells"][0]["gx"] = "2"
    second = build_p1_rt0_runtime_packet(
        changed["mesh"], changed["p1_cells"], changed["rt0_cells"]
    )
    assert first["packet_sha256"] != second["packet_sha256"]


@pytest.mark.parametrize(
    "family, field",
    [
        ("p1_cells", "gx"),
        ("rt0_cells", "radial"),
    ],
)
def test_binary_float_coefficients_are_rejected(family, field):
    data = runtime_fixture()
    data[family][0][field] = 0.5
    with pytest.raises(ValueError, match="binary floats are intentionally rejected"):
        build_p1_rt0_runtime_packet(data["mesh"], data["p1_cells"], data["rt0_cells"])


def test_cell_count_must_match_mesh():
    data = runtime_fixture()
    data["p1_cells"].pop()
    with pytest.raises(ValueError, match="does not match triangle count"):
        build_p1_rt0_runtime_packet(data["mesh"], data["p1_cells"], data["rt0_cells"])


def test_coefficient_schema_is_fail_closed():
    data = runtime_fixture()
    data["rt0_cells"][0]["r"] = data["rt0_cells"][0].pop("radial")
    with pytest.raises(ValueError, match="coefficient fields mismatch"):
        build_p1_rt0_runtime_packet(data["mesh"], data["p1_cells"], data["rt0_cells"])


def test_tampered_packet_is_rejected():
    packet = build_packet()
    bad = copy.deepcopy(packet)
    bad["p1_cells"][0]["gx"] = "7"
    check = verify_p1_rt0_runtime_packet(bad)
    assert check["passed"] is False
    assert any("packet_sha256" in item or "differs" in item for item in check["errors"])


def test_lean_source_contains_exact_mesh_p1_rt0_binding_without_proof_shortcuts():
    packet = build_packet()
    source = render_lean_p1_rt0_binding(
        packet,
        mesh_definition_name="testRuntimeMesh",
        binding_prefix="testRuntimeBinding",
    )
    assert "def testRuntimeMesh : MeshCertificate where" in source
    assert "def testRuntimeBindingP1" in source
    assert "def testRuntimeBindingRT0" in source
    assert f'def testRuntimeBindingPacketSha256 : String := "{packet["packet_sha256"]}"' in source
    assert "import CACEFormal.P1RT0Element" in source
    assert "sorry" not in source
    assert "admit" not in source


def test_source_binding_is_content_addressed_and_unqualified():
    packet = build_packet()
    source = render_lean_p1_rt0_binding(
        packet,
        mesh_definition_name="testRuntimeMesh",
        binding_prefix="testRuntimeBinding",
    )
    binding = create_formal_source_binding(
        packet,
        source,
        mesh_definition_name="testRuntimeMesh",
        binding_prefix="testRuntimeBinding",
    )
    check = verify_formal_source_binding(binding, packet, source)
    assert check["passed"] is True
    assert binding["formal_claim"] is False
    assert binding["lean_build_state"] == "NOT_RUN"
    assert binding["qualification_state"] == "NOT_RUN"
    assert binding["fsl_status"]["FSL-2"] == "GENERATED_NOT_BUILT"
    assert binding["fsl_status"]["FSL-13"] == "UNRESOLVED"


def test_tampered_generated_source_breaks_binding():
    packet = build_packet()
    source = render_lean_p1_rt0_binding(
        packet,
        mesh_definition_name="testRuntimeMesh",
        binding_prefix="testRuntimeBinding",
    )
    binding = create_formal_source_binding(
        packet,
        source,
        mesh_definition_name="testRuntimeMesh",
        binding_prefix="testRuntimeBinding",
    )
    check = verify_formal_source_binding(binding, packet, source + "\n-- tampered")
    assert check["passed"] is False
    assert "Lean source SHA-256 mismatch" in check["errors"]


def test_registry_exposes_exact_runtime_binding_module():
    registry = build_registry()
    assert registry.contains("formal_bridge.p1_rt0_runtime_packet")


def test_module_emits_symbolic_not_formal_evidence():
    registry = build_registry()
    module = registry.create("formal_bridge.p1_rt0_runtime_packet")
    data = runtime_fixture()
    params = module.resolved_params({})
    module.validate({"runtime_data": data}, params)
    outputs = module.execute(
        {"runtime_data": data},
        params,
        ExecutionContext(run_id="fsl-test"),
    )
    records = module.verify(
        {"runtime_data": data},
        params,
        outputs,
        ExecutionContext(run_id="fsl-test"),
    )
    assert len(records) == 1
    assert records[0].state is VerificationState.PASS
    assert records[0].kind.value == "symbolic"
    assert outputs["source_binding"]["fsl_status"]["FSL-5"] == "UNRESOLVED"
    check = verify_formal_source_binding(\n        outputs["source_binding"], outputs["runtime_packet"], outputs["lean_source"]\n    )\n    assert check["passed"] is True\n
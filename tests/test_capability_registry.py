from __future__ import annotations

import json
from pathlib import Path

import pytest

from cace_studio.app import build_qualified_capabilities, build_registry
from cace_studio.core.capability_registry import CapabilityRegistryError
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, Node


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "ops" / "capability_workflows.json"

EXPECTED_INITIAL_UI = {
    "core.constant",
    "core.add",
    "science.grid1d",
    "science.quadratic",
    "science.second_derivative",
    "verify.constant_residual",
    "verify.interval_literal",
    "verify.interval_square",
    "geometry.circle",
    "geometry.parabola",
    "geometry.conic",
    "geometry.hyperbola",
    "geometry.sphere",
    "geometry.hypercube",
    "chemistry.atom",
    "chemistry.bond",
    "geometry.affine_transform_object",
    "math.graph_equation_3d",
    "math.graph_equation_2d",
    "math.equation_features",
    "math.custom_equation",
}


def _experiment(payload: dict) -> Experiment:
    return Experiment(
        schema_version=int(payload.get("schema_version", 1)),
        name=str(payload.get("name", "Capability workflow")),
        nodes=[
            Node(
                id=str(item["id"]),
                module_id=str(item["module_id"]),
                params=dict(item.get("params", {})),
            )
            for item in payload.get("nodes", [])
        ],
        edges=[
            Edge(
                source_node=str(item["source_node"]),
                source_port=str(item["source_port"]),
                target_node=str(item["target_node"]),
                target_port=str(item["target_port"]),
            )
            for item in payload.get("edges", [])
        ],
    )


def _lookup_output(result, dotted: str):
    node_id, port = dotted.split(".", 1)
    return result.outputs[node_id][port]


def test_initial_production_palette_is_explicit_and_fail_closed():
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)

    assert set(capabilities.module_ids("ui")) == EXPECTED_INITIAL_UI
    assert set(capabilities.module_ids("link")) == EXPECTED_INITIAL_UI
    assert set(capabilities.module_ids("ai")) == EXPECTED_INITIAL_UI
    assert set(capabilities.module_ids("api")) == EXPECTED_INITIAL_UI

    # The engineering registry intentionally contains much more research/formal
    # code than the product palette. Presence in Python is never enough to expose it.
    assert registry.contains("formal325.mesh_certificate_generator")
    assert not capabilities.contains("formal325.mesh_certificate_generator")
    assert not capabilities.allowed("formal325.mesh_certificate_generator", "ui")
    with pytest.raises(CapabilityRegistryError):
        capabilities.require("formal325.mesh_certificate_generator", "api")


def test_every_exposed_module_has_workflow_and_safe_public_help():
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)
    workflow_ids = {
        item["workflow_id"]
        for item in json.loads(WORKFLOWS.read_text())["workflows"]
    }

    for module_id in capabilities.module_ids("ui"):
        payload = capabilities.module_payload(module_id)
        assert payload["workflow_ids"]
        assert set(payload["workflow_ids"]) <= workflow_ids
        assert payload["public_help"]["summary"].strip()
        assert payload["metadata_is_verification_evidence"] is False
        assert payload["proof_effect"] == "none"
        assert payload["promotion_authority"] is False
        # Public help describes contracts, not implementation source.
        public_help_text = json.dumps(payload["public_help"]).lower()
        assert "cace_studio/" not in public_help_text
        assert "formal/cace_formal" not in public_help_text
        assert "source code" not in public_help_text


def test_every_declared_capability_workflow_executes_and_matches_expectations():
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)
    data = json.loads(WORKFLOWS.read_text())

    seen: set[str] = set()
    for workflow in data["workflows"]:
        exp = _experiment(workflow["experiment"])
        capabilities.validate_experiment(exp, surface="api")

        # Every edge offered by a production workflow is known-compatible through
        # the same connection contract consumed by the UI.
        nodes = exp.node_map()
        for edge in exp.edges:
            assert capabilities.connection_error(
                nodes[edge.source_node].module_id,
                edge.source_port,
                nodes[edge.target_node].module_id,
                edge.target_port,
            ) is None

        executor = GraphExecutor(registry)
        executor.validate(exp)
        result = executor.run(exp)
        expected = workflow["expected"]
        assert result.completed is bool(expected.get("completed", True))

        for dotted, value in expected.get("outputs", {}).items():
            assert _lookup_output(result, dotted) == value

        for dotted, upper in expected.get("numeric_upper_bounds", {}).items():
            assert float(_lookup_output(result, dotted)) <= float(upper)

        for dotted, enclosure in expected.get("interval_contains", {}).items():
            actual = _lookup_output(result, dotted)
            assert float(actual[0]) <= float(enclosure[0])
            assert float(actual[1]) >= float(enclosure[1])

        seen.update(node.module_id for node in exp.nodes)

    assert seen == EXPECTED_INITIAL_UI


def test_compatible_targets_are_backed_by_typed_port_contracts():
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)

    for module_id in capabilities.module_ids("link"):
        for target in capabilities.compatible_targets(module_id):
            assert capabilities.connection_error(
                module_id,
                target["source_port"],
                target["target_module_id"],
                target["target_port"],
            ) is None



def test_type_compatible_but_untested_connection_is_not_offered():
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)

    # Both ports are arrays, but this edge is not part of a qualified workflow.
    reason = capabilities.connection_error(
        "science.grid1d",
        "x",
        "verify.constant_residual",
        "values",
    )
    assert reason == "connection path is not qualified by a tested workflow"
    offered = capabilities.compatible_targets("science.grid1d")
    assert not any(
        item["target_module_id"] == "verify.constant_residual"
        and item["target_port"] == "values"
        for item in offered
    )

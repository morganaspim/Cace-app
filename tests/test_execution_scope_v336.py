from dataclasses import replace

import pytest

from cace_studio.core.executor import GraphExecutor
from cace_studio.core.execution_scope import build_upstream_subgraph
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.report import run_report
from cace_studio.core.types import Maturity, ModuleMetadata, PortSpec


class Const(Module):
    metadata = ModuleMetadata(
        "test.scope.const",
        "Scope Const",
        "1.0.0",
        "Tests",
        "Constant source for execution-scope tests.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("x", "number"),)

    def execute(self, inputs, params, ctx):
        return {"x": 2.0}


class Double(Module):
    metadata = ModuleMetadata(
        "test.scope.double",
        "Scope Double",
        "1.0.0",
        "Tests",
        "Double an upstream value.",
        Maturity.EXPERIMENTAL,
    )
    inputs = (PortSpec("x", "number"),)
    outputs = (PortSpec("y", "number"),)

    def execute(self, inputs, params, ctx):
        return {"y": 2.0 * inputs["x"]}


def registry():
    result = ModuleRegistry()
    result.register(Const)
    result.register(Double)
    return result


def experiment():
    return Experiment(
        name="scope-test",
        nodes=[
            Node("a", Const.metadata.module_id, {"nested": {"v": 1}}, (0.0, 0.0)),
            Node("b", Double.metadata.module_id, {}, (100.0, 0.0)),
            Node("c", Double.metadata.module_id, {}, (200.0, 0.0)),
            Node("unrelated", Const.metadata.module_id, {}, (0.0, 200.0)),
        ],
        edges=[
            Edge("a", "x", "b", "x"),
            Edge("b", "y", "c", "x"),
        ],
        metadata={"purpose": "scope-test"},
    )


def test_upstream_scope_excludes_unrelated_nodes_and_is_deep_copied():
    source = experiment()
    scoped, scope = build_upstream_subgraph(source, ["c"])

    assert [node.id for node in scoped.nodes] == ["a", "b", "c"]
    assert [(edge.source_node, edge.target_node) for edge in scoped.edges] == [
        ("a", "b"),
        ("b", "c"),
    ]
    assert scope.kind == "selected-upstream"
    assert scope.target_node_ids == ("c",)
    assert scope.included_node_ids == ("a", "b", "c")
    assert len(scope.scope_sha256) == 64
    assert scope.source_semantic_experiment_sha256 != scope.execution_semantic_experiment_sha256

    scoped.nodes[0].params["nested"]["v"] = 99
    assert source.nodes[0].params["nested"]["v"] == 1


def test_upstream_scope_rejects_unknown_or_empty_targets():
    with pytest.raises(ValueError, match="at least one"):
        build_upstream_subgraph(experiment(), [])
    with pytest.raises(ValueError, match="unknown target"):
        build_upstream_subgraph(experiment(), ["missing"])


def test_selected_upstream_execution_is_bound_to_source_and_scope_identity():
    source = experiment()
    result = GraphExecutor(registry()).run_selected_upstream(source, ["c"], seed=7)

    assert tuple(result.outputs) == ("a", "b", "c")
    assert result.outputs["c"]["y"] == 8.0
    assert result.run_scope == "selected-upstream"
    assert result.scope_target_node_ids == ("c",)
    assert result.scope_included_node_ids == ("a", "b", "c")
    assert result.seed == 7
    assert result.source_semantic_experiment_sha256 != result.semantic_experiment_sha256
    assert len(result.execution_scope_sha256) == 64

    report = run_report(result, source.name)
    assert report["report_schema"] == 4
    assert report["run_scope"] == "selected-upstream"
    assert report["scope_target_node_ids"] == ["c"]
    assert report["scope_included_node_ids"] == ["a", "b", "c"]
    assert report["source_semantic_experiment_sha256"] == result.source_semantic_experiment_sha256
    assert report["semantic_experiment_sha256"] == result.semantic_experiment_sha256
    assert report["execution_scope_sha256"] == result.execution_scope_sha256
    assert report["graph_certificate"]["execution_scope_sha256"] == result.execution_scope_sha256


def test_executor_rejects_tampered_scope_before_running():
    scoped, scope = build_upstream_subgraph(experiment(), ["c"])
    tampered = replace(scope, execution_semantic_experiment_sha256="0" * 64)
    with pytest.raises(ValidationError, match="semantic graph hash"):
        GraphExecutor(registry()).run(scoped, execution_scope=tampered)


def test_full_run_scope_binds_source_and_execution_to_same_graph():
    source = experiment()
    result = GraphExecutor(registry()).run(source)
    assert result.run_scope == "full"
    assert result.scope_target_node_ids == ()
    assert result.scope_included_node_ids == ("a", "b", "c", "unrelated")
    assert result.source_semantic_experiment_sha256 == result.semantic_experiment_sha256
    assert result.source_full_experiment_sha256 == result.full_experiment_sha256
    assert len(result.execution_scope_sha256) == 64

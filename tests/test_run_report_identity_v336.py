from __future__ import annotations

from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Experiment, Node
from cace_studio.core.module import Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.report import REPORT_SCHEMA, graph_certificate, run_report
from cace_studio.core.reproducibility import experiment_fingerprint
from cace_studio.core.types import Maturity, ModuleMetadata, ParameterSpec, PortSpec


class _IdentityModule(Module):
    metadata = ModuleMetadata(
        "test.run-identity",
        "Run Identity",
        "1.0.0",
        "Test",
        "Deterministic module used to test run/report graph binding.",
        Maturity.EXPERIMENTAL,
    )
    parameters = (ParameterSpec("value", "number", 1.0),)
    outputs = (PortSpec("value", "number"),)

    def execute(self, inputs, params, ctx):
        return {"value": float(params["value"])}


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.register(_IdentityModule)
    return registry


def _experiment(value: float) -> Experiment:
    return Experiment(
        name="identity-test",
        nodes=[Node("n1", "test.run-identity", {"value": value}, (10.0, 20.0))],
    )


def test_executor_binds_run_result_to_exact_experiment_fingerprints():
    exp = _experiment(2.0)
    result = GraphExecutor(_registry()).run(exp, seed=17)

    assert result.experiment_name == "identity-test"
    assert result.semantic_experiment_sha256 == experiment_fingerprint(exp, include_layout=False)
    assert result.full_experiment_sha256 == experiment_fingerprint(exp, include_layout=True)
    assert result.seed == 17
    assert result.run_scope == "full"


def test_current_report_schema_surfaces_executor_recorded_identity():
    exp = _experiment(2.0)
    result = GraphExecutor(_registry()).run(exp, seed=3, run_scope="full")
    report = run_report(result, "caller-supplied-wrong-name")

    assert report["report_schema"] == REPORT_SCHEMA
    assert report["experiment"] == "identity-test"
    assert report["semantic_experiment_sha256"] == result.semantic_experiment_sha256
    assert report["full_experiment_sha256"] == result.full_experiment_sha256
    assert report["seed"] == 3
    assert report["run_scope"] == "full"

    certificate = report["graph_certificate"]
    assert certificate["semantic_experiment_sha256"] == result.semantic_experiment_sha256
    assert certificate["full_experiment_sha256"] == result.full_experiment_sha256
    assert certificate["seed"] == 3
    assert certificate["run_scope"] == "full"


def test_semantic_graph_change_changes_report_certificate_identity():
    left = GraphExecutor(_registry()).run(_experiment(1.0))
    right = GraphExecutor(_registry()).run(_experiment(2.0))

    assert left.semantic_experiment_sha256 != right.semantic_experiment_sha256
    assert graph_certificate(left)["certificate_hash"] != graph_certificate(right)["certificate_hash"]


def test_layout_only_change_preserves_semantic_but_changes_full_identity():
    first = _experiment(1.0)
    second = _experiment(1.0)
    second.nodes[0].position = (500.0, 700.0)

    left = GraphExecutor(_registry()).run(first)
    right = GraphExecutor(_registry()).run(second)

    assert left.semantic_experiment_sha256 == right.semantic_experiment_sha256
    assert left.full_experiment_sha256 != right.full_experiment_sha256
    assert graph_certificate(left)["certificate_hash"] != graph_certificate(right)["certificate_hash"]

from __future__ import annotations

from cace_studio.core.execution_control import ExecutionControl, ExecutionLimits
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.module import Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.types import Maturity, ModuleMetadata, PortSpec


class LimitSource(Module):
    metadata = ModuleMetadata(
        "test.limit.source",
        "Limit Source",
        "1.0.0",
        "Tests",
        "Source for bounded execution tests.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("x", "number"),)

    def execute(self, inputs, params, ctx):
        return {"x": 1.0}


class LimitMiddle(Module):
    metadata = ModuleMetadata(
        "test.limit.middle",
        "Limit Middle",
        "1.0.0",
        "Tests",
        "Middle node for bounded execution tests.",
        Maturity.EXPERIMENTAL,
    )
    inputs = (PortSpec("x", "number"),)
    outputs = (PortSpec("y", "number"),)

    def execute(self, inputs, params, ctx):
        return {"y": inputs["x"] + 1.0}


class LargeOutput(Module):
    metadata = ModuleMetadata(
        "test.limit.large-output",
        "Large Output",
        "1.0.0",
        "Tests",
        "Produces output large enough to hit byte budget.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("payload", "object"),)

    def execute(self, inputs, params, ctx):
        return {"payload": "x" * 4096}


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.register(LimitSource)
    registry.register(LimitMiddle)
    registry.register(LargeOutput)
    return registry


def test_node_budget_stops_before_next_node_not_at_exact_limit() -> None:
    exp = Experiment(
        name="node-budget",
        nodes=[
            Node("a", LimitSource.metadata.module_id),
            Node("b", LimitMiddle.metadata.module_id),
        ],
        edges=[Edge("a", "x", "b", "x")],
    )
    control = ExecutionControl(limits=ExecutionLimits(max_nodes=1))
    result = GraphExecutor(_registry()).run(exp, control=control)

    assert result.completed is False
    assert result.interruption_reason == "node-budget-before-node:b"
    assert tuple(result.outputs) == ("a",)
    assert control.nodes_completed == 1


def test_exact_node_budget_allows_one_node_experiment_to_complete() -> None:
    exp = Experiment(
        name="one-node",
        nodes=[Node("a", LimitSource.metadata.module_id)],
    )
    control = ExecutionControl(limits=ExecutionLimits(max_nodes=1))
    result = GraphExecutor(_registry()).run(exp, control=control)

    assert result.completed is True
    assert result.interruption_reason == ""
    assert tuple(result.outputs) == ("a",)
    assert control.nodes_completed == 1


def test_output_byte_budget_interrupts_after_large_node() -> None:
    exp = Experiment(
        name="output-budget",
        nodes=[Node("large", LargeOutput.metadata.module_id)],
    )
    control = ExecutionControl(limits=ExecutionLimits(max_output_bytes=128))
    result = GraphExecutor(_registry()).run(exp, control=control)

    assert result.completed is False
    assert result.interruption_reason == "output-byte-budget-after-node:large"
    assert "large" in result.outputs
    assert control.output_bytes > 128


def test_wall_time_budget_stops_at_next_module_boundary() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    control = ExecutionControl(
        limits=ExecutionLimits(max_wall_seconds=1.0),
        clock=clock,
    )
    assert control.wait_until_runnable() is True
    now[0] = 1.1
    assert control.wait_until_runnable() is False
    assert control.stop_reason == "wall-time-budget"


def test_external_cancel_state_is_observed_at_checkpoint() -> None:
    state = ["running"]
    control = ExecutionControl(
        external_state_provider=lambda: state[0],
        limits=ExecutionLimits(poll_seconds=0.01),
    )
    assert control.wait_until_runnable() is True
    state[0] = "cancelled"
    assert control.wait_until_runnable() is False
    assert control.stop_reason == "externally-cancelled"

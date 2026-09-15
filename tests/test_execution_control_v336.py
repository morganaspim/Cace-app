from threading import Event, Thread

from cace_studio.core.execution_control import ExecutionControl
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.module import Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.report import run_report
from cace_studio.core.types import Maturity, ModuleMetadata, PortSpec


class CancellingSource(Module):
    metadata = ModuleMetadata(
        "test.control.source",
        "Cancelling Source",
        "1.0.0",
        "Tests",
        "Source that requests cooperative cancellation during execution.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("x", "number"),)
    control: ExecutionControl | None = None

    def execute(self, inputs, params, ctx):
        if self.control is not None:
            self.control.cancel()
        return {"x": 3.0}


class Downstream(Module):
    metadata = ModuleMetadata(
        "test.control.downstream",
        "Downstream",
        "1.0.0",
        "Tests",
        "Should not execute after cooperative cancellation.",
        Maturity.EXPERIMENTAL,
    )
    inputs = (PortSpec("x", "number"),)
    outputs = (PortSpec("y", "number"),)

    def execute(self, inputs, params, ctx):
        return {"y": inputs["x"] + 1.0}


def _registry():
    registry = ModuleRegistry()
    registry.register(CancellingSource)
    registry.register(Downstream)
    return registry


def _experiment():
    return Experiment(
        name="control-test",
        nodes=[
            Node("source", CancellingSource.metadata.module_id),
            Node("downstream", Downstream.metadata.module_id),
        ],
        edges=[Edge("source", "x", "downstream", "x")],
    )


def test_pause_blocks_checkpoint_until_resume():
    control = ExecutionControl()
    assert control.pause() is True
    done = Event()
    result = []

    def wait():
        result.append(control.wait_until_runnable())
        done.set()

    thread = Thread(target=wait, daemon=True)
    thread.start()
    assert done.wait(0.05) is False
    assert control.resume() is True
    assert done.wait(1.0) is True
    thread.join(timeout=1.0)
    assert result == [True]


def test_cancel_wakes_paused_checkpoint_and_is_idempotent():
    control = ExecutionControl()
    control.pause()
    done = Event()
    result = []

    def wait():
        result.append(control.wait_until_runnable())
        done.set()

    thread = Thread(target=wait, daemon=True)
    thread.start()
    assert control.cancel() is True
    assert control.cancel() is False
    assert done.wait(1.0) is True
    thread.join(timeout=1.0)
    assert result == [False]
    assert control.cancelled is True
    assert control.paused is False
    assert control.resume() is False


def test_pre_cancelled_run_is_incomplete_and_executes_nothing():
    control = ExecutionControl()
    control.cancel()
    result = GraphExecutor(_registry()).run(_experiment(), control=control)

    assert result.completed is False
    assert result.interruption_reason == "cancelled-before-node:source"
    assert result.outputs == {}
    assert result.certificates == []
    assert result.all_verifiers_passed is False

    report = run_report(result, "control-test")
    assert report["completed"] is False
    assert report["interruption_reason"] == "cancelled-before-node:source"
    assert report["graph_certificate"]["completed"] is False


def test_cancellation_during_module_stops_before_downstream_node():
    control = ExecutionControl()
    CancellingSource.control = control
    try:
        result = GraphExecutor(_registry()).run(_experiment(), control=control)
    finally:
        CancellingSource.control = None

    assert result.completed is False
    assert result.interruption_reason == "cancelled-after-node:source"
    assert tuple(result.outputs) == ("source",)
    assert [certificate.node_id for certificate in result.certificates] == ["source"]
    assert "downstream" not in result.verification
    assert result.all_verifiers_passed is False

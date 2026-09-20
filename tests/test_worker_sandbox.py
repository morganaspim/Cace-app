from __future__ import annotations

import os

import pytest

from cace_studio.app import build_registry
from cace_studio.agent_runtime import (
    AutonomyLoopBudget,
    CapabilityPolicy,
    FileAgentLeaseManager,
    FileAutonomySessionStore,
    FileCanvasPlanStore,
    FileCanvasPreviewStore,
    FileExperimentWorkspace,
    FileOperationStore,
    FileRunArtifactStore,
    FileRunControlStore,
    FileWorkerReceiptStore,
    ProcessSandboxLimits,
    ProcessScienceRunner,
    ScienceWorkerError,
    ScienceWorkerTerminatedError,
    ToolBus,
    ToolCall,
    ToolStatus,
    autonomy_cycle_approval_callback,
    operation_id_for,
    register_autonomy_loop_tools,
    register_canvas_mutation_tools,
    register_canvas_plan_tools,
)
from cace_studio.core.graph import Experiment, Node
from cace_studio.core.registry import ModuleRegistry
from cace_studio.modules.builtin import Constant


def _experiment() -> Experiment:
    return Experiment(
        name="sandbox",
        nodes=[
            Node(
                id="constant",
                module_id="core.constant",
                params={"value": 7.0},
            )
        ],
    )


def _runner(tmp_path, *, registry=None) -> ProcessScienceRunner:
    return ProcessScienceRunner(
        registry=registry or build_registry(),
        control_store=FileRunControlStore(tmp_path / "controls"),
        receipt_store=FileWorkerReceiptStore(tmp_path / "receipts"),
        poll_seconds=0.01,
        terminate_grace_seconds=0.05,
    )


def test_process_science_runner_executes_canonical_registry_in_child(tmp_path) -> None:
    runner = _runner(tmp_path)
    outcome = runner.run(
        experiment=_experiment(),
        target_node_ids=(),
        external_inputs={},
        seed=17,
        gpu_enabled=False,
        control_id="sandbox-success",
        limits=ProcessSandboxLimits(
            max_wall_seconds=30.0,
            max_cpu_seconds=20.0,
            max_memory_bytes=3_221_225_472,
            max_nodes=10,
            max_output_bytes=1_000_000,
        ),
        worker_nonce="success",
    )

    assert outcome.result.completed is True
    assert outcome.result.outputs["constant"]["value"] == 7.0
    assert outcome.receipt.outcome == "completed"
    assert outcome.receipt.result_sha256
    assert outcome.receipt.registry_sha256
    assert outcome.receipt.resource_enforcement["parent_wall_deadline"] is True
    assert outcome.receipt.resource_enforcement["parent_hard_cancel"] is True
    assert outcome.receipt.resource_enforcement["network_isolation"] == (
        "not-hard-enforced"
    )
    if os.name == "posix":
        assert outcome.receipt.resource_enforcement["memory_limit"]["kind"] == (
            "RLIMIT_AS"
        )
        assert outcome.receipt.resource_enforcement["cpu_limit"]["kind"] == (
            "RLIMIT_CPU"
        )

    stored = runner.receipt_store.load(outcome.receipt.worker_id)
    assert stored is not None
    assert stored.to_dict() == outcome.receipt.to_dict()


def test_parent_hard_wall_deadline_terminates_worker_process(tmp_path) -> None:
    runner = _runner(tmp_path)
    with pytest.raises(ScienceWorkerTerminatedError) as exc_info:
        runner.run(
            experiment=_experiment(),
            target_node_ids=(),
            external_inputs={},
            seed=0,
            gpu_enabled=False,
            control_id="sandbox-timeout",
            limits=ProcessSandboxLimits(
                max_wall_seconds=0.001,
                max_cpu_seconds=20.0,
                max_memory_bytes=3_221_225_472,
                max_nodes=10,
                max_output_bytes=1_000_000,
            ),
            worker_nonce="timeout",
        )

    receipt = exc_info.value.receipt
    assert receipt.outcome == "terminated"
    assert receipt.termination_reason == "hard-wall-deadline"
    assert runner.receipt_store.load(receipt.worker_id) is not None


def test_worker_rejects_registry_contract_mismatch(tmp_path) -> None:
    registry = ModuleRegistry()
    registry.register(Constant)
    runner = _runner(tmp_path, registry=registry)

    with pytest.raises(ScienceWorkerError, match="registry contract mismatch"):
        runner.run(
            experiment=_experiment(),
            target_node_ids=(),
            external_inputs={},
            seed=0,
            gpu_enabled=False,
            control_id="sandbox-registry-mismatch",
            limits=ProcessSandboxLimits(
                max_wall_seconds=30.0,
                max_cpu_seconds=20.0,
                max_memory_bytes=3_221_225_472,
                max_nodes=10,
                max_output_bytes=1_000_000,
            ),
            worker_nonce="registry-mismatch",
        )


def test_autonomy_cycle_uses_process_sandbox_and_returns_worker_receipt(tmp_path) -> None:
    registry = build_registry()
    experiment = _experiment()
    previews = FileCanvasPreviewStore(tmp_path / "previews")
    plans = FileCanvasPlanStore(tmp_path / "plans")
    workspace = FileExperimentWorkspace(tmp_path / "workspace", workspace_id="main")
    sessions = FileAutonomySessionStore(tmp_path / "sessions")
    artifacts = FileRunArtifactStore(tmp_path / "artifacts")
    controls = FileRunControlStore(tmp_path / "controls")
    worker_receipts = FileWorkerReceiptStore(tmp_path / "worker-receipts")
    operations = FileOperationStore(tmp_path / "operations")
    leases = FileAgentLeaseManager(tmp_path / "leases")

    bus = ToolBus(
        policy=CapabilityPolicy.zero_contact(),
        operation_store=operations,
        lease_validator=lambda call: leases.assert_current(
            call.run_id,
            call.lease_id,
            call.lease_generation,
        ),
    )
    canvas = register_canvas_mutation_tools(
        bus,
        registry=registry,
        active_experiment=experiment,
        preview_store=previews,
        workspace_store=workspace,
    )
    plan_runtime = register_canvas_plan_tools(
        bus,
        canvas_runtime=canvas,
        registry=registry,
        preview_store=previews,
        plan_store=plans,
        workspace_store=workspace,
    )
    process_runner = ProcessScienceRunner(
        registry=registry,
        control_store=controls,
        receipt_store=worker_receipts,
        poll_seconds=0.01,
        terminate_grace_seconds=0.05,
    )
    autonomy = register_autonomy_loop_tools(
        bus,
        registry=registry,
        plan_runtime=plan_runtime,
        plan_store=plans,
        workspace_store=workspace,
        session_store=sessions,
        run_artifact_store=artifacts,
        run_control_store=controls,
        process_science_runner=process_runner,
    )
    bus.approval_callback = autonomy_cycle_approval_callback(
        sessions,
        plans,
        lambda _payload: True,
    )

    preview = bus.invoke(
        ToolCall(
            "sandbox-plan-preview",
            "cace.canvas.preview_plan",
            {
                "steps": [
                    {
                        "step_id": "move",
                        "operations": [
                            {
                                "action": "move_node",
                                "node_id": "constant",
                                "position": [2.0, 3.0],
                            }
                        ],
                    }
                ]
            },
        )
    )
    assert preview.status is ToolStatus.OK
    session = autonomy.create_session(
        initial_plan_id=preview.output["plan_id"],
        session_id="sandbox-autonomy",
        budget=AutonomyLoopBudget(
            max_cycles=1,
            max_science_runs=1,
            max_replans=0,
            max_plan_steps_per_cycle=5,
            max_wall_seconds_per_run=30.0,
            max_nodes_per_run=10,
            max_output_bytes_per_run=1_000_000,
            max_artifact_bytes_per_run=10_000_000,
            max_cpu_seconds_per_run=20.0,
            max_memory_bytes_per_run=3_221_225_472,
        ),
    )
    lease = leases.acquire("sandbox-autonomy-run", "owner-a", ttl_seconds=60.0)
    arguments = {
        "session_id": session.session_id,
        "plan_id": preview.output["plan_id"],
    }
    result = bus.invoke(
        ToolCall(
            "sandbox-autonomy-run:1",
            "cace.autonomy.advance",
            arguments,
            run_id="sandbox-autonomy-run",
            operation_id=operation_id_for(
                run_id="sandbox-autonomy-run",
                ordinal=1,
                tool_name="cace.autonomy.advance",
                arguments=arguments,
            ),
            lease_id=lease.lease_id,
            lease_generation=lease.generation,
        )
    )

    assert result.status is ToolStatus.OK
    assert result.output["worker_receipt_id"]
    assert result.output["run_artifact_id"]
    worker = worker_receipts.load(result.output["worker_receipt_id"])
    assert worker is not None
    assert worker.outcome == "completed"
    assert worker.registry_sha256

    inspected_worker = bus.invoke(
        ToolCall(
            "inspect-worker",
            "cace.autonomy.inspect_worker_receipt",
            {"worker_receipt_id": result.output["worker_receipt_id"]},
        )
    )
    assert inspected_worker.status is ToolStatus.OK
    assert inspected_worker.output["receipt"]["worker_id"] == worker.worker_id
    assert inspected_worker.output["receipt"]["proof_effect"] == "none"

    artifact = artifacts.load(result.output["run_artifact_id"])
    assert artifact is not None
    assert artifact["run_id"] == result.output["science_run_id"]

from __future__ import annotations

from cace_studio.agent_runtime import (
    AutonomyLoopBudget,
    CapabilityPolicy,
    FileAgentLeaseManager,
    FileAutonomySessionStore,
    FileCanvasPlanStore,
    FileCanvasPreviewStore,
    FileExperimentWorkspace,
    FileOperationStore,
    FileRecoveryInbox,
    FileRunArtifactStore,
    FileRunControlStore,
    RunControlState,
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
from cace_studio.core.module import Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.types import Maturity, ModuleMetadata, PortSpec


class ContainedSource(Module):
    metadata = ModuleMetadata(
        "test.contained.source",
        "Contained Source",
        "1.0.0",
        "Tests",
        "Source for autonomous containment tests.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("x", "number"),)
    executions = 0

    def execute(self, inputs, params, ctx):
        type(self).executions += 1
        return {"x": 1.0}


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.register(ContainedSource)
    return registry


def _setup(tmp_path):
    ContainedSource.executions = 0
    registry = _registry()
    experiment = Experiment(
        name="contained",
        nodes=[Node("source", ContainedSource.metadata.module_id)],
    )
    previews = FileCanvasPreviewStore(tmp_path / "previews")
    plans = FileCanvasPlanStore(tmp_path / "plans")
    workspace = FileExperimentWorkspace(tmp_path / "workspace", workspace_id="main")
    sessions = FileAutonomySessionStore(tmp_path / "sessions")
    artifacts = FileRunArtifactStore(tmp_path / "artifacts")
    controls = FileRunControlStore(tmp_path / "controls")
    inbox = FileRecoveryInbox(tmp_path / "inbox")
    leases = FileAgentLeaseManager(tmp_path / "leases")
    operations = FileOperationStore(tmp_path / "operations")
    approvals = []

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
    autonomy = register_autonomy_loop_tools(
        bus,
        registry=registry,
        plan_runtime=plan_runtime,
        plan_store=plans,
        workspace_store=workspace,
        session_store=sessions,
        run_artifact_store=artifacts,
        run_control_store=controls,
        recovery_inbox=inbox,
    )
    bus.approval_callback = autonomy_cycle_approval_callback(
        sessions,
        plans,
        lambda payload: (approvals.append(dict(payload)), True)[1],
    )

    plan_preview = bus.invoke(
        ToolCall(
            "plan-preview",
            "cace.canvas.preview_plan",
            {
                "steps": [
                    {
                        "step_id": "move-source",
                        "operations": [
                            {
                                "action": "move_node",
                                "node_id": "source",
                                "position": [1.0, 1.0],
                            }
                        ],
                    }
                ]
            },
        )
    )
    assert plan_preview.status is ToolStatus.OK
    return {
        "bus": bus,
        "autonomy": autonomy,
        "experiment": experiment,
        "plans": plans,
        "workspace": workspace,
        "sessions": sessions,
        "artifacts": artifacts,
        "controls": controls,
        "inbox": inbox,
        "leases": leases,
        "operations": operations,
        "approvals": approvals,
        "plan_id": plan_preview.output["plan_id"],
    }


def _advance_call(env, *, run_id="contained-run"):
    session = env["sessions"].load("contained-session")
    lease = env["leases"].acquire(run_id, "owner-a", ttl_seconds=60.0)
    args = {"session_id": session.session_id, "plan_id": session.pending_plan_id}
    return ToolCall(
        f"{run_id}:1",
        "cace.autonomy.advance",
        args,
        run_id=run_id,
        operation_id=operation_id_for(
            run_id=run_id,
            ordinal=1,
            tool_name="cace.autonomy.advance",
            arguments=args,
        ),
        lease_id=lease.lease_id,
        lease_generation=lease.generation,
    )


def test_completed_cycle_persists_content_addressed_run_artifact(tmp_path) -> None:
    env = _setup(tmp_path)
    session = env["autonomy"].create_session(
        initial_plan_id=env["plan_id"],
        session_id="contained-session",
        budget=AutonomyLoopBudget(
            max_cycles=1,
            max_science_runs=1,
            max_replans=0,
            max_plan_steps_per_cycle=5,
            max_wall_seconds_per_run=10.0,
            max_nodes_per_run=10,
            max_output_bytes_per_run=4096,
            max_artifact_bytes_per_run=1_000_000,
        ),
    )
    call = _advance_call(env)
    result = env["bus"].invoke(call)

    assert result.status is ToolStatus.OK
    assert result.output["run_control_id"]
    assert result.output["run_artifact_id"]
    artifact = env["artifacts"].load(result.output["run_artifact_id"])
    assert artifact is not None
    assert artifact["session_id"] == session.session_id
    assert artifact["cycle_index"] == 1
    assert artifact["run_id"] == result.output["science_run_id"]
    assert artifact["report"]["completed"] is True
    assert artifact["perception"]["evidence_authority"] is False
    assert artifact["proof_effect"] == "none"
    assert artifact["promotion_authority"] is False
    assert ContainedSource.executions == 1


def test_pre_cancelled_cycle_persists_partial_artifact_and_attention_item(tmp_path) -> None:
    env = _setup(tmp_path)
    session = env["autonomy"].create_session(
        initial_plan_id=env["plan_id"],
        session_id="contained-session",
        budget=AutonomyLoopBudget(
            max_cycles=1,
            max_science_runs=1,
            max_replans=0,
            max_plan_steps_per_cycle=5,
            max_wall_seconds_per_run=10.0,
            max_nodes_per_run=10,
            max_output_bytes_per_run=4096,
            max_artifact_bytes_per_run=1_000_000,
        ),
    )
    control_id = env["autonomy"].cancel_session(session.session_id)
    call = _advance_call(env, run_id="cancelled-run")

    first = env["bus"].invoke(call)
    assert first.status is ToolStatus.RECOVERY_BLOCKED
    assert "externally-cancelled-before-node:source" in first.error
    assert ContainedSource.executions == 0

    items = env["inbox"].list_open(session_id=session.session_id)
    assert len(items) == 1
    item = items[0]
    assert item.operation_id == call.operation_id
    assert item.category == "science-run-interrupted"
    assert item.run_artifact_id

    artifact = env["artifacts"].load(item.run_artifact_id)
    assert artifact is not None
    assert artifact["report"]["completed"] is False

    listed = env["bus"].invoke(
        ToolCall(
            "attention-list",
            "cace.autonomy.list_attention",
            {"session_id": session.session_id},
        )
    )
    assert listed.status is ToolStatus.OK
    assert listed.output["items"][0]["item_id"] == item.item_id

    retry = ToolCall(
        "cancelled-retry",
        call.tool_name,
        dict(call.arguments),
        run_id=call.run_id,
        operation_id=call.operation_id,
        lease_id=call.lease_id,
        lease_generation=call.lease_generation,
    )
    second = env["bus"].invoke(retry)
    assert second.status is ToolStatus.RECOVERY_BLOCKED
    assert ContainedSource.executions == 0

    env["controls"].set_state(control_id, RunControlState.RUNNING)
    resolved = env["inbox"].resolve(item.item_id)
    assert resolved.resolved is True
    assert env["inbox"].list_open(session_id=session.session_id) == ()


def test_output_budget_interrupt_is_durable_and_recovery_blocked(tmp_path) -> None:
    env = _setup(tmp_path)
    env["autonomy"].create_session(
        initial_plan_id=env["plan_id"],
        session_id="contained-session",
        budget=AutonomyLoopBudget(
            max_cycles=1,
            max_science_runs=1,
            max_replans=0,
            max_plan_steps_per_cycle=5,
            max_wall_seconds_per_run=10.0,
            max_nodes_per_run=10,
            max_output_bytes_per_run=1,
            max_artifact_bytes_per_run=1_000_000,
        ),
    )
    call = _advance_call(env, run_id="output-budget-run")
    result = env["bus"].invoke(call)

    assert result.status is ToolStatus.RECOVERY_BLOCKED
    assert "output-byte-budget-after-node:source" in result.error
    assert ContainedSource.executions == 1
    item = env["inbox"].find_open_by_operation(call.operation_id)
    assert item is not None
    artifact = env["artifacts"].load(item.run_artifact_id)
    assert artifact is not None
    assert artifact["report"]["completed"] is False

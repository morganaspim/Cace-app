from __future__ import annotations

from cace_studio.agent_runtime import (
    CapabilityPolicy,
    CanvasCommitRequest,
    CanvasPlanExecuteRequest,
    FileAgentLeaseManager,
    FileCanvasPlanStore,
    FileCanvasPreviewStore,
    FileExperimentWorkspace,
    FileOperationStore,
    ToolBus,
    ToolCall,
    ToolContext,
    ToolStatus,
    canvas_plan_approval_callback,
    operation_id_for,
    register_canvas_mutation_tools,
    register_canvas_plan_tools,
)
from cace_studio.core.graph import Experiment, Node
from cace_studio.core.module import ExecutionContext, Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.reproducibility import experiment_fingerprint, sha256_identity
from cace_studio.core.types import Maturity, ModuleMetadata, PortSpec


class PlanSource(Module):
    metadata = ModuleMetadata(
        module_id="plan.source",
        name="Plan Source",
        version="1",
        category="test",
        description="Plan source.",
        maturity=Maturity.PROTOTYPE,
    )
    outputs = (PortSpec("y", "scalar"),)

    def execute(self, inputs, params, ctx: ExecutionContext):
        return {"y": 1.0}


class PlanSink(Module):
    metadata = ModuleMetadata(
        module_id="plan.sink",
        name="Plan Sink",
        version="1",
        category="test",
        description="Plan sink.",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "scalar"),)

    def execute(self, inputs, params, ctx: ExecutionContext):
        return {}


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.register(PlanSource)
    registry.register(PlanSink)
    return registry


def _setup(tmp_path, *, approve=True):
    registry = _registry()
    experiment = Experiment(
        name="plan",
        nodes=[Node("src", "plan.source", position=(0.0, 0.0))],
    )
    previews = FileCanvasPreviewStore(tmp_path / "previews")
    plans = FileCanvasPlanStore(tmp_path / "plans")
    workspace = FileExperimentWorkspace(tmp_path / "workspace", workspace_id="main")
    leases = FileAgentLeaseManager(tmp_path / "leases")
    operations = FileOperationStore(tmp_path / "operations")
    approvals: list[dict] = []

    def decide(payload):
        approvals.append(dict(payload))
        return approve

    bus = ToolBus(
        policy=CapabilityPolicy.zero_contact(),
        approval_callback=canvas_plan_approval_callback(plans, decide),
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
    return (
        bus,
        canvas,
        plan_runtime,
        experiment,
        previews,
        plans,
        workspace,
        leases,
        operations,
        approvals,
    )


def _plan_preview(bus: ToolBus):
    return bus.invoke(
        ToolCall(
            "plan-preview",
            "cace.canvas.preview_plan",
            {
                "steps": [
                    {
                        "step_id": "wire",
                        "depends_on": ["add-sink"],
                        "operations": [
                            {
                                "action": "add_edge",
                                "source_node": "src",
                                "source_port": "y",
                                "target_node": "sink",
                                "target_port": "x",
                            }
                        ],
                    },
                    {
                        "step_id": "add-sink",
                        "operations": [
                            {
                                "action": "add_node",
                                "node_id": "sink",
                                "module_id": "plan.sink",
                                "position": [2.0, 3.0],
                            }
                        ],
                    },
                ]
            },
        )
    )


def _execute_call(plan_id: str, *, run_id: str, ordinal: int, lease):
    arguments = {"plan_id": plan_id}
    return ToolCall(
        f"{run_id}:{ordinal}",
        "cace.canvas.execute_plan",
        arguments,
        run_id=run_id,
        operation_id=operation_id_for(
            run_id=run_id,
            ordinal=ordinal,
            tool_name="cace.canvas.execute_plan",
            arguments=arguments,
        ),
        lease_id=lease.lease_id,
        lease_generation=lease.generation,
    )


def test_plan_preview_is_non_mutating_deterministic_and_dependency_aware(tmp_path) -> None:
    (
        bus,
        _canvas,
        _runtime,
        experiment,
        _previews,
        plans,
        workspace,
        _leases,
        _operations,
        _approvals,
    ) = _setup(tmp_path)

    before = experiment_fingerprint(experiment, include_layout=True)
    result = _plan_preview(bus)
    assert result.status is ToolStatus.OK
    assert result.output["ordered_step_ids"] == ["add-sink", "wire"]
    assert result.output["step_count"] == 2
    assert result.output["base_workspace_version"] == 0
    assert result.output["target_workspace_version"] == 2
    assert experiment_fingerprint(experiment, include_layout=True) == before

    record = plans.load(result.output["plan_id"])
    assert record is not None
    assert tuple(step.step_id for step in record.ordered_steps) == (
        "add-sink",
        "wire",
    )
    estimate = result.output["dependency_estimate"]
    assert estimate["execution_node_order"] == ["src", "sink"]
    assert estimate["execution_module_order"] == ["plan.source", "plan.sink"]
    assert "not executed verification evidence" in estimate["proof_metadata_note"]

    persisted, persisted_experiment = workspace.load()
    assert persisted.version == 0
    assert len(persisted_experiment.nodes) == 1


def test_plan_executes_with_one_approval_and_per_step_workspace_receipts(tmp_path) -> None:
    (
        bus,
        _canvas,
        _runtime,
        experiment,
        _previews,
        plans,
        workspace,
        leases,
        operations,
        approvals,
    ) = _setup(tmp_path)
    preview = _plan_preview(bus)
    plan_id = preview.output["plan_id"]
    lease = leases.acquire("plan-run", "owner-a", ttl_seconds=60.0)

    call = _execute_call(plan_id, run_id="plan-run", ordinal=1, lease=lease)
    result = bus.invoke(call)
    assert result.status is ToolStatus.OK
    assert approvals and len(approvals) == 1
    assert approvals[0]["plan_id"] == plan_id
    assert [step["step_id"] for step in approvals[0]["ordered_steps"]] == [
        "add-sink",
        "wire",
    ]
    assert result.output["completed_steps"] == ["add-sink", "wire"]
    assert len(result.output["child_operation_ids"]) == 2
    assert result.output["final_workspace_version"] == 2
    assert result.output["semantic_hash_verified"] is True
    assert result.output["full_hash_verified"] is True

    record, persisted = workspace.load()
    assert record.version == 2
    assert len(record.history) == 2
    assert tuple(item.operation_id for item in record.history) == tuple(
        result.output["child_operation_ids"]
    )
    assert len(experiment.nodes) == 2
    assert len(experiment.edges) == 1
    assert experiment_fingerprint(
        persisted, include_layout=True
    ) == preview.output["target_full_sha256"]

    outer = operations.load(call.operation_id)
    assert outer is not None
    assert outer.state == "committed"


def test_plan_crash_recovery_skips_completed_child_and_resumes_remaining(tmp_path) -> None:
    (
        bus,
        canvas,
        runtime,
        _experiment,
        previews,
        plans,
        workspace,
        leases,
        operations,
        _approvals,
    ) = _setup(tmp_path)
    preview = _plan_preview(bus)
    plan_id = preview.output["plan_id"]
    plan = plans.load(plan_id)
    assert plan is not None

    lease = leases.acquire("resume-plan", "owner-a", ttl_seconds=60.0)
    outer_call = _execute_call(plan_id, run_id="resume-plan", ordinal=1, lease=lease)
    assert bus.approval_callback is not None
    assert bus.approval_callback(
        outer_call,
        bus.descriptor(outer_call.tool_name),
    ) is True
    assert len(_approvals) == 1
    input_sha = sha256_identity(dict(outer_call.arguments))
    claim = operations.claim(
        operation_id=outer_call.operation_id,
        call_id=outer_call.call_id,
        tool_name=outer_call.tool_name,
        input_sha256=input_sha,
        lease_id=outer_call.lease_id,
        lease_generation=outer_call.lease_generation,
        approved=True,
    )
    assert claim.action == "execute"

    first = plan.ordered_steps[0]
    first_preview = previews.load(first.preview_id)
    assert first_preview is not None
    child_id = runtime._child_operation_id(
        plan_id=plan.plan_id,
        plan_operation_id=outer_call.operation_id,
        step=first,
    )
    direct = canvas.commit(
        CanvasCommitRequest(first.preview_id),
        ToolContext(
            sequence=1,
            call_id="partial-step",
            tool_name="cace.canvas.commit_preview",
            capability=bus.descriptor("cace.canvas.commit_preview").capability,
            run_id=outer_call.run_id,
            operation_id=child_id,
            lease_id=lease.lease_id,
            lease_generation=lease.generation,
        ),
    )
    assert direct.workspace_version == 1
    assert workspace.load()[0].version == 1
    assert operations.load(outer_call.operation_id).state == "in_progress"

    retry = ToolCall(
        "resume-retry",
        outer_call.tool_name,
        dict(outer_call.arguments),
        run_id=outer_call.run_id,
        operation_id=outer_call.operation_id,
        lease_id=lease.lease_id,
        lease_generation=lease.generation,
    )
    recovered = bus.invoke(retry)
    assert recovered.status is ToolStatus.OK
    assert len(_approvals) == 1
    assert recovered.output["completed_steps"] == ["add-sink", "wire"]
    assert recovered.output["final_workspace_version"] == 2
    assert operations.load(outer_call.operation_id).state == "committed"

    record, persisted = workspace.load()
    assert record.version == 2
    assert len(record.history) == 2
    assert record.history[0].operation_id == child_id
    assert experiment_fingerprint(
        persisted, include_layout=True
    ) == plan.target_full_sha256


def test_plan_dependency_cycle_is_rejected_without_mutation(tmp_path) -> None:
    bus, *_rest = _setup(tmp_path)
    result = bus.invoke(
        ToolCall(
            "cycle-preview",
            "cace.canvas.preview_plan",
            {
                "steps": [
                    {
                        "step_id": "a",
                        "depends_on": ["b"],
                        "operations": [
                            {
                                "action": "move_node",
                                "node_id": "src",
                                "position": [1.0, 0.0],
                            }
                        ],
                    },
                    {
                        "step_id": "b",
                        "depends_on": ["a"],
                        "operations": [
                            {
                                "action": "move_node",
                                "node_id": "src",
                                "position": [2.0, 0.0],
                            }
                        ],
                    },
                ]
            },
        )
    )
    assert result.status is ToolStatus.INVALID_REQUEST
    assert "dependency graph contains a cycle" in result.error


def test_plan_human_denial_preserves_workspace(tmp_path) -> None:
    (
        bus,
        _canvas,
        _runtime,
        experiment,
        _previews,
        _plans,
        workspace,
        leases,
        _operations,
        approvals,
    ) = _setup(tmp_path, approve=False)
    preview = _plan_preview(bus)
    lease = leases.acquire("deny-plan", "owner-a", ttl_seconds=60.0)

    denied = bus.invoke(
        _execute_call(
            preview.output["plan_id"],
            run_id="deny-plan",
            ordinal=1,
            lease=lease,
        )
    )
    assert denied.status is ToolStatus.DENIED
    assert len(approvals) == 1
    assert workspace.load()[0].version == 0
    assert len(experiment.nodes) == 1


def test_stale_plan_is_safe_rejection_before_any_step_commits(tmp_path) -> None:
    (
        bus,
        canvas,
        _runtime,
        _experiment,
        _previews,
        _plans,
        workspace,
        leases,
        _operations,
        _approvals,
    ) = _setup(tmp_path)
    plan_preview = _plan_preview(bus)

    # Advance the workspace independently before executing the stored plan.
    single = bus.invoke(
        ToolCall(
            "single-preview",
            "cace.canvas.preview_mutation",
            {
                "operations": [
                    {
                        "action": "move_node",
                        "node_id": "src",
                        "position": [9.0, 9.0],
                    }
                ]
            },
        )
    )
    assert single.status is ToolStatus.OK

    lease_a = leases.acquire("advance", "owner-a", ttl_seconds=60.0)
    advance_context = ToolContext(
        sequence=1,
        call_id="advance-commit",
        tool_name="cace.canvas.commit_preview",
        capability=bus.descriptor("cace.canvas.commit_preview").capability,
        run_id="advance",
        operation_id="advance-operation",
        lease_id=lease_a.lease_id,
        lease_generation=lease_a.generation,
    )
    committed = canvas.commit(
        CanvasCommitRequest(single.output["preview_id"]),
        advance_context,
    )
    assert committed.workspace_version == 1
    assert leases.release(lease_a) is True

    lease_b = leases.acquire("stale-plan", "owner-b", ttl_seconds=60.0)
    stale = bus.invoke(
        _execute_call(
            plan_preview.output["plan_id"],
            run_id="stale-plan",
            ordinal=1,
            lease=lease_b,
        )
    )
    assert stale.status is ToolStatus.INVALID_REQUEST
    assert "expected workspace version 0, found 1" in stale.error
    assert workspace.load()[0].version == 1


def test_completed_plan_reconciles_after_newer_workspace_version_without_rollback(tmp_path) -> None:
    (
        bus,
        canvas,
        runtime,
        _experiment,
        _previews,
        _plans,
        workspace,
        leases,
        operations,
        approvals,
    ) = _setup(tmp_path)
    preview = _plan_preview(bus)
    plan_id = preview.output["plan_id"]

    lease_a = leases.acquire("history-plan", "owner-a", ttl_seconds=60.0)
    outer = _execute_call(plan_id, run_id="history-plan", ordinal=1, lease=lease_a)
    assert bus.approval_callback is not None
    assert bus.approval_callback(outer, bus.descriptor(outer.tool_name)) is True
    assert len(approvals) == 1
    operations.claim(
        operation_id=outer.operation_id,
        call_id=outer.call_id,
        tool_name=outer.tool_name,
        input_sha256=sha256_identity(dict(outer.arguments)),
        lease_id=outer.lease_id,
        lease_generation=outer.lease_generation,
        approved=True,
    )
    direct_plan = runtime.execute_plan(
        CanvasPlanExecuteRequest(plan_id),
        ToolContext(
            sequence=1,
            call_id=outer.call_id,
            tool_name=outer.tool_name,
            capability=bus.descriptor(outer.tool_name).capability,
            run_id=outer.run_id,
            operation_id=outer.operation_id,
            lease_id=outer.lease_id,
            lease_generation=outer.lease_generation,
        ),
    )
    assert direct_plan.final_workspace_version == 2
    assert operations.load(outer.operation_id).state == "in_progress"
    assert leases.release(lease_a) is True

    extra_preview = bus.invoke(
        ToolCall(
            "after-plan-preview",
            "cace.canvas.preview_mutation",
            {
                "operations": [
                    {
                        "action": "move_node",
                        "node_id": "src",
                        "position": [7.0, 7.0],
                    }
                ]
            },
        )
    )
    assert extra_preview.status is ToolStatus.OK
    lease_b = leases.acquire("after-plan", "owner-b", ttl_seconds=60.0)
    extra = canvas.commit(
        CanvasCommitRequest(extra_preview.output["preview_id"]),
        ToolContext(
            sequence=2,
            call_id="after-plan-commit",
            tool_name="cace.canvas.commit_preview",
            capability=bus.descriptor("cace.canvas.commit_preview").capability,
            run_id="after-plan",
            operation_id="after-plan-operation",
            lease_id=lease_b.lease_id,
            lease_generation=lease_b.generation,
        ),
    )
    assert extra.workspace_version == 3
    latest_hash = workspace.load()[0].target_full_sha256
    assert leases.release(lease_b) is True

    lease_a2 = leases.acquire("history-plan", "owner-a2", ttl_seconds=60.0)
    retry = ToolCall(
        "history-plan-retry",
        outer.tool_name,
        dict(outer.arguments),
        run_id=outer.run_id,
        operation_id=outer.operation_id,
        lease_id=lease_a2.lease_id,
        lease_generation=lease_a2.generation,
    )
    recovered = bus.invoke(retry)
    assert recovered.status is ToolStatus.OK
    assert len(approvals) == 1
    assert recovered.output["final_workspace_version"] == 2
    assert recovered.output["target_full_sha256"] == direct_plan.target_full_sha256
    assert operations.load(outer.operation_id).state == "committed"

    latest, latest_experiment = workspace.load()
    assert latest.version == 3
    assert latest.target_full_sha256 == latest_hash
    assert experiment_fingerprint(latest_experiment, include_layout=True) == latest_hash

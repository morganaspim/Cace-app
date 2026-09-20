from __future__ import annotations

from cace_studio.agent_runtime import (
    AutonomyAdvanceRequest,
    AutonomyLoopBudget,
    AutonomyReplanContext,
    AutonomyRunSpec,
    CanvasMutationOperation,
    CanvasPlanPreviewRequest,
    CanvasPlanStep,
    CapabilityPolicy,
    FileAgentLeaseManager,
    FileAutonomySessionStore,
    FileCanvasPlanStore,
    FileCanvasPreviewStore,
    FileExperimentWorkspace,
    FileOperationStore,
    LocalJSONReplanProvider,
    ToolBus,
    ToolCall,
    ToolContext,
    ToolStatus,
    autonomy_cycle_approval_callback,
    operation_id_for,
    register_autonomy_loop_tools,
    register_canvas_mutation_tools,
    register_canvas_plan_tools,
)
from cace_studio.core.graph import Experiment, Node
from cace_studio.core.module import ExecutionContext, Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.reproducibility import experiment_fingerprint, sha256_identity
from cace_studio.core.types import Maturity, ModuleMetadata, PortSpec


class LoopSource(Module):
    metadata = ModuleMetadata(
        module_id="loop.source",
        name="Loop Source",
        version="1",
        category="test",
        description="Autonomy loop source.",
        maturity=Maturity.PROTOTYPE,
    )
    outputs = (PortSpec("y", "scalar"),)
    executions = 0

    def execute(self, inputs, params, ctx: ExecutionContext):
        type(self).executions += 1
        return {"y": 1.0}


class LoopSink(Module):
    metadata = ModuleMetadata(
        module_id="loop.sink",
        name="Loop Sink",
        version="1",
        category="test",
        description="Autonomy loop sink.",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "scalar"),)

    def execute(self, inputs, params, ctx: ExecutionContext):
        return {}


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.register(LoopSource)
    registry.register(LoopSink)
    return registry


def _initial_plan(bus: ToolBus):
    result = bus.invoke(
        ToolCall(
            "initial-plan-preview",
            "cace.canvas.preview_plan",
            {
                "steps": [
                    {
                        "step_id": "add-sink",
                        "operations": [
                            {
                                "action": "add_node",
                                "node_id": "sink",
                                "module_id": "loop.sink",
                                "position": [1.0, 2.0],
                            }
                        ],
                    },
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
                ]
            },
        )
    )
    assert result.status is ToolStatus.OK
    return result.output["plan_id"]


def _follow_up_plan() -> CanvasPlanPreviewRequest:
    return CanvasPlanPreviewRequest(
        steps=(
            CanvasPlanStep(
                step_id="move-source",
                operations=(
                    CanvasMutationOperation(
                        action="move_node",
                        node_id="src",
                        position=(4.0, 5.0),
                    ),
                ),
            ),
        )
    )


def _advance_call(session_id: str, plan_id: str, *, run_id: str, ordinal: int, lease):
    arguments = {"session_id": session_id, "plan_id": plan_id}
    return ToolCall(
        f"{run_id}:{ordinal}",
        "cace.autonomy.advance",
        arguments,
        run_id=run_id,
        operation_id=operation_id_for(
            run_id=run_id,
            ordinal=ordinal,
            tool_name="cace.autonomy.advance",
            arguments=arguments,
        ),
        lease_id=lease.lease_id,
        lease_generation=lease.generation,
    )


def _setup(tmp_path, *, replan_provider=None, approve=True):
    LoopSource.executions = 0
    registry = _registry()
    experiment = Experiment(
        name="autonomy",
        nodes=[Node("src", "loop.source", position=(0.0, 0.0))],
    )
    previews = FileCanvasPreviewStore(tmp_path / "previews")
    plans = FileCanvasPlanStore(tmp_path / "plans")
    workspace = FileExperimentWorkspace(tmp_path / "workspace", workspace_id="main")
    sessions = FileAutonomySessionStore(tmp_path / "sessions")
    leases = FileAgentLeaseManager(tmp_path / "leases")
    operations = FileOperationStore(tmp_path / "operations")
    approvals: list[dict] = []

    def decide(payload):
        approvals.append(dict(payload))
        return approve

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
        replan_provider=replan_provider,
    )
    bus.approval_callback = autonomy_cycle_approval_callback(
        sessions,
        plans,
        decide,
    )
    return (
        bus,
        autonomy,
        experiment,
        plans,
        workspace,
        sessions,
        leases,
        operations,
        approvals,
    )


def test_autonomy_cycle_executes_observes_and_previews_next_plan_without_mutating_it(tmp_path) -> None:
    replans: list[dict] = []

    def replan(context):
        replans.append(context.to_dict())
        return _follow_up_plan()

    (
        bus,
        autonomy,
        experiment,
        plans,
        workspace,
        sessions,
        leases,
        _operations,
        approvals,
    ) = _setup(tmp_path, replan_provider=replan)
    initial_plan_id = _initial_plan(bus)
    session = autonomy.create_session(
        initial_plan_id=initial_plan_id,
        objective="connect the source, run it, then improve layout",
        budget=AutonomyLoopBudget(
            max_cycles=3,
            max_science_runs=3,
            max_replans=2,
            max_plan_steps_per_cycle=10,
        ),
        session_id="session-a",
    )
    lease = leases.acquire("autonomy-run", "owner-a", ttl_seconds=60.0)

    first = bus.invoke(
        _advance_call(
            session.session_id,
            initial_plan_id,
            run_id="autonomy-run",
            ordinal=1,
            lease=lease,
        )
    )
    assert first.status is ToolStatus.OK
    assert len(approvals) == 1
    assert approvals[0]["pending_plan"]["plan_id"] == initial_plan_id
    assert approvals[0]["post_plan_behavior"].startswith("run one bounded")
    assert first.output["stage"] == "WAITING_PLAN_APPROVAL"
    assert first.output["next_plan_id"]
    assert first.output["science_completed"] is True
    assert first.output["workspace_version"] == 2
    assert first.output["perception"]["evidence_authority"] is False
    assert first.output["perception"]["semantic_graph_hash"] == (
        workspace.load()[0].target_semantic_sha256
    )
    assert len(replans) == 1
    assert replans[0]["remaining_replans"] == 2
    assert LoopSource.executions == 1

    # The follow-up plan is previewed only. No second mutation occurs before
    # its own approval/advance call.
    record_after_first, persisted_after_first = workspace.load()
    assert record_after_first.version == 2
    assert experiment_fingerprint(
        persisted_after_first, include_layout=True
    ) == experiment_fingerprint(experiment, include_layout=True)

    pending = plans.load(first.output["next_plan_id"])
    assert pending is not None
    assert pending.base_workspace_version == 2
    assert pending.target_workspace_version == 3

    inspected = bus.invoke(
        ToolCall(
            "inspect-session",
            "cace.autonomy.inspect_session",
            {"session_id": session.session_id},
        )
    )
    assert inspected.status is ToolStatus.OK
    assert inspected.output["pending_plan_id"] == first.output["next_plan_id"]
    assert inspected.output["cycles_completed"] == 1
    assert inspected.output["science_runs"] == 1
    assert inspected.output["replans"] == 1


def test_second_autonomy_cycle_requires_new_approval_and_can_finish(tmp_path) -> None:
    calls = [0]

    def replan(_context):
        calls[0] += 1
        if calls[0] == 1:
            return _follow_up_plan()
        return None

    (
        bus,
        autonomy,
        experiment,
        _plans,
        workspace,
        sessions,
        leases,
        _operations,
        approvals,
    ) = _setup(tmp_path, replan_provider=replan)
    initial_plan_id = _initial_plan(bus)
    session = autonomy.create_session(
        initial_plan_id=initial_plan_id,
        budget=AutonomyLoopBudget(
            max_cycles=3,
            max_science_runs=3,
            max_replans=2,
            max_plan_steps_per_cycle=10,
        ),
        session_id="session-b",
    )
    lease = leases.acquire("two-cycle-run", "owner-a", ttl_seconds=60.0)

    first = bus.invoke(
        _advance_call(
            session.session_id,
            initial_plan_id,
            run_id="two-cycle-run",
            ordinal=1,
            lease=lease,
        )
    )
    assert first.status is ToolStatus.OK
    next_plan_id = first.output["next_plan_id"]
    assert len(approvals) == 1
    assert workspace.load()[0].version == 2

    second = bus.invoke(
        _advance_call(
            session.session_id,
            next_plan_id,
            run_id="two-cycle-run",
            ordinal=2,
            lease=lease,
        )
    )
    assert second.status is ToolStatus.OK
    assert len(approvals) == 2
    assert approvals[1]["pending_plan"]["plan_id"] == next_plan_id
    assert second.output["stage"] == "FINISHED"
    assert second.output["next_plan_id"] == ""
    assert second.output["workspace_version"] == 3
    assert LoopSource.executions == 2

    final_session = sessions.load(session.session_id)
    assert final_session is not None
    assert final_session.stage.value == "FINISHED"
    assert final_session.cycles_completed == 2
    assert final_session.science_runs == 2
    assert final_session.replans == 1
    assert len(final_session.receipts) == 2
    assert workspace.load()[0].version == 3
    assert experiment.nodes[0].position == (4.0, 5.0)


def test_cycle_budget_prevents_replan_even_if_provider_is_available(tmp_path) -> None:
    provider_calls = [0]

    def replan(_context):
        provider_calls[0] += 1
        return _follow_up_plan()

    (
        bus,
        autonomy,
        _experiment,
        _plans,
        workspace,
        sessions,
        leases,
        _operations,
        _approvals,
    ) = _setup(tmp_path, replan_provider=replan)
    plan_id = _initial_plan(bus)
    session = autonomy.create_session(
        initial_plan_id=plan_id,
        budget=AutonomyLoopBudget(
            max_cycles=1,
            max_science_runs=1,
            max_replans=5,
            max_plan_steps_per_cycle=10,
        ),
        session_id="budget-session",
    )
    lease = leases.acquire("budget-run", "owner-a", ttl_seconds=60.0)

    result = bus.invoke(
        _advance_call(
            session.session_id,
            plan_id,
            run_id="budget-run",
            ordinal=1,
            lease=lease,
        )
    )
    assert result.status is ToolStatus.OK
    assert result.output["stage"] == "FINISHED"
    assert result.output["cycles_remaining"] == 0
    assert result.output["science_runs_remaining"] == 0
    assert result.output["next_plan_id"] == ""
    assert provider_calls[0] == 0
    assert workspace.load()[0].version == 2

    stored = sessions.load(session.session_id)
    assert stored is not None
    assert stored.cycles_completed == 1
    assert stored.replans == 0


def test_crash_retry_reuses_cycle_receipt_without_rerunning_science_or_approval(tmp_path) -> None:
    (
        bus,
        autonomy,
        _experiment,
        _plans,
        workspace,
        sessions,
        leases,
        operations,
        approvals,
    ) = _setup(tmp_path, replan_provider=None)
    plan_id = _initial_plan(bus)
    session = autonomy.create_session(
        initial_plan_id=plan_id,
        budget=AutonomyLoopBudget(
            max_cycles=2,
            max_science_runs=2,
            max_replans=0,
            max_plan_steps_per_cycle=10,
        ),
        session_id="crash-session",
    )
    lease = leases.acquire("crash-cycle", "owner-a", ttl_seconds=60.0)
    call = _advance_call(
        session.session_id,
        plan_id,
        run_id="crash-cycle",
        ordinal=1,
        lease=lease,
    )

    assert bus.approval_callback is not None
    assert bus.approval_callback(call, bus.descriptor(call.tool_name)) is True
    assert len(approvals) == 1
    claim = operations.claim(
        operation_id=call.operation_id,
        call_id=call.call_id,
        tool_name=call.tool_name,
        input_sha256=sha256_identity(dict(call.arguments)),
        lease_id=call.lease_id,
        lease_generation=call.lease_generation,
        approved=True,
    )
    assert claim.action == "execute"

    direct = autonomy.advance(
        AutonomyAdvanceRequest(session.session_id, plan_id),
        ToolContext(
            sequence=1,
            call_id=call.call_id,
            tool_name=call.tool_name,
            capability=bus.descriptor(call.tool_name).capability,
            run_id=call.run_id,
            operation_id=call.operation_id,
            lease_id=call.lease_id,
            lease_generation=call.lease_generation,
        ),
    )
    assert direct.stage == "FINISHED"
    assert LoopSource.executions == 1
    assert operations.load(call.operation_id).state == "in_progress"
    assert sessions.load(session.session_id).receipts[0].operation_id == call.operation_id

    retry = ToolCall(
        "crash-cycle-retry",
        call.tool_name,
        dict(call.arguments),
        run_id=call.run_id,
        operation_id=call.operation_id,
        lease_id=call.lease_id,
        lease_generation=call.lease_generation,
    )
    recovered = bus.invoke(retry)
    assert recovered.status is ToolStatus.OK
    assert recovered.output["science_run_id"] == direct.science_run_id
    assert recovered.output["workspace_version"] == direct.workspace_version
    assert len(approvals) == 1
    assert LoopSource.executions == 1
    assert operations.load(call.operation_id).state == "committed"
    assert workspace.load()[0].version == 2


def test_new_follow_up_plan_is_denied_without_its_own_approval(tmp_path) -> None:
    approval_count = [0]

    def replan(_context):
        return _follow_up_plan()

    (
        bus,
        autonomy,
        _experiment,
        _plans,
        workspace,
        sessions,
        leases,
        _operations,
        approvals,
    ) = _setup(tmp_path, replan_provider=replan, approve=True)
    plan_id = _initial_plan(bus)
    session = autonomy.create_session(
        initial_plan_id=plan_id,
        budget=AutonomyLoopBudget(
            max_cycles=2,
            max_science_runs=2,
            max_replans=1,
            max_plan_steps_per_cycle=10,
        ),
        session_id="approval-boundary",
    )
    lease = leases.acquire("approval-boundary-run", "owner-a", ttl_seconds=60.0)
    first = bus.invoke(
        _advance_call(
            session.session_id,
            plan_id,
            run_id="approval-boundary-run",
            ordinal=1,
            lease=lease,
        )
    )
    assert first.status is ToolStatus.OK
    assert len(approvals) == 1
    assert workspace.load()[0].version == 2

    # Replace the human decision with denial before the newly proposed plan.
    bus.approval_callback = autonomy_cycle_approval_callback(
        sessions,
        _plans,
        lambda payload: (approval_count.__setitem__(0, approval_count[0] + 1), False)[1],
    )
    denied = bus.invoke(
        _advance_call(
            session.session_id,
            first.output["next_plan_id"],
            run_id="approval-boundary-run",
            ordinal=2,
            lease=lease,
        )
    )
    assert denied.status is ToolStatus.DENIED
    assert approval_count[0] == 1
    assert workspace.load()[0].version == 2
    stored = sessions.load(session.session_id)
    assert stored is not None
    assert stored.stage.value == "WAITING_PLAN_APPROVAL"
    assert stored.pending_plan_id == first.output["next_plan_id"]


class _FakeReplanAI:
    def __init__(self, responses):
        self.responses = list(responses)
        self.messages = []

    def chat(self, messages, *, temperature=0.2):
        self.messages.append((messages, temperature))
        return self.responses.pop(0)


def _replan_context() -> AutonomyReplanContext:
    return AutonomyReplanContext(
        session_id="ai-session",
        objective="improve the layout after observing the run",
        cycle_index=1,
        run_summary={
            "run_id": "run-1",
            "completed": True,
            "proof_effect": "none",
            "promotion_authority": False,
        },
        perception={
            "schema_version": "cace-agent-perception-v1",
            "run_id": "run-1",
            "experiment_id": "exp",
            "monotonic_seq": 0,
            "semantic_graph_hash": "a" * 64,
            "emitted_at": "2026-09-20T00:00:00+00:00",
            "network_mode": "LOCAL_ZERO_CONTACT",
            "nodes": [],
            "evidence_authority": False,
        },
        workspace_id="main",
        workspace_version=2,
        semantic_experiment_sha256="a" * 64,
        full_experiment_sha256="b" * 64,
        remaining_cycles=2,
        remaining_science_runs=2,
        remaining_replans=1,
    )


def test_local_json_replan_provider_returns_only_typed_plan_or_finish() -> None:
    ai = _FakeReplanAI(
        [
            '{"action":"replan","steps":[{"step_id":"move","operations":[{"action":"move_node","node_id":"src","position":[3,4]}]}]}',
            '{"action":"finish"}',
        ]
    )
    provider = LocalJSONReplanProvider(ai, temperature=0.0)
    proposal = provider(_replan_context())
    assert isinstance(proposal, CanvasPlanPreviewRequest)
    assert proposal.steps[0].step_id == "move"
    assert proposal.steps[0].operations[0].action == "move_node"
    assert provider(_replan_context()) is None
    assert len(ai.messages) == 2


def test_local_json_replan_provider_rejects_unknown_fields() -> None:
    ai = _FakeReplanAI(
        ['{"action":"replan","steps":[],"unexpected":"x"}']
    )
    provider = LocalJSONReplanProvider(ai)
    try:
        provider(_replan_context())
    except ValueError as exc:
        assert "unknown fields" in str(exc)
    else:
        raise AssertionError("replan provider accepted an unknown field")

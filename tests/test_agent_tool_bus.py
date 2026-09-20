from __future__ import annotations

from dataclasses import dataclass

import pytest

from cace_studio.app import build_qualified_capabilities, build_registry

from cace_studio.agent_runtime import (
    AgentBudget,
    AgentController,
    AgentDecision,
    AgentTurnContext,
    Capability,
    CapabilityPolicy,
    FileAgentLeaseManager,
    FileOperationStore,
    ToolBus,
    ToolCall,
    ToolStatus,
    TypedTool,
    LocalJSONPlanner,
    register_core_tools,
)
from cace_studio.core.graph import Experiment, Node
from cace_studio.core.module import ExecutionContext, Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.types import Maturity, ModuleMetadata, PortSpec
from cace_studio.ai.provider import AIProvider, ProviderHealth
from cace_studio.core.reproducibility import sha256_identity


@dataclass(frozen=True)
class EchoRequest:
    text: str
    count: int = 1


@dataclass(frozen=True)
class EchoResponse:
    text: str


def _echo(request: EchoRequest, _context) -> EchoResponse:
    return EchoResponse(request.text * request.count)


def _echo_tool(capability: Capability = Capability.READ_RUNTIME) -> TypedTool:
    return TypedTool(
        name="test.echo",
        description="Echo typed text.",
        capability=capability,
        request_type=EchoRequest,
        response_type=EchoResponse,
        handler=_echo,
    )


def test_typed_tool_bus_validates_request_and_hashes_audit() -> None:
    bus = ToolBus()
    bus.register(_echo_tool())

    ok = bus.invoke(ToolCall("call-1", "test.echo", {"text": "ab", "count": 2}))
    assert ok.status is ToolStatus.OK
    assert ok.output == {"text": "abab"}
    assert ok.proof_effect == "none"
    assert ok.promotion_authority is False

    bad = bus.invoke(ToolCall("call-2", "test.echo", {"text": "ab", "extra": 1}))
    assert bad.status is ToolStatus.INVALID_REQUEST
    assert "unknown fields" in bad.error

    records = bus.audit_records
    assert len(records) == 2
    assert records[0].input_sha256 != records[0].output_sha256
    assert records[0].proof_effect == "none"
    assert records[0].promotion_authority is False


def test_zero_contact_policy_hard_denies_network_even_when_registered() -> None:
    called = False

    def handler(request: EchoRequest, _context) -> EchoResponse:
        nonlocal called
        called = True
        return EchoResponse(request.text)

    bus = ToolBus(policy=CapabilityPolicy.zero_contact())
    bus.register(
        TypedTool(
            name="test.network",
            description="A deliberately forbidden network-capability test tool.",
            capability=Capability.NETWORK,
            request_type=EchoRequest,
            response_type=EchoResponse,
            handler=handler,
        )
    )
    result = bus.invoke(ToolCall("call-network", "test.network", {"text": "x"}))
    assert result.status is ToolStatus.DENIED
    assert "network" in result.error
    assert called is False
    assert "test.network" not in {item.name for item in bus.descriptors()}


def test_approval_required_capability_fails_closed_without_approval(tmp_path) -> None:
    bus = ToolBus(policy=CapabilityPolicy.zero_contact())
    bus.register(_echo_tool(Capability.CANVAS_MUTATE))
    denied = bus.invoke(ToolCall("call-1", "test.echo", {"text": "x"}))
    assert denied.status is ToolStatus.DENIED
    assert "approval required" in denied.error

    lease_manager = FileAgentLeaseManager(tmp_path / "approved-leases")
    lease = lease_manager.acquire("approved-run", "approved-owner", ttl_seconds=60.0)
    approved_bus = ToolBus(
        policy=CapabilityPolicy.zero_contact(),
        approval_callback=lambda call, descriptor: (
            call.tool_name == descriptor.name == "test.echo"
        ),
        operation_store=FileOperationStore(tmp_path / "approved-operations"),
        lease_validator=lambda call: lease_manager.assert_current(
            call.run_id,
            call.lease_id,
            call.lease_generation,
        ),
    )
    approved_bus.register(_echo_tool(Capability.CANVAS_MUTATE))
    allowed = approved_bus.invoke(
        ToolCall(
            "call-2",
            "test.echo",
            {"text": "y"},
            run_id="approved-run",
            operation_id="approved-operation-1",
            lease_id=lease.lease_id,
            lease_generation=lease.generation,
        )
    )
    assert allowed.status is ToolStatus.OK
    assert approved_bus.audit_records[-1].approved is True


def test_handler_response_type_mismatch_fails_closed() -> None:
    def bad_handler(request: EchoRequest, _context):
        return {"text": request.text}

    bus = ToolBus()
    bus.register(
        TypedTool(
            name="test.bad_response",
            description="Return the wrong response type.",
            capability=Capability.READ_RUNTIME,
            request_type=EchoRequest,
            response_type=EchoResponse,
            handler=bad_handler,
        )
    )
    result = bus.invoke(ToolCall("call-1", "test.bad_response", {"text": "x"}))
    assert result.status is ToolStatus.INVALID_RESPONSE


class ScriptedPlanner:
    def __init__(self, decisions):
        self.decisions = list(decisions)

    def decide(self, _context):
        if not self.decisions:
            return AgentDecision.abort("script exhausted")
        return self.decisions.pop(0)


def test_agent_controller_routes_actions_only_through_tool_bus() -> None:
    bus = ToolBus()
    bus.register(_echo_tool())
    controller = AgentController(bus, budget=AgentBudget(max_steps=4, max_tool_calls=2, max_failures=2))
    planner = ScriptedPlanner(
        [
            AgentDecision.tool("test.echo", {"text": "ok", "count": 2}),
            AgentDecision.finish("done"),
        ]
    )
    report = controller.run("test the tool", planner)
    assert report.status == "finished"
    assert report.message == "done"
    assert report.tool_calls == 1
    assert report.failures == 0
    assert report.trace[0].tool_result is not None
    assert report.trace[0].tool_result.output == {"text": "okok"}
    assert report.proof_effect == "none"
    assert report.promotion_authority is False


def test_agent_controller_stops_on_failure_budget() -> None:
    bus = ToolBus()
    controller = AgentController(bus, budget=AgentBudget(max_steps=5, max_tool_calls=5, max_failures=2))
    planner = ScriptedPlanner(
        [
            AgentDecision.tool("missing.tool", {}),
            AgentDecision.tool("missing.tool", {}),
            AgentDecision.finish("should not reach"),
        ]
    )
    report = controller.run("bounded failure loop", planner)
    assert report.status == "aborted"
    assert report.failures == 2
    assert report.tool_calls == 2


class AddOneModule(Module):
    metadata = ModuleMetadata(
        module_id="test.add_one",
        name="Add One",
        version="1",
        category="test",
        description="Simple deterministic test module.",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "scalar"),)
    outputs = (PortSpec("y", "scalar"),)

    def execute(self, inputs, params, ctx: ExecutionContext):
        return {"y": inputs["x"] + 1}


def test_core_tool_registration_exposes_catalog_and_active_graph_without_proof_authority() -> None:
    registry = ModuleRegistry()
    registry.register(AddOneModule)
    experiment = Experiment(name="agent-test", nodes=[Node("n1", "test.add_one")])

    bus = ToolBus()
    register_core_tools(bus, registry=registry, active_experiment=experiment)

    names = {item.name for item in bus.descriptors()}
    assert "cace.runtime.native_status" in names
    assert "cace.registry.list_modules" in names
    assert "cace.experiment.describe_active" in names
    assert "cace.experiment.run_active" in names

    catalog = bus.invoke(
        ToolCall("catalog", "cace.registry.list_modules", {"limit": 10})
    )
    assert catalog.status is ToolStatus.OK
    assert catalog.output["modules"][0]["module_id"] == "test.add_one"
    assert catalog.output["modules"][0]["evidence_note"].startswith("module metadata")

    summary = bus.invoke(
        ToolCall("summary", "cace.experiment.describe_active", {})
    )
    assert summary.status is ToolStatus.OK
    assert summary.output["node_count"] == 1
    assert summary.output["module_ids"] == ["test.add_one"]


def test_run_active_uses_canonical_graph_executor_and_requires_real_inputs() -> None:
    registry = ModuleRegistry()
    registry.register(AddOneModule)
    experiment = Experiment(name="agent-test", nodes=[Node("n1", "test.add_one")])
    bus = ToolBus()
    register_core_tools(bus, registry=registry, active_experiment=experiment)

    missing = bus.invoke(
        ToolCall("run-missing", "cace.experiment.run_active", {"seed": 3})
    )
    assert missing.status is ToolStatus.ERROR
    assert "missing inputs" in missing.error

    result = bus.invoke(
        ToolCall(
            "run-ok",
            "cace.experiment.run_active",
            {"seed": 3, "external_inputs": {"n1": {"x": 4}}},
        )
    )
    assert result.status is ToolStatus.OK
    assert result.output["completed"] is True
    assert result.output["node_output_ports"] == {"n1": ["y"]}
    assert result.output["all_verifiers_passed"] is False
    assert result.proof_effect == "none"
    assert result.promotion_authority is False


class FakeLocalProvider(AIProvider):
    provider_id = "fake-local"
    display_name = "Fake local"

    def __init__(self, reply: str):
        super().__init__("http://127.0.0.1:9999", model="fake")
        self.reply = reply

    def health(self) -> ProviderHealth:
        return ProviderHealth(self.provider_id, self.display_name, self.endpoint, True, ("fake",), "ok")

    def list_models(self) -> tuple[str, ...]:
        return ("fake",)

    def chat(self, messages, *, temperature: float = 0.2) -> str:
        return self.reply


def test_local_json_planner_accepts_only_strict_json_and_visible_tools() -> None:
    bus = ToolBus()
    bus.register(_echo_tool())
    context = AgentTurnContext(
        task="echo",
        step=1,
        tools=bus.descriptors(),
        observations=(),
        remaining_tool_calls=1,
        remaining_failures=1,
    )
    planner = LocalJSONPlanner(
        FakeLocalProvider('{"action":"tool","tool_name":"test.echo","arguments":{"text":"x"}}')
    )
    decision = planner.decide(context)
    assert decision.action == "tool"
    assert decision.tool_name == "test.echo"

    unavailable = LocalJSONPlanner(
        FakeLocalProvider('{"action":"tool","tool_name":"test.hidden","arguments":{}}')
    )
    with pytest.raises(ValueError, match="unavailable tool"):
        unavailable.decide(context)

    fenced = LocalJSONPlanner(
        FakeLocalProvider('```json\\n{"action":"finish","message":"x"}\\n```')
    )
    with pytest.raises(ValueError, match="one JSON object"):
        fenced.decide(context)


def test_consequential_capability_requires_durable_idempotency(tmp_path) -> None:
    bus = ToolBus(
        policy=CapabilityPolicy.zero_contact(),
        approval_callback=lambda _call, _descriptor: True,
    )
    bus.register(_echo_tool(Capability.CANVAS_MUTATE))
    descriptor = bus.descriptor("test.echo")
    assert descriptor.idempotency_required is True

    missing_id = bus.invoke(ToolCall("call-no-id", "test.echo", {"text": "x"}))
    assert missing_id.status is ToolStatus.INVALID_REQUEST
    assert "operation_id" in missing_id.error

    with_id_no_store = bus.invoke(
        ToolCall(
            "call-no-store",
            "test.echo",
            {"text": "x"},
            operation_id="mutation-operation",
            lease_id="lease-a",
            lease_generation=2,
        )
    )
    assert with_id_no_store.status is ToolStatus.INVALID_REQUEST
    assert "operation store" in with_id_no_store.error

    fenced_bus = ToolBus(
        policy=CapabilityPolicy.zero_contact(),
        approval_callback=lambda _call, _descriptor: True,
        operation_store=FileOperationStore(tmp_path / "fenced-operations"),
    )
    fenced_bus.register(_echo_tool(Capability.CANVAS_MUTATE))
    missing_lease = fenced_bus.invoke(
        ToolCall(
            "call-no-lease",
            "test.echo",
            {"text": "x"},
            operation_id="mutation-operation-2",
        )
    )
    assert missing_lease.status is ToolStatus.INVALID_REQUEST
    assert "lease fencing token" in missing_lease.error


def test_operation_store_replays_committed_result_without_handler_reexecution(tmp_path) -> None:
    calls: list[tuple[str, str | None, int]] = []

    def handler(request: EchoRequest, context) -> EchoResponse:
        calls.append((request.text, context.operation_id, context.lease_generation))
        return EchoResponse(request.text)

    tool = TypedTool(
        name="test.idempotent_echo",
        description="Exercise durable operation replay.",
        capability=Capability.READ_RUNTIME,
        request_type=EchoRequest,
        response_type=EchoResponse,
        handler=handler,
    )
    root = tmp_path / "operations"
    first = ToolBus(operation_store=FileOperationStore(root))
    second = ToolBus(operation_store=FileOperationStore(root))
    first.register(tool)
    second.register(tool)

    call1 = ToolCall(
        "call-a",
        "test.idempotent_echo",
        {"text": "once"},
        operation_id="same-operation",
        lease_id="lease-a",
        lease_generation=7,
    )
    result1 = first.invoke(call1)
    assert result1.status is ToolStatus.OK
    assert calls == [("once", "same-operation", 7)]

    call2 = ToolCall(
        "call-b",
        "test.idempotent_echo",
        {"text": "once"},
        operation_id="same-operation",
        lease_id="lease-b",
        lease_generation=8,
    )
    result2 = second.invoke(call2)
    assert result2.status is ToolStatus.OK
    assert result2.call_id == "call-b"
    assert result2.output == {"text": "once"}
    assert calls == [("once", "same-operation", 7)]

    conflict = second.invoke(
        ToolCall(
            "call-c",
            "test.idempotent_echo",
            {"text": "different"},
            operation_id="same-operation",
            lease_id="lease-b",
            lease_generation=8,
        )
    )
    assert conflict.status is ToolStatus.INVALID_REQUEST
    assert "idempotency conflict" in conflict.error


def test_in_progress_operation_blocks_duplicate_execution(tmp_path) -> None:
    calls: list[str] = []

    def handler(request: EchoRequest, _context) -> EchoResponse:
        calls.append(request.text)
        return EchoResponse(request.text)

    store = FileOperationStore(tmp_path / "blocked-operations")
    store.claim(
        operation_id="pending-operation",
        call_id="prior-call",
        tool_name="test.pending_echo",
        input_sha256=sha256_identity({"text": "x"}),
        lease_id="old-lease",
        lease_generation=1,
    )
    bus = ToolBus(operation_store=store)
    bus.register(
        TypedTool(
            name="test.pending_echo",
            description="Exercise unresolved operation blocking.",
            capability=Capability.READ_RUNTIME,
            request_type=EchoRequest,
            response_type=EchoResponse,
            handler=handler,
        )
    )
    result = bus.invoke(
        ToolCall(
            "new-call",
            "test.pending_echo",
            {"text": "x"},
            operation_id="pending-operation",
            lease_id="new-lease",
            lease_generation=2,
        )
    )
    assert result.status is ToolStatus.RECOVERY_BLOCKED
    assert "already in progress" in result.error
    assert calls == []



def test_qualified_capability_gate_filters_local_ai_catalog() -> None:
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)
    experiment = Experiment(
        name="qualified-agent",
        nodes=[Node("n1", "core.constant", {"value": 4})],
    )
    bus = ToolBus()
    register_core_tools(
        bus,
        registry=registry,
        qualified_capabilities=capabilities,
        active_experiment=experiment,
    )

    catalog = bus.invoke(
        ToolCall("qualified-catalog", "cace.registry.list_modules", {"limit": 100})
    )
    assert catalog.status is ToolStatus.OK
    assert catalog.output["capability_surface"] == "ai"
    module_ids = {item["module_id"] for item in catalog.output["modules"]}
    assert module_ids == set(capabilities.module_ids("ai"))
    assert "formal325.mesh_certificate_generator" not in module_ids
    assert all("capability_gates" in item for item in catalog.output["modules"])


def test_qualified_capability_gate_rejects_hidden_module_execution_for_local_ai() -> None:
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)
    experiment = Experiment(
        name="hidden-agent",
        nodes=[Node("n1", "formal325.mesh_certificate_generator")],
    )
    bus = ToolBus()
    register_core_tools(
        bus,
        registry=registry,
        qualified_capabilities=capabilities,
        active_experiment=experiment,
    )

    result = bus.invoke(
        ToolCall("hidden-run", "cace.experiment.run_active", {"seed": 0})
    )
    assert result.status is ToolStatus.ERROR
    assert "unavailable on ai surface" in result.error

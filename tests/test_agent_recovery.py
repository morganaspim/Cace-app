from __future__ import annotations

from dataclasses import dataclass
import json

import pytest

from cace_studio.agent_runtime import (
    AgentBudget,
    AgentCheckpoint,
    AgentController,
    AgentDecision,
    AgentHeartbeat,
    AgentLeaseManager,
    AgentPhase,
    Capability,
    FileCheckpointStore,
    HashChainedAuditJournal,
    LeaseUnavailableError,
    ToolBus,
    ToolCall,
    ToolStatus,
    TypedTool,
)


@dataclass(frozen=True)
class EchoRequest:
    text: str


@dataclass(frozen=True)
class EchoResponse:
    text: str


def _echo_tool() -> TypedTool:
    return TypedTool(
        name="test.echo",
        description="Echo typed text.",
        capability=Capability.READ_RUNTIME,
        request_type=EchoRequest,
        response_type=EchoResponse,
        handler=lambda request, context: EchoResponse(request.text),
    )


class ScriptedPlanner:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.calls = 0

    def decide(self, context):
        self.calls += 1
        if not self.decisions:
            return AgentDecision.abort("script exhausted")
        return self.decisions.pop(0)


def test_hash_chained_audit_journal_detects_tampering(tmp_path) -> None:
    bus = ToolBus()
    bus.register(_echo_tool())
    result = bus.invoke(ToolCall("call-1", "test.echo", {"text": "x"}))
    assert result.status is ToolStatus.OK

    path = tmp_path / "audit.jsonl"
    journal = HashChainedAuditJournal(path, session_id="session-1")
    digest = journal.append(bus.audit_records[-1])
    assert journal.verify() == (1, digest)

    line = json.loads(path.read_text(encoding="utf-8"))
    line["record"]["tool_name"] = "tampered"
    path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="content hash mismatch"):
        HashChainedAuditJournal(path)


def test_file_checkpoint_store_round_trip_and_hash_guard(tmp_path) -> None:
    store = FileCheckpointStore(tmp_path)
    checkpoint = AgentCheckpoint(
        run_id="run-1",
        task="inspect",
        next_step=2,
        tool_calls=1,
        failures=0,
        heartbeat_seq=3,
        observations=({"status": "ok"},),
    )
    digest = store.save(checkpoint)
    assert store.load("run-1") == checkpoint
    assert store.digest("run-1") == digest

    path = tmp_path / "run-1.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["checkpoint"]["tool_calls"] = 99
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        store.load("run-1")


def test_process_local_lease_expires_and_can_be_reacquired() -> None:
    now = [100.0]
    manager = AgentLeaseManager(clock=lambda: now[0])
    first = manager.acquire("run-1", "owner-a", ttl_seconds=5.0)
    with pytest.raises(LeaseUnavailableError):
        manager.acquire("run-1", "owner-b", ttl_seconds=5.0)

    now[0] = 106.0
    second = manager.acquire("run-1", "owner-b", ttl_seconds=5.0)
    assert second.generation == first.generation + 1


def test_controller_resumes_clean_checkpoint_and_blocks_uncertain_replay(tmp_path) -> None:
    store = FileCheckpointStore(tmp_path)
    store.save(
        AgentCheckpoint(
            run_id="resume-1",
            task="continue",
            next_step=2,
            tool_calls=1,
            failures=0,
            heartbeat_seq=4,
            observations=({"status": "ok"},),
        )
    )

    heartbeats: list[AgentHeartbeat] = []
    planner = ScriptedPlanner([AgentDecision.finish("done")])
    controller = AgentController(
        ToolBus(),
        checkpoint_store=store,
        heartbeat_callback=heartbeats.append,
        owner_id="test-owner",
    )
    report = controller.run("continue", planner, resume_run_id="resume-1")
    assert report.status == "finished"
    assert report.steps == 2
    assert report.tool_calls == 1
    assert planner.calls == 1
    assert heartbeats[0].monotonic_seq == 5
    assert all(item.evidence_authority is False for item in heartbeats)

    store.save(
        AgentCheckpoint(
            run_id="pending-1",
            task="continue",
            next_step=2,
            tool_calls=1,
            failures=0,
            heartbeat_seq=2,
            pending_call={
                "call_id": "pending-1:1",
                "tool_name": "test.echo",
                "arguments": {"text": "x"},
                "step": 1,
            },
        )
    )
    blocked_planner = ScriptedPlanner([AgentDecision.finish("must not run")])
    blocked = controller.run("continue", blocked_planner, resume_run_id="pending-1")
    assert blocked.status == "recovery_blocked"
    assert "pending tool call" in blocked.message
    assert blocked_planner.calls == 0


def test_controller_persists_audit_and_blocks_if_durable_audit_fails(tmp_path) -> None:
    bus = ToolBus()
    bus.register(_echo_tool())
    store = FileCheckpointStore(tmp_path / "checkpoints")
    journal = HashChainedAuditJournal(tmp_path / "audit.jsonl", session_id="agent-session")
    heartbeats: list[AgentHeartbeat] = []
    controller = AgentController(
        bus,
        checkpoint_store=store,
        audit_journal=journal,
        heartbeat_callback=heartbeats.append,
        owner_id="test-owner",
        budget=AgentBudget(max_steps=4, max_tool_calls=2, max_failures=2),
    )
    planner = ScriptedPlanner(
        [
            AgentDecision.tool("test.echo", {"text": "hello"}),
            AgentDecision.finish("done"),
        ]
    )
    report = controller.run("echo once", planner)
    assert report.status == "finished"
    assert journal.verify()[0] == 1
    phases = {item.phase for item in heartbeats}
    assert AgentPhase.ACTING in phases
    assert AgentPhase.CHECKPOINTED in phases
    assert AgentPhase.FINISHED in phases

    class FailingJournal:
        def append(self, record):
            raise OSError("disk unavailable")

    failing_bus = ToolBus()
    failing_bus.register(_echo_tool())
    failing = AgentController(
        failing_bus,
        checkpoint_store=FileCheckpointStore(tmp_path / "failed"),
        audit_journal=FailingJournal(),
        owner_id="test-owner-2",
    )
    blocked_report = failing.run(
        "audit guard",
        ScriptedPlanner(
            [
                AgentDecision.tool("test.echo", {"text": "x"}),
                AgentDecision.finish("must not continue"),
            ]
        ),
    )
    assert blocked_report.status == "recovery_blocked"
    assert "durable audit persistence failed" in blocked_report.message
    checkpoint = failing.checkpoint_store.load(blocked_report.run_id)
    assert checkpoint is not None
    assert checkpoint.pending_call is not None


def test_v2_audit_recovers_completed_pending_call_without_reexecution(tmp_path) -> None:
    calls: list[str] = []

    @dataclass(frozen=True)
    class CountRequest:
        text: str

    @dataclass(frozen=True)
    class CountResponse:
        text: str

    def handler(request: CountRequest, _context) -> CountResponse:
        calls.append(request.text)
        return CountResponse(request.text)

    tool = TypedTool(
        name="test.counted_echo",
        description="Count executions while echoing text.",
        capability=Capability.READ_RUNTIME,
        request_type=CountRequest,
        response_type=CountResponse,
        handler=handler,
    )
    bus = ToolBus()
    bus.register(tool)
    call = ToolCall(
        "recover-result:1",
        "test.counted_echo",
        {"text": "once"},
    )
    result = bus.invoke(call)
    assert result.status is ToolStatus.OK
    assert calls == ["once"]

    journal = HashChainedAuditJournal(
        tmp_path / "audit-v2.jsonl",
        session_id="session-v2",
    )
    journal.append(bus.audit_records[-1], result)
    event = journal.lookup_event(call.call_id)
    assert event is not None
    assert event[1].output == {"text": "once"}

    store = FileCheckpointStore(tmp_path / "checkpoints-v2")
    store.save(
        AgentCheckpoint(
            run_id="recover-result",
            task="continue recovered result",
            next_step=1,
            tool_calls=1,
            failures=0,
            heartbeat_seq=1,
            pending_call={
                "call_id": call.call_id,
                "tool_name": call.tool_name,
                "arguments": dict(call.arguments),
                "step": 1,
            },
        )
    )
    controller = AgentController(
        bus,
        checkpoint_store=store,
        audit_journal=journal,
        owner_id="resume-owner",
        budget=AgentBudget(max_steps=4, max_tool_calls=2, max_failures=2),
    )
    report = controller.run(
        "continue recovered result",
        ScriptedPlanner([AgentDecision.finish("done")]),
        resume_run_id="recover-result",
    )
    assert report.status == "finished"
    assert report.tool_calls == 1
    assert calls == ["once"]
    assert report.trace[0].tool_result is not None
    assert report.trace[0].tool_result.output == {"text": "once"}


def test_resume_rejects_budget_expansion_and_tool_contract_drift(tmp_path) -> None:
    store = FileCheckpointStore(tmp_path / "bound-checkpoints")
    bus = ToolBus()
    bus.register(_echo_tool())
    original = AgentController(
        bus,
        checkpoint_store=store,
        owner_id="original-owner",
        budget=AgentBudget(
            max_steps=3,
            max_tool_calls=2,
            max_failures=2,
            max_observation_chars=2048,
        ),
    )
    store.save(
        AgentCheckpoint(
            run_id="bound-run",
            task="bound resume",
            next_step=1,
            tool_calls=0,
            failures=0,
            heartbeat_seq=0,
            budget=original._budget_snapshot(),
            tool_contract_sha256=original._tool_contract_sha256(),
        )
    )

    expanded = AgentController(
        bus,
        checkpoint_store=store,
        owner_id="expanded-owner",
        budget=AgentBudget(
            max_steps=30,
            max_tool_calls=20,
            max_failures=20,
            max_observation_chars=2048,
        ),
    )
    with pytest.raises(ValueError, match="budget does not match"):
        expanded.run(
            "bound resume",
            ScriptedPlanner([AgentDecision.finish("no")]),
            resume_run_id="bound-run",
        )

    drifted_bus = ToolBus()
    drifted = AgentController(
        drifted_bus,
        checkpoint_store=store,
        owner_id="drifted-owner",
        budget=original.budget,
    )
    with pytest.raises(ValueError, match="contract changed"):
        drifted.run(
            "bound resume",
            ScriptedPlanner([AgentDecision.finish("no")]),
            resume_run_id="bound-run",
        )

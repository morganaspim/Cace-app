from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Mapping, Protocol, Sequence
from uuid import uuid4

from cace_studio.ai.provider import AIProvider
from cace_studio.core.reproducibility import sha256_identity

from .audit import HashChainedAuditJournal
from .contracts import ToolCall, ToolDescriptor, ToolResult, ToolStatus
from .durable_lease import DurableAgentLease, FileAgentLeaseManager
from .operations import FileOperationStore, operation_id_for
from .recovery import (
    AgentCheckpoint,
    AgentHeartbeat,
    AgentLease,
    AgentLeaseManager,
    AgentPhase,
    FileCheckpointStore,
    LeaseUnavailableError,
)
from .tool_bus import ToolBus


@dataclass(frozen=True)
class AgentBudget:
    max_steps: int = 12
    max_tool_calls: int = 24
    max_failures: int = 4
    max_observation_chars: int = 32_768

    def __post_init__(self) -> None:
        for name in ("max_steps", "max_tool_calls", "max_failures", "max_observation_chars"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class AgentDecision:
    action: str
    tool_name: str = ""
    arguments: Mapping[str, Any] | None = None
    message: str = ""

    def __post_init__(self) -> None:
        if self.action not in {"tool", "finish", "abort"}:
            raise ValueError("agent action must be tool, finish, or abort")
        if self.action == "tool" and not self.tool_name:
            raise ValueError("tool action requires tool_name")
        if self.action != "tool" and self.tool_name:
            raise ValueError("non-tool action must not specify tool_name")
        if self.arguments is not None and not isinstance(self.arguments, Mapping):
            raise TypeError("agent tool arguments must be a mapping")

    @classmethod
    def tool(cls, name: str, arguments: Mapping[str, Any] | None = None) -> "AgentDecision":
        return cls("tool", tool_name=name, arguments=arguments or {})

    @classmethod
    def finish(cls, message: str) -> "AgentDecision":
        return cls("finish", message=message)

    @classmethod
    def abort(cls, message: str) -> "AgentDecision":
        return cls("abort", message=message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "tool_name": self.tool_name,
            "arguments": dict(self.arguments or {}),
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AgentDecision":
        if not isinstance(payload, Mapping):
            raise ValueError("agent decision checkpoint value must be an object")
        allowed = {"action", "tool_name", "arguments", "message"}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"agent decision contains unknown fields: {unknown}")
        action = payload.get("action")
        if action == "tool":
            arguments = payload.get("arguments", {})
            if not isinstance(arguments, Mapping):
                raise ValueError("checkpoint tool arguments must be an object")
            return cls.tool(str(payload.get("tool_name", "")), dict(arguments))
        if action == "finish":
            return cls.finish(str(payload.get("message", "")))
        if action == "abort":
            return cls.abort(str(payload.get("message", "")))
        raise ValueError("checkpoint agent action is invalid")


@dataclass(frozen=True)
class AgentTurnContext:
    task: str
    step: int
    tools: tuple[ToolDescriptor, ...]
    observations: tuple[Mapping[str, Any], ...]
    remaining_tool_calls: int
    remaining_failures: int
    perception: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_context_schema": 1,
            "task": self.task,
            "step": self.step,
            "tools": [tool.to_dict() for tool in self.tools],
            "observations": [dict(item) for item in self.observations],
            "remaining_tool_calls": self.remaining_tool_calls,
            "remaining_failures": self.remaining_failures,
            "perception": dict(self.perception) if self.perception is not None else None,
            "proof_effect": "none",
            "promotion_authority": False,
        }


class AgentPlanner(Protocol):
    def decide(self, context: AgentTurnContext) -> AgentDecision:
        ...


@dataclass(frozen=True)
class AgentTraceEntry:
    step: int
    decision: AgentDecision
    tool_result: ToolResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "decision": self.decision.to_dict(),
            "tool_result": self.tool_result.to_dict() if self.tool_result else None,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AgentTraceEntry":
        if not isinstance(payload, Mapping):
            raise ValueError("agent trace checkpoint value must be an object")
        allowed = {"step", "decision", "tool_result"}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"agent trace contains unknown fields: {unknown}")
        decision_raw = payload.get("decision")
        if not isinstance(decision_raw, Mapping):
            raise ValueError("agent trace decision must be an object")
        result_raw = payload.get("tool_result")
        result = None
        if result_raw is not None:
            if not isinstance(result_raw, Mapping):
                raise ValueError("agent trace tool_result must be an object or null")
            if result_raw.get("tool_result_schema") != 1:
                raise ValueError("unsupported tool_result checkpoint schema")
            output = result_raw.get("output")
            if output is not None and not isinstance(output, Mapping):
                raise ValueError("checkpoint tool_result output must be an object or null")
            result = ToolResult(
                call_id=str(result_raw.get("call_id", "")),
                tool_name=str(result_raw.get("tool_name", "")),
                status=ToolStatus(str(result_raw.get("status", ""))),
                output=dict(output) if output is not None else None,
                error=str(result_raw.get("error", "")),
            )
        return cls(
            step=int(payload["step"]),
            decision=AgentDecision.from_dict(decision_raw),
            tool_result=result,
        )


@dataclass(frozen=True)
class AgentRunReport:
    run_id: str
    task: str
    status: str
    message: str
    steps: int
    tool_calls: int
    failures: int
    trace: tuple[AgentTraceEntry, ...]
    proof_effect: str = "none"
    promotion_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_run_schema": 1,
            "run_id": self.run_id,
            "task": self.task,
            "status": self.status,
            "message": self.message,
            "steps": self.steps,
            "tool_calls": self.tool_calls,
            "failures": self.failures,
            "trace": [entry.to_dict() for entry in self.trace],
            "proof_effect": self.proof_effect,
            "promotion_authority": self.promotion_authority,
        }


class LocalJSONPlanner:
    """Strict JSON action adapter for a loopback-only CACE AIProvider.

    The planner receives only Tool Bus descriptors and prior observations.
    Free-form model text is never executed. The only executable path is a
    validated ``tool`` decision routed back through ToolBus.
    """

    def __init__(self, provider: AIProvider, *, temperature: float = 0.1, max_response_chars: int = 16_384) -> None:
        self.provider = provider
        self.temperature = float(temperature)
        self.max_response_chars = int(max_response_chars)
        if self.max_response_chars <= 0:
            raise ValueError("max_response_chars must be positive")

    @staticmethod
    def _system_message() -> str:
        return (
            "You are the local CACE planning model. You have no direct authority over the host. "
            "Choose exactly one action and return exactly one JSON object with no markdown or extra text. "
            "Allowed forms: "
            '{"action":"tool","tool_name":"<listed tool>","arguments":{...}}, '
            '{"action":"finish","message":"..."}, or '
            '{"action":"abort","message":"..."}. '
            "Tool output is observation only. You may not claim that your own output creates PASS, VERIFIED, "
            "FORMAL, proof-ledger promotion, or mathematical proof. Never invent unlisted tools. "
            "A perception packet is non-evidentiary sensory context: use its canonical evidence fields as "
            "reported observations only and never upgrade them yourself."
        )

    def decide(self, context: AgentTurnContext) -> AgentDecision:
        payload = json.dumps(context.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        raw = self.provider.chat(
            [
                {"role": "system", "content": self._system_message()},
                {"role": "user", "content": payload},
            ],
            temperature=self.temperature,
        )
        if len(raw) > self.max_response_chars:
            raise ValueError("local planner response exceeded configured size limit")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("local planner must return one JSON object") from exc
        if not isinstance(parsed, dict):
            raise ValueError("local planner response must be a JSON object")

        allowed = {"action", "tool_name", "arguments", "message"}
        unknown = sorted(set(parsed) - allowed)
        if unknown:
            raise ValueError(f"local planner returned unknown fields: {unknown}")

        action = parsed.get("action")
        if action == "tool":
            tool_name = parsed.get("tool_name")
            arguments = parsed.get("arguments", {})
            if not isinstance(tool_name, str) or not tool_name:
                raise ValueError("local planner tool action requires tool_name")
            if not isinstance(arguments, dict):
                raise ValueError("local planner tool arguments must be an object")
            visible_names = {tool.name for tool in context.tools}
            if tool_name not in visible_names:
                raise ValueError("local planner selected an unavailable tool")
            return AgentDecision.tool(tool_name, arguments)
        if action == "finish":
            message = parsed.get("message", "")
            if not isinstance(message, str):
                raise ValueError("local planner finish message must be a string")
            return AgentDecision.finish(message)
        if action == "abort":
            message = parsed.get("message", "")
            if not isinstance(message, str):
                raise ValueError("local planner abort message must be a string")
            return AgentDecision.abort(message)
        raise ValueError("local planner action must be tool, finish, or abort")


HeartbeatCallback = Callable[[AgentHeartbeat], None]
PerceptionProvider = Callable[[], Mapping[str, Any] | None]


class AgentController:
    """Bounded planner/action/observation runtime over a ToolBus.

    Optional checkpoints support safe resume. If a checkpoint contains a pending
    tool call, automatic replay is forbidden because the prior process may have
    executed the call before it stopped.
    """

    def __init__(
        self,
        tool_bus: ToolBus,
        *,
        budget: AgentBudget | None = None,
        checkpoint_store: FileCheckpointStore | None = None,
        lease_manager: AgentLeaseManager | FileAgentLeaseManager | None = None,
        heartbeat_callback: HeartbeatCallback | None = None,
        perception_provider: PerceptionProvider | None = None,
        audit_journal: HashChainedAuditJournal | None = None,
        owner_id: str | None = None,
        lease_ttl_seconds: float = 30.0,
    ) -> None:
        self.tool_bus = tool_bus
        self.budget = budget or AgentBudget()
        self.checkpoint_store = checkpoint_store
        if lease_manager is not None:
            self.lease_manager = lease_manager
        elif checkpoint_store is not None:
            self.lease_manager = FileAgentLeaseManager(
                checkpoint_store.root / ".leases"
            )
        else:
            self.lease_manager = AgentLeaseManager()
        if checkpoint_store is not None and self.tool_bus.operation_store is None:
            self.tool_bus.set_operation_store(
                FileOperationStore(checkpoint_store.root / ".operations")
            )
        self.heartbeat_callback = heartbeat_callback
        self.perception_provider = perception_provider
        self.audit_journal = audit_journal
        self.owner_id = owner_id or f"controller-{uuid4()}"
        self.lease_ttl_seconds = float(lease_ttl_seconds)
        if self.lease_ttl_seconds <= 0:
            raise ValueError("lease_ttl_seconds must be positive")

    def _budget_snapshot(self) -> dict[str, int]:
        return {
            "max_steps": self.budget.max_steps,
            "max_tool_calls": self.budget.max_tool_calls,
            "max_failures": self.budget.max_failures,
            "max_observation_chars": self.budget.max_observation_chars,
        }

    def _tool_contract_sha256(self) -> str:
        return sha256_identity(
            [descriptor.to_dict() for descriptor in self.tool_bus.descriptors()]
        )

    @staticmethod
    def _bounded_observation(result: ToolResult, max_chars: int) -> Mapping[str, Any]:
        payload = result.to_dict()
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if len(text) <= max_chars:
            return payload
        return {
            "tool_result_schema": 1,
            "call_id": result.call_id,
            "tool_name": result.tool_name,
            "status": result.status.value,
            "output": None,
            "error": "observation omitted from planner context because it exceeded size limit",
            "proof_effect": "none",
            "promotion_authority": False,
        }

    def _heartbeat(
        self,
        *,
        run_id: str,
        heartbeat_seq: int,
        phase: AgentPhase,
        step: int,
        tool_calls: int,
        failures: int,
        lease: AgentLease | DurableAgentLease,
        checkpoint_sha256: str | None = None,
        detail: str = "",
    ) -> int:
        next_seq = heartbeat_seq + 1
        heartbeat = AgentHeartbeat(
            run_id=run_id,
            monotonic_seq=next_seq,
            phase=phase,
            step=max(0, step),
            tool_calls=tool_calls,
            failures=failures,
            lease_id=lease.lease_id,
            lease_generation=lease.generation,
            checkpoint_sha256=checkpoint_sha256,
            detail=detail,
        )
        if self.heartbeat_callback is not None:
            self.heartbeat_callback(heartbeat)
        return next_seq

    def _current_perception(self) -> Mapping[str, Any] | None:
        if self.perception_provider is None:
            return None
        payload = self.perception_provider()
        if payload is None:
            return None
        if not isinstance(payload, Mapping):
            raise TypeError("perception provider must return an object or null")
        packet = dict(payload)
        required = {
            "schema_version",
            "run_id",
            "experiment_id",
            "monotonic_seq",
            "semantic_graph_hash",
            "emitted_at",
            "network_mode",
            "nodes",
            "evidence_authority",
        }
        missing = sorted(required - set(packet))
        unknown = sorted(set(packet) - required)
        if missing:
            raise ValueError(f"perception packet missing required fields: {missing}")
        if unknown:
            raise ValueError(f"perception packet contains unknown fields: {unknown}")
        if packet.get("schema_version") != "cace-agent-perception-v1":
            raise ValueError("unsupported perception packet schema")
        if packet.get("evidence_authority") is not False:
            raise ValueError("perception packet must have evidence_authority=false")
        if not isinstance(packet.get("nodes"), list):
            raise ValueError("perception packet nodes must be an array")
        return packet

    def _save_checkpoint(
        self,
        *,
        run_id: str,
        task: str,
        next_step: int,
        tool_calls: int,
        failures: int,
        heartbeat_seq: int,
        observations: list[Mapping[str, Any]],
        trace: list[AgentTraceEntry],
        pending_call: Mapping[str, Any] | None,
        status: str = "running",
    ) -> str | None:
        if self.checkpoint_store is None:
            return None
        return self.checkpoint_store.save(
            AgentCheckpoint(
                run_id=run_id,
                task=task,
                next_step=next_step,
                tool_calls=tool_calls,
                failures=failures,
                heartbeat_seq=heartbeat_seq,
                budget=self._budget_snapshot(),
                tool_contract_sha256=self._tool_contract_sha256(),
                observations=tuple(dict(item) for item in observations),
                trace=tuple(entry.to_dict() for entry in trace),
                pending_call=dict(pending_call) if pending_call is not None else None,
                status=status,
            )
        )

    @staticmethod
    def _report(
        run_id: str,
        task: str,
        status: str,
        message: str,
        steps: int,
        tool_calls: int,
        failures: int,
        trace: list[AgentTraceEntry],
    ) -> AgentRunReport:
        return AgentRunReport(
            run_id, task, status, message, steps, tool_calls, failures, tuple(trace)
        )

    def run(
        self,
        task: str,
        planner: AgentPlanner,
        *,
        resume_run_id: str | None = None,
    ) -> AgentRunReport:
        if not isinstance(task, str) or not task.strip():
            raise ValueError("agent task must be a non-empty string")
        task = task.strip()
        if resume_run_id is not None and self.checkpoint_store is None:
            raise ValueError("resume_run_id requires a checkpoint_store")

        run_id = resume_run_id or str(uuid4())
        start_step = 1
        trace: list[AgentTraceEntry] = []
        observations: list[Mapping[str, Any]] = []
        tool_calls = 0
        failures = 0
        heartbeat_seq = 0

        if resume_run_id is not None:
            checkpoint = self.checkpoint_store.load(run_id) if self.checkpoint_store else None
            if checkpoint is None:
                raise ValueError(f"no checkpoint exists for run {run_id!r}")
            if checkpoint.task != task:
                raise ValueError("resume task does not match checkpoint task")
            if checkpoint.status != "running":
                raise ValueError(f"checkpoint is not resumable: status={checkpoint.status}")
            if (
                checkpoint.budget is not None
                and dict(checkpoint.budget) != self._budget_snapshot()
            ):
                raise ValueError("resume budget does not match checkpoint budget")
            if (
                checkpoint.tool_contract_sha256 is not None
                and checkpoint.tool_contract_sha256 != self._tool_contract_sha256()
            ):
                raise ValueError("Tool Bus contract changed since checkpoint")
            start_step = checkpoint.next_step
            tool_calls = checkpoint.tool_calls
            failures = checkpoint.failures
            heartbeat_seq = checkpoint.heartbeat_seq
            observations = [dict(item) for item in checkpoint.observations]
            trace = [AgentTraceEntry.from_dict(item) for item in checkpoint.trace]
            if checkpoint.pending_call is not None:
                pending = dict(checkpoint.pending_call)
                pending_tool = str(pending.get("tool_name", ""))
                pending_arguments = pending.get("arguments", {})
                pending_operation_id = pending.get("operation_id")
                recovered_result: ToolResult | None = None
                recovery_error = ""

                if not isinstance(pending_arguments, Mapping):
                    recovery_error = "pending tool arguments are malformed"

                if (
                    not recovery_error
                    and isinstance(pending_operation_id, str)
                    and pending_operation_id
                    and self.tool_bus.operation_store is not None
                ):
                    try:
                        operation = self.tool_bus.operation_store.load(
                            pending_operation_id
                        )
                        if operation is not None and operation.state == "committed":
                            expected_input = sha256_identity(dict(pending_arguments))
                            if (
                                operation.tool_name != pending_tool
                                or operation.input_sha256 != expected_input
                            ):
                                recovery_error = (
                                    "durable operation result does not match the "
                                    "pending tool call"
                                )
                            else:
                                recovered_result = (
                                    self.tool_bus.operation_store.lookup_result(
                                        pending_operation_id
                                    )
                                )
                    except Exception as exc:
                        recovery_error = (
                            "durable operation verification failed during recovery: "
                            f"{type(exc).__name__}: {exc}"
                        )

                recovered_event = None
                if (
                    recovered_result is None
                    and not recovery_error
                    and self.audit_journal is not None
                ):
                    try:
                        recovered_event = self.audit_journal.lookup_event(
                            str(pending.get("call_id", ""))
                        )
                    except Exception as exc:
                        recovery_error = (
                            "durable audit verification failed during recovery: "
                            f"{type(exc).__name__}: {exc}"
                        )

                if (
                    recovered_result is None
                    and recovered_event is not None
                    and not recovery_error
                ):
                    record, audit_result = recovered_event
                    expected_input = sha256_identity(dict(pending_arguments))
                    if (
                        record.tool_name != pending_tool
                        or record.input_sha256 != expected_input
                    ):
                        recovery_error = (
                            "durable audit result does not match the pending tool call"
                        )
                    elif audit_result.status is ToolStatus.RECOVERY_BLOCKED:
                        recovery_error = (
                            "durable audit records an unresolved operation; "
                            "automatic continuation remains blocked"
                        )
                    else:
                        recovered_result = audit_result

                if recovered_result is not None and not recovery_error:
                    recovered_step = int(
                        pending.get("step", max(1, start_step))
                    )
                    recovered_decision = AgentDecision.tool(
                        pending_tool,
                        dict(pending_arguments),
                    )
                    trace.append(
                        AgentTraceEntry(
                            recovered_step,
                            recovered_decision,
                            recovered_result,
                        )
                    )
                    observations.append(
                        self._bounded_observation(
                            recovered_result,
                            self.budget.max_observation_chars,
                        )
                    )
                    if recovered_result.status is not ToolStatus.OK:
                        failures += 1
                    start_step = recovered_step + 1

                if recovered_result is None or recovery_error:
                    lease = self.lease_manager.acquire(
                        run_id, self.owner_id, ttl_seconds=self.lease_ttl_seconds
                    )
                    try:
                        detail = recovery_error or (
                            "prior process stopped with a pending tool call and no "
                            "recoverable typed result; automatic replay is forbidden"
                        )
                        heartbeat_seq = self._heartbeat(
                            run_id=run_id,
                            heartbeat_seq=heartbeat_seq,
                            phase=AgentPhase.RECOVERY_BLOCKED,
                            step=max(0, start_step - 1),
                            tool_calls=tool_calls,
                            failures=failures,
                            lease=lease,
                            detail=detail,
                        )
                        self._save_checkpoint(
                            run_id=run_id,
                            task=task,
                            next_step=start_step,
                            tool_calls=tool_calls,
                            failures=failures,
                            heartbeat_seq=heartbeat_seq,
                            observations=observations,
                            trace=trace,
                            pending_call=checkpoint.pending_call,
                            status="recovery_blocked",
                        )
                        return self._report(
                            run_id,
                            task,
                            "recovery_blocked",
                            detail,
                            max(0, start_step - 1),
                            tool_calls,
                            failures,
                            trace,
                        )
                    finally:
                        self.lease_manager.release(lease)


        lease = self.lease_manager.acquire(
            run_id, self.owner_id, ttl_seconds=self.lease_ttl_seconds
        )
        try:
            heartbeat_seq = self._heartbeat(
                run_id=run_id,
                heartbeat_seq=heartbeat_seq,
                phase=AgentPhase.STARTING,
                step=max(0, start_step - 1),
                tool_calls=tool_calls,
                failures=failures,
                lease=lease,
                detail="resuming durable checkpoint" if resume_run_id else "starting new local-agent run",
            )
            checkpoint_sha = self._save_checkpoint(
                run_id=run_id,
                task=task,
                next_step=start_step,
                tool_calls=tool_calls,
                failures=failures,
                heartbeat_seq=heartbeat_seq,
                observations=observations,
                trace=trace,
                pending_call=None,
            )

            for step in range(start_step, self.budget.max_steps + 1):
                lease = self.lease_manager.renew(lease)
                heartbeat_seq = self._heartbeat(
                    run_id=run_id,
                    heartbeat_seq=heartbeat_seq,
                    phase=AgentPhase.PLANNING,
                    step=step,
                    tool_calls=tool_calls,
                    failures=failures,
                    lease=lease,
                    checkpoint_sha256=checkpoint_sha,
                )
                checkpoint_sha = self._save_checkpoint(
                    run_id=run_id,
                    task=task,
                    next_step=step,
                    tool_calls=tool_calls,
                    failures=failures,
                    heartbeat_seq=heartbeat_seq,
                    observations=observations,
                    trace=trace,
                    pending_call=None,
                )
                try:
                    perception = self._current_perception()
                except Exception as exc:
                    failures += 1
                    message = f"perception failure: {type(exc).__name__}: {exc}"
                    checkpoint_sha = self._save_checkpoint(
                        run_id=run_id,
                        task=task,
                        next_step=step,
                        tool_calls=tool_calls,
                        failures=failures,
                        heartbeat_seq=heartbeat_seq,
                        observations=observations,
                        trace=trace,
                        pending_call=None,
                        status="aborted",
                    )
                    self._heartbeat(
                        run_id=run_id,
                        heartbeat_seq=heartbeat_seq,
                        phase=AgentPhase.ABORTED,
                        step=max(0, step - 1),
                        tool_calls=tool_calls,
                        failures=failures,
                        lease=lease,
                        checkpoint_sha256=checkpoint_sha,
                        detail=message,
                    )
                    return self._report(
                        run_id, task, "aborted", message, step - 1, tool_calls, failures, trace
                    )

                context = AgentTurnContext(
                    task=task,
                    step=step,
                    tools=self.tool_bus.descriptors(),
                    observations=tuple(observations),
                    remaining_tool_calls=max(0, self.budget.max_tool_calls - tool_calls),
                    remaining_failures=max(0, self.budget.max_failures - failures),
                    perception=perception,
                )
                try:
                    decision = planner.decide(context)
                except Exception as exc:
                    failures += 1
                    message = f"planner failure: {type(exc).__name__}: {exc}"
                    checkpoint_sha = self._save_checkpoint(
                        run_id=run_id,
                        task=task,
                        next_step=step,
                        tool_calls=tool_calls,
                        failures=failures,
                        heartbeat_seq=heartbeat_seq,
                        observations=observations,
                        trace=trace,
                        pending_call=None,
                        status="aborted",
                    )
                    self._heartbeat(
                        run_id=run_id,
                        heartbeat_seq=heartbeat_seq,
                        phase=AgentPhase.ABORTED,
                        step=max(0, step - 1),
                        tool_calls=tool_calls,
                        failures=failures,
                        lease=lease,
                        checkpoint_sha256=checkpoint_sha,
                        detail=message,
                    )
                    return self._report(
                        run_id, task, "aborted", message, step - 1, tool_calls, failures, trace
                    )

                if decision.action in {"finish", "abort"}:
                    trace.append(AgentTraceEntry(step, decision))
                    status = "finished" if decision.action == "finish" else "aborted"
                    phase = AgentPhase.FINISHED if decision.action == "finish" else AgentPhase.ABORTED
                    checkpoint_sha = self._save_checkpoint(
                        run_id=run_id,
                        task=task,
                        next_step=step + 1,
                        tool_calls=tool_calls,
                        failures=failures,
                        heartbeat_seq=heartbeat_seq,
                        observations=observations,
                        trace=trace,
                        pending_call=None,
                        status=status,
                    )
                    self._heartbeat(
                        run_id=run_id,
                        heartbeat_seq=heartbeat_seq,
                        phase=phase,
                        step=step,
                        tool_calls=tool_calls,
                        failures=failures,
                        lease=lease,
                        checkpoint_sha256=checkpoint_sha,
                        detail=decision.message,
                    )
                    return self._report(
                        run_id, task, status, decision.message, step, tool_calls, failures, trace
                    )

                if tool_calls >= self.budget.max_tool_calls:
                    checkpoint_sha = self._save_checkpoint(
                        run_id=run_id,
                        task=task,
                        next_step=step,
                        tool_calls=tool_calls,
                        failures=failures,
                        heartbeat_seq=heartbeat_seq,
                        observations=observations,
                        trace=trace,
                        pending_call=None,
                        status="budget_exhausted",
                    )
                    self._heartbeat(
                        run_id=run_id,
                        heartbeat_seq=heartbeat_seq,
                        phase=AgentPhase.BUDGET_EXHAUSTED,
                        step=max(0, step - 1),
                        tool_calls=tool_calls,
                        failures=failures,
                        lease=lease,
                        checkpoint_sha256=checkpoint_sha,
                        detail="tool-call budget exhausted",
                    )
                    return self._report(
                        run_id, task, "budget_exhausted", "tool-call budget exhausted",
                        step - 1, tool_calls, failures, trace
                    )

                # Revalidate ownership immediately before an executable action.
                # This prevents slow planner/model latency from carrying an expired
                # lease into a Tool Bus invocation.
                lease = self.lease_manager.renew(lease)
                tool_calls += 1
                arguments = dict(decision.arguments or {})
                operation_id = operation_id_for(
                    run_id=run_id,
                    ordinal=tool_calls,
                    tool_name=decision.tool_name,
                    arguments=arguments,
                )
                call = ToolCall(
                    call_id=f"{run_id}:{tool_calls}",
                    tool_name=decision.tool_name,
                    arguments=arguments,
                    operation_id=operation_id,
                    lease_id=lease.lease_id,
                    lease_generation=lease.generation,
                )
                pending_call = {
                    "call_id": call.call_id,
                    "operation_id": operation_id,
                    "tool_name": call.tool_name,
                    "arguments": dict(call.arguments),
                    "lease_id": lease.lease_id,
                    "lease_generation": lease.generation,
                    "step": step,
                }
                checkpoint_sha = self._save_checkpoint(
                    run_id=run_id,
                    task=task,
                    next_step=step,
                    tool_calls=tool_calls,
                    failures=failures,
                    heartbeat_seq=heartbeat_seq,
                    observations=observations,
                    trace=trace,
                    pending_call=pending_call,
                )
                heartbeat_seq = self._heartbeat(
                    run_id=run_id,
                    heartbeat_seq=heartbeat_seq,
                    phase=AgentPhase.ACTING,
                    step=step,
                    tool_calls=tool_calls,
                    failures=failures,
                    lease=lease,
                    checkpoint_sha256=checkpoint_sha,
                    detail=f"calling {call.tool_name}",
                )
                checkpoint_sha = self._save_checkpoint(
                    run_id=run_id,
                    task=task,
                    next_step=step,
                    tool_calls=tool_calls,
                    failures=failures,
                    heartbeat_seq=heartbeat_seq,
                    observations=observations,
                    trace=trace,
                    pending_call=pending_call,
                )

                result = self.tool_bus.invoke(call)
                trace.append(AgentTraceEntry(step, decision, result))

                if self.audit_journal is not None:
                    try:
                        if not self.tool_bus.audit_records:
                            raise RuntimeError("Tool Bus returned without an audit record")
                        latest_audit = self.tool_bus.audit_records[-1]
                        if latest_audit.call_id != call.call_id:
                            raise RuntimeError("Tool Bus audit tail does not match completed call")
                        self.audit_journal.append(latest_audit, result)
                    except Exception as exc:
                        failures += 1
                        message = (
                            "tool completed but durable audit persistence failed; "
                            f"automatic continuation is blocked: {type(exc).__name__}: {exc}"
                        )
                        checkpoint_sha = self._save_checkpoint(
                            run_id=run_id,
                            task=task,
                            next_step=step,
                            tool_calls=tool_calls,
                            failures=failures,
                            heartbeat_seq=heartbeat_seq,
                            observations=observations,
                            trace=trace,
                            pending_call=pending_call,
                            status="recovery_blocked",
                        )
                        self._heartbeat(
                            run_id=run_id,
                            heartbeat_seq=heartbeat_seq,
                            phase=AgentPhase.RECOVERY_BLOCKED,
                            step=step,
                            tool_calls=tool_calls,
                            failures=failures,
                            lease=lease,
                            checkpoint_sha256=checkpoint_sha,
                            detail=message,
                        )
                        return self._report(
                            run_id, task, "recovery_blocked", message,
                            step, tool_calls, failures, trace
                        )

                observations.append(
                    self._bounded_observation(result, self.budget.max_observation_chars)
                )
                if result.status is ToolStatus.RECOVERY_BLOCKED:
                    failures += 1
                    message = result.error or (
                        "operation entered an uncertain durable state; "
                        "automatic continuation is blocked"
                    )
                    checkpoint_sha = self._save_checkpoint(
                        run_id=run_id,
                        task=task,
                        next_step=step,
                        tool_calls=tool_calls,
                        failures=failures,
                        heartbeat_seq=heartbeat_seq,
                        observations=observations,
                        trace=trace,
                        pending_call=pending_call,
                        status="recovery_blocked",
                    )
                    self._heartbeat(
                        run_id=run_id,
                        heartbeat_seq=heartbeat_seq,
                        phase=AgentPhase.RECOVERY_BLOCKED,
                        step=step,
                        tool_calls=tool_calls,
                        failures=failures,
                        lease=lease,
                        checkpoint_sha256=checkpoint_sha,
                        detail=message,
                    )
                    return self._report(
                        run_id,
                        task,
                        "recovery_blocked",
                        message,
                        step,
                        tool_calls,
                        failures,
                        trace,
                    )
                if result.status is not ToolStatus.OK:
                    failures += 1

                heartbeat_seq = self._heartbeat(
                    run_id=run_id,
                    heartbeat_seq=heartbeat_seq,
                    phase=AgentPhase.CHECKPOINTED,
                    step=step,
                    tool_calls=tool_calls,
                    failures=failures,
                    lease=lease,
                    checkpoint_sha256=checkpoint_sha,
                    detail=f"completed {call.tool_name} with status {result.status.value}",
                )
                checkpoint_sha = self._save_checkpoint(
                    run_id=run_id,
                    task=task,
                    next_step=step + 1,
                    tool_calls=tool_calls,
                    failures=failures,
                    heartbeat_seq=heartbeat_seq,
                    observations=observations,
                    trace=trace,
                    pending_call=None,
                )

                if failures >= self.budget.max_failures:
                    checkpoint_sha = self._save_checkpoint(
                        run_id=run_id,
                        task=task,
                        next_step=step + 1,
                        tool_calls=tool_calls,
                        failures=failures,
                        heartbeat_seq=heartbeat_seq,
                        observations=observations,
                        trace=trace,
                        pending_call=None,
                        status="aborted",
                    )
                    self._heartbeat(
                        run_id=run_id,
                        heartbeat_seq=heartbeat_seq,
                        phase=AgentPhase.ABORTED,
                        step=step,
                        tool_calls=tool_calls,
                        failures=failures,
                        lease=lease,
                        checkpoint_sha256=checkpoint_sha,
                        detail="tool failure budget exhausted",
                    )
                    return self._report(
                        run_id, task, "aborted", "tool failure budget exhausted",
                        step, tool_calls, failures, trace
                    )

            checkpoint_sha = self._save_checkpoint(
                run_id=run_id,
                task=task,
                next_step=self.budget.max_steps + 1,
                tool_calls=tool_calls,
                failures=failures,
                heartbeat_seq=heartbeat_seq,
                observations=observations,
                trace=trace,
                pending_call=None,
                status="budget_exhausted",
            )
            self._heartbeat(
                run_id=run_id,
                heartbeat_seq=heartbeat_seq,
                phase=AgentPhase.BUDGET_EXHAUSTED,
                step=self.budget.max_steps,
                tool_calls=tool_calls,
                failures=failures,
                lease=lease,
                checkpoint_sha256=checkpoint_sha,
                detail="step budget exhausted",
            )
            return self._report(
                run_id, task, "budget_exhausted", "step budget exhausted",
                self.budget.max_steps, tool_calls, failures, trace
            )
        except LeaseUnavailableError as exc:
            return self._report(
                run_id, task, "aborted", f"lease failure: {exc}",
                max(0, start_step - 1), tool_calls, failures + 1, trace
            )
        finally:
            self.lease_manager.release(lease)

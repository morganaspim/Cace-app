from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Protocol, Sequence
from uuid import uuid4

from cace_studio.ai.provider import AIProvider

from .contracts import ToolCall, ToolDescriptor, ToolResult, ToolStatus
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


@dataclass(frozen=True)
class AgentTurnContext:
    task: str
    step: int
    tools: tuple[ToolDescriptor, ...]
    observations: tuple[Mapping[str, Any], ...]
    remaining_tool_calls: int
    remaining_failures: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_context_schema": 1,
            "task": self.task,
            "step": self.step,
            "tools": [tool.to_dict() for tool in self.tools],
            "observations": [dict(item) for item in self.observations],
            "remaining_tool_calls": self.remaining_tool_calls,
            "remaining_failures": self.remaining_failures,
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
            "decision": {
                "action": self.decision.action,
                "tool_name": self.decision.tool_name,
                "arguments": dict(self.decision.arguments or {}),
                "message": self.decision.message,
            },
            "tool_result": self.tool_result.to_dict() if self.tool_result else None,
        }


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
            "FORMAL, proof-ledger promotion, or mathematical proof. Never invent unlisted tools."
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


class AgentController:
    """Bounded planner/action/observation runtime over a ToolBus."""

    def __init__(self, tool_bus: ToolBus, *, budget: AgentBudget | None = None) -> None:
        self.tool_bus = tool_bus
        self.budget = budget or AgentBudget()

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

    def run(self, task: str, planner: AgentPlanner) -> AgentRunReport:
        if not isinstance(task, str) or not task.strip():
            raise ValueError("agent task must be a non-empty string")

        run_id = str(uuid4())
        trace: list[AgentTraceEntry] = []
        observations: list[Mapping[str, Any]] = []
        tool_calls = 0
        failures = 0

        for step in range(1, self.budget.max_steps + 1):
            context = AgentTurnContext(
                task=task.strip(),
                step=step,
                tools=self.tool_bus.descriptors(),
                observations=tuple(observations),
                remaining_tool_calls=max(0, self.budget.max_tool_calls - tool_calls),
                remaining_failures=max(0, self.budget.max_failures - failures),
            )
            try:
                decision = planner.decide(context)
            except Exception as exc:
                message = f"planner failure: {type(exc).__name__}: {exc}"
                return AgentRunReport(
                    run_id, task.strip(), "aborted", message, step - 1, tool_calls, failures + 1, tuple(trace)
                )

            if decision.action == "finish":
                trace.append(AgentTraceEntry(step, decision))
                return AgentRunReport(
                    run_id, task.strip(), "finished", decision.message, step, tool_calls, failures, tuple(trace)
                )

            if decision.action == "abort":
                trace.append(AgentTraceEntry(step, decision))
                return AgentRunReport(
                    run_id, task.strip(), "aborted", decision.message, step, tool_calls, failures, tuple(trace)
                )

            if tool_calls >= self.budget.max_tool_calls:
                return AgentRunReport(
                    run_id,
                    task.strip(),
                    "budget_exhausted",
                    "tool-call budget exhausted",
                    step - 1,
                    tool_calls,
                    failures,
                    tuple(trace),
                )

            tool_calls += 1
            call = ToolCall(
                call_id=f"{run_id}:{tool_calls}",
                tool_name=decision.tool_name,
                arguments=decision.arguments or {},
            )
            result = self.tool_bus.invoke(call)
            trace.append(AgentTraceEntry(step, decision, result))
            observations.append(self._bounded_observation(result, self.budget.max_observation_chars))

            if result.status is not ToolStatus.OK:
                failures += 1
                if failures >= self.budget.max_failures:
                    return AgentRunReport(
                        run_id,
                        task.strip(),
                        "aborted",
                        "tool failure budget exhausted",
                        step,
                        tool_calls,
                        failures,
                        tuple(trace),
                    )

        return AgentRunReport(
            run_id,
            task.strip(),
            "budget_exhausted",
            "step budget exhausted",
            self.budget.max_steps,
            tool_calls,
            failures,
            tuple(trace),
        )

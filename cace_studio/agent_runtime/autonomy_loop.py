from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4

from cace_studio.ai.provider import AIProvider
from cace_studio.core.executor import GraphExecutor, RunResult
from cace_studio.core.graph import Experiment
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.reproducibility import experiment_fingerprint, sha256_identity

from .canvas_plan import (
    CanvasPlanExecuteRequest,
    CanvasPlanPreviewRequest,
    CanvasPlanRuntime,
    FileCanvasPlanStore,
)
from .contracts import (
    Capability,
    ToolCall,
    ToolContext,
    ToolDescriptor,
    ToolPreconditionError,
    TypedTool,
    decode_dataclass,
)
from .durability import (
    CrossProcessFileLock,
    atomic_write_json,
    hashed_envelope,
    validate_hashed_envelope,
)
from .perception import AgentNetworkMode, AgentPerceptionTracker
from .tool_bus import ApprovalCallback, ToolBus
from .workspace_store import FileExperimentWorkspace


class AutonomyLoopError(ToolPreconditionError):
    pass


class AutonomyStage(str, Enum):
    WAITING_PLAN_APPROVAL = "WAITING_PLAN_APPROVAL"
    FINISHED = "FINISHED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AutonomyLoopBudget:
    max_cycles: int = 3
    max_science_runs: int = 3
    max_replans: int = 2
    max_plan_steps_per_cycle: int = 20

    def __post_init__(self) -> None:
        for name in (
            "max_cycles",
            "max_science_runs",
            "max_plan_steps_per_cycle",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if (
            not isinstance(self.max_replans, int)
            or isinstance(self.max_replans, bool)
            or self.max_replans < 0
        ):
            raise ValueError("max_replans must be a non-negative integer")

    def to_dict(self) -> dict[str, int]:
        return {
            "max_cycles": self.max_cycles,
            "max_science_runs": self.max_science_runs,
            "max_replans": self.max_replans,
            "max_plan_steps_per_cycle": self.max_plan_steps_per_cycle,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutonomyLoopBudget":
        return cls(
            max_cycles=int(payload["max_cycles"]),
            max_science_runs=int(payload["max_science_runs"]),
            max_replans=int(payload["max_replans"]),
            max_plan_steps_per_cycle=int(payload["max_plan_steps_per_cycle"]),
        )


@dataclass(frozen=True)
class AutonomyRunSpec:
    target_node_ids: tuple[str, ...] = ()
    external_inputs: dict[str, dict[str, Any]] | None = None
    seed: int = 0

    def __post_init__(self) -> None:
        if len(set(self.target_node_ids)) != len(self.target_node_ids):
            raise ValueError("autonomy target_node_ids must be unique")
        if self.external_inputs is not None and not isinstance(
            self.external_inputs, Mapping
        ):
            raise TypeError("autonomy external_inputs must be an object or null")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_node_ids": list(self.target_node_ids),
            "external_inputs": {
                str(node_id): dict(values)
                for node_id, values in dict(self.external_inputs or {}).items()
            },
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutonomyRunSpec":
        targets = payload.get("target_node_ids", [])
        inputs = payload.get("external_inputs", {})
        if not isinstance(targets, list):
            raise ValueError("autonomy target_node_ids must be an array")
        if not isinstance(inputs, Mapping):
            raise ValueError("autonomy external_inputs must be an object")
        malformed = [
            str(node_id)
            for node_id, values in inputs.items()
            if not isinstance(values, Mapping)
        ]
        if malformed:
            raise ValueError(
                f"autonomy external_inputs node values must be objects: {sorted(malformed)}"
            )
        return cls(
            target_node_ids=tuple(str(item) for item in targets),
            external_inputs={
                str(node_id): dict(values)
                for node_id, values in inputs.items()
            },
            seed=int(payload.get("seed", 0)),
        )


@dataclass(frozen=True)
class AutonomyRunSummary:
    run_id: str
    completed: bool
    interruption_reason: str
    run_scope: str
    semantic_experiment_sha256: str
    source_semantic_experiment_sha256: str
    execution_scope_sha256: str
    all_verifiers_passed: bool
    node_output_ports: Mapping[str, tuple[str, ...]]
    verification_states: Mapping[str, tuple[str, ...]]
    public_resolution_claim_allowed: bool
    proof_effect: str = "none"
    promotion_authority: bool = False

    @classmethod
    def from_run_result(cls, result: RunResult) -> "AutonomyRunSummary":
        return cls(
            run_id=result.run_id,
            completed=result.completed,
            interruption_reason=result.interruption_reason,
            run_scope=result.run_scope,
            semantic_experiment_sha256=result.semantic_experiment_sha256,
            source_semantic_experiment_sha256=result.source_semantic_experiment_sha256,
            execution_scope_sha256=result.execution_scope_sha256,
            all_verifiers_passed=result.all_verifiers_passed,
            node_output_ports={
                node_id: tuple(sorted(outputs))
                for node_id, outputs in result.outputs.items()
            },
            verification_states={
                node_id: tuple(record.state.value for record in records)
                for node_id, records in result.verification.items()
            },
            public_resolution_claim_allowed=result.any_public_resolution_claim_allowed,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "completed": self.completed,
            "interruption_reason": self.interruption_reason,
            "run_scope": self.run_scope,
            "semantic_experiment_sha256": self.semantic_experiment_sha256,
            "source_semantic_experiment_sha256": self.source_semantic_experiment_sha256,
            "execution_scope_sha256": self.execution_scope_sha256,
            "all_verifiers_passed": self.all_verifiers_passed,
            "node_output_ports": {
                key: list(value) for key, value in self.node_output_ports.items()
            },
            "verification_states": {
                key: list(value) for key, value in self.verification_states.items()
            },
            "public_resolution_claim_allowed": self.public_resolution_claim_allowed,
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutonomyRunSummary":
        outputs = payload.get("node_output_ports", {})
        states = payload.get("verification_states", {})
        if not isinstance(outputs, Mapping) or not isinstance(states, Mapping):
            raise ValueError("autonomy run summary maps are malformed")
        if payload.get("proof_effect", "none") != "none" or bool(
            payload.get("promotion_authority", False)
        ):
            raise ValueError("autonomy run summary cannot carry proof authority")
        return cls(
            run_id=str(payload["run_id"]),
            completed=bool(payload["completed"]),
            interruption_reason=str(payload.get("interruption_reason", "")),
            run_scope=str(payload["run_scope"]),
            semantic_experiment_sha256=str(payload["semantic_experiment_sha256"]),
            source_semantic_experiment_sha256=str(
                payload["source_semantic_experiment_sha256"]
            ),
            execution_scope_sha256=str(payload["execution_scope_sha256"]),
            all_verifiers_passed=bool(payload["all_verifiers_passed"]),
            node_output_ports={
                str(key): tuple(str(item) for item in value)
                for key, value in outputs.items()
            },
            verification_states={
                str(key): tuple(str(item) for item in value)
                for key, value in states.items()
            },
            public_resolution_claim_allowed=bool(
                payload["public_resolution_claim_allowed"]
            ),
        )


@dataclass(frozen=True)
class AutonomyReplanContext:
    session_id: str
    objective: str
    cycle_index: int
    run_summary: Mapping[str, Any]
    perception: Mapping[str, Any]
    workspace_id: str
    workspace_version: int
    semantic_experiment_sha256: str
    full_experiment_sha256: str
    remaining_cycles: int
    remaining_science_runs: int
    remaining_replans: int
    proof_effect: str = "none"
    promotion_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "autonomy_replan_context_schema": 1,
            "session_id": self.session_id,
            "objective": self.objective,
            "cycle_index": self.cycle_index,
            "run_summary": dict(self.run_summary),
            "perception": dict(self.perception),
            "workspace_id": self.workspace_id,
            "workspace_version": self.workspace_version,
            "semantic_experiment_sha256": self.semantic_experiment_sha256,
            "full_experiment_sha256": self.full_experiment_sha256,
            "remaining_cycles": self.remaining_cycles,
            "remaining_science_runs": self.remaining_science_runs,
            "remaining_replans": self.remaining_replans,
            "proof_effect": "none",
            "promotion_authority": False,
        }


ReplanProvider = Callable[
    [AutonomyReplanContext], CanvasPlanPreviewRequest | None
]


class LocalJSONReplanProvider:
    """Strict loopback-AI adapter for autonomy follow-up plan proposals.

    The model may only finish or return a typed canvas-plan preview request.
    Its output is never executed directly and carries no proof authority.
    """

    def __init__(
        self,
        provider: AIProvider,
        *,
        temperature: float = 0.1,
        max_response_chars: int = 32_768,
    ) -> None:
        self.provider = provider
        self.temperature = float(temperature)
        self.max_response_chars = int(max_response_chars)
        if self.max_response_chars <= 0:
            raise ValueError("max_response_chars must be positive")

    @staticmethod
    def _system_message() -> str:
        return (
            "You are CACE's local replan model. Return exactly one JSON object "
            "with no markdown or extra text. Allowed forms are "
            '{"action":"finish"} or '
            '{"action":"replan","steps":[...]}. '
            "Each replan step must use the typed canvas operation contract already "
            "described in the context. You cannot execute tools, mutate the workspace, "
            "grant approval, create verification evidence, claim PASS/VERIFIED/FORMAL, "
            "or promote proof state. Perception and verification summaries are "
            "observations only; do not upgrade their authority."
        )

    def __call__(
        self,
        context: AutonomyReplanContext,
    ) -> CanvasPlanPreviewRequest | None:
        payload = json.dumps(
            context.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        raw = self.provider.chat(
            [
                {"role": "system", "content": self._system_message()},
                {"role": "user", "content": payload},
            ],
            temperature=self.temperature,
        )
        if len(raw) > self.max_response_chars:
            raise ValueError("local replan response exceeded configured size limit")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("local replan provider must return one JSON object") from exc
        if not isinstance(parsed, dict):
            raise ValueError("local replan provider response must be an object")
        allowed = {"action", "steps"}
        unknown = sorted(set(parsed) - allowed)
        if unknown:
            raise ValueError(
                f"local replan provider returned unknown fields: {unknown}"
            )
        action = parsed.get("action")
        if action == "finish":
            if "steps" in parsed:
                raise ValueError("finish response must not include steps")
            return None
        if action != "replan":
            raise ValueError("local replan action must be finish or replan")
        if "steps" not in parsed:
            raise ValueError("replan response requires steps")
        return decode_dataclass(
            CanvasPlanPreviewRequest,
            {"steps": parsed["steps"]},
        )


@dataclass(frozen=True)
class AutonomyAdvanceRequest:
    session_id: str
    plan_id: str

    def __post_init__(self) -> None:
        if not self.session_id or len(self.session_id) > 128:
            raise ValueError("autonomy session_id must be non-empty and bounded")
        if (
            len(self.plan_id) != 64
            or any(ch not in "0123456789abcdef" for ch in self.plan_id)
        ):
            raise ValueError("autonomy plan_id must be a lowercase SHA-256 identity")


@dataclass(frozen=True)
class AutonomyInspectRequest:
    session_id: str


@dataclass(frozen=True)
class AutonomyAdvanceResponse:
    session_id: str
    operation_id: str
    cycle_index: int
    executed_plan_id: str
    workspace_id: str
    workspace_version: int
    science_run_id: str
    science_completed: bool
    all_verifiers_passed: bool
    perception: dict[str, Any]
    next_plan_id: str
    stage: str
    cycles_remaining: int
    science_runs_remaining: int
    replans_remaining: int
    proof_effect: str = "none"
    promotion_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "operation_id": self.operation_id,
            "cycle_index": self.cycle_index,
            "executed_plan_id": self.executed_plan_id,
            "workspace_id": self.workspace_id,
            "workspace_version": self.workspace_version,
            "science_run_id": self.science_run_id,
            "science_completed": self.science_completed,
            "all_verifiers_passed": self.all_verifiers_passed,
            "perception": dict(self.perception),
            "next_plan_id": self.next_plan_id,
            "stage": self.stage,
            "cycles_remaining": self.cycles_remaining,
            "science_runs_remaining": self.science_runs_remaining,
            "replans_remaining": self.replans_remaining,
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutonomyAdvanceResponse":
        perception = payload.get("perception")
        if not isinstance(perception, Mapping):
            raise ValueError("autonomy response perception must be an object")
        if payload.get("proof_effect", "none") != "none" or bool(
            payload.get("promotion_authority", False)
        ):
            raise ValueError("autonomy response cannot carry proof authority")
        return cls(
            session_id=str(payload["session_id"]),
            operation_id=str(payload["operation_id"]),
            cycle_index=int(payload["cycle_index"]),
            executed_plan_id=str(payload["executed_plan_id"]),
            workspace_id=str(payload["workspace_id"]),
            workspace_version=int(payload["workspace_version"]),
            science_run_id=str(payload["science_run_id"]),
            science_completed=bool(payload["science_completed"]),
            all_verifiers_passed=bool(payload["all_verifiers_passed"]),
            perception=dict(perception),
            next_plan_id=str(payload.get("next_plan_id", "")),
            stage=str(payload["stage"]),
            cycles_remaining=int(payload["cycles_remaining"]),
            science_runs_remaining=int(payload["science_runs_remaining"]),
            replans_remaining=int(payload["replans_remaining"]),
        )


@dataclass(frozen=True)
class AutonomyCycleReceipt:
    operation_id: str
    plan_id: str
    cycle_index: int
    response: AutonomyAdvanceResponse

    def to_dict(self) -> dict[str, Any]:
        return {
            "autonomy_cycle_receipt_schema": 1,
            "operation_id": self.operation_id,
            "plan_id": self.plan_id,
            "cycle_index": self.cycle_index,
            "response": self.response.to_dict(),
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutonomyCycleReceipt":
        if payload.get("autonomy_cycle_receipt_schema") != 1:
            raise ValueError("unsupported autonomy cycle receipt schema")
        response = payload.get("response")
        if not isinstance(response, Mapping):
            raise ValueError("autonomy cycle receipt response must be an object")
        if payload.get("proof_effect", "none") != "none" or bool(
            payload.get("promotion_authority", False)
        ):
            raise ValueError("autonomy cycle receipt cannot carry proof authority")
        return cls(
            operation_id=str(payload["operation_id"]),
            plan_id=str(payload["plan_id"]),
            cycle_index=int(payload["cycle_index"]),
            response=AutonomyAdvanceResponse.from_dict(response),
        )


@dataclass(frozen=True)
class AutonomySessionRecord:
    session_id: str
    objective: str
    workspace_id: str
    pending_plan_id: str
    stage: AutonomyStage
    run_spec: AutonomyRunSpec
    budget: AutonomyLoopBudget
    cycles_completed: int = 0
    science_runs: int = 0
    replans: int = 0
    latest_perception: Mapping[str, Any] | None = None
    receipts: tuple[AutonomyCycleReceipt, ...] = ()
    proof_effect: str = "none"
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        if not self.session_id or len(self.session_id) > 128:
            raise ValueError("autonomy session_id must be non-empty and bounded")
        if len(self.objective) > 16_384:
            raise ValueError("autonomy objective is too large")
        if not self.workspace_id:
            raise ValueError("autonomy workspace_id must be non-empty")
        if self.stage is AutonomyStage.WAITING_PLAN_APPROVAL and not self.pending_plan_id:
            raise ValueError("waiting autonomy session requires a pending plan")
        if self.stage is not AutonomyStage.WAITING_PLAN_APPROVAL and self.pending_plan_id:
            raise ValueError("non-waiting autonomy session cannot carry pending plan")
        for value, maximum, name in (
            (self.cycles_completed, self.budget.max_cycles, "cycles_completed"),
            (self.science_runs, self.budget.max_science_runs, "science_runs"),
            (self.replans, self.budget.max_replans, "replans"),
        ):
            if value < 0 or value > maximum:
                raise ValueError(f"autonomy {name} is outside configured budget")
        if len(self.receipts) != self.cycles_completed:
            raise ValueError("autonomy receipt count must equal cycles_completed")
        if self.proof_effect != "none" or self.promotion_authority:
            raise ValueError("autonomy session cannot carry proof authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "autonomy_session_schema": 1,
            "session_id": self.session_id,
            "objective": self.objective,
            "workspace_id": self.workspace_id,
            "pending_plan_id": self.pending_plan_id,
            "stage": self.stage.value,
            "run_spec": self.run_spec.to_dict(),
            "budget": self.budget.to_dict(),
            "cycles_completed": self.cycles_completed,
            "science_runs": self.science_runs,
            "replans": self.replans,
            "latest_perception": (
                dict(self.latest_perception)
                if self.latest_perception is not None
                else None
            ),
            "receipts": [receipt.to_dict() for receipt in self.receipts],
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutonomySessionRecord":
        if payload.get("autonomy_session_schema") != 1:
            raise ValueError("unsupported autonomy session schema")
        run_spec = payload.get("run_spec")
        budget = payload.get("budget")
        perception = payload.get("latest_perception")
        receipts = payload.get("receipts", [])
        if not isinstance(run_spec, Mapping) or not isinstance(budget, Mapping):
            raise ValueError("autonomy session run_spec/budget must be objects")
        if perception is not None and not isinstance(perception, Mapping):
            raise ValueError("autonomy latest_perception must be an object or null")
        if not isinstance(receipts, list) or not all(
            isinstance(item, Mapping) for item in receipts
        ):
            raise ValueError("autonomy receipts must be an array of objects")
        if payload.get("proof_effect", "none") != "none" or bool(
            payload.get("promotion_authority", False)
        ):
            raise ValueError("autonomy session cannot carry proof authority")
        return cls(
            session_id=str(payload["session_id"]),
            objective=str(payload.get("objective", "")),
            workspace_id=str(payload["workspace_id"]),
            pending_plan_id=str(payload.get("pending_plan_id", "")),
            stage=AutonomyStage(str(payload["stage"])),
            run_spec=AutonomyRunSpec.from_dict(run_spec),
            budget=AutonomyLoopBudget.from_dict(budget),
            cycles_completed=int(payload.get("cycles_completed", 0)),
            science_runs=int(payload.get("science_runs", 0)),
            replans=int(payload.get("replans", 0)),
            latest_perception=dict(perception) if perception is not None else None,
            receipts=tuple(AutonomyCycleReceipt.from_dict(item) for item in receipts),
        )


@dataclass(frozen=True)
class AutonomyInspectResponse:
    session_id: str
    objective: str
    workspace_id: str
    pending_plan_id: str
    stage: str
    cycles_completed: int
    science_runs: int
    replans: int
    cycles_remaining: int
    science_runs_remaining: int
    replans_remaining: int
    latest_perception: dict[str, Any] | None
    proof_effect: str = "none"
    promotion_authority: bool = False


class FileAutonomySessionStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_session_id(session_id: str) -> str:
        if not session_id or len(session_id) > 128 or any(
            ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            for ch in session_id
        ):
            raise ValueError("autonomy session_id contains unsupported characters")
        return session_id

    def _path(self, session_id: str) -> Path:
        return self.root / f"{self._safe_session_id(session_id)}.json"

    def _lock(self, session_id: str) -> Path:
        return self.root / f".{self._safe_session_id(session_id)}.lock"

    def load(self, session_id: str) -> AutonomySessionRecord | None:
        path = self._path(session_id)
        with CrossProcessFileLock(self._lock(session_id)):
            if not path.exists():
                return None
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = validate_hashed_envelope(
                raw,
                schema_key="autonomy_session_envelope_schema",
                schema_value=1,
                digest_key="autonomy_session_sha256",
                payload_key="session",
            )
            record = AutonomySessionRecord.from_dict(payload)
            if record.session_id != session_id:
                raise ValueError("autonomy session filename/content mismatch")
            return record

    def create(self, record: AutonomySessionRecord) -> None:
        path = self._path(record.session_id)
        with CrossProcessFileLock(self._lock(record.session_id)):
            if path.exists():
                raise AutonomyLoopError("autonomy session_id already exists")
            envelope = hashed_envelope(
                schema_key="autonomy_session_envelope_schema",
                schema_value=1,
                digest_key="autonomy_session_sha256",
                payload_key="session",
                payload=record.to_dict(),
            )
            atomic_write_json(path, envelope)

    def save(
        self,
        record: AutonomySessionRecord,
        *,
        expected_receipts: int | None = None,
    ) -> None:
        path = self._path(record.session_id)
        with CrossProcessFileLock(self._lock(record.session_id)):
            if expected_receipts is not None and path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                payload = validate_hashed_envelope(
                    raw,
                    schema_key="autonomy_session_envelope_schema",
                    schema_value=1,
                    digest_key="autonomy_session_sha256",
                    payload_key="session",
                )
                current = AutonomySessionRecord.from_dict(payload)
                if len(current.receipts) != expected_receipts:
                    raise AutonomyLoopError(
                        "autonomy session changed concurrently"
                    )
            envelope = hashed_envelope(
                schema_key="autonomy_session_envelope_schema",
                schema_value=1,
                digest_key="autonomy_session_sha256",
                payload_key="session",
                payload=record.to_dict(),
            )
            atomic_write_json(path, envelope)


class AutonomyLoopRuntime:
    def __init__(
        self,
        *,
        bus: ToolBus,
        registry: ModuleRegistry,
        plan_runtime: CanvasPlanRuntime,
        plan_store: FileCanvasPlanStore,
        workspace_store: FileExperimentWorkspace,
        session_store: FileAutonomySessionStore,
        replan_provider: ReplanProvider | None = None,
        network_mode: AgentNetworkMode = AgentNetworkMode.LOCAL_ZERO_CONTACT,
        gpu_enabled: bool = False,
    ) -> None:
        self.bus = bus
        self.registry = registry
        self.plan_runtime = plan_runtime
        self.plan_store = plan_store
        self.workspace_store = workspace_store
        self.session_store = session_store
        self.replan_provider = replan_provider
        self.network_mode = network_mode
        self._perception_trackers: dict[str, AgentPerceptionTracker] = {}
        self.executor = GraphExecutor(registry, gpu_enabled=gpu_enabled)

    def create_session(
        self,
        *,
        initial_plan_id: str,
        objective: str = "",
        run_spec: AutonomyRunSpec | None = None,
        budget: AutonomyLoopBudget | None = None,
        session_id: str | None = None,
    ) -> AutonomySessionRecord:
        plan = self.plan_store.load(initial_plan_id)
        if plan is None:
            raise AutonomyLoopError("unknown initial autonomy plan")
        if plan.workspace_id != self.workspace_store.workspace_id:
            raise AutonomyLoopError("initial autonomy plan belongs to another workspace")
        selected_budget = budget or AutonomyLoopBudget()
        if len(plan.ordered_steps) > selected_budget.max_plan_steps_per_cycle:
            raise AutonomyLoopError(
                "initial autonomy plan exceeds max_plan_steps_per_cycle"
            )
        record = AutonomySessionRecord(
            session_id=session_id or str(uuid4()),
            objective=objective,
            workspace_id=plan.workspace_id,
            pending_plan_id=plan.plan_id,
            stage=AutonomyStage.WAITING_PLAN_APPROVAL,
            run_spec=run_spec or AutonomyRunSpec(),
            budget=selected_budget,
        )
        self.session_store.create(record)
        return record

    @staticmethod
    def _remaining(record: AutonomySessionRecord) -> tuple[int, int, int]:
        return (
            record.budget.max_cycles - record.cycles_completed,
            record.budget.max_science_runs - record.science_runs,
            record.budget.max_replans - record.replans,
        )

    @staticmethod
    def _inspect(record: AutonomySessionRecord) -> AutonomyInspectResponse:
        cycles, runs, replans = AutonomyLoopRuntime._remaining(record)
        return AutonomyInspectResponse(
            session_id=record.session_id,
            objective=record.objective,
            workspace_id=record.workspace_id,
            pending_plan_id=record.pending_plan_id,
            stage=record.stage.value,
            cycles_completed=record.cycles_completed,
            science_runs=record.science_runs,
            replans=record.replans,
            cycles_remaining=cycles,
            science_runs_remaining=runs,
            replans_remaining=replans,
            latest_perception=(
                dict(record.latest_perception)
                if record.latest_perception is not None
                else None
            ),
        )

    def inspect_session(
        self, request: AutonomyInspectRequest, _context: ToolContext
    ) -> AutonomyInspectResponse:
        record = self.session_store.load(request.session_id)
        if record is None:
            raise AutonomyLoopError("unknown autonomy session")
        return self._inspect(record)

    def _run_science(
        self, experiment: Experiment, run_spec: AutonomyRunSpec
    ) -> RunResult:
        external_inputs = dict(run_spec.external_inputs or {})
        if run_spec.target_node_ids:
            return self.executor.run_selected_upstream(
                experiment,
                run_spec.target_node_ids,
                external_inputs=external_inputs,
                seed=run_spec.seed,
            )
        return self.executor.run(
            experiment,
            external_inputs=external_inputs,
            seed=run_spec.seed,
        )

    @staticmethod
    def _receipt_for_operation(
        record: AutonomySessionRecord, operation_id: str
    ) -> AutonomyCycleReceipt | None:
        matches = [
            receipt
            for receipt in record.receipts
            if receipt.operation_id == operation_id
        ]
        if len(matches) > 1:
            raise AutonomyLoopError("duplicate autonomy operation receipt")
        return matches[0] if matches else None

    def _advance(
        self,
        request: AutonomyAdvanceRequest,
        context: ToolContext,
    ) -> AutonomyAdvanceResponse:
        if not context.operation_id:
            raise AutonomyLoopError("autonomy advance requires operation_id")
        session = self.session_store.load(request.session_id)
        if session is None:
            raise AutonomyLoopError("unknown autonomy session")
        prior = self._receipt_for_operation(session, context.operation_id)
        if prior is not None:
            if prior.plan_id != request.plan_id:
                raise AutonomyLoopError(
                    "autonomy operation receipt belongs to a different plan"
                )
            return prior.response

        if session.stage is not AutonomyStage.WAITING_PLAN_APPROVAL:
            raise AutonomyLoopError(
                f"autonomy session is not awaiting a plan: {session.stage.value}"
            )
        if session.pending_plan_id != request.plan_id:
            raise AutonomyLoopError(
                "autonomy advance plan_id does not match the session pending plan"
            )
        if session.cycles_completed >= session.budget.max_cycles:
            raise AutonomyLoopError("autonomy cycle budget exhausted")
        if session.science_runs >= session.budget.max_science_runs:
            raise AutonomyLoopError("autonomy science-run budget exhausted")

        plan = self.plan_store.load(request.plan_id)
        if plan is None:
            raise AutonomyLoopError("unknown pending autonomy plan")
        if len(plan.ordered_steps) > session.budget.max_plan_steps_per_cycle:
            raise AutonomyLoopError(
                "pending plan exceeds max_plan_steps_per_cycle"
            )

        try:
            plan_result = self.plan_runtime.execute_plan(
                CanvasPlanExecuteRequest(request.plan_id),
                context,
            )
        except ToolPreconditionError as exc:
            raise AutonomyLoopError(str(exc)) from exc

        workspace_record, experiment = self.workspace_store.load()
        if (
            workspace_record.version != plan_result.final_workspace_version
            or workspace_record.target_semantic_sha256
            != plan_result.target_semantic_sha256
            or workspace_record.target_full_sha256
            != plan_result.target_full_sha256
        ):
            raise RuntimeError(
                "workspace changed between approved plan completion and science observation"
            )

        run_result = self._run_science(experiment, session.run_spec)
        if not run_result.completed:
            raise RuntimeError(
                "autonomy science run did not complete: "
                f"{run_result.interruption_reason or 'unknown interruption'}"
            )
        run_summary = AutonomyRunSummary.from_run_result(run_result)
        tracker = self._perception_trackers.setdefault(
            session.session_id,
            AgentPerceptionTracker(network_mode=self.network_mode),
        )
        perception = tracker.snapshot(
            experiment,
            run_result=run_result,
        ).to_dict()

        cycle_index = session.cycles_completed + 1
        cycles_after = cycle_index
        science_after = session.science_runs + 1
        replans_after = session.replans
        next_plan_id = ""
        stage = AutonomyStage.FINISHED

        remaining_cycles = session.budget.max_cycles - cycles_after
        remaining_runs = session.budget.max_science_runs - science_after
        remaining_replans = session.budget.max_replans - replans_after
        may_replan = (
            self.replan_provider is not None
            and remaining_cycles > 0
            and remaining_runs > 0
            and remaining_replans > 0
        )

        if may_replan:
            replan_context = AutonomyReplanContext(
                session_id=session.session_id,
                objective=session.objective,
                cycle_index=cycle_index,
                run_summary=run_summary.to_dict(),
                perception=perception,
                workspace_id=workspace_record.workspace_id,
                workspace_version=workspace_record.version,
                semantic_experiment_sha256=workspace_record.target_semantic_sha256,
                full_experiment_sha256=workspace_record.target_full_sha256,
                remaining_cycles=remaining_cycles,
                remaining_science_runs=remaining_runs,
                remaining_replans=remaining_replans,
            )
            proposal = self.replan_provider(replan_context)
            if proposal is not None:
                if not isinstance(proposal, CanvasPlanPreviewRequest):
                    raise TypeError(
                        "autonomy replan_provider must return CanvasPlanPreviewRequest or None"
                    )
                if len(proposal.steps) > session.budget.max_plan_steps_per_cycle:
                    raise RuntimeError(
                        "replan proposal exceeds max_plan_steps_per_cycle after "
                        "the approved plan already committed"
                    )
                try:
                    preview = self.plan_runtime.preview_plan(proposal)
                except Exception as exc:
                    raise RuntimeError(
                        "autonomy follow-up plan preview failed after the approved "
                        f"plan committed: {type(exc).__name__}: {exc}"
                    ) from exc
                next_plan_id = preview.plan_id
                replans_after += 1
                stage = AutonomyStage.WAITING_PLAN_APPROVAL

        cycles_remaining = session.budget.max_cycles - cycles_after
        science_runs_remaining = session.budget.max_science_runs - science_after
        replans_remaining = session.budget.max_replans - replans_after
        response = AutonomyAdvanceResponse(
            session_id=session.session_id,
            operation_id=context.operation_id,
            cycle_index=cycle_index,
            executed_plan_id=request.plan_id,
            workspace_id=workspace_record.workspace_id,
            workspace_version=workspace_record.version,
            science_run_id=run_summary.run_id,
            science_completed=run_summary.completed,
            all_verifiers_passed=run_summary.all_verifiers_passed,
            perception=perception,
            next_plan_id=next_plan_id,
            stage=stage.value,
            cycles_remaining=cycles_remaining,
            science_runs_remaining=science_runs_remaining,
            replans_remaining=replans_remaining,
        )
        receipt = AutonomyCycleReceipt(
            operation_id=context.operation_id,
            plan_id=request.plan_id,
            cycle_index=cycle_index,
            response=response,
        )
        updated = AutonomySessionRecord(
            session_id=session.session_id,
            objective=session.objective,
            workspace_id=session.workspace_id,
            pending_plan_id=next_plan_id,
            stage=stage,
            run_spec=session.run_spec,
            budget=session.budget,
            cycles_completed=cycles_after,
            science_runs=science_after,
            replans=replans_after,
            latest_perception=perception,
            receipts=session.receipts + (receipt,),
        )
        try:
            self.session_store.save(
                updated,
                expected_receipts=len(session.receipts),
            )
        except Exception as exc:
            raise RuntimeError(
                "autonomy cycle completed workspace/science work but durable "
                f"session receipt persistence failed: {type(exc).__name__}: {exc}"
            ) from exc
        return response

    def advance(
        self,
        request: AutonomyAdvanceRequest,
        context: ToolContext,
    ) -> AutonomyAdvanceResponse:
        return self._advance(request, context)

    def recover_advance(
        self,
        request: AutonomyAdvanceRequest,
        context: ToolContext,
    ) -> AutonomyAdvanceResponse | None:
        session = self.session_store.load(request.session_id)
        if session is None or not context.operation_id:
            return None
        prior = self._receipt_for_operation(session, context.operation_id)
        if prior is not None:
            if prior.plan_id != request.plan_id:
                return None
            return prior.response
        return self._advance(request, context)


AutonomyApprovalDecision = Callable[[Mapping[str, Any]], bool]


def autonomy_cycle_approval_callback(
    session_store: FileAutonomySessionStore,
    plan_store: FileCanvasPlanStore,
    decision: AutonomyApprovalDecision,
    *,
    fallback: ApprovalCallback | None = None,
) -> ApprovalCallback:
    if not callable(decision):
        raise TypeError("autonomy approval decision must be callable")

    def approve(call: ToolCall, descriptor: ToolDescriptor) -> bool:
        if call.tool_name != "cace.autonomy.advance":
            return bool(fallback(call, descriptor)) if fallback is not None else False
        session_id = call.arguments.get("session_id")
        plan_id = call.arguments.get("plan_id")
        if not isinstance(session_id, str) or not isinstance(plan_id, str):
            return False
        session = session_store.load(session_id)
        plan = plan_store.load(plan_id)
        if session is None or plan is None:
            return False
        if (
            session.stage is not AutonomyStage.WAITING_PLAN_APPROVAL
            or session.pending_plan_id != plan_id
            or session.workspace_id != plan.workspace_id
        ):
            return False
        payload = {
            "approval_schema": "cace-autonomy-cycle-approval-v1",
            "session_id": session.session_id,
            "objective": session.objective,
            "budget": session.budget.to_dict(),
            "budget_used": {
                "cycles_completed": session.cycles_completed,
                "science_runs": session.science_runs,
                "replans": session.replans,
            },
            "run_spec": session.run_spec.to_dict(),
            "pending_plan": plan.approval_payload(),
            "post_plan_behavior": (
                "run one bounded canonical science execution, build non-authoritative "
                "perception, and optionally create one follow-up plan preview; any "
                "follow-up plan requires a new approval before mutation"
            ),
            "proof_effect": "none",
            "promotion_authority": False,
        }
        return bool(decision(payload))

    return approve


def register_autonomy_loop_tools(
    bus: ToolBus,
    *,
    registry: ModuleRegistry,
    plan_runtime: CanvasPlanRuntime,
    plan_store: FileCanvasPlanStore,
    workspace_store: FileExperimentWorkspace,
    session_store: FileAutonomySessionStore,
    replan_provider: ReplanProvider | None = None,
    network_mode: AgentNetworkMode = AgentNetworkMode.LOCAL_ZERO_CONTACT,
    gpu_enabled: bool = False,
) -> AutonomyLoopRuntime:
    runtime = AutonomyLoopRuntime(
        bus=bus,
        registry=registry,
        plan_runtime=plan_runtime,
        plan_store=plan_store,
        workspace_store=workspace_store,
        session_store=session_store,
        replan_provider=replan_provider,
        network_mode=network_mode,
        gpu_enabled=gpu_enabled,
    )
    bus.register(
        TypedTool(
            name="cace.autonomy.inspect_session",
            description=(
                "Inspect bounded autonomous Plan -> Execute -> Observe -> Replan "
                "session state without mutating the workspace."
            ),
            capability=Capability.READ_RUNTIME,
            request_type=AutonomyInspectRequest,
            response_type=AutonomyInspectResponse,
            handler=runtime.inspect_session,
        )
    )
    bus.register(
        TypedTool(
            name="cace.autonomy.advance",
            description=(
                "Execute exactly one approved autonomy cycle: the session's exact "
                "pending plan, one bounded canonical science run, canonical "
                "non-authoritative perception, and at most one follow-up plan preview."
            ),
            capability=Capability.CANVAS_MUTATE,
            request_type=AutonomyAdvanceRequest,
            response_type=AutonomyAdvanceResponse,
            handler=runtime.advance,
            idempotency_required=True,
            recovery_handler=runtime.recover_advance,
        )
    )
    return runtime

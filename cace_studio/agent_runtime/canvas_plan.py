from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Experiment
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.reproducibility import (
    drift_report,
    experiment_fingerprint,
    sha256_identity,
)

from .canvas_mutation import (
    CanvasCommitRequest,
    CanvasMutationError,
    CanvasMutationOperation,
    CanvasMutationRuntime,
    CanvasPreviewRecord,
    FileCanvasPreviewStore,
)
from .contracts import (
    Capability,
    ToolCall,
    ToolContext,
    ToolDescriptor,
    ToolPreconditionError,
    TypedTool,
)
from .durability import (
    CrossProcessFileLock,
    atomic_write_json,
    hashed_envelope,
    validate_hashed_envelope,
)
from .tool_bus import ApprovalCallback, ToolBus
from .workspace_store import FileExperimentWorkspace, WorkspaceConflictError


class CanvasPlanError(ToolPreconditionError):
    pass


@dataclass(frozen=True)
class CanvasPlanStep:
    step_id: str
    operations: tuple[CanvasMutationOperation, ...]
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.step_id or self.step_id != self.step_id.strip():
            raise ValueError("plan step_id must be non-empty canonical text")
        if len(self.step_id) > 128 or any(
            ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            for ch in self.step_id
        ):
            raise ValueError("plan step_id contains unsupported characters")
        if not self.operations:
            raise ValueError("plan step requires at least one canvas operation")
        if len(self.operations) > 100:
            raise ValueError("plan step is limited to 100 canvas operations")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError("plan step dependencies must be unique")
        if self.step_id in self.depends_on:
            raise ValueError("plan step cannot depend on itself")

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "depends_on": list(self.depends_on),
            "operations": [operation.to_dict() for operation in self.operations],
        }


@dataclass(frozen=True)
class CanvasPlanPreviewRequest:
    steps: tuple[CanvasPlanStep, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("canvas plan requires at least one step")
        if len(self.steps) > 50:
            raise ValueError("canvas plan is limited to 50 steps")


@dataclass(frozen=True)
class CanvasPlanExecuteRequest:
    plan_id: str

    def __post_init__(self) -> None:
        if (
            len(self.plan_id) != 64
            or any(ch not in "0123456789abcdef" for ch in self.plan_id)
        ):
            raise ValueError("plan_id must be a lowercase SHA-256 identity")


@dataclass(frozen=True)
class CanvasPlanStepRecord:
    step_id: str
    order_index: int
    depends_on: tuple[str, ...]
    preview_id: str
    base_workspace_version: int
    target_workspace_version: int
    base_semantic_sha256: str
    base_full_sha256: str
    target_semantic_sha256: str
    target_full_sha256: str
    diff_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "order_index": self.order_index,
            "depends_on": list(self.depends_on),
            "preview_id": self.preview_id,
            "base_workspace_version": self.base_workspace_version,
            "target_workspace_version": self.target_workspace_version,
            "base_semantic_sha256": self.base_semantic_sha256,
            "base_full_sha256": self.base_full_sha256,
            "target_semantic_sha256": self.target_semantic_sha256,
            "target_full_sha256": self.target_full_sha256,
            "diff_sha256": self.diff_sha256,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanvasPlanStepRecord":
        return cls(
            step_id=str(payload["step_id"]),
            order_index=int(payload["order_index"]),
            depends_on=tuple(str(item) for item in payload.get("depends_on", [])),
            preview_id=str(payload["preview_id"]),
            base_workspace_version=int(payload["base_workspace_version"]),
            target_workspace_version=int(payload["target_workspace_version"]),
            base_semantic_sha256=str(payload["base_semantic_sha256"]),
            base_full_sha256=str(payload["base_full_sha256"]),
            target_semantic_sha256=str(payload["target_semantic_sha256"]),
            target_full_sha256=str(payload["target_full_sha256"]),
            diff_sha256=str(payload["diff_sha256"]),
        )


@dataclass(frozen=True)
class CanvasPlanRecord:
    plan_id: str
    workspace_id: str
    base_workspace_version: int
    target_workspace_version: int
    base_semantic_sha256: str
    base_full_sha256: str
    target_semantic_sha256: str
    target_full_sha256: str
    ordered_steps: tuple[CanvasPlanStepRecord, ...]
    dependency_estimate: Mapping[str, Any]
    proof_effect: str = "none"
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        if len(self.plan_id) != 64 or any(
            ch not in "0123456789abcdef" for ch in self.plan_id
        ):
            raise ValueError("plan_id must be lowercase SHA-256")
        if not self.workspace_id:
            raise ValueError("canvas plan requires a persisted workspace")
        if self.target_workspace_version != (
            self.base_workspace_version + len(self.ordered_steps)
        ):
            raise ValueError("plan target workspace version disagrees with step count")
        if self.proof_effect != "none" or self.promotion_authority:
            raise ValueError("canvas plan cannot carry proof authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "canvas_plan_schema": 1,
            "plan_id": self.plan_id,
            "workspace_id": self.workspace_id,
            "base_workspace_version": self.base_workspace_version,
            "target_workspace_version": self.target_workspace_version,
            "base_semantic_sha256": self.base_semantic_sha256,
            "base_full_sha256": self.base_full_sha256,
            "target_semantic_sha256": self.target_semantic_sha256,
            "target_full_sha256": self.target_full_sha256,
            "ordered_steps": [step.to_dict() for step in self.ordered_steps],
            "dependency_estimate": dict(self.dependency_estimate),
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanvasPlanRecord":
        if payload.get("canvas_plan_schema") != 1:
            raise CanvasPlanError("unsupported canvas plan schema")
        steps = payload.get("ordered_steps")
        estimate = payload.get("dependency_estimate")
        if not isinstance(steps, list) or not all(
            isinstance(item, Mapping) for item in steps
        ):
            raise CanvasPlanError("canvas plan ordered_steps must be an array")
        if not isinstance(estimate, Mapping):
            raise CanvasPlanError("canvas plan dependency_estimate must be an object")
        return cls(
            plan_id=str(payload["plan_id"]),
            workspace_id=str(payload["workspace_id"]),
            base_workspace_version=int(payload["base_workspace_version"]),
            target_workspace_version=int(payload["target_workspace_version"]),
            base_semantic_sha256=str(payload["base_semantic_sha256"]),
            base_full_sha256=str(payload["base_full_sha256"]),
            target_semantic_sha256=str(payload["target_semantic_sha256"]),
            target_full_sha256=str(payload["target_full_sha256"]),
            ordered_steps=tuple(CanvasPlanStepRecord.from_dict(item) for item in steps),
            dependency_estimate=dict(estimate),
            proof_effect=str(payload.get("proof_effect", "none")),
            promotion_authority=bool(payload.get("promotion_authority", False)),
        )

    def approval_payload(self) -> dict[str, Any]:
        return {
            "approval_schema": "cace-canvas-plan-approval-v1",
            **self.to_dict(),
        }


@dataclass(frozen=True)
class CanvasPlanPreviewResponse:
    plan_id: str
    step_count: int
    ordered_step_ids: tuple[str, ...]
    workspace_id: str
    base_workspace_version: int
    target_workspace_version: int
    base_semantic_sha256: str
    base_full_sha256: str
    target_semantic_sha256: str
    target_full_sha256: str
    dependency_estimate: dict[str, Any]
    proof_effect: str = "none"
    promotion_authority: bool = False


@dataclass(frozen=True)
class CanvasPlanExecuteResponse:
    plan_id: str
    operation_id: str
    completed_steps: tuple[str, ...]
    child_operation_ids: tuple[str, ...]
    workspace_id: str
    base_workspace_version: int
    final_workspace_version: int
    target_semantic_sha256: str
    target_full_sha256: str
    post_semantic_sha256: str
    post_full_sha256: str
    semantic_hash_verified: bool
    full_hash_verified: bool
    proof_effect: str = "none"
    promotion_authority: bool = False


class FileCanvasPlanStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, plan_id: str) -> Path:
        if len(plan_id) != 64 or any(ch not in "0123456789abcdef" for ch in plan_id):
            raise CanvasPlanError("invalid canvas plan id")
        return self.root / f"{plan_id}.json"

    def _lock(self, plan_id: str) -> Path:
        return self.root / f".{plan_id}.lock"

    @staticmethod
    def _identity_payload(record: CanvasPlanRecord) -> dict[str, Any]:
        payload = record.to_dict()
        payload.pop("plan_id", None)
        return payload

    @classmethod
    def _validate_identity(cls, record: CanvasPlanRecord) -> None:
        if sha256_identity(cls._identity_payload(record)) != record.plan_id:
            raise CanvasPlanError("canvas plan identity mismatch")
        steps = record.ordered_steps
        if tuple(step.order_index for step in steps) != tuple(range(len(steps))):
            raise CanvasPlanError("canvas plan step order indices are not contiguous")
        if len({step.step_id for step in steps}) != len(steps):
            raise CanvasPlanError("canvas plan step IDs are not unique")
        completed_ids: set[str] = set()
        for step in steps:
            unknown_or_future = sorted(set(step.depends_on) - completed_ids)
            if unknown_or_future:
                raise CanvasPlanError(
                    f"canvas plan step {step.step_id!r} has non-prior dependencies "
                    f"{unknown_or_future}"
                )
            completed_ids.add(step.step_id)
        for previous, current in zip(steps, steps[1:]):
            if previous.target_workspace_version != current.base_workspace_version:
                raise CanvasPlanError("canvas plan workspace version chain is broken")
            if previous.target_semantic_sha256 != current.base_semantic_sha256:
                raise CanvasPlanError("canvas plan semantic hash chain is broken")
            if previous.target_full_sha256 != current.base_full_sha256:
                raise CanvasPlanError("canvas plan full hash chain is broken")
        if steps:
            first, last = steps[0], steps[-1]
            if first.base_workspace_version != record.base_workspace_version:
                raise CanvasPlanError("canvas plan first step base version mismatch")
            if last.target_workspace_version != record.target_workspace_version:
                raise CanvasPlanError("canvas plan final step target version mismatch")
            if first.base_semantic_sha256 != record.base_semantic_sha256:
                raise CanvasPlanError("canvas plan first step semantic base mismatch")
            if first.base_full_sha256 != record.base_full_sha256:
                raise CanvasPlanError("canvas plan first step full base mismatch")
            if last.target_semantic_sha256 != record.target_semantic_sha256:
                raise CanvasPlanError("canvas plan final semantic target mismatch")
            if last.target_full_sha256 != record.target_full_sha256:
                raise CanvasPlanError("canvas plan final full target mismatch")

    def save(self, record: CanvasPlanRecord) -> None:
        self._validate_identity(record)
        path = self._path(record.plan_id)
        with CrossProcessFileLock(self._lock(record.plan_id)):
            envelope = hashed_envelope(
                schema_key="canvas_plan_envelope_schema",
                schema_value=1,
                digest_key="canvas_plan_sha256",
                payload_key="plan",
                payload=record.to_dict(),
            )
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                existing = validate_hashed_envelope(
                    raw,
                    schema_key="canvas_plan_envelope_schema",
                    schema_value=1,
                    digest_key="canvas_plan_sha256",
                    payload_key="plan",
                )
                if existing != record.to_dict():
                    raise CanvasPlanError("plan_id collision with different plan content")
                return
            atomic_write_json(path, envelope)

    def load(self, plan_id: str) -> CanvasPlanRecord | None:
        path = self._path(plan_id)
        with CrossProcessFileLock(self._lock(plan_id)):
            if not path.exists():
                return None
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = validate_hashed_envelope(
                raw,
                schema_key="canvas_plan_envelope_schema",
                schema_value=1,
                digest_key="canvas_plan_sha256",
                payload_key="plan",
            )
            record = CanvasPlanRecord.from_dict(payload)
            if record.plan_id != plan_id:
                raise CanvasPlanError("canvas plan filename/content mismatch")
            self._validate_identity(record)
            return record


class CanvasPlanRuntime:
    def __init__(
        self,
        *,
        canvas_runtime: CanvasMutationRuntime,
        registry: ModuleRegistry,
        preview_store: FileCanvasPreviewStore,
        plan_store: FileCanvasPlanStore,
        workspace_store: FileExperimentWorkspace,
    ) -> None:
        self.canvas_runtime = canvas_runtime
        self.registry = registry
        self.preview_store = preview_store
        self.plan_store = plan_store
        self.workspace_store = workspace_store

    @staticmethod
    def _topological_steps(
        steps: tuple[CanvasPlanStep, ...],
    ) -> tuple[CanvasPlanStep, ...]:
        by_id = {step.step_id: step for step in steps}
        if len(by_id) != len(steps):
            raise CanvasPlanError("canvas plan step IDs must be unique")
        for step in steps:
            unknown = sorted(set(step.depends_on) - set(by_id))
            if unknown:
                raise CanvasPlanError(
                    f"step {step.step_id!r} depends on unknown steps {unknown}"
                )
        incoming = {step.step_id: set(step.depends_on) for step in steps}
        outgoing = {step.step_id: set() for step in steps}
        for step in steps:
            for dependency in step.depends_on:
                outgoing[dependency].add(step.step_id)
        ready = sorted(step_id for step_id, deps in incoming.items() if not deps)
        ordered: list[CanvasPlanStep] = []
        while ready:
            step_id = ready.pop(0)
            ordered.append(by_id[step_id])
            for child in sorted(outgoing[step_id]):
                incoming[child].discard(step_id)
                if not incoming[child] and child not in {item.step_id for item in ordered} and child not in ready:
                    ready.append(child)
                    ready.sort()
        if len(ordered) != len(steps):
            raise CanvasPlanError("canvas plan dependency graph contains a cycle")
        return tuple(ordered)

    def _build_step_preview(
        self,
        *,
        base: Experiment,
        operations: tuple[CanvasMutationOperation, ...],
        workspace_id: str,
        base_version: int,
    ) -> tuple[CanvasPreviewRecord, Experiment]:
        candidate = self.canvas_runtime._apply(base, operations)
        base_semantic = experiment_fingerprint(base, include_layout=False)
        base_full = experiment_fingerprint(base, include_layout=True)
        target_semantic = experiment_fingerprint(candidate, include_layout=False)
        target_full = experiment_fingerprint(candidate, include_layout=True)
        operations_payload = [operation.to_dict() for operation in operations]
        mutation_sha = sha256_identity(
            {
                "canvas_mutation_schema": 1,
                "operations": operations_payload,
            }
        )
        diff = {
            "canvas_diff_schema": 1,
            "base_semantic_sha256": base_semantic,
            "base_full_sha256": base_full,
            "target_semantic_sha256": target_semantic,
            "target_full_sha256": target_full,
            "workspace_id": workspace_id,
            "base_workspace_version": base_version,
            "target_workspace_version": base_version + 1,
            "operations": operations_payload,
            "drift": drift_report(base, candidate),
            "proof_effect": "none",
            "promotion_authority": False,
        }
        diff_sha = sha256_identity(diff)
        preview_id = sha256_identity(
            {
                "canvas_preview_identity_schema": 1,
                "base_full_sha256": base_full,
                "target_full_sha256": target_full,
                "mutation_sha256": mutation_sha,
                "diff_sha256": diff_sha,
                "workspace_id": workspace_id,
                "base_workspace_version": base_version,
                "target_workspace_version": base_version + 1,
            }
        )
        record = CanvasPreviewRecord(
            preview_id=preview_id,
            base_semantic_sha256=base_semantic,
            base_full_sha256=base_full,
            target_semantic_sha256=target_semantic,
            target_full_sha256=target_full,
            mutation_sha256=mutation_sha,
            diff_sha256=diff_sha,
            operations=operations,
            diff=diff,
            workspace_id=workspace_id,
            base_workspace_version=base_version,
            target_workspace_version=base_version + 1,
        )
        self.preview_store.save(record)
        return record, candidate

    def _dependency_estimate(self, experiment: Experiment) -> dict[str, Any]:
        executor = GraphExecutor(self.registry)
        order = executor._validate_and_order(experiment)
        node_map = experiment.node_map()
        module_ids = tuple(sorted({node.module_id for node in experiment.nodes}))
        connected_inputs = {
            (edge.target_node, edge.target_port) for edge in experiment.edges
        }
        required_external_inputs: list[dict[str, Any]] = []
        for node in experiment.nodes:
            module = self.registry.create(node.module_id)
            for port in module.inputs:
                if port.required and (node.id, port.name) not in connected_inputs:
                    required_external_inputs.append(
                        {
                            "node_id": node.id,
                            "module_id": node.module_id,
                            "port": port.name,
                            "type_name": port.type_name,
                            "unit": port.unit,
                        }
                    )
        proof_modules: list[dict[str, Any]] = []
        for module_id in module_ids:
            cls = next(
                item
                for item in self.registry.classes()
                if item.metadata.module_id == module_id
            )
            proof_modules.append(
                {
                    "module_id": module_id,
                    "maturity": cls.metadata.maturity.value,
                    "declared_evidence": sorted(
                        item.value for item in cls.proof_status.evidence
                    ),
                    "formal_artifact": cls.proof_status.formal_artifact,
                    "limitations": list(cls.proof_status.limitations),
                }
            )
        return {
            "estimate_schema": "cace-canvas-plan-dependency-estimate-v1",
            "execution_node_order": order,
            "execution_module_order": [node_map[node_id].module_id for node_id in order],
            "unique_module_ids": list(module_ids),
            "required_external_inputs": required_external_inputs,
            "proof_metadata": proof_modules,
            "proof_metadata_note": (
                "descriptive module metadata only; this estimate is not executed "
                "verification evidence and creates no proof authority"
            ),
        }

    def preview_plan(
        self,
        request: CanvasPlanPreviewRequest,
    ) -> CanvasPlanPreviewResponse:
        ordered = self._topological_steps(request.steps)
        workspace_record, persisted = self.workspace_store.load()
        current = deepcopy(persisted)
        step_records: list[CanvasPlanStepRecord] = []
        version = workspace_record.version

        for index, step in enumerate(ordered):
            preview, candidate = self._build_step_preview(
                base=current,
                operations=step.operations,
                workspace_id=workspace_record.workspace_id,
                base_version=version,
            )
            step_records.append(
                CanvasPlanStepRecord(
                    step_id=step.step_id,
                    order_index=index,
                    depends_on=step.depends_on,
                    preview_id=preview.preview_id,
                    base_workspace_version=preview.base_workspace_version,
                    target_workspace_version=preview.target_workspace_version,
                    base_semantic_sha256=preview.base_semantic_sha256,
                    base_full_sha256=preview.base_full_sha256,
                    target_semantic_sha256=preview.target_semantic_sha256,
                    target_full_sha256=preview.target_full_sha256,
                    diff_sha256=preview.diff_sha256,
                )
            )
            current = candidate
            version += 1

        estimate = self._dependency_estimate(current)
        identity = {
            "canvas_plan_schema": 1,
            "workspace_id": workspace_record.workspace_id,
            "base_workspace_version": workspace_record.version,
            "target_workspace_version": version,
            "base_semantic_sha256": workspace_record.target_semantic_sha256,
            "base_full_sha256": workspace_record.target_full_sha256,
            "target_semantic_sha256": experiment_fingerprint(current, include_layout=False),
            "target_full_sha256": experiment_fingerprint(current, include_layout=True),
            "ordered_steps": [step.to_dict() for step in step_records],
            "dependency_estimate": estimate,
            "proof_effect": "none",
            "promotion_authority": False,
        }
        plan_id = sha256_identity(identity)
        record = CanvasPlanRecord(
            plan_id=plan_id,
            workspace_id=workspace_record.workspace_id,
            base_workspace_version=workspace_record.version,
            target_workspace_version=version,
            base_semantic_sha256=workspace_record.target_semantic_sha256,
            base_full_sha256=workspace_record.target_full_sha256,
            target_semantic_sha256=identity["target_semantic_sha256"],
            target_full_sha256=identity["target_full_sha256"],
            ordered_steps=tuple(step_records),
            dependency_estimate=estimate,
        )
        self.plan_store.save(record)
        return CanvasPlanPreviewResponse(
            plan_id=plan_id,
            step_count=len(step_records),
            ordered_step_ids=tuple(step.step_id for step in step_records),
            workspace_id=record.workspace_id,
            base_workspace_version=record.base_workspace_version,
            target_workspace_version=record.target_workspace_version,
            base_semantic_sha256=record.base_semantic_sha256,
            base_full_sha256=record.base_full_sha256,
            target_semantic_sha256=record.target_semantic_sha256,
            target_full_sha256=record.target_full_sha256,
            dependency_estimate=dict(record.dependency_estimate),
        )

    @staticmethod
    def _child_operation_id(
        *,
        plan_id: str,
        plan_operation_id: str,
        step: CanvasPlanStepRecord,
    ) -> str:
        return sha256_identity(
            {
                "canvas_plan_child_operation_schema": 1,
                "plan_id": plan_id,
                "plan_operation_id": plan_operation_id,
                "step_id": step.step_id,
                "step_index": step.order_index,
                "preview_id": step.preview_id,
            }
        )

    def _execute(
        self,
        request: CanvasPlanExecuteRequest,
        context: ToolContext,
    ) -> CanvasPlanExecuteResponse:
        record = self.plan_store.load(request.plan_id)
        if record is None:
            raise CanvasPlanError("unknown canvas plan")
        if not context.operation_id:
            raise CanvasPlanError("canvas plan execution requires operation_id")
        if record.workspace_id != self.workspace_store.workspace_id:
            raise CanvasPlanError("canvas plan belongs to a different workspace")

        completed: list[str] = []
        child_ids: list[str] = []
        made_progress = False

        for step in record.ordered_steps:
            preview = self.preview_store.load(step.preview_id)
            if preview is None:
                message = f"plan step {step.step_id!r} preview is missing"
                if made_progress:
                    raise RuntimeError(message)
                raise CanvasPlanError(message)

            child_operation_id = self._child_operation_id(
                plan_id=record.plan_id,
                plan_operation_id=context.operation_id,
                step=step,
            )
            child_ids.append(child_operation_id)

            try:
                receipt = self.workspace_store.reconcile(
                    operation_id=child_operation_id,
                    preview_id=preview.preview_id,
                    target_semantic_sha256=preview.target_semantic_sha256,
                    target_full_sha256=preview.target_full_sha256,
                )
            except WorkspaceConflictError as exc:
                raise RuntimeError(
                    f"plan step {step.step_id!r} receipt conflict: {exc}"
                ) from exc

            if receipt is not None:
                completed.append(step.step_id)
                made_progress = True
                continue

            current, _persisted = self.workspace_store.load()
            if current.version != step.base_workspace_version:
                message = (
                    f"plan step {step.step_id!r} expected workspace version "
                    f"{step.base_workspace_version}, found {current.version}"
                )
                if made_progress:
                    raise RuntimeError(message)
                raise CanvasPlanError(message)
            if (
                current.target_semantic_sha256 != step.base_semantic_sha256
                or current.target_full_sha256 != step.base_full_sha256
            ):
                message = f"plan step {step.step_id!r} base hashes no longer match"
                if made_progress:
                    raise RuntimeError(message)
                raise CanvasPlanError(message)

            try:
                committed = self.canvas_runtime.commit(
                    CanvasCommitRequest(preview.preview_id),
                    ToolContext(
                        sequence=context.sequence,
                        call_id=f"{context.call_id}:step:{step.order_index}",
                        tool_name="cace.canvas.commit_preview",
                        capability=Capability.CANVAS_MUTATE,
                        run_id=context.run_id,
                        operation_id=child_operation_id,
                        lease_id=context.lease_id,
                        lease_generation=context.lease_generation,
                    ),
                )
            except CanvasMutationError as exc:
                if made_progress:
                    raise RuntimeError(
                        f"plan partially committed before step {step.step_id!r}: {exc}"
                    ) from exc
                raise CanvasPlanError(str(exc)) from exc
            if committed.workspace_version != step.target_workspace_version:
                raise RuntimeError(
                    f"plan step {step.step_id!r} committed unexpected workspace version"
                )
            completed.append(step.step_id)
            made_progress = True

        final_record, final_experiment = self.workspace_store.load()
        if final_record.version < record.target_workspace_version:
            raise RuntimeError("canvas plan final workspace version is incomplete")

        current_semantic = experiment_fingerprint(final_experiment, include_layout=False)
        current_full = experiment_fingerprint(final_experiment, include_layout=True)
        if final_record.version == record.target_workspace_version:
            if (
                current_semantic != record.target_semantic_sha256
                or current_full != record.target_full_sha256
            ):
                raise RuntimeError("canvas plan final target hash verification failed")
        else:
            # The plan completed earlier and a later transaction advanced the
            # workspace. The validated receipt chain preserves the plan's exact
            # historical target, so recovery may finalize the outer operation
            # without rolling the newer workspace backward.
            last_step = record.ordered_steps[-1]
            last_child_id = self._child_operation_id(
                plan_id=record.plan_id,
                plan_operation_id=context.operation_id,
                step=last_step,
            )
            last_receipt = self.workspace_store.reconcile(
                operation_id=last_child_id,
                preview_id=last_step.preview_id,
                target_semantic_sha256=last_step.target_semantic_sha256,
                target_full_sha256=last_step.target_full_sha256,
            )
            if last_receipt is None:
                raise RuntimeError(
                    "canvas plan historical completion receipt is missing"
                )

        return CanvasPlanExecuteResponse(
            plan_id=record.plan_id,
            operation_id=context.operation_id,
            completed_steps=tuple(completed),
            child_operation_ids=tuple(child_ids),
            workspace_id=record.workspace_id,
            base_workspace_version=record.base_workspace_version,
            final_workspace_version=record.target_workspace_version,
            target_semantic_sha256=record.target_semantic_sha256,
            target_full_sha256=record.target_full_sha256,
            post_semantic_sha256=record.target_semantic_sha256,
            post_full_sha256=record.target_full_sha256,
            semantic_hash_verified=True,
            full_hash_verified=True,
        )

    def execute_plan(
        self,
        request: CanvasPlanExecuteRequest,
        context: ToolContext,
    ) -> CanvasPlanExecuteResponse:
        return self._execute(request, context)

    def recover_plan(
        self,
        request: CanvasPlanExecuteRequest,
        context: ToolContext,
    ) -> CanvasPlanExecuteResponse | None:
        record = self.plan_store.load(request.plan_id)
        if record is None:
            return None
        return self._execute(request, context)


CanvasPlanApprovalDecision = Callable[[Mapping[str, Any]], bool]


def canvas_plan_approval_callback(
    plan_store: FileCanvasPlanStore,
    decision: CanvasPlanApprovalDecision,
    *,
    fallback: ApprovalCallback | None = None,
) -> ApprovalCallback:
    if not callable(decision):
        raise TypeError("canvas plan approval decision must be callable")

    def approve(call: ToolCall, descriptor: ToolDescriptor) -> bool:
        if call.tool_name != "cace.canvas.execute_plan":
            return bool(fallback(call, descriptor)) if fallback is not None else False
        plan_id = call.arguments.get("plan_id")
        if not isinstance(plan_id, str):
            return False
        record = plan_store.load(plan_id)
        if record is None:
            return False
        return bool(decision(record.approval_payload()))

    return approve


def register_canvas_plan_tools(
    bus: ToolBus,
    *,
    canvas_runtime: CanvasMutationRuntime,
    registry: ModuleRegistry,
    preview_store: FileCanvasPreviewStore,
    plan_store: FileCanvasPlanStore,
    workspace_store: FileExperimentWorkspace,
) -> CanvasPlanRuntime:
    runtime = CanvasPlanRuntime(
        canvas_runtime=canvas_runtime,
        registry=registry,
        preview_store=preview_store,
        plan_store=plan_store,
        workspace_store=workspace_store,
    )
    bus.register(
        TypedTool(
            name="cace.canvas.preview_plan",
            description=(
                "Build and persist a deterministic multi-step canvas plan preview "
                "without mutating the active workspace."
            ),
            capability=Capability.READ_EXPERIMENT,
            request_type=CanvasPlanPreviewRequest,
            response_type=CanvasPlanPreviewResponse,
            handler=lambda request, _context: runtime.preview_plan(request),
        )
    )
    bus.register(
        TypedTool(
            name="cace.canvas.execute_plan",
            description=(
                "Execute one previously approved immutable canvas plan as ordered "
                "fenced/idempotent workspace transactions. Stops on first failure."
            ),
            capability=Capability.CANVAS_MUTATE,
            request_type=CanvasPlanExecuteRequest,
            response_type=CanvasPlanExecuteResponse,
            handler=runtime.execute_plan,
            idempotency_required=True,
            recovery_handler=runtime.recover_plan,
        )
    )
    return runtime

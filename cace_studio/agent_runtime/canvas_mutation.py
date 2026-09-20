from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Callable, Literal, Mapping

from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, ExperimentGroup, Node
from cace_studio.core.module import ValidationError
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.reproducibility import (
    drift_report,
    experiment_fingerprint,
    sha256_identity,
)

from .contracts import (
    Capability,
    ToolCall,
    ToolContext,
    ToolDescriptor,
    ToolPreconditionError,
    TypedTool,
    to_plain,
)
from .durability import (
    CrossProcessFileLock,
    atomic_write_json,
    hashed_envelope,
    validate_hashed_envelope,
)
from .tool_bus import ApprovalCallback, ToolBus


CanvasAction = Literal[
    "add_node",
    "remove_node",
    "replace_params",
    "move_node",
    "add_edge",
    "remove_edge",
]


class CanvasMutationError(ToolPreconditionError):
    pass


@dataclass(frozen=True)
class CanvasMutationOperation:
    action: CanvasAction
    node_id: str = ""
    module_id: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    position: tuple[float, float] | None = None
    source_node: str = ""
    source_port: str = ""
    target_node: str = ""
    target_port: str = ""

    def __post_init__(self) -> None:
        node_actions = {"add_node", "remove_node", "replace_params", "move_node"}
        edge_actions = {"add_edge", "remove_edge"}
        if self.action in node_actions and not self.node_id:
            raise ValueError(f"{self.action} requires node_id")
        if self.action == "add_node" and not self.module_id:
            raise ValueError("add_node requires module_id")
        if self.action == "move_node" and self.position is None:
            raise ValueError("move_node requires position")
        if self.action in edge_actions and not all(
            (self.source_node, self.source_port, self.target_node, self.target_port)
        ):
            raise ValueError(f"{self.action} requires complete edge identity")
        for value in (
            self.node_id,
            self.module_id,
            self.source_node,
            self.source_port,
            self.target_node,
            self.target_port,
        ):
            if value and (value != value.strip() or any(ord(ch) < 32 for ch in value)):
                raise ValueError("canvas identifiers must be canonical text")
        if self.position is not None:
            if len(self.position) != 2:
                raise ValueError("canvas position must contain exactly two coordinates")
            float(self.position[0])
            float(self.position[1])

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "node_id": self.node_id,
            "module_id": self.module_id,
            "params": to_plain(self.params),
            "position": list(self.position) if self.position is not None else None,
            "source_node": self.source_node,
            "source_port": self.source_port,
            "target_node": self.target_node,
            "target_port": self.target_port,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanvasMutationOperation":
        allowed = {
            "action",
            "node_id",
            "module_id",
            "params",
            "position",
            "source_node",
            "source_port",
            "target_node",
            "target_port",
        }
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise CanvasMutationError(f"canvas operation contains unknown fields: {unknown}")
        position = payload.get("position")
        if position is not None:
            if not isinstance(position, (list, tuple)) or len(position) != 2:
                raise CanvasMutationError("canvas position must contain two coordinates")
            position = (float(position[0]), float(position[1]))
        params = payload.get("params", {})
        if not isinstance(params, Mapping):
            raise CanvasMutationError("canvas params must be an object")
        return cls(
            action=str(payload["action"]),
            node_id=str(payload.get("node_id", "")),
            module_id=str(payload.get("module_id", "")),
            params=dict(params),
            position=position,
            source_node=str(payload.get("source_node", "")),
            source_port=str(payload.get("source_port", "")),
            target_node=str(payload.get("target_node", "")),
            target_port=str(payload.get("target_port", "")),
        )


@dataclass(frozen=True)
class CanvasPreviewRequest:
    operations: tuple[CanvasMutationOperation, ...]

    def __post_init__(self) -> None:
        if not self.operations:
            raise ValueError("canvas preview requires at least one operation")
        if len(self.operations) > 100:
            raise ValueError("canvas preview is limited to 100 operations")


@dataclass(frozen=True)
class CanvasCommitRequest:
    preview_id: str

    def __post_init__(self) -> None:
        if (
            not self.preview_id
            or len(self.preview_id) != 64
            or any(ch not in "0123456789abcdef" for ch in self.preview_id)
        ):
            raise ValueError("preview_id must be a lowercase SHA-256 identity")


@dataclass(frozen=True)
class CanvasPreviewResponse:
    preview_id: str
    operation_count: int
    base_semantic_sha256: str
    base_full_sha256: str
    target_semantic_sha256: str
    target_full_sha256: str
    mutation_sha256: str
    diff_sha256: str
    semantic_change: bool
    diff: dict[str, Any]
    proof_effect: str = "none"
    promotion_authority: bool = False


@dataclass(frozen=True)
class CanvasCommitResponse:
    preview_id: str
    operation_id: str
    base_semantic_sha256: str
    base_full_sha256: str
    target_semantic_sha256: str
    target_full_sha256: str
    post_semantic_sha256: str
    post_full_sha256: str
    diff_sha256: str
    semantic_hash_verified: bool
    full_hash_verified: bool
    proof_effect: str = "none"
    promotion_authority: bool = False


@dataclass(frozen=True)
class CanvasPreviewRecord:
    preview_id: str
    base_semantic_sha256: str
    base_full_sha256: str
    target_semantic_sha256: str
    target_full_sha256: str
    mutation_sha256: str
    diff_sha256: str
    operations: tuple[CanvasMutationOperation, ...]
    diff: Mapping[str, Any]
    proof_effect: str = "none"
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.preview_id,
            self.base_semantic_sha256,
            self.base_full_sha256,
            self.target_semantic_sha256,
            self.target_full_sha256,
            self.mutation_sha256,
            self.diff_sha256,
        ):
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise ValueError("canvas preview hashes must be lowercase SHA-256")
        if self.proof_effect != "none" or self.promotion_authority:
            raise ValueError("canvas preview cannot carry proof authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "canvas_preview_schema": 1,
            "preview_id": self.preview_id,
            "base_semantic_sha256": self.base_semantic_sha256,
            "base_full_sha256": self.base_full_sha256,
            "target_semantic_sha256": self.target_semantic_sha256,
            "target_full_sha256": self.target_full_sha256,
            "mutation_sha256": self.mutation_sha256,
            "diff_sha256": self.diff_sha256,
            "operations": [op.to_dict() for op in self.operations],
            "diff": dict(self.diff),
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanvasPreviewRecord":
        if payload.get("canvas_preview_schema") != 1:
            raise CanvasMutationError("unsupported canvas preview schema")
        operations = payload.get("operations")
        diff = payload.get("diff")
        if not isinstance(operations, list) or not all(
            isinstance(item, Mapping) for item in operations
        ):
            raise CanvasMutationError("canvas preview operations must be an array")
        if not isinstance(diff, Mapping):
            raise CanvasMutationError("canvas preview diff must be an object")
        if payload.get("proof_effect", "none") != "none" or bool(
            payload.get("promotion_authority", False)
        ):
            raise CanvasMutationError("canvas preview cannot carry proof authority")
        return cls(
            preview_id=str(payload["preview_id"]),
            base_semantic_sha256=str(payload["base_semantic_sha256"]),
            base_full_sha256=str(payload["base_full_sha256"]),
            target_semantic_sha256=str(payload["target_semantic_sha256"]),
            target_full_sha256=str(payload["target_full_sha256"]),
            mutation_sha256=str(payload["mutation_sha256"]),
            diff_sha256=str(payload["diff_sha256"]),
            operations=tuple(
                CanvasMutationOperation.from_dict(item) for item in operations
            ),
            diff=dict(diff),
        )

    def approval_payload(self) -> dict[str, Any]:
        return {
            "approval_schema": "cace-canvas-mutation-approval-v1",
            "preview_id": self.preview_id,
            "base_semantic_sha256": self.base_semantic_sha256,
            "base_full_sha256": self.base_full_sha256,
            "target_semantic_sha256": self.target_semantic_sha256,
            "target_full_sha256": self.target_full_sha256,
            "mutation_sha256": self.mutation_sha256,
            "diff_sha256": self.diff_sha256,
            "operations": [op.to_dict() for op in self.operations],
            "diff": dict(self.diff),
            "proof_effect": "none",
            "promotion_authority": False,
        }


class FileCanvasPreviewStore:
    """Durable immutable preview store used by approval and commit."""

    @staticmethod
    def _validate_identity(record: CanvasPreviewRecord) -> None:
        operations_payload = [operation.to_dict() for operation in record.operations]
        mutation_sha = sha256_identity(
            {
                "canvas_mutation_schema": 1,
                "operations": operations_payload,
            }
        )
        if mutation_sha != record.mutation_sha256:
            raise CanvasMutationError("canvas preview mutation hash mismatch")
        if sha256_identity(dict(record.diff)) != record.diff_sha256:
            raise CanvasMutationError("canvas preview diff hash mismatch")
        expected_preview_id = sha256_identity(
            {
                "canvas_preview_identity_schema": 1,
                "base_full_sha256": record.base_full_sha256,
                "target_full_sha256": record.target_full_sha256,
                "mutation_sha256": record.mutation_sha256,
                "diff_sha256": record.diff_sha256,
            }
        )
        if expected_preview_id != record.preview_id:
            raise CanvasMutationError("canvas preview identity mismatch")
        diff = dict(record.diff)
        if diff.get("operations") != operations_payload:
            raise CanvasMutationError(
                "canvas preview diff operations do not match mutation payload"
            )
        if diff.get("proof_effect") != "none" or bool(
            diff.get("promotion_authority", False)
        ):
            raise CanvasMutationError("canvas preview diff cannot carry proof authority")
        expected_fields = {
            "base_semantic_sha256": record.base_semantic_sha256,
            "base_full_sha256": record.base_full_sha256,
            "target_semantic_sha256": record.target_semantic_sha256,
            "target_full_sha256": record.target_full_sha256,
        }
        for key, value in expected_fields.items():
            if diff.get(key) != value:
                raise CanvasMutationError(
                    f"canvas preview diff field {key} does not match preview record"
                )

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, preview_id: str) -> Path:
        if (
            len(preview_id) != 64
            or any(ch not in "0123456789abcdef" for ch in preview_id)
        ):
            raise CanvasMutationError("invalid canvas preview id")
        return self.root / f"{preview_id}.json"

    def _lock(self, preview_id: str) -> Path:
        return self.root / f".{preview_id}.lock"

    def save(self, record: CanvasPreviewRecord) -> None:
        self._validate_identity(record)
        path = self._path(record.preview_id)
        with CrossProcessFileLock(self._lock(record.preview_id)):
            envelope = hashed_envelope(
                schema_key="canvas_preview_envelope_schema",
                schema_value=1,
                digest_key="canvas_preview_sha256",
                payload_key="preview",
                payload=record.to_dict(),
            )
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                existing = validate_hashed_envelope(
                    raw,
                    schema_key="canvas_preview_envelope_schema",
                    schema_value=1,
                    digest_key="canvas_preview_sha256",
                    payload_key="preview",
                )
                if existing != record.to_dict():
                    raise CanvasMutationError(
                        "preview_id collision with different preview content"
                    )
                return
            atomic_write_json(path, envelope)

    def load(self, preview_id: str) -> CanvasPreviewRecord | None:
        path = self._path(preview_id)
        with CrossProcessFileLock(self._lock(preview_id)):
            if not path.exists():
                return None
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = validate_hashed_envelope(
                raw,
                schema_key="canvas_preview_envelope_schema",
                schema_value=1,
                digest_key="canvas_preview_sha256",
                payload_key="preview",
            )
            record = CanvasPreviewRecord.from_dict(payload)
            if record.preview_id != preview_id:
                raise CanvasMutationError("preview filename/content identity mismatch")
            self._validate_identity(record)
            return record


class CanvasMutationRuntime:
    def __init__(
        self,
        *,
        registry: ModuleRegistry,
        active_experiment: Experiment,
        preview_store: FileCanvasPreviewStore,
    ) -> None:
        self.registry = registry
        self.active_experiment = active_experiment
        self.preview_store = preview_store

    def _validate_params(self, experiment: Experiment) -> None:
        classes = {
            cls.metadata.module_id: cls
            for cls in self.registry.classes()
        }
        for node in experiment.nodes:
            cls = classes.get(node.module_id)
            if cls is None:
                raise CanvasMutationError(
                    f"unknown module on node {node.id}: {node.module_id}"
                )
            allowed = {item.name for item in cls.parameters}
            unknown = sorted(set(node.params) - allowed)
            if unknown:
                raise CanvasMutationError(
                    f"{node.module_id}: unknown parameters {unknown}"
                )

    def _validate_candidate(self, experiment: Experiment) -> None:
        self._validate_params(experiment)
        try:
            GraphExecutor(self.registry)._validate_and_order(experiment)
        except ValidationError as exc:
            raise CanvasMutationError(str(exc)) from exc

    @staticmethod
    def _find_node(experiment: Experiment, node_id: str) -> Node:
        matches = [node for node in experiment.nodes if node.id == node_id]
        if len(matches) != 1:
            raise CanvasMutationError(
                f"expected exactly one node {node_id!r}; found {len(matches)}"
            )
        return matches[0]

    @staticmethod
    def _edge_from_operation(operation: CanvasMutationOperation) -> Edge:
        return Edge(
            source_node=operation.source_node,
            source_port=operation.source_port,
            target_node=operation.target_node,
            target_port=operation.target_port,
        )

    def _apply(
        self,
        base: Experiment,
        operations: tuple[CanvasMutationOperation, ...],
    ) -> Experiment:
        candidate = deepcopy(base)
        for operation in operations:
            if operation.action == "add_node":
                if any(node.id == operation.node_id for node in candidate.nodes):
                    raise CanvasMutationError(
                        f"node already exists: {operation.node_id}"
                    )
                if not self.registry.contains(operation.module_id):
                    raise CanvasMutationError(
                        f"unknown module: {operation.module_id}"
                    )
                candidate.nodes.append(
                    Node(
                        id=operation.node_id,
                        module_id=operation.module_id,
                        params=deepcopy(operation.params),
                        position=(
                            tuple(float(value) for value in operation.position)
                            if operation.position is not None
                            else (0.0, 0.0)
                        ),
                    )
                )
            elif operation.action == "remove_node":
                self._find_node(candidate, operation.node_id)
                candidate.nodes = [
                    node for node in candidate.nodes if node.id != operation.node_id
                ]
                candidate.edges = [
                    edge
                    for edge in candidate.edges
                    if edge.source_node != operation.node_id
                    and edge.target_node != operation.node_id
                ]
                groups: list[ExperimentGroup] = []
                for group in candidate.groups:
                    members = tuple(
                        node_id
                        for node_id in group.node_ids
                        if node_id != operation.node_id
                    )
                    if members:
                        groups.append(
                            ExperimentGroup(group.id, group.name, members)
                        )
                candidate.groups = groups
            elif operation.action == "replace_params":
                node = self._find_node(candidate, operation.node_id)
                node.params = deepcopy(operation.params)
            elif operation.action == "move_node":
                node = self._find_node(candidate, operation.node_id)
                assert operation.position is not None
                node.position = (
                    float(operation.position[0]),
                    float(operation.position[1]),
                )
            elif operation.action == "add_edge":
                edge = self._edge_from_operation(operation)
                if edge in candidate.edges:
                    raise CanvasMutationError("edge already exists")
                candidate.edges.append(edge)
            elif operation.action == "remove_edge":
                edge = self._edge_from_operation(operation)
                if edge not in candidate.edges:
                    raise CanvasMutationError("edge does not exist")
                candidate.edges = [item for item in candidate.edges if item != edge]
            else:
                raise CanvasMutationError(
                    f"unsupported canvas action: {operation.action}"
                )
        self._validate_candidate(candidate)
        return candidate

    @staticmethod
    def _operations_payload(
        operations: tuple[CanvasMutationOperation, ...],
    ) -> list[dict[str, Any]]:
        return [operation.to_dict() for operation in operations]

    def preview(self, request: CanvasPreviewRequest) -> CanvasPreviewResponse:
        base = deepcopy(self.active_experiment)
        base_semantic = experiment_fingerprint(base, include_layout=False)
        base_full = experiment_fingerprint(base, include_layout=True)
        candidate = self._apply(base, request.operations)
        target_semantic = experiment_fingerprint(candidate, include_layout=False)
        target_full = experiment_fingerprint(candidate, include_layout=True)
        operations_payload = self._operations_payload(request.operations)
        mutation_sha = sha256_identity(
            {
                "canvas_mutation_schema": 1,
                "operations": operations_payload,
            }
        )
        drift = drift_report(base, candidate)
        diff = {
            "canvas_diff_schema": 1,
            "base_semantic_sha256": base_semantic,
            "base_full_sha256": base_full,
            "target_semantic_sha256": target_semantic,
            "target_full_sha256": target_full,
            "operations": operations_payload,
            "drift": drift,
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
            operations=request.operations,
            diff=diff,
        )
        self.preview_store.save(record)
        return CanvasPreviewResponse(
            preview_id=preview_id,
            operation_count=len(request.operations),
            base_semantic_sha256=base_semantic,
            base_full_sha256=base_full,
            target_semantic_sha256=target_semantic,
            target_full_sha256=target_full,
            mutation_sha256=mutation_sha,
            diff_sha256=diff_sha,
            semantic_change=base_semantic != target_semantic,
            diff=diff,
        )

    def commit(
        self,
        request: CanvasCommitRequest,
        context: ToolContext,
    ) -> CanvasCommitResponse:
        record = self.preview_store.load(request.preview_id)
        if record is None:
            raise CanvasMutationError("unknown canvas preview")
        if not context.operation_id:
            raise CanvasMutationError("canvas commit requires operation_id")

        current_semantic = experiment_fingerprint(
            self.active_experiment, include_layout=False
        )
        current_full = experiment_fingerprint(
            self.active_experiment, include_layout=True
        )
        if (
            current_semantic != record.base_semantic_sha256
            or current_full != record.base_full_sha256
        ):
            raise CanvasMutationError(
                "active experiment changed since preview; create a new preview"
            )

        before = deepcopy(self.active_experiment)
        candidate = self._apply(before, record.operations)
        candidate_semantic = experiment_fingerprint(candidate, include_layout=False)
        candidate_full = experiment_fingerprint(candidate, include_layout=True)
        candidate_diff = {
            "canvas_diff_schema": 1,
            "base_semantic_sha256": record.base_semantic_sha256,
            "base_full_sha256": record.base_full_sha256,
            "target_semantic_sha256": candidate_semantic,
            "target_full_sha256": candidate_full,
            "operations": self._operations_payload(record.operations),
            "drift": drift_report(before, candidate),
            "proof_effect": "none",
            "promotion_authority": False,
        }
        if (
            candidate_semantic != record.target_semantic_sha256
            or candidate_full != record.target_full_sha256
            or sha256_identity(candidate_diff) != record.diff_sha256
        ):
            raise CanvasMutationError(
                "recomputed canvas preview does not match approved target"
            )

        self.active_experiment.schema_version = candidate.schema_version
        self.active_experiment.name = candidate.name
        self.active_experiment.nodes = deepcopy(candidate.nodes)
        self.active_experiment.edges = deepcopy(candidate.edges)
        self.active_experiment.metadata = deepcopy(candidate.metadata)
        self.active_experiment.groups = deepcopy(candidate.groups)

        post_semantic = experiment_fingerprint(
            self.active_experiment, include_layout=False
        )
        post_full = experiment_fingerprint(
            self.active_experiment, include_layout=True
        )
        semantic_verified = post_semantic == record.target_semantic_sha256
        full_verified = post_full == record.target_full_sha256
        if not semantic_verified or not full_verified:
            self.active_experiment.schema_version = before.schema_version
            self.active_experiment.name = before.name
            self.active_experiment.nodes = before.nodes
            self.active_experiment.edges = before.edges
            self.active_experiment.metadata = before.metadata
            self.active_experiment.groups = before.groups
            raise CanvasMutationError(
                "post-mutation experiment hash verification failed; mutation rolled back"
            )

        return CanvasCommitResponse(
            preview_id=record.preview_id,
            operation_id=context.operation_id,
            base_semantic_sha256=record.base_semantic_sha256,
            base_full_sha256=record.base_full_sha256,
            target_semantic_sha256=record.target_semantic_sha256,
            target_full_sha256=record.target_full_sha256,
            post_semantic_sha256=post_semantic,
            post_full_sha256=post_full,
            diff_sha256=record.diff_sha256,
            semantic_hash_verified=True,
            full_hash_verified=True,
        )


def register_canvas_mutation_tools(
    bus: ToolBus,
    *,
    registry: ModuleRegistry,
    active_experiment: Experiment,
    preview_store: FileCanvasPreviewStore,
) -> CanvasMutationRuntime:
    runtime = CanvasMutationRuntime(
        registry=registry,
        active_experiment=active_experiment,
        preview_store=preview_store,
    )

    bus.register(
        TypedTool(
            name="cace.canvas.preview_mutation",
            description=(
                "Build a non-mutating deterministic preview/diff for typed canvas "
                "operations and persist that exact preview for later approval."
            ),
            capability=Capability.READ_EXPERIMENT,
            request_type=CanvasPreviewRequest,
            response_type=CanvasPreviewResponse,
            handler=lambda request, _context: runtime.preview(request),
        )
    )
    bus.register(
        TypedTool(
            name="cace.canvas.commit_preview",
            description=(
                "Commit one previously persisted canvas preview. Human approval, "
                "durable idempotency, and current lease fencing are required."
            ),
            capability=Capability.CANVAS_MUTATE,
            request_type=CanvasCommitRequest,
            response_type=CanvasCommitResponse,
            handler=runtime.commit,
            idempotency_required=True,
        )
    )
    return runtime


CanvasApprovalDecision = Callable[[Mapping[str, Any]], bool]


def canvas_preview_approval_callback(
    preview_store: FileCanvasPreviewStore,
    decision: CanvasApprovalDecision,
    *,
    fallback: ApprovalCallback | None = None,
) -> ApprovalCallback:
    """Return an approval callback that resolves commit IDs to the exact stored diff."""

    if not callable(decision):
        raise TypeError("canvas approval decision must be callable")

    def approve(call: ToolCall, descriptor: ToolDescriptor) -> bool:
        if call.tool_name != "cace.canvas.commit_preview":
            return bool(fallback(call, descriptor)) if fallback is not None else False
        preview_id = call.arguments.get("preview_id")
        if not isinstance(preview_id, str):
            return False
        record = preview_store.load(preview_id)
        if record is None:
            return False
        return bool(decision(record.approval_payload()))

    return approve

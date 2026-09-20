from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Experiment
from cace_studio.core.native_runtime import NativeRuntime
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.reproducibility import experiment_fingerprint, registry_contract_fingerprint

from .contracts import Capability, ToolContext, TypedTool
from .tool_bus import ToolBus


@dataclass(frozen=True)
class EmptyRequest:
    pass


@dataclass(frozen=True)
class NativeStatusResponse:
    available: bool
    backend: str
    version: str
    path: str
    reason: str


@dataclass(frozen=True)
class RegistryListRequest:
    limit: int = 200

    def __post_init__(self) -> None:
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass(frozen=True)
class RegistryListResponse:
    module_contract_sha256: str
    total_modules: int
    returned_modules: int
    modules: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ActiveExperimentResponse:
    name: str
    semantic_experiment_sha256: str
    full_experiment_sha256: str
    node_count: int
    edge_count: int
    group_count: int
    node_ids: tuple[str, ...]
    module_ids: tuple[str, ...]


@dataclass(frozen=True)
class RunActiveExperimentRequest:
    target_node_ids: tuple[str, ...] = ()
    external_inputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    seed: int = 0


@dataclass(frozen=True)
class RunActiveExperimentResponse:
    run_id: str
    completed: bool
    interruption_reason: str
    run_scope: str
    semantic_experiment_sha256: str
    source_semantic_experiment_sha256: str
    execution_scope_sha256: str
    all_verifiers_passed: bool
    node_output_ports: dict[str, tuple[str, ...]]
    verification_states: dict[str, tuple[str, ...]]
    public_resolution_claim_allowed: bool
    proof_effect: str = "none"
    promotion_authority: bool = False


def _registry_entry(cls: type) -> dict[str, Any]:
    metadata = cls.metadata
    return {
        "module_id": metadata.module_id,
        "name": metadata.name,
        "version": metadata.version,
        "category": metadata.category,
        "description": metadata.description,
        "maturity": metadata.maturity.value,
        "assumptions": list(metadata.assumptions),
        "inputs": [
            {
                "name": item.name,
                "type_name": item.type_name,
                "required": item.required,
                "unit": item.unit,
            }
            for item in cls.inputs
        ],
        "outputs": [
            {
                "name": item.name,
                "type_name": item.type_name,
                "required": item.required,
                "unit": item.unit,
            }
            for item in cls.outputs
        ],
        "parameters": [
            {
                "name": item.name,
                "type_name": item.type_name,
                "default": item.default,
                "description": item.description,
                "unit": item.unit,
            }
            for item in cls.parameters
        ],
        "supports_gpu": bool(cls.supports_gpu),
        "declared_evidence": sorted(item.value for item in cls.proof_status.evidence),
        "limitations": list(cls.proof_status.limitations),
        "formal_artifact": cls.proof_status.formal_artifact,
        "evidence_note": "module metadata is descriptive and is not executed verification evidence",
    }


def register_core_tools(
    bus: ToolBus,
    *,
    registry: ModuleRegistry | None = None,
    active_experiment: Experiment | None = None,
    gpu_enabled: bool = False,
) -> None:
    """Register non-proof-authoritative tools backed by canonical CACE core APIs."""

    native_runtime = NativeRuntime()

    def native_status(_: EmptyRequest, __: ToolContext) -> NativeStatusResponse:
        status = native_runtime.status
        return NativeStatusResponse(
            available=status.available,
            backend=status.backend,
            version=status.version,
            path=status.path,
            reason=status.reason,
        )

    bus.register(
        TypedTool(
            name="cace.runtime.native_status",
            description="Inspect the currently available CACE native runtime backend without mutating it.",
            capability=Capability.READ_RUNTIME,
            request_type=EmptyRequest,
            response_type=NativeStatusResponse,
            handler=native_status,
        )
    )

    if registry is not None:
        def list_modules(request: RegistryListRequest, _: ToolContext) -> RegistryListResponse:
            classes = sorted(registry.classes(), key=lambda item: item.metadata.module_id)
            selected = classes[: request.limit]
            return RegistryListResponse(
                module_contract_sha256=registry_contract_fingerprint(registry),
                total_modules=len(classes),
                returned_modules=len(selected),
                modules=tuple(_registry_entry(cls) for cls in selected),
            )

        bus.register(
            TypedTool(
                name="cace.registry.list_modules",
                description=(
                    "List canonical registered CACE modules and typed contracts. "
                    "Declared evidence metadata is not executed proof evidence."
                ),
                capability=Capability.READ_CATALOG,
                request_type=RegistryListRequest,
                response_type=RegistryListResponse,
                handler=list_modules,
            )
        )

    if active_experiment is not None:
        def describe_active(_: EmptyRequest, __: ToolContext) -> ActiveExperimentResponse:
            return ActiveExperimentResponse(
                name=active_experiment.name,
                semantic_experiment_sha256=experiment_fingerprint(active_experiment, include_layout=False),
                full_experiment_sha256=experiment_fingerprint(active_experiment, include_layout=True),
                node_count=len(active_experiment.nodes),
                edge_count=len(active_experiment.edges),
                group_count=len(active_experiment.groups),
                node_ids=tuple(node.id for node in active_experiment.nodes),
                module_ids=tuple(sorted({node.module_id for node in active_experiment.nodes})),
            )

        bus.register(
            TypedTool(
                name="cace.experiment.describe_active",
                description="Describe the active experiment using canonical CACE semantic/full fingerprints.",
                capability=Capability.READ_EXPERIMENT,
                request_type=EmptyRequest,
                response_type=ActiveExperimentResponse,
                handler=describe_active,
            )
        )

    if registry is not None and active_experiment is not None:
        executor = GraphExecutor(registry, gpu_enabled=gpu_enabled)

        def run_active(request: RunActiveExperimentRequest, _: ToolContext) -> RunActiveExperimentResponse:
            if request.target_node_ids:
                result = executor.run_selected_upstream(
                    active_experiment,
                    request.target_node_ids,
                    external_inputs=request.external_inputs,
                    seed=request.seed,
                )
            else:
                result = executor.run(
                    active_experiment,
                    external_inputs=request.external_inputs,
                    seed=request.seed,
                )

            verification_states = {
                node_id: tuple(record.state.value for record in records)
                for node_id, records in result.verification.items()
            }
            node_output_ports = {
                node_id: tuple(sorted(outputs))
                for node_id, outputs in result.outputs.items()
            }
            return RunActiveExperimentResponse(
                run_id=result.run_id,
                completed=result.completed,
                interruption_reason=result.interruption_reason,
                run_scope=result.run_scope,
                semantic_experiment_sha256=result.semantic_experiment_sha256,
                source_semantic_experiment_sha256=result.source_semantic_experiment_sha256,
                execution_scope_sha256=result.execution_scope_sha256,
                all_verifiers_passed=result.all_verifiers_passed,
                node_output_ports=node_output_ports,
                verification_states=verification_states,
                public_resolution_claim_allowed=result.any_public_resolution_claim_allowed,
            )

        bus.register(
            TypedTool(
                name="cace.experiment.run_active",
                description=(
                    "Execute the already-active experiment, or a selected-upstream scope, "
                    "through the canonical GraphExecutor. This tool cannot edit the graph or promote proof state."
                ),
                capability=Capability.RUN_SCIENCE,
                request_type=RunActiveExperimentRequest,
                response_type=RunActiveExperimentResponse,
                handler=run_active,
            )
        )

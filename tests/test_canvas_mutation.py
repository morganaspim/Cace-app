from __future__ import annotations

from dataclasses import dataclass

import pytest

from cace_studio.app import build_qualified_capabilities, build_registry

from cace_studio.agent_runtime import (
    CapabilityPolicy,
    FileAgentLeaseManager,
    FileCanvasPreviewStore,
    FileOperationStore,
    ToolBus,
    ToolCall,
    ToolStatus,
    canvas_preview_approval_callback,
    operation_id_for,
    register_canvas_mutation_tools,
)
from cace_studio.core.graph import Experiment, Node
from cace_studio.core.module import ExecutionContext, Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.reproducibility import experiment_fingerprint
from cace_studio.core.types import (
    Maturity,
    ModuleMetadata,
    PortSpec,
)


class SourceModule(Module):
    metadata = ModuleMetadata(
        module_id="test.source",
        name="Source",
        version="1",
        category="test",
        description="Canvas mutation source.",
        maturity=Maturity.PROTOTYPE,
    )
    outputs = (PortSpec("y", "scalar"),)

    def execute(self, inputs, params, ctx: ExecutionContext):
        return {"y": 1.0}


class SinkModule(Module):
    metadata = ModuleMetadata(
        module_id="test.sink",
        name="Sink",
        version="1",
        category="test",
        description="Canvas mutation sink.",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "scalar"),)

    def execute(self, inputs, params, ctx: ExecutionContext):
        return {}


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.register(SourceModule)
    registry.register(SinkModule)
    return registry


def _setup(tmp_path, *, approve=True):
    preview_store = FileCanvasPreviewStore(tmp_path / "previews")
    lease_manager = FileAgentLeaseManager(tmp_path / "leases")
    operation_store = FileOperationStore(tmp_path / "operations")
    approvals: list[dict] = []

    def decide(payload):
        approvals.append(dict(payload))
        return approve

    bus = ToolBus(
        policy=CapabilityPolicy.zero_contact(),
        approval_callback=canvas_preview_approval_callback(
            preview_store,
            decide,
        ),
        operation_store=operation_store,
        lease_validator=lambda call: lease_manager.assert_current(
            call.run_id,
            call.lease_id,
            call.lease_generation,
        ),
    )
    experiment = Experiment(
        name="canvas",
        nodes=[Node("src", "test.source", position=(1.0, 2.0))],
    )
    register_canvas_mutation_tools(
        bus,
        registry=_registry(),
        active_experiment=experiment,
        preview_store=preview_store,
    )
    return bus, experiment, preview_store, lease_manager, approvals


def _preview_add_sink(bus: ToolBus):
    return bus.invoke(
        ToolCall(
            "preview-1",
            "cace.canvas.preview_mutation",
            {
                "operations": [
                    {
                        "action": "add_node",
                        "node_id": "sink",
                        "module_id": "test.sink",
                        "position": [3.0, 4.0],
                    },
                    {
                        "action": "add_edge",
                        "source_node": "src",
                        "source_port": "y",
                        "target_node": "sink",
                        "target_port": "x",
                    },
                ]
            },
        )
    )


def test_preview_is_non_mutating_and_commit_matches_approved_hashes(tmp_path) -> None:
    bus, experiment, preview_store, leases, approvals = _setup(tmp_path)
    before_semantic = experiment_fingerprint(experiment, include_layout=False)
    before_full = experiment_fingerprint(experiment, include_layout=True)

    preview = _preview_add_sink(bus)
    assert preview.status is ToolStatus.OK
    assert len(experiment.nodes) == 1
    assert len(experiment.edges) == 0
    assert experiment_fingerprint(experiment, include_layout=False) == before_semantic
    assert experiment_fingerprint(experiment, include_layout=True) == before_full

    preview_id = preview.output["preview_id"]
    persisted = preview_store.load(preview_id)
    assert persisted is not None
    assert persisted.diff_sha256 == preview.output["diff_sha256"]
    assert preview.output["semantic_change"] is True

    lease = leases.acquire("canvas-run", "owner-a", ttl_seconds=60.0)
    arguments = {"preview_id": preview_id}
    operation_id = operation_id_for(
        run_id="canvas-run",
        ordinal=1,
        tool_name="cace.canvas.commit_preview",
        arguments=arguments,
    )
    committed = bus.invoke(
        ToolCall(
            "commit-1",
            "cace.canvas.commit_preview",
            arguments,
            run_id="canvas-run",
            operation_id=operation_id,
            lease_id=lease.lease_id,
            lease_generation=lease.generation,
        )
    )
    assert committed.status is ToolStatus.OK
    assert approvals and approvals[-1]["preview_id"] == preview_id
    assert approvals[-1]["diff_sha256"] == preview.output["diff_sha256"]
    assert approvals[-1]["target_semantic_sha256"] == preview.output["target_semantic_sha256"]

    assert len(experiment.nodes) == 2
    assert len(experiment.edges) == 1
    assert committed.output["semantic_hash_verified"] is True
    assert committed.output["full_hash_verified"] is True
    assert experiment_fingerprint(
        experiment, include_layout=False
    ) == committed.output["target_semantic_sha256"]
    assert experiment_fingerprint(
        experiment, include_layout=True
    ) == committed.output["target_full_sha256"]
    assert committed.proof_effect == "none"
    assert committed.promotion_authority is False


def test_commit_fails_closed_on_stale_preview_without_mutation(tmp_path) -> None:
    bus, experiment, _preview_store, leases, _approvals = _setup(tmp_path)
    preview = _preview_add_sink(bus)
    assert preview.status is ToolStatus.OK
    preview_id = preview.output["preview_id"]

    # A real out-of-band graph change invalidates the exact approved base.
    experiment.nodes[0].position = (99.0, 99.0)
    stale_full = experiment_fingerprint(experiment, include_layout=True)

    lease = leases.acquire("stale-run", "owner-a", ttl_seconds=60.0)
    arguments = {"preview_id": preview_id}
    operation_id = operation_id_for(
        run_id="stale-run",
        ordinal=1,
        tool_name="cace.canvas.commit_preview",
        arguments=arguments,
    )
    result = bus.invoke(
        ToolCall(
            "stale-commit",
            "cace.canvas.commit_preview",
            arguments,
            run_id="stale-run",
            operation_id=operation_id,
            lease_id=lease.lease_id,
            lease_generation=lease.generation,
        )
    )
    assert result.status is ToolStatus.INVALID_REQUEST
    assert "changed since preview" in result.error
    assert len(experiment.nodes) == 1
    assert len(experiment.edges) == 0
    assert experiment_fingerprint(experiment, include_layout=True) == stale_full

    stored = bus.operation_store.lookup_result(operation_id)
    assert stored is not None
    assert stored.status is ToolStatus.INVALID_REQUEST


def test_stale_fencing_generation_cannot_commit_preview(tmp_path) -> None:
    bus, experiment, _preview_store, leases, _approvals = _setup(tmp_path)
    preview = _preview_add_sink(bus)
    preview_id = preview.output["preview_id"]

    old = leases.acquire("fence-run", "owner-a", ttl_seconds=60.0)
    assert leases.release(old) is True
    current = leases.acquire("fence-run", "owner-b", ttl_seconds=60.0)
    assert current.generation == old.generation + 1

    arguments = {"preview_id": preview_id}
    result = bus.invoke(
        ToolCall(
            "stale-fence",
            "cace.canvas.commit_preview",
            arguments,
            run_id="fence-run",
            operation_id=operation_id_for(
                run_id="fence-run",
                ordinal=1,
                tool_name="cace.canvas.commit_preview",
                arguments=arguments,
            ),
            lease_id=old.lease_id,
            lease_generation=old.generation,
        )
    )
    assert result.status is ToolStatus.RECOVERY_BLOCKED
    assert "fencing validation failed" in result.error
    assert len(experiment.nodes) == 1
    assert len(experiment.edges) == 0


def test_human_denial_blocks_commit_and_preserves_preview(tmp_path) -> None:
    bus, experiment, preview_store, leases, approvals = _setup(
        tmp_path,
        approve=False,
    )
    preview = _preview_add_sink(bus)
    preview_id = preview.output["preview_id"]
    lease = leases.acquire("denied-run", "owner-a", ttl_seconds=60.0)
    arguments = {"preview_id": preview_id}

    denied = bus.invoke(
        ToolCall(
            "denied-commit",
            "cace.canvas.commit_preview",
            arguments,
            run_id="denied-run",
            operation_id=operation_id_for(
                run_id="denied-run",
                ordinal=1,
                tool_name="cace.canvas.commit_preview",
                arguments=arguments,
            ),
            lease_id=lease.lease_id,
            lease_generation=lease.generation,
        )
    )
    assert denied.status is ToolStatus.DENIED
    assert approvals[-1]["preview_id"] == preview_id
    assert preview_store.load(preview_id) is not None
    assert len(experiment.nodes) == 1
    assert len(experiment.edges) == 0


def test_preview_uses_canonical_graph_validation(tmp_path) -> None:
    bus, experiment, _preview_store, _leases, _approvals = _setup(tmp_path)
    invalid = bus.invoke(
        ToolCall(
            "bad-preview",
            "cace.canvas.preview_mutation",
            {
                "operations": [
                    {
                        "action": "add_node",
                        "node_id": "sink",
                        "module_id": "test.sink",
                    },
                    {
                        "action": "add_edge",
                        "source_node": "src",
                        "source_port": "missing",
                        "target_node": "sink",
                        "target_port": "x",
                    },
                ]
            },
        )
    )
    assert invalid.status is ToolStatus.INVALID_REQUEST
    assert "missing port" in invalid.error
    assert len(experiment.nodes) == 1
    assert len(experiment.edges) == 0



def test_canvas_preview_rejects_hidden_module_when_capability_gate_is_active(tmp_path) -> None:
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)
    bus = ToolBus()
    experiment = Experiment(
        name="qualified-canvas",
        nodes=[Node("src", "core.constant", {"value": 1})],
    )
    register_canvas_mutation_tools(
        bus,
        registry=registry,
        qualified_capabilities=capabilities,
        active_experiment=experiment,
        preview_store=FileCanvasPreviewStore(tmp_path / "qualified-previews"),
    )

    preview = bus.invoke(
        ToolCall(
            "hidden-preview",
            "cace.canvas.preview_mutation",
            {
                "operations": [
                    {
                        "action": "add_node",
                        "node_id": "hidden",
                        "module_id": "formal325.mesh_certificate_generator",
                        "position": [0.0, 0.0],
                    }
                ]
            },
        )
    )
    assert preview.status is ToolStatus.INVALID_REQUEST
    assert "unavailable on ai surface" in preview.error
    assert [node.id for node in experiment.nodes] == ["src"]

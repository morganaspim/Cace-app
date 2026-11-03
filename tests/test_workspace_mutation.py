from __future__ import annotations

from cace_studio.agent_runtime import (
    CapabilityPolicy,
    CanvasCommitRequest,
    FileAgentLeaseManager,
    FileCanvasPreviewStore,
    FileExperimentWorkspace,
    FileOperationStore,
    ToolBus,
    ToolCall,
    ToolContext,
    ToolStatus,
    canvas_preview_approval_callback,
    operation_id_for,
    register_canvas_mutation_tools,
)
from cace_studio.core.graph import Experiment, Node
from cace_studio.core.module import ExecutionContext, Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.reproducibility import experiment_fingerprint, sha256_identity
from cace_studio.core.types import Maturity, ModuleMetadata, PortSpec


class WorkspaceSource(Module):
    metadata = ModuleMetadata(
        module_id="workspace.source",
        name="Workspace Source",
        version="1",
        category="test",
        description="Persisted workspace source.",
        maturity=Maturity.PROTOTYPE,
    )
    outputs = (PortSpec("y", "scalar"),)

    def execute(self, inputs, params, ctx: ExecutionContext):
        return {"y": 1.0}


class WorkspaceSink(Module):
    metadata = ModuleMetadata(
        module_id="workspace.sink",
        name="Workspace Sink",
        version="1",
        category="test",
        description="Persisted workspace sink.",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "scalar"),)

    def execute(self, inputs, params, ctx: ExecutionContext):
        return {}


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.register(WorkspaceSource)
    registry.register(WorkspaceSink)
    return registry


def _experiment() -> Experiment:
    return Experiment(
        name="persisted",
        nodes=[Node("src", "workspace.source", position=(0.0, 0.0))],
    )


def _setup(tmp_path, *, active: Experiment | None = None):
    registry = _registry()
    experiment = active or _experiment()
    previews = FileCanvasPreviewStore(tmp_path / "previews")
    workspace = FileExperimentWorkspace(
        tmp_path / "workspace",
        workspace_id="main",
    )
    leases = FileAgentLeaseManager(tmp_path / "leases")
    operations = FileOperationStore(tmp_path / "operations")
    bus = ToolBus(
        policy=CapabilityPolicy.zero_contact(),
        approval_callback=canvas_preview_approval_callback(
            previews,
            lambda _payload: True,
        ),
        operation_store=operations,
        lease_validator=lambda call: leases.assert_current(
            call.run_id,
            call.lease_id,
            call.lease_generation,
        ),
    )
    runtime = register_canvas_mutation_tools(
        bus,
        registry=registry,
        active_experiment=experiment,
        preview_store=previews,
        workspace_store=workspace,
    )
    return bus, runtime, experiment, previews, workspace, leases, operations


def _preview(bus: ToolBus, *, node_id: str = "sink"):
    return bus.invoke(
        ToolCall(
            f"preview-{node_id}",
            "cace.canvas.preview_mutation",
            {
                "operations": [
                    {
                        "action": "add_node",
                        "node_id": node_id,
                        "module_id": "workspace.sink",
                        "position": [1.0, 2.0],
                    },
                    {
                        "action": "add_edge",
                        "source_node": "src",
                        "source_port": "y",
                        "target_node": node_id,
                        "target_port": "x",
                    },
                ]
            },
        )
    )


def _commit_call(preview_id: str, *, run_id: str, ordinal: int, lease):
    arguments = {"preview_id": preview_id}
    return ToolCall(
        f"{run_id}:{ordinal}",
        "cace.canvas.commit_preview",
        arguments,
        run_id=run_id,
        operation_id=operation_id_for(
            run_id=run_id,
            ordinal=ordinal,
            tool_name="cace.canvas.commit_preview",
            arguments=arguments,
        ),
        lease_id=lease.lease_id,
        lease_generation=lease.generation,
    )


def test_persisted_canvas_commit_binds_version_preview_operation_and_fence(tmp_path) -> None:
    bus, _runtime, experiment, _previews, workspace, leases, _operations = _setup(tmp_path)
    initial_record, initial_experiment = workspace.load()
    assert initial_record.version == 0
    assert experiment_fingerprint(initial_experiment, include_layout=True) == experiment_fingerprint(
        experiment, include_layout=True
    )

    preview = _preview(bus)
    assert preview.status is ToolStatus.OK
    assert preview.output["workspace_id"] == "main"
    assert preview.output["base_workspace_version"] == 0
    assert preview.output["target_workspace_version"] == 1
    assert len(experiment.nodes) == 1

    lease = leases.acquire("persist-run", "owner-a", ttl_seconds=60.0)
    call = _commit_call(
        preview.output["preview_id"],
        run_id="persist-run",
        ordinal=1,
        lease=lease,
    )
    result = bus.invoke(call)
    assert result.status is ToolStatus.OK
    assert result.output["workspace_id"] == "main"
    assert result.output["workspace_version"] == 1
    assert result.output["workspace_parent_version"] == 0

    record, persisted = workspace.load()
    assert record.version == 1
    assert record.parent_version == 0
    assert record.operation_id == call.operation_id
    assert record.preview_id == preview.output["preview_id"]
    assert record.lease_id == lease.lease_id
    assert record.lease_generation == lease.generation
    assert record.target_semantic_sha256 == preview.output["target_semantic_sha256"]
    assert record.target_full_sha256 == preview.output["target_full_sha256"]
    assert experiment_fingerprint(persisted, include_layout=False) == record.target_semantic_sha256
    assert experiment_fingerprint(persisted, include_layout=True) == record.target_full_sha256
    assert experiment_fingerprint(experiment, include_layout=True) == record.target_full_sha256


def test_persisted_workspace_is_source_of_truth_for_restarted_runtime(tmp_path) -> None:
    bus, _runtime, _experiment_a, _previews, workspace, leases, _operations = _setup(tmp_path)
    preview = _preview(bus)
    lease = leases.acquire("restart-run", "owner-a", ttl_seconds=60.0)
    committed = bus.invoke(
        _commit_call(
            preview.output["preview_id"],
            run_id="restart-run",
            ordinal=1,
            lease=lease,
        )
    )
    assert committed.status is ToolStatus.OK

    stale_local = _experiment()
    stale_local.name = "stale local copy"
    _bus_b, _runtime_b, active_b, _p, workspace_b, _l, _o = _setup(
        tmp_path,
        active=stale_local,
    )
    record, persisted = workspace_b.load()
    assert record.version == 1
    assert active_b.name == persisted.name
    assert len(active_b.nodes) == 2
    assert experiment_fingerprint(active_b, include_layout=True) == record.target_full_sha256


def test_workspace_version_conflict_rejects_second_stale_preview(tmp_path) -> None:
    bus, _runtime, experiment, _previews, workspace, leases, _operations = _setup(tmp_path)
    first_preview = _preview(bus, node_id="sink-a")
    second_preview = _preview(bus, node_id="sink-b")
    assert first_preview.output["base_workspace_version"] == 0
    assert second_preview.output["base_workspace_version"] == 0

    first_lease = leases.acquire("first-run", "owner-a", ttl_seconds=60.0)
    first = bus.invoke(
        _commit_call(
            first_preview.output["preview_id"],
            run_id="first-run",
            ordinal=1,
            lease=first_lease,
        )
    )
    assert first.status is ToolStatus.OK
    assert leases.release(first_lease) is True

    second_lease = leases.acquire("second-run", "owner-b", ttl_seconds=60.0)
    second = bus.invoke(
        _commit_call(
            second_preview.output["preview_id"],
            run_id="second-run",
            ordinal=1,
            lease=second_lease,
        )
    )
    assert second.status is ToolStatus.INVALID_REQUEST
    assert "version changed" in second.error

    record, persisted = workspace.load()
    assert record.version == 1
    assert len(persisted.nodes) == 2
    assert {node.id for node in persisted.nodes} == {"src", "sink-a"}
    assert experiment_fingerprint(experiment, include_layout=True) == record.target_full_sha256


def test_in_progress_operation_reconciles_from_already_committed_workspace(tmp_path) -> None:
    bus, runtime, experiment, _previews, workspace, leases, operations = _setup(tmp_path)
    preview = _preview(bus)
    assert preview.status is ToolStatus.OK
    preview_id = preview.output["preview_id"]

    lease = leases.acquire("crash-run", "owner-a", ttl_seconds=60.0)
    call = _commit_call(
        preview_id,
        run_id="crash-run",
        ordinal=1,
        lease=lease,
    )
    input_sha = sha256_identity(dict(call.arguments))
    claim = operations.claim(
        operation_id=call.operation_id,
        call_id=call.call_id,
        tool_name=call.tool_name,
        input_sha256=input_sha,
        lease_id=call.lease_id,
        lease_generation=call.lease_generation,
    )
    assert claim.action == "execute"

    # Simulate: handler/workspace commit succeeded, process died before the
    # Tool Bus could commit the operation ledger result.
    direct = runtime.commit(
        CanvasCommitRequest(preview_id),
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
    assert direct.workspace_version == 1
    in_progress = operations.load(call.operation_id)
    assert in_progress is not None
    assert in_progress.state == "in_progress"

    retry = ToolCall(
        "retry-call",
        call.tool_name,
        dict(call.arguments),
        run_id=call.run_id,
        operation_id=call.operation_id,
        lease_id=call.lease_id,
        lease_generation=call.lease_generation,
    )
    recovered = bus.invoke(retry)
    assert recovered.status is ToolStatus.OK
    assert recovered.output["workspace_version"] == 1

    committed_operation = operations.load(call.operation_id)
    assert committed_operation is not None
    assert committed_operation.state == "committed"
    record, persisted = workspace.load()
    assert record.version == 1
    assert record.operation_id == call.operation_id
    assert len(persisted.nodes) == 2
    assert len(experiment.nodes) == 2


def test_older_in_progress_operation_reconciles_after_later_workspace_version(tmp_path) -> None:
    bus, runtime, experiment, _previews, workspace, leases, operations = _setup(tmp_path)

    preview_a = _preview(bus, node_id="sink-a")
    assert preview_a.status is ToolStatus.OK
    lease_a1 = leases.acquire("lineage-run", "owner-a1", ttl_seconds=60.0)
    call_a = _commit_call(
        preview_a.output["preview_id"],
        run_id="lineage-run",
        ordinal=1,
        lease=lease_a1,
    )
    input_sha_a = sha256_identity(dict(call_a.arguments))
    claim_a = operations.claim(
        operation_id=call_a.operation_id,
        call_id=call_a.call_id,
        tool_name=call_a.tool_name,
        input_sha256=input_sha_a,
        lease_id=call_a.lease_id,
        lease_generation=call_a.lease_generation,
    )
    assert claim_a.action == "execute"

    direct_a = runtime.commit(
        CanvasCommitRequest(preview_a.output["preview_id"]),
        ToolContext(
            sequence=1,
            call_id=call_a.call_id,
            tool_name=call_a.tool_name,
            capability=bus.descriptor(call_a.tool_name).capability,
            run_id=call_a.run_id,
            operation_id=call_a.operation_id,
            lease_id=call_a.lease_id,
            lease_generation=call_a.lease_generation,
        ),
    )
    assert direct_a.workspace_version == 1
    assert operations.load(call_a.operation_id).state == "in_progress"
    assert leases.release(lease_a1) is True

    preview_b = _preview(bus, node_id="sink-b")
    assert preview_b.status is ToolStatus.OK
    assert preview_b.output["base_workspace_version"] == 1
    lease_b = leases.acquire("other-run", "owner-b", ttl_seconds=60.0)
    committed_b = bus.invoke(
        _commit_call(
            preview_b.output["preview_id"],
            run_id="other-run",
            ordinal=1,
            lease=lease_b,
        )
    )
    assert committed_b.status is ToolStatus.OK
    assert committed_b.output["workspace_version"] == 2

    record_v2, persisted_v2 = workspace.load()
    assert record_v2.version == 2
    assert len(record_v2.history) == 2
    assert record_v2.history[0].operation_id == call_a.operation_id
    target_v2 = record_v2.target_full_sha256

    lease_a2 = leases.acquire("lineage-run", "owner-a2", ttl_seconds=60.0)
    retry_a = ToolCall(
        "lineage-retry",
        call_a.tool_name,
        dict(call_a.arguments),
        run_id=call_a.run_id,
        operation_id=call_a.operation_id,
        lease_id=lease_a2.lease_id,
        lease_generation=lease_a2.generation,
    )
    recovered_a = bus.invoke(retry_a)
    assert recovered_a.status is ToolStatus.OK
    assert recovered_a.output["workspace_version"] == 1
    assert recovered_a.output["workspace_parent_version"] == 0
    assert recovered_a.output["target_full_sha256"] == direct_a.target_full_sha256

    operation_a = operations.load(call_a.operation_id)
    assert operation_a is not None
    assert operation_a.state == "committed"

    final_record, final_experiment = workspace.load()
    assert final_record.version == 2
    assert final_record.target_full_sha256 == target_v2
    assert experiment_fingerprint(final_experiment, include_layout=True) == target_v2
    assert experiment_fingerprint(experiment, include_layout=True) == target_v2
    assert {node.id for node in final_experiment.nodes} == {"src", "sink-a", "sink-b"}

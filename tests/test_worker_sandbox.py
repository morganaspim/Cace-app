from __future__ import annotations

import os

import pytest

from cace_studio.app import build_registry
from cace_studio.agent_runtime import (
    AutonomyLoopBudget,
    CapabilityPolicy,
    FileAgentLeaseManager,
    FileAutonomySessionStore,
    FileCanvasPlanStore,
    FileCanvasPreviewStore,
    FileExperimentWorkspace,
    FileOperationStore,
    FileRunArtifactStore,
    FileRunControlStore,
    FileWorkerReceiptStore,
    ProcessSandboxLimits,
    ProcessScienceRunner,
    SandboxRequirements,
    ScienceWorkerError,
    ScienceWorkerTerminatedError,
    ToolBus,
    ToolCall,
    ToolStatus,
    autonomy_cycle_approval_callback,
    operation_id_for,
    register_autonomy_loop_tools,
    register_core_tools,
    register_canvas_mutation_tools,
    register_canvas_plan_tools,
)
from cace_studio.core.graph import Experiment, Node
from cace_studio.core.registry import ModuleRegistry
from cace_studio.modules.builtin import Constant


def _experiment() -> Experiment:
    return Experiment(
        name="sandbox",
        nodes=[
            Node(
                id="constant",
                module_id="core.constant",
                params={"value": 7.0},
            )
        ],
    )


def _runner(tmp_path, *, registry=None) -> ProcessScienceRunner:
    return ProcessScienceRunner(
        registry=registry or build_registry(),
        control_store=FileRunControlStore(tmp_path / "controls"),
        receipt_store=FileWorkerReceiptStore(tmp_path / "receipts"),
        poll_seconds=0.01,
        terminate_grace_seconds=0.05,
    )


def test_process_science_runner_executes_canonical_registry_in_child(tmp_path) -> None:
    runner = _runner(tmp_path)
    outcome = runner.run(
        experiment=_experiment(),
        target_node_ids=(),
        external_inputs={},
        seed=17,
        gpu_enabled=False,
        control_id="sandbox-success",
        limits=ProcessSandboxLimits(
            max_wall_seconds=30.0,
            max_cpu_seconds=20.0,
            max_memory_bytes=3_221_225_472,
            max_nodes=10,
            max_output_bytes=1_000_000,
        ),
        worker_nonce="success",
    )

    assert outcome.result.completed is True
    assert outcome.result.outputs["constant"]["value"] == 7.0
    assert outcome.receipt.outcome == "completed"
    assert outcome.receipt.result_sha256
    assert outcome.receipt.registry_sha256
    assert outcome.receipt.resource_enforcement["parent_wall_deadline"] is True
    assert outcome.receipt.resource_enforcement["parent_hard_cancel"] is True
    report = outcome.receipt.sandbox_capabilities
    assert report["sandbox_capability_schema"] == 1
    assert report["proof_effect"] == "none"
    assert report["promotion_authority"] is False
    assert set(report["controls"]) >= {
        "network_namespace",
        "user_namespace",
        "no_new_privs",
        "dumpability",
        "privilege_hardening",
        "landlock",
        "seccomp",
        "cgroup_v2",
        "mount_namespace",
        "private_tmp",
        "device_restrictions",
    }
    assert report["requirements"] == {
        "require_network_namespace": False,
        "require_seccomp_filter": False,
        "require_filesystem_restriction": False,
        "require_privilege_hardening": False,
        "require_cgroup_v2": False,
        "require_mount_namespace": False,
        "require_private_tmp": False,
        "require_device_restrictions": False,
    }
    cgroup = outcome.receipt.resource_enforcement["cgroup_v2"]
    assert cgroup["status"] in {"active", "prepared", "failed", "unavailable", "not-applicable"}
    if cgroup.get("active"):
        assert cgroup["attachment"]["active"] is True
        assert cgroup["usage"]["cpu_stat"]["usage_usec"] >= 0
    mount_ns = report["controls"]["mount_namespace"]
    if mount_ns["active"]:
        assert mount_ns["parent_inode"] != mount_ns["child_inode"]
    private_tmp = report["controls"]["private_tmp"]
    if private_tmp["active"]:
        assert private_tmp["path"] == "/tmp"
        assert private_tmp["nodev"] is True
        assert private_tmp["noexec"] is True
    devices = report["controls"]["device_restrictions"]
    if devices["active"]:
        assert devices["blocked_probe_success"] is True
    if os.name == "posix":
        assert outcome.receipt.resource_enforcement["memory_limit"]["kind"] == (
            "RLIMIT_AS"
        )
        assert outcome.receipt.resource_enforcement["cpu_limit"]["kind"] == (
            "RLIMIT_CPU"
        )

    stored = runner.receipt_store.load(outcome.receipt.worker_id)
    assert stored is not None
    assert stored.to_dict() == outcome.receipt.to_dict()


def test_parent_hard_wall_deadline_terminates_worker_process(tmp_path) -> None:
    runner = _runner(tmp_path)
    with pytest.raises(ScienceWorkerTerminatedError) as exc_info:
        runner.run(
            experiment=_experiment(),
            target_node_ids=(),
            external_inputs={},
            seed=0,
            gpu_enabled=False,
            control_id="sandbox-timeout",
            limits=ProcessSandboxLimits(
                max_wall_seconds=0.001,
                max_cpu_seconds=20.0,
                max_memory_bytes=3_221_225_472,
                max_nodes=10,
                max_output_bytes=1_000_000,
            ),
            worker_nonce="timeout",
        )

    receipt = exc_info.value.receipt
    assert receipt.outcome == "terminated"
    assert receipt.termination_reason == "hard-wall-deadline"
    assert runner.receipt_store.load(receipt.worker_id) is not None


def test_worker_rejects_registry_contract_mismatch(tmp_path) -> None:
    registry = ModuleRegistry()
    registry.register(Constant)
    runner = _runner(tmp_path, registry=registry)

    with pytest.raises(ScienceWorkerError, match="registry contract mismatch"):
        runner.run(
            experiment=_experiment(),
            target_node_ids=(),
            external_inputs={},
            seed=0,
            gpu_enabled=False,
            control_id="sandbox-registry-mismatch",
            limits=ProcessSandboxLimits(
                max_wall_seconds=30.0,
                max_cpu_seconds=20.0,
                max_memory_bytes=3_221_225_472,
                max_nodes=10,
                max_output_bytes=1_000_000,
            ),
            worker_nonce="registry-mismatch",
        )


def test_autonomy_cycle_uses_process_sandbox_and_returns_worker_receipt(tmp_path) -> None:
    registry = build_registry()
    experiment = _experiment()
    previews = FileCanvasPreviewStore(tmp_path / "previews")
    plans = FileCanvasPlanStore(tmp_path / "plans")
    workspace = FileExperimentWorkspace(tmp_path / "workspace", workspace_id="main")
    sessions = FileAutonomySessionStore(tmp_path / "sessions")
    artifacts = FileRunArtifactStore(tmp_path / "artifacts")
    controls = FileRunControlStore(tmp_path / "controls")
    worker_receipts = FileWorkerReceiptStore(tmp_path / "worker-receipts")
    operations = FileOperationStore(tmp_path / "operations")
    leases = FileAgentLeaseManager(tmp_path / "leases")

    bus = ToolBus(
        policy=CapabilityPolicy.zero_contact(),
        operation_store=operations,
        lease_validator=lambda call: leases.assert_current(
            call.run_id,
            call.lease_id,
            call.lease_generation,
        ),
    )
    canvas = register_canvas_mutation_tools(
        bus,
        registry=registry,
        active_experiment=experiment,
        preview_store=previews,
        workspace_store=workspace,
    )
    plan_runtime = register_canvas_plan_tools(
        bus,
        canvas_runtime=canvas,
        registry=registry,
        preview_store=previews,
        plan_store=plans,
        workspace_store=workspace,
    )
    process_runner = ProcessScienceRunner(
        registry=registry,
        control_store=controls,
        receipt_store=worker_receipts,
        poll_seconds=0.01,
        terminate_grace_seconds=0.05,
    )
    autonomy = register_autonomy_loop_tools(
        bus,
        registry=registry,
        plan_runtime=plan_runtime,
        plan_store=plans,
        workspace_store=workspace,
        session_store=sessions,
        run_artifact_store=artifacts,
        run_control_store=controls,
        process_science_runner=process_runner,
    )
    bus.approval_callback = autonomy_cycle_approval_callback(
        sessions,
        plans,
        lambda _payload: True,
    )

    preview = bus.invoke(
        ToolCall(
            "sandbox-plan-preview",
            "cace.canvas.preview_plan",
            {
                "steps": [
                    {
                        "step_id": "move",
                        "operations": [
                            {
                                "action": "move_node",
                                "node_id": "constant",
                                "position": [2.0, 3.0],
                            }
                        ],
                    }
                ]
            },
        )
    )
    assert preview.status is ToolStatus.OK
    session = autonomy.create_session(
        initial_plan_id=preview.output["plan_id"],
        session_id="sandbox-autonomy",
        budget=AutonomyLoopBudget(
            max_cycles=1,
            max_science_runs=1,
            max_replans=0,
            max_plan_steps_per_cycle=5,
            max_wall_seconds_per_run=30.0,
            max_nodes_per_run=10,
            max_output_bytes_per_run=1_000_000,
            max_artifact_bytes_per_run=10_000_000,
            max_cpu_seconds_per_run=20.0,
            max_memory_bytes_per_run=3_221_225_472,
        ),
    )
    lease = leases.acquire("sandbox-autonomy-run", "owner-a", ttl_seconds=60.0)
    arguments = {
        "session_id": session.session_id,
        "plan_id": preview.output["plan_id"],
    }
    result = bus.invoke(
        ToolCall(
            "sandbox-autonomy-run:1",
            "cace.autonomy.advance",
            arguments,
            run_id="sandbox-autonomy-run",
            operation_id=operation_id_for(
                run_id="sandbox-autonomy-run",
                ordinal=1,
                tool_name="cace.autonomy.advance",
                arguments=arguments,
            ),
            lease_id=lease.lease_id,
            lease_generation=lease.generation,
        )
    )

    assert result.status is ToolStatus.OK
    assert result.output["worker_receipt_id"]
    assert result.output["run_artifact_id"]
    worker = worker_receipts.load(result.output["worker_receipt_id"])
    assert worker is not None
    assert worker.outcome == "completed"
    assert worker.registry_sha256
    assert worker.sandbox_capabilities["sandbox_capability_schema"] == 1

    inspected_worker = bus.invoke(
        ToolCall(
            "inspect-worker",
            "cace.autonomy.inspect_worker_receipt",
            {"worker_receipt_id": result.output["worker_receipt_id"]},
        )
    )
    assert inspected_worker.status is ToolStatus.OK
    assert inspected_worker.output["receipt"]["worker_id"] == worker.worker_id
    assert inspected_worker.output["receipt"]["proof_effect"] == "none"

    artifact = artifacts.load(result.output["run_artifact_id"])
    assert artifact is not None
    assert artifact["run_id"] == result.output["science_run_id"]


def test_strict_linux_hardening_is_active_or_fails_closed_with_capability_report(tmp_path) -> None:
    runner = ProcessScienceRunner(
        registry=build_registry(),
        control_store=FileRunControlStore(tmp_path / "strict-controls"),
        receipt_store=FileWorkerReceiptStore(tmp_path / "strict-receipts"),
        poll_seconds=0.01,
        terminate_grace_seconds=0.05,
        sandbox_requirements=SandboxRequirements(
            require_network_namespace=True,
            require_seccomp_filter=True,
            require_filesystem_restriction=True,
            require_privilege_hardening=True,
        ),
    )

    try:
        outcome = runner.run(
            experiment=_experiment(),
            target_node_ids=(),
            external_inputs={},
            seed=0,
            gpu_enabled=False,
            control_id="sandbox-strict",
            limits=ProcessSandboxLimits(
                max_wall_seconds=30.0,
                max_cpu_seconds=20.0,
                max_memory_bytes=3_221_225_472,
                max_nodes=10,
                max_output_bytes=1_000_000,
            ),
            worker_nonce="strict",
        )
    except ScienceWorkerError as exc:
        assert exc.receipt is not None
        report = exc.receipt.sandbox_capabilities
        assert report["sandbox_capability_schema"] == 1
        assert report["all_required_active"] is False
        required = report["requirements"]
        assert required == {
            "require_network_namespace": True,
            "require_seccomp_filter": True,
            "require_filesystem_restriction": True,
            "require_privilege_hardening": True,
            "require_cgroup_v2": False,
            "require_mount_namespace": False,
            "require_private_tmp": False,
            "require_device_restrictions": False,
        }
        controls = report["controls"]
        assert any(
            not controls[name]["active"]
            for name in (
                "network_namespace",
                "seccomp",
                "landlock",
                "privilege_hardening",
            )
        )
    else:
        report = outcome.receipt.sandbox_capabilities
        assert report["all_required_active"] is True
        for name in (
            "network_namespace",
            "seccomp",
            "landlock",
            "privilege_hardening",
        ):
            assert report["controls"][name]["active"] is True
            assert report["controls"][name]["status"] == "active"


def test_linux_hardening_flag_requires_process_sandbox() -> None:
    bus = ToolBus(policy=CapabilityPolicy.zero_contact())
    with pytest.raises(
        ValueError,
        match="Linux autonomy hardening requires autonomy_use_process_sandbox",
    ):
        register_core_tools(
            bus,
            autonomy_require_linux_hardening=True,
            autonomy_use_process_sandbox=False,
        )


def test_process_runner_minimum_hardening_is_persisted_into_session_budget(tmp_path) -> None:
    registry = build_registry()
    experiment = _experiment()
    previews = FileCanvasPreviewStore(tmp_path / "binding-previews")
    plans = FileCanvasPlanStore(tmp_path / "binding-plans")
    workspace = FileExperimentWorkspace(
        tmp_path / "binding-workspace",
        workspace_id="binding-main",
    )
    sessions = FileAutonomySessionStore(tmp_path / "binding-sessions")
    controls = FileRunControlStore(tmp_path / "binding-controls")
    receipts = FileWorkerReceiptStore(tmp_path / "binding-receipts")
    bus = ToolBus(policy=CapabilityPolicy.zero_contact())
    canvas = register_canvas_mutation_tools(
        bus,
        registry=registry,
        active_experiment=experiment,
        preview_store=previews,
        workspace_store=workspace,
    )
    plan_runtime = register_canvas_plan_tools(
        bus,
        canvas_runtime=canvas,
        registry=registry,
        preview_store=previews,
        plan_store=plans,
        workspace_store=workspace,
    )
    runner = ProcessScienceRunner(
        registry=registry,
        control_store=controls,
        receipt_store=receipts,
        sandbox_requirements=SandboxRequirements(
            require_network_namespace=True,
            require_seccomp_filter=True,
            require_filesystem_restriction=True,
            require_privilege_hardening=True,
        ),
    )
    autonomy = register_autonomy_loop_tools(
        bus,
        registry=registry,
        plan_runtime=plan_runtime,
        plan_store=plans,
        workspace_store=workspace,
        session_store=sessions,
        run_control_store=controls,
        process_science_runner=runner,
    )
    preview = bus.invoke(
        ToolCall(
            "binding-preview",
            "cace.canvas.preview_plan",
            {
                "steps": [
                    {
                        "step_id": "move",
                        "operations": [
                            {
                                "action": "move_node",
                                "node_id": "constant",
                                "position": [8.0, 9.0],
                            }
                        ],
                    }
                ]
            },
        )
    )
    assert preview.status is ToolStatus.OK
    session = autonomy.create_session(
        initial_plan_id=preview.output["plan_id"],
        session_id="binding-session",
    )
    assert session.budget.require_network_namespace is True
    assert session.budget.require_seccomp_filter is True
    assert session.budget.require_filesystem_restriction is True
    assert session.budget.require_privilege_hardening is True

    persisted = sessions.load(session.session_id)
    assert persisted is not None
    assert persisted.budget.to_dict() == session.budget.to_dict()


def test_strict_v111_process_tree_hardening_is_active_or_fails_closed(tmp_path) -> None:
    requirements = SandboxRequirements(
        require_network_namespace=True,
        require_seccomp_filter=True,
        require_filesystem_restriction=True,
        require_privilege_hardening=True,
        require_cgroup_v2=True,
        require_mount_namespace=True,
        require_private_tmp=True,
        require_device_restrictions=True,
    )
    runner = ProcessScienceRunner(
        registry=build_registry(),
        control_store=FileRunControlStore(tmp_path / "v111-controls"),
        receipt_store=FileWorkerReceiptStore(tmp_path / "v111-receipts"),
        poll_seconds=0.01,
        terminate_grace_seconds=0.05,
        sandbox_requirements=requirements,
    )

    try:
        outcome = runner.run(
            experiment=_experiment(),
            target_node_ids=(),
            external_inputs={},
            seed=0,
            gpu_enabled=False,
            control_id="sandbox-v111-strict",
            limits=ProcessSandboxLimits(
                max_wall_seconds=30.0,
                max_cpu_seconds=20.0,
                max_memory_bytes=3_221_225_472,
                max_nodes=10,
                max_output_bytes=1_000_000,
                max_pids=32,
                max_cpu_cores=2.0,
            ),
            worker_nonce="v111-strict",
        )
    except ScienceWorkerError as exc:
        assert exc.receipt is not None
        report = exc.receipt.sandbox_capabilities
        assert report["sandbox_capability_schema"] == 1
        assert report["all_required_active"] is False
        assert report["requirements"] == requirements.to_dict()
        controls = report["controls"]
        assert any(
            not controls[name]["active"]
            for name in (
                "network_namespace",
                "seccomp",
                "landlock",
                "privilege_hardening",
                "cgroup_v2",
                "mount_namespace",
                "private_tmp",
                "device_restrictions",
            )
        )
    else:
        report = outcome.receipt.sandbox_capabilities
        assert report["all_required_active"] is True
        assert report["requirements"] == requirements.to_dict()
        for name in (
            "network_namespace",
            "seccomp",
            "landlock",
            "privilege_hardening",
            "cgroup_v2",
            "mount_namespace",
            "private_tmp",
            "device_restrictions",
        ):
            assert report["controls"][name]["active"] is True
        cgroup = outcome.receipt.resource_enforcement["cgroup_v2"]
        assert cgroup["active"] is True
        assert cgroup["attachment"]["active"] is True
        assert cgroup["limits"]["max_pids"] == 32
        assert cgroup["limits"]["max_cpu_cores"] == 2.0


def test_v111_strict_budget_enables_all_kernel_controls() -> None:
    budget = AutonomyLoopBudget.strict_linux_sandbox(
        max_pids_per_run=17,
        max_cpu_cores_per_run=1.5,
    )
    assert budget.max_pids_per_run == 17
    assert budget.max_cpu_cores_per_run == 1.5
    assert budget.require_network_namespace is True
    assert budget.require_seccomp_filter is True
    assert budget.require_filesystem_restriction is True
    assert budget.require_privilege_hardening is True
    assert budget.require_cgroup_v2 is True
    assert budget.require_mount_namespace is True
    assert budget.require_private_tmp is True
    assert budget.require_device_restrictions is True


def test_process_tree_hardening_flag_requires_process_sandbox() -> None:
    bus = ToolBus(policy=CapabilityPolicy.zero_contact())
    with pytest.raises(
        ValueError,
        match="Linux autonomy hardening requires autonomy_use_process_sandbox",
    ):
        register_core_tools(
            bus,
            autonomy_require_linux_process_tree_hardening=True,
            autonomy_use_process_sandbox=False,
        )


def test_gpu_run_cannot_claim_minimal_device_isolation(tmp_path) -> None:
    runner = ProcessScienceRunner(
        registry=build_registry(),
        control_store=FileRunControlStore(tmp_path / "gpu-controls"),
        receipt_store=FileWorkerReceiptStore(tmp_path / "gpu-receipts"),
        poll_seconds=0.01,
        terminate_grace_seconds=0.05,
        sandbox_requirements=SandboxRequirements(
            require_device_restrictions=True,
        ),
    )
    with pytest.raises(ScienceWorkerError) as exc_info:
        runner.run(
            experiment=_experiment(),
            target_node_ids=(),
            external_inputs={},
            seed=0,
            gpu_enabled=True,
            control_id="gpu-device-profile",
            limits=ProcessSandboxLimits(
                max_wall_seconds=30.0,
                max_cpu_seconds=20.0,
                max_memory_bytes=3_221_225_472,
                max_nodes=10,
                max_output_bytes=1_000_000,
            ),
            worker_nonce="gpu-device-profile",
        )
    receipt = exc_info.value.receipt
    assert receipt is not None
    report = receipt.sandbox_capabilities
    assert report["requirements"]["require_device_restrictions"] is True
    assert report["controls"]["device_restrictions"]["active"] is False

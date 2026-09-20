from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Mapping

from cace_studio.core.execution_control import ExecutionControl, ExecutionLimits
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.reproducibility import registry_contract_fingerprint
from cace_studio.core.serialization import experiment_from_data

from .execution_containment import FileRunControlStore
from .linux_sandbox import (
    SandboxRequirementError,
    SandboxRequirements,
    apply_linux_worker_sandbox,
)
from .worker_transport import run_result_to_data


def _apply_posix_limits(
    *,
    max_memory_bytes: int | None,
    max_cpu_seconds: float | None,
) -> dict[str, Any]:
    applied: dict[str, Any] = {
        "platform": sys.platform,
        "memory_limit": "unsupported",
        "cpu_limit": "unsupported",
    }
    if os.name != "posix":
        return applied
    import resource

    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except Exception:
        pass

    if max_memory_bytes is not None:
        limit = int(max_memory_bytes)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        applied["memory_limit"] = {
            "kind": "RLIMIT_AS",
            "bytes": limit,
        }

    if max_cpu_seconds is not None:
        soft = max(1, int(math.ceil(max_cpu_seconds)))
        hard = soft + 1
        resource.setrlimit(resource.RLIMIT_CPU, (soft, hard))
        applied["cpu_limit"] = {
            "kind": "RLIMIT_CPU",
            "soft_seconds": soft,
            "hard_seconds": hard,
        }
    return applied


def _require_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def worker_main(argv: list[str] | None = None) -> int:
    sandbox_report = None
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise ValueError("worker request must be an object")
        if request.get("science_worker_request_schema") != 1:
            raise ValueError("unsupported science worker request schema")

        limits = _require_mapping(request.get("limits", {}), name="limits")
        requirements_raw = _require_mapping(
            request.get("sandbox_requirements", {}),
            name="sandbox_requirements",
        )
        requirements = SandboxRequirements.from_dict(requirements_raw)

        control_root = Path(str(request["control_root"]))
        job_dir = args.result.parent.resolve()
        read_only_paths = [
            Path.cwd(),
            Path(__file__).resolve().parents[2],
            Path(sys.prefix),
            Path(sys.base_prefix),
            control_root,
            "/usr",
            "/lib",
            "/lib64",
            "/etc",
            "/proc",
            "/dev",
            "/sys",
        ]
        read_only_paths.extend(
            Path(item)
            for item in sys.path
            if isinstance(item, str) and item.strip()
        )
        try:
            sandbox_report = apply_linux_worker_sandbox(
                parent_netns_inode=(
                    int(request["parent_netns_inode"])
                    if request.get("parent_netns_inode") is not None
                    else None
                ),
                read_only_paths=read_only_paths,
                read_write_paths=[job_dir],
                requirements=requirements,
            )
        except SandboxRequirementError as exc:
            args.result.write_text(
                json.dumps(
                    {
                        "science_worker_result_schema": 1,
                        "status": "error",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "sandbox_capability_report": exc.report.to_dict(),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ),
                encoding="utf-8",
            )
            return 71

        enforcement = _apply_posix_limits(
            max_memory_bytes=(
                int(limits["max_memory_bytes"])
                if limits.get("max_memory_bytes") is not None
                else None
            ),
            max_cpu_seconds=(
                float(limits["max_cpu_seconds"])
                if limits.get("max_cpu_seconds") is not None
                else None
            ),
        )

        from cace_studio.app import build_registry

        registry = build_registry()
        actual_registry_sha = registry_contract_fingerprint(registry)
        expected_registry_sha = str(request["expected_registry_sha256"])
        if actual_registry_sha != expected_registry_sha:
            raise RuntimeError(
                "worker registry contract mismatch: "
                f"expected {expected_registry_sha}, got {actual_registry_sha}"
            )

        experiment = experiment_from_data(
            dict(_require_mapping(request["experiment"], name="experiment"))
        )
        external_inputs_raw = _require_mapping(
            request.get("external_inputs", {}),
            name="external_inputs",
        )
        external_inputs = {
            str(node_id): dict(
                _require_mapping(values, name=f"external_inputs[{node_id!r}]")
            )
            for node_id, values in external_inputs_raw.items()
        }
        target_node_ids_raw = request.get("target_node_ids", [])
        if not isinstance(target_node_ids_raw, list):
            raise ValueError("target_node_ids must be an array")
        target_node_ids = tuple(str(item) for item in target_node_ids_raw)

        control_id = str(request["control_id"])
        control_store = FileRunControlStore(control_root)
        control = ExecutionControl(
            limits=ExecutionLimits(
                max_wall_seconds=(
                    float(limits["max_wall_seconds"])
                    if limits.get("max_wall_seconds") is not None
                    else None
                ),
                max_nodes=(
                    int(limits["max_nodes"])
                    if limits.get("max_nodes") is not None
                    else None
                ),
                max_output_bytes=(
                    int(limits["max_output_bytes"])
                    if limits.get("max_output_bytes") is not None
                    else None
                ),
            ),
            external_state_provider=lambda: control_store.state_readonly(control_id),
        )
        executor = GraphExecutor(
            registry,
            gpu_enabled=bool(request.get("gpu_enabled", False)),
        )
        seed = int(request.get("seed", 0))
        if target_node_ids:
            result = executor.run_selected_upstream(
                experiment,
                target_node_ids,
                external_inputs=external_inputs,
                seed=seed,
                control=control,
            )
        else:
            result = executor.run(
                experiment,
                external_inputs=external_inputs,
                seed=seed,
                control=control,
            )

        payload = {
            "science_worker_result_schema": 1,
            "status": "ok",
            "registry_sha256": actual_registry_sha,
            "resource_enforcement": enforcement,
            "sandbox_capability_report": sandbox_report.to_dict(),
            "run_result": run_result_to_data(result),
        }
        args.result.write_text(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ),
            encoding="utf-8",
        )
        return 0
    except BaseException as exc:
        try:
            args.result.write_text(
                json.dumps(
                    {
                        "science_worker_result_schema": 1,
                        "status": "error",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        **(
                            {
                                "sandbox_capability_report": sandbox_report.to_dict()
                            }
                            if sandbox_report is not None
                            else {}
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass
        return 70


if __name__ == "__main__":
    raise SystemExit(worker_main())

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping
from uuid import uuid4

from cace_studio.core.executor import RunResult
from cace_studio.core.graph import Experiment
from cace_studio.core.reproducibility import (
    registry_contract_fingerprint,
    sha256_identity,
)
from cace_studio.core.serialization import experiment_to_data
from cace_studio.core.registry import ModuleRegistry

from .durability import (
    CrossProcessFileLock,
    atomic_write_json,
    hashed_envelope,
    validate_hashed_envelope,
)
from .execution_containment import FileRunControlStore, RunControlState
from .linux_sandbox import SandboxRequirements
from .worker_transport import run_result_from_data


class ScienceWorkerError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        receipt: "WorkerExecutionReceipt | None" = None,
    ) -> None:
        super().__init__(message)
        self.receipt = receipt


class ScienceWorkerTerminatedError(ScienceWorkerError):
    def __init__(self, message: str, *, receipt: "WorkerExecutionReceipt") -> None:
        super().__init__(message, receipt=receipt)


@dataclass(frozen=True)
class ProcessSandboxLimits:
    max_wall_seconds: float
    max_cpu_seconds: float
    max_memory_bytes: int
    max_nodes: int
    max_output_bytes: int

    def __post_init__(self) -> None:
        if self.max_wall_seconds <= 0:
            raise ValueError("max_wall_seconds must be positive")
        if self.max_cpu_seconds <= 0:
            raise ValueError("max_cpu_seconds must be positive")
        if self.max_memory_bytes <= 0:
            raise ValueError("max_memory_bytes must be positive")
        if self.max_nodes <= 0:
            raise ValueError("max_nodes must be positive")
        if self.max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_wall_seconds": self.max_wall_seconds,
            "max_cpu_seconds": self.max_cpu_seconds,
            "max_memory_bytes": self.max_memory_bytes,
            "max_nodes": self.max_nodes,
            "max_output_bytes": self.max_output_bytes,
        }


@dataclass(frozen=True)
class WorkerExecutionReceipt:
    worker_id: str
    request_sha256: str
    started_unix: float
    finished_unix: float
    pid: int
    exit_code: int | None
    outcome: str
    termination_reason: str
    result_sha256: str
    registry_sha256: str
    limits: Mapping[str, Any]
    resource_enforcement: Mapping[str, Any]
    sandbox_capabilities: Mapping[str, Any]
    stderr_tail: str = ""
    proof_effect: str = "none"
    promotion_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_receipt_schema": 1,
            "worker_id": self.worker_id,
            "request_sha256": self.request_sha256,
            "started_unix": self.started_unix,
            "finished_unix": self.finished_unix,
            "pid": self.pid,
            "exit_code": self.exit_code,
            "outcome": self.outcome,
            "termination_reason": self.termination_reason,
            "result_sha256": self.result_sha256,
            "registry_sha256": self.registry_sha256,
            "limits": dict(self.limits),
            "resource_enforcement": dict(self.resource_enforcement),
            "sandbox_capabilities": dict(self.sandbox_capabilities),
            "stderr_tail": self.stderr_tail,
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "WorkerExecutionReceipt":
        if payload.get("worker_receipt_schema") != 1:
            raise ValueError("unsupported worker receipt schema")
        if payload.get("proof_effect", "none") != "none" or bool(
            payload.get("promotion_authority", False)
        ):
            raise ValueError("worker receipt cannot carry proof authority")
        limits = payload.get("limits", {})
        enforcement = payload.get("resource_enforcement", {})
        sandbox_capabilities = payload.get("sandbox_capabilities", {})
        if (
            not isinstance(limits, Mapping)
            or not isinstance(enforcement, Mapping)
            or not isinstance(sandbox_capabilities, Mapping)
        ):
            raise ValueError(
                "worker receipt limits/enforcement/sandbox capabilities must be objects"
            )
        return cls(
            worker_id=str(payload["worker_id"]),
            request_sha256=str(payload["request_sha256"]),
            started_unix=float(payload["started_unix"]),
            finished_unix=float(payload["finished_unix"]),
            pid=int(payload["pid"]),
            exit_code=(
                int(payload["exit_code"])
                if payload.get("exit_code") is not None
                else None
            ),
            outcome=str(payload["outcome"]),
            termination_reason=str(payload.get("termination_reason", "")),
            result_sha256=str(payload.get("result_sha256", "")),
            registry_sha256=str(payload.get("registry_sha256", "")),
            limits=dict(limits),
            resource_enforcement=dict(enforcement),
            sandbox_capabilities=dict(sandbox_capabilities),
            stderr_tail=str(payload.get("stderr_tail", "")),
        )


class FileWorkerReceiptStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, worker_id: str) -> Path:
        if len(worker_id) != 64 or any(
            ch not in "0123456789abcdef" for ch in worker_id
        ):
            raise ValueError("worker_id must be lowercase SHA-256")
        return self.root / f"{worker_id}.json"

    def save(self, receipt: WorkerExecutionReceipt) -> None:
        path = self._path(receipt.worker_id)
        with CrossProcessFileLock(self.root / f".{receipt.worker_id}.lock"):
            envelope = hashed_envelope(
                schema_key="worker_receipt_envelope_schema",
                schema_value=1,
                digest_key="worker_receipt_sha256",
                payload_key="receipt",
                payload=receipt.to_dict(),
            )
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                existing = validate_hashed_envelope(
                    raw,
                    schema_key="worker_receipt_envelope_schema",
                    schema_value=1,
                    digest_key="worker_receipt_sha256",
                    payload_key="receipt",
                )
                if existing != receipt.to_dict():
                    raise ValueError(
                        "worker_id collision with different execution receipt"
                    )
                return
            atomic_write_json(path, envelope)

    def load(self, worker_id: str) -> WorkerExecutionReceipt | None:
        path = self._path(worker_id)
        with CrossProcessFileLock(self.root / f".{worker_id}.lock"):
            if not path.exists():
                return None
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = validate_hashed_envelope(
                raw,
                schema_key="worker_receipt_envelope_schema",
                schema_value=1,
                digest_key="worker_receipt_sha256",
                payload_key="receipt",
            )
            return WorkerExecutionReceipt.from_dict(payload)


@dataclass(frozen=True)
class ProcessScienceOutcome:
    result: RunResult
    receipt: WorkerExecutionReceipt


class ProcessScienceRunner:
    """Run canonical CACE science in a separate Python worker process.

    The child independently rebuilds and fingerprints the canonical registry.
    On POSIX the child applies RLIMIT_AS and RLIMIT_CPU. The parent separately
    enforces a hard wall deadline and hard cancellation by terminating/killing
    the process group. Pause remains cooperative at module boundaries.
    """

    def __init__(
        self,
        *,
        registry: ModuleRegistry,
        control_store: FileRunControlStore,
        receipt_store: FileWorkerReceiptStore,
        python_executable: str | None = None,
        poll_seconds: float = 0.05,
        terminate_grace_seconds: float = 0.5,
        sandbox_requirements: SandboxRequirements | None = None,
        clock=time.monotonic,
        wall_clock=time.time,
    ) -> None:
        self.registry = registry
        self.control_store = control_store
        self.receipt_store = receipt_store
        self.python_executable = python_executable or sys.executable
        self.poll_seconds = float(poll_seconds)
        self.terminate_grace_seconds = float(terminate_grace_seconds)
        self.sandbox_requirements = (
            sandbox_requirements or SandboxRequirements()
        )
        self._clock = clock
        self._wall_clock = wall_clock
        if self.poll_seconds <= 0 or self.terminate_grace_seconds < 0:
            raise ValueError("invalid process science runner timing")

    @staticmethod
    def _clean_environment(job_dir: Path) -> dict[str, str]:
        allowed = {
            "PATH",
            "PYTHONPATH",
            "VIRTUAL_ENV",
            "LD_LIBRARY_PATH",
            "LANG",
            "LC_ALL",
            "CUDA_VISIBLE_DEVICES",
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
        }
        env = {
            key: value
            for key, value in os.environ.items()
            if key in allowed
        }
        env["HOME"] = str(job_dir)
        env["TMPDIR"] = str(job_dir)
        env["XDG_CACHE_HOME"] = str(job_dir / ".cache")
        env["PYTHONNOUSERSITE"] = "1"
        env["CACE_SCIENCE_WORKER"] = "1"
        env["CACE_NETWORK_MODE"] = "LOCAL_ZERO_CONTACT"
        return env

    @staticmethod
    def _kill_process_group(proc: subprocess.Popen[bytes]) -> None:
        if proc.poll() is not None:
            return
        if os.name == "posix":
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                return
            except ProcessLookupError:
                return
            except Exception:
                pass
        proc.terminate()

    @staticmethod
    def _hard_kill_process_group(proc: subprocess.Popen[bytes]) -> None:
        if proc.poll() is not None:
            return
        if os.name == "posix":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
                return
            except ProcessLookupError:
                return
            except Exception:
                pass
        proc.kill()

    def run(
        self,
        *,
        experiment: Experiment,
        target_node_ids: tuple[str, ...],
        external_inputs: Mapping[str, Mapping[str, Any]],
        seed: int,
        gpu_enabled: bool,
        control_id: str,
        limits: ProcessSandboxLimits,
        worker_nonce: str,
        sandbox_requirements: SandboxRequirements | None = None,
    ) -> ProcessScienceOutcome:
        expected_registry_sha = registry_contract_fingerprint(self.registry)
        effective_requirements = (
            sandbox_requirements or self.sandbox_requirements
        )
        parent_netns_inode = None
        if sys.platform == "linux":
            try:
                parent_netns_inode = os.stat("/proc/self/ns/net").st_ino
            except OSError:
                parent_netns_inode = None

        request = {
            "science_worker_request_schema": 1,
            "experiment": experiment_to_data(experiment),
            "target_node_ids": list(target_node_ids),
            "external_inputs": {
                str(node_id): dict(values)
                for node_id, values in external_inputs.items()
            },
            "seed": int(seed),
            "gpu_enabled": bool(gpu_enabled),
            "expected_registry_sha256": expected_registry_sha,
            "control_root": str(self.control_store.root.resolve()),
            "control_id": control_id,
            "parent_netns_inode": parent_netns_inode,
            "sandbox_requirements": effective_requirements.to_dict(),
            "limits": limits.to_dict(),
        }
        request_sha = sha256_identity(request)
        worker_id = sha256_identity(
            {
                "science_worker_identity_schema": 1,
                "request_sha256": request_sha,
                "worker_nonce": worker_nonce,
                "attempt_uuid": str(uuid4()),
            }
        )
        started_unix = float(self._wall_clock())
        started_mono = float(self._clock())
        self.control_store.ensure_running(control_id)

        jobs_root = self.receipt_store.root / ".jobs"
        jobs_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=f"cace-worker-{worker_id[:12]}-",
            dir=jobs_root,
        ) as tmp:
            job_dir = Path(tmp)
            request_path = job_dir / "request.json"
            result_path = job_dir / "result.json"
            request_path.write_text(
                json.dumps(
                    request,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ),
                encoding="utf-8",
            )
            proc = subprocess.Popen(
                [
                    self.python_executable,
                    "-m",
                    "cace_studio.agent_runtime.science_worker",
                    "--request",
                    str(request_path),
                    "--result",
                    str(result_path),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self._clean_environment(job_dir),
                start_new_session=(os.name == "posix"),
            )
            termination_reason = ""
            while proc.poll() is None:
                state = self.control_store.state(control_id)
                if state == RunControlState.CANCELLED.value:
                    termination_reason = "hard-cancel"
                    self._kill_process_group(proc)
                    break
                if float(self._clock()) - started_mono >= limits.max_wall_seconds:
                    termination_reason = "hard-wall-deadline"
                    self._kill_process_group(proc)
                    break
                time.sleep(self.poll_seconds)

            if proc.poll() is None:
                deadline = float(self._clock()) + self.terminate_grace_seconds
                while proc.poll() is None and float(self._clock()) < deadline:
                    time.sleep(min(self.poll_seconds, 0.05))
            if proc.poll() is None:
                self._hard_kill_process_group(proc)
                termination_reason = termination_reason or "hard-kill"
            stdout, stderr = proc.communicate()
            exit_code = proc.returncode
            stderr_tail = stderr.decode("utf-8", errors="replace")[-4096:]

            payload: Mapping[str, Any] | None = None
            if result_path.exists():
                raw = json.loads(result_path.read_text(encoding="utf-8"))
                if not isinstance(raw, Mapping):
                    raise ScienceWorkerError("worker result must be an object")
                payload = raw

            finished_unix = float(self._wall_clock())
            if termination_reason:
                receipt = WorkerExecutionReceipt(
                    worker_id=worker_id,
                    request_sha256=request_sha,
                    started_unix=started_unix,
                    finished_unix=finished_unix,
                    pid=proc.pid,
                    exit_code=exit_code,
                    outcome="terminated",
                    termination_reason=termination_reason,
                    result_sha256="",
                    registry_sha256=expected_registry_sha,
                    limits=limits.to_dict(),
                    resource_enforcement={
                        "parent_wall_deadline": True,
                        "parent_hard_cancel": True,
                        "posix_rlimit_requested": os.name == "posix",
                    },
                    sandbox_capabilities={},
                    stderr_tail=stderr_tail,
                )
                self.receipt_store.save(receipt)
                raise ScienceWorkerTerminatedError(
                    f"science worker terminated: {termination_reason}",
                    receipt=receipt,
                )

            if payload is None:
                no_result_reason = "worker-produced-no-result"
                if os.name == "posix" and exit_code == -getattr(signal, "SIGXCPU", 24):
                    no_result_reason = "cpu-limit"
                elif os.name == "posix" and exit_code == -getattr(signal, "SIGKILL", 9):
                    no_result_reason = "resource-kill-unknown"
                receipt = WorkerExecutionReceipt(
                    worker_id=worker_id,
                    request_sha256=request_sha,
                    started_unix=started_unix,
                    finished_unix=finished_unix,
                    pid=proc.pid,
                    exit_code=exit_code,
                    outcome="crashed",
                    termination_reason=no_result_reason,
                    result_sha256="",
                    registry_sha256=expected_registry_sha,
                    limits=limits.to_dict(),
                    resource_enforcement={
                        "parent_wall_deadline": True,
                        "parent_hard_cancel": True,
                        "posix_rlimit_requested": os.name == "posix",
                    },
                    sandbox_capabilities={},
                    stderr_tail=stderr_tail,
                )
                self.receipt_store.save(receipt)
                raise ScienceWorkerTerminatedError(
                    "science worker exited without a result",
                    receipt=receipt,
                )

            if payload.get("science_worker_result_schema") != 1:
                raise ScienceWorkerError("unsupported science worker result schema")
            if payload.get("status") != "ok":
                receipt = WorkerExecutionReceipt(
                    worker_id=worker_id,
                    request_sha256=request_sha,
                    started_unix=started_unix,
                    finished_unix=finished_unix,
                    pid=proc.pid,
                    exit_code=exit_code,
                    outcome="error",
                    termination_reason=str(payload.get("error_type", "worker-error")),
                    result_sha256=sha256_identity(dict(payload)),
                    registry_sha256=expected_registry_sha,
                    limits=limits.to_dict(),
                    resource_enforcement={
                        "worker_error": str(payload.get("error", ""))[:2048],
                    },
                    sandbox_capabilities=(
                        dict(payload["sandbox_capability_report"])
                        if isinstance(
                            payload.get("sandbox_capability_report"),
                            Mapping,
                        )
                        else {}
                    ),
                    stderr_tail=stderr_tail,
                )
                self.receipt_store.save(receipt)
                raise ScienceWorkerError(
                    "science worker failed: "
                    f"{payload.get('error_type', 'Error')}: {payload.get('error', '')}",
                    receipt=receipt,
                )

            actual_registry_sha = str(payload.get("registry_sha256", ""))
            if actual_registry_sha != expected_registry_sha:
                raise ScienceWorkerError("worker returned mismatched registry identity")
            raw_result = payload.get("run_result")
            if not isinstance(raw_result, Mapping):
                raise ScienceWorkerError("worker run_result must be an object")
            result = run_result_from_data(raw_result)
            result_sha = sha256_identity(dict(raw_result))
            enforcement = payload.get("resource_enforcement", {})
            sandbox_capabilities = payload.get(
                "sandbox_capability_report", {}
            )
            if not isinstance(enforcement, Mapping):
                raise ScienceWorkerError(
                    "worker resource_enforcement must be an object"
                )
            if not isinstance(sandbox_capabilities, Mapping):
                raise ScienceWorkerError(
                    "worker sandbox_capability_report must be an object"
                )
            receipt = WorkerExecutionReceipt(
                worker_id=worker_id,
                request_sha256=request_sha,
                started_unix=started_unix,
                finished_unix=finished_unix,
                pid=proc.pid,
                exit_code=exit_code,
                outcome="completed",
                termination_reason="",
                result_sha256=result_sha,
                registry_sha256=actual_registry_sha,
                limits=limits.to_dict(),
                resource_enforcement={
                    **dict(enforcement),
                    "parent_wall_deadline": True,
                    "parent_hard_cancel": True,
                },
                sandbox_capabilities=dict(sandbox_capabilities),
                stderr_tail=stderr_tail,
            )
            self.receipt_store.save(receipt)
            return ProcessScienceOutcome(result=result, receipt=receipt)

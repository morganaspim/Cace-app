from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import shutil
import signal
import subprocess
from typing import Iterable


class SandboxUnavailable(RuntimeError):
    pass


class SandboxViolation(RuntimeError):
    pass


@dataclass(frozen=True)
class SandboxPolicy:
    memory_mb: int = 512
    cpus: float = 1.0
    pids_limit: int = 128
    wall_seconds: int = 300
    network: str = "none"
    read_only_root: bool = True
    no_new_privileges: bool = True
    cap_drop_all: bool = True

    def __post_init__(self) -> None:
        if self.memory_mb <= 0 or self.cpus <= 0 or self.pids_limit <= 0 or self.wall_seconds <= 0:
            raise ValueError("sandbox resource limits must be positive")
        if self.network != "none":
            raise ValueError("Growth Sandbox internet/network access must be denied")


@dataclass(frozen=True)
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str
    runtime: str
    command: tuple[str, ...]
    timed_out: bool


class GrowthSandbox:
    """Fail-closed container sandbox for experimental/self-growing execution.

    There is intentionally no unsafe local-subprocess fallback. If neither Podman
    nor Docker is available, autonomous growth is unavailable instead of silently
    executing with host privileges.
    """

    def __init__(self, policy: SandboxPolicy | None = None, *, runtime: str | None = None) -> None:
        self.policy = policy or SandboxPolicy()
        self.runtime = runtime or self._detect_runtime()

    @staticmethod
    def _detect_runtime() -> str:
        for candidate in ("podman", "docker"):
            path = shutil.which(candidate)
            if path:
                return path
        raise SandboxUnavailable("strict Growth Sandbox requires Podman or Docker")

    def build_command(
        self,
        *,
        image: str,
        argv: Iterable[str],
        input_dir: str | Path,
        output_dir: str | Path,
    ) -> list[str]:
        input_path = Path(input_dir).resolve()
        output_path = Path(output_dir).resolve()
        if not input_path.is_dir():
            raise ValueError("sandbox input_dir must exist and be a directory")
        output_path.mkdir(parents=True, exist_ok=True)

        command = [
            self.runtime,
            "run",
            "--rm",
            "--network=none",
            f"--memory={self.policy.memory_mb}m",
            f"--cpus={self.policy.cpus}",
            f"--pids-limit={self.policy.pids_limit}",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=64m",
            f"--mount=type=bind,src={input_path},dst=/cace/input,ro",
            f"--mount=type=bind,src={output_path},dst=/cace/output,rw",
        ]
        if self.policy.read_only_root:
            command.append("--read-only")
        command.append(image)
        command.extend(argv)
        return command

    def run(
        self,
        *,
        image: str,
        argv: Iterable[str],
        input_dir: str | Path,
        output_dir: str | Path,
    ) -> SandboxResult:
        command = self.build_command(
            image=image,
            argv=argv,
            input_dir=input_dir,
            output_dir=output_dir,
        )
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=self.policy.wall_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
        return SandboxResult(
            returncode=124 if timed_out else int(proc.returncode),
            stdout=stdout,
            stderr=stderr,
            runtime=Path(self.runtime).name,
            command=tuple(command),
            timed_out=timed_out,
        )


@dataclass(frozen=True)
class AirlockPolicy:
    max_files: int = 128
    max_total_bytes: int = 128 * 1024 * 1024
    allowed_suffixes: tuple[str, ...] = (
        ".json",
        ".txt",
        ".csv",
        ".npz",
        ".npy",
        ".cace",
        ".lean",
        ".md",
    )


@dataclass(frozen=True)
class AirlockManifest:
    schema: str
    file_count: int
    total_bytes: int
    files: tuple[tuple[str, int, str], ...]
    sha256: str


class Airlock:
    """Read-only inspection boundary between sandbox output and primary graph.

    Passing inspection never merges or elevates evidence. A separate explicit
    human authorization must reference the exact manifest SHA-256.
    """

    def __init__(self, policy: AirlockPolicy | None = None) -> None:
        self.policy = policy or AirlockPolicy()

    def inspect(self, output_dir: str | Path) -> AirlockManifest:
        root = Path(output_dir).resolve()
        if not root.is_dir():
            raise SandboxViolation("airlock output directory does not exist")
        rows: list[tuple[str, int, str]] = []
        total = 0
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise SandboxViolation(f"airlock rejects symlink: {rel}")
            if path.suffix.lower() not in self.policy.allowed_suffixes:
                raise SandboxViolation(f"airlock rejects file type: {rel}")
            size = path.stat().st_size
            total += size
            if len(rows) + 1 > self.policy.max_files:
                raise SandboxViolation("airlock file-count limit exceeded")
            if total > self.policy.max_total_bytes:
                raise SandboxViolation("airlock byte limit exceeded")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append((rel, size, digest))
        body = {
            "schema": "cace-airlock-manifest-v1",
            "file_count": len(rows),
            "total_bytes": total,
            "files": [list(row) for row in rows],
        }
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return AirlockManifest(
            schema=body["schema"],
            file_count=len(rows),
            total_bytes=total,
            files=tuple(rows),
            sha256=hashlib.sha256(encoded).hexdigest(),
        )

    @staticmethod
    def authorize(*, manifest: AirlockManifest, reviewer: str, approved_manifest_sha256: str) -> dict[str, str]:
        if not reviewer.strip():
            raise SandboxViolation("airlock authorization requires human reviewer identity")
        if approved_manifest_sha256 != manifest.sha256:
            raise SandboxViolation("airlock authorization does not match inspected manifest")
        return {
            "schema": "cace-airlock-approval-v1",
            "reviewer": reviewer.strip(),
            "manifest_sha256": manifest.sha256,
            "decision": "APPROVED_FOR_IMPORT",
        }

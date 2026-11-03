from __future__ import annotations

from dataclasses import dataclass
import errno
import os
from pathlib import Path
import signal
from typing import Any, Mapping


@dataclass(frozen=True)
class CgroupV2Limits:
    max_memory_bytes: int
    max_pids: int
    max_cpu_cores: float
    max_cpu_seconds: float

    def __post_init__(self) -> None:
        if self.max_memory_bytes <= 0:
            raise ValueError("max_memory_bytes must be positive")
        if self.max_pids <= 0:
            raise ValueError("max_pids must be positive")
        if self.max_cpu_cores <= 0:
            raise ValueError("max_cpu_cores must be positive")
        if self.max_cpu_seconds <= 0:
            raise ValueError("max_cpu_seconds must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_memory_bytes": self.max_memory_bytes,
            "max_pids": self.max_pids,
            "max_cpu_cores": self.max_cpu_cores,
            "max_cpu_seconds": self.max_cpu_seconds,
        }


@dataclass
class CgroupV2Handle:
    path: Path | None
    relative_path: str
    active: bool
    report: dict[str, Any]

    @property
    def cpu_budget_usec(self) -> int:
        limits = self.report.get("limits", {})
        return int(float(limits.get("max_cpu_seconds", 0.0)) * 1_000_000)

    def _read_text(self, name: str) -> str:
        if self.path is None:
            return ""
        try:
            return (self.path / name).read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    @staticmethod
    def _parse_key_values(text: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for line in text.splitlines():
            parts = line.split()
            if len(parts) != 2:
                continue
            try:
                result[parts[0]] = int(parts[1])
            except ValueError:
                continue
        return result

    def usage(self) -> dict[str, Any]:
        if self.path is None:
            return {}
        cpu = self._parse_key_values(self._read_text("cpu.stat"))
        memory_events = self._parse_key_values(
            self._read_text("memory.events")
        )
        pids_events = self._parse_key_values(self._read_text("pids.events"))
        values: dict[str, Any] = {
            "cpu_stat": cpu,
            "memory_events": memory_events,
            "pids_events": pids_events,
        }
        for name in (
            "memory.current",
            "memory.peak",
            "pids.current",
            "pids.peak",
        ):
            raw = self._read_text(name)
            if raw:
                try:
                    values[name.replace(".", "_")] = int(raw)
                except ValueError:
                    values[name.replace(".", "_")] = raw
        return values

    def cpu_budget_exceeded(self) -> bool:
        if not self.active:
            return False
        usage_usec = int(self.usage().get("cpu_stat", {}).get("usage_usec", 0))
        return usage_usec >= self.cpu_budget_usec > 0

    def attach(self, pid: int) -> dict[str, Any]:
        if not self.active or self.path is None:
            return {
                "status": "unavailable",
                "active": False,
                "attached": False,
                "detail": self.report.get("detail", "cgroup inactive"),
            }
        try:
            (self.path / "cgroup.procs").write_text(
                f"{int(pid)}\n",
                encoding="ascii",
            )
            members = {
                int(line)
                for line in (self.path / "cgroup.procs")
                .read_text(encoding="ascii")
                .splitlines()
                if line.strip().isdigit()
            }
            attached = int(pid) in members
            result = {
                "status": "active" if attached else "failed",
                "active": attached,
                "attached": attached,
                "pid": int(pid),
                "detail": (
                    "worker PID verified in delegated cgroup"
                    if attached
                    else "worker PID missing after cgroup.procs write"
                ),
            }
            self.report["attachment"] = result
            self.report["active"] = bool(attached)
            self.report["status"] = "active" if attached else "failed"
            return result
        except OSError as exc:
            result = {
                "status": "failed",
                "active": False,
                "attached": False,
                "pid": int(pid),
                "errno": exc.errno,
                "detail": f"{type(exc).__name__}: {exc}",
            }
            self.report["attachment"] = result
            self.report["active"] = False
            self.report["status"] = "failed"
            return result

    def member_pids(self) -> tuple[int, ...]:
        if self.path is None:
            return ()
        try:
            return tuple(
                int(line)
                for line in (self.path / "cgroup.procs")
                .read_text(encoding="ascii")
                .splitlines()
                if line.strip().isdigit()
            )
        except OSError:
            return ()

    def kill_tree(self) -> dict[str, Any]:
        if self.path is None:
            return {
                "active": False,
                "method": "none",
                "killed": False,
                "detail": "cgroup path unavailable",
            }
        kill_file = self.path / "cgroup.kill"
        if kill_file.exists():
            try:
                kill_file.write_text("1\n", encoding="ascii")
                return {
                    "active": True,
                    "method": "cgroup.kill",
                    "killed": True,
                }
            except OSError as exc:
                kill_error = f"{type(exc).__name__}: {exc}"
        else:
            kill_error = "cgroup.kill unavailable"

        killed_any = False
        errors: list[str] = []
        for _ in range(4):
            pids = self.member_pids()
            if not pids:
                break
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                    killed_any = True
                except ProcessLookupError:
                    continue
                except OSError as exc:
                    errors.append(f"{pid}:{type(exc).__name__}:{exc}")
        return {
            "active": True,
            "method": "cgroup.procs+SIGKILL",
            "killed": killed_any,
            "cgroup_kill_error": kill_error,
            "errors": errors,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            **dict(self.report),
            "usage": self.usage(),
            "member_pids": list(self.member_pids()),
        }

    def cleanup(self) -> dict[str, Any]:
        if self.path is None:
            return {"removed": False, "detail": "no cgroup path"}
        remaining = self.member_pids()
        kill = {}
        if remaining:
            kill = self.kill_tree()
        try:
            self.path.rmdir()
            return {
                "removed": True,
                "kill": kill,
                "remaining_before_cleanup": list(remaining),
            }
        except OSError as exc:
            return {
                "removed": False,
                "kill": kill,
                "remaining_before_cleanup": list(remaining),
                "detail": f"{type(exc).__name__}: {exc}",
            }


class CgroupV2Manager:
    """Best-effort cgroup v2 delegation with explicit capability reporting."""

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        prefix: str = "cace-worker",
    ) -> None:
        self.explicit_root = Path(root).expanduser() if root is not None else None
        self.prefix = prefix

    @staticmethod
    def _self_relative_path() -> str:
        try:
            lines = Path("/proc/self/cgroup").read_text(
                encoding="utf-8"
            ).splitlines()
        except OSError:
            return ""
        for line in lines:
            parts = line.split(":", 2)
            if len(parts) == 3 and parts[0] == "0":
                return parts[2] or "/"
        return ""

    def discover_root(self) -> Path | None:
        if self.explicit_root is not None:
            return self.explicit_root.resolve()
        env_root = os.environ.get("CACE_CGROUP_ROOT", "").strip()
        if env_root:
            return Path(env_root).expanduser().resolve()
        unified = Path("/sys/fs/cgroup")
        if not (unified / "cgroup.controllers").exists():
            return None
        relative = self._self_relative_path().lstrip("/")
        return (unified / relative).resolve()

    @staticmethod
    def _read_words(path: Path) -> tuple[str, ...]:
        try:
            return tuple(
                item
                for item in path.read_text(encoding="ascii").split()
                if item
            )
        except OSError:
            return ()

    @staticmethod
    def _enable_controllers(root: Path, controllers: tuple[str, ...]) -> dict[str, Any]:
        available = set(CgroupV2Manager._read_words(root / "cgroup.controllers"))
        requested = tuple(item for item in controllers if item in available)
        if not requested:
            return {
                "requested": list(controllers),
                "available": sorted(available),
                "enabled": [],
                "active": False,
                "detail": "required cgroup v2 controllers are not available",
            }
        subtree = root / "cgroup.subtree_control"
        try:
            current = set(CgroupV2Manager._read_words(subtree))
            missing = [item for item in requested if item not in current]
            if missing:
                with subtree.open("w", encoding="ascii") as handle:
                    handle.write(" ".join(f"+{item}" for item in missing) + "\n")
            after = set(CgroupV2Manager._read_words(subtree))
            enabled = [item for item in requested if item in after]
            return {
                "requested": list(controllers),
                "available": sorted(available),
                "enabled": enabled,
                "active": set(requested).issubset(after),
            }
        except OSError as exc:
            return {
                "requested": list(controllers),
                "available": sorted(available),
                "enabled": [],
                "active": False,
                "errno": exc.errno,
                "detail": f"{type(exc).__name__}: {exc}",
            }

    def prepare(
        self,
        worker_id: str,
        limits: CgroupV2Limits,
    ) -> CgroupV2Handle:
        if os.name != "posix" or not Path("/sys/fs/cgroup/cgroup.controllers").exists():
            report = {
                "status": "not-applicable",
                "active": False,
                "detail": "cgroup v2 unified hierarchy unavailable",
                "limits": limits.to_dict(),
            }
            return CgroupV2Handle(None, "", False, report)

        root = self.discover_root()
        if root is None:
            report = {
                "status": "unavailable",
                "active": False,
                "detail": "no cgroup v2 delegation root discovered",
                "limits": limits.to_dict(),
            }
            return CgroupV2Handle(None, "", False, report)

        controller_report = self._enable_controllers(
            root,
            ("cpu", "memory", "pids"),
        )
        if not controller_report.get("active", False):
            report = {
                "status": "unavailable",
                "active": False,
                "detail": "required cgroup controllers are not delegated/writable",
                "root": str(root),
                "controllers": controller_report,
                "limits": limits.to_dict(),
            }
            return CgroupV2Handle(None, "", False, report)

        safe = "".join(ch for ch in worker_id[:24] if ch.isalnum() or ch in "-_")
        child = root / f"{self.prefix}-{safe}"
        try:
            child.mkdir(mode=0o700)
            period = 100_000
            quota = max(1_000, int(limits.max_cpu_cores * period))
            writes = {
                "memory.max": str(limits.max_memory_bytes),
                "pids.max": str(limits.max_pids),
                "cpu.max": f"{quota} {period}",
            }
            if (child / "memory.oom.group").exists():
                writes["memory.oom.group"] = "1"
            for name, value in writes.items():
                (child / name).write_text(value + "\n", encoding="ascii")
            relative = self._relative_to_mount(child)
            report = {
                "status": "prepared",
                "active": True,
                "root": str(root),
                "path": str(child),
                "relative_path": relative,
                "controllers": controller_report,
                "limits": limits.to_dict(),
                "configured": writes,
                "cgroup_kill_available": (child / "cgroup.kill").exists(),
                "attachment": {
                    "status": "pending",
                    "active": False,
                    "attached": False,
                },
            }
            return CgroupV2Handle(child, relative, True, report)
        except OSError as exc:
            try:
                child.rmdir()
            except OSError:
                pass
            report = {
                "status": "unavailable",
                "active": False,
                "root": str(root),
                "detail": f"{type(exc).__name__}: {exc}",
                "errno": exc.errno,
                "limits": limits.to_dict(),
                "controllers": controller_report,
            }
            return CgroupV2Handle(None, "", False, report)

    @staticmethod
    def _relative_to_mount(path: Path) -> str:
        mount = Path("/sys/fs/cgroup").resolve()
        try:
            rel = path.resolve().relative_to(mount)
        except ValueError:
            return ""
        return "/" + str(rel)

    @staticmethod
    def verify_current_membership(
        expected_relative_path: str,
    ) -> dict[str, Any]:
        actual = CgroupV2Manager._self_relative_path()
        active = bool(expected_relative_path) and actual == expected_relative_path
        return {
            "status": "active" if active else "failed",
            "active": active,
            "expected_relative_path": expected_relative_path,
            "actual_relative_path": actual,
            "detail": (
                "worker /proc/self/cgroup matches delegated cgroup"
                if active
                else "worker cgroup membership does not match delegated cgroup"
            ),
        }

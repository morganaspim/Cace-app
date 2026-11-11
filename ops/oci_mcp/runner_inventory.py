from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import os
from pathlib import Path
import platform
import shutil
import subprocess
from typing import Any, Callable

RUNNER_ROOT = Path("/opt/actions-runner")


def _memory_total_bytes(meminfo: Path = Path("/proc/meminfo")) -> int | None:
    """Read only the aggregate MemTotal field; do not expose process memory."""
    try:
        for line in meminfo.read_text(encoding="ascii").splitlines():
            if line.startswith("MemTotal:"):
                fields = line.split()
                if len(fields) >= 2 and fields[1].isdigit():
                    return int(fields[1]) * 1024
    except (OSError, UnicodeError):
        return None
    return None


def _os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    """Return a small allowlist of non-secret OS identity fields."""
    allowed = {"ID", "VERSION_ID", "PRETTY_NAME"}
    result: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key in allowed:
                result[key.lower()] = value.strip().strip('"').strip("'")[:160]
    except (OSError, UnicodeError):
        pass
    return result


def _proc_listener_state(
    tcp: Path = Path("/proc/net/tcp"),
    tcp6: Path = Path("/proc/net/tcp6"),
) -> str:
    """Inspect kernel TCP tables read-only for a listening MCP port 8765."""
    observed = False
    loopback = False
    non_loopback = False
    for path, family in ((tcp, 4), (tcp6, 6)):
        try:
            lines = path.read_text(encoding="ascii").splitlines()
            observed = True
        except (OSError, UnicodeError):
            continue
        for line in lines[1:]:
            fields = line.split()
            if len(fields) < 4 or fields[3] != "0A":
                continue
            try:
                address_hex, port_hex = fields[1].split(":", 1)
                if int(port_hex, 16) != 8765:
                    continue
                raw = bytes.fromhex(address_hex)
                if family == 4:
                    address = ipaddress.IPv4Address(raw[::-1])
                else:
                    if len(raw) != 16:
                        continue
                    normalized = b"".join(
                        raw[index:index + 4][::-1]
                        for index in range(0, 16, 4)
                    )
                    address = ipaddress.IPv6Address(normalized)
            except (ValueError, TypeError):
                continue
            if address.is_loopback:
                loopback = True
            else:
                non_loopback = True
    if non_loopback:
        return "non_loopback"
    if loopback:
        return "loopback"
    return "not_listening" if observed else "unavailable"


def collect_runner_status(
    runner_root: Path = RUNNER_ROOT,
    *,
    run: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Collect bounded, read-only metadata; never read runner credential files."""
    root = Path(runner_root)
    exists = root.is_dir()
    result: dict[str, Any] = {
        "schema": "cace-oci-runner-inventory-v1",
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner_root": str(root),
        "directory_present": exists,
        "registration_metadata_present": (root / ".runner").is_file() if exists else False,
        "listener_script_present": (root / "run.sh").is_file() if exists else False,
        "credential_file_contents_read": False,
        "listener_process": "not_observed",
        "service_units": [],
        "github_online": "not_observed",
        "host": {
            "os": platform.system(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count(),
            "memory_total_bytes": _memory_total_bytes(),
            "os_release": _os_release(),
        },
        "actions_environment": {
            key: os.environ[key]
            for key in ("RUNNER_NAME", "RUNNER_OS", "RUNNER_ARCH", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")
            if os.environ.get(key)
        },
    }

    if exists:
        try:
            usage = shutil.disk_usage(root)
            result["filesystem"] = {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
            }
        except OSError as exc:
            result["filesystem_error"] = type(exc).__name__

    try:
        proc = run(
            ["/usr/bin/pgrep", "-x", "Runner.Listener"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        result["listener_process"] = "running" if proc.returncode == 0 else "not_running"
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["listener_process"] = "unavailable"
        result["listener_probe_error"] = type(exc).__name__

    try:
        service = run(
            ["/usr/bin/systemctl", "is-active", "--quiet", "cace-oci-mcp"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        result["oci_mcp_service"] = "active" if service.returncode == 0 else "not_active"
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["oci_mcp_service"] = "unavailable"
        result["oci_mcp_service_probe_error"] = type(exc).__name__

    result["oci_mcp_listener"] = _proc_listener_state()

    try:
        units = run(
            [
                "/usr/bin/systemctl",
                "list-units",
                "--all",
                "--type=service",
                "--no-legend",
                "--no-pager",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        matches = []
        if units.returncode == 0:
            for line in (units.stdout or "").splitlines():
                fields = line.split()
                if fields and (fields[0].startswith("actions.runner") or fields[0] == "cace-oci-mcp.service"):
                    matches.append(
                        {
                            "unit": fields[0],
                            "load": fields[1] if len(fields) > 1 else "unknown",
                            "active": fields[2] if len(fields) > 2 else "unknown",
                            "sub": fields[3] if len(fields) > 3 else "unknown",
                        }
                    )
        result["service_units"] = matches[:20]
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["service_probe_error"] = type(exc).__name__

    result["interpretation"] = (
        "Local runner process/service observations only. GitHub assignment or "
        "online state must be confirmed from a matching Actions job; this tool "
        "does not inspect credentials or contact GitHub."
    )
    return result

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable

RUNNER_ROOT = Path("/opt/actions-runner")


def collect_runner_status(
    runner_root: Path = RUNNER_ROOT,
    *,
    run: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Collect bounded, read-only metadata; never read runner credential files."""
    root = Path(runner_root)
    exists = root.is_dir()
    result: dict[str, Any] = {
        "runner_root": str(root),
        "directory_present": exists,
        "registration_metadata_present": (root / ".runner").is_file() if exists else False,
        "listener_script_present": (root / "run.sh").is_file() if exists else False,
        "credential_file_contents_read": False,
        "listener_process": "not_observed",
        "service_units": [],
        "github_online": "not_observed",
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
                if fields and fields[0].startswith("actions.runner"):
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

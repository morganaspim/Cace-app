"""Root-only fixed read diagnostics for our private Merlin service. No inputs."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

SERVICE = "merlin-dot-private.service"
SAFE_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}


def _command(arguments):
    try:
        result = subprocess.run(arguments, env=SAFE_ENV, cwd="/", capture_output=True,
                                timeout=10, check=False)
        return {"exit_code": result.returncode,
                "stdout": result.stdout[-16384:].decode("utf-8", "replace"),
                "stderr": result.stderr[-4096:].decode("utf-8", "replace"),
                "stdout_bytes": len(result.stdout), "stderr_bytes": len(result.stderr),
                "truncated": len(result.stdout) > 16384 or len(result.stderr) > 4096}
    except subprocess.TimeoutExpired as exc:
        return {"exit_code": None, "error_class": "TimeoutExpired",
                "stdout": (exc.stdout or b"")[-16384:].decode("utf-8", "replace"),
                "stderr": (exc.stderr or b"")[-4096:].decode("utf-8", "replace")}
    except OSError as exc:
        return {"exit_code": None, "error_class": type(exc).__name__, "errno": exc.errno}


def _file(path, *, content=False):
    try:
        info = path.lstat()
        result = {"path": str(path), "uid": info.st_uid, "gid": info.st_gid,
                  "mode": oct(stat.S_IMODE(info.st_mode)), "size_bytes": info.st_size}
        if stat.S_ISLNK(info.st_mode):
            return {**result, "kind": "symlink", "target": os.readlink(path)}
        if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
            return {**result, "kind": "not_bounded_regular_file"}
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
        try:
            raw = os.read(descriptor, 65537)
        finally:
            os.close(descriptor)
        result.update(kind="regular", sha256=hashlib.sha256(raw).hexdigest())
        if content:
            value = json.loads(raw)
            if isinstance(value, dict):
                fields = {"schema", "status", "error_class", "old_bundle_sha256", "new_bundle_sha256",
                          "old_config_sha256", "new_config_sha256", "service_uid", "service",
                          "state_seed_changed", "release", "previous_release", "config_backup",
                          "service_properties", "both_releases_preserved", "new_tools",
                          "new_manifest_sha256", "fixed_tool_probe", "qualification", "promotion_authority"}
                result["record"] = {key: value[key] for key in fields if key in value}
        return result
    except (OSError, ValueError, UnicodeError) as exc:
        return {"path": str(path), "error_class": type(exc).__name__, "errno": getattr(exc, "errno", None)}


def diagnose():
    if os.geteuid() != 0:
        raise PermissionError("fixed service diagnostics require root")
    history = Path("/etc/merlin-dot-private/upgrade-history")
    records = []
    try:
        names = sorted(name for name in os.listdir(history)
                       if re.fullmatch(r"(?:intent|result)-[0-9a-f]{64}\.json", name))
        records = [_file(history / name, content=True) for name in names[-8:]]
    except OSError as exc:
        records = [{"error_class": type(exc).__name__, "errno": exc.errno}]
    return {"schema": "merlin-dot-own-service-diagnostics/1", "read_only": True,
            "current": _file(Path("/opt/merlin-dot-private/current")),
            "config": _file(Path("/etc/merlin-dot-private/config.json")),
            "unit": _file(Path("/etc/systemd/system") / SERVICE),
            "systemctl": _command(["/usr/bin/systemctl", "show", SERVICE,
                "--property=ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,MainPID,User,Group,PrivateNetwork,NoNewPrivileges,RestrictAddressFamilies,DropInPaths,FragmentPath"]),
            "journal": _command(["/usr/bin/journalctl", "--unit=" + SERVICE,
                "--lines=40", "--no-pager", "--output=short-monotonic"]),
            "upgrade_records": records, "host_mutations": False,
            "private_database_content_read": False, "qualification": False, "promotion_authority": False}

"""Fixed non-secret host prerequisites; no installation or service changes."""
import json
import os
from pathlib import Path
import platform
import pwd
import shutil
import subprocess


def collect():
    safe_env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}
    candidates = ["/usr/bin/python3.12", "/usr/bin/python3.11", "/usr/bin/python3.10", "/usr/bin/python3"]
    interpreters = []
    for path in candidates:
        if not Path(path).is_file():
            continue
        try:
            p = subprocess.run([path, "-I", "-c", "import json,sys,sqlite3,venv; print(json.dumps({'version':list(sys.version_info[:3]),'sqlite':sqlite3.sqlite_version}))"], env=safe_env, capture_output=True, text=True, timeout=5)
            interpreters.append({"path": path, "returncode": p.returncode, "capabilities": json.loads(p.stdout) if p.returncode == 0 else None})
        except (OSError, ValueError, subprocess.TimeoutExpired) as e:
            interpreters.append({"path": path, "error": type(e).__name__})
    disk = shutil.disk_usage("/opt/actions-runner")
    stat = os.statvfs("/opt/actions-runner")
    sudo = shutil.which("sudo", path=safe_env["PATH"])
    can_sudo = False
    if sudo:
        try:
            can_sudo = subprocess.run([sudo, "-n", "/usr/bin/true"], env=safe_env, capture_output=True, timeout=5).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {
        "schema": "merlin-dot-host-preflight-v1",
        "runner": os.environ.get("RUNNER_NAME"), "architecture": platform.machine(),
        "uid": os.getuid(), "gid": os.getgid(), "username": pwd.getpwuid(os.getuid()).pw_name,
        "python_interpreters": interpreters,
        "filesystem": {"free_bytes": disk.free, "total_bytes": disk.total, "free_inodes": stat.f_favail},
        "sudo_noninteractive_true": can_sudo,
        "systemd_present": Path("/run/systemd/system").is_dir(),
        "executables": {name: shutil.which(name, path=safe_env["PATH"]) for name in ("systemctl", "ngspice", "FreeCADCmd", "freecadcmd", "git")},
        "existing_paths": {path: Path(path).exists() for path in ("/opt/merlin-dot", "/var/lib/merlin-dot", "/etc/systemd/system/merlin-dot-private.service")},
        "host_configuration_changed": False, "qualification": False,
    }

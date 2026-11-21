"""Fixed, credential-free OCI browser capability inventory; installs nothing.

The authenticated workflow pins this controller and its tests before execution.
Requests contain no command, URL, package name, filesystem path, or policy override.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
import uuid


REPOSITORY = "morganaspim/Cace-app"
BRANCH = "refs/heads/merlin/browser-operations-20261121"
RUNNER = "cace-oci-a1"
REQUEST_SCHEMA = "merlin-browser-inventory-request/1"
SAFE_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8", "HOME": "/var/empty",
            "XDG_CONFIG_HOME": "/var/empty", "XDG_CACHE_HOME": "/var/empty",
            "XDG_DATA_HOME": "/var/empty"}
BINARY_PATHS = (
    "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/usr/lib64/chromium-browser/chromium-browser",
    "/usr/lib64/chromium-browser/headless_shell",
    "/usr/bin/google-chrome", "/usr/bin/chromedriver",
    "/usr/bin/podman", "/usr/bin/docker", "/usr/bin/bwrap", "/usr/bin/unshare",
    "/usr/bin/rpm", "/usr/bin/dnf", "/usr/bin/node",
    "/usr/bin/python3", "/usr/bin/python3.11", "/usr/bin/python3.12",
    "/usr/bin/systemd-run", "/usr/bin/true",
)
VERSION_PATHS = frozenset(BINARY_PATHS) - {"/usr/bin/true", "/usr/bin/dnf"}
PACKAGE_NAMES = (
    "chromium", "chromium-common", "chromium-headless", "chromedriver",
    "bubblewrap", "podman", "docker-ce", "moby-engine", "python3",
    "python3-pip", "python3.11", "python3.12", "nodejs",
    "oracle-epel-release-el9", "dnf", "glibc", "nss", "nspr", "gtk3",
    "mesa-libgbm", "libX11", "fontconfig",
)
SYSCTL_PATHS = (
    "/proc/sys/user/max_user_namespaces",
    "/proc/sys/kernel/unprivileged_userns_clone",
    "/proc/sys/kernel/apparmor_restrict_unprivileged_userns",
)


class InventoryError(RuntimeError):
    pass


def unique(items):
    answer = {}
    for key, value in items:
        if key in answer:
            raise InventoryError("duplicate JSON field")
        answer[key] = value
    return answer


def decode(raw, maximum=16000):
    if len(raw) > maximum:
        raise InventoryError("input byte limit")
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(InventoryError("nonfinite JSON")))


def validate_request(request, identity):
    if (not isinstance(request, dict)
            or set(request) != {"schema", "request_id", "operation", "created_at"}
            or request["schema"] != REQUEST_SCHEMA
            or request["operation"] != "inventory"):
        raise InventoryError("fixed inventory request required")
    try:
        if str(uuid.UUID(request["request_id"])) != request["request_id"]:
            raise ValueError()
        when = datetime.fromisoformat(request["created_at"].replace("Z", "+00:00"))
        if when.tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise InventoryError("invalid request identity or timestamp")
    fields = {"repository", "ref", "runner", "workflow_commit", "run_id", "run_attempt", "controller_sha256"}
    if (not isinstance(identity, dict) or set(identity) != fields
            or identity["repository"] != REPOSITORY or identity["ref"] != BRANCH
            or identity["runner"] != RUNNER
            or not isinstance(identity["workflow_commit"], str)
            or not re.fullmatch("[0-9a-f]{40}", identity["workflow_commit"])
            or not isinstance(identity["controller_sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", identity["controller_sha256"])
            or any(type(identity[k]) is not int or identity[k] <= 0 for k in ("run_id", "run_attempt"))):
        raise InventoryError("unexpected authenticated invocation")


def read_regular(path, maximum, require_root=True):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_size > maximum
                or (require_root and (before.st_uid != 0 or before.st_mode & 0o022))):
            raise InventoryError("unsafe bounded regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            body = stream.read(maximum + 1)
        after = os.fstat(fd)
        if (len(body) > maximum or (before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_ino, after.st_size, after.st_mtime_ns)):
            raise InventoryError("file changed or limit exceeded")
        return body
    finally:
        os.close(fd)


def os_release():
    path = Path("/etc/os-release")
    if path.is_symlink():
        if path.resolve(strict=True) != Path("/usr/lib/os-release"):
            raise InventoryError("unexpected OS release link")
        path = Path("/usr/lib/os-release")
    raw = read_regular(path, 16000)
    answer = {}
    for line in raw.decode("utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key in {"ID", "VERSION_ID", "PRETTY_NAME"}:
            answer[key] = value.strip('"')[:256]
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "fields": answer}


def executable_identity(path):
    if path not in BINARY_PATHS:
        raise InventoryError("path is not in fixed binary inventory")
    supplied = Path(path)
    if not supplied.exists():
        return {"path": path, "present": False}
    real = supplied.resolve(strict=True)
    allowed = ("/usr/bin/", "/usr/sbin/", "/usr/lib64/", "/usr/libexec/")
    if not str(real).startswith(allowed):
        return {"path": path, "present": True, "usable_for_version_probe": False,
                "reason": "resolved path outside system binary roots"}
    info = real.stat()
    for parent in [real] + list(real.parents):
        row = parent.stat()
        if row.st_uid != 0 or row.st_mode & 0o022:
            return {"path": path, "present": True, "usable_for_version_probe": False,
                    "reason": "non-root-owned or writable system path"}
    safe = stat.S_ISREG(info.st_mode) and bool(info.st_mode & 0o111)
    return {"path": path, "present": True, "resolved_path": str(real),
            "size_bytes": info.st_size, "uid": info.st_uid,
            "mode": oct(stat.S_IMODE(info.st_mode)), "usable_for_version_probe": safe}


def run_fixed(argv, seconds=4, maximum=8192):
    """Bound a trusted fixed version/capability probe without shell or inherited env."""
    permitted = ((len(argv) == 2 and argv[0] in VERSION_PATHS and argv[1] == "--version")
                 or argv == ["/usr/bin/unshare", "--user", "--map-root-user", "/usr/bin/true"]
                 or argv == ["/usr/bin/rpm", "-q", "--qf", "%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n"] + list(PACKAGE_NAMES))
    if not permitted:
        raise InventoryError("probe is not fixed")
    start = time.monotonic()
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, cwd="/", env=SAFE_ENV,
                               start_new_session=True)
    result = bytearray()
    state = "completed"
    poll = selectors.DefaultSelector()
    try:
        poll.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = seconds - (time.monotonic() - start)
            if remaining <= 0:
                state = "timeout"
                break
            ready = poll.select(min(remaining, 0.1))
            if not ready:
                continue
            block = os.read(process.stdout.fileno(), min(4096, maximum + 1 - len(result)))
            if not block:
                break
            result.extend(block)
            if len(result) > maximum:
                state = "output_limit"
                break
        if state != "completed":
            os.killpg(process.pid, signal.SIGKILL)
        try:
            code = process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait(timeout=1)
            state = "timeout"
        return {"argv": argv, "returncode": code, "state": state,
                "elapsed_seconds": round(time.monotonic() - start, 6),
                "output": bytes(result[:maximum]).decode("utf-8", "replace")}
    finally:
        poll.close()
        process.stdout.close()
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=1)


def collect(request, identity):
    validate_request(request, identity)
    if os.geteuid() == 0:
        raise InventoryError("inventory must execute without root privileges")
    binaries = [executable_identity(path) for path in BINARY_PATHS]
    by_path = {row["path"]: row for row in binaries}
    versions = []
    for path in BINARY_PATHS:
        if path in VERSION_PATHS and by_path[path].get("usable_for_version_probe"):
            versions.append(run_fixed([path, "--version"]))
    packages = {"status": "rpm unavailable"}
    if by_path["/usr/bin/rpm"].get("usable_for_version_probe"):
        packages = run_fixed(["/usr/bin/rpm", "-q", "--qf", "%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n"] + list(PACKAGE_NAMES), seconds=8)
    modules = {}
    for name in ("playwright", "selenium", "pyee", "greenlet"):
        try:
            modules[name] = {"version": importlib.metadata.version(name), "status": "distribution_metadata_present"}
        except importlib.metadata.PackageNotFoundError:
            modules[name] = {"status": "not_in_isolated_system_python_path"}
    sysctls = {}
    for path in SYSCTL_PATHS:
        try:
            text = read_regular(path, 64).decode("ascii").strip()
            if not re.fullmatch("[0-9]+", text):
                raise InventoryError("non-numeric fixed sysctl")
            sysctls[path] = {"value": int(text)}
        except FileNotFoundError:
            sysctls[path] = {"status": "absent"}
        except (OSError, InventoryError) as exc:
            sysctls[path] = {"status": "unavailable", "error_type": type(exc).__name__}
    userns = {"status": "fixed unshare/true unavailable"}
    if all(by_path[path].get("usable_for_version_probe") for path in ("/usr/bin/unshare", "/usr/bin/true")):
        userns = run_fixed(["/usr/bin/unshare", "--user", "--map-root-user", "/usr/bin/true"])
    memory = {}
    for line in read_regular("/proc/meminfo", 16000).decode("ascii").splitlines():
        key, _, value = line.partition(":")
        if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            parts = value.split()
            if len(parts) == 2 and parts[1] == "kB":
                memory[key + "_kib"] = int(parts[0])
    disk = os.statvfs("/opt")
    return {"schema": "merlin-browser-host-inventory/1", "status": "collected",
            "observed_at": datetime.now(timezone.utc).isoformat(), "identity": identity,
            "request": request, "uid": os.geteuid(), "architecture": platform.machine(),
            "kernel_release": platform.release(), "python": sys.version,
            "os_release": os_release(), "cpu_count": os.cpu_count(), "memory": memory,
            "disk_opt": {"available_bytes": disk.f_bavail * disk.f_frsize,
                         "available_inodes": disk.f_favail},
            "cgroup_v2": Path("/sys/fs/cgroup/cgroup.controllers").is_file(),
            "binaries": binaries, "version_probes": versions, "packages": packages,
            "python_distributions": modules, "namespace_sysctls": sysctls,
            "unprivileged_user_namespace_probe": userns,
            "browser_launch_performed": False, "sandbox_qualified": False,
            "container_images_or_daemons_inspected": False, "repository_configuration_read": False,
            "host_configuration_changed": False, "private_state_accessed": False,
            "credentials_read": False, "controller_network_calls": 0,
            "child_network_syscalls_observed": False, "model_calls": 0,
            "existing_model_budget_changed": False, "qualification": False, "promotion_authority": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = decode(read_regular(args.request, 16000, require_root=False))
    identity = decode(read_regular(args.identity, 16000, require_root=False))
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != identity.get("controller_sha256"):
        raise InventoryError("controller source identity mismatch")
    result = collect(request, identity)
    body = (json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    if len(body) > 128 * 1024:
        raise InventoryError("inventory output ceiling")
    with args.output.open("xb") as stream:
        stream.write(body)
    print(json.dumps({"status": result["status"], "bytes": len(body),
                      "sha256": hashlib.sha256(body).hexdigest(), "host_configuration_changed": False}))


if __name__ == "__main__":
    main()

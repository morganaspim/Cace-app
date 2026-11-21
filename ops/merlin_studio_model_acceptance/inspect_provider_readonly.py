"""Root-readable provider identity only; no install, generation or service mutation.

The frozen original inspector bytes are authenticated before loading. Only its
inspect_ready() entry point is called. Root writes no files; JSON goes to stdout.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import stat
import subprocess
import sys

INSPECTOR_SHA256 = "f47637659c5d71e5d75cdb7198a0e07092a69f1b7857d45c92fa19be40bd8fa5"
INSPECTOR_BYTES = 57177
MANIFEST_SHA256 = "35cf7ea56185126587e7dc10bb400ec53df51057407f9920d0ab03aff4299203"
RECEIPT_SHA256 = "7b7489297414d8304f12e8c0e28aec8ddd806704889f8b17986eac8ada0cba57"
UNIT = "merlin-model-provider.service"
PROPERTIES = ("LoadState", "ActiveState", "SubState", "MainPID", "UnitFileState", "User", "Group",
              "MemoryMax", "MemorySwapMax", "CPUQuotaPerSecUSec", "TasksMax", "PrivateNetwork",
              "RestrictAddressFamilies", "FragmentPath", "Result", "ExecMainStatus")
READ_ONLY_ARGV = ["/usr/bin/systemctl", "show", UNIT, "--no-pager"] + ["--property=" + key for key in PROPERTIES]
CLEAN_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
             "SYSTEMD_PAGER": "", "SYSTEMD_COLORS": "0", "PYTHONDONTWRITEBYTECODE": "1"}


class InspectionError(RuntimeError):
    pass


def read_frozen(path):
    path = Path(path)
    if not path.is_absolute() or path.name != "frozen_provider_inspector.py":
        raise InspectionError("fixed frozen inspector filename required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size != INSPECTOR_BYTES:
            raise InspectionError("frozen inspector regular-file identity differs")
        raw = bytearray()
        while len(raw) <= INSPECTOR_BYTES:
            part = os.read(fd, min(65536, INSPECTOR_BYTES + 1 - len(raw)))
            if not part:
                break
            raw.extend(part)
        after = os.fstat(fd)
        if (len(raw) != INSPECTOR_BYTES or hashlib.sha256(raw).hexdigest() != INSPECTOR_SHA256
            or any(getattr(before, field) != getattr(after, field)
                   for field in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns"))):
            raise InspectionError("frozen inspector bytes differ")
        return bytes(raw)
    finally:
        os.close(fd)


def readonly_command(argv, *, allowed_codes=(0, 1, 4), **unused):
    if argv != READ_ONLY_ARGV or tuple(allowed_codes) != (0, 1, 4) or unused:
        raise InspectionError("only the fixed systemctl show operation is permitted")
    completed = subprocess.run(READ_ONLY_ARGV, cwd="/", env=CLEAN_ENV, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, check=False)
    if completed.returncode not in (0, 1, 4) or len(completed.stdout) + len(completed.stderr) > 32768:
        raise InspectionError("bounded systemctl observation failed")
    return completed.stdout


def denied(*args, **kwargs):
    raise InspectionError("mutating and inference entry points are unavailable in this wrapper")


def load_inspector(path):
    raw = read_frozen(path)
    namespace = {"__name__": "frozen_provider_readonly"}
    exec(compile(raw, "frozen_provider_inspector", "exec"), namespace)
    namespace["command"] = readonly_command
    # Definitions retain their original byte identity. Disable every entry point
    # outside the read-only dependency closure as an additional narrow guard.
    for name in ("run", "install", "build", "download", "smoke", "wait_ready", "rollback",
                 "write_new", "rooted_directory", "_authorize_source_recovery"):
        if name in namespace:
            namespace[name] = denied
    return namespace


def inspect(path):
    namespace = load_inspector(path)
    for filename, expected, maximum in (
            ("/etc/merlin-model-provider/manifest.json", MANIFEST_SHA256, 16384),
            ("/etc/merlin-model-provider/bootstrap-receipt.json", RECEIPT_SHA256, 65536)):
        raw = namespace["read_regular"](filename, maximum)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise InspectionError("fixed provider authority record differs")
    result = namespace["inspect_ready"]()
    if (result.get("schema") != "merlin-local-model-inspect/1" or result.get("status") != "ready"
        or result.get("manifest_sha256") != MANIFEST_SHA256
        or result.get("bootstrap_receipt_sha256") != RECEIPT_SHA256
        or result.get("inference_requests") != 0 or result.get("qualification") is not False):
        raise InspectionError("frozen read-only inspection returned an unexpected receipt")
    return {"schema": "merlin-studio-root-provider-inspection/1", "passed": True,
            "inspector_sha256": INSPECTOR_SHA256, "inspection": result,
            "service_mutations": False, "model_generation_calls": 0,
            "file_writes": 0, "source_entry_point": "inspect_ready"}


def expired(signum, frame):
    raise TimeoutError("root read-only inspection exceeded 90 seconds")


def main():
    try:
        if len(sys.argv) != 2 or os.geteuid() != 0 or platform.system() != "Linux" or platform.machine() != "aarch64":
            raise InspectionError("fixed root-readable Linux aarch64 inspection only")
        os.chdir("/")
        os.environ.clear()
        os.environ.update(CLEAN_ENV)
        signal.signal(signal.SIGALRM, expired)
        signal.alarm(90)
        result = inspect(sys.argv[1])
        signal.alarm(0)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except Exception as exc:
        print(json.dumps({"schema": "merlin-studio-root-provider-inspection/1", "passed": False,
                          "error_type": type(exc).__name__, "error": str(exc)[:1000],
                          "model_generation_calls": 0, "service_mutations": False, "file_writes": 0}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

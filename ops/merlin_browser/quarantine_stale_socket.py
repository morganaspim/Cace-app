"""Single-use, source-pinned Merlin browser stale-socket quarantine candidate.

No CI workflow or installation invokes this module. The privileged CLI requires
a separate reviewed root operator action; GitHub hosted CI only executes
unprivileged isolated synthetic socket tests. A rename preserves the abandoned
socket inode for audit and potential rollback instead of unlinking it.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

SOCKET_NAME = "browser.sock"
QUARANTINE_NAME = "browser.sock.quarantine-2482964-20261122"
RUNTIME_DIRECTORY = Path("/run/merlin-public-browser")
SOCKET_PATH = str(RUNTIME_DIRECTORY / SOCKET_NAME)
LOCK_FILE = Path("/var/lib/merlin-browser-bootstrap/operation.lock")
STATE_DIRECTORY = LOCK_FILE.parent
SERVICE_UNIT = "merlin-public-browser.service"
EXPECTED_OLD_SOCKET = {
    "dev": 28, "inode": 2482964, "uid": 0, "gid": 1000,
    "mode": "0o660", "nlink": 1,
    "ctime_ns": 1795293187100973755,
    "mtime_ns": 1795293187100973755,
}
EXPECTED_PRIOR_INSPECTIONS = {
    45045149558: "0a5079914b4e0586dc8feabd0f5e76fadf0f7a5bda440f7cd59173f6b638934f",
    45050760629: "506e72c9fe7444004d69503df104585894c5838275c98ba7ab022b9b390bed7c",
}
PINNED_CONFIGS = {
    "/etc/merlin-public-browser/host.json":
        "728199723582985bc21357e72059fab26a0220e01a6d109f36288b39ecbd8600",
    "/etc/merlin-public-browser/service.json":
        "ddebe3b75f64187425feb5c0de017336b2b9685d4dafeed55f548c8ac4950d3f",
    "/etc/systemd/system/merlin-public-browser.service":
        "b4169da017658c97a039c945af9f8d22b7513eb5d0230f9db4c6902ba4a85487",
}
SERVICE_REQUIRED = {
    "LoadState": "loaded", "ActiveState": "inactive", "SubState": "dead",
    "UnitFileState": "disabled", "MainPID": "0", "ControlGroup": "",
    "User": "root", "Group": "root",
    "FragmentPath": "/etc/systemd/system/merlin-public-browser.service",
}
SAFE_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8", "HOME": "/var/empty", "SYSTEMD_PAGER": ""}


def _identity(st):
    return {
        "dev": st.st_dev, "inode": st.st_ino,
        "uid": st.st_uid, "gid": st.st_gid,
        "mode": oct(stat.S_IMODE(st.st_mode)), "nlink": st.st_nlink,
        "ctime_ns": st.st_ctime_ns, "mtime_ns": st.st_mtime_ns,
    }


def _service_safe(properties):
    return (isinstance(properties, dict)
            and all(type(properties.get(k)) is str and properties[k] == v
                    for k, v in SERVICE_REQUIRED.items()))


def classify_live_gate(observed, expected, service_state, listeners, *,
                       pair_accepted):
    """Pure, conservative gate. No observation ever creates root authority."""
    reasons = []
    if type(pair_accepted) is not bool or not pair_accepted:
        reasons.append("independent inspection evidence was not accepted")
    if type(listeners) is not int or listeners != 0:
        reasons.append("active listener or ambiguous Unix socket table")
    if not _service_safe(service_state):
        reasons.append("browser supervisor is active, changed or unobserved")
    if not isinstance(expected, dict) or set(expected) != set(EXPECTED_OLD_SOCKET):
        reasons.append("complete expected exact socket identity missing")
    if not isinstance(observed, os.stat_result):
        reasons.append("no trusted stat_result for socket inode")
    elif not stat.S_ISSOCK(observed.st_mode):
        reasons.append("original socket path is not a socket inode")
    elif isinstance(expected, dict):
        actual = _identity(observed)
        for key in EXPECTED_OLD_SOCKET:
            if type(expected.get(key)) is not type(EXPECTED_OLD_SOCKET[key]):
                reasons.append("socket identity field has wrong type: " + key)
            elif actual.get(key) != expected[key]:
                reasons.append("socket inode identity changed: " + key)
    return {
        "schema": "merlin-browser-stale-socket-live-gate/1",
        "status": "eligible_for_separate_quarantine_approval" if not reasons else "blocked",
        "reasons": sorted(set(reasons)),
        "authority_granted": False,
        "may_unlink_socket": False,
        "host_mutations": 0,
        "production_qualified": False,
    }


def _same_inode(a, b):
    return (stat.S_ISSOCK(a.st_mode) and stat.S_ISSOCK(b.st_mode)
            and (a.st_dev, a.st_ino, a.st_uid, a.st_gid, stat.S_IMODE(a.st_mode))
                == (b.st_dev, b.st_ino, b.st_uid, b.st_gid, stat.S_IMODE(b.st_mode)))


def quarantine_same_inode(dirfd, source, destination, expected, *, precheck,
                          postcheck):
    """Atomic same-directory rename with immediate rollback on postcheck drift.

    The supplied directory FD must be opened O_NOFOLLOW by the trusted caller.
    This operation alone cannot install a release, enable a unit or qualify
    the browser. The CLI below binds the paths, source, lock and root authority.
    """
    if (source != SOCKET_NAME or not isinstance(destination, str)
            or re.fullmatch(r"browser\.sock\.quarantine-[a-zA-Z0-9_-]{1,64}",
                            destination) is None
            or destination == source):
        raise ValueError("fixed socket and bounded quarantine target required")
    if not isinstance(dirfd, int) or type(dirfd) is not int or dirfd < 0:
        raise ValueError("trusted parent directory FD required")
    directory = os.fstat(dirfd)
    if not stat.S_ISDIR(directory.st_mode):
        raise ValueError("source parent is not a directory")
    before = os.stat(source, dir_fd=dirfd, follow_symlinks=False)
    if (not isinstance(expected, dict) or set(expected) != set(EXPECTED_OLD_SOCKET)
            or _identity(before) != expected or not stat.S_ISSOCK(before.st_mode)):
        raise ValueError("socket inode changed since final preflight")
    try:
        os.stat(destination, dir_fd=dirfd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise ValueError("quarantine destination already exists")
    gate = precheck()
    if not isinstance(gate, dict) or gate.get("status") != "eligible_for_separate_quarantine_approval":
        raise ValueError("read-only live gate rejected the socket quarantine")
    before_again = os.stat(source, dir_fd=dirfd, follow_symlinks=False)
    if (not _same_inode(before, before_again)
            or _identity(before_again) != expected):
        raise ValueError("socket inode changed between gate and rename")
    moved = False
    try:
        os.rename(source, destination, src_dir_fd=dirfd, dst_dir_fd=dirfd)
        moved = True
        quarantined = os.stat(destination, dir_fd=dirfd, follow_symlinks=False)
        if not _same_inode(before, quarantined):
            raise RuntimeError("postcheck moved socket inode differs")
        try:
            os.stat(source, dir_fd=dirfd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise RuntimeError("postcheck original socket path was repopulated")
        result = postcheck()
        if not _service_safe(result):
            raise RuntimeError("postcheck browser supervisor changed during quarantine")
    except BaseException:
        if moved:
            try:
                # Never overwrite an unexpectedly recreated source socket.
                os.stat(source, dir_fd=dirfd, follow_symlinks=False)
            except FileNotFoundError:
                dest = os.stat(destination, dir_fd=dirfd, follow_symlinks=False)
                if _same_inode(before, dest):
                    os.rename(destination, source, src_dir_fd=dirfd,
                              dst_dir_fd=dirfd)
        raise
    return {
        "schema": "merlin-browser-socket-quarantine/1", "status": "quarantined",
        "source": SOCKET_PATH,
        "quarantine_name": destination, "socket_inode": before.st_ino,
        "socket_dev": before.st_dev, "socket_identity_rechecked": True,
        "postcheck_supervisor_inactive": True,
        "production_qualified": False, "browser_service_started": False,
        "automatic_retry": False,
    }


def _trusted_regular(path, limit, owner=0):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != owner
                or before.st_mode & 0o022 or before.st_size > limit
                or before.st_nlink != 1):
            raise ValueError("trusted root-owned file metadata differs")
        data = bytearray()
        while len(data) <= limit:
            block = os.read(fd, min(65536, limit + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        after = os.fstat(fd)
        if (len(data) > limit or (before.st_dev, before.st_ino, before.st_size,
                                  before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("trusted root-owned file changed while read")
        return bytes(data)
    finally:
        os.close(fd)


def _systemd():
    args = ["/usr/bin/systemctl", "show", SERVICE_UNIT, "--no-pager"] + [
        "--property=" + key for key in SERVICE_REQUIRED]
    answer = subprocess.run(args, cwd="/", env=SAFE_ENV, timeout=8,
                            capture_output=True, check=True)
    if len(answer.stdout) > 16384:
        raise RuntimeError("unbounded fixed systemd result")
    properties = {}
    for line in answer.stdout.decode("ascii", "strict").splitlines():
        key, sep, value = line.partition("=")
        if not sep or key in properties:
            raise RuntimeError("invalid or duplicate systemd property")
        properties[key] = value
    if set(properties) != set(SERVICE_REQUIRED):
        raise RuntimeError("systemd properties absent or additional")
    return properties


def _listeners():
    raw = _trusted_regular("/proc/net/unix", 131072, owner=0)
    matches = 0
    for row in raw.decode("ascii", "replace").splitlines()[1:]:
        cols = row.split()
        if len(cols) >= 8 and cols[-1] == SOCKET_PATH:
            matches += 1
    return matches


def _host_precheck():
    # Retain the published previous config and release; no automatic upgrades.
    for path, expected_hash in PINNED_CONFIGS.items():
        if hashlib.sha256(_trusted_regular(path, 65536)).hexdigest() != expected_hash:
            raise ValueError("root browser configuration changed: " + path)
    socket_fd = os.open(RUNTIME_DIRECTORY, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parent = os.fstat(socket_fd)
        if (parent.st_uid, parent.st_gid, stat.S_IMODE(parent.st_mode)) != (0, 1000, 0o755):
            raise ValueError("browser socket parent metadata differs")
        st = os.stat(SOCKET_NAME, dir_fd=socket_fd, follow_symlinks=False)
        service = _systemd()
        listener_count = _listeners()
        gate = classify_live_gate(st, EXPECTED_OLD_SOCKET, service,
                                  listener_count, pair_accepted=True)
        if gate["status"] != "eligible_for_separate_quarantine_approval":
            raise ValueError("root-held browser host state not safe for candidate")
        return socket_fd, gate
    except BaseException:
        os.close(socket_fd)
        raise


def _write_unique_receipt(path, data):
    raw = (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
           + "\n").encode("utf-8")
    if len(raw) > 8192:
        raise ValueError("unexpectedly large fixed socket receipt")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)


def perform_root_quarantine():
    """Opt-in root operation; not called by repository workflows."""
    if os.geteuid() != 0 or sys.platform != "linux" or os.uname().machine != "aarch64":
        raise RuntimeError("reviewed root execution on exact OCI ARM64 required")
    root = STATE_DIRECTORY.lstat()
    if not stat.S_ISDIR(root.st_mode) or root.st_uid != 0 or root.st_mode & 0o022:
        raise RuntimeError("trusted root-owned operation directory required")
    lock = os.open(LOCK_FILE, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        ls = os.fstat(lock)
        if not stat.S_ISREG(ls.st_mode) or ls.st_uid != 0 or ls.st_mode & 0o077:
            raise RuntimeError("trusted exclusive root-owned operation lock required")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt_basename = "socket-quarantine-2482964-20261122"
        intent = STATE_DIRECTORY / (receipt_basename + ".intent.json")
        result_file = STATE_DIRECTORY / (receipt_basename + ".result.json")
        if intent.exists() or intent.is_symlink() or result_file.exists() or result_file.is_symlink():
            raise RuntimeError("existing operation intent/result requires explicit reconciliation")
        parent_fd, gate = _host_precheck()
        try:
            _write_unique_receipt(intent, {
                "schema":"merlin-browser-socket-quarantine-intent/1",
                "source_run_ids":sorted(EXPECTED_PRIOR_INSPECTIONS),
                "observed_socket_inode": EXPECTED_OLD_SOCKET["inode"],
                "status":"accepted_root_preflight", "automatic_retry":False,
            })
            record = quarantine_same_inode(
                parent_fd, SOCKET_NAME, QUARANTINE_NAME, EXPECTED_OLD_SOCKET,
                precheck=lambda: classify_live_gate(
                    os.stat(SOCKET_NAME, dir_fd=parent_fd, follow_symlinks=False),
                    EXPECTED_OLD_SOCKET, _systemd(), _listeners(),
                    pair_accepted=True),
                postcheck=lambda: _systemd() if _listeners() == 0 else {})
            _write_unique_receipt(result_file, record)
        finally:
            os.close(parent_fd)
        return record
    finally:
        os.close(lock)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Reviewed, one-time root-only stale socket quarantine; no installation")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quarantine-verified-stale-socket", action="store_true")
    parser.add_argument("--confirm-second-receipt-sha256", default="")
    args = parser.parse_args(argv)
    if args.dry_run == args.quarantine_verified_stale_socket:
        parser.error("specify exactly one mode")
    if args.quarantine_verified_stale_socket:
        if args.confirm_second_receipt_sha256 != EXPECTED_PRIOR_INSPECTIONS[45050760629]:
            parser.error("fixed previous independent source digest must be acknowledged")
        result = perform_root_quarantine()
        print(json.dumps(result, sort_keys=True))
        return 0
    print(json.dumps({
        "status":"review_only_dry_run", "host_mutations":0,
        "operation":"stale_socket_exact_inode_rollback_candidate",
        "authority_granted":False, "production_qualified":False,
        "requires_explicit_privileged_authorization":True,
    },sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

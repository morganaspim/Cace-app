from __future__ import annotations

from dataclasses import dataclass
import ctypes
import ctypes.util
import errno
import os
from pathlib import Path
import platform
import socket
import sys
from typing import Any, Iterable, Mapping
from uuid import uuid4


_STATUS_ACTIVE = "active"
_STATUS_UNAVAILABLE = "unavailable"
_STATUS_FAILED = "failed"
_STATUS_NOT_APPLICABLE = "not-applicable"


@dataclass(frozen=True)
class SandboxRequirements:
    require_network_namespace: bool = False
    require_seccomp_filter: bool = False
    require_filesystem_restriction: bool = False
    require_privilege_hardening: bool = False
    require_cgroup_v2: bool = False
    require_mount_namespace: bool = False
    require_private_tmp: bool = False
    require_device_restrictions: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "require_network_namespace": self.require_network_namespace,
            "require_seccomp_filter": self.require_seccomp_filter,
            "require_filesystem_restriction": self.require_filesystem_restriction,
            "require_privilege_hardening": self.require_privilege_hardening,
            "require_cgroup_v2": self.require_cgroup_v2,
            "require_mount_namespace": self.require_mount_namespace,
            "require_private_tmp": self.require_private_tmp,
            "require_device_restrictions": self.require_device_restrictions,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SandboxRequirements":
        return cls(
            require_network_namespace=bool(
                payload.get("require_network_namespace", False)
            ),
            require_seccomp_filter=bool(
                payload.get("require_seccomp_filter", False)
            ),
            require_filesystem_restriction=bool(
                payload.get("require_filesystem_restriction", False)
            ),
            require_privilege_hardening=bool(
                payload.get("require_privilege_hardening", False)
            ),
            require_cgroup_v2=bool(
                payload.get("require_cgroup_v2", False)
            ),
            require_mount_namespace=bool(
                payload.get("require_mount_namespace", False)
            ),
            require_private_tmp=bool(
                payload.get("require_private_tmp", False)
            ),
            require_device_restrictions=bool(
                payload.get("require_device_restrictions", False)
            ),
        )


@dataclass(frozen=True)
class SandboxCapabilityReport:
    platform: str
    kernel_release: str
    architecture: str
    host_uid_before: int
    host_gid_before: int
    controls: Mapping[str, Mapping[str, Any]]
    requirements: SandboxRequirements
    all_required_active: bool
    proof_effect: str = "none"
    promotion_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "sandbox_capability_schema": 1,
            "platform": self.platform,
            "kernel_release": self.kernel_release,
            "architecture": self.architecture,
            "host_uid_before": self.host_uid_before,
            "host_gid_before": self.host_gid_before,
            "controls": {
                str(key): dict(value) for key, value in self.controls.items()
            },
            "requirements": self.requirements.to_dict(),
            "all_required_active": self.all_required_active,
            "proof_effect": "none",
            "promotion_authority": False,
        }


class SandboxRequirementError(RuntimeError):
    def __init__(self, message: str, *, report: SandboxCapabilityReport) -> None:
        super().__init__(message)
        self.report = report


def _control(
    status: str,
    *,
    active: bool,
    detail: str = "",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "status": status,
        "active": bool(active),
        "detail": detail,
        **extra,
    }


def _libc() -> ctypes.CDLL:
    return ctypes.CDLL(None, use_errno=True)


def _set_no_new_privs() -> dict[str, Any]:
    if sys.platform != "linux":
        return _control(
            _STATUS_NOT_APPLICABLE,
            active=False,
            detail="PR_SET_NO_NEW_PRIVS is Linux-specific",
        )
    libc = _libc()
    PR_SET_NO_NEW_PRIVS = 38
    PR_GET_NO_NEW_PRIVS = 39
    rc = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    if rc != 0:
        err = ctypes.get_errno()
        return _control(
            _STATUS_FAILED,
            active=False,
            detail=os.strerror(err),
            errno=err,
        )
    value = libc.prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0)
    active = value == 1
    return _control(
        _STATUS_ACTIVE if active else _STATUS_FAILED,
        active=active,
        detail="PR_GET_NO_NEW_PRIVS confirmed" if active else "confirmation failed",
        value=value,
    )


def _disable_dumpability() -> dict[str, Any]:
    if sys.platform != "linux":
        return _control(
            _STATUS_NOT_APPLICABLE,
            active=False,
            detail="PR_SET_DUMPABLE is Linux-specific",
        )
    libc = _libc()
    PR_SET_DUMPABLE = 4
    PR_GET_DUMPABLE = 3
    rc = libc.prctl(PR_SET_DUMPABLE, 0, 0, 0, 0)
    if rc != 0:
        err = ctypes.get_errno()
        return _control(
            _STATUS_FAILED,
            active=False,
            detail=os.strerror(err),
            errno=err,
        )
    value = libc.prctl(PR_GET_DUMPABLE, 0, 0, 0, 0)
    active = value == 0
    return _control(
        _STATUS_ACTIVE if active else _STATUS_FAILED,
        active=active,
        detail="process marked non-dumpable" if active else "confirmation failed",
        value=value,
    )


def _namespace_inode(kind: str) -> int | None:
    try:
        return os.stat(f"/proc/self/ns/{kind}").st_ino
    except OSError:
        return None


def _attempt_network_user_namespace(
    *,
    parent_netns_inode: int | None,
    host_uid: int,
    host_gid: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if sys.platform != "linux":
        unavailable = _control(
            _STATUS_NOT_APPLICABLE,
            active=False,
            detail="Linux namespaces unavailable on this platform",
        )
        return unavailable, unavailable

    libc = _libc()
    CLONE_NEWUSER = 0x10000000
    CLONE_NEWNET = 0x40000000
    before = _namespace_inode("net")
    rc = libc.unshare(CLONE_NEWUSER | CLONE_NEWNET)
    if rc != 0:
        err = ctypes.get_errno()
        status = _STATUS_UNAVAILABLE if err in {errno.EPERM, errno.EINVAL, errno.ENOSYS} else _STATUS_FAILED
        detail = os.strerror(err)
        return (
            _control(status, active=False, detail=detail, errno=err),
            _control(status, active=False, detail=detail, errno=err),
        )

    try:
        setgroups = Path("/proc/self/setgroups")
        if setgroups.exists():
            setgroups.write_text("deny", encoding="ascii")
        Path("/proc/self/uid_map").write_text(
            f"{host_uid} {host_uid} 1\n",
            encoding="ascii",
        )
        Path("/proc/self/gid_map").write_text(
            f"{host_gid} {host_gid} 1\n",
            encoding="ascii",
        )
        os.setresgid(host_gid, host_gid, host_gid)
        os.setresuid(host_uid, host_uid, host_uid)
    except Exception as exc:
        detail = (
            "user/network namespace created but uid/gid mapping failed: "
            f"{type(exc).__name__}: {exc}"
        )
        failed = _control(
            _STATUS_FAILED,
            active=False,
            detail=detail,
            irreversible_partial_transition=True,
        )
        return failed, failed

    after = _namespace_inode("net")
    parent = parent_netns_inode if parent_netns_inode is not None else before
    isolated = after is not None and parent is not None and after != parent
    user = _control(
        _STATUS_ACTIVE,
        active=True,
        detail="user namespace active while preserving the original non-root numeric identity",
        namespace_uid=os.geteuid(),
        namespace_gid=os.getegid(),
        host_uid_mapped=host_uid,
        host_gid_mapped=host_gid,
    )
    net = _control(
        _STATUS_ACTIVE if isolated else _STATUS_FAILED,
        active=isolated,
        detail=(
            "network namespace inode differs from parent"
            if isolated
            else "network namespace inode did not change"
        ),
        parent_inode=parent,
        child_inode=after,
    )
    return user, net


def _mount(
    source: str | None,
    target: str | Path,
    fstype: str | None,
    flags: int,
    data: str | None = None,
) -> None:
    libc = _libc()
    libc.mount.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_ulong,
        ctypes.c_char_p,
    ]
    libc.mount.restype = ctypes.c_int
    rc = libc.mount(
        source.encode() if source is not None else None,
        os.fsencode(str(target)),
        fstype.encode() if fstype is not None else None,
        ctypes.c_ulong(flags),
        data.encode() if data is not None else None,
    )
    if rc != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), str(target))


def _attempt_mount_namespace(
    *,
    parent_mntns_inode: int | None,
    job_dir: Path,
    gpu_enabled: bool,
    tmpfs_bytes: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if sys.platform != "linux":
        unavailable = _control(
            _STATUS_NOT_APPLICABLE,
            active=False,
            detail="Linux mount namespaces unavailable on this platform",
        )
        return unavailable, unavailable, unavailable

    libc = _libc()
    CLONE_NEWNS = 0x00020000
    MS_BIND = 4096
    MS_REC = 16384
    MS_PRIVATE = 1 << 18
    MS_NOSUID = 2
    MS_NODEV = 4
    MS_NOEXEC = 8

    before = _namespace_inode("mnt")
    rc = libc.unshare(CLONE_NEWNS)
    if rc != 0:
        err = ctypes.get_errno()
        status = (
            _STATUS_UNAVAILABLE
            if err in {errno.EPERM, errno.EINVAL, errno.ENOSYS}
            else _STATUS_FAILED
        )
        unavailable = _control(
            status,
            active=False,
            detail=os.strerror(err),
            errno=err,
        )
        return unavailable, unavailable, unavailable

    after = _namespace_inode("mnt")
    parent = parent_mntns_inode if parent_mntns_inode is not None else before
    isolated = after is not None and parent is not None and after != parent
    mount_ns = _control(
        _STATUS_ACTIVE if isolated else _STATUS_FAILED,
        active=isolated,
        detail=(
            "mount namespace inode differs from parent"
            if isolated
            else "mount namespace inode did not change"
        ),
        parent_inode=parent,
        child_inode=after,
    )
    if not isolated:
        unavailable = _control(
            _STATUS_FAILED,
            active=False,
            detail="mount namespace verification failed",
        )
        return mount_ns, unavailable, unavailable

    try:
        _mount(None, "/", None, MS_REC | MS_PRIVATE)
    except OSError as exc:
        failed = _control(
            _STATUS_FAILED,
            active=False,
            detail=f"failed to make mount propagation private: {exc}",
        )
        return mount_ns, failed, failed

    tmp_dir = Path("/tmp")
    private_tmp: dict[str, Any]
    try:
        before_dev = os.stat(tmp_dir).st_dev
        _mount(
            "tmpfs",
            tmp_dir,
            "tmpfs",
            MS_NOSUID | MS_NODEV | MS_NOEXEC,
            f"size={max(1_048_576, int(tmpfs_bytes))},mode=700",
        )
        after_dev = os.stat(tmp_dir).st_dev
        active = before_dev != after_dev
        private_tmp = _control(
            _STATUS_ACTIVE if active else _STATUS_FAILED,
            active=active,
            detail=(
                "private tmpfs mounted inside worker mount namespace"
                if active
                else "tmpfs mount did not change backing device"
            ),
            path=str(tmp_dir),
            size_bytes=max(1_048_576, int(tmpfs_bytes)),
            nosuid=True,
            nodev=True,
            noexec=True,
        )
    except OSError as exc:
        private_tmp = _control(
            _STATUS_FAILED,
            active=False,
            detail=f"{type(exc).__name__}: {exc}",
            path=str(tmp_dir),
        )

    if gpu_enabled:
        devices = _control(
            _STATUS_UNAVAILABLE,
            active=False,
            detail=(
                "minimal private /dev is not enabled for GPU runs; "
                "GPU device allowlisting requires an explicit future profile"
            ),
            gpu_enabled=True,
        )
        return mount_ns, private_tmp, devices

    dev_view = job_dir / "dev-view"
    try:
        dev_view.mkdir(parents=True, exist_ok=True)
        allowed = ("null", "zero", "random", "urandom")
        for name in allowed:
            target = dev_view / name
            target.touch(exist_ok=True)
            _mount(f"/dev/{name}", target, None, MS_BIND)
        for link, destination in (
            ("fd", "/proc/self/fd"),
            ("stdin", "/proc/self/fd/0"),
            ("stdout", "/proc/self/fd/1"),
            ("stderr", "/proc/self/fd/2"),
        ):
            path = dev_view / link
            if not path.exists() and not path.is_symlink():
                path.symlink_to(destination)
        shm = dev_view / "shm"
        shm.mkdir(exist_ok=True)
        _mount(
            "tmpfs",
            shm,
            "tmpfs",
            MS_NOSUID | MS_NODEV | MS_NOEXEC,
            "size=67108864,mode=1777",
        )
        _mount(str(dev_view), "/dev", None, MS_BIND | MS_REC)
        with open("/dev/null", "wb", buffering=0) as handle:
            handle.write(b"")
        forbidden_absent = all(
            not Path(path).exists()
            for path in (
                "/dev/kmsg",
                "/dev/mem",
                "/dev/port",
                "/dev/dri",
                "/dev/nvidia0",
                "/dev/nvidiactl",
            )
        )
        devices = _control(
            _STATUS_ACTIVE if forbidden_absent else _STATUS_FAILED,
            active=forbidden_absent,
            detail=(
                "private minimal /dev active"
                if forbidden_absent
                else "unexpected host device remained visible"
            ),
            allowed_devices=list(allowed),
            private_shm=True,
            blocked_probe_paths=[
                "/dev/kmsg",
                "/dev/mem",
                "/dev/port",
                "/dev/dri",
                "/dev/nvidia0",
                "/dev/nvidiactl",
            ],
            blocked_probe_success=forbidden_absent,
        )
    except OSError as exc:
        devices = _control(
            _STATUS_FAILED,
            active=False,
            detail=f"{type(exc).__name__}: {exc}",
        )

    return mount_ns, private_tmp, devices


def _landlock_syscall_numbers() -> tuple[int, int, int]:
    # Landlock uses the generic syscall numbers on current Linux architectures,
    # including x86_64 and aarch64.
    return (444, 445, 446)


class _LandlockRulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _LandlockPathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int),
        ("reserved", ctypes.c_uint32),
    ]


def _landlock_access_bits(abi: int) -> tuple[int, int]:
    EXECUTE = 1 << 0
    WRITE_FILE = 1 << 1
    READ_FILE = 1 << 2
    READ_DIR = 1 << 3
    REMOVE_DIR = 1 << 4
    REMOVE_FILE = 1 << 5
    MAKE_CHAR = 1 << 6
    MAKE_DIR = 1 << 7
    MAKE_REG = 1 << 8
    MAKE_SOCK = 1 << 9
    MAKE_FIFO = 1 << 10
    MAKE_BLOCK = 1 << 11
    MAKE_SYM = 1 << 12
    REFER = 1 << 13
    TRUNCATE = 1 << 14

    read_bits = EXECUTE | READ_FILE | READ_DIR
    write_bits = (
        WRITE_FILE
        | REMOVE_DIR
        | REMOVE_FILE
        | MAKE_CHAR
        | MAKE_DIR
        | MAKE_REG
        | MAKE_SOCK
        | MAKE_FIFO
        | MAKE_BLOCK
        | MAKE_SYM
    )
    if abi >= 2:
        write_bits |= REFER
    if abi >= 3:
        write_bits |= TRUNCATE
    return read_bits, write_bits


def _existing_unique_dirs(paths: Iterable[str | Path]) -> tuple[Path, ...]:
    result: list[Path] = []
    seen: set[str] = set()
    for raw in paths:
        try:
            path = Path(raw).expanduser().resolve()
        except Exception:
            continue
        if not path.exists():
            continue
        if path.is_file():
            path = path.parent
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return tuple(result)


def _apply_landlock(
    *,
    read_only_paths: Iterable[str | Path],
    read_write_paths: Iterable[str | Path],
    probe_outside_path: Path,
) -> dict[str, Any]:
    if sys.platform != "linux":
        return _control(
            _STATUS_NOT_APPLICABLE,
            active=False,
            detail="Landlock is Linux-specific",
        )
    libc = _libc()
    create_nr, add_nr, restrict_nr = _landlock_syscall_numbers()
    LANDLOCK_CREATE_RULESET_VERSION = 1
    abi = libc.syscall(
        create_nr,
        ctypes.c_void_p(0),
        ctypes.c_size_t(0),
        ctypes.c_uint(LANDLOCK_CREATE_RULESET_VERSION),
    )
    if abi < 0:
        err = ctypes.get_errno()
        status = _STATUS_UNAVAILABLE if err in {errno.ENOSYS, errno.EOPNOTSUPP, errno.EINVAL} else _STATUS_FAILED
        return _control(
            status,
            active=False,
            detail=os.strerror(err),
            errno=err,
        )

    read_bits, write_bits = _landlock_access_bits(int(abi))
    handled = read_bits | write_bits
    attr = _LandlockRulesetAttr(handled_access_fs=handled)
    ruleset_fd = libc.syscall(
        create_nr,
        ctypes.byref(attr),
        ctypes.sizeof(attr),
        ctypes.c_uint(0),
    )
    if ruleset_fd < 0:
        err = ctypes.get_errno()
        return _control(
            _STATUS_FAILED,
            active=False,
            detail=f"create ruleset failed: {os.strerror(err)}",
            errno=err,
            abi=int(abi),
        )

    O_PATH = getattr(os, "O_PATH", 0o10000000)
    rule_type_path_beneath = 1
    ro = _existing_unique_dirs(read_only_paths)
    rw = _existing_unique_dirs(read_write_paths)
    added: list[dict[str, Any]] = []
    try:
        for path, allowed in [
            *((item, read_bits) for item in ro),
            *((item, handled) for item in rw),
        ]:
            fd = os.open(path, O_PATH | os.O_CLOEXEC)
            try:
                rule = _LandlockPathBeneathAttr(
                    allowed_access=allowed,
                    parent_fd=fd,
                    reserved=0,
                )
                rc = libc.syscall(
                    add_nr,
                    ruleset_fd,
                    rule_type_path_beneath,
                    ctypes.byref(rule),
                    ctypes.c_uint(0),
                )
                if rc != 0:
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err), str(path))
                added.append(
                    {
                        "path": str(path),
                        "mode": "rw" if allowed == handled else "ro",
                    }
                )
            finally:
                os.close(fd)

        rc = libc.syscall(restrict_nr, ruleset_fd, ctypes.c_uint(0))
        if rc != 0:
            err = ctypes.get_errno()
            return _control(
                _STATUS_FAILED,
                active=False,
                detail=f"restrict_self failed: {os.strerror(err)}",
                errno=err,
                abi=int(abi),
                rules=added,
            )
    finally:
        os.close(ruleset_fd)

    probe_blocked = False
    probe_error = ""
    try:
        probe_outside_path.write_text("probe", encoding="utf-8")
        try:
            probe_outside_path.unlink()
        except OSError:
            pass
    except OSError as exc:
        probe_blocked = exc.errno in {errno.EACCES, errno.EPERM}
        probe_error = f"{type(exc).__name__}: {exc}"

    active = probe_blocked
    return _control(
        _STATUS_ACTIVE if active else _STATUS_FAILED,
        active=active,
        detail=(
            "Landlock active; outside write probe denied"
            if active
            else "Landlock probe did not confirm outside-write denial"
        ),
        abi=int(abi),
        rules=added,
        outside_write_probe_blocked=probe_blocked,
        outside_write_probe_error=probe_error,
    )


def _apply_seccomp() -> dict[str, Any]:
    if sys.platform != "linux":
        return _control(
            _STATUS_NOT_APPLICABLE,
            active=False,
            detail="seccomp is Linux-specific",
        )
    libname = ctypes.util.find_library("seccomp")
    if not libname:
        return _control(
            _STATUS_UNAVAILABLE,
            active=False,
            detail="libseccomp not found",
        )
    try:
        lib = ctypes.CDLL(libname, use_errno=True)
    except OSError as exc:
        return _control(
            _STATUS_UNAVAILABLE,
            active=False,
            detail=str(exc),
            library=libname,
        )

    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    lib.seccomp_rule_add.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    lib.seccomp_rule_add.restype = ctypes.c_int
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_load.restype = ctypes.c_int
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int

    SCMP_ACT_ALLOW = 0x7FFF0000
    SCMP_ACT_ERRNO = 0x00050000 | errno.EPERM
    ctx = lib.seccomp_init(SCMP_ACT_ALLOW)
    if not ctx:
        return _control(
            _STATUS_FAILED,
            active=False,
            detail="seccomp_init failed",
            library=libname,
        )

    deny_names = (
        "socket",
        "socketpair",
        "connect",
        "bind",
        "listen",
        "accept",
        "accept4",
        "sendto",
        "sendmsg",
        "sendmmsg",
        "recvfrom",
        "recvmsg",
        "recvmmsg",
        "shutdown",
        "setsockopt",
        "getsockopt",
        "execve",
        "execveat",
        "ptrace",
        "bpf",
        "perf_event_open",
        "keyctl",
        "add_key",
        "request_key",
        "mount",
        "umount2",
        "pivot_root",
        "setns",
        "unshare",
    )
    installed: list[str] = []
    try:
        for name in deny_names:
            nr = lib.seccomp_syscall_resolve_name(name.encode("ascii"))
            if nr < 0:
                continue
            rc = lib.seccomp_rule_add(ctx, SCMP_ACT_ERRNO, nr, 0)
            if rc != 0:
                return _control(
                    _STATUS_FAILED,
                    active=False,
                    detail=f"seccomp_rule_add failed for {name}: {rc}",
                    library=libname,
                    installed=installed,
                )
            installed.append(name)
        rc = lib.seccomp_load(ctx)
        if rc != 0:
            return _control(
                _STATUS_FAILED,
                active=False,
                detail=f"seccomp_load failed: {rc}",
                library=libname,
                installed=installed,
            )
    finally:
        lib.seccomp_release(ctx)

    socket_blocked = False
    socket_probe_error = ""
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.close()
    except OSError as exc:
        socket_blocked = exc.errno in {errno.EPERM, errno.EACCES}
        socket_probe_error = f"{type(exc).__name__}: {exc}"

    active = socket_blocked
    return _control(
        _STATUS_ACTIVE if active else _STATUS_FAILED,
        active=active,
        detail=(
            "seccomp active; socket syscall probe denied"
            if active
            else "seccomp loaded but socket probe was not denied"
        ),
        library=libname,
        denied_syscalls=installed,
        socket_probe_blocked=socket_blocked,
        socket_probe_error=socket_probe_error,
    )


def _requirements_satisfied(
    requirements: SandboxRequirements,
    controls: Mapping[str, Mapping[str, Any]],
) -> tuple[bool, tuple[str, ...]]:
    required_map = {
        "network_namespace": requirements.require_network_namespace,
        "seccomp": requirements.require_seccomp_filter,
        "landlock": requirements.require_filesystem_restriction,
        "privilege_hardening": requirements.require_privilege_hardening,
        "cgroup_v2": requirements.require_cgroup_v2,
        "mount_namespace": requirements.require_mount_namespace,
        "private_tmp": requirements.require_private_tmp,
        "device_restrictions": requirements.require_device_restrictions,
    }
    missing = tuple(
        name
        for name, required in required_map.items()
        if required and not bool(controls.get(name, {}).get("active", False))
    )
    return not missing, missing


def apply_linux_worker_sandbox(
    *,
    parent_netns_inode: int | None,
    parent_mntns_inode: int | None,
    read_only_paths: Iterable[str | Path],
    read_write_paths: Iterable[str | Path],
    requirements: SandboxRequirements,
    job_dir: str | Path,
    gpu_enabled: bool = False,
    tmpfs_bytes: int = 268_435_456,
    external_controls: Mapping[str, Mapping[str, Any]] | None = None,
) -> SandboxCapabilityReport:
    host_uid = os.geteuid() if hasattr(os, "geteuid") else -1
    host_gid = os.getegid() if hasattr(os, "getegid") else -1
    controls: dict[str, dict[str, Any]] = {
        str(key): dict(value)
        for key, value in dict(external_controls or {}).items()
    }

    os.umask(0o077)
    userns, netns = _attempt_network_user_namespace(
        parent_netns_inode=parent_netns_inode,
        host_uid=host_uid,
        host_gid=host_gid,
    )
    controls["user_namespace"] = userns
    controls["network_namespace"] = netns

    mount_ns, private_tmp, devices = _attempt_mount_namespace(
        parent_mntns_inode=parent_mntns_inode,
        job_dir=Path(job_dir).resolve(),
        gpu_enabled=gpu_enabled,
        tmpfs_bytes=tmpfs_bytes,
    )
    controls["mount_namespace"] = mount_ns
    controls["private_tmp"] = private_tmp
    controls["device_restrictions"] = devices

    no_new_privs = _set_no_new_privs()
    controls["no_new_privs"] = no_new_privs
    controls["dumpability"] = _disable_dumpability()

    host_unprivileged = host_uid not in {-1, 0}
    userns_isolated = bool(userns.get("active", False)) and host_unprivileged
    privilege_active = bool(no_new_privs.get("active", False)) and (
        host_unprivileged or userns_isolated
    )
    controls["privilege_hardening"] = _control(
        _STATUS_ACTIVE if privilege_active else _STATUS_FAILED,
        active=privilege_active,
        detail=(
            "host identity is unprivileged and no_new_privs is active"
            if privilege_active
            else "host process is privileged or no_new_privs was not confirmed"
        ),
        host_uid=host_uid,
        host_gid=host_gid,
        namespace_user_active=bool(userns.get("active", False)),
    )

    probe_path = Path("/var/tmp") / f".cace-landlock-probe-{uuid4().hex}"
    try:
        controls["landlock"] = _apply_landlock(
            read_only_paths=read_only_paths,
            read_write_paths=read_write_paths,
            probe_outside_path=probe_path,
        )
    except Exception as exc:
        controls["landlock"] = _control(
            _STATUS_FAILED,
            active=False,
            detail=f"{type(exc).__name__}: {exc}",
        )
    try:
        controls["seccomp"] = _apply_seccomp()
    except Exception as exc:
        controls["seccomp"] = _control(
            _STATUS_FAILED,
            active=False,
            detail=f"{type(exc).__name__}: {exc}",
        )

    irreversible_partial = any(
        bool(control.get("irreversible_partial_transition", False))
        for control in controls.values()
    )
    satisfied, missing = _requirements_satisfied(requirements, controls)
    if irreversible_partial:
        satisfied = False
        missing = tuple(
            sorted(set(missing) | {"irreversible_namespace_transition"})
        )
    report = SandboxCapabilityReport(
        platform=sys.platform,
        kernel_release=platform.release(),
        architecture=platform.machine(),
        host_uid_before=host_uid,
        host_gid_before=host_gid,
        controls=controls,
        requirements=requirements,
        all_required_active=satisfied,
    )
    if not satisfied:
        reason = (
            "worker sandbox entered an irreversible partial namespace state"
            if irreversible_partial
            else "required worker sandbox controls are inactive"
        )
        raise SandboxRequirementError(
            f"{reason}: {list(missing)}",
            report=report,
        )
    return report

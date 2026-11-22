#!/usr/bin/env python3
"""Private loopback and zero-cap setup for exactly two fixed local model turns.

Rootless --user --map-current-user --net --keep-caps, then setpriv drops
all capabilities before any model binary can run. Existing root service is
neither changed nor queried. This derivative is not a production runtime.
"""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def isolated_interfaces():
    """Enumerate links in the CURRENT network namespace, not host-mounted sysfs.

    A rootless user+net namespace may keep a sysfs mount from the parent
    mount namespace. /sys/class/net can therefore show HOST interfaces even
    while socket/netlink calls correctly report only the child's loopback.
    """
    entries = socket.if_nameindex()
    require(isinstance(entries, list) and len(entries) > 0,
            "network interface enumeration unavailable")
    indexes = [index for index, name in entries]
    names = [name for index, name in entries]
    require(all(type(index) is int and index > 0 for index in indexes)
            and all(isinstance(name, str) and name for name in names)
            and len(indexes) == len(set(indexes))
            and len(names) == len(set(names)),
            "network link identities are ambiguous")
    return sorted(names)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    require(len(argv) == 6, "require parent netns + 5 exact source/result paths")
    parent_inum = int(argv[0])
    runner, python, product, temp_root, evidence = map(Path, argv[1:])
    evidence.mkdir(mode=0o700, exist_ok=True)
    result = {"schema": "merlin-oci-private-model-loopback-setup/1",
              "uid": os.geteuid(), "host_network_changed": False,
              "model_generation_calls": 0, "maximum_generation_calls": 2,
              "existing_root_service_mutated": False,
              "system_installation": False,
              "production_qualified": False, "status": "blocked"}
    try:
        require(os.geteuid() == 1000, "host user UID must be 1000")
        mapping = Path("/proc/self/uid_map").read_text().split()
        require(mapping == ["1000", "1000", "1"], "UID mapping must be current-user")
        child_inum = os.stat("/proc/self/ns/net").st_ino
        require(child_inum != parent_inum, "new network namespace required")
        # socket.if_nameindex is a namespace-aware kernel link query.
        # Never use /sys/class/net here: sysfs can be inherited from the host.
        interfaces = isolated_interfaces()
        result["namespace_interfaces"] = interfaces
        result["interface_source"] = "socket.if_nameindex/current_netns"
        require(interfaces == ["lo"], "new namespace has unexpected network interface")
        # Scoped CAP_NET_ADMIN exists only during this setup and only for the
        # private network namespace. No external network interfaces are added.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            req = struct.pack("16sH14s", b"lo", 0, b"")
            name, flags, pad = struct.unpack(
                "16sH14s", fcntl.ioctl(sock.fileno(), 0x8913, req))
            require(name.rstrip(b"\0") == b"lo", "loopback identity differs")
            if not (flags & 1):
                fcntl.ioctl(sock.fileno(), 0x8914,
                            struct.pack("16sH14s", b"lo", flags | 1, pad))
            _, now, _ = struct.unpack("16sH14s",
                                      fcntl.ioctl(sock.fileno(), 0x8913, req))
            require(now & 1, "rootless loopback did not become UP")
        result["private_loopback_prepared"] = True
        result["separate_network_namespace"] = True
        result["namespace_inode"] = child_inum
        result["parent_namespace_inode"] = parent_inum
        result["uid_mapping"] = mapping
        result["interfaces"] = interfaces
        # Drop every effective, inheritable and bounding capability, and set
        # no_new_privs BEFORE executing any product script or browser.
        command = ["/usr/bin/setpriv", "--no-new-privs",
                   "--bounding-set=-all", "--inh-caps=-all",
                   "/usr/bin/python3", "-I", "-B", str(runner),
                   str(python), str(product), str(temp_root), str(evidence)]
        env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
               "LC_ALL": "C.UTF-8", "HOME": "/var/empty",
               "PYTHONDONTWRITEBYTECODE": "1",
               "MERLIN_PARENT_NETNS_INODE": str(parent_inum)}
        process = subprocess.Popen(
            command, env=env, cwd="/", stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        expired = False
        try:
            stdout, stderr = process.communicate(timeout=260)
        except subprocess.TimeoutExpired:
            expired = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate(timeout=5)
        (evidence / "isolated-runner.stdout").write_bytes(stdout[:128 * 1024])
        (evidence / "isolated-runner.stderr").write_bytes(stderr[:128 * 1024])
        require(not expired, "isolated child deadline expired")
        require(len(stdout) <= 128 * 1024 and len(stderr) <= 128 * 1024,
                "isolated child output ceiling exceeded")
        require(process.returncode == 0,
                "rootless zero-cap model test returned nonzero")
        episode = json.loads((evidence / "model-episode-result.json").read_text())
        require(episode.get("status")=="two_live_local_model_turns_verified_in_private_netns"
                and episode.get("generation_calls")==2
                and episode.get("two_reference_checks_passed") is True
                and episode.get("owned_process_stopped") is True
                and episode.get("private_endpoint_removed_with_process") is True
                and episode.get("host_service_mutations") is False
                and episode.get("production_qualified") is False,
                "bounded inference episode receipt did not pass")
        result["status"] = "private_loopback_two_local_model_turns_passed"
        result["model_generation_calls"] = 2
        result["runner_exit_code"] = 0
        result["zero_capability_verified_by_child"] = True
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)[:240]
        return 2
    finally:
        (evidence / "isolated-setup-result.json").write_text(
            json.dumps(result, sort_keys=True, indent=2))
        print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    raise SystemExit(main())

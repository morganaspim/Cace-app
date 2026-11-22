#!/usr/bin/env python3
"""Bounded integrity/startup preflight for root-owned, nonroot-readable local model.

Never invokes the existing model service or reads host process credentials.
This is only integrity and version evidence: it never generates a token,
installs packages, changes file modes, or qualifies production.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import signal
import stat
import subprocess
import sys
import time

MANIFEST = Path("/etc/merlin-model-provider/manifest.json")
MANIFEST_SHA = "35cf7ea56185126587e7dc10bb400ec53df51057407f9920d0ab03aff4299203"
MODEL_SHA = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
MODEL_BYTES = 1117320768
MODEL_ALIAS = "merlin-qwen-coder-1.5b-q4"
SOURCE_COMMIT = "2a4daf0e08d6a9b6993ee0d4a9a3cfc35a6f405c"
REVISION = "f86cb2c1fa58255f8052cc32aeede1b7482d4361"
RELEASES = Path("/opt/merlin-model-provider/releases")
MIN_MEMORY_HEADROOM = 2 * 1024**3
BINARY_LIMIT = 256 * 1024**2


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def unique(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, "duplicate JSON key")
        out[key] = value
    return out


def regular(path, expected_size, expected_uid=0):
    """Open a trusted regular file with no-follow and stable inode/size."""
    path = Path(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_uid == expected_uid
            and not (stat.S_IMODE(before.st_mode) & 0o022),
            "file ownership, type, or write boundary differs")
    require(0 < before.st_size <= expected_size, "file exceeds allowed byte count")
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0))
    try:
        after = os.fstat(fd)
        require(stat.S_ISREG(after.st_mode)
                and after.st_ino == before.st_ino and after.st_dev == before.st_dev
                and after.st_size == before.st_size and after.st_uid == expected_uid,
                "trusted file replaced during open")
        return fd, before
    except BaseException:
        os.close(fd)
        raise


def full_digest(path, expected_size, expected_hash, seconds=100, owner=0):
    """Stream bounded files with inode recheck; hash never trusted from manifest alone."""
    require(type(expected_size) is int and expected_size > 0
            and re.fullmatch(r"[0-9a-f]{64}", expected_hash),
            "invalid fixed digest assertion")
    fd, info = regular(path, expected_size, expected_uid=owner)
    require(info.st_size == expected_size, "exact model/binary length differs")
    start = time.monotonic()
    amount = 0
    digest = hashlib.sha256()
    try:
        while amount < expected_size:
            require(time.monotonic() - start < seconds, "fixed file hash deadline exceeded")
            part = os.read(fd, min(1024 * 1024, expected_size - amount))
            require(bool(part), "trusted file truncated during read")
            amount += len(part)
            digest.update(part)
        final = os.fstat(fd)
        require((final.st_dev, final.st_ino, final.st_size) ==
                (info.st_dev, info.st_ino, info.st_size),
                "trusted file identity shifted during hash")
        require(amount == expected_size and digest.hexdigest() == expected_hash,
                "trusted file SHA-256 mismatch")
        return {"sha256": digest.hexdigest(), "bytes": amount,
                "elapsed_seconds": round(time.monotonic() - start, 3),
                "owner_uid": info.st_uid, "mode": oct(stat.S_IMODE(info.st_mode))}
    finally:
        os.close(fd)


def validated_release_paths(data):
    require(isinstance(data, dict)
            and data.get("schema") == "merlin-local-model-provider/1"
            and data.get("status") == "ready"
            and data.get("qualification") is False
            and data.get("model") == MODEL_ALIAS, "manifest fixed role differs")
    model = data.get("model_artifact", {})
    runtime = data.get("runtime", {})
    require(isinstance(model, dict) and isinstance(runtime, dict)
            and model.get("sha256") == MODEL_SHA
            and model.get("size_bytes") == MODEL_BYTES
            and model.get("repository_revision") == REVISION
            and runtime.get("source_commit") == SOURCE_COMMIT,
            "fixed model or runtime provenance differs")
    bsha = runtime.get("binary_sha256")
    binary = runtime.get("binary_path")
    weights = model.get("path")
    require(isinstance(bsha, str) and re.fullmatch("[a-f0-9]{64}", bsha)
            and isinstance(binary, str) and isinstance(weights, str),
            "trusted manifest lacks exact binary identity")
    bpath, wpath = Path(binary), Path(weights)
    # No arbitrary model paths: both must live in one immutable release leaf.
    require(bpath.name == "llama-server"
            and wpath.name == "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
            and bpath.parent == wpath.parent
            and bpath.parent.parent == RELEASES
            and re.fullmatch("[a-f0-9]{64}", bpath.parent.name),
            "model release directory differs")
    for parent in [RELEASES, bpath.parent]:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0
                and not (stat.S_IMODE(info.st_mode) & 0o022),
                "release parent is symbolic, writable or not root-owned")
    return bpath, wpath, bsha


def headroom():
    memory = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            memory["mem_available_bytes"] = int(line.split()[1]) * 1024
            break
    require("mem_available_bytes" in memory, "MemAvailable not observed")
    # cgroup v2, when finite, is a second stricter bound.
    v2 = Path("/sys/fs/cgroup")
    if (v2 / "memory.max").is_file() and (v2 / "memory.current").is_file():
        max_raw = (v2 / "memory.max").read_text().strip()
        current_raw = (v2 / "memory.current").read_text().strip()
        if max_raw != "max":
            memory["cgroup_memory_remaining_bytes"] = max(0, int(max_raw) - int(current_raw))
    memory["candidate_headroom_bytes"] = min(memory.values())
    memory["meets_two_gib_gate"] = memory["candidate_headroom_bytes"] >= MIN_MEMORY_HEADROOM
    return memory


def check_version(binary, seconds=12):
    def bounds():
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024, 256 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    argv = ["/usr/bin/unshare", "--user", "--map-current-user", "--net",
            "--fork", str(binary), "--version"]
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
           "HOME": "/var/empty", "TMPDIR": "/tmp",
           "PYTHONDONTWRITEBYTECODE": "1"}
    start = time.monotonic()
    proc = subprocess.Popen(argv, cwd="/", env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True, preexec_fn=bounds)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate(timeout=3)
    require(not timed_out, "fixed binary version invocation timed out")
    require(len(stdout) <= 16 * 1024 and len(stderr) <= 16 * 1024,
            "version output exceeds ceiling")
    require(proc.returncode == 0 and bool((stdout + stderr).strip()),
            "fixed binary --version did not complete normally")
    return {"command": "unshare-current-user-net-only llama-server --version",
            "exit_code": proc.returncode,
            "version_output_sha256": hashlib.sha256(stdout + stderr).hexdigest(),
            "version_output_excerpt": (stdout + stderr).decode("utf-8", "replace")[:256],
            "elapsed_seconds": round(time.monotonic() - start, 3),
            "external_network_connected": False}


def preflight(evidence):
    require(os.geteuid() == 1000 and platform.machine() == "aarch64",
            "exact nonroot OCI machine required")
    evidence = Path(evidence)
    require(evidence.is_dir() and not evidence.is_symlink(),
            "private evidence directory required")
    receipt = {"schema": "merlin-oci-nonroot-model-integrity/1", "status": "blocked",
               "model_generation_calls": 0, "root_execution": False,
               "service_mutations": False, "model_file_modified": False,
               "package_installation": False, "production_qualified": False,
               "full_model_quality_qualified": False}
    stage = "manifest"
    try:
        raw = MANIFEST.read_bytes()
        require(len(raw) <= 16384 and hashlib.sha256(raw).hexdigest() == MANIFEST_SHA,
                "root manifest exact digest differs")
        fd, _ = regular(MANIFEST, 16384)
        try:
            stable = os.read(fd, 16385)
        finally:
            os.close(fd)
        require(stable == raw, "manifest changed during read")
        manifest = json.loads(stable, object_pairs_hook=unique)
        binary, weights, binary_hash = validated_release_paths(manifest)
        receipt["manifest_sha256"] = MANIFEST_SHA
        stage = "binary_sha256"
        bs = binary.stat().st_size
        require(0 < bs <= BINARY_LIMIT, "model executable size exceeds limit")
        receipt["binary"] = full_digest(binary, bs, binary_hash, seconds=45)
        require(os.access(binary, os.X_OK), "trusted executable is not executable")
        stage = "model_sha256"
        receipt["model"] = full_digest(weights, MODEL_BYTES, MODEL_SHA, seconds=120)
        stage = "resource_budget"
        receipt["memory"] = headroom()
        # This preflight invokes only --version; no model is loaded regardless
        # of free memory. A later model-loading workflow must recheck budget.
        stage = "version_smoke"
        receipt["version"] = check_version(binary)
        receipt["eligible_for_separate_inference_trial"] = bool(
            receipt["memory"]["meets_two_gib_gate"])
        receipt["status"] = "hashes_verified_version_passed_no_inference"
        return receipt
    except BaseException as exc:
        receipt["blocked_at_stage"] = stage
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)[:240]
        raise
    finally:
        (evidence / "model-integrity-result.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2))
        print(json.dumps({"status": receipt["status"],
                          "blocked_at_stage": receipt.get("blocked_at_stage"),
                          "eligible_for_separate_inference_trial": receipt.get(
                              "eligible_for_separate_inference_trial", False),
                          "model_generation_calls": 0,
                          "production_qualified": False}, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("fixed private evidence directory argument required")
    try:
        preflight(sys.argv[1])
    except Exception:
        raise SystemExit(2)

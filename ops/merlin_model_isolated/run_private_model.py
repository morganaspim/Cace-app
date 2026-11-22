#!/usr/bin/env python3
"""One-shot unprivileged Merlin local-model inference; exact model/binary identity.

Phase setup is called only inside a fresh rootless user+net namespace, where
CAP_NET_ADMIN is temporary and restricted to that disposable namespace.
It activates ONLY lo, then launches phase test with all capabilities removed,
no_new_privs and no outgoing route. No host service alteration or installs.
"""
from __future__ import annotations
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import resource
import signal
import socket
import stat
import struct
import subprocess
import sys
import time

ROOT = "/opt/merlin-model-provider/releases/3f432dc172cf06f1af75974dbc4ec2b9135a8a82bd1fa2bfc35c0e53fe69f33e"
BINARY = ROOT + "/llama-server"
MODEL = ROOT + "/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
ALIAS = "merlin-qwen-coder-1.5b-q4"
PORT = 18772
PINS = {
    "binary": (BINARY, 14614984,
               "af4c10f1f4a1e7f0878dc9b3896bb742f65170861276ef04ddecdf2a9be3cd82"),
    "model": (MODEL, 1117320768,
              "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046")}
COMMAND = [BINARY, "--model", MODEL, "--alias", ALIAS, "--host",
           "127.0.0.1", "--port", str(PORT), "--ctx-size", "2048",
           "--parallel", "1", "--threads", "2", "--threads-batch", "2",
           "--threads-http", "2", "--n-gpu-layers", "0", "--offline", "--no-webui"]
TESTS = [
    {"question": "Compute 6 times 7. Reply with only the number.",
     "expected": "42"},
    {"question": "Compute 19 plus 23. Reply with only the number.",
     "expected": "42"},
]


def require(test, why):
    if not test:
        raise RuntimeError(why)


def files():
    observations = {}
    for label, (path, expected_size, expected_sha) in PINS.items():
        before = os.lstat(path)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == 65534
                and not stat.S_IMODE(before.st_mode) & 0o022
                and before.st_size == expected_size, "fixed " + label + " metadata differs")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        digest = hashlib.sha256()
        actual_size = 0
        try:
            handle = os.fstat(fd)
            require((handle.st_dev, handle.st_ino, handle.st_size) ==
                    (before.st_dev, before.st_ino, before.st_size),
                    label + " changed during open")
            deadline = time.monotonic() + 75
            while True:
                require(time.monotonic() < deadline, "fixed file hash deadline exceeded")
                chunk = os.read(fd, 4 * 1024 * 1024)
                if not chunk:
                    break
                actual_size += len(chunk)
                require(actual_size <= expected_size, "hashed bytes exceed pin")
                digest.update(chunk)
            after = os.fstat(fd)
            require((after.st_dev, after.st_ino, after.st_size) ==
                    (before.st_dev, before.st_ino, before.st_size),
                    label + " changed during hashing")
        finally:
            os.close(fd)
        require(actual_size == expected_size and digest.hexdigest() == expected_sha,
                "pinned " + label + " digest mismatch")
        observations[label] = {"sha256": digest.hexdigest(), "bytes": actual_size,
                               "dev": before.st_dev, "ino": before.st_ino}
    return observations


def status(pid):
    values = {}
    for line in Path("/proc/%d/status" % pid).read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            if k in ("Uid", "CapEff", "NoNewPrivs", "Seccomp"):
                values[k] = v.strip()
    return values


def namespace_identity(parent):
    require(os.geteuid() == 1000, "UID1000 required")
    require(os.stat("/proc/self/ns/net").st_ino != parent,
            "private network namespace missing")
    require(Path("/proc/self/uid_map").read_text().split() == ["1000", "1000", "1"],
            "unexpected uid mapping")
    require(sorted(n for _, n in socket.if_nameindex()) == ["lo"],
            "unexpected interface inside model netns")
    routes = Path("/proc/net/route").read_text().splitlines()[1:]
    require(all(len(x.split()) < 2 or x.split()[1] != "00000000" for x in routes),
            "default IPv4 route in model netns")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
        request = struct.pack("16sH14s", b"lo", 0, b"")
        _, flags, _ = struct.unpack("16sH14s", fcntl.ioctl(sk.fileno(), 0x8913, request))
        require(flags & 1, "loopback not up")
    return os.stat("/proc/self/ns/net").st_ino


def json_local(method, path, payload=None, seconds=6):
    require((method, path) in {
        ("GET", "/health"), ("GET", "/v1/models"),
        ("POST", "/v1/chat/completions")}, "unapproved local HTTP path")
    data = None if payload is None else json.dumps(payload, allow_nan=False).encode()
    require(data is None or len(data) <= 4096, "model request too large")
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=seconds)
    try:
        conn.request(method, path, body=data, headers={
            "Host": "127.0.0.1:%d" % PORT, "Content-Type": "application/json",
            "Connection": "close"})
        resp = conn.getresponse()
        buf = resp.read(65537)
        require(len(buf) <= 65536, "model response exceeds bound")
        require(resp.status == 200, "model HTTP status " + str(resp.status))
        result = json.loads(buf)
        require(isinstance(result, dict), "model HTTP returned nonobject")
        return result
    finally:
        conn.close()


def check_process(pid, source, parent):
    require(os.stat("/proc/%d/ns/net" % pid).st_ino ==
            os.stat("/proc/self/ns/net").st_ino != parent,
            "model process outside private namespace")
    st = status(pid)
    require(st.get("Uid", "").split() == ["1000"] * 4
            and st.get("CapEff") == "0000000000000000"
            and st.get("NoNewPrivs") == "1",
            "model worker gained authority")
    actual = os.stat("/proc/%d/exe" % pid)
    require(os.readlink("/proc/%d/exe" % pid) == BINARY
            and (actual.st_dev, actual.st_ino) ==
                (source["binary"]["dev"], source["binary"]["ino"]),
            "executing model binary differs from hash-bound image")
    argv = Path("/proc/%d/cmdline" % pid).read_bytes().split(b"\0")
    require(argv[-1] == b"" and [a.decode() for a in argv[:-1]] == COMMAND,
            "executing model argv differs")
    lines = Path("/proc/%d/maps" % pid).read_text().splitlines()
    expected_device = "%02x:%02x" % (
        os.major(source["model"]["dev"]), os.minor(source["model"]["dev"]))
    mapped = []
    for line in lines:
        fields = line.split(None, 5)
        if len(fields) == 6 and fields[5] == MODEL:
            mapped.append(fields[3] == expected_device
                          and fields[4] == str(source["model"]["ino"]))
    require(mapped and all(mapped), "running model mmap not bound to hashed GGUF")
    return {"pid": pid, "uid": 1000, "cap_effective": st["CapEff"],
            "no_new_privs": True, "model_mmap_verified": True,
            "binary_device_inode_match": True,
            "command_sha256": hashlib.sha256(json.dumps(COMMAND).encode()).hexdigest(),
            "netns_inode": os.stat("/proc/%d/ns/net" % pid).st_ino}


def restricted_limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (12 * 1024 * 1024, 12 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_CPU, (260, 260))
    resource.setrlimit(resource.RLIMIT_AS, (6 * 1024**3, 6 * 1024**3))


def test(out, parent):
    st = status(os.getpid())
    require(st.get("CapEff") == "0000000000000000"
            and st.get("NoNewPrivs") == "1",
            "child capabilities still enabled")
    net = namespace_identity(parent)
    result = {"schema": "merlin-oci-private-model-generations/1",
              "status": "blocked", "uid": 1000, "netns_inode": net,
              "host_network_modified": False, "existing_service_modified": False,
              "root_used": False, "software_installation": False,
              "model_execution_under_userns": True,
              "production_qualified": False, "generation_requests": 0}
    server = None
    started = time.monotonic()
    scratch = out / "worker-home"
    scratch.mkdir(mode=0o700, exist_ok=False)
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
           "HOME": str(scratch), "TMPDIR": str(scratch),
           "XDG_CACHE_HOME": str(scratch), "XDG_CONFIG_HOME": str(scratch),
           "GGML_N_THREADS": "2", "OMP_NUM_THREADS": "2",
           "OPENBLAS_NUM_THREADS": "2", "GGML_CUDA_ENABLE_UNIFIED_MEMORY": "0"}
    try:
        source = files()
        result["file_sha256"] = {k: v["sha256"] for k, v in source.items()}
        result["bytes_hashed"] = {k: v["bytes"] for k, v in source.items()}
        with (out / "model-server.stdout.log").open("wb") as so, \
             (out / "model-server.stderr.log").open("wb") as se:
            server = subprocess.Popen(COMMAND, cwd="/", env=env,
                stdin=subprocess.DEVNULL, stdout=so, stderr=se,
                start_new_session=True, preexec_fn=restricted_limits)
        # Probe real process identity before/after I/O. No generation request
        # may be made until the worker binary, uid, argv and model map match.
        ready = False
        start_wait = time.monotonic()
        for _ in range(400):
            require(time.monotonic() - start_wait < 160,
                    "private model server startup time exceeded")
            require(server.poll() is None, "private model server terminated early")
            try:
                health = json_local("GET", "/health", seconds=2)
                if health.get("status") == "ok":
                    ready = True
                    break
            except (OSError, ValueError, RuntimeError, http.client.HTTPException):
                pass
            time.sleep(0.3)
        require(ready, "private model HTTP health never became ready")
        before = check_process(server.pid, source, parent)
        models = json_local("GET", "/v1/models", seconds=4)
        names = [row.get("id") for row in models.get("data", [])
                 if isinstance(row, dict)]
        require(ALIAS in names, "model alias missing from private endpoint")
        results = []
        for test_case in TESTS:
            require(server.poll() is None, "private model process exited during test")
            input_data = {"model": ALIAS, "messages": [
                {"role": "system", "content": "You are Merlin. Return only the integer answer to the arithmetic question."},
                {"role": "user", "content": test_case["question"]}],
                "max_tokens": 32, "temperature": 0, "stream": False, "seed": 7}
            result["generation_requests"] += 1
            response = json_local("POST", "/v1/chat/completions", input_data, seconds=100)
            choices = response.get("choices")
            require(isinstance(choices, list) and len(choices) == 1
                    and isinstance(choices[0], dict)
                    and isinstance(choices[0].get("message"), dict),
                    "model did not return chat completion")
            message = choices[0]["message"].get("content")
            require(isinstance(message, str) and 0 < len(message) < 500,
                    "model response content missing or overlong")
            normalized = message.strip().strip(".").strip()
            good = bool(re.fullmatch(re.escape(test_case["expected"]), normalized))
            usage = response.get("usage", {})
            n = usage.get("completion_tokens")
            require(type(n) is int and 1 <= n <= 32, "model token budget violated")
            results.append({"prompt_sha256": hashlib.sha256(
                            test_case["question"].encode()).hexdigest(),
                            "expected": test_case["expected"],
                            "response_sha256": hashlib.sha256(message.encode()).hexdigest(),
                            "response_text": message[:100], "correct": good,
                            "completion_tokens": n})
        after = check_process(server.pid, source, parent)
        require(before == after, "model provider identity changed during inference")
        result.update(status="passed" if all(x["correct"] for x in results)
                      else "failed_independent_math_reference",
                      worker=before, generations=results,
                      model_alias=ALIAS,
                      correct_count=sum(x["correct"] for x in results),
                      elapsed_seconds=round(time.monotonic() - started, 3))
        return result["status"] == "passed"
    except BaseException as exc:
        result["failure_type"] = type(exc).__name__
        result["failure_reason"] = str(exc)[:200]
        return False
    finally:
        if server is not None:
            if server.poll() is None:
                try: os.killpg(server.pid, signal.SIGTERM)
                except ProcessLookupError: pass
            try: server.wait(timeout=7)
            except subprocess.TimeoutExpired:
                try: os.killpg(server.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                server.wait(timeout=5)
            result["worker_terminated"] = server.poll() is not None
        else:
            result["worker_terminated"] = True
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (out / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2))
        print(json.dumps({"status": result["status"],
            "generation_requests": result["generation_requests"],
            "correct_count": result.get("correct_count", 0),
            "worker_terminated": result["worker_terminated"],
            "production_qualified": False}, sort_keys=True))


def setup(out, parent):
    namespace_identity(parent) if False else None
    require(os.geteuid() == 1000, "setup must be UID1000")
    require(Path("/proc/self/uid_map").read_text().split() == ["1000", "1000", "1"],
            "model setup userns identity mismatch")
    require(os.stat("/proc/self/ns/net").st_ino != parent, "no private model netns")
    require(sorted(n for _, n in socket.if_nameindex()) == ["lo"],
            "model namespace has non-loopback interfaces")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
        request = struct.pack("16sH14s", b"lo", 0, b"")
        name, flags, pad = struct.unpack("16sH14s",
                                         fcntl.ioctl(sk.fileno(), 0x8913, request))
        require(name.rstrip(b"\0") == b"lo", "wrong lo name")
        if not flags & 1:
            fcntl.ioctl(sk.fileno(), 0x8914,
                        struct.pack("16sH14s", b"lo", flags | 1, pad))
    namespace_identity(parent)
    proc = subprocess.run(["/usr/bin/setpriv", "--no-new-privs",
        "--bounding-set=-all", "--inh-caps=-all", "/usr/bin/python3",
        "-I", "-B", str(Path(__file__).resolve()), "test", str(out), str(parent)],
        cwd="/", stdin=subprocess.DEVNULL, capture_output=True,
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
             "PYTHONDONTWRITEBYTECODE": "1",
             "HOME": str(out)}, timeout=330)
    (out / "worker.stdout").write_bytes(proc.stdout[:65536])
    (out / "worker.stderr").write_bytes(proc.stderr[:65536])
    require(len(proc.stdout) <= 65536 and len(proc.stderr) <= 65536,
            "model acceptance child output ceiling exceeded")
    return proc.returncode == 0


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ("setup", "test"):
        raise SystemExit("requires fixed phase, evidence directory and parent netns inode")
    phase, evidence_dir, raw_parent = sys.argv[1:]
    parent = int(raw_parent)
    out = Path(evidence_dir)
    require(out.is_dir() and not out.is_symlink(), "evidence directory missing")
    if phase == "setup":
        try:
            return 0 if setup(out, parent) else 2
        except BaseException as exc:
            (out / "setup-error.json").write_text(json.dumps({
                "status": "blocked", "type": type(exc).__name__,
                "reason": str(exc)[:200], "production_qualified": False}))
            return 2
    return 0 if test(out, parent) else 2


if __name__ == "__main__":
    raise SystemExit(main())

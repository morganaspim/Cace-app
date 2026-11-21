"""Fixed OCI inspection and exact-source software tests, without deployment.

This controller does not install software, change services, run model generation,
acquire research sources, or attest a sandbox. Its children use the runner's UID.
"""
from __future__ import annotations

import hashlib
import http.client
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import selectors
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone

PRODUCT_COMMIT = "8497597f297bba83189afef2026c27f9244537ce"
APPLICATION_PREDECESSOR = "3022e0fcfff8908718abafbd6684a8ac6d13765e"
BROWSER_COMMIT = "74bd09166f338172f4af3854a124c12b5b07081a"
OPS_REPOSITORY = "morganaspim/Cace-app"
OPS_REF = "refs/heads/merlin/browser-operations-20261121"
OPERATION = "inspect-and-test-studio-8497597"
MODEL_ID = "merlin-qwen-coder-1.5b-q4"
PROVIDER_ROOT = "/opt/merlin-model-provider/releases/3f432dc172cf06f1af75974dbc4ec2b9135a8a82bd1fa2bfc35c0e53fe69f33e"
PROVIDER_FILES = {
    "model": {"path": PROVIDER_ROOT + "/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
              "bytes": 1117320768, "maximum": 1117320768,
              "sha256": "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"},
    "binary": {"path": PROVIDER_ROOT + "/llama-server", "maximum": 128 * 1024 * 1024,
               "sha256": "af4c10f1f4a1e7f0878dc9b3896bb742f65170861276ef04ddecdf2a9be3cd82"},
    "service_unit": {"path": "/etc/systemd/system/merlin-model-provider.service",
                     "maximum": 65536,
                     "sha256": "77629b0ef1afc4bcca4fa11282e6ca0bb7f0164110982fe85ae8ca6c267cad99"},
}
TOKEN_REQUEST_SHA256 = "07545d5ef91771730f35054d290e721dadfd0efe401b1948e15ea8a4f816a4de"
EXPECTED_PATHS = frozenset({
    "cpp/include/expert_robot/protocol.hpp", "cpp/include/expert_robot/runtime.hpp",
    "cpp/src/main.cpp", "cpp/src/runtime.cpp", "portable/build_portable.py",
    "portable/merlin_studio/MODEL_SETUP.md", "portable/merlin_studio/README.md",
    "portable/merlin_studio/START.bat", "portable/merlin_studio/START.command",
    "portable/merlin_studio/START.sh", "portable/merlin_studio/bin/README.md",
    "portable/merlin_studio/engine.py", "portable/merlin_studio/model.py",
    "portable/merlin_studio/models/README.md", "portable/merlin_studio/public_web.py",
    "portable/merlin_studio/server.py", "portable/merlin_studio/storage.py",
    "portable/merlin_studio/tests/test_studio.py", "portable/merlin_studio/tools.py",
    "portable/merlin_studio/web/index.html", "portable/merlin_studio/worker.py",
    "portable/tests/test_model_deadline.py", "portable/tests/test_public_web.py",
    "python/experimental_fault_advisory.py", "python/experimental_self_healing.py",
    "python/merlin/__init__.py", "python/merlin/artifact_ref.py",
    "python/merlin/project_registry.py", "python/merlin_research_browser.py",
    "python/orchestrator.py", "python/runtime_supervisor.py", "scripts/verify_portable.py",
    "tests/test_experimental_self_healing.py", "tests/test_merlin_research_browser.py",
    "tests/test_orchestrator_protocol.py", "tests/test_runtime_supervisor.py",
})
PYTHON_CANDIDATES = tuple(
    prefix + name for prefix in ("/usr/bin/", "/usr/local/bin/")
    for name in ("python3.13", "python3.12", "python3.11", "python3.10", "python3")
)
STAGES = (
    ("recovery", "tests", "test_experimental_self_healing.py", 25),
    ("protocol", "tests", "test_orchestrator_protocol.py", 9),
    ("native_supervisor", "tests", "test_runtime_supervisor.py", 9),
    ("research", "tests", "test_merlin_research_browser.py", 4),
    ("studio", "portable/merlin_studio/tests", "test_studio.py", 35),
    ("transport", "portable/tests", "test_*.py", 29),
)
TEST_CODE = """import json,sys,unittest
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'portable'))
suite=unittest.defaultTestLoader.discover(str(root/sys.argv[2]),pattern=sys.argv[3])
result=unittest.TextTestRunner(verbosity=2).run(suite)
value={'tests':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),'skipped':len(result.skipped)}
value['passed']=result.wasSuccessful() and not result.skipped and result.testsRun==int(sys.argv[4])
Path(sys.argv[5]).write_text(json.dumps(value,sort_keys=True)+'\\n')
sys.exit(0 if value['passed'] else 1)
"""
PROBE_CODE = """import json,sys,sqlite3,ssl,http.client,multiprocessing,resource
print(json.dumps({'version':list(sys.version_info[:3]),'executable':sys.executable,'sqlite':sqlite3.sqlite_version,'ssl':ssl.OPENSSL_VERSION},sort_keys=True))
"""


class ValidationError(RuntimeError):
    pass


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValidationError("duplicate JSON field")
        result[key] = value
    return result


def parse_json(raw):
    return json.loads(raw, object_pairs_hook=unique)


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(("blob %d\0" % len(raw)).encode() + raw).hexdigest()}


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as target:
        json.dump(value, target, sort_keys=True, indent=2, allow_nan=False)
        target.write("\n")


def validate_request(request, execution):
    if (not isinstance(request, dict)
        or set(request) != {"schema", "request_id", "operation", "created_at"}
        or request.get("schema") != "merlin-studio-validation-request/1"
        or request.get("operation") != OPERATION):
        raise ValidationError("exact fixed inspection/test request required")
    try:
        request_id = uuid.UUID(request["request_id"])
        when = datetime.strptime(request["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ValidationError("canonical UUID and UTC timestamp required") from exc
    if str(request_id) != request["request_id"] or request_id.version != 4:
        raise ValidationError("canonical UUID4 required")
    if when.strftime("%Y-%m-%dT%H:%M:%SZ") != request["created_at"]:
        raise ValidationError("canonical UTC timestamp required")
    if (execution.get("repository") != OPS_REPOSITORY or execution.get("ref") != OPS_REF
        or execution.get("runner") != "cace-oci-a1" or execution.get("uid") != 1000
        or execution.get("machine") != "aarch64" or execution.get("system") != "Linux"
        or type(execution.get("run_id")) is not int or execution["run_id"] <= 0
        or type(execution.get("run_attempt")) is not int or execution["run_attempt"] != 1
        or not isinstance(execution.get("workflow_commit"), str)
        or not re.fullmatch("[0-9a-f]{40}", execution["workflow_commit"])):
        raise ValidationError("fixed first-attempt OCI execution identity required")


def open_regular(path, *, owner=None, maximum=2 * 1024 * 1024):
    """Reject symlink ancestors and special files before reading any bytes."""
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValidationError("absolute fixed path required")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:-1]:
            next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_fd
        file_fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
                          dir_fd=descriptor)
    finally:
        os.close(descriptor)
    info = os.fstat(file_fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_size > maximum
        or owner is not None and (info.st_uid != owner or info.st_mode & 0o022)):
        os.close(file_fd)
        raise ValidationError("bounded immutable regular file required")
    return file_fd, info


def regular_identity(path, *, owner=None, maximum=2 * 1024 * 1024, seconds=60):
    descriptor, before = open_regular(path, owner=owner, maximum=maximum)
    started = time.monotonic()
    digest = hashlib.sha256()
    count = 0
    try:
        while True:
            if time.monotonic() - started > seconds:
                raise ValidationError("file identity deadline")
            raw = os.read(descriptor, 1024 * 1024)
            if not raw:
                break
            count += len(raw)
            if count > maximum:
                raise ValidationError("file identity byte ceiling")
            digest.update(raw)
        after = os.fstat(descriptor)
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if count != before.st_size or any(getattr(before, key) != getattr(after, key) for key in fields):
            raise ValidationError("file changed during identity read")
        return {"path": str(path), "bytes": count, "sha256": digest.hexdigest(),
                "owner": before.st_uid, "mode": oct(stat.S_IMODE(before.st_mode)),
                "device_id": before.st_dev, "inode": before.st_ino}
    finally:
        os.close(descriptor)


def read_small(path, maximum=2 * 1024 * 1024):
    descriptor, before = open_regular(path, maximum=maximum)
    try:
        raw = bytearray()
        while True:
            part = os.read(descriptor, min(65536, maximum + 1 - len(raw)))
            if not part:
                break
            raw.extend(part)
            if len(raw) > maximum:
                raise ValidationError("file byte ceiling")
        after = os.fstat(descriptor)
        if (len(raw) != before.st_size or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ino != after.st_ino or before.st_ctime_ns != after.st_ctime_ns):
            raise ValidationError("file changed during read")
        return bytes(raw)
    finally:
        os.close(descriptor)


def validate_bundle(pins, archive_bytes):
    if (not isinstance(pins, dict) or pins.get("schema") != "merlin-studio-validation-source/1"
        or pins.get("repository") != "Mannyspiro/expert-robot" or pins.get("commit") != PRODUCT_COMMIT
        or pins.get("application_bytes_equal_to") != APPLICATION_PREDECESSOR
        or pins.get("separate_browser_commit") != BROWSER_COMMIT
        or set(pins.get("files", {})) != EXPECTED_PATHS
        or identity(archive_bytes) != pins.get("archive") or len(archive_bytes) > 1024 * 1024):
        raise ValidationError("published source archive identity differs")
    members = {}
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        entries = archive.infolist()
        if len(entries) != len(EXPECTED_PATHS) or len({entry.filename for entry in entries}) != len(entries):
            raise ValidationError("duplicate or incomplete source inventory")
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (entry.filename not in EXPECTED_PATHS or path.is_absolute() or ".." in path.parts
                or "\\" in entry.filename or path.as_posix() != entry.filename
                or entry.is_dir() or not stat.S_ISREG(entry.external_attr >> 16)
                or entry.file_size > 256 * 1024 or entry.flag_bits & 1):
                raise ValidationError("unexpected source archive entry")
            raw = archive.read(entry)
            if identity(raw) != pins["files"][entry.filename]:
                raise ValidationError("published source member differs: " + entry.filename)
            members[entry.filename] = raw
    return members


def extract_bundle(members, target):
    target = Path(target)
    target.mkdir(mode=0o700, exist_ok=False)
    for name, raw in sorted(members.items()):
        path = target / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(raw)


def child_env(temporary):
    return {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
            "SYSTEMD_PAGER": "", "SYSTEMD_COLORS": "0"}


def run_process(argv, *, cwd, env, log, seconds, maximum=2 * 1024 * 1024):
    """Stream bounded partial evidence and kill the whole child group on failure."""
    start = time.monotonic()
    error = None
    count = 0
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        with Path(log).open("xb") as output:
            while selector.get_map():
                remaining = seconds - (time.monotonic() - start)
                if remaining <= 0:
                    raise ValidationError("child absolute deadline")
                for key, _ in selector.select(min(.1, remaining)):
                    raw = os.read(key.fd, 65536)
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    accepted = raw[:max(0, maximum - count)]
                    output.write(accepted)
                    output.flush()
                    count += len(accepted)
                    if len(accepted) != len(raw):
                        raise ValidationError("child output ceiling")
            process.wait(timeout=max(.01, seconds - (time.monotonic() - start)))
            if process.returncode:
                raise ValidationError("child exit " + str(process.returncode))
    except BaseException as exc:
        error = type(exc).__name__ + ": " + str(exc)[:1000]
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            error += "; child reaping deadline exceeded"
    finally:
        selector.close()
        process.stdout.close()
    result = {"passed": error is None and process.returncode == 0, "returncode": process.returncode,
              "elapsed_seconds": time.monotonic() - start, "output_bytes": count,
              "deadline_seconds": seconds, "output_limit": maximum, "error": error}
    write_json(str(log) + ".json", result)
    return result


def trusted_executable(path):
    resolved = Path(path).resolve(strict=True)
    actual = regular_identity(resolved, owner=0, maximum=128 * 1024 * 1024, seconds=10)
    if not os.access(resolved, os.X_OK):
        raise ValidationError("fixed executable is not executable")
    return resolved, actual


def inspect_python(out, env):
    inventory = []
    selected = None
    seen = set()
    for index, candidate in enumerate(PYTHON_CANDIDATES):
        entry = {"candidate": candidate, "passed": False}
        try:
            executable, file_info = trusted_executable(candidate)
            if str(executable) in seen:
                entry.update({"resolved": str(executable), "duplicate": True})
                inventory.append(entry)
                continue
            seen.add(str(executable))
            log = out / ("python-probe-%02d.txt" % index)
            result = run_process([str(executable), "-I", "-B", "-c", PROBE_CODE],
                                 cwd="/", env=env, log=log, seconds=5, maximum=65536)
            if not result["passed"]:
                raise ValidationError("stdlib interpreter probe failed")
            value = parse_json(read_small(log, 65536))
            version = value.get("version")
            if (not isinstance(version, list) or len(version) != 3
                or any(type(part) is not int for part in version) or version[0] != 3
                or not value.get("sqlite") or not value.get("ssl")):
                raise ValidationError("invalid interpreter probe")
            entry.update(value)
            entry.update({"file_identity": file_info, "passed": version[:2] >= [3, 10],
                          "executable": str(executable)})
            if entry["passed"] and (selected is None or version > selected["version"]):
                selected = dict(entry)
        except (OSError, ValueError, ValidationError) as exc:
            entry["error"] = type(exc).__name__ + ": " + str(exc)[:500]
        inventory.append(entry)
    return {"passed": selected is not None, "required": "Python 3.10+ with sqlite3 and ssl",
            "selected": selected, "candidates": inventory,
            "candidate_scope": "Fixed /usr/bin and /usr/local/bin python3.10 through python3.13 plus python3; other installation paths are not searched"}


def local_json(method, path, body=None):
    allowed = {("GET", "/health"), ("GET", "/v1/models"),
               ("POST", "/v1/chat/completions/input_tokens")}
    if (method, path) not in allowed or method == "GET" and body is not None:
        raise ValidationError("only fixed read-only provider endpoints are allowed")
    if method == "POST" and (body is None or hashlib.sha256(body).hexdigest() != TOKEN_REQUEST_SHA256):
        raise ValidationError("tokenization payload identity differs")
    connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=3)
    deadline = time.monotonic() + 8
    timer = None
    try:
        connection.connect()
        channel = connection.sock
        def expire():
            try:
                channel.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            channel.close()
        timer = threading.Timer(max(.001, deadline - time.monotonic()), expire)
        timer.daemon = True
        timer.start()
        headers = {"Accept": "application/json", "Connection": "close"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise ValidationError("provider read-only endpoint returned " + str(response.status))
        pairs = response.getheaders()
        lengths = [v for k, v in pairs if k.lower() == "content-length"]
        transfers = [v for k, v in pairs if k.lower() == "transfer-encoding"]
        if (len(lengths) > 1 or len(transfers) > 1 or lengths and transfers
            or lengths and (not re.fullmatch("[0-9]+", lengths[0]) or int(lengths[0]) > 128 * 1024)
            or transfers and transfers[0].lower() != "chunked"):
            raise ValidationError("ambiguous provider response framing")
        raw = bytearray()
        while True:
            if time.monotonic() >= deadline:
                raise ValidationError("provider absolute deadline")
            part = response.read(min(65536, 128 * 1024 + 1 - len(raw)))
            if not part:
                break
            raw.extend(part)
            if len(raw) > 128 * 1024:
                raise ValidationError("provider read-only response ceiling")
            if response.isclosed():
                break
        if time.monotonic() >= deadline or lengths and len(raw) != int(lengths[0]):
            raise ValidationError("incomplete or late provider response")
        return parse_json(bytes(raw))
    finally:
        if timer is not None:
            timer.cancel()
        connection.close()


def provider_argv():
    return [PROVIDER_FILES["binary"]["path"], "--model", PROVIDER_FILES["model"]["path"],
            "--alias", MODEL_ID, "--host", "127.0.0.1", "--port", "8080",
            "--ctx-size", "4096", "--parallel", "1", "--threads", "2",
            "--threads-batch", "2", "--threads-http", "2", "--n-gpu-layers", "0",
            "--offline", "--no-webui"]


def read_proc(pid, name, maximum=65536):
    if type(pid) is not int or not 1 < pid < 2**31 or name not in {"stat", "status", "cmdline", "maps"}:
        raise ValidationError("fixed provider process observation required")
    descriptor = os.open("/proc/%d/%s" % (pid, name), os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValidationError("regular proc observation required")
        raw = bytearray()
        while True:
            part = os.read(descriptor, min(65536, maximum + 1 - len(raw)))
            if not part:
                return bytes(raw)
            raw.extend(part)
            if len(raw) > maximum:
                raise ValidationError("provider proc observation ceiling")
    finally:
        os.close(descriptor)


def process_binding(service, files):
    """Read current process identity; denied cross-UID reads block qualification."""
    pid = int(service.get("MainPID", "0"))
    if not 1 < pid < 2**31:
        raise ValidationError("positive provider MainPID required")
    def start_ticks():
        value = read_proc(pid, "stat").decode().rsplit(")", 1)[1].split()[19]
        if not value.isdigit():
            raise ValidationError("provider start ticks are invalid")
        return value
    before = start_ticks()
    if os.readlink("/proc/%d/exe" % pid) != PROVIDER_FILES["binary"]["path"]:
        raise ValidationError("provider live executable differs")
    executable = os.stat("/proc/%d/exe" % pid)
    if (executable.st_dev, executable.st_ino) != (files["binary"]["device_id"], files["binary"]["inode"]):
        raise ValidationError("provider executable inode differs from hashed binary")
    status = read_proc(pid, "status").decode()
    if not re.search(r"^Uid:\s+981\s+981\s+981\s+981$", status, re.M):
        raise ValidationError("provider live UID differs from accepted merlin-model UID981")
    raw_argv = read_proc(pid, "cmdline", 8192)
    if not raw_argv.endswith(b"\0") or raw_argv[:-1].decode().split("\0") != provider_argv():
        raise ValidationError("provider live argv differs")
    namespace = os.readlink("/proc/%d/ns/net" % pid)
    if namespace != os.readlink("/proc/self/ns/net"):
        raise ValidationError("provider is not in the inspected loopback namespace")
    model = files["model"]
    device = "%02x:%02x" % (os.major(model["device_id"]), os.minor(model["device_id"]))
    matches = []
    for line in read_proc(pid, "maps", 2 * 1024 * 1024).decode().splitlines():
        fields = line.split(None, 5)
        if len(fields) == 6 and fields[5] == PROVIDER_FILES["model"]["path"]:
            matches.append(fields[3] == device and fields[4] == str(model["inode"]))
    if not matches or not all(matches):
        raise ValidationError("provider mapped model does not match the hashed file inode")
    if start_ticks() != before:
        raise ValidationError("provider process changed during inspection")
    argv_hash = hashlib.sha256((json.dumps(provider_argv(), sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()
    return {"passed": True, "pid": pid, "process_start_ticks": before, "uid": 981,
            "network_namespace": namespace, "binary_inode": files["binary"]["inode"],
            "model_inode": model["inode"], "argv_sha256": argv_hash}


def inspect_provider(out, env, token_request=None, *, tokenize=True):
    result = {"passed": False, "files": {}, "live_model_generation_calls": 0,
              "tokenization_calls": 0, "errors": [],
              "process_binding": {"passed": False, "status": "not_checked"}}
    for label, pin in PROVIDER_FILES.items():
        try:
            observed = regular_identity(pin["path"], owner=0, maximum=pin["maximum"])
            observed["passed"] = (observed["sha256"] == pin["sha256"]
                                  and ("bytes" not in pin or observed["bytes"] == pin["bytes"]))
            result["files"][label] = observed
            if not observed["passed"]:
                result["errors"].append(label + " identity mismatch")
        except (OSError, ValidationError) as exc:
            result["files"][label] = {"passed": False, "error": type(exc).__name__ + ": " + str(exc)[:500]}
            result["errors"].append(label + " unavailable")
    try:
        executable, _ = trusted_executable("/usr/bin/systemctl")
        log = out / "provider-service.txt"
        state = run_process([str(executable), "show", "merlin-model-provider.service",
                             "--property=LoadState,ActiveState,SubState,MainPID,FragmentPath"],
                            cwd="/", env=env, log=log, seconds=5, maximum=16384)
        if not state["passed"]:
            raise ValidationError("provider unit inspection failed")
        values = dict(line.split("=", 1) for line in read_small(log, 16384).decode().splitlines() if "=" in line)
        result["service"] = values
        if (values.get("LoadState") != "loaded" or values.get("ActiveState") != "active"
            or values.get("SubState") != "running"
            or values.get("FragmentPath") != PROVIDER_FILES["service_unit"]["path"]):
            raise ValidationError("provider service is not active at the pinned unit")
        if not result["errors"]:
            result["process_binding"] = process_binding(values, result["files"])
    except (OSError, ValueError, ValidationError, IndexError, KeyError) as exc:
        if result.get("service") and not result["process_binding"]["passed"]:
            result["process_binding"].update({"status": "unverified",
                "error": type(exc).__name__ + ": " + str(exc)[:500]})
        result["errors"].append(type(exc).__name__ + ": " + str(exc)[:500])
    if not result["errors"]:
        try:
            health = local_json("GET", "/health")
            models = local_json("GET", "/v1/models")
            if not isinstance(health, dict) or health.get("status") != "ok":
                raise ValidationError("provider health is not ready")
            if not isinstance(models, dict) or not isinstance(models.get("data"), list):
                raise ValidationError("provider model list is malformed")
            ids = [entry.get("id") for entry in models["data"] if isinstance(entry, dict)]
            if ids != [MODEL_ID]:
                raise ValidationError("provider model identity differs")
            result["health"] = health
            result["model_ids"] = ids
            if tokenize:
                result["tokenization_calls"] = 1
                tokens = local_json("POST", "/v1/chat/completions/input_tokens", token_request)
                count = tokens.get("input_tokens") if isinstance(tokens, dict) else None
                if (type(count) is not int or count <= 0 or tokens.get("object") != "response.input_tokens"
                    or count + 2048 + 128 > 4096):
                    raise ValidationError("unchanged initial Studio request exceeds provider context or count is invalid")
                result["initial_context"] = {"input_tokens": count, "max_tokens": 2048,
                                             "margin": 128, "context_tokens": 4096,
                                             "request_sha256": TOKEN_REQUEST_SHA256, "passed": True}
            after_log = out / "provider-service-after.txt"
            after_state = run_process([str(executable), "show", "merlin-model-provider.service",
                "--property=LoadState,ActiveState,SubState,MainPID,FragmentPath"],
                cwd="/", env=env, log=after_log, seconds=5, maximum=16384)
            if not after_state["passed"]:
                raise ValidationError("provider unit could not be rechecked after HTTP")
            after_values = dict(line.split("=", 1) for line in read_small(after_log, 16384).decode().splitlines() if "=" in line)
            result["service_after"] = after_values
            if (after_values.get("LoadState") != "loaded" or after_values.get("ActiveState") != "active"
                or after_values.get("SubState") != "running"
                or after_values.get("MainPID") != result["service"].get("MainPID")
                or after_values.get("FragmentPath") != PROVIDER_FILES["service_unit"]["path"]):
                raise ValidationError("provider service identity changed across read-only HTTP checks")
            if process_binding(after_values, result["files"]) != result["process_binding"]:
                raise ValidationError("provider process changed across read-only endpoint checks")
        except (OSError, ValueError, ValidationError, IndexError, KeyError, http.client.HTTPException) as exc:
            result["errors"].append(type(exc).__name__ + ": " + str(exc)[:500])
    result["passed"] = not result["errors"] and result["process_binding"]["passed"]
    return result


def model_preflight(provider, python_inventory, source_ok):
    chosen = python_inventory.get("selected") or {}
    service = provider.get("service", {})
    files = provider.get("files", {})
    return {"schema": "merlin-studio-model-preflight/1",
            "passed": bool(source_ok and provider.get("passed") and python_inventory.get("passed")
                           and provider.get("process_binding", {}).get("passed")),
            "observed_at": utc_now(), "studio_revision": PRODUCT_COMMIT,
            "provider_identity": {
                "model_sha256": files.get("model", {}).get("sha256"),
                "binary_sha256": files.get("binary", {}).get("sha256"),
                "service_unit_sha256": files.get("service_unit", {}).get("sha256"),
                "active_state": service.get("ActiveState"), "sub_state": service.get("SubState"),
                "model_id": MODEL_ID},
            "python": {"version": chosen.get("version"), "executable": chosen.get("executable")},
            "initial_context": provider.get("initial_context"),
            "process_binding": provider.get("process_binding"),
            "live_model_generation_calls": 0}


def run_source_tests(source, out, python_inventory, env, pins):
    result = {"status": "not_run", "passed": False, "expected_tests": 111,
              "tests": 0, "stages": [], "source_commit": PRODUCT_COMMIT,
              "provider_inference": False, "fixture_models": True,
              "not_run_stages": [entry[0] for entry in STAGES],
              "aggregate_deadline_seconds": 360}
    if not python_inventory["passed"]:
        result["blocker"] = "no supported Python 3.10+ at the fixed inspected paths; other paths not searched; no installation or version downgrade attempted"
        return result
    interpreter = python_inventory["selected"]["executable"]
    try:
        compiler, compiler_identity = trusted_executable("/usr/bin/g++")
    except (OSError, ValidationError) as exc:
        result["blocker"] = "fixed g++ compiler unavailable: " + type(exc).__name__
        return result
    result["compiler"] = compiler_identity
    deadline = time.monotonic() + 360
    def execute(argv, *, log, seconds, maximum=2 * 1024 * 1024, child_environment=env):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {"passed": False, "returncode": None, "error": "aggregate source-test deadline"}
        return run_process(argv, cwd=source, env=child_environment, log=log,
                           seconds=min(seconds, remaining), maximum=maximum)
    build = source / "build"
    build.mkdir(mode=0o700)
    runtime = build / "expert_robot_runtime"
    compile_result = execute([str(compiler), "-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic",
                                  "-I", "cpp/include", "cpp/src/runtime.cpp", "cpp/src/main.cpp", "-o", str(runtime)],
                                 log=out / "compile-protocol.txt", seconds=120)
    result["compile"] = compile_result
    if not compile_result["passed"]:
        result.update({"status": "failed", "blocker": "actual protocol core compilation failed"})
        return result
    test_env = dict(env)
    test_env["MERLIN_TEST_RUNTIME"] = str(runtime)
    for name, directory, pattern, expected in STAGES:
        summary = out / (name + "-tests.json")
        command = [interpreter, "-I", "-B", "-c", TEST_CODE, str(source), directory,
                   pattern, str(expected), str(summary)]
        observed = execute(command, log=out / (name + "-tests.txt"), child_environment=test_env,
                           seconds=120, maximum=4 * 1024 * 1024)
        entry = {"stage": name, "expected": expected, "process": observed, "status": "failed"}
        try:
            value = parse_json(read_small(summary, 16384))
            if (set(value) != {"tests", "errors", "failures", "skipped", "passed"}
                or any(type(value[k]) is not int for k in ("tests", "errors", "failures", "skipped"))
                or type(value["passed"]) is not bool):
                raise ValidationError("invalid test count receipt")
            entry["result"] = value
            entry["status"] = "passed" if (observed["passed"] and value["passed"]
                and value["tests"] == expected and value["errors"] == value["failures"] == value["skipped"] == 0) else "failed"
            result["tests"] += value["tests"]
        except (OSError, ValueError, ValidationError) as exc:
            entry["error"] = type(exc).__name__ + ": " + str(exc)[:500]
        result["stages"].append(entry)
        result["not_run_stages"].remove(name)
        if entry["status"] != "passed":
            result.update({"status": "failed", "blocker": "exact-count zero-skip source stage failed: " + name})
            return result
    package = build / "Merlin_Studio_Source_OCI.zip"
    result["package_kind"] = "source_only; existing --include-native supports Linux x86_64, not this aarch64 host"
    for name, args in (("build-source-package", ["portable/build_portable.py", "--output", str(package)]),
                       ("verify-source-package", ["scripts/verify_portable.py", str(package)])):
        checked = execute([interpreter, "-I", "-B"] + args, log=out / (name + ".txt"), seconds=60)
        result[name] = checked
        if not checked["passed"]:
            result.update({"status": "failed", "blocker": name + " failed"})
            return result
    for path, pin in pins["files"].items():
        if identity(read_small(source / path, 256 * 1024)) != pin:
            raise ValidationError("source changed during tests: " + path)
    result.update({"status": "passed", "passed": result["tests"] == 111,
                   "runtime": regular_identity(runtime, maximum=16 * 1024 * 1024),
                   "package": regular_identity(package, maximum=2 * 1024 * 1024),
                   "native_protocol_tests": 3, "skipped": 0})
    return result


def run(request, execution, source_directory, out):
    validate_request(request, execution)
    out = Path(out)
    source_directory = Path(source_directory)
    pins = parse_json(read_small(source_directory / "source-pins.json"))
    archive_bytes = read_small(source_directory / "product-source.zip")
    members = validate_bundle(pins, archive_bytes)
    token_request = read_small(source_directory / "initial-model-request.json", 128 * 1024)
    if hashlib.sha256(token_request).hexdigest() != TOKEN_REQUEST_SHA256:
        raise ValidationError("initial Studio tokenization payload differs")
    source = out / "exact-product-source"
    extract_bundle(members, source)
    temporary = out / "temporary"
    temporary.mkdir(mode=0o700)
    env = child_env(temporary)
    write_json(out / "source-identities.json", pins)
    python_inventory = inspect_python(out, env)
    write_json(out / "python-inventory.json", python_inventory)
    provider = inspect_provider(out, env, token_request)
    write_json(out / "provider-inspection.json", provider)
    preflight = model_preflight(provider, python_inventory, True)
    write_json(out / "studio-model-preflight.json", preflight)
    tests = run_source_tests(source, out, python_inventory, env, pins)
    write_json(out / "source-test-results.json", tests)
    receipt = {"schema": "merlin-studio-oci-validation/1", "request": request, "execution": execution,
               "observed_at": utc_now(), "status": "passed" if tests["passed"] and preflight["passed"] else
               ("failed" if tests["status"] == "failed" else "blocked"),
               "source_commit": PRODUCT_COMMIT, "separate_browser_commit": BROWSER_COMMIT,
               "source_tests": tests, "studio_model_preflight": preflight,
               "software_installation": False, "service_mutations": False,
               "research_source_acquisitions": 0, "live_model_generation_calls": 0,
               "provider_tokenization_calls": provider["tokenization_calls"],
               "automatic_retry": False, "promotion_authority": False, "qualification": False,
               "isolation_scope": "ordinary unprivileged runner processes, not an OS sandbox"}
    write_json(out / "validation-receipt.json", receipt)
    return receipt

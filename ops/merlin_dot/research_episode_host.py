"""Pinned root supervisor for one source-grounded Merlin research episode.

This is an operational gateway, not a caller-configurable execution interface.
The renderer must replace PINS with actual accepted source/evidence identities.
All candidate evaluation remains in SystemdFixedPythonProcess nonroot workers.
"""
import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import socket
import sqlite3
import stat
import struct
import subprocess
import sys
import tempfile
import time
import zipfile

PINS = {'native_validation': {'artifact_bytes': 648079, 'artifact_id': 14712123112, 'artifact_sha256': '77ad1e585dc978022515ef05683f2d59a5fd54b2f9bc576782ad600c72aeb75a', 'controller_git_blob': 'd4e3325a9d1c5c8c9d03b93c4b19b58e09232d04', 'controller_sha256': 'bb55bba0fe1fdf4b77e53c02d2f724f4301e550a96c75266092f11b3435503ef', 'report_sha256': '004c916100162ca83cd34dce50fc9704ea98cca058a4a20acd9660071910a271', 'run_attempt': 1, 'run_id': 44916652257, 'software_tests': 597, 'source_commit': 'ed6be62d577f0675d50a4487b7a9f43270bb515f', 'source_map_sha256': '85bc3c30d91c72c2f960a98539cdb72809a2ae0610df8e239018c77940452c2a', 'source_package_sha256': 'c4263a03ccfa9f728f186e0caf9f1382f8e4fc8501e4dc56f1cb2fde3b50cab6', 'test_inventory_sha256': '141f459fc85791b6cfca49001653847a32c1f08b30cbd865491c629e4c9ae1c8', 'workflow_commit': 'b2a7aacfcf73396ab92f2104245d70715fd2dd9d', 'workflow_git_blob': 'bb86a2d649d7ecaa2036dedf6622194f61f4b10d'}, 'oracle_sha256': '73ad01b8443ab3e72ee3d54c43a75ff55104b75a3d4125cc17599cced87e9abb', 'source_commit': 'ed6be62d577f0675d50a4487b7a9f43270bb515f', 'source_file_count': 130, 'source_map_sha256': '85bc3c30d91c72c2f960a98539cdb72809a2ae0610df8e239018c77940452c2a', 'source_notes_sha256': 'ad412f724f95df30077a6fb21503a5f291478a0048f762e2c16bddefdbfb7192', 'source_package_sha256': 'c4263a03ccfa9f728f186e0caf9f1382f8e4fc8501e4dc56f1cb2fde3b50cab6', 'worker_sha256': '7f0947df45c3239cce48dd7e112886f4ccff98dd097673d0275844d227caf8f6'}
HOST_SOURCE_LIMIT = 48 * 1024
SESSION = "merlin-exact-solver-20261121"
PROJECT = "dot-production-docs"
STATE = Path("/var/lib/merlin-dot-private/state")
CONFIG = Path("/etc/merlin-dot-private/config.json")
SOCKET = Path("/run/merlin-dot-private/tools.sock")
PROVIDER = Path("/etc/merlin-model-provider")
HOST_PREFIX = "local-research/" + SESSION + "/host/"
ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8",
       "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
MODEL_SHA = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
RUNTIME_COMMIT = "2a4daf0e08d6a9b6993ee0d4a9a3cfc35a6f405c"
MODEL_BYTES = 1117320768


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def read_regular(path, maximum, *, root_owned=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ValueError("bounded regular file required")
        if root_owned and (before.st_uid != 0 or before.st_mode & 0o022):
            raise PermissionError("root-owned immutable host file required")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(maximum + 1)
        after = os.fstat(fd)
        identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        if len(data) > maximum or identity(before) != identity(after):
            raise ValueError("file changed while reading")
        return data
    finally:
        os.close(fd)


def hash_large(path, expected_bytes):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0
                or before.st_mode & 0o022 or before.st_size != expected_bytes):
            raise ValueError("fixed root-owned model size/ownership differs")
        digest = hashlib.sha256()
        with os.fdopen(fd, "rb", closefd=False) as stream:
            for chunk in iter(lambda: stream.read(256 * 1024), b""):
                digest.update(chunk)
        after = os.fstat(fd)
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, name) != getattr(after, name) for name in fields):
            raise ValueError("model changed while hashing")
        return digest.hexdigest()
    finally:
        os.close(fd)


def service(name):
    if name not in {"merlin-model-provider.service", "merlin-dot-private.service"}:
        raise ValueError("fixed unit required")
    command = ["/usr/bin/systemctl", "show", name,
        "--property=ActiveState,SubState,MainPID,User,Group,PrivateNetwork,RestrictAddressFamilies,MemoryMax,MemorySwapMax,CPUQuotaPerSecUSec,TasksMax"]
    result = subprocess.run(command, env=ENV, cwd="/", capture_output=True, timeout=8)
    if result.returncode or len(result.stdout) > 8192:
        raise RuntimeError("bounded service observation failed")
    return dict(line.split("=", 1) for line in result.stdout.decode().splitlines() if "=" in line)


def require_provider():
    manifest_raw = read_regular(PROVIDER / "manifest.json", 16384, root_owned=True)
    bootstrap_raw = read_regular(PROVIDER / "bootstrap-receipt.json", 65536, root_owned=True)
    manifest = json.loads(manifest_raw, object_pairs_hook=unique)
    bootstrap = json.loads(bootstrap_raw, object_pairs_hook=unique)
    if (manifest.get("schema") != "merlin-local-model-provider/1"
            or manifest.get("status") != "ready"
            or manifest.get("endpoint") != "http://127.0.0.1:8080/v1/chat/completions"
            or manifest.get("model") != "merlin-qwen-coder-1.5b-q4"
            or manifest.get("bootstrap_receipt_sha256") != sha(bootstrap_raw)
            or manifest.get("qualification") is not False or manifest.get("promotion_authority") is not False
            or bootstrap.get("schema") != "merlin-local-model-bootstrap-receipt/1"
            or bootstrap.get("smoke", {}).get("passed") is not True):
        raise ValueError("actual accepted provider bootstrap evidence required")
    model, runtime = manifest["model_artifact"], manifest["runtime"]
    if (model.get("sha256") != MODEL_SHA or model.get("size_bytes") != MODEL_BYTES
            or runtime.get("source_commit") != RUNTIME_COMMIT
            or runtime.get("source_tree_sha") != "445f2b6c9555e93c2e2c526d68497d8f47d97a1d"
            or runtime.get("source_archive_sha256") != "fd484b0ba95d74e0cd76ff7793f220fa3bb64bf85c9638962783d1085ee8bd28"):
        raise ValueError("provider model/runtime identity differs")
    for path in (model["path"], runtime["binary_path"]):
        if not str(Path(path).resolve()).startswith("/opt/merlin-model-provider/releases/"):
            raise ValueError("fixed versioned provider path required")
    if hash_large(model["path"], MODEL_BYTES) != MODEL_SHA:
        raise ValueError("actual model bytes differ")
    binary_sha = sha(read_regular(runtime["binary_path"], 128 * 1024 * 1024, root_owned=True))
    if binary_sha != runtime["binary_sha256"]:
        raise ValueError("actual model runtime binary differs")
    revision = "gguf:" + MODEL_SHA + ";llama:" + RUNTIME_COMMIT + ";bin:" + binary_sha
    if manifest["revision"] != revision:
        raise ValueError("actual provider revision differs")
    unit = read_regular("/etc/systemd/system/merlin-model-provider.service", 16384, root_owned=True)
    if sha(unit) != manifest["service"]["unit_sha256"]:
        raise ValueError("provider unit identity differs")
    observed = service("merlin-model-provider.service")
    if (observed.get("ActiveState") != "active" or observed.get("SubState") != "running"
            or observed.get("MainPID") != str(manifest["service"]["main_pid"])
            or observed.get("MemoryMax") != "3221225472" or observed.get("MemorySwapMax") != "0"):
        raise ValueError("provider service no longer matches actual bootstrap")
    return manifest_raw, bootstrap_raw, manifest, observed


def unzip_source(raw):
    if sha(raw) != PINS["source_package_sha256"]:
        raise ValueError("accepted source package differs")
    files = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if len(archive.infolist()) != PINS["source_file_count"] + 1:
            raise ValueError("source membership count differs")
        total = 0
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            mode = item.external_attr >> 16
            if (item.filename in files or path.is_absolute() or ".." in path.parts
                    or "\\" in item.filename or item.is_dir() or stat.S_ISLNK(mode)
                    or item.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}):
                raise ValueError("invalid source archive entry")
            total += item.file_size
            if item.file_size > 4 * 1024 * 1024 or total > 4 * 1024 * 1024:
                raise ValueError("source expansion ceiling")
            files[item.filename] = archive.read(item)
    manifest = json.loads(files.pop("manifest.json"), object_pairs_hook=unique)
    actual = {name: sha(body) for name, body in sorted(files.items())}
    if (actual != manifest["files"] or sha(canonical(actual)) != PINS["source_map_sha256"]
            or manifest["source_commit"] != PINS["source_commit"]
            or set(files) != set(manifest["git_blobs"])):
        raise ValueError("accepted source manifest differs")
    for name, body in files.items():
        if hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() != manifest["git_blobs"][name]:
            raise ValueError("source Git blob differs")
    return files


def put_once(registry, path, raw, media_type="application/json"):
    history = registry.artifact_history(PROJECT, path)
    if history:
        if len(history) != 1:
            raise ValueError("immutable host record has multiple versions")
        ref = registry.artifact_ref(PROJECT, path, version=1)
        if registry.read_artifact_ref(ref, max_bytes=2 * 1024 * 1024)["content"] != raw:
            raise ValueError("immutable host record content differs")
        return ref
    registry.put_artifact(PROJECT, path, raw, media_type)
    return registry.artifact_ref(PROJECT, path, version=1)


def owned_registry(owner):
    """Keep each newly written CAS object readable even if a later stage fails."""
    from merlin.project_registry import MerlinRegistry
    class HostRegistry(MerlinRegistry):
        def put_artifact(self, project_id, logical_path, content, media_type="application/octet-stream", **kwargs):
            if project_id != PROJECT or not isinstance(content, bytes):
                raise ValueError("fixed project and immutable bytes required")
            digest = sha(content)
            path = self.blobs / digest[:2] / digest[2:]
            new_parent, new_file = not path.parent.exists(), not path.exists()
            try:
                return super().put_artifact(project_id, logical_path, content, media_type, **kwargs)
            finally:
                for target, created in ((path.parent, new_parent), (path, new_file)):
                    if created and target.exists():
                        item = target.lstat()
                        if stat.S_ISLNK(item.st_mode) or item.st_uid not in {0, owner.pw_uid}:
                            raise PermissionError("new CAS custody differs")
                        if target == path and sha(read_regular(path, 2 * 1024 * 1024)) != digest:
                            raise ValueError("new CAS object digest differs")
                        if item.st_uid == 0:
                            os.chown(target, owner.pw_uid, owner.pw_gid, follow_symlinks=False)
    return HostRegistry(STATE)


def inventory_rows(registry):
    rows = registry.inventory(PROJECT)["artifacts"]
    if len(rows) > 4096:
        raise ValueError("fixed registry inventory ceiling")
    return {row["logical_path"]: {key: row[key] for key in ("digest", "version", "size_bytes")}
            for row in rows}


def repair_new_objects(registry, before, owner):
    after = inventory_rows(registry)
    for name, old in before.items():
        if after.get(name) != old:
            raise ValueError("pre-existing canonical artifact changed")
    changed = []
    for name in sorted(set(after) - set(before)):
        if not (name.startswith("context/merlin/") or name.startswith("local-research/" + SESSION + "/")
                or name.startswith("local-solver/" + SESSION + "/")
                or name.startswith("dual-coder/" + SESSION + "/") or name == "handoffs/" + SESSION + ".json"):
            raise ValueError("unexpected canonical write scope")
        digest = after[name]["digest"]
        path = registry.blobs / digest[:2] / digest[2:]
        raw = read_regular(path, 2 * 1024 * 1024)
        if sha(raw) != digest:
            raise ValueError("new canonical bytes differ")
        # Change only the exact new CAS object and its canonical digest prefix.
        # Existing shared objects already readable by this owner need no chmod.
        old_digests = {row["digest"] for row in before.values()}
        old_prefixes = {value[:2] for value in old_digests}
        for target in (path.parent, path):
            item = target.lstat()
            if stat.S_ISLNK(item.st_mode):
                raise ValueError("new canonical path is a symlink")
            if item.st_uid == 0:
                if (target == path and digest in old_digests) or (target == path.parent and digest[:2] in old_prefixes):
                    raise PermissionError("pre-existing canonical ownership is outside repair scope")
                os.chown(target, owner.pw_uid, owner.pw_gid, follow_symlinks=False)
            elif item.st_uid != owner.pw_uid:
                raise PermissionError("unexpected new canonical ownership")
        changed.append(registry.artifact_ref(PROJECT, name))
    lock = registry.root / "dot-dual-coder.lock"
    if lock.exists() and lock.lstat().st_uid == 0:
        if not stat.S_ISREG(lock.lstat().st_mode):
            raise ValueError("workflow lock type differs")
        os.chown(lock, owner.pw_uid, owner.pw_gid, follow_symlinks=False)
    return {"new_refs": changed, "preexisting_artifacts_unchanged": True,
            "owner_uid": owner.pw_uid, "new_objects": len(changed)}


def private_status(source_root):
    """Actual Unix peer-authenticated status as the existing granted runner UID."""
    code = ("import sys,json;sys.path.insert(0,sys.argv[1]);"
            "from dot_ai_os.private_runtime import call_socket;"
            "r=call_socket('/run/merlin-dot-private/tools.sock',"
            "{'schema':'merlin-private-call/1','request_id':'research-status',"
            "'tool':'rsi_status','arguments':{'session_id':'" + SESSION + "'}},"
            "expected_server_uid=int(sys.argv[2]));print(json.dumps(r,sort_keys=True))")
    owner, caller = pwd.getpwnam("merlin-dot"), pwd.getpwnam("opc")
    result = subprocess.run(["/usr/sbin/runuser", "-u", "opc", "--", "/usr/bin/python3", "-I", "-B", "-S",
                             "-c", code, str(source_root / "python"), str(owner.pw_uid)],
                            env=ENV, cwd="/", capture_output=True, timeout=30)
    if result.returncode or len(result.stdout) > 65536:
        raise RuntimeError("actual private status probe failed")
    value = json.loads(result.stdout, object_pairs_hook=unique)
    if value.get("ok") is not True:
        raise RuntimeError("actual private status rejected: " + str(value.get("error")))
    return {"caller_uid": caller.pw_uid, "server_uid": owner.pw_uid,
            "transport": "SO_PEERCRED Unix socket", "result": value["result"],
            "result_sha256": sha(canonical(value["result"]))}


def phase_main(stage, phase):
    """Fresh root process, exact input capsule, existing typed runtime interfaces."""
    if os.geteuid() != 0 or phase not in {"coder_a", "complete", "replay"}:
        raise PermissionError("fixed privileged phase required")
    stage = Path(stage).resolve(strict=True)
    if not str(stage).startswith("/run/merlin-research-") or stage.stat().st_uid != 0:
        raise PermissionError("root-owned operation stage required")
    capsule_raw = read_regular(stage / "capsule.json", 65536, root_owned=True)
    capsule = json.loads(capsule_raw, object_pairs_hook=unique)
    if capsule["source_commit"] != PINS["source_commit"] or capsule["session_id"] != SESSION:
        raise ValueError("phase identity differs")
    source_root = stage / "source"
    if sha(read_regular(stage / "host.py", HOST_SOURCE_LIMIT, root_owned=True)) != capsule["host_source_sha256"]:
        raise ValueError("fresh process host source identity differs")
    sys.path.insert(0, str(source_root / "python"))
    from merlin.project_registry import MerlinRegistry
    from merlin.hermes_systemd import SystemdFixedPythonProcess
    from merlin.hermes_worker import TaskExecutionContext
    from merlin.telemetry import normalize_event
    from dot_ai_os.local_research import run_episode
    registry = owned_registry(pwd.getpwnam("merlin-dot"))
    def check():
        if time.time() >= capsule["deadline_epoch"] or read_regular(stage / "capsule.json", 65536, root_owned=True) != capsule_raw:
            raise InterruptedError("fixed episode lease expired or changed")
    def emit(kind, details):
        event = normalize_event({"source": "runtime", "kind": kind, "run_id": SESSION,
            "task_id": SESSION, "payload": {"phase": phase, **details}})
        path = HOST_PREFIX + "telemetry/" + phase + "-" + event["event_id"] + ".json"
        put_once(registry, path, canonical(event))
    context = TaskExecutionContext(task_id=SESSION, hypothesis_id="exact-rational-solver-alternatives",
        resource_budget={"cpu_cores": 2, "memory_bytes": 4 * 1024**3,
                         "max_wall_seconds": 3900, "compute_budget_units": 1},
        approval_ref=capsule["admission_ref"]["sha256"], lease_ref=capsule["lease_ref"],
        artifact_refs=tuple(capsule["admitted_refs"]), idempotency_key=SESSION,
        deadline_epoch=capsule["deadline_epoch"],
        emit_progress=lambda name, data=None: emit("task.progress", {"summary": name, "details": data}),
        emit_tool_event=lambda name, status, data: emit("agent.tool.completed", {"name": name, "status": status, "details": data}),
        heartbeat=check, check_cancelled=check)
    process = SystemdFixedPythonProcess(source_root / "python/dot_ai_os/fixed_solver_worker.py",
                                       PINS["worker_sha256"], tasks_max=8)
    def authorize(policy):
        check()
        return admitted_policy(policy, capsule, phase)
    started = time.monotonic()
    emit("task.started", {"new_process_pid": os.getpid(), "external_model_budget_usd": 0})
    result = run_episode(registry, project_id=PROJECT, session_id=SESSION,
        source_commit=PINS["source_commit"], context_refs=capsule["context_refs"],
        oracle_ref=capsule["oracle_ref"], provider_config=capsule["provider_config"],
        provider_evidence_refs=capsule["provider_evidence_refs"], process=process,
        execution_context=context, authorize=authorize, phase=phase)
    emit("task.completed", {"duration_seconds": time.monotonic() - started, "result_status": result.get("status")})
    out = {"schema": "merlin-research-host-phase/1", "phase": phase, "pid": os.getpid(),
           "elapsed_seconds": time.monotonic() - started, "result": result}
    (stage / (phase + ".json")).write_bytes(canonical(out))


def admitted_policy(policy, capsule, phase):
    if not isinstance(policy, dict):
        return False
    expected = {"schema": "merlin-local-research-authorization/1",
        "session_id": SESSION, "source_commit": PINS["source_commit"],
        "oracle_ref": capsule["oracle_ref"], "provider_evidence_refs": capsule["provider_evidence_refs"],
        "max_cost_usd": 0, "qualification": False, "promotion_authority": False}
    if (any(policy.get(key) != value for key, value in expected.items())
            or type(policy.get("max_cost_usd")) is not int
            or policy.get("qualification") is not False or policy.get("promotion_authority") is not False):
        return False
    action = policy.get("action")
    common = set(expected) | {"action"}
    if action == "admit_episode":
        return set(policy) == common | {"phase"} and policy["phase"] == phase
    from merlin.artifact_ref import ArtifactRef
    from dot_ai_os.private_runtime import PrivateReadOnlyRegistry
    def exact_ref(value, maximum):
        ref = ArtifactRef.from_mapping(value)
        if (ref.project_id != PROJECT or ref.version != 1
                or not ref.logical_path.startswith("local-solver/" + SESSION + "/")):
            return False
        reader = PrivateReadOnlyRegistry(STATE)
        reader.read_artifact_ref(ref.to_dict(), max_bytes=maximum)
        return True
    if action == "local_model_inference":
        if set(policy) != common | {"stage", "request_ref", "provider_revision", "max_output_tokens", "model_context_tokens"}:
            return False
        expected_stage = {"coder_a": "coder_a", "complete": "coder_b"}.get(phase)
        return (expected_stage is not None and policy["stage"] == expected_stage
            and policy["provider_revision"] == capsule["provider_config"]["revision"]
            and type(policy["max_output_tokens"]) is int and policy["max_output_tokens"] == 900
            and type(policy["model_context_tokens"]) is int and policy["model_context_tokens"] == 4096
            and exact_ref(policy["request_ref"], 32000))
    if action == "solver_worker":
        if (phase != "complete" or set(policy) != common | {"partition", "variant", "input_ref", "native_policy"}
                or policy["partition"] not in {"selection", "final"}
                or policy["variant"] not in {"baseline", "coder_a", "coder_b"}):
            return False
        native = policy["native_policy"]
        from merlin.hermes_process import ProcessLimits
        from merlin.hermes_systemd import _properties
        limits = ProcessLimits(memory_bytes=64 * 1024**2, cpu_seconds=2,
                               wall_seconds=5, cpu_cores=1, output_bytes=16 * 1024)
        if (not isinstance(native, dict) or set(native) != {"program_sha256", "unit", "limits", "tasks_max", "isolation", "compute_budget_units_enforced"}
                or native["program_sha256"] != PINS["worker_sha256"]
                or not isinstance(native["unit"], str) or not re.fullmatch(r"merlin-fixed-[0-9a-f]{32}\.service", native["unit"])
                or native["limits"] != _properties(limits, 8)
                or type(native["tasks_max"]) is not int or native["tasks_max"] != 8
                or native["isolation"] != "systemd_cgroup_v2" or native["compute_budget_units_enforced"] is not False):
            return False
        return exact_ref(policy["input_ref"], 128 * 1024)
    return False


def root_run(incoming, output):
    previous_umask = os.umask(0o022)
    try:
        return _root_run(incoming, output)
    finally:
        os.umask(previous_umask)


def _root_run(incoming, output):
    """One fixed operation; source and assets arrive through the pinned runner loader."""
    if os.geteuid() != 0 or socket.gethostname() != "cace-oci-a1":
        raise PermissionError("intended privileged host supervisor required")
    incoming, output = Path(incoming).resolve(strict=True), Path(output).resolve(strict=True)
    runner = pwd.getpwnam("opc")
    if incoming != output or incoming.stat().st_uid != runner.pw_uid:
        raise PermissionError("one runner-owned operation output directory required")
    native_raw = read_regular(incoming / "tested-source.zip", 4 * 1024 * 1024)
    files = unzip_source(native_raw)
    oracle_raw = read_regular(incoming / "oracle.json", 32000)
    notes_raw = read_regular(incoming / "source-notes.json", 32000)
    if sha(oracle_raw) != PINS["oracle_sha256"] or sha(notes_raw) != PINS["source_notes_sha256"]:
        raise ValueError("pre-model independent reference/source notes differ")
    invocation_raw = read_regular(incoming / "invocation.json", 4096)
    invocation = json.loads(invocation_raw, object_pairs_hook=unique)
    if (set(invocation) != {"request_id", "run_id", "run_attempt", "workflow_commit"}
            or not re.fullmatch(r"[0-9a-f-]{36}", invocation["request_id"])
            or type(invocation["run_id"]) is not int or invocation["run_attempt"] != 1
            or not re.fullmatch(r"[0-9a-f]{40}", invocation["workflow_commit"])):
        raise ValueError("fixed one-attempt operation identity required")
    manifest_raw, bootstrap_raw, provider, provider_live = require_provider()
    config_raw = read_regular(CONFIG, 16000, root_owned=True)
    if sha(config_raw) != "a25921442e2d3e463ccd685de6c67d824140b8c1592ab4fe942fb50c5d3b22e8":
        raise ValueError("existing project and access configuration changed")
    config = json.loads(config_raw, object_pairs_hook=unique)
    if (config["project_id"] != PROJECT or config["namespaces"] != ["merlin", "expert-robot"]
            or len(config["grants"]) != 1 or config["grants"][0]["uid"] != runner.pw_uid
            or config["grants"][0]["principal"] != "local-runner-opc"
            or "rsi_status" not in config["grants"][0]["tools"]):
        raise ValueError("canonical host binding differs")
    private_before = service("merlin-dot-private.service")
    if (private_before.get("ActiveState") != "active" or private_before.get("SubState") != "running"
            or private_before.get("PrivateNetwork") != "yes"
            or private_before.get("RestrictAddressFamilies") != "AF_UNIX"):
        raise ValueError("existing private service profile differs")
    owner = pwd.getpwnam("merlin-dot")
    if STATE.is_symlink() or STATE.stat().st_uid != owner.pw_uid:
        raise ValueError("existing canonical state ownership differs")
    db_path = STATE / "merlin.sqlite3"
    header = read_regular(db_path, 16 * 1024 * 1024)[:100]
    if header[:16] != b"SQLite format 3\x00" or header[18:20] != b"\x01\x01":
        raise ValueError("existing non-WAL registry required")
    backups = STATE.parent / "backups"
    backups.mkdir(mode=0o700, exist_ok=True)
    if backups.is_symlink() or backups.stat().st_uid != 0:
        raise ValueError("root-owned backup directory required")
    backup_path = backups / ("before-research-" + invocation["request_id"] + ".sqlite3")
    if backup_path.exists():
        raise ValueError("operation already has a preserved pre-write snapshot")
    began = time.monotonic()
    with sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True, timeout=2) as source:
        with sqlite3.connect(backup_path) as target:
            def backup_progress(status, remaining, total):
                if time.monotonic() - began > 10:
                    raise TimeoutError("bounded pre-write backup timed out")
            source.backup(target, pages=64, progress=backup_progress)
    backup_path.chmod(0o600)
    backup_sha = sha(read_regular(backup_path, 16 * 1024 * 1024, root_owned=True))
    (output / "intent.json").write_bytes(canonical({"schema": "merlin-real-research-intent/1",
        "session_id": SESSION, "invocation": invocation, "source_commit": PINS["source_commit"],
        "source_map_sha256": PINS["source_map_sha256"], "backup_sha256": backup_sha,
        "external_model_budget_usd": 0, "provider_manifest_sha256": sha(manifest_raw),
        "oracle_sha256": sha(oracle_raw), "no_automatic_retry_after_ambiguous_intent": True}))
    with tempfile.TemporaryDirectory(prefix="merlin-research-", dir="/run") as temporary:
        stage = Path(temporary)
        stage.chmod(0o755)
        source_root = stage / "source"
        for name, body in files.items():
            path = source_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            path.chmod(0o444)
        script = read_regular(incoming / "research_episode_host.py", HOST_SOURCE_LIMIT)
        if sha(script) != _HOST_SOURCE_SHA256:
            raise ValueError("privileged host controller bytes differ")
        (stage / "host.py").write_bytes(script)
        (stage / "host.py").chmod(0o444)
        sys.path.insert(0, str(source_root / "python"))
        from merlin.project_registry import MerlinRegistry
        from dot_ai_os.bridge import DotContextBridge
        from dot_ai_os.dual_coder import DualCoderWorkflow
        registry = owned_registry(owner)
        before = inventory_rows(registry)
        if any(name.startswith(prefix + SESSION + "/") for name in before
               for prefix in ("local-research/", "local-solver/", "dual-coder/")):
            raise ValueError("fixed episode already exists; inspect its status without repeating providers")
        bridge = DotContextBridge(registry, project_id=PROJECT, namespaces=config["namespaces"])
        notes = json.loads(notes_raw, object_pairs_hook=unique)
        baseline_source = files["python/dot_ai_os/simulation_research.py"].decode()
        function = next(node for node in ast.parse(baseline_source).body
                        if isinstance(node, ast.FunctionDef) and node.name == "_solve")
        baseline = ast.get_source_segment(baseline_source, function).encode()
        if sha(baseline) != "72ba14b8f8b98475c3c25f885bc2edd88e05bd1d36422ab6b5e3ee20c2799798":
            raise ValueError("original-task baseline differs")
        inputs = [("solver-baseline", "Merlin exact-rational solver baseline", baseline,
                   "https://github.com/Mannyspiro/expert-robot/blob/" + notes["baseline"]["commit"] + "/python/dot_ai_os/simulation_research.py")]
        for row in notes["sources"][:2]:
            content = (row["title"] + "\nSource: " + row["url"] + "\n" + row["notes"] + "\n").encode()
            inputs.append((row["source_id"], row["title"], content, row["url"]))
        context_refs = []
        for source_id, title, content, url in inputs:
            record = bridge.ingest(namespace="merlin", source_id=SESSION + ":" + source_id,
                title=title, content=content, source_url=url, source_version=sha(content),
                epistemic="source_snapshot" if source_id == "solver-baseline" else "research_proposal",
                captured_at="2026-11-21T13:56:49Z")
            context_refs.append(record["source_ref"])
        source_notes_ref = put_once(registry, HOST_PREFIX + "source-notes.json", notes_raw)
        oracle_ref = put_once(registry, HOST_PREFIX + "oracle.json", oracle_raw)
        manifest_ref = put_once(registry, HOST_PREFIX + "provider-manifest.json", manifest_raw)
        bootstrap_ref = put_once(registry, HOST_PREFIX + "provider-bootstrap.json", bootstrap_raw)
        admitted_refs = context_refs + [source_notes_ref, oracle_ref, manifest_ref, bootstrap_ref]
        admission = {"schema": "merlin-fixed-research-admission/1", "session_id": SESSION,
            "source_commit": PINS["source_commit"], "source_map_sha256": PINS["source_map_sha256"],
            "invocation": invocation, "artifact_refs": admitted_refs,
            "basis": "User explicitly authorized connecting the actual zero-cost providers, one real research task, native validation, restart/status and reviewed release.",
            "authority": "bounded_execution_only", "external_model_budget_usd": 0,
            "model_calls_max": 2, "model_output_tokens_per_call_max": 900,
            "model_client_wall_seconds_max": 1800, "episode_wall_seconds_max": 3900,
            "promotion_authority": False, "independent_attestation": False}
        admission_ref = put_once(registry, HOST_PREFIX + "admission.json", canonical(admission))
        admitted_refs.append(admission_ref)
        capsule = {"source_commit": PINS["source_commit"], "session_id": SESSION,
            "host_source_sha256": _HOST_SOURCE_SHA256,
            "context_refs": context_refs, "oracle_ref": oracle_ref,
            "provider_config": {key: provider[key] for key in ("endpoint", "model", "revision")},
            "provider_evidence_refs": {"manifest_ref": manifest_ref, "bootstrap_ref": bootstrap_ref},
            "admission_ref": admission_ref, "admitted_refs": admitted_refs,
            "deadline_epoch": time.time() + 3900, "lease_ref": sha(canonical(invocation))}
        capsule["provider_config"]["client_timeout_seconds"] = 1800
        (stage / "capsule.json").write_bytes(canonical(capsule))
        (stage / "capsule.json").chmod(0o600)
        ownership = [repair_new_objects(registry, before, owner)]
        phase_rows, socket_rows = {}, {}
        try:
            for phase, timeout in (("coder_a", 1840), ("complete", 1870), ("replay", 30)):
                existing = inventory_rows(registry)
                started = time.monotonic()
                try:
                    child = subprocess.run(["/usr/bin/python3", "-I", "-B", "-S", str(stage / "host.py"),
                                            "--phase", str(stage), phase],
                                           env=ENV, cwd="/", capture_output=True, timeout=timeout)
                    if len(child.stdout) + len(child.stderr) > 65536:
                        raise ValueError("phase diagnostics ceiling")
                    (output / (phase + "-process.txt")).write_bytes(child.stdout + child.stderr)
                    if child.returncode:
                        raise RuntimeError("fixed research phase failed: " + phase)
                    raw = read_regular(stage / (phase + ".json"), 256 * 1024, root_owned=True)
                    phase_rows[phase] = json.loads(raw, object_pairs_hook=unique)
                    (output / (phase + ".json")).write_bytes(raw)
                finally:
                    ownership.append(repair_new_objects(registry, existing, owner))
                socket_rows[phase] = private_status(source_root)
                (output / (phase + "-private-status.json")).write_bytes(canonical(socket_rows[phase]))
                if time.monotonic() - started > timeout + 5:
                    raise TimeoutError("phase exceeded supervisor deadline")
            validate_phase_outcomes(phase_rows, socket_rows)
            bridge.save_handoff(SESSION,
                summary="Actual local-model coder A and coder B research completed with separately constructed exact-rational reference checks. Preserve candidate failures and the original solver; consult the immutable workflow and final assessment references.",
                next_action="Review the recorded original-task result and deploy only the separately validated fixed runtime package.",
                source_refs=context_refs)
            handoff = bridge.load_handoff(SESSION)
            private_after = service("merlin-dot-private.service")
            if private_after != private_before or read_regular(CONFIG, 16000, root_owned=True) != config_raw:
                raise ValueError("task changed the existing service/configuration")
            provider_after = service("merlin-model-provider.service")
            if provider_after != provider_live:
                raise ValueError("provider service changed during the fixed task")
            after = inventory_rows(registry)
            telemetry_refs = [registry.artifact_ref(PROJECT, name) for name in sorted(after)
                              if name.startswith(HOST_PREFIX + "telemetry/")]
            receipt = {"schema": "merlin-real-research-host/1", "status": "succeeded",
                "source_commit": PINS["source_commit"], "source_map_sha256": PINS["source_map_sha256"],
                "native_validation": PINS["native_validation"], "project_id": PROJECT, "session_id": SESSION,
                "invocation": invocation, "phases": phase_rows,
                "source_refs": context_refs, "source_notes_ref": source_notes_ref, "oracle_ref": oracle_ref,
                "provider_manifest_ref": manifest_ref, "provider_bootstrap_ref": bootstrap_ref,
                "provider_revision": provider["revision"], "external_model_budget_usd": 0,
                "coders": "Two separate invocations of the same pinned model; no independent-model claim.",
                "private_status": socket_rows,
                "expected_private_status_sha256": socket_rows["replay"]["result_sha256"],
                "ownership": ownership, "preexisting_artifacts_unchanged": True,
                "prewrite_backup_sha256": backup_sha, "handoff": handoff,
                "telemetry_refs": telemetry_refs,
                "telemetry_scope": "Typed runtime events retained as canonical artifacts; no separate telemetry consumer is asserted.",
                "private_service_before": private_before, "private_service_after": private_after,
                "provider_service": provider_after,
                "qualification": False, "promotion_authority": False}
            receipt_raw = canonical(receipt)
            receipt_ref = put_once(registry, HOST_PREFIX + "receipt.json", receipt_raw)
            (output / "host-receipt.json").write_bytes(receipt_raw)
            (output / "host-receipt-ref.json").write_bytes(canonical(receipt_ref))
            (output / "reference-oracle.json").write_bytes(oracle_raw)
            (output / "source-notes.json").write_bytes(notes_raw)
            (output / "provider-manifest.json").write_bytes(manifest_raw)
            (output / "provider-bootstrap.json").write_bytes(bootstrap_raw)
        finally:
            repair_new_objects(registry, before, owner)
            export_episode(registry, before, output)


def validate_phase_outcomes(phases, statuses):
    if set(phases) != {"coder_a", "complete", "replay"} or set(statuses) != set(phases):
        raise ValueError("all three actual phases required")
    if len({row["pid"] for row in phases.values()}) != 3:
        raise ValueError("restart must use separate observed processes")
    effects = {phase: row["result"]["effects_this_call"] for phase, row in phases.items()}
    for phase, calls in (("coder_a", 1), ("complete", 1), ("replay", 0)):
        if (effects[phase].get("inference_attempts") != calls
                or effects[phase].get("inference_responses") != calls):
            raise ValueError("actual provider call/replay count differs")
    if effects["coder_a"].get("native_process_launches") != 0 or effects["replay"].get("native_process_launches") != 0:
        raise ValueError("unexpected candidate execution in paused/replay phase")
    if effects["complete"].get("native_process_launches") != 6:
        raise ValueError("both selection/final must evaluate all three implementations")
    first, complete, replay = (statuses[name]["result"] for name in ("coder_a", "complete", "replay"))
    if (first.get("status") != "incomplete" or first.get("next_stage") != "coder_b"
            or first.get("stages") != {"coder_a": "completed", "coder_b": "not_started", "evaluator": "not_started"}):
        raise ValueError("actual saved pause after coder A differs")
    if complete.get("status") != "completed_research_only" or complete != replay:
        raise ValueError("actual completed private status did not restore identically")
    for field in ("report_ref", "selection_ref", "final_ref", "provider_observation_refs", "process_receipt_refs"):
        if not phases["complete"]["result"].get(field) or phases["complete"]["result"][field] != phases["replay"]["result"].get(field):
            raise ValueError("completed exact artifact references changed during replay")


def export_episode(registry, before, output):
    rows = inventory_rows(registry)
    total, exported = 0, {}
    for name in sorted(set(rows) - set(before)):
        if not any(name.startswith(prefix + SESSION + "/")
                   for prefix in ("local-research/", "local-solver/", "dual-coder/")):
            continue
        ref = registry.artifact_ref(PROJECT, name)
        raw = registry.read_artifact_ref(ref, max_bytes=2 * 1024 * 1024)["content"]
        total += len(raw)
        if total > 4 * 1024 * 1024 or len(exported) >= 256:
            raise ValueError("exact episode export ceiling")
        exported[name] = {"ref": ref, "content": raw.decode("utf-8")}
    (output / "episode-artifacts.json").write_bytes(canonical({"schema": "merlin-exact-episode-export/1",
        "project_id": PROJECT, "session_id": SESSION, "artifacts": exported}))


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "--phase":
        raise SystemExit("fixed phase supervisor invocation required")
    phase_main(sys.argv[2], sys.argv[3])

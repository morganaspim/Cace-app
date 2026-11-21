"""Fixed, read-only metadata for the Merlin OCI context inventory.

No environment files, process environments, private databases or model contents
are read. A model-list GET requires a current known process/listener association.
This module cannot start a runtime or issue inference. Presence is not qualification.
"""
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess


SAFE_PATH = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/bin"
SAFE_ENV = {"PATH": SAFE_PATH, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
CONFIG = Path("/etc/merlin-dot-private/config.json")
SOCKET = Path("/run/merlin-dot-private/tools.sock")
MODEL_RELATIVE = "models/hermes_coder/NousResearch_NousCoder-14B-Q4_K_M.gguf"
MODEL_PATHS = tuple(Path(root) / MODEL_RELATIVE for root in (
    "/opt/merlin-dot-private/current", "/opt/merlin-dot/source"))
PROC = Path("/proc")
RUNTIMES = {"llama-server": (8080, "/v1/models", "openai"),
            "ollama": (11434, "/api/tags", "ollama")}
KNOWN_TOOLS = frozenset({"health", "context_status", "context_search", "context_fetch",
    "session_handoff", "rsi_status", "virtual_circuit_demo", "research_contract",
    "research_episode_demo", "mathematical_lenses_demo", "job_submit", "job_status"})
MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,127}\Z")
MODEL_CREDENTIAL = re.compile(r"(?:^|[./:@+_\-])(?:sk[-_]|hf_|bearer)", re.IGNORECASE)


def _small(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("regular metadata file required")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("metadata ceiling")
        return raw
    finally:
        os.close(fd)


def _metadata(path):
    try:
        item = path.lstat()
        kind = ("file" if stat.S_ISREG(item.st_mode) else
                "socket" if stat.S_ISSOCK(item.st_mode) else
                "symlink" if stat.S_ISLNK(item.st_mode) else
                "directory" if stat.S_ISDIR(item.st_mode) else "other")
        return {"path": str(path), "present": True, "kind": kind,
                "size_bytes": item.st_size, "uid": item.st_uid, "gid": item.st_gid,
                "mode": oct(stat.S_IMODE(item.st_mode))}
    except OSError as exc:
        return {"path": str(path), "present": False if isinstance(exc, FileNotFoundError) else None,
                "error_class": type(exc).__name__}


def _config():
    result = {"path": str(CONFIG), "provider_environment_read": False}
    try:
        raw = _small(CONFIG, 16384)
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get("schema") != "merlin-private-host/1":
            raise ValueError("unsupported private configuration")
        grants, namespaces = value.get("grants"), value.get("namespaces")
        if not isinstance(grants, list) or len(grants) > 64 or not isinstance(namespaces, list) or len(namespaces) > 64:
            raise ValueError("invalid configuration shape")
        tools = set()
        unknown = 0
        for grant in grants:
            if not isinstance(grant, dict) or not isinstance(grant.get("tools"), list) or len(grant["tools"]) > 64:
                raise ValueError("invalid grant shape")
            for tool in grant["tools"]:
                if not isinstance(tool, str):
                    raise ValueError("invalid tool name")
                if tool in KNOWN_TOOLS:
                    tools.add(tool)
                else:
                    unknown += 1
        result.update(status="observed", schema="merlin-private-host/1",
            sha256=hashlib.sha256(raw).hexdigest(), grant_count=len(grants),
            namespace_count=len(namespaces), recognized_tools=sorted(tools),
            unrecognized_tool_entries=unknown,
            provider_configuration="not_defined_by_this_schema")
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        result.update(status="unavailable", error_class=type(exc).__name__)
    return result


def _processes():
    result = subprocess.run(["/usr/bin/ps", "-C", "llama-server,ollama", "-o", "pid=,comm="],
        cwd="/", env=SAFE_ENV, capture_output=True, text=True, timeout=3)
    if result.returncode not in (0, 1) or len(result.stdout) > 4096:
        raise ValueError("runtime process observation unavailable")
    rows = []
    for line in result.stdout.splitlines():
        match = re.fullmatch(r"\s*([1-9][0-9]{0,9})\s+(llama-server|ollama)\s*", line)
        if not match:
            raise ValueError("invalid runtime process observation")
        rows.append((int(match[1]), match[2]))
    if len(rows) > 8 or len(set(rows)) != len(rows):
        raise ValueError("runtime process ceiling or ambiguity")
    return sorted(rows)


def _process_identity(pid, name):
    directory = PROC / str(pid)
    if _small(directory / "comm", 64).decode("ascii").strip() != name:
        raise ValueError("runtime process changed")
    raw = _small(directory / "stat", 4096).decode("ascii")
    end = raw.rfind(")")
    fields = raw[end + 2:].split()
    if not raw.startswith(str(pid) + " (") or end < 0 or len(fields) < 20 or not fields[19].isdigit():
        raise ValueError("runtime identity unavailable")
    return int(fields[19])


def _network_namespace(pid):
    current = os.readlink(PROC / "self/ns/net")
    observed = os.readlink(PROC / str(pid) / "ns/net")
    if not re.fullmatch(r"net:\[[1-9][0-9]*\]", current) or observed != current:
        raise ValueError("runtime is not in the collector network namespace")
    return current


def _listener_links(pid, name):
    """Match only the documented model port to sockets owned by this process."""
    identity = (_process_identity(pid, name), _network_namespace(pid))
    fds = []
    with os.scandir(PROC / str(pid) / "fd") as children:
        for child in children:
            if len(fds) >= 256:
                raise ValueError("runtime descriptor ceiling")
            fds.append(child.path)
    inodes = set()
    for child in fds:
        try:
            match = re.fullmatch(r"socket:\[([0-9]+)\]", os.readlink(child))
        except FileNotFoundError:
            continue
        if match:
            inodes.add(match[1])
    links = set()
    port = RUNTIMES[name][0]
    for filename, family in (("tcp", 4), ("tcp6", 6)):
        try:
            raw = _small(PROC / str(pid) / "net" / filename, 65536)
        except FileNotFoundError:
            continue
        for line in raw.decode("ascii").splitlines()[1:]:
            fields = line.split()
            if len(fields) < 10 or fields[3] != "0A" or fields[9] not in inodes:
                continue
            address, sep, number = fields[1].partition(":")
            if not sep or int(number, 16) != port:
                continue
            data = bytes.fromhex(address)
            if family == 4 and len(data) == 4:
                host = str(ipaddress.IPv4Address(data[::-1]))
            elif family == 6 and len(data) == 16:
                host = str(ipaddress.IPv6Address(b"".join(data[i:i + 4][::-1] for i in range(0, 16, 4))))
            else:
                raise ValueError("invalid local listener observation")
            if host in ("127.0.0.1", "::1"):
                links.add((host, port))
    if (_process_identity(pid, name), _network_namespace(pid)) != identity:
        raise ValueError("runtime identity changed")
    return identity, links


def _model_list(name, host, port):
    expected_port, target, contract = RUNTIMES[name]
    if host not in ("127.0.0.1", "::1") or port != expected_port:
        raise ValueError("fixed model endpoint required")
    connection = http.client.HTTPConnection(host, port, timeout=2)
    try:
        connection.request("GET", target, headers={"Accept": "application/json"})
        response = connection.getresponse()
        try:
            if response.status != 200:
                return {"status": "http_rejected", "http_status": response.status}
            raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError("model response ceiling")
            value = json.loads(raw)
        finally:
            response.close()
    finally:
        connection.close()
    if not isinstance(value, dict):
        raise ValueError("invalid model list")
    items = value.get("data" if contract == "openai" else "models")
    if not isinstance(items, list) or len(items) > 256:
        raise ValueError("invalid model list")
    models = []
    for item in items[:16]:
        key = "id" if contract == "openai" else "name"
        model = item.get(key) if isinstance(item, dict) else None
        if (not isinstance(model, str) or not MODEL_NAME.fullmatch(model)
                or MODEL_CREDENTIAL.search(model)):
            raise ValueError("invalid model identifier")
        models.append(model)
    return {"status": "observed", "model_names": models, "reported_count": len(models),
            "total_count": len(items), "truncated": len(items) > 16,
            "scope": "runtime-reported list; loaded weights and Merlin provider binding are not verified"}


def collect():
    report = {"schema": "merlin-provider-presence/1", "private_config": _config(),
        "private_socket": _metadata(SOCKET),
        "documented_model_files": [_metadata(path) for path in MODEL_PATHS],
        "model_file_contents_read": False, "credential_sources_inspected": False,
        "credential_values_returned": False,
        "process_environment_read": False, "private_state_accessed": False,
        "host_configuration_changed": False, "inference_requests": 0,
        "external_model_requests": 0, "model_list_requests": 0,
        "qualification": False, "promotion_authority": False,
        "runtime_executables": {name: shutil.which(name, path=SAFE_PATH) for name in RUNTIMES},
        "runtimes": [], "observation_atomic": False}
    try:
        processes = _processes()
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        report["process_observation"] = {"status": "unavailable", "error_class": type(exc).__name__}
        return report
    report["process_observation"] = {"status": "observed", "count": len(processes)}
    for name in RUNTIMES:
        rows, associations = [], []
        for pid, observed in processes:
            if observed != name:
                continue
            row = {"pid": pid}
            try:
                identity, links = _listener_links(pid, name)
                row.update(status="observed", documented_loopback_listener=bool(links))
                for host, port in links:
                    associations.append((pid, identity, host, port))
            except (OSError, ValueError, UnicodeError) as exc:
                row.update(status="unavailable", error_class=type(exc).__name__)
            rows.append(row)
        runtime = {"name": name, "processes": rows, "model_list": {"status": "not_queried"},
                   "linked_to_merlin_configuration": False}
        # Multiple processes sharing the port are ambiguous; do not guess an owner.
        if len({row[0] for row in associations}) == 1:
            pid, identity, host, port = sorted(associations, key=lambda row: row[2] != "127.0.0.1")[0]
            try:
                current, links = _listener_links(pid, name)
                if current != identity or (host, port) not in links:
                    raise ValueError("runtime listener changed before query")
                report["model_list_requests"] += 1
                result = _model_list(name, host, port)
                current, links = _listener_links(pid, name)
                if current != identity or (host, port) not in links:
                    raise ValueError("runtime listener changed after query")
                runtime["model_list"] = {**result, "host": host, "port": port}
            except (OSError, ValueError, TypeError, UnicodeError, http.client.HTTPException) as exc:
                runtime["model_list"] = {"status": "unavailable", "error_class": type(exc).__name__}
        elif associations:
            runtime["model_list"] = {"status": "ambiguous_runtime_ownership"}
        report["runtimes"].append(runtime)
    if len(json.dumps(report).encode()) > 32768:
        raise ValueError("presence report ceiling")
    return report

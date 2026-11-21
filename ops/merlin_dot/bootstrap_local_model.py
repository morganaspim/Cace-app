"""Fixed cace-oci-a1 local provider bootstrap; never a command/URL gateway.

This establishes a bounded operational coding smoke, not model qualification.
Only the pinned workflow invokes run(), as root, after authenticating these bytes.
An unfinished durable intent is deliberately not retried automatically.
"""
import ast
from contextlib import contextmanager
import hashlib
import grp
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import platform
import pwd
import re
import selectors
import shutil
import signal
import socket
import stat
import subprocess
import tarfile
import time
from urllib.parse import urljoin, urlsplit
import uuid


SOURCE_COMMIT = "2a4daf0e08d6a9b6993ee0d4a9a3cfc35a6f405c"
SOURCE_TREE = "445f2b6c9555e93c2e2c526d68497d8f47d97a1d"
SOURCE_SHA = "fd484b0ba95d74e0cd76ff7793f220fa3bb64bf85c9638962783d1085ee8bd28"
SOURCE_BYTES = 38930336
SOURCE_URL = "https://codeload.github.com/ggml-org/llama.cpp/legacy.tar.gz/" + SOURCE_COMMIT
SOURCE_PREFIX = "ggml-org-llama.cpp-2a4daf0"
MODEL_REPO = "Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF"
MODEL_REVISION = "f86cb2c1fa58255f8052cc32aeede1b7482d4361"
MODEL_FILENAME = "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
MODEL_SHA = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
MODEL_BYTES = 1117320768
MODEL_URL = "https://huggingface.co/" + MODEL_REPO + "/resolve/" + MODEL_REVISION + "/" + MODEL_FILENAME
MODEL_ALIAS = "merlin-qwen-coder-1.5b-q4"
ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
UNIT = "merlin-model-provider.service"
USER = "merlin-model"
UNIT_PATH = Path("/etc/systemd/system") / UNIT
CONFIG = Path("/etc/merlin-model-provider")
MANIFEST = CONFIG / "manifest.json"
BOOTSTRAP_RECEIPT = CONFIG / "bootstrap-receipt.json"
INSTALL = Path("/opt/merlin-model-provider/releases")
STATE = Path("/var/lib/merlin-model-bootstrap")
INTENT = STATE / "bootstrap-intent.json"
CMAKE = "/home/opc/.local/bin/cmake"
CLEAN_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
LIMITS = {"context_tokens": 4096, "parallel": 1, "threads": 2,
          "memory_max_bytes": 3221225472, "memory_swap_max_bytes": 0,
          "cpu_quota_percent": 150, "tasks_max": 32}
BUILD_FLAGS = ["-DCMAKE_BUILD_TYPE=Release", "-DBUILD_SHARED_LIBS=OFF", "-DGGML_BACKEND_DL=OFF",
               "-DGGML_NATIVE=OFF", "-DGGML_CPU_ALL_VARIANTS=OFF",
               "-DGGML_CPU_KLEIDIAI=OFF", "-DGGML_OPENMP=OFF",
               "-DLLAMA_OPENSSL=OFF", "-DLLAMA_SUBPROCESS=OFF",
               "-DLLAMA_BUILD_TESTS=OFF", "-DLLAMA_BUILD_EXAMPLES=OFF",
               "-DLLAMA_BUILD_UI=OFF", "-DLLAMA_USE_PREBUILT_UI=OFF",
               "-DLLAMA_BUILD_APP=OFF", "-DLLAMA_BUILD_TOOLS=ON",
               "-DLLAMA_BUILD_SERVER=ON"]
DOWNLOAD_HOSTS = {"codeload.github.com", "huggingface.co", "cdn-lfs.huggingface.co",
                  "cdn-lfs-us-1.hf.co", "cdn-lfs-eu-1.hf.co", "cas-bridge.xethub.hf.co",
                  "us.aws.cdn.hf.co", "eu.aws.cdn.hf.co"}
SMOKE_REQUEST = {"model": MODEL_ALIAS, "temperature": 0, "stream": False, "max_tokens": 384,
                 "messages": [
                     {"role": "system", "content": "Write correct concise Python. Return only the requested function, without explanations."},
                     {"role": "user", "content": "Write def clamp(value, low, high): for finite numeric values with low <= high. Return low if value is below low, high if value is above high, otherwise value. Use only if/return, comparisons, or min/max. No imports, decorators, annotations, assignments, loops, classes or helper functions."}]}
SMOKE_CASES = [(-2, 0, 5, 0), (0, 0, 5, 0), (3, 0, 5, 3), (5, 0, 5, 5), (9, 0, 5, 5),
               (-9, -5, -1, -5), (-3, -5, -1, -3), (2, -5, -1, -1),
               (0, 2, 2, 2), (4, 2, 2, 2), (0.25, -0.5, 0.5, 0.25), (0.75, -0.5, 0.5, 0.5)]


class BootstrapError(RuntimeError):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise BootstrapError("duplicate JSON field")
        result[key] = value
    return result


def decode(raw, limit):
    if len(raw) > limit:
        raise BootstrapError("JSON byte limit")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(BootstrapError("nonfinite JSON")))


def read_regular(path, limit):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise BootstrapError("invalid bounded regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(fd)
        if len(raw) > limit or (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise BootstrapError("file changed during read")
        return raw
    finally:
        os.close(fd)


def file_identity(path, maximum):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise BootstrapError("invalid identity file")
        h = hashlib.sha256()
        total = 0
        while True:
            raw = os.read(fd, 1024 * 1024)
            if not raw:
                break
            total += len(raw)
            if total > maximum:
                raise BootstrapError("identity size limit")
            h.update(raw)
        after = os.fstat(fd)
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise BootstrapError("identity changed during read")
        return {"sha256": h.hexdigest(), "size_bytes": total}
    finally:
        os.close(fd)


def write_new(path, raw, mode=0o644):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    parent = os.open(str(Path(path).parent), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def rooted_directory(path):
    """Create only fixed/derived descendants; reject writable or symbolic ancestors."""
    for part in reversed([Path(path)] + list(Path(path).parents)):
        if not part.exists():
            part.mkdir(mode=0o755)
        info = part.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise BootstrapError("unsafe root-owned directory")


def validate_request(request, identity):
    if not isinstance(request, dict) or set(request) != {"schema", "request_id", "operation", "created_at"}:
        raise BootstrapError("request fields")
    if request["schema"] != "merlin-model-bootstrap-request/1" or request["operation"] not in {"bootstrap", "inspect"}:
        raise BootstrapError("request operation")
    if not isinstance(request["request_id"], str) or str(uuid.UUID(request["request_id"])) != request["request_id"]:
        raise BootstrapError("request ID")
    if not isinstance(request["created_at"], str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", request["created_at"]):
        raise BootstrapError("request time")
    if set(identity) != {"run_id", "run_attempt", "workflow_commit", "controller_sha256", "runner"} or identity["runner"] != "cace-oci-a1":
        raise BootstrapError("execution identity")
    if type(identity["run_id"]) is not int or identity["run_id"] <= 0 or type(identity["run_attempt"]) is not int or identity["run_attempt"] != 1:
        raise BootstrapError("first attempt required")
    if not re.fullmatch(r"[0-9a-f]{40}", identity["workflow_commit"]) or not re.fullmatch(r"[0-9a-f]{64}", identity["controller_sha256"]):
        raise BootstrapError("source identity")


def command(argv, timeout=20, limit=65536, log_path=None, stop_unit=None, monitored_files=(), allowed_codes=(0,)):
    """Wall-bounded fixed argv, clean environment, bounded combined output."""
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, env=CLEAN_ENV, cwd="/", start_new_session=True)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    output = bytearray()
    deadline = time.monotonic() + timeout
    failed = False
    try:
        while selector.get_map():
            if any(path.stat().st_size > ceiling for path, ceiling in monitored_files):
                raise BootstrapError("manager-opened log output limit")
            left = deadline - time.monotonic()
            if left <= 0:
                raise BootstrapError("command deadline")
            for key, _ in selector.select(min(0.25, left)):
                raw = os.read(key.fd, 65536)
                if not raw:
                    selector.unregister(key.fileobj)
                    continue
                if len(output) + len(raw) > limit:
                    raise BootstrapError("command output limit")
                output.extend(raw)
        result = process.wait(timeout=max(0.01, deadline - time.monotonic()))
        if result not in allowed_codes:
            raise BootstrapError("fixed command failed with exit " + str(result))
        return bytes(output)
    except BaseException:
        failed = True
        raise
    finally:
        selector.close()
        if failed:
            if stop_unit:
                subprocess.run(["/usr/bin/systemctl", "stop", stop_unit], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=CLEAN_ENV, timeout=25, check=False)
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        process.stdout.close()
        if log_path is not None:
            write_new(log_path, bytes(output))


def service(unit=UNIT):
    names = ["LoadState", "ActiveState", "SubState", "MainPID", "UnitFileState", "User", "Group",
             "MemoryMax", "MemorySwapMax", "CPUQuotaPerSecUSec", "TasksMax", "PrivateNetwork",
             "RestrictAddressFamilies", "FragmentPath", "Result", "ExecMainStatus"]
    raw = command(["/usr/bin/systemctl", "show", unit, "--no-pager"] + ["--property=" + n for n in names], allowed_codes=(0, 1, 4))
    values = dict(line.split("=", 1) for line in raw.decode().splitlines() if "=" in line)
    if values.get("LoadState") not in ("loaded", "not-found", "masked", "error", "bad-setting", "stub", "merged"):
        raise BootstrapError("systemd observation unavailable")
    return {name: values.get(name, "") for name in names}


def private_observation():
    values = service("merlin-dot-private.service")
    config = Path("/etc/merlin-dot-private/config.json")
    return {"service": values, "config_sha256": file_identity(config, 65536)["sha256"] if config.exists() else None,
            "current": os.readlink("/opt/merlin-dot-private/current")}


def preflight():
    if os.geteuid() != 0 or platform.system() != "Linux" or platform.machine() != "aarch64":
        raise BootstrapError("fixed native root host required")
    release = dict(line.split("=", 1) for line in read_regular("/usr/lib/os-release", 8192).decode().splitlines() if "=" in line)
    if release.get("ID", "").strip('"') != "ol" or not release.get("VERSION_ID", "").strip('"').startswith("9."):
        raise BootstrapError("observed Oracle Linux9 ABI required")
    if (os.cpu_count() or 0) < 2:
        raise BootstrapError("two CPUs required")
    memory = dict(re.findall(r"^(\w+):\s+(\d+) kB$", Path("/proc/meminfo").read_text(), re.M))
    available = int(memory["MemAvailable"]) * 1024
    free = shutil.disk_usage("/opt").free
    if available < 6 * 1024**3 or free < 8 * 1024**3:
        raise BootstrapError("insufficient fixed build/model headroom")
    for executable in (CMAKE, "/usr/bin/g++", "/usr/bin/gcc", "/usr/bin/readelf", "/usr/bin/systemd-run", "/usr/sbin/runuser"):
        if not os.access(executable, os.X_OK):
            raise BootstrapError("required observed tool unavailable")
    before = service()
    if before["LoadState"] != "not-found" or os.path.lexists(UNIT_PATH) or CONFIG.exists() or INSTALL.parent.exists():
        raise BootstrapError("provider previous state is not absent")
    try:
        pwd.getpwnam(USER)
    except KeyError:
        pass
    else:
        raise BootstrapError("provider user already exists")
    try:
        grp.getgrnam(USER)
    except KeyError:
        pass
    else:
        raise BootstrapError("provider group already exists")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 8080))
    return {"provider": before, "private": private_observation(), "available_memory_bytes": available,
            "free_disk_bytes": free, "architecture": platform.machine(), "os": "Oracle Linux9"}


@contextmanager
def wall_deadline(seconds):
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise BootstrapError("unexpected existing deadline")
    def expired(signum, frame):
        raise BootstrapError("download wall deadline")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def download(url, path, expected_bytes, expected_sha, seconds):
    with wall_deadline(seconds):
        return _download(url, path, expected_bytes, expected_sha, seconds)


def _download(url, path, expected_bytes, expected_sha, seconds):
    """Public fixed source/model bytes only; no proxies, cookies or credentials."""
    deadline = time.monotonic() + seconds
    destination = url
    for redirects in range(5):
        parsed = urlsplit(destination)
        if parsed.scheme != "https" or parsed.hostname not in DOWNLOAD_HOSTS or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None, 443):
            raise BootstrapError("download redirect rejected")
        connection = http.client.HTTPSConnection(parsed.hostname, 443, timeout=max(0.1, min(30, deadline - time.monotonic())))
        response = None
        try:
            connection.request("GET", parsed.path + (("?" + parsed.query) if parsed.query else ""), headers={"User-Agent": "merlin-fixed-model-bootstrap/1", "Accept-Encoding": "identity"})
            transport = connection.sock
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                destination = urljoin(destination, response.getheader("Location", ""))
                continue
            if response.status != 200 or response.getheader("Content-Encoding", "identity") != "identity":
                raise BootstrapError("download response rejected")
            declared = response.getheader("Content-Length")
            if declared is not None and (not declared.isdigit() or int(declared) != expected_bytes):
                raise BootstrapError("download declared size mismatch")
            h, count = hashlib.sha256(), 0
            with open(path, "xb") as stream:
                while True:
                    left = deadline - time.monotonic()
                    if left <= 0:
                        raise BootstrapError("download deadline")
                    transport.settimeout(min(30, left))
                    raw = response.read1(min(1024 * 1024, expected_bytes - count + 1))
                    if not raw:
                        break
                    count += len(raw)
                    if count > expected_bytes:
                        raise BootstrapError("download size limit")
                    h.update(raw)
                    stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if count != expected_bytes or h.hexdigest() != expected_sha:
                raise BootstrapError("download identity mismatch")
            return {"sha256": h.hexdigest(), "size_bytes": count, "https_host": parsed.hostname, "redirects": redirects}
        finally:
            if response is not None:
                response.close()
            connection.close()
    raise BootstrapError("download redirect limit")


def extract_members(archive, target):
    seen, total, files = set(), 0, 0
    for index, member in enumerate(archive):
        if index >= 5000:
            raise BootstrapError("archive member limit")
        parts = PurePosixPath(member.name).parts
        if not parts or parts[0] != SOURCE_PREFIX or any(p in ("", ".", "..") for p in parts) or member.name.startswith("/"):
            raise BootstrapError("archive path")
        relative = "/".join(parts[1:])
        if not relative:
            if not member.isdir():
                raise BootstrapError("archive root")
            continue
        if relative in seen or (not member.isdir() and not member.isfile()) or member.issym() or member.islnk() or member.sparse:
            raise BootstrapError("archive entry type or duplicate")
        seen.add(relative)
        destination = target.joinpath(*parts[1:])
        if member.isdir():
            destination.mkdir(mode=0o755, parents=True, exist_ok=True)
            continue
        if member.mode not in (0o644, 0o755) or member.size < 0:
            raise BootstrapError("archive mode or size")
        total += member.size
        if total > 256 * 1024**2:
            raise BootstrapError("archive expansion limit")
        destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        with archive.extractfile(member) as source:
            raw = source.read(member.size + 1)
        if len(raw) != member.size:
            raise BootstrapError("archive member length")
        write_new(destination, raw, member.mode)
        files += 1
    return {"files": files, "uncompressed_bytes": total}


BUILD_SCRIPT = r'''
import json,os,pathlib,re,subprocess,sys
source,build,cmake=sys.argv[1:4];flags=json.loads(sys.argv[4])
group=pathlib.Path('/sys/fs/cgroup')/pathlib.Path(pathlib.Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/'))
policy={n:(group/n).read_text().strip() for n in ['memory.max','memory.swap.max','pids.max','cpu.max']}
assert policy['memory.max']=='4294967296' and policy['memory.swap.max']=='0' and policy['pids.max']=='32'
q,p=map(int,policy['cpu.max'].split());assert q*2==p*3
pathlib.Path(build,'build-policy.json').write_text(json.dumps(policy))
env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','CC':'/usr/bin/gcc','CXX':'/usr/bin/g++','CMAKE_BUILD_PARALLEL_LEVEL':'2'}
subprocess.run([cmake,'--version'],check=True,env=env)
subprocess.run(['/usr/bin/g++','--version'],check=True,env=env)
subprocess.run([cmake,'-S',source,'-B',build]+flags,check=True,env=env)
cache=pathlib.Path(build,'CMakeCache.txt').read_text()
for key in ['BUILD_SHARED_LIBS','GGML_BACKEND_DL','GGML_CPU_ALL_VARIANTS','GGML_CPU_KLEIDIAI','GGML_OPENMP','LLAMA_OPENSSL','LLAMA_SUBPROCESS','LLAMA_BUILD_UI','LLAMA_USE_PREBUILT_UI']:
 assert re.search(r'^'+key+r':BOOL=OFF$',cache,re.M),key
subprocess.run([cmake,'--build',build,'--target','llama-server','--parallel','2'],check=True,env=env)
binary=str(pathlib.Path(build,'bin','llama-server'))
elf=subprocess.run(['/usr/bin/readelf','-d',binary],check=True,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10).stdout
assert len(elf)<=65536
needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',elf.decode())
allowed={'libstdc++.so.6','libm.so.6','libgcc_s.so.1','libc.so.6','libpthread.so.0','libdl.so.2','librt.so.1','ld-linux-aarch64.so.1'}
assert set(needed)<=allowed,needed
pathlib.Path(build,'runtime-linkage.json').write_text(json.dumps({'needed':needed,'build_shared_libs':False,'ggml_backend_dl':False}))
version=subprocess.run([binary,'--version'],check=True,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10).stdout
assert len(version)<=4096
pathlib.Path(build,'version.txt').write_bytes(version)
'''


def build(source, out, identity):
    target = out / "build"
    target.mkdir()
    account = pwd.getpwnam("opc")
    os.chown(target, account.pw_uid, account.pw_gid)
    build_unit = "merlin-model-build-" + str(identity["run_id"]) + "-" + str(identity["run_attempt"])
    stdio = {name: out / ("build-" + name) for name in ("stdin", "stdout", "stderr")}
    for path in stdio.values():
        write_new(path, b"", 0o600)
    properties = ["User=opc", "Group=opc", "NoNewPrivileges=yes", "PrivateNetwork=yes", "PrivateTmp=yes",
                  "ProtectSystem=strict", "ProtectHome=read-only", "ReadWritePaths=" + str(target),
                  "MemoryMax=4294967296", "MemorySwapMax=0", "CPUQuota=150%", "TasksMax=32",
                  "RuntimeMaxSec=1800", "TimeoutStopSec=15", "KillMode=control-group", "LimitFSIZE=268435456",
                  "StandardInput=file:" + str(stdio["stdin"]), "StandardOutput=file:" + str(stdio["stdout"]),
                  "StandardError=file:" + str(stdio["stderr"])]
    argv = ["/usr/bin/systemd-run", "--quiet", "--wait", "--service-type=exec", "--unit=" + build_unit]
    for prop in properties:
        argv += ["--property=" + prop]
    argv += ["/usr/bin/python3", "-I", "-B", "-c", BUILD_SCRIPT, str(source), str(target), CMAKE, json.dumps(BUILD_FLAGS)]
    try:
        command(argv, timeout=1830, limit=65536, log_path=out / "build-manager.log", stop_unit=build_unit,
                monitored_files=[(stdio["stdout"], 1024**2), (stdio["stderr"], 1024**2)])
        if any(stdio[name].stat().st_size > 1024**2 for name in ("stdout", "stderr")):
            raise BootstrapError("completed build log limit")
    finally:
        combined = bytearray()
        for name in ("stdout", "stderr"):
            with open(stdio[name], "rb") as stream:
                data = stream.read(1024**2)
            combined.extend(("\n[" + name + "]\n").encode() + data)
        write_new(out / "build.log", bytes(combined))
    binary = target / "bin/llama-server"
    observed = file_identity(binary, 256 * 1024**2)
    observed.update({"path": str(binary), "version_text": read_regular(target / "version.txt", 4096).decode("utf-8", "strict").strip(),
                     "cgroup": decode(read_regular(target / "build-policy.json", 4096), 4096),
                     "runtime_linkage": decode(read_regular(target / "runtime-linkage.json", 4096), 4096),
                     "io_transport": "manager_opened_files", "per_stream_log_monitor_bytes": 1024**2,
                     "maximum_file_bytes": 268435456})
    return observed


def provider_argv(binary, model):
    return [str(binary), "--model", str(model), "--alias", MODEL_ALIAS, "--host", "127.0.0.1", "--port", "8080",
            "--ctx-size", "4096", "--parallel", "1", "--threads", "2", "--threads-batch", "2",
            "--threads-http", "2", "--n-gpu-layers", "0", "--offline", "--no-webui"]


def unit_text(binary, model):
    args = provider_argv(binary, model)
    return ("[Unit]\nDescription=Merlin pinned local coding provider\nAfter=network.target\n\n[Service]\nType=simple\n"
            "User=merlin-model\nGroup=merlin-model\nExecStart=/usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin LANG=C.UTF-8 " + " ".join(args) + "\n"
            "Restart=no\nTimeoutStopSec=20\nKillMode=control-group\nNoNewPrivileges=yes\nPrivateTmp=yes\nPrivateNetwork=no\n"
            "ProtectSystem=strict\nProtectHome=yes\nProtectKernelTunables=yes\nProtectControlGroups=yes\n"
            "RestrictAddressFamilies=AF_INET AF_UNIX\nIPAddressDeny=any\nIPAddressAllow=127.0.0.1/32\n"
            "CapabilityBoundingSet=\nMemoryMax=3221225472\nMemorySwapMax=0\nCPUQuota=150%\nTasksMax=32\n"
            "UMask=0077\nWorkingDirectory=/\nEnvironment=LANG=C.UTF-8\nStandardOutput=journal\nStandardError=journal\n"
            "\n[Install]\nWantedBy=multi-user.target\n").encode()


def install(binary, model_path):
    release_id = digest(canonical({"source": SOURCE_COMMIT, "model": MODEL_SHA,
                                   "binary": binary["sha256"], "build_flags": BUILD_FLAGS, "limits": LIMITS}))
    rooted_directory(INSTALL)
    release = INSTALL / release_id
    release.mkdir(mode=0o755)
    target_binary, target_model = release / "llama-server", release / MODEL_FILENAME
    raw = read_regular(binary["path"], 256 * 1024**2)
    if digest(raw) != binary["sha256"]:
        raise BootstrapError("built binary changed")
    write_new(target_binary, raw, 0o755)
    if file_identity(model_path, MODEL_BYTES) != {"sha256": MODEL_SHA, "size_bytes": MODEL_BYTES}:
        raise BootstrapError("model changed before install")
    os.rename(model_path, target_model)
    os.chmod(target_model, 0o644)
    command(["/usr/sbin/useradd", "--system", "--user-group", "--no-create-home", "--home-dir", "/nonexistent", "--shell", "/sbin/nologin", USER])
    text = unit_text(target_binary, target_model)
    write_new(UNIT_PATH, text)
    return {"release_id": release_id, "binary": str(target_binary), "model": str(target_model), "unit_sha256": digest(text)}


HTTP_SCRIPT = r'''
import http.client,json,sys
path=sys.argv[1];body=sys.argv[2].encode() if len(sys.argv)>2 else None
assert path in ['/health','/v1/models','/v1/chat/completions/input_tokens','/v1/chat/completions']
c=http.client.HTTPConnection('127.0.0.1',8080,timeout=170)
try:
 c.request('POST' if body is not None else 'GET',path,body=body,headers={'Content-Type':'application/json'} if body is not None else {})
 r=c.getresponse();assert r.status==200
 data=r.read(65537);assert len(data)<=65536
 sys.stdout.buffer.write(data)
finally:c.close()
'''


def http_json(path, payload=None, timeout=10):
    argv = ["/usr/sbin/runuser", "-u", "opc", "--", "/usr/bin/python3", "-I", "-B", "-c", HTTP_SCRIPT, path]
    if payload is not None:
        argv.append(canonical(payload).decode())
    raw = command(argv, timeout=timeout, limit=65536)
    value = decode(raw, 65536)
    if not isinstance(value, dict):
        raise BootstrapError("model metadata object required")
    return value, raw


def wait_ready():
    deadline = time.monotonic() + 120
    attempts = 0
    while time.monotonic() < deadline:
        attempts += 1
        try:
            health, raw = http_json("/health", timeout=min(3, max(0.1, deadline - time.monotonic())))
            if health.get("status") != "ok":
                raise BootstrapError("provider not ready")
            models, model_raw = http_json("/v1/models", timeout=5)
            if not isinstance(models.get("data"), list) or [m.get("id") for m in models["data"] if isinstance(m, dict)] != [MODEL_ALIAS]:
                raise BootstrapError("configured model alias mismatch")
            return {"health_sha256": digest(raw), "models_sha256": digest(model_raw), "model_ids": [MODEL_ALIAS], "attempts": attempts}
        except (BootstrapError, OSError, ValueError, subprocess.SubprocessError):
            if service()["ActiveState"] not in ("active", "activating"):
                raise BootstrapError("provider did not stay active")
            time.sleep(min(0.5, max(0, deadline - time.monotonic())))
    raise BootstrapError("provider startup deadline")


def observe_installed(installed, expected_binary_sha):
    observed = service()
    account = pwd.getpwnam(USER)
    if observed["ActiveState"] != "active" or observed["SubState"] != "running" or observed["User"] != USER or observed["Group"] != USER or observed["UnitFileState"] != "enabled":
        raise BootstrapError("provider service state mismatch")
    for path in (UNIT_PATH, installed["binary"], installed["model"]):
        info = Path(path).lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise BootstrapError("provider file is not root-owned and immutable to service user")
    if file_identity(UNIT_PATH, 16384)["sha256"] != installed["unit_sha256"] or observed["FragmentPath"] != str(UNIT_PATH):
        raise BootstrapError("provider unit changed")
    pid = int(observed["MainPID"])
    if pid <= 1 or os.readlink("/proc/" + str(pid) + "/exe") != installed["binary"]:
        raise BootstrapError("provider process executable mismatch")
    if file_identity(installed["binary"], 256 * 1024**2)["sha256"] != expected_binary_sha:
        raise BootstrapError("installed binary mismatch")
    if file_identity(installed["model"], MODEL_BYTES) != {"sha256": MODEL_SHA, "size_bytes": MODEL_BYTES}:
        raise BootstrapError("installed model mismatch")
    process = Path("/proc") / str(pid)
    start_ticks = (process / "stat").read_text().rsplit(")", 1)[1].split()[19]
    commandline = read_regular(process / "cmdline", 8192)
    if not commandline.endswith(b"\0"):
        raise BootstrapError("provider argv representation")
    argv = commandline[:-1].decode().split("\0")
    if argv != provider_argv(installed["binary"], installed["model"]):
        raise BootstrapError("provider live argv mismatch")
    namespace = os.readlink(process / "ns/net")
    if namespace != os.readlink("/proc/self/ns/net") or observed["PrivateNetwork"] != "no" or set(observed["RestrictAddressFamilies"].split()) != {"AF_INET", "AF_UNIX"}:
        raise BootstrapError("provider host-loopback namespace mismatch")
    status = (process / "status").read_text()
    if not re.search(r"^Uid:\s+" + str(account.pw_uid) + r"\s+" + str(account.pw_uid) + r"\s+" + str(account.pw_uid) + r"\s+" + str(account.pw_uid) + r"$", status, re.M):
        raise BootstrapError("provider process UID mismatch")
    model_stat = Path(installed["model"]).stat()
    device = "%02x:%02x" % (os.major(model_stat.st_dev), os.minor(model_stat.st_dev))
    matches = []
    with open(process / "maps") as stream:
        for index, line in enumerate(stream):
            if index >= 8192:
                raise BootstrapError("provider mapping limit")
            fields = line.rstrip("\n").split(None, 5)
            if len(fields) == 6 and fields[5] == installed["model"]:
                matches.append(fields[3] == device and fields[4] == str(model_stat.st_ino))
    if not matches or not all(matches):
        raise BootstrapError("provider mapped model identity mismatch")
    cgroup = (process / "cgroup").read_text().strip()
    if not cgroup.startswith("0::/") or ".." in cgroup:
        raise BootstrapError("provider cgroupv2 required")
    group = Path("/sys/fs/cgroup") / cgroup[4:]
    policy = {name: (group / name).read_text().strip() for name in ("memory.max", "memory.swap.max", "pids.max", "cpu.max")}
    q, period = map(int, policy["cpu.max"].split())
    if policy["memory.max"] != str(LIMITS["memory_max_bytes"]) or policy["memory.swap.max"] != "0" or policy["pids.max"] != "32" or q * 2 != period * 3:
        raise BootstrapError("provider cgroup limits mismatch")
    if int(service()["MainPID"]) != pid or (process / "stat").read_text().rsplit(")", 1)[1].split()[19] != start_ticks or os.readlink(process / "ns/net") != namespace:
        raise BootstrapError("provider process changed during observation")
    return {"unit": UNIT, "unit_sha256": installed["unit_sha256"], "user": USER, "uid": account.pw_uid,
            "group": USER, "gid": account.pw_gid, "active_state": "active", "sub_state": "running", "main_pid": pid,
            "enabled": True, "mapped_model_sha256": MODEL_SHA, "actual_cgroup": policy,
            "process_start_ticks": start_ticks, "network_namespace": namespace,
            "private_network": False, "restrict_address_families": sorted({"AF_INET", "AF_UNIX"}),
            "argv_sha256": digest(canonical(argv))}


def check_code(text):
    """Interpret a small AST; model text is never exec/eval or a shell command."""
    if not isinstance(text, str) or len(text.encode()) > 4096:
        raise BootstrapError("smoke code bound")
    code = text.strip()
    match = re.fullmatch(r"```(?:python)?\s*\n(.*)\n```", code, re.S)
    if match:
        code = match.group(1).strip()
    tree = ast.parse(code)
    nodes = list(ast.walk(tree))
    if len(nodes) > 128 or len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise BootstrapError("smoke function shape")
    function = tree.body[0]
    args = function.args
    if function.name != "clamp" or function.decorator_list or function.returns or args.posonlyargs or args.kwonlyargs or args.defaults or args.kw_defaults or args.vararg or args.kwarg or [a.arg for a in args.args] != ["value", "low", "high"] or any(a.annotation for a in args.args):
        raise BootstrapError("smoke function signature")
    allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.If, ast.Return, ast.Expr, ast.Constant,
               ast.Compare, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq, ast.IfExp, ast.Name, ast.Load,
               ast.Call, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.USub, ast.UAdd)
    if any(not isinstance(node, allowed) for node in nodes):
        raise BootstrapError("smoke syntax outside oracle")
    def expression(node, values, depth=0):
        if depth > 20:
            raise BootstrapError("smoke expression depth")
        if isinstance(node, ast.Name) and node.id in values:
            return values[node.id]
        if isinstance(node, ast.Constant) and type(node.value) in (int, float) and abs(node.value) <= 10**12:
            return node.value
        sub = lambda child: expression(child, values, depth + 1)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("min", "max") and not node.keywords and 2 <= len(node.args) <= 3:
            return (min if node.func.id == "min" else max)(sub(a) for a in node.args)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return -sub(node.operand) if isinstance(node.op, ast.USub) else +sub(node.operand)
        if isinstance(node, ast.IfExp):
            return sub(node.body) if sub(node.test) else sub(node.orelse)
        if isinstance(node, ast.Compare):
            left = sub(node.left)
            for op, right_node in zip(node.ops, node.comparators):
                right = sub(right_node)
                good = {ast.Lt: lambda: left < right, ast.LtE: lambda: left <= right, ast.Gt: lambda: left > right,
                        ast.GtE: lambda: left >= right, ast.Eq: lambda: left == right, ast.NotEq: lambda: left != right}[type(op)]()
                if not good:
                    return False
                left = right
            return True
        if isinstance(node, ast.BoolOp):
            results = [sub(value) for value in node.values]
            return all(results) if isinstance(node.op, ast.And) else any(results)
        raise BootstrapError("smoke expression rejected")
    def statements(body, values, depth=0):
        if depth > 20:
            raise BootstrapError("smoke statement depth")
        for node in body:
            if isinstance(node, ast.Return):
                return True, expression(node.value, values)
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            if isinstance(node, ast.If):
                found, value = statements(node.body if expression(node.test, values) else node.orelse, values, depth + 1)
                if found:
                    return True, value
            else:
                raise BootstrapError("smoke statement rejected")
        return False, None
    checks = []
    for value, low, high, expected in SMOKE_CASES:
        found, actual = statements(function.body, {"value": value, "low": low, "high": high})
        passed = found and type(actual) in (int, float) and actual == expected
        checks.append({"input": [value, low, high], "expected": expected, "actual": actual, "passed": passed})
    if not all(check["passed"] for check in checks):
        raise BootstrapError("coding smoke oracle failed")
    return {"code_sha256": digest(code.encode()), "checks": checks, "oracle_id": "restricted-ast-numeric-clamp/1"}


def smoke(out):
    request_raw = canonical(SMOKE_REQUEST)
    write_new(out / "smoke-request.json", request_raw)
    counted, count_raw = http_json("/v1/chat/completions/input_tokens", SMOKE_REQUEST, timeout=20)
    write_new(out / "smoke-token-count.json", count_raw)
    count = counted.get("input_tokens")
    if counted.get("object") != "response.input_tokens" or type(count) is not int or count <= 0 or count + 384 > 4096:
        raise BootstrapError("smoke token budget rejected")
    write_new(out / "smoke-inference-intent.json", canonical({"request_sha256": digest(request_raw), "input_tokens": count, "max_tokens": 384}))
    response, raw = http_json("/v1/chat/completions", SMOKE_REQUEST, timeout=180)
    write_new(out / "smoke-response.json", raw)
    usage = response.get("usage", {})
    completion = usage.get("completion_tokens")
    if response.get("model") != MODEL_ALIAS or type(completion) is not int or not 0 < completion <= 384 or type(usage.get("prompt_tokens")) is not int or usage["prompt_tokens"] != count or type(usage.get("total_tokens")) is not int or usage["total_tokens"] != count + completion or count + completion > 4096:
        raise BootstrapError("smoke actual usage mismatch")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or choices[0].get("finish_reason") != "stop":
        raise BootstrapError("smoke completion is incomplete")
    text = choices[0].get("message", {}).get("content")
    verified = check_code(text)
    return dict(verified, passed=True, request_sha256=digest(request_raw), response_sha256=digest(raw),
                response_text_sha256=digest(text.encode()), token_count_response_sha256=digest(count_raw),
                prompt_tokens=count, completion_tokens=completion, inference_requests=1)


def rollback(installed):
    if installed is None:
        return {"status": "no-service-start-reached", "service": service(),
                "unit_file_present": os.path.lexists(UNIT_PATH),
                "residuals": "acquisition/build files or incomplete install identities may remain; no retry is authorized"}
    if file_identity(UNIT_PATH, 16384)["sha256"] != installed["unit_sha256"]:
        raise BootstrapError("rollback refuses changed unit")
    command(["/usr/bin/systemctl", "disable", "--now", UNIT], timeout=40)
    UNIT_PATH.unlink()
    command(["/usr/bin/systemctl", "daemon-reload"])
    after = service()
    if after["ActiveState"] == "active" or after["LoadState"] != "not-found":
        raise BootstrapError("rollback did not restore absent service")
    return {"previous_state": "absent", "service_absent": True,
            "retained": ["root-owned versioned candidate files", "dedicated unprivileged user", "failed attempt evidence"],
            "manifest_published": False}


def build_manifest(identity, binary, installed, observed, receipt_raw):
    return {"schema": "merlin-local-model-provider/1", "status": "ready", "provider_id": MODEL_ALIAS,
            "endpoint": ENDPOINT, "model": MODEL_ALIAS,
            "revision": "gguf:" + MODEL_SHA + ";llama:" + SOURCE_COMMIT + ";bin:" + binary["sha256"],
            "model_artifact": {"repository": MODEL_REPO, "repository_revision": MODEL_REVISION, "filename": MODEL_FILENAME,
                               "size_bytes": MODEL_BYTES, "sha256": MODEL_SHA, "path": installed["model"]},
            "runtime": {"source_commit": SOURCE_COMMIT, "source_tree_sha": SOURCE_TREE,
                        "source_archive_sha256": SOURCE_SHA, "source_archive_bytes": SOURCE_BYTES,
                        "binary_path": installed["binary"], "binary_sha256": binary["sha256"], "version_text": binary["version_text"],
                        "build_flags": BUILD_FLAGS, "runtime_linkage": binary["runtime_linkage"]}, "service": observed, "limits": LIMITS,
            "bootstrap_receipt_sha256": digest(receipt_raw), "bootstrap_identity": identity,
            "qualification": False, "promotion_authority": False}


def inspect_ready():
    for path in (MANIFEST, BOOTSTRAP_RECEIPT):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise BootstrapError("provider authority file ownership")
    manifest_raw = read_regular(MANIFEST, 16384)
    receipt_raw = read_regular(BOOTSTRAP_RECEIPT, 65536)
    manifest, receipt = decode(manifest_raw, 16384), decode(receipt_raw, 65536)
    if manifest.get("schema") != "merlin-local-model-provider/1" or manifest.get("status") != "ready" or manifest.get("bootstrap_receipt_sha256") != digest(receipt_raw) or receipt.get("status") != "ready":
        raise BootstrapError("ready record mismatch")
    if manifest.get("model_artifact", {}).get("sha256") != MODEL_SHA or manifest.get("runtime", {}).get("source_commit") != SOURCE_COMMIT or manifest.get("endpoint") != ENDPOINT or manifest.get("model") != MODEL_ALIAS or manifest.get("limits") != LIMITS or manifest.get("qualification") is not False:
        raise BootstrapError("provider fixed pins mismatch")
    installed = {"binary": manifest["runtime"]["binary_path"], "model": manifest["model_artifact"]["path"], "unit_sha256": manifest["service"]["unit_sha256"]}
    observed = observe_installed(installed, manifest["runtime"]["binary_sha256"])
    return {"schema": "merlin-local-model-inspect/1", "status": "ready", "manifest_sha256": digest(manifest_raw),
            "bootstrap_receipt_sha256": digest(receipt_raw), "service": observed, "inference_requests": 0,
            "qualification": False, "external_model_cost_usd": 0}


def run(request, identity):
    validate_request(request, identity)
    if os.geteuid() != 0:
        raise BootstrapError("root workflow entry required")
    previous_umask = os.umask(0o022)
    try:
        return _run_validated(request, identity)
    finally:
        os.umask(previous_umask)


def _run_validated(request, identity):
    rooted_directory(STATE / "runs")
    out = STATE / "runs" / (str(identity["run_id"]) + "-" + str(identity["run_attempt"]))
    if request["operation"] == "inspect":
        out.mkdir(mode=0o755, exist_ok=False)
        observed = inspect_ready() if MANIFEST.exists() else {"status": "not-ready", "service": service(), "pending_intent": INTENT.exists()}
        write_new(out / "inspection.json", canonical(observed))
        return observed
    request_sha = digest(canonical(request))
    if INTENT.exists():
        previous = decode(read_regular(INTENT, 16384), 16384)
        if previous.get("request_sha256") == request_sha and MANIFEST.exists():
            return inspect_ready()
        raise BootstrapError("previous bootstrap intent requires reconciliation; no automatic effects")
    out.mkdir(mode=0o755, exist_ok=False)
    receipt = {"schema": "merlin-local-model-bootstrap-receipt/1", "status": "pending", "identity": identity,
               "request": request, "request_sha256": request_sha, "phases": [], "external_model_cost_usd": 0,
               "qualification": False, "promotion_authority": False}
    installed = None
    try:
        receipt["before"] = preflight()
        write_new(INTENT, canonical({"schema": "merlin-local-model-bootstrap-intent/1", "request_sha256": request_sha, "identity": identity, "output": str(out)}), 0o600)
        receipt["phases"].append("intent-recorded")
        source_archive, model_path = out / "llama-source.tar.gz", out / MODEL_FILENAME
        receipt["source_acquisition"] = download(SOURCE_URL, source_archive, SOURCE_BYTES, SOURCE_SHA, 180)
        source = out / "source"
        source.mkdir()
        with tarfile.open(source_archive, "r:gz") as archive:
            extracted = extract_members(archive, source)
        if extracted != {"files": 4176, "uncompressed_bytes": 184232076}:
            raise BootstrapError("exact verified source inventory mismatch")
        receipt["source_identity"] = dict(extracted, commit=SOURCE_COMMIT, tree=SOURCE_TREE, archive_sha256=SOURCE_SHA)
        receipt["phases"].append("source-verified")
        binary = build(source, out, identity)
        receipt["build"] = {key: value for key, value in binary.items() if key != "path"}
        receipt["phases"].append("native-build-passed")
        receipt["model_acquisition"] = download(MODEL_URL, model_path, MODEL_BYTES, MODEL_SHA, 900)
        with open(model_path, "rb") as stream:
            if stream.read(4) != b"GGUF":
                raise BootstrapError("model GGUF header mismatch")
        installed = install(binary, model_path)
        receipt["installed"] = installed
        receipt["phases"].append("fixed-unit-installed")
        command(["/usr/bin/systemctl", "daemon-reload"])
        command(["/usr/bin/systemctl", "enable", "--now", UNIT], timeout=30)
        receipt["startup"] = wait_ready()
        first = observe_installed(installed, binary["sha256"])
        receipt["first_service"] = first
        receipt["phases"].append("startup-verified")
        receipt["smoke"] = smoke(out)
        receipt["phases"].append("coding-smoke-passed")
        command(["/usr/bin/systemctl", "restart", UNIT], timeout=40)
        receipt["restart_probe"] = wait_ready()
        after = observe_installed(installed, binary["sha256"])
        if after["main_pid"] == first["main_pid"]:
            raise BootstrapError("restart did not change process")
        receipt["after"] = {"provider": after, "private": private_observation()}
        if receipt["after"]["private"] != receipt["before"]["private"]:
            raise BootstrapError("preexisting private runtime observations changed")
        receipt["phases"].append("restart-and-private-observations-verified")
        receipt["status"] = "ready"
        receipt_raw = canonical(receipt)
        manifest_raw = canonical(build_manifest(identity, binary, installed, after, receipt_raw))
        if len(receipt_raw) > 65536 or len(manifest_raw) > 16384:
            raise BootstrapError("provider record size limit")
        rooted_directory(CONFIG)
        write_new(out / "bootstrap-receipt.json", receipt_raw)
        write_new(out / "manifest.json", manifest_raw)
        write_new(BOOTSTRAP_RECEIPT, receipt_raw)
        write_new(MANIFEST, manifest_raw)
        return {"status": "ready", "manifest_sha256": digest(manifest_raw), "bootstrap_receipt_sha256": digest(receipt_raw), "inference_requests": 1}
    except BaseException as exc:
        receipt["status"] = "failed"
        receipt["error"] = {"type": type(exc).__name__, "message": str(exc)[:800]}
        try:
            receipt["rollback"] = rollback(installed)
        except BaseException as rollback_error:
            receipt["rollback"] = {"status": "needs-review", "type": type(rollback_error).__name__, "message": str(rollback_error)[:500]}
        write_new(out / "failed-receipt.json", canonical(receipt))
        raise

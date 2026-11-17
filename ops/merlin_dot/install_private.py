"""One-time, additive private-service installation; called only after OCI tests."""
import hashlib
import grp
import io
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import shutil
import stat
import subprocess
import sys
import zipfile

SERVICE = "merlin-dot-private.service"
SOURCE = Path("/opt/merlin-dot-private")
STATE = Path("/var/lib/merlin-dot-private")
CONFIG = Path("/etc/merlin-dot-private")
UNIT = Path("/etc/systemd/system") / SERVICE
MAX_ARCHIVE_BYTES = 13 * 1024 * 1024
MAX_EXPANDED_BYTES = 12 * 1024 * 1024


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate manifest field")
        result[key] = value
    return result


def read_bundle(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_ARCHIVE_BYTES:
            raise ValueError("bounded regular bundle file required")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(MAX_ARCHIVE_BYTES + 1)
        if len(raw) > MAX_ARCHIVE_BYTES:
            raise ValueError("bundle byte limit exceeded")
        return raw
    finally:
        os.close(descriptor)


def unpack_verified(raw, expected_digest, destination):
    if (not isinstance(raw, bytes) or len(raw) > MAX_ARCHIVE_BYTES
            or not isinstance(expected_digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None):
        raise ValueError("bounded bundle bytes and full lowercase digest required")
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("bundle digest mismatch")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        if not 1 <= len(members) <= 50 or sum(x.file_size for x in members) > MAX_EXPANDED_BYTES:
            raise ValueError("bundle limits exceeded")
        names = [x.filename for x in members]
        if len(set(names)) != len(names) or "manifest.json" not in names:
            raise ValueError("duplicate or missing bundle manifest")
        for member in members:
            raw_parts = member.filename.split("/")
            path = PurePosixPath(member.filename)
            kind = (member.external_attr >> 16) & 0o170000
            if (path.is_absolute() or "\\" in member.filename
                    or member.filename != member.orig_filename
                    or any(x in {"", ".", ".."} for x in raw_parts)
                    or any(ord(c) < 32 or ord(c) == 127 for c in member.filename)
                    or len(raw_parts) > 12 or len(member.filename.encode("utf-8")) > 1024
                    or any(len(part.encode("utf-8")) > 255 for part in raw_parts)
                    or member.is_dir() or kind not in {0, stat.S_IFREG}
                    or member.flag_bits & 1):
                raise ValueError("unsafe bundle member")
            if any(str(parent) in names for parent in path.parents if str(parent) != "."):
                raise ValueError("bundle file/directory prefix conflict")
        if archive.getinfo("manifest.json").file_size > 128 * 1024:
            raise ValueError("manifest size limit exceeded")
        manifest = json.loads(archive.read("manifest.json"), object_pairs_hook=_unique_object)
        if (not isinstance(manifest, dict)
                or set(manifest) != {"schema", "files", "source_repository", "source_base_commit"}
                or manifest["schema"] != "merlin-dot-release/1"
                or not isinstance(manifest["files"], dict) or "manifest.json" in manifest["files"]
                or not isinstance(manifest["source_repository"], str)
                or re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", manifest["source_repository"]) is None
                or not isinstance(manifest["source_base_commit"], str)
                or re.fullmatch(r"[0-9a-f]{40}", manifest["source_base_commit"]) is None
                or any(not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
                       for value in manifest["files"].values())):
            raise ValueError("invalid manifest")
        if set(names) != set(manifest["files"]) | {"manifest.json"}:
            raise ValueError("manifest file set mismatch")
        checked = {}
        for member in members:
            content = archive.read(member)
            if member.filename != "manifest.json" and hashlib.sha256(content).hexdigest() != manifest["files"][member.filename]:
                raise ValueError("manifest content mismatch")
            checked[member.filename] = content
    # All byte/path checks complete before creating the destination. Its parent
    # is operator-provisioned; never chmod or create arbitrary ancestors here.
    destination = Path(destination)
    destination.mkdir(mode=0o755, parents=False, exist_ok=False)
    for name, content in checked.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(content)
        target.chmod(0o644)
    for base, directories, files in os.walk(destination):
        os.chmod(base, 0o755)
    return manifest


def install(bundle_path, expected_digest):
    if os.geteuid() != 0:
        raise PermissionError("dedicated service installation requires root")
    for path in (SOURCE, STATE, CONFIG, UNIT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("refusing to overwrite existing installation path: " + str(path))
    try:
        pwd.getpwnam("merlin-dot")
    except KeyError:
        pass
    else:
        raise RuntimeError("refusing to reuse an existing service identity")
    runner = pwd.getpwnam("opc")
    if runner.pw_uid != 1000:
        raise RuntimeError("runner identity changed from validated preflight")
    runner_group = grp.getgrnam("opc")
    if runner_group.gr_gid not in os.getgrouplist("opc", runner.pw_gid):
        raise RuntimeError("validated runner cannot access the private socket group")
    usage = shutil.disk_usage("/opt/actions-runner")
    if usage.free < 2 * 1024**3 or os.statvfs("/opt/actions-runner").f_favail < 10000:
        raise RuntimeError("insufficient deployment headroom")
    raw = read_bundle(bundle_path)
    # Validate every byte and path before making a persistent host change.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="merlin-dot-root-validation-") as temp:
        unpack_verified(raw, expected_digest, Path(temp) / "checked")
    safe_env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}
    subprocess.run(["/usr/sbin/useradd", "--system", "--no-create-home", "--home-dir", str(STATE), "--shell", "/sbin/nologin", "merlin-dot"], env=safe_env, check=True, timeout=15)
    identity = pwd.getpwnam("merlin-dot")
    SOURCE.mkdir(mode=0o755)
    SOURCE.chmod(0o755)
    releases = SOURCE / "releases"
    releases.mkdir(mode=0o755)
    releases.chmod(0o755)
    release = releases / expected_digest
    unpack_verified(raw, expected_digest, release)
    (SOURCE / "current").symlink_to(release)
    STATE.mkdir(mode=0o700)
    CONFIG.mkdir(mode=0o755)
    CONFIG.chmod(0o755)
    code = """import json,sys
from pathlib import Path
from merlin.project_registry import MerlinRegistry
from dot_ai_os.bridge import DotContextBridge
source=Path(sys.argv[1]);root=Path(sys.argv[2])
r=MerlinRegistry(root);b=DotContextBridge(r,project_id='dot-production-docs',namespaces=('merlin','expert-robot'))
b.initialize()
for doc in json.loads((source/'seed-documents.json').read_text()):
 b.ingest(namespace=doc['namespace'],source_id=doc['source_id'],title=doc['title'],content=doc['content'].encode(),source_url=doc['source_url'],source_version=doc['source_version'],epistemic=doc['epistemic'],captured_at=doc['captured_at'])
print(json.dumps(b.status()))
"""
    env = dict(safe_env, PYTHONPATH=str(release / "python"), PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    seeded = subprocess.run(["/usr/bin/python3", "-s", "-c", code, str(release), str(STATE / "state")], env=env, check=True, capture_output=True, text=True, timeout=120)
    tools = ["health", "context_status", "context_search", "context_fetch", "session_handoff", "rsi_status", "virtual_circuit_demo"]
    config = {"schema": "merlin-private-host/1", "project_id": "dot-production-docs", "namespaces": ["merlin", "expert-robot"], "grants": [{"uid": runner.pw_uid, "principal": "local-runner-opc", "tools": tools}]}
    with (CONFIG / "config.json").open("x") as stream:
        stream.write(json.dumps(config, indent=2) + "\n")
    (CONFIG / "config.json").chmod(0o644)
    for base, directories, files in os.walk(STATE):
        os.chown(base, identity.pw_uid, identity.pw_gid)
        os.chmod(base, 0o700)
        for name in files:
            os.chown(Path(base) / name, identity.pw_uid, identity.pw_gid)
            os.chmod(Path(base) / name, 0o600)
    with UNIT.open("xb") as stream:
        stream.write((release / "ops/merlin-dot-private.service").read_bytes())
    UNIT.chmod(0o644)
    subprocess.run(["/usr/bin/systemctl", "daemon-reload"], env=safe_env, check=True, timeout=20)
    subprocess.run(["/usr/bin/systemctl", "enable", "--now", SERVICE], env=safe_env, check=True, timeout=30)
    return {"service": SERVICE, "service_uid": identity.pw_uid, "release": str(release), "bundle_sha256": expected_digest,
            "seed_status": json.loads(seeded.stdout), "public_listener": False, "raw_chat_exports_deployed": False,
            "created_paths": [str(SOURCE), str(STATE), str(CONFIG), str(UNIT)], "created_identity": "merlin-dot"}

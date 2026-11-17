"""Bounded offline recovery of the canonical Merlin SQLite/blob registry.

Python 3.9/Linux, standard library only. The operator must publish a quiescent,
non-WAL source; immutable read-only SQLite access is not a writer lock. No
registry constructor/migration runs against a source or restored database.
Manifests attest byte identity and structural checks, never scientific truth,
qualification, authorization or an independently trusted backup location.
"""
from __future__ import annotations

from contextlib import closing
import ctypes
from dataclasses import dataclass
from functools import lru_cache
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
import time
from typing import Any

from merlin.artifact_ref import ArtifactRef
from merlin.project_registry import MerlinRegistry


class RecoveryError(ValueError):
    """Unsafe, inconsistent, corrupt or over-budget recovery input/output."""


@dataclass(frozen=True)
class SnapshotBounds:
    max_db_bytes: int = 64 * 1024 * 1024
    max_blob_bytes: int = 25 * 1024 * 1024
    max_total_bytes: int = 256 * 1024 * 1024
    max_blobs: int = 4096
    max_rows: int = 100000
    max_manifest_bytes: int = 1024 * 1024
    max_seconds: float = 15.0

    def __post_init__(self):
        for name in ("max_db_bytes", "max_blob_bytes", "max_total_bytes", "max_blobs", "max_rows", "max_manifest_bytes"):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= 1024 ** 4:
                raise RecoveryError("positive bounded integer ceilings required")
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 300:
            raise RecoveryError("finite recovery deadline in (0,300] seconds required")


_TABLES = ("projects", "artifacts", "project_artifacts", "artifact_versions",
           "artifact_version_provenance", "claims", "relations", "capability_qualification_receipts")
_MANIFEST_FIELDS = {"schema", "database", "blobs", "table_counts", "inventory_sha256",
                    "source_database_sha256", "payload_bytes", "source_policy",
                    "qualification", "promotion_authority"}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _digest(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise RecoveryError("full lowercase SHA-256 identity required")
    return value


class _Budget:
    def __init__(self, bounds):
        if not isinstance(bounds, SnapshotBounds):
            raise RecoveryError("typed SnapshotBounds required")
        self.bounds = bounds
        self.end = time.monotonic() + bounds.max_seconds

    def check(self):
        if time.monotonic() > self.end:
            raise RecoveryError("recovery deadline exceeded")


def _path(value):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or "\x00" in str(path):
        raise RecoveryError("absolute traversal-free path required")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise RecoveryError("symlink path components are forbidden")
    return path


def _directory(path, *, exact=False):
    info = path.lstat()
    mode = stat.S_IMODE(info.st_mode)
    if (not stat.S_ISDIR(info.st_mode) or mode & 0o7022
            or (exact and mode != 0o700)):
        raise RecoveryError("safe directory mode required")
    return info


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_mode, info.st_nlink)


def _read_file(path, maximum, budget, *, expected=None, destination=None, exact=False):
    budget.check()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    out = None
    try:
        before = os.fstat(fd)
        mode = stat.S_IMODE(before.st_mode)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > maximum or mode & 0o7022 or (exact and mode != 0o600)):
            raise RecoveryError("bounded unlinked-safe regular file and safe mode required")
        if destination is not None:
            out = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            os.fchmod(out, 0o600)
        digest = hashlib.sha256(); size = 0
        while True:
            budget.check()
            chunk = os.read(fd, min(1024 * 1024, maximum + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > maximum:
                raise RecoveryError("file exceeds byte ceiling")
            digest.update(chunk)
            if out is not None:
                offset = 0
                while offset < len(chunk):
                    offset += os.write(out, chunk[offset:])
        if size != before.st_size or _signature(before) != _signature(os.fstat(fd)) or _signature(before) != _signature(path.lstat()):
            raise RecoveryError("file identity changed during recovery")
        if expected is not None and digest.hexdigest() != expected:
            raise RecoveryError("file SHA-256 mismatch")
        if out is not None:
            os.fsync(out)
        return {"size_bytes": size, "sha256": digest.hexdigest(), "mode": 0o600}, _signature(before)
    finally:
        os.close(fd)
        if out is not None:
            os.close(out)


def _scan(root, budget, *, exact=False):
    _directory(root, exact=exact)
    files = {}; directories = {""}
    for base, names, leaves in os.walk(root, followlinks=False):
        budget.check()
        if len(files) + len(directories) > budget.bounds.max_blobs * 2 + 20:
            raise RecoveryError("filesystem entry ceiling exceeded")
        for name in names:
            budget.check()
            path = Path(base) / name
            _directory(path, exact=exact)
            directories.add(path.relative_to(root).as_posix())
            if len(files) + len(directories) > budget.bounds.max_blobs * 2 + 20:
                raise RecoveryError("filesystem entry ceiling exceeded")
        for name in leaves:
            budget.check()
            path = Path(base) / name
            info = path.lstat()
            mode = stat.S_IMODE(info.st_mode)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or mode & 0o7022
                    or (exact and mode != 0o600)):
                raise RecoveryError("links, special files or unsafe file modes forbidden")
            files[path.relative_to(root).as_posix()] = _signature(info)
            if len(files) + len(directories) > budget.bounds.max_blobs * 2 + 20:
                raise RecoveryError("filesystem entry ceiling exceeded")
    return files, directories


def _non_wal(root):
    db = root / "merlin.sqlite3"
    for suffix in ("-wal", "-shm", "-journal"):
        if (root / ("merlin.sqlite3" + suffix)).exists() or (root / ("merlin.sqlite3" + suffix)).is_symlink():
            raise RecoveryError("published source must have no SQLite sidecars")
    fd = os.open(db, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RecoveryError("regular SQLite database required")
        header = os.read(fd, 100)
    finally:
        os.close(fd)
    if len(header) != 100 or header[:16] != b"SQLite format 3\x00" or header[18:20] != b"\x01\x01":
        raise RecoveryError("quiescent non-WAL canonical SQLite database required")


def _open_db(root, budget):
    _non_wal(root)
    db = sqlite3.connect((root / "merlin.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True, timeout=0)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    db.execute("PRAGMA trusted_schema=OFF")
    db.execute("PRAGMA foreign_keys=ON")
    db.set_progress_handler(lambda: int(time.monotonic() > budget.end), 1000)
    return db


def _schema(db):
    return [tuple(row) for row in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name")]


@lru_cache(maxsize=1)
def _canonical_schema():
    # Reuse the maintained schema, not a competing schema/migration definition.
    with tempfile.TemporaryDirectory(prefix="merlin-recovery-schema-") as directory:
        registry = MerlinRegistry(Path(directory) / "registry")
        with closing(sqlite3.connect(registry.db_path)) as db:
            return _schema(db)


def _catalog(db, budget):
    budget.check()
    schema = _schema(db)
    if schema != _canonical_schema():
        raise RecoveryError("database schema differs from the canonical registry")
    if [tuple(row) for row in db.execute("PRAGMA integrity_check")] != [("ok",)]:
        raise RecoveryError("SQLite integrity check failed")
    if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise RecoveryError("SQLite foreign key check failed")
    digest = hashlib.sha256(_json(schema)); counts = {}; rows_total = 0
    for table in _TABLES:
        columns = [row[1] for row in db.execute('PRAGMA table_info("' + table + '")')]
        order = ",".join('"' + column + '"' for column in columns)
        count = 0
        for row in db.execute('SELECT * FROM "' + table + '" ORDER BY ' + order):
            budget.check(); count += 1; rows_total += 1
            if rows_total > budget.bounds.max_rows:
                raise RecoveryError("database row ceiling exceeded")
            digest.update(_json([table, list(row)])); digest.update(b"\n")
        counts[table] = count
    if counts["artifacts"] > budget.bounds.max_blobs:
        raise RecoveryError("blob count ceiling exceeded")
    artifacts = {}
    for row in db.execute("SELECT digest,size_bytes,relative_path FROM artifacts ORDER BY digest"):
        identity = _digest(row["digest"])
        path = "blobs/sha256/" + identity[:2] + "/" + identity[2:]
        if (row["relative_path"] != path or type(row["size_bytes"]) is not int
                or not 0 <= row["size_bytes"] <= budget.bounds.max_blob_bytes):
            raise RecoveryError("artifact path or size violates canonical content addressing")
        artifacts[identity] = {"path": path, "size_bytes": row["size_bytes"], "sha256": identity, "mode": 0o600}
    latest = {}
    for row in db.execute("SELECT * FROM artifact_versions ORDER BY project_id,logical_path,version"):
        ref = ArtifactRef(row["project_id"], row["logical_path"], row["version"], row["digest"])
        previous = latest.get((ref.project_id, ref.logical_path))
        if (ref.sha256 not in artifacts or row["size_bytes"] != artifacts[ref.sha256]["size_bytes"]
                or ref.version != (previous[0] + 1 if previous else 1)
                or row["previous_digest"] != (previous[1] if previous else None)):
            raise RecoveryError("artifact version lineage is inconsistent")
        latest[(ref.project_id, ref.logical_path)] = (ref.version, ref.sha256)
    pointers = {(r["project_id"], r["logical_path"]): r["digest"] for r in db.execute("SELECT * FROM project_artifacts")}
    if pointers != {key: value[1] for key, value in latest.items()}:
        raise RecoveryError("current artifact pointers differ from historical latest versions")
    for table, payload, identity in (("artifact_version_provenance", "provenance_json", "provenance_sha256"),
                                     ("capability_qualification_receipts", "receipt_json", "receipt_sha256")):
        for row in db.execute('SELECT "' + payload + '","' + identity + '" FROM "' + table + '"'):
            raw = row[0]
            if not isinstance(raw, str) or _sha(raw.encode("utf-8")) != _digest(row[1]):
                raise RecoveryError("stored provenance/receipt digest mismatch")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict) or _json(parsed).decode("utf-8") != raw:
                raise RecoveryError("stored provenance/receipt must be canonical JSON")
    return {"inventory_sha256": digest.hexdigest(), "table_counts": counts}, artifacts


def _expected_tree(artifacts):
    files = {"merlin.sqlite3"} | {row["path"] for row in artifacts.values()}
    directories = {"", "blobs", "blobs/sha256"}
    directories.update(str(Path(row["path"]).parent) for row in artifacts.values())
    return files, directories


def _target(value, source):
    dest = _path(value)
    _directory(dest.parent)
    if dest.exists() or dest.is_symlink():
        raise RecoveryError("destination must not exist; overwrite is forbidden")
    if source == dest or source in dest.parents or dest in source.parents:
        raise RecoveryError("source and destination must be disjoint")
    return dest


def _stage(dest):
    path = Path(tempfile.mkdtemp(prefix=".merlin-recovery-quarantine-", dir=dest.parent))
    path.chmod(0o700)
    return path


def _mkdir(path):
    missing = []; current = path
    while not current.exists():
        missing.append(current); current = current.parent
    _directory(current, exact=True)
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        directory.chmod(0o700)


def _sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish(stage, dest):
    # Linux renameat2 NOREPLACE is atomic even if another caller creates dest.
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise RecoveryError("Linux atomic rename-noreplace support required")
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    def move(a, b):
        if rename(-100, os.fsencode(a), -100, os.fsencode(b), 1) != 0:
            error = ctypes.get_errno()
            raise OSError(error, "atomic non-overwriting publication failed")
    move(stage, dest)
    try:
        _sync_dir(dest.parent)
    except OSError:
        # The rename may have committed before directory fsync failed.
        move(dest, stage)
        raise


def _receipt(manifest, identity, **extra):
    return {"schema": "merlin-registry-recovery-receipt/1", "manifest_sha256": identity,
            "inventory_sha256": manifest["inventory_sha256"], "table_counts": manifest["table_counts"],
            "blob_count": len(manifest["blobs"]), "payload_bytes": manifest["payload_bytes"],
            "integrity_verified": True, "claim_scope": "bytes_and_canonical_structure_only",
            "qualification": False, "promotion_authority": False, **extra}


def _manifest(root, expected, budget):
    _digest(expected)
    row, signature = _read_file(root / "manifest.json", budget.bounds.max_manifest_bytes, budget, expected=expected, exact=True)
    fd = os.open(root / "manifest.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        raw = os.read(fd, budget.bounds.max_manifest_bytes + 1)
        if _signature(os.fstat(fd)) != signature:
            raise RecoveryError("manifest identity changed during recovery")
    finally:
        os.close(fd)
    if len(raw) != row["size_bytes"] or _sha(raw) != expected:
        raise RecoveryError("manifest changed during recovery")
    value = json.loads(raw)
    if (not isinstance(value, dict) or set(value) != _MANIFEST_FIELDS or value.get("schema") != "merlin-registry-snapshot/1"
            or value.get("qualification") is not False or value.get("promotion_authority") is not False
            or _json(value) != raw):
        raise RecoveryError("exact canonical snapshot manifest required")
    _digest(value["inventory_sha256"]); _digest(value["source_database_sha256"])
    if (not isinstance(value["blobs"], list) or len(value["blobs"]) > budget.bounds.max_blobs
            or not isinstance(value["table_counts"], dict) or set(value["table_counts"]) != set(_TABLES)
            or any(type(x) is not int or x < 0 for x in value["table_counts"].values())
            or sum(value["table_counts"].values()) > budget.bounds.max_rows):
        raise RecoveryError("manifest inventory exceeds bounds")
    if type(value["payload_bytes"]) is not int or not 0 <= value["payload_bytes"] <= budget.bounds.max_total_bytes:
        raise RecoveryError("manifest payload exceeds total byte ceiling")
    return value, signature


def _verify(root, expected, budget):
    root = _path(root); _directory(root, exact=True)
    manifest, _ = _manifest(root, expected, budget)
    before, dirs = _scan(root, budget, exact=True)
    if ("registry/merlin.sqlite3" not in before
            or before["registry/merlin.sqlite3"][2] > budget.bounds.max_db_bytes):
        raise RecoveryError("snapshot database missing or exceeds byte ceiling")
    registry = root / "registry"
    with closing(_open_db(registry, budget)) as db:
        summary, artifacts = _catalog(db, budget)
    rows = [manifest["database"], *manifest["blobs"]]
    expected_rows = [{"path": "merlin.sqlite3", **{k: manifest["database"].get(k) for k in ("size_bytes", "sha256", "mode")}},
                     *[artifacts[key] for key in sorted(artifacts)]]
    if rows != expected_rows or any(set(row) != {"path", "size_bytes", "sha256", "mode"} for row in rows):
        raise RecoveryError("manifest paths differ from canonical registered content")
    dbrow = manifest["database"]
    _digest(dbrow["sha256"])
    if (type(dbrow["size_bytes"]) is not int or not 0 < dbrow["size_bytes"] <= budget.bounds.max_db_bytes
            or any(row["mode"] != 0o600 for row in rows)):
        raise RecoveryError("manifest database size/mode exceeds bounds")
    files, registry_dirs = _expected_tree(artifacts)
    if set(before) != {"manifest.json"} | {"registry/" + path for path in files} or dirs != {""} | {"registry" + ("/" + path if path else "") for path in registry_dirs}:
        raise RecoveryError("snapshot contains missing or unmanifested filesystem entries")
    total = 0
    for row in rows:
        ceiling = budget.bounds.max_db_bytes if row["path"] == "merlin.sqlite3" else budget.bounds.max_blob_bytes
        observed, _ = _read_file(registry / row["path"], ceiling, budget, expected=row["sha256"], exact=True)
        if observed["size_bytes"] != row["size_bytes"]:
            raise RecoveryError("manifest file size mismatch")
        total += observed["size_bytes"]
        if total > budget.bounds.max_total_bytes:
            raise RecoveryError("total payload ceiling exceeded")
    if total != manifest["payload_bytes"] or summary != {key: manifest[key] for key in ("inventory_sha256", "table_counts")}:
        raise RecoveryError("manifest metadata inventory differs from database")
    if _scan(root, budget, exact=True) != (before, dirs):
        raise RecoveryError("snapshot changed during verification")
    return manifest


def _boundary(call):
    @wraps(call)
    def guarded(*args, **kwargs):
        try:
            return call(*args, **kwargs)
        except RecoveryError:
            raise
        except (OSError, sqlite3.Error, TypeError, KeyError, AttributeError, UnicodeError, json.JSONDecodeError) as exc:
            raise RecoveryError("recovery input unavailable or invalid: " + type(exc).__name__) from exc
    return guarded


@_boundary
def verify_snapshot(snapshot_root, expected_manifest_sha256, bounds=SnapshotBounds()):
    """Verify a pinned snapshot; never open a writable source connection."""
    budget = _Budget(bounds)
    manifest = _verify(snapshot_root, expected_manifest_sha256, budget)
    return _receipt(manifest, expected_manifest_sha256, operation="verify")


@_boundary
def create_snapshot(source_root, snapshot_dest, bounds=SnapshotBounds()):
    """Snapshot a quiescent published registry, leaving failures quarantined.

    Operational lock files and unregistered extras must be excluded by publishing
    a clean canonical root first. No source locks, sidecars or migrations are made.
    """
    budget = _Budget(bounds); source = _path(source_root); _directory(source)
    dest = _target(snapshot_dest, source)
    before, directories = _scan(source, budget)
    source_db, _ = _read_file(source / "merlin.sqlite3", bounds.max_db_bytes, budget)
    with closing(_open_db(source, budget)) as db:
        summary, artifacts = _catalog(db, budget)
        files, expected_dirs = _expected_tree(artifacts)
        if set(before) != files or directories != expected_dirs:
            raise RecoveryError("published registry must contain exactly canonical database and registered blobs")
        total = source_db["size_bytes"] + sum(row["size_bytes"] for row in artifacts.values())
        if total > bounds.max_total_bytes:
            raise RecoveryError("total payload ceiling exceeded")
        stage = _stage(dest); target = stage / "registry"
        _mkdir(target / "blobs" / "sha256")
        try:
            with closing(sqlite3.connect(target / "merlin.sqlite3")) as output:
                os.chmod(target / "merlin.sqlite3", 0o600)
                output.execute("PRAGMA journal_mode=DELETE")
                db.backup(output, pages=128, progress=lambda status, remaining, count: budget.check(), sleep=0.0)
            os.chmod(target / "merlin.sqlite3", 0o600)
            for row in artifacts.values():
                _mkdir((target / row["path"]).parent)
                observed, _ = _read_file(source / row["path"], bounds.max_blob_bytes, budget,
                                         expected=row["sha256"], destination=target / row["path"])
                if observed["size_bytes"] != row["size_bytes"]:
                    raise RecoveryError("registered blob size differs from content")
            with closing(_open_db(target, budget)) as copy:
                if _catalog(copy, budget) != (summary, artifacts):
                    raise RecoveryError("online backup changed canonical metadata inventory")
            source_after, _ = _read_file(source / "merlin.sqlite3", bounds.max_db_bytes, budget, expected=source_db["sha256"])
            _non_wal(source)
            if source_after != source_db or _scan(source, budget) != (before, directories):
                raise RecoveryError("published source changed during snapshot")
            database, _ = _read_file(target / "merlin.sqlite3", bounds.max_db_bytes, budget, exact=True)
            total = database["size_bytes"] + sum(row["size_bytes"] for row in artifacts.values())
            manifest = {"schema": "merlin-registry-snapshot/1", "database": {"path": "merlin.sqlite3", **database},
                        "blobs": [artifacts[key] for key in sorted(artifacts)], **summary,
                        "source_database_sha256": source_db["sha256"], "payload_bytes": total,
                        "source_policy": "operator_published_quiescent_non_wal; immutable_read_only_backup",
                        "qualification": False, "promotion_authority": False}
            raw = _json(manifest)
            if len(raw) > bounds.max_manifest_bytes:
                raise RecoveryError("manifest byte ceiling exceeded")
            path = stage / "manifest.json"
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                os.fchmod(stream.fileno(), 0o600); stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            identity = _sha(raw)
            _verify(stage, identity, budget)
            for directory, _, _ in os.walk(stage, topdown=False):
                _sync_dir(Path(directory))
            _publish(stage, dest)
        except Exception as exc:
            raise RecoveryError("snapshot failed; any staged output remains quarantined at " + str(stage)) from exc
    return _receipt(manifest, identity, operation="snapshot", snapshot_root=str(dest))


@_boundary
def restore_snapshot(snapshot_root, dest, expected_manifest_sha256, bounds=SnapshotBounds()):
    """Restore exact checked bytes to a new canonical root, without migrations."""
    budget = _Budget(bounds); source = _path(snapshot_root)
    target = _target(dest, source)
    manifest = _verify(source, expected_manifest_sha256, budget)
    stage = _stage(target); _mkdir(stage / "blobs" / "sha256")
    try:
        for row in [manifest["database"], *manifest["blobs"]]:
            _mkdir((stage / row["path"]).parent)
            limit = bounds.max_db_bytes if row["path"] == "merlin.sqlite3" else bounds.max_blob_bytes
            _read_file(source / "registry" / row["path"], limit, budget,
                       expected=row["sha256"], destination=stage / row["path"], exact=True)
        with closing(_open_db(stage, budget)) as db:
            summary, artifacts = _catalog(db, budget)
        if summary != {key: manifest[key] for key in ("inventory_sha256", "table_counts")}:
            raise RecoveryError("restored metadata differs from pinned snapshot")
        _verify(source, expected_manifest_sha256, budget)
        for directory, _, _ in os.walk(stage, topdown=False):
            _sync_dir(Path(directory))
        _publish(stage, target)
    except Exception as exc:
        raise RecoveryError("restore failed; any staged output remains quarantined at " + str(stage)) from exc
    return _receipt(manifest, expected_manifest_sha256, operation="restore", registry_root=str(target))

"""Small durable project/artifact/claim registry for Merlin foundation.

SQLite stores metadata and typed relationships; immutable SHA-256 blobs store
artifact bytes. Hashes establish identity/integrity, not truth or approval.
"""
from __future__ import annotations
from contextlib import closing

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import time
from typing import Any, Mapping

from .artifact_ref import ArtifactRef


MAX_ARTIFACT_READ_BYTES = 25 * 1024 * 1024


def _file_sha256(path: Path) -> str:
    """Hash fresh file bytes with bounded auxiliary memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        # Size only selects buffer capacity; it never limits verified bytes.
        buffer = bytearray(min(256 * 1024, max(4096, os.fstat(stream.fileno()).st_size)))
        view = memoryview(buffer)
        while count := stream.readinto(buffer):
            digest.update(view[:count])
    return digest.hexdigest()


class ArtifactSizeLimitError(ValueError):
    """Raised when an exact artifact read exceeds the configured byte ceiling."""


class MerlinRegistry:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.blobs = self.root / "blobs" / "sha256"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "merlin.sqlite3"
        self._initialize()

    def _connect(self):
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _initialize(self):
        with closing(self._connect()) as db, db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS projects(
              project_id TEXT PRIMARY KEY, name TEXT NOT NULL,
              version TEXT NOT NULL, metadata_json TEXT NOT NULL,
              created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS artifacts(
              digest TEXT PRIMARY KEY, media_type TEXT NOT NULL,
              size_bytes INTEGER NOT NULL, relative_path TEXT NOT NULL,
              created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS project_artifacts(
              project_id TEXT NOT NULL REFERENCES projects(project_id),
              digest TEXT NOT NULL REFERENCES artifacts(digest),
              logical_path TEXT NOT NULL,
              PRIMARY KEY(project_id, logical_path));
            CREATE TABLE IF NOT EXISTS artifact_versions(
              project_id TEXT NOT NULL REFERENCES projects(project_id),
              logical_path TEXT NOT NULL,
              version INTEGER NOT NULL CHECK(version > 0),
              digest TEXT NOT NULL REFERENCES artifacts(digest),
              media_type TEXT NOT NULL,
              size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
              previous_digest TEXT REFERENCES artifacts(digest),
              created_at REAL NOT NULL,
              PRIMARY KEY(project_id, logical_path, version));
            CREATE INDEX IF NOT EXISTS artifact_versions_by_digest
              ON artifact_versions(digest);
            CREATE TABLE IF NOT EXISTS artifact_version_provenance(
              project_id TEXT NOT NULL,
              logical_path TEXT NOT NULL,
              version INTEGER NOT NULL,
              provenance_json TEXT NOT NULL,
              provenance_sha256 TEXT NOT NULL,
              PRIMARY KEY(project_id, logical_path, version),
              FOREIGN KEY(project_id, logical_path, version)
                REFERENCES artifact_versions(project_id, logical_path, version));
            CREATE TRIGGER IF NOT EXISTS artifact_version_provenance_no_update
              BEFORE UPDATE ON artifact_version_provenance
              BEGIN SELECT RAISE(ABORT, 'artifact version provenance is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS artifact_version_provenance_no_delete
              BEFORE DELETE ON artifact_version_provenance
              BEGIN SELECT RAISE(ABORT, 'artifact version provenance is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS artifact_versions_no_update
              BEFORE UPDATE ON artifact_versions
              BEGIN SELECT RAISE(ABORT, 'artifact versions are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS artifact_versions_no_delete
              BEFORE DELETE ON artifact_versions
              BEGIN SELECT RAISE(ABORT, 'artifact versions are append-only'); END;
            CREATE TABLE IF NOT EXISTS claims(
              claim_id TEXT PRIMARY KEY, statement TEXT NOT NULL,
              evidence_class TEXT NOT NULL, assumptions_json TEXT NOT NULL,
              status TEXT NOT NULL, created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS relations(
              source_id TEXT NOT NULL, relation TEXT NOT NULL, target_id TEXT NOT NULL,
              metadata_json TEXT NOT NULL,
              PRIMARY KEY(source_id, relation, target_id));
            CREATE TABLE IF NOT EXISTS capability_qualification_receipts(
              receipt_id TEXT PRIMARY KEY,
              capability_id TEXT NOT NULL,
              artifact_digest TEXT NOT NULL REFERENCES artifacts(digest),
              receipt_json TEXT NOT NULL,
              receipt_sha256 TEXT NOT NULL UNIQUE,
              created_at REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS capability_receipts_by_capability
              ON capability_qualification_receipts(capability_id, created_at);
            CREATE TRIGGER IF NOT EXISTS capability_receipts_no_update
              BEFORE UPDATE ON capability_qualification_receipts
              BEGIN SELECT RAISE(ABORT, 'capability qualification receipts are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS capability_receipts_no_delete
              BEFORE DELETE ON capability_qualification_receipts
              BEGIN SELECT RAISE(ABORT, 'capability qualification receipts are append-only'); END;
            INSERT OR IGNORE INTO artifact_versions(
              project_id,logical_path,version,digest,media_type,size_bytes,
              previous_digest,created_at)
            SELECT pa.project_id,pa.logical_path,1,pa.digest,a.media_type,a.size_bytes,
                   NULL,a.created_at
            FROM project_artifacts pa JOIN artifacts a USING(digest);
            """)
    
    def register_project(self, project_id: str, name: str, version: str = "0.1.0",
                         metadata: dict[str, Any] | None = None) -> None:
        if not project_id.strip() or not name.strip():
            raise ValueError("project ID and name are required")
        payload = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"))
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO projects VALUES(?,?,?,?,?) "
                "ON CONFLICT(project_id) DO UPDATE SET name=excluded.name, "
                "version=excluded.version, metadata_json=excluded.metadata_json",
                (project_id, name, version, payload, time.time()),
            )

    def put_artifact(self, project_id: str, logical_path: str, content: bytes,
                     media_type: str = "application/octet-stream", *,
                     provenance: Mapping[str, Any] | None = None) -> str:
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project_id is required")
        if (not isinstance(logical_path, str) or not logical_path
                or logical_path.startswith("/")
                or ".." in Path(logical_path).parts):
            raise ValueError("artifact logical path must be relative and traversal-free")
        if not isinstance(content, bytes):
            raise TypeError("artifact content must be bytes")
        if not isinstance(media_type, str) or not media_type.strip():
            raise ValueError("media_type is required")
        provenance_json = None
        provenance_sha256 = None
        if provenance is not None:
            expected_provenance_fields = {
                "schema", "source_repo", "source_commit",
                "artifact_id", "artifact_kind", "artifact_schema",
            }
            if not isinstance(provenance, Mapping) or set(provenance) != expected_provenance_fields:
                raise ValueError("artifact provenance must contain the exact v1 field set")
            if provenance.get("schema") != "merlin-artifact-provenance/1":
                raise ValueError("unsupported artifact provenance schema")
            source_repo = provenance.get("source_repo")
            source_commit = provenance.get("source_commit")
            if not isinstance(source_repo, str) or not source_repo.strip():
                raise ValueError("artifact provenance source_repo is required")
            if (not isinstance(source_commit, str) or len(source_commit) != 40
                    or any(ch not in "0123456789abcdef" for ch in source_commit)):
                raise ValueError("artifact provenance source_commit must be a full lowercase Git SHA")
            for field in ("artifact_id", "artifact_kind", "artifact_schema"):
                value = provenance.get(field)
                if not isinstance(value, str) or not value.strip() or len(value) > 256:
                    raise ValueError(f"artifact provenance {field} is invalid")
            provenance_json = self._canonical_json(provenance)
            provenance_sha256 = hashlib.sha256(provenance_json.encode("utf-8")).hexdigest()
        with closing(self._connect()) as db:
            if not db.execute("SELECT 1 FROM projects WHERE project_id=?",
                              (project_id,)).fetchone():
                raise KeyError(f"unknown project: {project_id}")

        digest = hashlib.sha256(content).hexdigest()
        target = self.blobs / digest[:2] / digest[2:]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise RuntimeError("content-addressed blob integrity mismatch")
        else:
            # Concurrent producers can legitimately publish the same digest.
            # A shared digest.tmp path lets one replace remove another writer's
            # staging file. Each writer instead owns a unique completed file;
            # replacing the digest with those identical bytes remains atomic.
            descriptor, temporary = tempfile.mkstemp(
                prefix="." + target.name + ".", suffix=".tmp", dir=str(target.parent))
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass

        timestamp = time.time()
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?,?)",
                       (digest, media_type.strip(), len(content),
                        str(target.relative_to(self.root)), timestamp))
            current = db.execute(
                "SELECT digest FROM project_artifacts WHERE project_id=? AND logical_path=?",
                (project_id, logical_path),
            ).fetchone()
            if current is None or current["digest"] != digest:
                previous_digest = current["digest"] if current else None
                next_version = db.execute(
                    "SELECT COALESCE(MAX(version),0)+1 AS next_version "
                    "FROM artifact_versions WHERE project_id=? AND logical_path=?",
                    (project_id, logical_path),
                ).fetchone()["next_version"]
                db.execute(
                    "INSERT INTO artifact_versions(project_id,logical_path,version,digest,"
                    "media_type,size_bytes,previous_digest,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (project_id, logical_path, next_version, digest, media_type.strip(),
                     len(content), previous_digest, timestamp),
                )
                db.execute(
                    "INSERT INTO project_artifacts(project_id,digest,logical_path) VALUES(?,?,?) "
                    "ON CONFLICT(project_id,logical_path) DO UPDATE SET digest=excluded.digest",
                    (project_id, digest, logical_path),
                )
                if provenance_json is not None:
                    db.execute(
                        "INSERT INTO artifact_version_provenance VALUES(?,?,?,?,?)",
                        (project_id, logical_path, next_version, provenance_json, provenance_sha256),
                    )
            elif provenance_json is not None:
                current_version = db.execute(
                    "SELECT MAX(version) AS version FROM artifact_versions "
                    "WHERE project_id=? AND logical_path=?",
                    (project_id, logical_path),
                ).fetchone()["version"]
                existing_provenance = db.execute(
                    "SELECT provenance_json FROM artifact_version_provenance "
                    "WHERE project_id=? AND logical_path=? AND version=?",
                    (project_id, logical_path, current_version),
                ).fetchone()
                if existing_provenance is None or existing_provenance["provenance_json"] != provenance_json:
                    raise ValueError("cannot attach or alter provenance for an already registered artifact version")
        return digest

    def artifact_history(self, project_id: str, logical_path: str) -> list[dict[str, Any]]:
        """Return the append-only version lineage for one project artifact path."""
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project_id is required")
        if (not isinstance(logical_path, str) or not logical_path
                or logical_path.startswith("/")
                or ".." in Path(logical_path).parts):
            raise ValueError("artifact logical path must be relative and traversal-free")
        with closing(self._connect()) as db, db:
            if not db.execute("SELECT 1 FROM projects WHERE project_id=?",
                              (project_id,)).fetchone():
                raise KeyError(f"unknown project: {project_id}")
            rows = db.execute(
                "SELECT version,digest,media_type,size_bytes,previous_digest,created_at "
                "FROM artifact_versions WHERE project_id=? AND logical_path=? "
                "ORDER BY version",
                (project_id, logical_path),
            ).fetchall()
        return [dict(row) for row in rows]

    def artifact_ref(self, project_id: str, logical_path: str,
                     version: int | None = None) -> dict[str, Any]:
        """Return an immutable reference to one exact artifact version.

        Omitting version selects the latest version at lookup time. The returned
        reference remains pinned even after the logical path advances.
        """
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project_id is required")
        if (not isinstance(logical_path, str) or not logical_path
                or logical_path.startswith("/") or "\\" in logical_path
                or "\x00" in logical_path
                or ".." in Path(logical_path).parts):
            raise ValueError("artifact logical path must be relative and traversal-free")
        if version is not None and (
            isinstance(version, bool) or not isinstance(version, int) or version < 1
        ):
            raise ValueError("version must be a positive integer")
        with closing(self._connect()) as db:
            if not db.execute("SELECT 1 FROM projects WHERE project_id=?",
                              (project_id,)).fetchone():
                raise KeyError(f"unknown project: {project_id}")
            if version is None:
                row = db.execute(
                    "SELECT version,digest FROM artifact_versions "
                    "WHERE project_id=? AND logical_path=? ORDER BY version DESC LIMIT 1",
                    (project_id, logical_path),
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT version,digest FROM artifact_versions "
                    "WHERE project_id=? AND logical_path=? AND version=?",
                    (project_id, logical_path, version),
                ).fetchone()
        if row is None:
            raise KeyError(f"unknown artifact version: {project_id}/{logical_path}/{version}")
        return ArtifactRef(project_id, logical_path, row["version"], row["digest"]).to_dict()

    def resolve_artifact_ref(self, value: Mapping[str, Any]) -> dict[str, Any]:
        """Resolve and re-hash the exact immutable version named by a reference."""
        ref = ArtifactRef.from_mapping(value)
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT digest,media_type,size_bytes,previous_digest,created_at "
                "FROM artifact_versions WHERE project_id=? AND logical_path=? AND version=?",
                (ref.project_id, ref.logical_path, ref.version),
            ).fetchone()
            if row is None:
                raise KeyError("artifact reference does not identify a registered version")
            current = db.execute(
                "SELECT MAX(version) AS version FROM artifact_versions "
                "WHERE project_id=? AND logical_path=?",
                (ref.project_id, ref.logical_path),
            ).fetchone()
        if row["digest"] != ref.sha256:
            raise ValueError("artifact reference digest does not match its registered version")
        if not self.verify_artifact(ref.sha256):
            raise RuntimeError("artifact reference content failed SHA-256 verification")
        blob_path = self.blobs / ref.sha256[:2] / ref.sha256[2:]
        if blob_path.stat().st_size != row["size_bytes"]:
            raise RuntimeError("artifact reference content size does not match its version record")
        with closing(self._connect()) as db:
            provenance_row = db.execute(
                "SELECT provenance_json,provenance_sha256 FROM artifact_version_provenance "
                "WHERE project_id=? AND logical_path=? AND version=?",
                (ref.project_id, ref.logical_path, ref.version),
            ).fetchone()
        result = {
            "schema": "merlin-artifact-resolution/1",
            "artifact_ref": ref.to_dict(),
            "media_type": row["media_type"],
            "size_bytes": row["size_bytes"],
            "previous_digest": row["previous_digest"],
            "created_at": row["created_at"],
            "is_current": current is not None and current["version"] == ref.version,
            "verified": True,
        }
        if provenance_row is not None:
            provenance_json = provenance_row["provenance_json"]
            if hashlib.sha256(provenance_json.encode("utf-8")).hexdigest() != provenance_row["provenance_sha256"]:
                raise RuntimeError("artifact version provenance integrity check failed")
            try:
                result["provenance"] = json.loads(provenance_json)
            except ValueError as exc:
                raise RuntimeError("artifact version provenance is malformed") from exc
        return result

    def read_artifact_ref(
        self,
        value: Mapping[str, Any],
        *,
        max_bytes: int = MAX_ARTIFACT_READ_BYTES,
    ) -> dict[str, Any]:
        """Return exact immutable version bytes after independent digest/size checks."""
        if (isinstance(max_bytes, bool) or not isinstance(max_bytes, int)
                or not 1 <= max_bytes <= MAX_ARTIFACT_READ_BYTES):
            raise ValueError("max_bytes must be between 1 and 25 MiB")
        resolution = self.resolve_artifact_ref(value)
        if resolution["size_bytes"] > max_bytes:
            raise ArtifactSizeLimitError("artifact exceeds the configured read byte limit")
        ref = ArtifactRef.from_mapping(value)
        path = self.blobs / ref.sha256[:2] / ref.sha256[2:]
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise RuntimeError("artifact reference blob is unavailable") from exc
        if len(content) != resolution["size_bytes"]:
            raise RuntimeError("artifact reference content size changed during read")
        if hashlib.sha256(content).hexdigest() != ref.sha256:
            raise RuntimeError("artifact reference content digest changed during read")
        return {"resolution": resolution, "content": content}

    def verify_artifact(self, digest: str) -> bool:
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT relative_path FROM artifacts WHERE digest=?", (digest,)).fetchone()
        if row is None:
            return False
        path = self.root / row["relative_path"]
        return path.is_file() and _file_sha256(path) == digest

    def add_claim(self, claim_id: str, statement: str, evidence_class: str,
                  assumptions: tuple[str, ...] = (), status: str = "unreviewed") -> None:
        if not claim_id.strip() or not statement.strip() or not evidence_class.strip():
            raise ValueError("claim identity, statement and evidence class are required")
        with closing(self._connect()) as db, db:
            db.execute("INSERT INTO claims VALUES(?,?,?,?,?,?)",
                       (claim_id, statement, evidence_class,
                        json.dumps(list(assumptions), sort_keys=True), status, time.time()))

    def relate(self, source_id: str, relation: str, target_id: str,
               metadata: dict[str, Any] | None = None) -> None:
        if not source_id.strip() or not relation.strip() or not target_id.strip():
            raise ValueError("relation endpoints and type are required")
        encoded = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"))
        with closing(self._connect()) as db, db:
            existing = db.execute(
                "SELECT metadata_json FROM relations WHERE source_id=? AND relation=? AND target_id=?",
                (source_id, relation, target_id),
            ).fetchone()
            if existing is not None:
                if existing["metadata_json"] != encoded:
                    raise ValueError("registry relation already exists with different metadata")
                return
            db.execute("INSERT INTO relations VALUES(?,?,?,?)",
                       (source_id, relation, target_id, encoded))

    @staticmethod
    def _canonical_json(value: Mapping[str, Any]) -> str:
        return json.dumps(dict(value), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)

    @staticmethod
    def _valid_sha256(value: Any) -> bool:
        return (isinstance(value, str) and len(value) == 64
                and all(char in "0123456789abcdef" for char in value))

    def record_capability_qualification(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        """Append an untrusted qualification claim pending independent CACE review.

        This stores evidence; it does not grant a capability or assert that a
        provider is qualified. Only an independent verifier may promote it.
        """
        if not isinstance(receipt, Mapping):
            raise ValueError("qualification receipt must be an object")
        required = (
            "receipt_id", "capability_id", "capability_version", "provider",
            "model_revision", "heldout_suite", "environment_sha256",
            "artifact_digest", "result", "signer_id", "signed_at",
        )
        normalized: dict[str, Any] = {}
        for key in required:
            value = receipt.get(key)
            if key in {"environment_sha256", "artifact_digest"}:
                if not self._valid_sha256(value):
                    raise ValueError(f"{key} must be a lowercase SHA-256 digest")
                normalized[key] = value
            elif key == "signed_at":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError("signed_at must be a finite positive timestamp")
                if not (0 < float(value) < float("inf")):
                    raise ValueError("signed_at must be a finite positive timestamp")
                normalized[key] = float(value)
            else:
                if not isinstance(value, str) or not value.strip() or len(value) > 512:
                    raise ValueError(f"{key} must be a non-empty string of at most 512 characters")
                normalized[key] = value.strip()
        if normalized["result"] not in {"passed", "failed"}:
            raise ValueError("result must be passed or failed")
        # Preserve additional structured evidence fields in the digest, but do
        # not let them override the validated contract fields.
        for key, value in receipt.items():
            if key not in normalized:
                normalized[key] = value
        encoded = self._canonical_json(normalized)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        artifact_digest = normalized["artifact_digest"]
        if not self.verify_artifact(artifact_digest):
            raise ValueError("qualification evidence artifact is missing or fails digest verification")
        with closing(self._connect()) as db, db:
            existing = db.execute(
                "SELECT receipt_sha256 FROM capability_qualification_receipts WHERE receipt_id=?",
                (normalized["receipt_id"],),
            ).fetchone()
            if existing is not None:
                if existing["receipt_sha256"] != digest:
                    raise ValueError("receipt_id was reused with different qualification content")
                return {
                    "receipt_id": normalized["receipt_id"],
                    "receipt_sha256": digest,
                    "status": "pending_independent_verification",
                    "qualified": False,
                    "idempotent_replay": True,
                }
            db.execute(
                "INSERT INTO capability_qualification_receipts"
                "(receipt_id,capability_id,artifact_digest,receipt_json,receipt_sha256,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (normalized["receipt_id"], normalized["capability_id"],
                 artifact_digest, encoded, digest, time.time()),
            )
        return {
            "receipt_id": normalized["receipt_id"],
            "receipt_sha256": digest,
            "status": "pending_independent_verification",
            "qualified": False,
            "idempotent_replay": False,
        }

    def capability_qualification_receipts(self, capability_id: str) -> list[dict[str, Any]]:
        if not isinstance(capability_id, str) or not capability_id.strip():
            raise ValueError("capability_id is required")
        with closing(self._connect()) as db, db:
            rows = db.execute(
                "SELECT receipt_id,receipt_json,receipt_sha256,created_at "
                "FROM capability_qualification_receipts WHERE capability_id=? "
                "ORDER BY created_at,receipt_id",
                (capability_id.strip(),),
            ).fetchall()
        return [{
            "receipt_id": row["receipt_id"],
            "receipt": json.loads(row["receipt_json"]),
            "receipt_sha256": row["receipt_sha256"],
            "created_at": row["created_at"],
            "status": "pending_independent_verification",
            "qualified": False,
        } for row in rows]

    def artifact_paths(self, project_id: str, *, prefix: str = "", suffix: str = "",
                       limit: int = 1024) -> dict[str, Any]:
        """Bounded canonical path query; literal prefix/suffix, explicit truncation."""
        if (not isinstance(project_id, str) or not project_id
                or not isinstance(prefix, str) or not isinstance(suffix, str)
                or len(prefix) > 2000 or len(suffix) > 2000
                or type(limit) is not int or not 1 <= limit <= 4096):
            raise ValueError("bounded artifact path query required")
        with closing(self._connect()) as db, db:
            if db.execute("SELECT 1 FROM projects WHERE project_id=?", (project_id,)).fetchone() is None:
                raise KeyError(project_id)
            rows = db.execute(
                "SELECT logical_path FROM project_artifacts WHERE project_id=? "
                "AND substr(logical_path,1,?)=? AND (?='' OR substr(logical_path,-?)=?) "
                "ORDER BY logical_path LIMIT ?",
                (project_id, len(prefix), prefix, suffix, len(suffix), suffix, limit + 1),
            ).fetchall()
        return {"paths": [row["logical_path"] for row in rows[:limit]],
                "truncated": len(rows) > limit}

    def storage_inventory(self, *, limit: int = 1024) -> dict[str, Any]:
        """Bounded host-wide accounting, without reading content or reclaiming it.

        Each metadata scan retains at most ``limit`` rows. The CAS scan visits
        at most ``limit`` entries plus one truncation sentinel, in filesystem
        order. Totals are None when their coverage or required sizes are unknown.
        Known absent files contribute zero stored bytes and a missing-file count;
        unreadable/unknown file observations withhold the corresponding totals.
        SQLite reads share a snapshot; filesystem stats are separate observations.
        This is neither content verification nor a physical ownership estimate.
        """
        if type(limit) is not int or not 1 <= limit <= 4096:
            raise ValueError("storage inventory limit must be between 1 and 4096")

        def valid_size(value):
            return type(value) is int and value >= 0

        def valid_hex(value, length):
            return (isinstance(value, str) and len(value) == length
                    and all(c in "0123456789abcdef" for c in value))

        def observation(path):
            try:
                info = path.lstat()
            except FileNotFoundError:
                return ("missing", 0, 0)
            except OSError:
                return ("unreadable", 0, None)
            if not stat.S_ISREG(info.st_mode):
                return ("non_regular", 0, None)
            blocks = getattr(info, "st_blocks", None)
            return ("file", info.st_size, blocks * 512 if valid_size(blocks) else None)

        def footprint(items, complete):
            counts = {kind: sum(item[0] == kind for item in items)
                      for kind in ("file", "missing", "unreadable", "non_regular", "invalid_path")}
            size = sum(item[1] for item in items if item[0] == "file")
            allocated = sum(item[2] for item in items if item[0] == "file" and item[2] is not None)
            unavailable = sum(item[0] == "file" and item[2] is None for item in items)
            complete = complete and not any(counts[k] for k in ("unreadable", "non_regular", "invalid_path"))
            return {"files_observed": counts["file"], "bytes_observed": size,
                    "bytes": size if complete else None,
                    "allocated_bytes_observed": allocated,
                    "allocated_bytes": allocated if complete and not unavailable else None,
                    "allocation_unavailable_files": unavailable,
                    "missing_files": counts["missing"], "unreadable_files": counts["unreadable"],
                    "non_regular_entries": counts["non_regular"], "invalid_paths": counts["invalid_path"],
                    "complete": complete}

        with closing(self._connect()) as db:
            db.execute("BEGIN")

            def page(query):
                rows = db.execute(query + " LIMIT ?", (limit + 1,)).fetchall()
                return rows[:limit], len(rows) > limit

            artifacts, artifacts_truncated = page(
                "SELECT digest,size_bytes,relative_path FROM artifacts ORDER BY digest")
            current, current_truncated = page(
                "SELECT pa.digest,a.size_bytes FROM project_artifacts pa "
                "LEFT JOIN artifacts a USING(digest) ORDER BY pa.project_id,pa.logical_path")
            versions, versions_truncated = page(
                "SELECT digest,size_bytes FROM artifact_versions ORDER BY project_id,logical_path,version")
            metadata = {row["digest"]: row for row in artifacts}
            current_sizes = {row["digest"]: row["size_bytes"] for row in current}
            version_digests = {row["digest"] for row in versions}
            stored = {}
            for digest, row in metadata.items():
                if not valid_hex(digest, 64):
                    stored[digest] = ("invalid_path", 0, None)
                    continue
                expected = Path("blobs") / "sha256" / digest[:2] / digest[2:]
                if row["relative_path"] != str(expected):
                    stored[digest] = ("invalid_path", 0, None)
                    continue
                # The shard itself must be a directory, not a link to another store.
                try:
                    directory = (self.blobs / digest[:2]).lstat()
                    if not stat.S_ISDIR(directory.st_mode):
                        stored[digest] = ("non_regular", 0, None)
                        continue
                except FileNotFoundError:
                    stored[digest] = ("missing", 0, 0)
                    continue
                except OSError:
                    stored[digest] = ("unreadable", 0, None)
                    continue
                stored[digest] = observation(self.root / expected)

            # Only the existing two-level CAS layout is traversed. Unknown
            # directories and non-regular entries are reported, never followed.
            pending = [(self.blobs, 0)]
            entries = errors = unexamined_directories = 0
            cas_truncated = False
            unclassified = []
            while pending and not cas_truncated:
                directory, depth = pending.pop()
                try:
                    with os.scandir(directory) as children:
                        for entry in children:
                            if entries == limit:
                                cas_truncated = True
                                break
                            entries += 1
                            try:
                                info = entry.stat(follow_symlinks=False)
                            except OSError:
                                errors += 1
                                continue
                            if stat.S_ISDIR(info.st_mode):
                                if depth == 0 and valid_hex(entry.name, 2):
                                    pending.append((Path(entry.path), 1))
                                else:
                                    unexamined_directories += 1
                                continue
                            if not stat.S_ISREG(info.st_mode):
                                unclassified.append(("non_regular", 0, None))
                                continue
                            digest = directory.name + entry.name if depth == 1 else ""
                            if valid_hex(digest, 64):
                                known = db.execute("SELECT relative_path FROM artifacts WHERE digest=?",
                                                   (digest,)).fetchone()
                                relative = str(Path(entry.path).relative_to(self.root))
                                if known is not None and known["relative_path"] == relative:
                                    continue
                            blocks = getattr(info, "st_blocks", None)
                            unclassified.append(("file", info.st_size,
                                                 blocks * 512 if valid_size(blocks) else None))
                except OSError:
                    errors += 1

            declared = sum(row["size_bytes"] for row in artifacts if valid_size(row["size_bytes"]))
            invalid_sizes = sum(not valid_size(row["size_bytes"]) for row in artifacts)
            current_invalid = sum(not valid_size(row["size_bytes"]) for row in current)
            current_bytes = sum(row["size_bytes"] for row in current if valid_size(row["size_bytes"]))
            current_unique = sum(size for size in current_sizes.values() if valid_size(size))
            version_invalid = sum(not valid_size(row["size_bytes"]) for row in versions)
            version_bytes = sum(row["size_bytes"] for row in versions if valid_size(row["size_bytes"]))
            classification_complete = not any((artifacts_truncated, current_truncated, versions_truncated,
                                               invalid_sizes, current_invalid, version_invalid))
            classification_complete = classification_complete and version_digests <= metadata.keys()
            historical = version_digests - current_sizes.keys()
            historical_result = {"classification_complete": classification_complete,
                                 "digests": None, "declared_bytes": None, "stored": None}
            if classification_complete:
                historical_result.update(
                    digests=len(historical), declared_bytes=sum(metadata[d]["size_bytes"] for d in historical),
                    stored=footprint([stored[d] for d in historical], True))

            return {
                "schema": "merlin-storage-inventory/1", "scope": "host_registry", "limit": limit,
                "scan": {"artifacts_truncated": artifacts_truncated, "current_truncated": current_truncated,
                         "versions_truncated": versions_truncated, "cas_entries_observed": entries,
                         "cas_entries_truncated": cas_truncated, "cas_scan_errors": errors,
                         "cas_unexamined_directories": unexamined_directories},
                "registered": {
                    "digests_observed": len(artifacts), "digests": None if artifacts_truncated else len(artifacts),
                    "declared_bytes_observed": declared,
                    "declared_bytes": declared if not artifacts_truncated and not invalid_sizes else None,
                    "invalid_sizes": invalid_sizes,
                    "stored": footprint(list(stored.values()), not artifacts_truncated),
                    "size_mismatches": sum(stored[d][0] == "file" and stored[d][1] != row["size_bytes"]
                                           for d, row in metadata.items())},
                "current": {
                    "references_observed": len(current), "references": None if current_truncated else len(current),
                    "logical_bytes_observed": current_bytes,
                    "logical_bytes": current_bytes if not current_truncated and not current_invalid else None,
                    "unique_digests_observed": len(current_sizes),
                    "unique_digests": None if current_truncated else len(current_sizes),
                    "unique_declared_bytes_observed": current_unique,
                    "unique_declared_bytes": current_unique if not current_truncated and not current_invalid else None,
                    "missing_or_invalid_sizes": current_invalid},
                "versions": {
                    "references_observed": len(versions), "references": None if versions_truncated else len(versions),
                    "logical_bytes_observed": version_bytes,
                    "logical_bytes": version_bytes if not versions_truncated and not version_invalid else None,
                    "invalid_sizes": version_invalid},
                "historical_only": historical_result,
                "unclassified_cas": footprint(unclassified, not cas_truncated and not errors
                                               and not unexamined_directories),
                "sqlite_files": footprint([observation(Path(str(self.db_path) + suffix))
                                            for suffix in ("", "-journal", "-wal", "-shm")], True),
                "content_integrity_verified": False, "reclaimability_assessed": False,
                "coverage": "Configured CAS and four SQLite paths only; other root files/caches excluded. "
                            "Metadata snapshot and non-atomic filesystem observations; allocation is st_blocks*512, "
                            "not exclusive extents. Row/entry limits are not I/O deadlines.",
            }

    def inventory(self, project_id: str) -> dict[str, Any]:
        with closing(self._connect()) as db, db:
            project = db.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
            if project is None:
                raise KeyError(project_id)
            artifacts = db.execute(
                "SELECT pa.logical_path,a.digest,a.media_type,a.size_bytes,"
                "(SELECT MAX(av.version) FROM artifact_versions av "
                " WHERE av.project_id=pa.project_id AND av.logical_path=pa.logical_path) AS version "
                "FROM project_artifacts pa JOIN artifacts a USING(digest) "
                "WHERE pa.project_id=? ORDER BY pa.logical_path", (project_id,)
            ).fetchall()
        return {
            "project_id": project["project_id"], "name": project["name"],
            "version": project["version"], "metadata": json.loads(project["metadata_json"]),
            "artifacts": [dict(row) for row in artifacts],
        }

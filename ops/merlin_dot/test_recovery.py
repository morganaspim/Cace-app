import ast
from contextlib import closing
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import tempfile
import unittest
from unittest.mock import patch

from merlin.project_registry import MerlinRegistry
from dot_ai_os import recovery
from dot_ai_os.recovery import (RecoveryError, SnapshotBounds, create_snapshot,
                                restore_snapshot, verify_snapshot)


class _Reader(MerlinRegistry):
    def __init__(self, root):
        self.root = Path(root)
        self.db_path = self.root / "merlin.sqlite3"
        self.blobs = self.root / "blobs" / "sha256"

    def _connect(self):
        db = sqlite3.connect(self.db_path.as_uri() + "?mode=ro&immutable=1", uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        return db


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.registry = MerlinRegistry(self.source)
        self.registry.register_project("research", "Synthetic recovery fixture", metadata={"private": False})
        provenance = {"schema": "merlin-artifact-provenance/1", "source_repo": "fixture/recovery",
                      "source_commit": "a" * 40, "artifact_id": "test-input", "artifact_kind": "synthetic",
                      "artifact_schema": "fixture/1"}
        first = self.registry.put_artifact("research", "context/input.json", b'{"version":1}', provenance=provenance)
        self.ref1 = self.registry.artifact_ref("research", "context/input.json")
        self.registry.put_artifact("research", "context/input.json", b'{"version":2}', provenance={**provenance, "artifact_id": "test-input-v2"})
        self.ref2 = self.registry.artifact_ref("research", "context/input.json")
        self.registry.add_claim("fixture-claim", "Synthetic unverified claim", "simulated", ("Ideal fixture",))
        self.registry.relate("fixture-claim", "supported_by", first, {"scope": "fixture_only"})
        self.registry.record_capability_qualification({"receipt_id": "fixture-receipt", "capability_id": "fixture",
            "capability_version": "1", "provider": "synthetic", "model_revision": "fixture-only",
            "heldout_suite": "not-generalized", "environment_sha256": "b" * 64, "artifact_digest": first,
            "result": "passed", "signer_id": "untrusted-fixture", "signed_at": 1.0})
        self.snapshot = self.root / "snapshot"

    def state(self, root):
        return {path.relative_to(root).as_posix():
                (hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(path.stat().st_mode),
                 path.stat().st_mtime_ns, path.stat().st_ctime_ns)
                for path in root.rglob("*") if path.is_file()}

    def make_snapshot(self):
        return create_snapshot(self.source, self.snapshot)

    def blob(self, root):
        return root / "blobs" / "sha256" / self.ref1["sha256"][:2] / self.ref1["sha256"][2:]

    def reseal_manifest(self):
        raw = (self.snapshot / "manifest.json").read_bytes()
        return hashlib.sha256(raw).hexdigest()

    def test_roundtrip_preserves_history_provenance_claims_and_pending_receipts(self):
        original = self.state(self.source)
        receipt = self.make_snapshot()
        check = verify_snapshot(self.snapshot, receipt["manifest_sha256"])
        target = self.root / "restored"
        restored = restore_snapshot(self.snapshot, target, receipt["manifest_sha256"])
        self.assertEqual(original, self.state(self.source))
        self.assertEqual(receipt["inventory_sha256"], check["inventory_sha256"])
        self.assertEqual(check["inventory_sha256"], restored["inventory_sha256"])
        reader = _Reader(target)
        self.assertEqual(reader.read_artifact_ref(self.ref1)["content"], b'{"version":1}')
        self.assertEqual(reader.read_artifact_ref(self.ref2)["content"], b'{"version":2}')
        self.assertEqual(reader.resolve_artifact_ref(self.ref1)["provenance"]["artifact_id"], "test-input")
        self.assertEqual(reader.resolve_artifact_ref(self.ref2)["previous_digest"], self.ref1["sha256"])
        self.assertEqual(reader.artifact_history("research", "context/input.json"), self.registry.artifact_history("research", "context/input.json"))
        self.assertEqual(reader.capability_qualification_receipts("fixture")[0]["status"], "pending_independent_verification")
        for report in (receipt, check, restored):
            self.assertTrue(report["integrity_verified"])
            self.assertFalse(report["qualification"])
            self.assertFalse(report["promotion_authority"])
            self.assertEqual(report["table_counts"]["artifact_version_provenance"], 2)
            self.assertEqual(report["table_counts"]["claims"], 1)
            self.assertEqual(report["table_counts"]["relations"], 1)

    def test_payload_modes_are_exact_under_restrictive_umask(self):
        old = os.umask(0o077)
        try:
            receipt = self.make_snapshot()
            target = self.root / "restored"
            restore_snapshot(self.snapshot, target, receipt["manifest_sha256"])
        finally:
            os.umask(old)
        for root in (self.snapshot, target):
            for path in (root, *root.rglob("*")):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700 if path.is_dir() else 0o600)

    def test_readonly_source_files_are_never_modified_or_given_sidecars(self):
        for path in self.source.rglob("*"):
            if path.is_file():
                path.chmod(0o400)
        before = self.state(self.source)
        self.make_snapshot()
        self.assertEqual(self.state(self.source), before)
        self.assertEqual(set(path.name for path in self.source.iterdir()), {"merlin.sqlite3", "blobs"})

    def test_empty_canonical_registry_roundtrip(self):
        empty = self.root / "empty"
        MerlinRegistry(empty)
        receipt = create_snapshot(empty, self.snapshot)
        restore_snapshot(self.snapshot, self.root / "restored", receipt["manifest_sha256"])
        self.assertEqual(receipt["blob_count"], 0)

    def test_manifest_requires_the_exact_out_of_band_digest(self):
        receipt = self.make_snapshot()
        for digest in ("0" * 64, "short", receipt["manifest_sha256"].upper()):
            with self.subTest(digest=digest), self.assertRaises(RecoveryError):
                verify_snapshot(self.snapshot, digest)
        raw = json.loads((self.snapshot / "manifest.json").read_bytes())
        raw["qualification"] = True
        (self.snapshot / "manifest.json").write_bytes(recovery._json(raw))
        with self.assertRaises(RecoveryError):
            verify_snapshot(self.snapshot, self.reseal_manifest())

    def test_corrupt_or_missing_snapshot_blob_is_rejected_before_restore(self):
        receipt = self.make_snapshot()
        blob = self.blob(self.snapshot / "registry")
        raw = blob.read_bytes()
        for operation in ("corrupt", "missing"):
            if operation == "corrupt":
                blob.write_bytes(b"X" * len(raw))
            else:
                blob.unlink()
            with self.subTest(operation=operation), self.assertRaises(RecoveryError):
                restore_snapshot(self.snapshot, self.root / "restored", receipt["manifest_sha256"])
            self.assertFalse((self.root / "restored").exists())
            blob.write_bytes(raw); blob.chmod(0o600)

    def test_corrupt_database_is_rejected(self):
        receipt = self.make_snapshot()
        db = self.snapshot / "registry" / "merlin.sqlite3"
        raw = bytearray(db.read_bytes()); raw[0] = 0; db.write_bytes(raw)
        with self.assertRaises(RecoveryError):
            verify_snapshot(self.snapshot, receipt["manifest_sha256"])

    def test_missing_or_corrupt_source_blob_never_publishes_snapshot(self):
        blob = self.blob(self.source); raw = blob.read_bytes()
        blob.unlink()
        with self.assertRaises(RecoveryError):
            self.make_snapshot()
        self.assertFalse(self.snapshot.exists())
        blob.write_bytes(b"X" * len(raw))
        with self.assertRaises(RecoveryError):
            self.make_snapshot()
        self.assertFalse(self.snapshot.exists())

    def test_traversal_in_database_and_manifest_is_rejected(self):
        with closing(sqlite3.connect(self.source / "merlin.sqlite3")) as db, db:
            db.execute("UPDATE artifacts SET relative_path='../outside' WHERE digest=?", (self.ref1["sha256"],))
        with self.assertRaises(RecoveryError):
            self.make_snapshot()
        self.assertFalse(self.snapshot.exists())

    def test_rehashed_manifest_cannot_redirect_a_blob(self):
        self.make_snapshot()
        raw = json.loads((self.snapshot / "manifest.json").read_bytes())
        raw["blobs"][0]["path"] = "../../outside"
        (self.snapshot / "manifest.json").write_bytes(recovery._json(raw))
        with self.assertRaises(RecoveryError):
            verify_snapshot(self.snapshot, self.reseal_manifest())

    def test_links_and_unsafe_modes_fail_closed(self):
        blob = self.blob(self.source); raw = blob.read_bytes()
        outside = self.root / "outside"; outside.write_bytes(raw)
        blob.unlink(); blob.symlink_to(outside)
        with self.assertRaises(RecoveryError):
            self.make_snapshot()
        blob.unlink(); os.link(outside, blob)
        with self.assertRaises(RecoveryError):
            self.make_snapshot()
        blob.unlink(); blob.write_bytes(raw); blob.chmod(0o666)
        with self.assertRaises(RecoveryError):
            self.make_snapshot()
        blob.chmod(0o644)
        alias = self.root / "alias"; alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(RecoveryError):
            create_snapshot(alias, self.snapshot)

    def test_snapshot_links_extras_and_inexact_permissions_are_rejected(self):
        receipt = self.make_snapshot()
        extra = self.snapshot / "extra"; extra.write_bytes(b"unmanifested"); extra.chmod(0o600)
        with self.assertRaises(RecoveryError):
            verify_snapshot(self.snapshot, receipt["manifest_sha256"])
        extra.unlink()
        manifest = self.snapshot / "manifest.json"; manifest.chmod(0o644)
        with self.assertRaises(RecoveryError):
            verify_snapshot(self.snapshot, receipt["manifest_sha256"])
        manifest.chmod(0o600)
        blob = self.blob(self.snapshot / "registry"); raw = blob.read_bytes()
        blob.unlink(); blob.symlink_to(self.blob(self.source))
        with self.assertRaises(RecoveryError):
            verify_snapshot(self.snapshot, receipt["manifest_sha256"])

    def test_wal_and_even_empty_journal_sidecars_are_rejected(self):
        journal = self.source / "merlin.sqlite3-journal"; journal.write_bytes(b"")
        with self.assertRaises(RecoveryError):
            self.make_snapshot()
        journal.unlink()
        with closing(sqlite3.connect(self.source / "merlin.sqlite3")) as db:
            db.execute("PRAGMA journal_mode=WAL")
        with self.assertRaises(RecoveryError):
            self.make_snapshot()
        self.assertFalse(self.snapshot.exists())

    def test_existing_destination_relative_or_nested_paths_are_refused(self):
        self.snapshot.mkdir()
        with self.assertRaises(RecoveryError):
            self.make_snapshot()
        self.assertEqual(list(self.snapshot.iterdir()), [])
        self.snapshot.rmdir()
        with self.assertRaises(RecoveryError):
            create_snapshot(self.source, self.source / "nested")
        with self.assertRaises(RecoveryError):
            create_snapshot(Path("relative"), self.snapshot)
        receipt = self.make_snapshot()
        target = self.root / "existing"; target.mkdir(); (target / "sentinel").write_bytes(b"preserve")
        with self.assertRaises(RecoveryError):
            restore_snapshot(self.snapshot, target, receipt["manifest_sha256"])
        self.assertEqual((target / "sentinel").read_bytes(), b"preserve")

    def test_resource_ceilings_and_invalid_bounds(self):
        for changes in ({"max_db_bytes": 1}, {"max_blob_bytes": 1}, {"max_total_bytes": 1},
                        {"max_blobs": 1}, {"max_rows": 1}, {"max_manifest_bytes": 10}):
            with self.subTest(changes=changes), self.assertRaises(RecoveryError):
                create_snapshot(self.source, self.snapshot, replace(SnapshotBounds(), **changes))
            self.assertFalse(self.snapshot.exists())
        for changes in ({"max_rows": True}, {"max_db_bytes": 0}, {"max_seconds": float("nan")}, {"max_seconds": 301}):
            with self.subTest(changes=changes), self.assertRaises(RecoveryError):
                SnapshotBounds(**changes)
        with patch.object(recovery.time, "monotonic", side_effect=(0.0, 2.0)):
            with self.assertRaises(RecoveryError):
                create_snapshot(self.source, self.snapshot, SnapshotBounds(max_seconds=1))

    def test_schema_tamper_and_broken_foreign_key_are_refused(self):
        with closing(sqlite3.connect(self.source / "merlin.sqlite3")) as db, db:
            db.execute("CREATE TABLE unknown_state(value TEXT)")
        with self.assertRaises(RecoveryError):
            self.make_snapshot()
        with closing(sqlite3.connect(self.source / "merlin.sqlite3")) as db, db:
            db.execute("DROP TABLE unknown_state")
            db.execute("UPDATE project_artifacts SET project_id='missing'")
        with self.assertRaises(RecoveryError):
            self.make_snapshot()

    def test_source_change_during_copy_leaves_only_quarantine(self):
        real_read = recovery._read_file; changed = []
        def read(path, *args, **kwargs):
            result = real_read(path, *args, **kwargs)
            if path == self.blob(self.source) and kwargs.get("destination") is not None and not changed:
                self.registry.add_claim("concurrent-writer", "Writer violates quiescence", "reported")
                changed.append(True)
            return result
        with patch.object(recovery, "_read_file", side_effect=read):
            with self.assertRaises(RecoveryError):
                self.make_snapshot()
        self.assertEqual(changed, [True]); self.assertFalse(self.snapshot.exists())
        self.assertTrue(list(self.root.glob(".merlin-recovery-quarantine-*")))

    def test_atomic_publication_never_overwrites_racing_destination(self):
        publish = recovery._publish
        def race(stage, dest):
            dest.mkdir(); (dest / "sentinel").write_bytes(b"preserve")
            return publish(stage, dest)
        with patch.object(recovery, "_publish", side_effect=race):
            with self.assertRaises(RecoveryError):
                self.make_snapshot()
        self.assertEqual((self.snapshot / "sentinel").read_bytes(), b"preserve")

    def test_fsync_failure_after_rename_returns_output_to_quarantine(self):
        sync = recovery._sync_dir; failed = []
        def fail(path):
            if path == self.root and self.snapshot.exists() and not failed:
                failed.append(True); raise OSError("injected parent fsync error")
            return sync(path)
        with patch.object(recovery, "_sync_dir", side_effect=fail):
            with self.assertRaises(RecoveryError):
                self.make_snapshot()
        self.assertEqual(failed, [True]); self.assertFalse(self.snapshot.exists())
        self.assertTrue(list(self.root.glob(".merlin-recovery-quarantine-*")))

    def test_python_39_grammar(self):
        ast.parse(Path(recovery.__file__).read_text(), feature_version=(3, 9))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""No-network negative controls for Merlin rootless fixed-model integrity gate."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).with_name("nonroot_model_integrity.py")
spec = importlib.util.spec_from_file_location("pinned_nonroot_integrity_under_test", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IntegrityControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="merlin-nonroot-model-tests-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "sample"
        self.data = b"merlin bytes for pinned nonroot model regression\n"
        self.path.write_bytes(self.data)
        self.path.chmod(0o600)

    def digest(self, expected_hash=None, size=None, path=None):
        return module.full_digest(
            self.path if path is None else path,
            len(self.data) if size is None else size,
            hashlib.sha256(self.data).hexdigest() if expected_hash is None else expected_hash,
            seconds=3, owner=os.geteuid())

    def test_valid_file_bytes_and_inode(self):
        result = self.digest()
        self.assertEqual(result["bytes"], len(self.data))
        self.assertEqual(result["sha256"], hashlib.sha256(self.data).hexdigest())

    def test_content_substitution_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
            self.digest(expected_hash="0" * 64)

    def test_truncation_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "length differs"):
            self.digest(size=len(self.data) + 1)

    def test_symlink_rejected_before_open(self):
        target = Path(self.temp.name) / "link"
        target.symlink_to(self.path)
        with self.assertRaisesRegex(RuntimeError, "file ownership, type"):
            self.digest(path=target)

    def test_group_writable_file_rejected(self):
        self.path.chmod(0o620)
        with self.assertRaisesRegex(RuntimeError, "write boundary"):
            self.digest()

    def test_directory_input_rejected(self):
        target = Path(self.temp.name) / "directory"
        target.mkdir()
        with self.assertRaisesRegex(RuntimeError, "file ownership, type"):
            self.digest(path=target)

    def test_wrong_owner_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "file ownership"):
            module.regular(self.path, len(self.data), expected_uid=os.geteuid() + 1000)

    def test_duplicate_manifest_json_key_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "duplicate JSON"):
            json.loads('{"a":1,"a":2}', object_pairs_hook=module.unique)

    def test_invalid_manifest_role_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "manifest fixed role differs"):
            module.validated_release_paths({"schema":"merlin-local-model-provider/1",
                 "status":"ready","qualification":False,"model":"attacker"})

    def test_invalid_model_source_revision_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "fixed model or runtime provenance differs"):
            module.validated_release_paths({
                "schema":"merlin-local-model-provider/1","status":"ready",
                "qualification":False,"model":module.MODEL_ALIAS,
                "model_artifact":{"sha256":module.MODEL_SHA,
                    "size_bytes":module.MODEL_BYTES,"repository_revision":"moving"},
                "runtime":{"source_commit":module.SOURCE_COMMIT}})

    def test_invalid_model_release_path_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "model release directory differs"):
            module.validated_release_paths({
                "schema":"merlin-local-model-provider/1","status":"ready",
                "qualification":False,"model":module.MODEL_ALIAS,
                "model_artifact":{"sha256":module.MODEL_SHA,
                    "size_bytes":module.MODEL_BYTES,"repository_revision":module.REVISION,
                    "path":"/tmp/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"},
                "runtime":{"source_commit":module.SOURCE_COMMIT,
                    "binary_sha256":"a"*64,
                    "binary_path":"/tmp/llama-server"}})

    def test_bad_binary_hash_string_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "lacks exact binary identity"):
            module.validated_release_paths({
                "schema":"merlin-local-model-provider/1","status":"ready",
                "qualification":False,"model":module.MODEL_ALIAS,
                "model_artifact":{"sha256":module.MODEL_SHA,
                    "size_bytes":module.MODEL_BYTES,"repository_revision":module.REVISION,
                    "path":"/tmp/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"},
                "runtime":{"source_commit":module.SOURCE_COMMIT,
                    "binary_sha256":"not-a-digest","binary_path":"/tmp/llama-server"}})


if __name__ == "__main__":
    unittest.main()

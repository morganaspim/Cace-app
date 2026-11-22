"""Exercise evidence binding using local data; no runner, token or host changes."""
import base64
from copy import deepcopy
from email.message import Message
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import zipfile

import run_operation
import validation_evidence as ve


def git_blob(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def archive(entries):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        for name, value in entries:
            z.writestr(name, value)
    return stream.getvalue()


class ValidationEvidenceTest(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"GITHUB_REF": "refs/heads/merlin/dot-ops/test", "GITHUB_SHA": "b"*40,
            "GITHUB_RUN_ID": "99", "GITHUB_TOKEN": "controlled-local-placeholder"})
        env.start(); self.addCleanup(env.stop)
        self.run_id = 41
        self.commit = "a"*40
        self.source = {"merlin.py": "local-fixture"}
        self.bundle = b"local bundle only"
        self.blob = git_blob(self.bundle)
        self.digest = hashlib.sha256(self.bundle).hexdigest()
        self.req = {"operation": "deploy", "request_id": "local", "validation_run_id": self.run_id,
                    "validation_commit": self.commit}
        self.prior = {"schema": "merlin-dot-ops-request-v1", "created_at": "2026-11-17T10:00:00Z",
                      "operation": "validate", "request_id": "9b3d20da-ce48-4601-b1e0-7f3fa88ccf35"}
        self.branch = "merlin/dot-ops/test"
        self.producer = "f"*40
        repo = {"full_name": ve.REPOSITORY, "id": 2}
        self.run = {"id": 41, "event": "push", "run_attempt": 1, "head_sha": self.commit,
                    "path": ve.WORKFLOW, "head_branch": self.branch, "repository": repo,
                    "head_repository": repo.copy(), "status": "completed", "conclusion": "success"}
        self.art = {"id": 10, "expired": False, "name": "merlin-dot-operation-41-1",
                    "workflow_run": {"id": 41, "head_sha": self.commit, "head_branch": self.branch,
                                     "repository_id": 2, "head_repository_id": 2}}
        self.receipt = {"schema": "merlin-dot-operation-receipt/1", "operation": "validate", "status": "succeeded",
                        "runner": "cace-oci-a1", "request_id": self.prior["request_id"], "bundle_git_blob": self.blob,
                        "bundle_sha256": self.digest, "source_files": self.source, "run_id": "41",
                        "workflow_commit": self.commit, "host_configuration_changed": False, "qualification": False,
                        "promotion_authority": False, "tests": {"tests": 116, "errors": 0, "failures": 0,
                                                              "skipped": 0, "passed": True}}
        self.entries = None
        self.archive_override = None
        self.list_size = 1

    def response(self, path):
        prior_bytes = json.dumps(self.prior).encode()
        prior_blob = git_blob(prior_bytes)
        archive_bytes = archive(self.entries if self.entries is not None else
                                [("operation-receipt.json", json.dumps(self.receipt)), ("validation-tests.txt", "ok")])
        self.download_bytes = archive_bytes
        file = {"status": "added", "filename": "merlin/dot-requests/" + self.prior["request_id"] + ".json",
                "sha": prior_blob}
        if path == f"actions/runs/{self.run_id}": return self.run
        if path == "commits/" + self.commit: return {"sha": self.commit, "files": [file]}
        if path == f"contents/{ve.WORKFLOW}?ref={self.commit}": return {"sha": self.producer}
        if path == f"contents/{ve.WORKFLOW}?ref=" + os.environ["GITHUB_SHA"]: return {"sha": "f"*40}
        if path == "git/blobs/" + prior_blob:
            return {"sha": prior_blob, "encoding": "base64", "size": len(prior_bytes),
                    "content": base64.encodebytes(prior_bytes).decode()}
        if path == "git/blobs/" + self.blob:
            return {"sha": self.blob, "encoding": "base64", "content": base64.b64encode(self.bundle).decode()}
        if path == "actions/runs/41/artifacts?name=merlin-dot-operation-41-1&per_page=2":
            art = {"size_in_bytes": len(archive_bytes), "digest": "sha256:"+hashlib.sha256(archive_bytes).hexdigest(),
                   **self.art}
            return {"total_count": self.list_size, "artifacts": [art]*self.list_size}
        raise AssertionError("unexpected fixture API request")

    def check(self):
        return ve.check_validation(self.req, self.response, self.blob, self.digest, self.source, 110,
                                   lambda identifier, size: self.archive_override or self.download_bytes)

    def test_valid_control_retains_run_attempt_receipt_and_package_pin(self):
        result = self.check()
        self.assertEqual(result["bundle_sha256"], self.digest)
        self.assertEqual(result["tests_passed"], 116)
        self.assertEqual(result["validation_run_attempt"], 1)
        self.assertEqual(result["receipt_sha256"], hashlib.sha256(json.dumps(self.receipt).encode()).hexdigest())
        self.producer = ve.REVIEWED_PRIOR_WORKFLOW
        self.assertEqual(self.check()["workflow_git_blob"], ve.REVIEWED_PRIOR_WORKFLOW)

    def test_wrong_operation_and_unreviewed_workflow(self):
        self.prior["operation"] = "validate_learning"
        with self.assertRaisesRegex(ValueError, "prior request must be validate"): self.check()
        self.prior["operation"] = "validate"; self.producer = "1"*40
        with self.assertRaisesRegex(ValueError, "workflow definition"): self.check()

    def test_run_and_artifact_identity(self):
        for key, value in (("head_sha", "e"*40), ("head_branch", "merlin/dot-ops/other"),
                           ("conclusion", "failure"), ("id", 7), ("event", "pull_request")):
            with self.subTest(key=key), patch.dict(self.run, {key: value}), self.assertRaises(ValueError):
                self.check()
        for key, value in (("expired", True), ("name", "merlin-dot-operation-41-2"),
                           ("workflow_run", {"id": 7}), ("size_in_bytes", 2), ("digest", "sha256:"+"0"*64)):
            with self.subTest(key=key), patch.dict(self.art, {key: value}), self.assertRaises(ValueError):
                self.check()

    def test_missing_ambiguous_malformed_and_corrupt_evidence(self):
        for n in (0,2):
            self.list_size=n
            with self.assertRaises(ValueError): self.check()
        self.list_size=1
        for entries in ([], [("nested/operation-receipt.json", "{}")],
                        [("operation-receipt.json", '{"operation":"validate","operation":"inspect"}')],
                        [("operation-receipt.json", "X"*(ve.MAX_RECEIPT+1))]):
            self.entries=entries
            with self.assertRaises(ValueError): self.check()
        self.entries=None;self.archive_override=b"wrong bytes"
        with self.assertRaisesRegex(ValueError, "digest or size"): self.check()

    def test_wrong_source_package_receipt_and_test_state(self):
        for key, value in (("workflow_commit", "0"*40), ("request_id", "other"), ("operation", "inspect"),
                           ("bundle_git_blob", "9"*40), ("bundle_sha256", "0"*64), ("source_files", {}),
                           ("promotion_authority", 0), ("host_configuration_changed", True), ("status", "failed")):
            with self.subTest(key=key), patch.dict(self.receipt, {key: value}), self.assertRaises(ValueError):
                self.check()
        for key,value in (("passed", 1),("tests",109),("errors",1),("skipped",1),("failures",False)):
            with self.subTest(key=key), patch.dict(self.receipt["tests"], {key:value}), self.assertRaises(ValueError):
                self.check()

    def test_redirect_uses_fresh_request_without_credentials(self):
        opener=Mock(); headers=Message()
        headers["Location"]="https://example.blob.core.windows.net/fixed/controlled"
        redirect=urllib.error.HTTPError("https://api.github.com",302,"found",headers,BytesIO())
        opener.open.side_effect=[redirect,BytesIO(b"abc")]
        with patch.object(ve.urllib.request,"build_opener",return_value=opener):
            self.assertEqual(ve._download(41,3),b"abc")
        first=opener.open.call_args_list[0].args[0];second=opener.open.call_args_list[1].args[0]
        self.assertIn("Authorization",first.headers);self.assertNotIn("Authorization",second.headers)

    def test_real_operation_entry_rejects_each_guarded_operation_before_installer(self):
        self.prior["operation"]="inspect"
        module=Path(ve.__file__).read_bytes()
        test_process=Mock(returncode=0,stdout='MERLIN_TEST_RESULT={"passed":true}',stderr='')
        installer={"unpack_verified":lambda *args: {"files":self.source}}
        for operation in ("deploy","resume_research","upgrade_research"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as tmp:
                fetch=Mock(return_value=(module,git_blob(module)))
                with patch.object(run_operation.subprocess,"run",return_value=test_process) as run:
                    with self.assertRaisesRegex(ValueError,"prior request must be validate"):
                        run_operation.run_operation({**self.req,"operation":operation},self.response,fetch,installer,
                                                    self.blob,self.digest,Path(tmp))
                fetch.assert_called_once_with("ops/merlin_dot/validation_evidence.py")
                self.assertTrue(all(call.args[0][0]!="/usr/bin/sudo" for call in run.call_args_list))


if __name__=="__main__":
    unittest.main()

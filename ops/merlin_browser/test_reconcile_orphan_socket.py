"""Synthetic negative and positive controls for read-only browser state assessment."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reconcile_orphan_socket import (EXPECTED_PATHS, SOCKET, assess, from_json_bytes, main)

RUN_ID = 45045149558
COMMIT = "f4f7a4799c8a309a277b879f38209b3568d87c6c"


def observed():
    paths = []
    for path in EXPECTED_PATHS:
        value = {"path": path, "follows_symlinks": False,
                 "status": "absent", "exists": False}
        if path == SOCKET:
            value.update({"status": "present", "exists": True,
                          "metadata": {"type": "socket", "uid": 0, "gid": 1000,
                                       "mode": "0o660", "inode": 2482964, "nlink": 1,
                                       "dev": 28, "ctime_ns": 1795293187100973755,
                                       "mtime_ns": 1795293187100973755}})
        paths.append(value)
    return {
        "schema": "merlin-browser-state-inspection/1",
        "operation": "inspect-state-44956695079",
        "status": "inspection_complete", "complete": True, "acceptance_allowed": False,
        "qualification": False,
        "application_mutations": 0, "connections": 0,
        "acquisitions": 0, "model_calls": 0,
        "execution": {"run_id": RUN_ID, "workflow_commit": COMMIT,
                      "repository": "morganaspim/Cace-app",
                      "runner": "cace-oci-a1", "run_attempt": 1},
        "paths": paths,
        "all_six_absent_snapshot": False,
        "successor_marker": {"status": "absent", "verified": False},
        "supervisor": {"status": "observed", "properties": {
            "ActiveState": "inactive", "SubState": "dead",
            "UnitFileState": "disabled", "MainPID": "0", "User": "root"}},
        "unix_socket_table": {"status": "observed", "matching_path": SOCKET,
                              "matches": 0, "rows": []},
    }


def check(item):
    return assess(item, expected_run_id=RUN_ID, expected_workflow_commit=COMMIT)


class ReconciliationPreflightTests(unittest.TestCase):
    def test_exact_observation_is_candidate_not_authorization(self):
        result = check(observed())
        self.assertEqual(result["status"], "candidate_for_separate_locked_reinspection")
        self.assertFalse(result["authority_granted"])
        self.assertFalse(result["may_unlink_socket"])
        self.assertFalse(result["native_browser_qualified"])
        self.assertEqual(result["host_mutations"], 0)
        self.assertIn("operation.lock", result["next_gate"])

    def test_immutable_run_and_source_identity_required(self):
        for field, value in (("run_id", RUN_ID + 1), ("workflow_commit", "f" * 40),
                             ("repository", "different/repo"), ("runner", "other-host"),
                             ("run_attempt", 2)):
            with self.subTest(field=field):
                candidate = observed()
                candidate["execution"][field] = value
                self.assertEqual(check(candidate)["status"], "blocked")
        self.assertEqual(assess(observed(), expected_run_id=RUN_ID + 1,
                                expected_workflow_commit=COMMIT)["status"], "blocked")

    def test_active_service_or_socket_listener_is_blocked(self):
        for key, value in (("ActiveState", "active"), ("SubState", "running"),
                           ("UnitFileState", "enabled"), ("MainPID", "43")):
            with self.subTest(key=key):
                candidate = observed()
                candidate["supervisor"]["properties"][key] = value
                self.assertEqual(check(candidate)["status"], "blocked")
        for bad in (1, None, False):
            with self.subTest(matches=bad):
                candidate = observed()
                candidate["unix_socket_table"]["matches"] = bad
                if bad == 1:
                    candidate["unix_socket_table"]["rows"] = ["active"]
                self.assertEqual(check(candidate)["status"], "blocked")

    def test_wrong_socket_inode_or_owner_or_shape_is_blocked(self):
        for key, bad in (("type", "file"), ("uid", 1000), ("gid", 0),
                         ("mode", "0o777"), ("inode", 0), ("nlink", 2)):
            with self.subTest(key=key):
                candidate = observed()
                next(p for p in candidate["paths"] if p["path"] == SOCKET)["metadata"][key] = bad
                self.assertEqual(check(candidate)["status"], "blocked")

    def test_boolean_integer_substitution_rejected_at_all_identity_boundaries(self):
        for value in (True, False):
            c = observed()
            c["unix_socket_table"]["matches"] = value
            self.assertEqual(check(c)["status"], "blocked")
            c = observed()
            c["execution"]["run_attempt"] = value
            self.assertEqual(check(c)["status"], "blocked")
            for member in ("uid", "gid", "inode", "nlink"):
                c = observed()
                item = next(p for p in c["paths"] if p["path"] == SOCKET)
                item["metadata"][member] = value
                self.assertEqual(check(c)["status"], "blocked")
            c = observed()
            c["execution"]["run_id"] = value
            self.assertEqual(check(c)["status"], "blocked")

    def test_no_path_substitution_duplicate_or_symlink(self):
        for damage in ("path_substitution", "duplicate", "follow_symlink", "missing"):
            with self.subTest(damage=damage):
                candidate = observed()
                if damage == "path_substitution":
                    candidate["paths"][0]["path"] = "/tmp/not-the-release"
                elif damage == "duplicate":
                    candidate["paths"][0] = copy.deepcopy(candidate["paths"][1])
                elif damage == "follow_symlink":
                    candidate["paths"][4]["follows_symlinks"] = True
                else:
                    candidate["paths"].pop()
                self.assertEqual(check(candidate)["status"], "blocked")

    def test_no_auto_repair_from_nonempty_released_or_ledger_state(self):
        for index in (0, 1, 2, 3, 5):
            with self.subTest(index=index):
                candidate = observed()
                candidate["paths"][index]["status"] = "present"
                candidate["paths"][index]["exists"] = True
                self.assertEqual(check(candidate)["status"], "blocked")
        c = observed()
        c["successor_marker"]["status"] = "observed"
        self.assertEqual(check(c)["status"], "blocked")

    def test_incomplete_or_authority_promoted_receipt_rejected(self):
        for field, value in (("complete", False), ("status", "inspection_incomplete"),
                             ("acceptance_allowed", True), ("qualification", True),
                             ("application_mutations", 1), ("connections", 1),
                             ("model_calls", 1), ("acquisitions", 1)):
            with self.subTest(field=field):
                candidate = observed()
                candidate[field] = value
                self.assertEqual(check(candidate)["status"], "blocked")

    def test_missing_or_malformed_fields_fail_closed(self):
        for field in ("paths", "supervisor", "unix_socket_table", "execution"):
            with self.subTest(field=field):
                candidate = observed()
                candidate.pop(field)
                self.assertEqual(check(candidate)["status"], "blocked")
        self.assertEqual(check({"schema": "wrong"})["status"], "blocked")

    def test_pair_accepts_only_stable_read_only_evidence(self):
        from reconcile_orphan_socket import assess_observation_pair
        first = observed()
        first["observed_at"] = "2026-11-22T16:40:38Z"
        second = copy.deepcopy(first)
        second["execution"]["run_id"] = 45050760629
        second["execution"]["workflow_commit"] = "0344e0a5d69850b400454dd085330788e4acc68e"
        second["observed_at"] = "2026-11-22T17:40:33Z"
        first_raw = json.dumps(first, sort_keys=True).encode()
        second_raw = json.dumps(second, sort_keys=True).encode()
        result = assess_observation_pair(first_raw, second_raw,
            expected_first=(RUN_ID, COMMIT), expected_second=(
                45050760629, "0344e0a5d69850b400454dd085330788e4acc68e"),
            first_sha256=hashlib.sha256(first_raw).hexdigest(),
            second_sha256=hashlib.sha256(second_raw).hexdigest())
        self.assertEqual(result["status"], "stable_candidate_for_locked_reinspection")
        self.assertEqual(result["consistent_observations"], True)
        self.assertFalse(result["authority_granted"])
        self.assertFalse(result["may_unlink_socket"])
        self.assertEqual(result["host_mutations"], 0)

    def test_pair_rejects_socket_replacement_and_service_drift(self):
        from reconcile_orphan_socket import assess_observation_pair
        first = observed()
        first["observed_at"] = "2026-11-22T16:40:38Z"
        second = copy.deepcopy(first)
        second["execution"]["run_id"] = 45050760629
        second["execution"]["workflow_commit"] = "0344e0a5d69850b400454dd085330788e4acc68e"
        second["observed_at"] = "2026-11-22T17:40:33Z"
        def run_pair(candidate):
            a = json.dumps(first, sort_keys=True).encode()
            b = json.dumps(candidate, sort_keys=True).encode()
            return assess_observation_pair(a, b, expected_first=(RUN_ID, COMMIT),
                expected_second=(45050760629, "0344e0a5d69850b400454dd085330788e4acc68e"),
                first_sha256=hashlib.sha256(a).hexdigest(),
                second_sha256=hashlib.sha256(b).hexdigest())
        for key in ("inode", "dev", "ctime_ns", "mtime_ns"):
            with self.subTest(key=key):
                c = copy.deepcopy(second)
                next(p for p in c["paths"] if p["path"] == SOCKET)["metadata"][key] = (
                    42 if key != "dev" else 29)
                self.assertEqual(run_pair(c)["status"], "blocked")
        c = copy.deepcopy(second)
        c["supervisor"]["properties"]["Result"] = "failed"
        self.assertEqual(run_pair(c)["status"], "blocked")
        c = copy.deepcopy(second)
        c["observed_at"] = "2026-11-22T15:40:00Z"
        self.assertEqual(run_pair(c)["status"], "blocked")

    def test_pair_refuses_checksum_ambiguity_and_reused_run(self):
        from reconcile_orphan_socket import assess_observation_pair
        first = observed()
        first["observed_at"] = "2026-11-22T16:40:38Z"
        raw = json.dumps(first).encode()
        def call(**changes):
            kw={"expected_first":(RUN_ID, COMMIT),
                "expected_second":(RUN_ID, COMMIT),
                "first_sha256":hashlib.sha256(raw).hexdigest(),
                "second_sha256":hashlib.sha256(raw).hexdigest()}
            kw.update(changes)
            return assess_observation_pair(raw, raw, **kw)
        self.assertEqual(call()["status"], "blocked")
        with self.assertRaises(ValueError):
            call(first_sha256="0" * 64)
        with self.assertRaises(ValueError):
            assess_observation_pair(raw + b" " * (256 * 1024), raw,
                expected_first=(RUN_ID, COMMIT), expected_second=(RUN_ID, COMMIT),
                first_sha256=hashlib.sha256(raw).hexdigest(),
                second_sha256=hashlib.sha256(raw).hexdigest())

    def test_json_bytes_bound_and_duplicate_keys_rejected(self):
        source = json.dumps(observed(), sort_keys=True).encode()
        result = from_json_bytes(source, expected_run_id=RUN_ID,
                                 expected_workflow_commit=COMMIT)
        self.assertEqual(result["source_receipt_sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(result["status"], "candidate_for_separate_locked_reinspection")
        for value in (b'', b' ' * (256 * 1024 + 1), b'[]',
                      b'{"schema":"a","schema":"b"}'):
            with self.subTest(size=len(value)):
                if value == b'[]':
                    self.assertEqual(from_json_bytes(value, expected_run_id=RUN_ID,
                                     expected_workflow_commit=COMMIT)["status"], "blocked")
                else:
                    with self.assertRaises((ValueError, json.JSONDecodeError)):
                        from_json_bytes(value, expected_run_id=RUN_ID,
                                        expected_workflow_commit=COMMIT)

    def test_cli_creates_offline_report_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "source.json"
            out = root / "result.json"
            src.write_bytes(json.dumps(observed()).encode())
            self.assertEqual(main(["--input", str(src), "--output", str(out),
                                   "--expected-run-id", str(RUN_ID),
                                   "--expected-workflow-commit", COMMIT]), 0)
            result = json.loads(out.read_text())
            self.assertFalse(result["authority_granted"])
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["result.json", "source.json"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

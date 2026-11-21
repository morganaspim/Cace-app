"""Synthetic controller controls; no OCI access or actual inference."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

import accept as a
import inspect_provider_readonly as root_probe

HERE = Path(__file__).resolve().parent


def fixture_root_proof():
    service = {"unit": "merlin-model-provider.service", "unit_sha256": a.UNIT_SHA256,
               "argv_sha256": a.ARGV_SHA256, "mapped_model_sha256": a.MODEL_SHA256,
               "active_state": "active", "sub_state": "running", "user": "merlin-model",
               "group": "merlin-model", "uid": 981, "gid": 981, "main_pid": 2623747,
               "process_start_ticks": "579375053", "network_namespace": "net:[4026531840]",
               "private_network": False, "restrict_address_families": ["AF_INET", "AF_UNIX"],
               "actual_cgroup": {"cpu.max": "150000 100000", "memory.max": "3221225472",
                                 "memory.swap.max": "0", "pids.max": "32"}}
    return {"schema": "merlin-studio-root-provider-inspection/1", "passed": True,
            "inspector_sha256": root_probe.INSPECTOR_SHA256, "source_entry_point": "inspect_ready",
            "model_generation_calls": 0, "file_writes": 0, "service_mutations": False,
            "inspection": {"schema": "merlin-local-model-inspect/1", "status": "ready",
                           "manifest_sha256": a.MANIFEST_SHA256,
                           "bootstrap_receipt_sha256": a.BOOTSTRAP_RECEIPT_SHA256,
                           "inference_requests": 0, "qualification": False, "service": service}}


class AcceptanceControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.request = {"schema": "merlin-studio-model-acceptance-request/1",
                        "request_id": str(uuid.uuid4()), "operation": a.OPERATION,
                        "created_at": "2026-11-21T23:00:00Z"}
        self.execution = {"repository": a.OPS_REPOSITORY, "ref": a.OPS_REF,
                          "runner": "cace-oci-a1", "uid": 1000, "machine": "aarch64", "system": "Linux",
                          "run_id": 1, "run_attempt": 1, "workflow_commit": "a" * 40}

    def tearDown(self):
        self.temp.cleanup()

    def test_request_cannot_expand_prompt_budget_authority_or_retry(self):
        a.validate_request(self.request, self.execution)
        for values in ({"operation": "install"}, {"prompt": "other"}, {"model": "other"}, {"max_calls": 3}):
            with self.assertRaises(a.AcceptanceError):
                a.validate_request(dict(self.request, **values), self.execution)
        for values in ({"run_attempt": 2}, {"uid": 0}, {"run_id": True}, {"runner": "other"}):
            with self.assertRaises(a.AcceptanceError):
                a.validate_request(self.request, dict(self.execution, **values))

    def test_assets_match_frozen_exact_source(self):
        support, values = a.load_assets(HERE)
        self.assertEqual(support["PRODUCT_COMMIT"], a.PRODUCT_COMMIT)
        self.assertEqual(hashlib.sha256(values["frozen_provider_inspector.py"]).hexdigest(), root_probe.INSPECTOR_SHA256)
        self.assertEqual(support["TOKEN_REQUEST_SHA256"], hashlib.sha256(values["initial-model-request.json"]).hexdigest())

    def test_root_wrapper_rejects_mutation_and_arbitrary_command(self):
        for argv in (["/usr/bin/systemctl", "restart", root_probe.UNIT], ["id"], ["/bin/sh", "-c", "id"]):
            with patch.object(subprocess, "run", side_effect=AssertionError("must not execute")):
                with self.assertRaises(root_probe.InspectionError):
                    root_probe.readonly_command(argv)
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"ActiveState=active\n", b"")) as call:
            self.assertEqual(root_probe.readonly_command(root_probe.READ_ONLY_ARGV), b"ActiveState=active\n")
            self.assertEqual(call.call_args.kwargs["timeout"], 5)
            self.assertNotIn("GITHUB_TOKEN", call.call_args.kwargs["env"])

    def test_frozen_inspector_hash_and_denied_effect_entrypoints(self):
        namespace = root_probe.load_inspector(HERE / "frozen_provider_inspector.py")
        for name in ("run", "install", "download", "smoke", "write_new", "rollback"):
            with self.assertRaises(root_probe.InspectionError):
                namespace[name]()
        corrupt = self.root / "frozen_provider_inspector.py"
        corrupt.write_bytes((HERE / "frozen_provider_inspector.py").read_bytes() + b"\n")
        with self.assertRaises(root_probe.InspectionError):
            root_probe.load_inspector(corrupt)

    def test_process_proof_requires_live_binding_and_fixed_limits(self):
        valid = fixture_root_proof()
        a.validate_root_receipt(valid)
        for key, value in (("main_pid", 0), ("argv_sha256", "0" * 64), ("mapped_model_sha256", "0" * 64),
                           ("uid", 1000), ("actual_cgroup", {}), ("process_start_ticks", "")):
            changed = copy.deepcopy(valid)
            changed["inspection"]["service"][key] = value
            with self.assertRaises(a.AcceptanceError):
                a.validate_root_receipt(changed)

    def test_after_snapshot_rejects_a_restarted_provider(self):
        before = fixture_root_proof()
        after = copy.deepcopy(before)
        self.assertTrue(a.matching_after(before, after))
        after["inspection"]["service"]["main_pid"] += 1
        self.assertFalse(a.matching_after(before, after))

    def test_template_token_count_is_typed_and_reserves_context(self):
        for count, allowed in ((1920, True), (1921, False), (True, False), (0, False)):
            values = iter([{"status": "ok"}, {"data": [{"id": a.MODEL_ID}]},
                           {"object": "response.input_tokens", "input_tokens": count}])
            v = {"local_json": lambda *args: next(values)}
            with self.subTest(count=count):
                if allowed:
                    result = a.inspect_transport(v, b"fixture")
                    self.assertEqual(result["generation_calls"], 0)
                    self.assertEqual(result["tokenization_calls"], 1)
                else:
                    with self.assertRaises(a.AcceptanceError):
                        a.inspect_transport(v, b"fixture")

    def fake_support(self, python_passed=False, emit_receipt=True, include_counter=True):
        python = {"passed": python_passed, "selected": {"version": [3, 12, 0], "executable": sys.executable}}
        assets = {"source-pins.json": b'{"files":{}}', "product-source.zip": b'fixture', "initial-model-request.json": b'fixture'}
        def extract(members, target):
            target.mkdir()
        def harness(argv, **kwargs):
            result_dir = Path(argv[argv.index("--evidence-dir") + 1])
            result_dir.mkdir()
            if emit_receipt:
                payload = {"passed": True, "real_model_inference_observed": True}
                if include_counter:
                    payload["generation_requests_attempted"] = 2
                (result_dir / "acceptance-result.json").write_text(json.dumps(payload))
            return {"passed": True}
        return {"parse_json": json.loads, "validate_bundle": lambda *args: {}, "extract_bundle": extract,
                "child_env": lambda *args: {}, "inspect_python": lambda *args: python,
                "run_process": harness, "read_small": lambda path, *args: path.read_bytes()}, assets

    def test_missing_python_stops_before_root_probe_and_generation(self):
        with patch.object(a, "load_assets", return_value=self.fake_support()), \
             patch.object(a, "inspect_provider", side_effect=AssertionError("no root probe")):
            receipt = a.run(self.request, self.execution, HERE, self.root)
        self.assertEqual(receipt["status"], "blocked")
        self.assertEqual(receipt["generation_requests_attempted"], 0)
        self.assertFalse(receipt["real_model_inference_observed"])

    def test_changed_after_proof_cannot_qualify_a_successful_loop(self):
        before = fixture_root_proof()
        after = copy.deepcopy(before)
        after["inspection"]["service"]["main_pid"] += 1
        def provider(v, controls, out, env):
            out.mkdir()
            (out / "root-inspection.json").write_text('{}')
            return before if out.name == 'provider-before' else after
        with patch.object(a, "load_assets", return_value=self.fake_support(True)), \
             patch.object(a, "inspect_provider", side_effect=provider), \
             patch.object(a, "inspect_transport", return_value={"passed": True}):
            receipt = a.run(self.request, self.execution, HERE, self.root)
        self.assertFalse(receipt["passed"])
        self.assertTrue(receipt["real_model_inference_observed"])
        self.assertEqual(receipt["generation_requests_attempted"], 2)
        self.assertFalse(receipt["provider_identity_unchanged"])

    def test_missing_harness_receipt_retains_unknown_attempt_count(self):
        before = fixture_root_proof()
        def provider(v, controls, out, env):
            out.mkdir()
            (out / "root-inspection.json").write_text('{}')
            return before
        with patch.object(a, "load_assets", return_value=self.fake_support(True, False)), \
             patch.object(a, "inspect_provider", side_effect=provider), \
             patch.object(a, "inspect_transport", return_value={"passed": True}):
            receipt = a.run(self.request, self.execution, HERE, self.root)
        self.assertFalse(receipt["passed"])
        self.assertIsNone(receipt["generation_requests_attempted"])
        self.assertEqual(receipt["generation_accounting"], "pending_harness_receipt")

    def test_receipt_missing_both_counters_is_rejected_with_unknown_count(self):
        before = fixture_root_proof()
        def provider(v, controls, out, env):
            out.mkdir()
            (out / "root-inspection.json").write_text('{}')
            return before
        with patch.object(a, "load_assets", return_value=self.fake_support(True, True, False)), \
             patch.object(a, "inspect_provider", side_effect=provider), \
             patch.object(a, "inspect_transport", return_value={"passed": True}):
            receipt = a.run(self.request, self.execution, HERE, self.root)
        self.assertFalse(receipt["passed"])
        self.assertIsNone(receipt["generation_requests_attempted"])
        self.assertEqual(receipt["generation_accounting"], "pending_harness_receipt")
        self.assertEqual(receipt["error_type"], 'AcceptanceError')
        self.assertIn('generation request budget receipt is invalid', receipt['error'])


if __name__ == "__main__":
    unittest.main(verbosity=2)

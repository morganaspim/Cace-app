"""Controller controls. Synthetic observations never qualify the OCI host."""
import copy
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import zipfile

import validate as v

HERE = Path(__file__).resolve().parent


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pins = json.loads((HERE / "source-pins.json").read_text())
        self.archive = (HERE / "product-source.zip").read_bytes()
        self.request = {"schema": "merlin-studio-validation-request/1",
                        "request_id": str(uuid.uuid4()), "operation": v.OPERATION,
                        "created_at": "2026-11-21T22:00:00Z"}
        self.execution = {"repository": v.OPS_REPOSITORY, "ref": v.OPS_REF,
                          "runner": "cace-oci-a1", "uid": 1000, "machine": "aarch64",
                          "system": "Linux", "run_id": 42, "run_attempt": 1,
                          "workflow_commit": "a" * 40}

    def tearDown(self):
        self.tmp.cleanup()

    def altered_archive(self, change):
        raw = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(self.archive)) as before:
            entries = [(entry, before.read(entry)) for entry in before.infolist()]
        entries = change(entries)
        with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as after:
            for entry, body in entries:
                after.writestr(entry, body)
        value = raw.getvalue()
        pins = copy.deepcopy(self.pins)
        pins["archive"] = v.identity(value)
        return pins, value

    def test_fixed_first_attempt_request_accepts_only_reviewed_identity(self):
        v.validate_request(self.request, self.execution)
        for field, value in (("operation", "deploy"), ("request_id", "not-uuid"),
                             ("created_at", "2026-11-21"), ("shell", "id")):
            with self.subTest(field=field):
                changed = dict(self.request, **{field: value})
                with self.assertRaises(v.ValidationError):
                    v.validate_request(changed, self.execution)
        for field, value in (("uid", 0), ("runner", "other"), ("ref", "refs/heads/main"),
                             ("run_attempt", 2), ("run_id", True), ("machine", "x86_64")):
            with self.subTest(execution=field):
                with self.assertRaises(v.ValidationError):
                    v.validate_request(self.request, dict(self.execution, **{field: value}))

    def test_duplicate_json_key_cannot_replace_an_identity(self):
        with self.assertRaises(v.ValidationError):
            v.parse_json('{"operation":"inspect","operation":"deploy"}')

    def test_published_bundle_has_exact_36_files_and_fresh_extraction(self):
        members = v.validate_bundle(self.pins, self.archive)
        self.assertEqual(len(members), 36)
        target = self.root / "source"
        v.extract_bundle(members, target)
        for name, pin in self.pins["files"].items():
            self.assertEqual(v.identity((target / name).read_bytes()), pin)
        with self.assertRaises(FileExistsError):
            v.extract_bundle(members, target)

    def test_altered_source_rejected_even_when_archive_hash_is_recomputed(self):
        def change(entries):
            entry, body = entries[0]
            return [(entry, body + b"\nchanged")] + entries[1:]
        pins, raw = self.altered_archive(change)
        with self.assertRaisesRegex(v.ValidationError, "member differs"):
            v.validate_bundle(pins, raw)
        bad = copy.deepcopy(self.pins)
        bad["commit"] = v.APPLICATION_PREDECESSOR
        with self.assertRaises(v.ValidationError):
            v.validate_bundle(bad, self.archive)

    def test_missing_extra_duplicate_symlink_and_traversal_members_rejected(self):
        changes = [
            lambda entries: entries[:-1],
            lambda entries: entries + [entries[0]],
            lambda entries: [(zipfile.ZipInfo("../escape"), b"bad")] + entries[1:],
        ]
        def symlink(entries):
            entry = copy.copy(entries[0][0])
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            return [(entry, entries[0][1])] + entries[1:]
        changes.append(symlink)
        for change in changes:
            with self.subTest(change=change.__name__):
                pins, raw = self.altered_archive(change)
                with self.assertRaises(v.ValidationError):
                    v.validate_bundle(pins, raw)

    def test_regular_reader_rejects_fifo_and_symlink_ancestry_without_blocking(self):
        fifo = self.root / "pipe"
        os.mkfifo(fifo)
        started = time.monotonic()
        with self.assertRaises(v.ValidationError):
            v.read_small(fifo)
        self.assertLess(time.monotonic() - started, .5)
        real = self.root / "real"
        real.mkdir()
        (real / "file").write_bytes(b"data")
        (self.root / "link").symlink_to(real, target_is_directory=True)
        with self.assertRaises(OSError):
            v.read_small(self.root / "link/file")

    def test_process_deadline_stops_real_child_and_retains_partial_output(self):
        log = self.root / "deadline.txt"
        started = time.monotonic()
        result = v.run_process([sys.executable, "-c", "import time;print('before',flush=True);time.sleep(30)"],
            cwd=self.root, env=v.child_env(self.root), log=log, seconds=.2)
        self.assertFalse(result["passed"])
        self.assertLess(time.monotonic() - started, 2)
        self.assertIn(b"before", log.read_bytes())
        self.assertIsNotNone(result["returncode"])

    def test_inherited_pipe_descendant_is_killed_at_absolute_deadline(self):
        pidfile = self.root / "child.pid"
        code = ("import subprocess,sys;from pathlib import Path;"
                "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);"
                "Path(sys.argv[1]).write_text(str(p.pid))")
        result = v.run_process([sys.executable, "-c", code, str(pidfile)], cwd=self.root,
                              env=v.child_env(self.root), log=self.root / "pipe.txt", seconds=.3)
        self.assertFalse(result["passed"])
        pid = int(pidfile.read_text())
        # A killed child may briefly remain a zombie until the system reaps it.
        status = Path("/proc") / str(pid) / "stat"
        deadline = time.monotonic() + 1
        while status.exists() and status.read_text().split()[2] != "Z" and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(not status.exists() or status.read_text().split()[2] == "Z")

    def test_output_limit_and_nonzero_exit_are_never_success(self):
        result = v.run_process([sys.executable, "-c", "print('x'*100000)"], cwd=self.root,
                              env=v.child_env(self.root), log=self.root / "large.txt", seconds=2, maximum=1024)
        self.assertFalse(result["passed"])
        self.assertEqual((self.root / "large.txt").stat().st_size, 1024)
        result = v.run_process([sys.executable, "-c", "raise SystemExit(7)"], cwd=self.root,
                              env=v.child_env(self.root), log=self.root / "bad.txt", seconds=2)
        self.assertFalse(result["passed"])
        self.assertEqual(result["returncode"], 7)

    def test_child_environment_excludes_credentials_and_model_override(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "private", "HTTPS_PROXY": "proxy",
                                     "MERLIN_MODEL_URL": "https://external.invalid"}):
            env = v.child_env(self.root)
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertNotIn("MERLIN_MODEL_URL", env)

    def test_python39_preserves_not_run_and_never_compiles_or_installs(self):
        inventory = {"passed": False, "selected": None}
        with patch.object(v, "trusted_executable", side_effect=AssertionError("must not compile")):
            result = v.run_source_tests(self.root, self.root, inventory, {}, self.pins)
        self.assertEqual(result["status"], "not_run")
        self.assertFalse(result["passed"])
        self.assertEqual(result["tests"], 0)
        self.assertEqual(len(result["not_run_stages"]), 6)

    def test_test_runner_rejects_skips_and_unexpected_count(self):
        source = self.root / "fake-source"
        (source / "tests").mkdir(parents=True)
        target = source / "tests/test_fixture.py"
        target.write_text("import unittest\nclass Test(unittest.TestCase):\n @unittest.skip('unavailable')\n def test_case(self): pass\n")
        receipt = self.root / "fake-result.json"
        command = [sys.executable, "-I", "-B", "-c", v.TEST_CODE, str(source), "tests",
                   "test_fixture.py", "1", str(receipt)]
        completed = subprocess.run(command, capture_output=True, timeout=5)
        self.assertNotEqual(completed.returncode, 0)
        value = json.loads(receipt.read_text())
        self.assertEqual(value["skipped"], 1)
        self.assertFalse(value["passed"])
        target.write_text("import unittest\nclass Test(unittest.TestCase):\n def test_case(self): pass\n")
        command[-2] = "2"
        completed = subprocess.run(command, capture_output=True, timeout=5)
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(json.loads(receipt.read_text())["passed"])

    def test_successful_fixture_runner_is_distinguished_from_source_suite(self):
        source = self.root / "fake-source"
        (source / "tests").mkdir(parents=True)
        (source / "tests/test_fixture.py").write_text("import unittest\nclass Test(unittest.TestCase):\n def test_case(self): self.assertEqual(2+2,4)\n")
        receipt = self.root / "result.json"
        command = [sys.executable, "-I", "-B", "-c", v.TEST_CODE, str(source), "tests",
                   "test_fixture.py", "1", str(receipt)]
        completed = subprocess.run(command, capture_output=True, timeout=5)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(json.loads(receipt.read_text()), {"tests": 1, "errors": 0, "failures": 0, "skipped": 0, "passed": True})

    def test_model_preflight_requires_all_real_prerequisites(self):
        provider = {"passed": True, "files": {key: {"sha256": value["sha256"]} for key, value in v.PROVIDER_FILES.items()},
                    "service": {"ActiveState": "active", "SubState": "running"},
                    "process_binding": {"passed": True}}
        python = {"passed": True, "selected": {"version": [3, 11, 0], "executable": "/usr/bin/python3.11"}}
        self.assertTrue(v.model_preflight(provider, python, True)["passed"])
        self.assertFalse(v.model_preflight(provider, python, False)["passed"])
        self.assertFalse(v.model_preflight(dict(provider, passed=False), python, True)["passed"])
        self.assertFalse(v.model_preflight(provider, dict(python, passed=False), True)["passed"])
        self.assertFalse(v.model_preflight(dict(provider, process_binding={}), python, True)["passed"])

    def test_provider_transport_never_accepts_generation_or_changed_token_payload(self):
        for method, path, body in (("POST", "/v1/chat/completions", b"{}"),
                                    ("GET", "https://external.invalid", None),
                                    ("POST", "/v1/chat/completions/input_tokens", b"{}")):
            with self.subTest(path=path):
                with patch.object(http.client, "HTTPConnection", side_effect=AssertionError("no connection")):
                    with self.assertRaises(v.ValidationError):
                        v.local_json(method, path, body)

    def test_provider_context_and_post_inspection_keep_zero_generation(self):
        body = (HERE / "initial-model-request.json").read_bytes()
        observations = []
        def regular(path, **kwargs):
            pin = next(value for value in v.PROVIDER_FILES.values() if value["path"] == path)
            return {"sha256": pin["sha256"], "bytes": pin.get("bytes", 10)}
        def process(argv, **kwargs):
            Path(kwargs["log"]).write_text("LoadState=loaded\nActiveState=active\nSubState=running\nMainPID=42\nFragmentPath=/etc/systemd/system/merlin-model-provider.service\n")
            return {"passed": True}
        count = [1920]
        def endpoint(method, path, payload=None):
            observations.append((method, path))
            if path == "/health":
                return {"status": "ok"}
            if path == "/v1/models":
                return {"data": [{"id": v.MODEL_ID}]}
            return {"input_tokens": count[0], "object": "response.input_tokens"}
        with patch.object(v, "regular_identity", side_effect=regular), \
             patch.object(v, "trusted_executable", return_value=(Path("/usr/bin/systemctl"), {})), \
             patch.object(v, "run_process", side_effect=process), \
             patch.object(v, "process_binding", return_value={"passed": True, "pid": 42}), \
             patch.object(v, "local_json", side_effect=endpoint):
            self.assertTrue(v.inspect_provider(self.root, {}, body)["passed"])
            count[0] = 1921
            self.assertFalse(v.inspect_provider(self.root, {}, body)["passed"])
            count[0] = True
            self.assertFalse(v.inspect_provider(self.root, {}, body)["passed"])
            observations.clear()
            after = v.inspect_provider(self.root, {}, tokenize=False)
            self.assertTrue(after["passed"])
            self.assertEqual(after["live_model_generation_calls"], 0)
            self.assertEqual(after["tokenization_calls"], 0)
            self.assertEqual(observations, [("GET", "/health"), ("GET", "/v1/models")])

    def test_process_binding_rejects_stale_or_unbound_provider(self):
        model = v.PROVIDER_FILES["model"]["path"]
        values = {
            "stat": ("42 (llama-server) " + " ".join(["S"] + ["0"] * 18 + ["55"])).encode(),
            "status": b"Name:\tllama-server\nUid:\t981\t981\t981\t981\n",
            "cmdline": ("\0".join(v.provider_argv()) + "\0").encode(),
            "maps": ("1000-2000 r--p 00000000 00:7b 2 " + model + "\n").encode(),
        }
        files = {"binary": {"device_id": 123, "inode": 1},
                 "model": {"device_id": 123, "inode": 2}}
        link = lambda path: v.PROVIDER_FILES["binary"]["path"] if path.endswith("/exe") else "net:[123]"
        with patch.object(v, "read_proc", side_effect=lambda pid, name, maximum=65536: values[name]), \
             patch.object(os, "readlink", side_effect=link), \
             patch.object(os, "stat", return_value=SimpleNamespace(st_dev=123, st_ino=1)):
            result = v.process_binding({"MainPID": "42"}, files)
            self.assertTrue(result["passed"])
            self.assertEqual(result["argv_sha256"], "53409829c524241d6baaad015cb2c60d874014c4e17ae13cb57f54b4c4466952")
            with self.assertRaises(v.ValidationError):
                v.process_binding({"MainPID": "0"}, files)
            values["maps"] = b"1000-2000 r--p 00000000 00:7b 99 /wrong/model\n"
            with self.assertRaises(v.ValidationError):
                v.process_binding({"MainPID": "42"}, files)
        with patch.object(v, "read_proc", side_effect=PermissionError("cross-UID proc access denied")):
            with self.assertRaises(PermissionError):
                v.process_binding({"MainPID": "42"}, files)

    def test_service_pid_change_cannot_reuse_original_live_process_proof(self):
        def regular(path, **kwargs):
            pin = next(value for value in v.PROVIDER_FILES.values() if value["path"] == path)
            return {"sha256": pin["sha256"], "bytes": pin.get("bytes", 10)}
        def process(argv, **kwargs):
            log = Path(kwargs["log"])
            pid = "43" if log.name == "provider-service-after.txt" else "42"
            log.write_text("LoadState=loaded\nActiveState=active\nSubState=running\nMainPID=" + pid
                           + "\nFragmentPath=/etc/systemd/system/merlin-model-provider.service\n")
            return {"passed": True}
        def endpoint(method, path, payload=None):
            return {"status": "ok"} if path == "/health" else {"data": [{"id": v.MODEL_ID}]}
        with patch.object(v, "regular_identity", side_effect=regular), \
             patch.object(v, "trusted_executable", return_value=(Path("/usr/bin/systemctl"), {})), \
             patch.object(v, "run_process", side_effect=process), \
             patch.object(v, "process_binding", return_value={"passed": True, "pid": 42}), \
             patch.object(v, "local_json", side_effect=endpoint):
            result = v.inspect_provider(self.root, {}, tokenize=False)
        self.assertFalse(result["passed"])
        self.assertEqual(result["service_after"]["MainPID"], "43")
        self.assertIn("service identity changed", result["errors"][-1])
        self.assertEqual(result["live_model_generation_calls"], 0)

    def test_slow_live_provider_body_hits_total_deadline(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", "200")
                self.end_headers()
                try:
                    for _ in range(200):
                        self.wfile.write(b" ")
                        self.wfile.flush()
                        time.sleep(.1)
                except OSError:
                    pass
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        actual = http.client.HTTPConnection
        started = time.monotonic()
        try:
            with patch.object(http.client, "HTTPConnection", side_effect=lambda host, port, timeout: actual(host, server.server_port, timeout=timeout)):
                with self.assertRaises((v.ValidationError, OSError, http.client.HTTPException)):
                    v.local_json("GET", "/health")
            self.assertGreater(time.monotonic() - started, 7)
            self.assertLess(time.monotonic() - started, 10)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_live_http_length_success_redirect_and_truncation_controls(self):
        response = [200, b'{"status":"ok"}', None]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(response[0])
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(response[2] if response[2] is not None else len(response[1])))
                self.end_headers()
                self.wfile.write(response[1])
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        actual = http.client.HTTPConnection
        try:
            with patch.object(http.client, "HTTPConnection", side_effect=lambda host, port, timeout: actual(host, server.server_port, timeout=timeout)):
                self.assertEqual(v.local_json("GET", "/health"), {"status": "ok"})
                response[0] = 302
                with self.assertRaises(v.ValidationError):
                    v.local_json("GET", "/health")
                response[0] = 200
                response[2] = len(response[1]) + 10
                with self.assertRaises((v.ValidationError, http.client.IncompleteRead)):
                    v.local_json("GET", "/health")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

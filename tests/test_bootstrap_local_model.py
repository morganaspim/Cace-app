"""Synthetic fixed-profile controls. They do not install or call a model."""
from contextlib import ExitStack, contextmanager
import copy
import io
import json
import os
from pathlib import Path
import signal
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

import bootstrap_local_model as b


REQUEST = {"schema": "merlin-model-bootstrap-request/1", "request_id": "27110294-3108-48dc-a5da-fa22c975423b",
           "operation": "bootstrap", "created_at": "2026-11-21T14:00:00Z"}
IDENTITY = {"run_id": 12345, "run_attempt": 1, "workflow_commit": "a" * 40,
            "controller_sha256": "b" * 64, "runner": "cace-oci-a1"}
GOOD_CODE = "def clamp(value, low, high):\n    return min(high, max(low, value))"


def response(text=GOOD_CODE, **updates):
    result = {"model": b.MODEL_ALIAS, "choices": [{"finish_reason": "stop", "message": {"content": text}}],
              "usage": {"prompt_tokens": 100, "completion_tokens": 25, "total_tokens": 125}}
    result.update(updates)
    return result


class Fixture:
    def __init__(self, root):
        self.root, self.calls, self.pid = root, [], 100
        self.model_calls = 0
        self.binary = {"sha256": b.digest(b"binary"), "size_bytes": 6, "path": str(root / "binary"),
                       "version_text": "synthetic-version", "cgroup": {},
                       "runtime_linkage": {"needed": ["libc.so.6"], "build_shared_libs": False, "ggml_backend_dl": False}}
        (root / "binary").write_bytes(b"binary")
        self.installed = {"release_id": "c" * 64, "binary": str(root / "binary"), "model": str(root / "model.gguf"),
                          "unit_sha256": "d" * 64}

    def enter(self, stack):
        values = {"STATE": self.root / "state", "INTENT": self.root / "state/intent.json",
                  "CONFIG": self.root / "config", "MANIFEST": self.root / "config/manifest.json",
                  "BOOTSTRAP_RECEIPT": self.root / "config/bootstrap-receipt.json", "UNIT_PATH": self.root / "provider.service"}
        for name, value in values.items():
            stack.enter_context(patch.object(b, name, value))
        stack.enter_context(patch.object(b.os, "geteuid", return_value=0))
        stack.enter_context(patch.object(b, "rooted_directory", side_effect=lambda p: p.mkdir(parents=True, exist_ok=True)))
        stack.enter_context(patch.object(b, "preflight", side_effect=self.preflight))
        stack.enter_context(patch.object(b, "download", side_effect=self.download))
        stack.enter_context(patch.object(b.tarfile, "open", return_value=Mock(__enter__=Mock(return_value=object()), __exit__=Mock(return_value=False))))
        stack.enter_context(patch.object(b, "extract_members", return_value={"files": 4176, "uncompressed_bytes": 184232076}))
        stack.enter_context(patch.object(b, "build", side_effect=self.build))
        stack.enter_context(patch.object(b, "install", side_effect=self.install))
        stack.enter_context(patch.object(b, "command", side_effect=self.command))
        stack.enter_context(patch.object(b, "wait_ready", side_effect=self.ready))
        stack.enter_context(patch.object(b, "observe_installed", side_effect=self.observe))
        stack.enter_context(patch.object(b, "private_observation", return_value={"unchanged": True}))
        stack.enter_context(patch.object(b, "http_json", side_effect=self.http))
        stack.enter_context(patch.object(b, "rollback", side_effect=self.rollback))
        return self

    def preflight(self):
        self.calls.append("preflight")
        return {"private": {"unchanged": True}, "provider": {"LoadState": "not-found"}}

    def download(self, url, path, size, sha, seconds):
        self.calls.append("download-source" if url == b.SOURCE_URL else "download-model")
        path.write_bytes(b"source" if url == b.SOURCE_URL else b"GGUFsynthetic")
        return {"sha256": sha, "size_bytes": size}

    def build(self, *args):
        self.calls.append("build")
        return self.binary

    def install(self, *args):
        self.calls.append("install")
        return self.installed

    def command(self, argv, **kwargs):
        self.calls.append("command:" + " ".join(argv[1:]))
        return b""

    def ready(self):
        self.calls.append("ready")
        return {"health_sha256": "e" * 64, "models_sha256": "f" * 64, "model_ids": [b.MODEL_ALIAS]}

    def observe(self, *args):
        self.pid += 1
        self.calls.append("observe")
        return {"unit": b.UNIT, "unit_sha256": self.installed["unit_sha256"], "main_pid": self.pid,
                "user": b.USER, "uid": 900, "group": b.USER, "gid": 900, "active_state": "active",
                "sub_state": "running", "enabled": True}

    def http(self, path, payload=None, timeout=None):
        self.calls.append("http:" + path)
        if path.endswith("input_tokens"):
            result = {"object": "response.input_tokens", "input_tokens": 100}
        else:
            self.model_calls += 1
            result = response()
        return result, b.canonical(result)

    def rollback(self, installed):
        self.calls.append("rollback")
        return {"fixture_only": True, "installed": installed is not None}


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
        yield Fixture(Path(folder)).enter(stack)


class BootstrapControls(unittest.TestCase):
    def test_request_and_execution_identity_are_fixed(self):
        b.validate_request(REQUEST, IDENTITY)
        cases = [(dict(REQUEST, command="anything"), IDENTITY), (dict(REQUEST, operation="shell"), IDENTITY),
                 (dict(REQUEST, model="other"), IDENTITY), (dict(REQUEST, request_id="bad"), IDENTITY),
                 (dict(REQUEST, created_at="now"), IDENTITY), (REQUEST, dict(IDENTITY, run_attempt=True)),
                 (REQUEST, dict(IDENTITY, run_attempt=2)), (REQUEST, dict(IDENTITY, runner="other")),
                 (REQUEST, dict(IDENTITY, workflow_commit="main")), (REQUEST, dict(IDENTITY, run_id=True))]
        for request, identity in cases:
            with self.subTest(request=request, identity=identity), self.assertRaises((b.BootstrapError, ValueError)):
                b.validate_request(request, identity)

    def test_duplicate_and_nonfinite_json_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b"[]" * 100):
            with self.subTest(raw=raw), self.assertRaises((b.BootstrapError, ValueError)):
                b.decode(raw, 50)

    def test_regular_reader_rejects_symlink_and_size(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data").write_bytes(b"1234")
            (root / "link").symlink_to(root / "data")
            self.assertEqual(b.read_regular(root / "data", 4), b"1234")
            for path, limit in [(root / "link", 4), (root / "data", 3)]:
                with self.subTest(path=path), self.assertRaises((b.BootstrapError, OSError)):
                    b.read_regular(path, limit)

    def test_immutable_write_preserves_prior_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record"
            b.write_new(path, b"first")
            with self.assertRaises(FileExistsError):
                b.write_new(path, b"other")
            self.assertEqual(path.read_bytes(), b"first")

    def archive(self, entries):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w") as archive:
            for name, kind, content in entries:
                member = tarfile.TarInfo(name)
                member.type, member.mode, member.size = kind, 0o644, len(content)
                member.linkname = "../outside"
                archive.addfile(member, io.BytesIO(content) if kind == tarfile.REGTYPE else None)
        data.seek(0)
        return tarfile.open(fileobj=data, mode="r")

    def test_archive_extracts_only_expected_regular_source(self):
        with tempfile.TemporaryDirectory() as folder, self.archive([(b.SOURCE_PREFIX + "/src/file", tarfile.REGTYPE, b"hello")]) as archive:
            got = b.extract_members(archive, Path(folder))
            self.assertEqual(got, {"files": 1, "uncompressed_bytes": 5})
            self.assertEqual((Path(folder) / "src/file").read_bytes(), b"hello")

    def test_archive_rejects_escape_links_and_duplicate_members(self):
        names = ["../outside", b.SOURCE_PREFIX + "/../../outside", "/" + b.SOURCE_PREFIX + "/a", "other/a"]
        cases = [[(name, tarfile.REGTYPE, b"x")] for name in names]
        cases += [[(b.SOURCE_PREFIX + "/link", kind, b"")] for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE)]
        cases += [[(b.SOURCE_PREFIX + "/a", tarfile.REGTYPE, b"x")] * 2]
        for entries in cases:
            with self.subTest(entries=entries), tempfile.TemporaryDirectory() as folder, self.archive(entries) as archive, self.assertRaises(b.BootstrapError):
                b.extract_members(archive, Path(folder))

    def test_download_exact_hash_size_and_no_credentials(self):
        raw = b"source-bytes"
        reply = Mock(status=200)
        reply.getheader.side_effect = lambda name, default=None: str(len(raw)) if name == "Content-Length" else default
        reply.read1.side_effect = [raw, b""]
        connection = Mock()
        connection.getresponse.return_value = reply
        with tempfile.TemporaryDirectory() as folder, patch.object(b.http.client, "HTTPSConnection", return_value=connection):
            path = Path(folder) / "data"
            result = b.download(b.SOURCE_URL, path, len(raw), b.digest(raw), 2)
            self.assertEqual(result["sha256"], b.digest(raw))
            self.assertEqual(path.read_bytes(), raw)
            self.assertNotIn("Authorization", connection.request.call_args.kwargs["headers"])
            connection.close.assert_called_once()
            reply.close.assert_called_once()

    def test_download_rejects_untrusted_route_before_connect(self):
        urls = ["http://huggingface.co/a", "https://evil.invalid/a", "https://user:secret@huggingface.co/a",
                "https://huggingface.co:444/a", "https://huggingface.co/a#fragment"]
        with patch.object(b.http.client, "HTTPSConnection") as network:
            for url in urls:
                with self.subTest(url=url), self.assertRaises(b.BootstrapError):
                    b.download(url, Path("unused"), 1, "a" * 64, 1)
            network.assert_not_called()

    def test_download_hash_mismatch_and_redirect_escape_fail_closed(self):
        reply = Mock(status=200)
        reply.getheader.side_effect = lambda name, default=None: "1" if name == "Content-Length" else default
        reply.read1.side_effect = [b"x", b""]
        connection = Mock()
        connection.getresponse.return_value = reply
        with tempfile.TemporaryDirectory() as folder, patch.object(b.http.client, "HTTPSConnection", return_value=connection), self.assertRaises(b.BootstrapError):
            b.download(b.SOURCE_URL, Path(folder) / "data", 1, "a" * 64, 2)
        reply = Mock(status=302)
        reply.getheader.return_value = "http://127.0.0.1:8080/anything"
        connection.getresponse.return_value = reply
        with patch.object(b.http.client, "HTTPSConnection", return_value=connection), self.assertRaises(b.BootstrapError):
            b.download(b.SOURCE_URL, Path("unused"), 1, "a" * 64, 1)

    def test_download_wall_deadline_interrupts_a_stalled_response(self):
        with self.assertRaisesRegex(b.BootstrapError, "wall deadline"):
            with b.wall_deadline(0.02):
                signal.pause()
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))

    def test_actual_child_deadline_and_output_are_bounded(self):
        with self.assertRaisesRegex(b.BootstrapError, "deadline"):
            b.command([sys.executable, "-c", "import time;time.sleep(2)"], timeout=0.03)
        with self.assertRaisesRegex(b.BootstrapError, "output limit"):
            b.command([sys.executable, "-c", "print('x'*10000)"], limit=30)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manager-opened-output"
            path.write_bytes(b"x" * 20)
            with self.assertRaisesRegex(b.BootstrapError, "manager-opened log output limit"):
                b.command([sys.executable, "-c", "import time;time.sleep(2)"], monitored_files=[(path, 10)])

    def test_build_uses_manager_opened_files_and_verified_static_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source"
            source.mkdir()
            def build_command(argv, **kwargs):
                self.assertNotIn("--pipe", argv)
                self.assertIn("--service-type=exec", argv)
                for prop in ("PrivateNetwork=yes", "MemoryMax=4294967296", "MemorySwapMax=0", "CPUQuota=150%", "TasksMax=32", "RuntimeMaxSec=1800"):
                    self.assertIn("--property=" + prop, argv)
                for channel in ("stdin", "stdout", "stderr"):
                    path = root / ("build-" + channel)
                    self.assertTrue(path.is_file())
                    self.assertIn("--property=Standard" + {"stdin": "Input", "stdout": "Output", "stderr": "Error"}[channel] + "=file:" + str(path), argv)
                self.assertEqual(len(kwargs["monitored_files"]), 2)
                target = root / "build"
                (target / "bin").mkdir()
                (target / "bin/llama-server").write_bytes(b"synthetic binary")
                (target / "version.txt").write_text("synthetic-version")
                (target / "build-policy.json").write_text(json.dumps({"memory.max": "4294967296"}))
                (target / "runtime-linkage.json").write_text(json.dumps({"needed": ["libc.so.6"], "build_shared_libs": False, "ggml_backend_dl": False}))
                return b""
            account = Mock(pw_uid=os.getuid(), pw_gid=os.getgid())
            with patch.object(b.pwd, "getpwnam", return_value=account), patch.object(b, "command", side_effect=build_command):
                result = b.build(source, root, IDENTITY)
            self.assertEqual(result["sha256"], b.digest(b"synthetic binary"))
            self.assertEqual(result["io_transport"], "manager_opened_files")
            self.assertFalse(result["runtime_linkage"]["ggml_backend_dl"])

    def test_fixed_unit_and_static_runtime_configuration(self):
        unit = b.unit_text(Path("/opt/merlin-model-provider/releases/abc/llama-server"), Path("/opt/merlin-model-provider/releases/abc/model.gguf")).decode()
        for field in ("--host 127.0.0.1", "--port 8080", "--ctx-size 4096", "--parallel 1", "--threads 2",
                      "--offline", "--no-webui", "MemoryMax=3221225472", "MemorySwapMax=0", "CPUQuota=150%", "TasksMax=32", "User=merlin-model"):
            self.assertIn(field, unit)
        self.assertNotIn("MERLIN_MODEL_QUALIFIED", unit)
        self.assertNotIn("EnvironmentFile", unit)
        self.assertIn("-DBUILD_SHARED_LIBS=OFF", b.BUILD_FLAGS)
        self.assertIn("-DGGML_BACKEND_DL=OFF", b.BUILD_FLAGS)
        self.assertIn("readelf", b.BUILD_SCRIPT)
        compile(b.BUILD_SCRIPT, "fixed-build-child", "exec")

    def test_smoke_interpreter_accepts_small_correct_functions(self):
        texts = [GOOD_CODE, "```python\n" + GOOD_CODE + "\n```",
                 "def clamp(value, low, high):\n if value < low:\n  return low\n if value > high:\n  return high\n return value"]
        for text in texts:
            with self.subTest(text=text):
                result = b.check_code(text)
                self.assertEqual(len(result["checks"]), 12)
                self.assertTrue(all(item["passed"] for item in result["checks"]))

    def test_smoke_interpreter_rejects_wrong_and_effectful_code(self):
        texts = ["def clamp(value, low, high):\n return value", "import os\n" + GOOD_CODE,
                 "def clamp(value, low, high):\n return __import__('os').getcwd()",
                 "def clamp(value, low, high):\n while True:\n  pass",
                 "@danger\n" + GOOD_CODE, "def clamp(value: int, low, high):\n return value",
                 "def clamp(value, low, high):\n return eval('1')", "def clamp(value, low, high):\n return open('/etc/passwd')",
                 "def clamp(value, low, high):\n value = 0\n return value"]
        for text in texts:
            with self.subTest(text=text), self.assertRaises(b.BootstrapError):
                b.check_code(text)

    def test_exact_token_count_precedes_one_inference(self):
        with fixture() as f:
            result = b.smoke(f.root)
            self.assertEqual(f.model_calls, 1)
            self.assertEqual(result["prompt_tokens"], 100)
            self.assertEqual(result["inference_requests"], 1)
            self.assertEqual(f.calls, ["http:/v1/chat/completions/input_tokens", "http:/v1/chat/completions"])
            self.assertEqual(b.digest((f.root / "smoke-response.json").read_bytes()), result["response_sha256"])

    def test_token_count_bad_or_over_budget_prevents_inference(self):
        for count in (True, 0, -1, 4096, "100"):
            with self.subTest(count=count), fixture() as f:
                data = {"object": "response.input_tokens", "input_tokens": count}
                with patch.object(b, "http_json", return_value=(data, b.canonical(data))) as api, self.assertRaises(b.BootstrapError):
                    b.smoke(f.root)
                self.assertEqual(api.call_count, 1)
                self.assertFalse((f.root / "smoke-inference-intent.json").exists())

    def test_actual_usage_or_alias_mismatch_is_retained_without_retry(self):
        variants = [response(model="wrong"), response(usage={"prompt_tokens": 101, "completion_tokens": 25, "total_tokens": 126}),
                    response(usage={"prompt_tokens": 100, "completion_tokens": 385, "total_tokens": 485}),
                    response(usage={"prompt_tokens": True, "completion_tokens": 25, "total_tokens": 125}),
                    response(choices=[{"finish_reason": "length", "message": {"content": GOOD_CODE}}])]
        count = {"object": "response.input_tokens", "input_tokens": 100}
        for result in variants:
            with self.subTest(result=result), fixture() as f:
                with patch.object(b, "http_json", side_effect=[(count, b.canonical(count)), (result, b.canonical(result))]) as api, self.assertRaises(b.BootstrapError):
                    b.smoke(f.root)
                self.assertEqual(api.call_count, 2)
                self.assertTrue((f.root / "smoke-response.json").exists())

    def test_full_orchestration_requires_smoke_restart_and_unchanged_private_service(self):
        with fixture() as f:
            result = b.run(REQUEST, IDENTITY)
            self.assertEqual(result["status"], "ready")
            self.assertEqual(f.model_calls, 1)
            manifest = json.loads(b.MANIFEST.read_bytes())
            receipt = json.loads(b.BOOTSTRAP_RECEIPT.read_bytes())
            self.assertIs(manifest["qualification"], False)
            self.assertIs(manifest["promotion_authority"], False)
            self.assertEqual(manifest["revision"], "gguf:" + b.MODEL_SHA + ";llama:" + b.SOURCE_COMMIT + ";bin:" + f.binary["sha256"])
            self.assertEqual(manifest["bootstrap_receipt_sha256"], b.digest(b.BOOTSTRAP_RECEIPT.read_bytes()))
            self.assertIs(receipt["smoke"]["passed"], True)
            self.assertNotEqual(receipt["first_service"]["main_pid"], receipt["after"]["provider"]["main_pid"])
            self.assertLess(f.calls.index("http:/v1/chat/completions"), f.calls.index("command:restart " + b.UNIT))
            self.assertLess(len(b.MANIFEST.read_bytes()), 16384)
            self.assertLess(len(b.BOOTSTRAP_RECEIPT.read_bytes()), 65536)

    def test_root_entry_normalizes_restrictive_parent_umask_and_restores_it(self):
        with fixture() as f:
            previous = os.umask(0o077)
            try:
                result = b.run(REQUEST, IDENTITY)
                self.assertEqual(result["status"], "ready")
                self.assertEqual(b.MANIFEST.stat().st_mode & 0o777, 0o644)
                self.assertEqual((b.STATE / "runs/12345-1/source").stat().st_mode & 0o777, 0o755)
                self.assertEqual(b.INTENT.stat().st_mode & 0o777, 0o600)
                self.assertEqual(os.umask(0o077), 0o077)
            finally:
                os.umask(previous)

    def test_build_failure_retains_intent_and_blocks_automatic_retry(self):
        with fixture() as f:
            with patch.object(b, "build", side_effect=b.BootstrapError("fixture build failure")) as build:
                with self.assertRaises(b.BootstrapError):
                    b.run(REQUEST, IDENTITY)
                with self.assertRaisesRegex(b.BootstrapError, "no automatic effects"):
                    b.run(REQUEST, dict(IDENTITY, run_id=12346))
                self.assertEqual(build.call_count, 1)
            self.assertTrue(b.INTENT.exists())
            self.assertFalse(b.MANIFEST.exists())
            self.assertTrue((b.STATE / "runs/12345-1/failed-receipt.json").exists())
            self.assertEqual(f.model_calls, 0)

    def test_each_post_install_failure_rolls_back_before_ready_publication(self):
        for stage in ("wait_ready", "observe_installed", "smoke", "private_observation"):
            with self.subTest(stage=stage), fixture() as f:
                with patch.object(b, stage, side_effect=b.BootstrapError("fixture interruption")), self.assertRaises(b.BootstrapError):
                    b.run(REQUEST, IDENTITY)
                self.assertIn("rollback", f.calls)
                self.assertFalse(b.MANIFEST.exists())
                failure = json.loads((b.STATE / "runs/12345-1/failed-receipt.json").read_bytes())
                self.assertEqual(failure["status"], "failed")
                self.assertTrue(failure["rollback"]["installed"])

    def test_private_observation_drift_blocks_publication(self):
        with fixture() as f:
            with patch.object(b, "private_observation", return_value={"changed": True}), self.assertRaisesRegex(b.BootstrapError, "preexisting private"):
                b.run(REQUEST, IDENTITY)
            self.assertEqual(f.model_calls, 1)
            self.assertFalse(b.MANIFEST.exists())
            self.assertEqual(f.calls[-1], "rollback")

    def test_restart_same_pid_blocks_publication(self):
        with fixture() as f:
            observed = f.observe()
            with patch.object(b, "observe_installed", return_value=observed), self.assertRaisesRegex(b.BootstrapError, "restart"):
                b.run(REQUEST, IDENTITY)
            self.assertFalse(b.MANIFEST.exists())

    def test_interruption_after_actual_response_preserves_no_repeat_intent(self):
        with fixture() as f:
            original = b.write_new
            def write(path, data, mode=0o644):
                if path.name == "smoke-response.json":
                    original(path, data, mode)
                    raise SystemExit("synthetic interruption after response receipt")
                return original(path, data, mode)
            with patch.object(b, "write_new", side_effect=write), self.assertRaises(SystemExit):
                b.run(REQUEST, IDENTITY)
            with self.assertRaises(b.BootstrapError):
                b.run(REQUEST, dict(IDENTITY, run_id=12346))
            self.assertEqual(f.model_calls, 1)
            out = b.STATE / "runs/12345-1"
            self.assertTrue((out / "smoke-response.json").exists())
            self.assertTrue((out / "smoke-inference-intent.json").exists())
            self.assertFalse(b.MANIFEST.exists())

    def test_artifact_write_failure_prevents_ready_manifest(self):
        with fixture() as f:
            original = b.write_new
            def write(path, data, mode=0o644):
                if path.name == "manifest.json" and path.parent != b.CONFIG:
                    raise OSError("synthetic output failure")
                return original(path, data, mode)
            with patch.object(b, "write_new", side_effect=write), self.assertRaises(OSError):
                b.run(REQUEST, IDENTITY)
            self.assertFalse(b.MANIFEST.exists())
            self.assertEqual(f.calls[-1], "rollback")

    def test_completed_duplicate_rechecks_live_state_without_inference(self):
        with fixture() as f:
            b.run(REQUEST, IDENTITY)
            before = list(f.calls)
            with patch.object(b, "inspect_ready", return_value={"status": "ready", "inference_requests": 0}) as inspect:
                result = b.run(REQUEST, dict(IDENTITY, run_id=12346))
            self.assertEqual(result["inference_requests"], 0)
            inspect.assert_called_once()
            self.assertEqual(before, f.calls)
            self.assertEqual(f.model_calls, 1)

    def test_other_request_is_not_authority_to_repeat_completed_bootstrap(self):
        with fixture() as f:
            b.run(REQUEST, IDENTITY)
            other = dict(REQUEST, request_id="8714c2c6-bc2d-4d4f-a683-4b734739507e")
            with self.assertRaisesRegex(b.BootstrapError, "no automatic effects"):
                b.run(other, dict(IDENTITY, run_id=12346))
            self.assertEqual(f.model_calls, 1)

    def test_inspect_without_provider_does_not_attempt_acquisition(self):
        with fixture() as f, patch.object(b, "service", return_value={"LoadState": "not-found"}):
            result = b.run(dict(REQUEST, operation="inspect"), IDENTITY)
            self.assertEqual(result["status"], "not-ready")
            self.assertEqual(f.calls, [])
            self.assertFalse(b.INTENT.exists())


if __name__ == "__main__":
    unittest.main()

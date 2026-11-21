import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "ops/merlin_dot/provider_inventory.py"
spec = importlib.util.spec_from_file_location("provider_inventory", MODULE)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
SECRET = "SYNTHETIC_PRIVATE_CREDENTIAL_NEVER_EMIT_73"


class ProviderInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({"schema": "merlin-private-host/1",
            "project_id": SECRET, "namespaces": [SECRET],
            "MERLIN_REMOTE_API_KEY": SECRET,
            "grants": [{"uid": 1000, "principal": SECRET,
                        "tools": ["health", "rsi_status", SECRET]}]}))
        self.patches = [patch.object(inventory, "CONFIG", self.config),
            patch.object(inventory, "SOCKET", self.root / "tools.sock"),
            patch.object(inventory, "MODEL_PATHS", (self.root / "model.gguf",)),
            patch.object(inventory, "PROC", self.root / "proc"),
            patch.object(inventory.shutil, "which", return_value=None)]
        for item in self.patches:
            item.start()
        self.addCleanup(self.temp.cleanup)
        for item in reversed(self.patches):
            self.addCleanup(item.stop)

    def process(self, pid=123, name="llama-server", address="0100007F", port=8080,
                inode="456", fd_inode="456", ticks=777):
        root = self.root / "proc" / str(pid)
        (root / "fd").mkdir(parents=True, exist_ok=True)
        (root / "net").mkdir(exist_ok=True)
        (root / "ns").mkdir(exist_ok=True)
        (root / "ns/net").symlink_to("net:[42]")
        current = self.root / "proc/self/ns/net"
        if not current.is_symlink():
            current.parent.mkdir(parents=True, exist_ok=True)
            current.symlink_to("net:[42]")
        (root / "comm").write_text(name + "\n")
        (root / "stat").write_text(str(pid) + " (" + name + ") " +
            " ".join(["S"] + ["0"] * 18 + [str(ticks)]) + "\n")
        (root / "fd/3").symlink_to("socket:[" + fd_inode + "]")
        (root / "net/tcp").write_text("header\n0: " + address + ":" + format(port, "04X") +
            " 00000000:0000 0A 00000000:00000000 00:00000000 00000000 1000 0 " + inode + "\n")
        (root / "net/tcp6").write_text("header\n")
        return root

    def collect(self, rows=()):
        with patch.object(inventory, "_processes", return_value=list(rows)):
            return inventory.collect()

    def test_private_config_projection_omits_all_unrecognized_values(self):
        value = inventory._config()
        self.assertEqual(value["recognized_tools"], ["health", "rsi_status"])
        self.assertEqual(value["unrecognized_tool_entries"], 1)
        self.assertEqual(value["provider_configuration"], "not_defined_by_this_schema")
        self.assertNotIn(SECRET, json.dumps(value))
        self.assertEqual(value["sha256"], hashlib.sha256(self.config.read_bytes()).hexdigest())

    def test_invalid_or_oversized_private_config_is_not_returned(self):
        for raw in (b"[", b"x" * 16385, json.dumps({"schema": SECRET}).encode(),
                    json.dumps({"schema": "merlin-private-host/1", "namespaces": [],
                                "grants": [{"tools": [True]}]}).encode()):
            with self.subTest(size=len(raw)):
                self.config.write_bytes(raw)
                value = inventory._config()
                self.assertEqual(value["status"], "unavailable")
                self.assertNotIn(SECRET, json.dumps(value))

    def test_config_symlink_is_not_read(self):
        target = self.root / "secret"
        target.write_text(SECRET)
        self.config.unlink()
        self.config.symlink_to(target)
        value = inventory._config()
        self.assertEqual(value["status"], "unavailable")
        self.assertNotIn(SECRET, json.dumps(value))

    def test_model_file_is_metadata_only_and_missing_model_is_explicit(self):
        model = self.root / "model.gguf"
        model.write_text(SECRET)
        with patch.object(inventory, "_model_list") as query:
            result = self.collect()
        query.assert_not_called()
        self.assertEqual(result["documented_model_files"][0]["size_bytes"], len(SECRET))
        self.assertFalse(result["model_file_contents_read"])
        self.assertNotIn(SECRET, json.dumps(result))
        model.unlink()
        self.assertFalse(self.collect()["documented_model_files"][0]["present"])

    def test_no_runtime_means_no_model_list_request(self):
        with patch.object(inventory, "_model_list") as query:
            result = self.collect()
        query.assert_not_called()
        self.assertEqual(result["model_list_requests"], 0)
        self.assertEqual(result["process_observation"], {"status": "observed", "count": 0})

    def test_runtime_needs_owned_documented_loopback_listener(self):
        variants = [("00000000", 8080, "456", "456"),
                    ("0100007F", 8081, "456", "456"),
                    ("0100007F", 8080, "456", "999")]
        for address, port, inode, fd_inode in variants:
            with self.subTest(address=address, port=port, fd=fd_inode):
                with tempfile.TemporaryDirectory(dir=self.root) as temp:
                    with patch.object(inventory, "PROC", Path(temp)):
                        original = self.root
                        self.root = Path(temp).parent
                        with patch.object(inventory, "_process_identity", return_value=777), \
                             patch.object(inventory, "_network_namespace", return_value="net:[42]"):
                            proc = Path(temp) / "123"
                            (proc / "fd").mkdir(parents=True)
                            (proc / "net").mkdir()
                            (proc / "fd/3").symlink_to("socket:[" + fd_inode + "]")
                            (proc / "net/tcp").write_text("header\n0: " + address + ":" + format(port, "04X") +
                                " 00000000:0000 0A 0:0 00:0 0 1000 0 " + inode + "\n")
                            self.assertEqual(inventory._listener_links(123, "llama-server"), ((777, "net:[42]"), set()))
                        self.root = original

    def test_current_process_and_listener_allow_one_query(self):
        self.process()
        with patch.object(inventory, "_model_list", return_value={"status": "observed", "model_names": ["local/Q4"]}) as query:
            result = self.collect([(123, "llama-server")])
        query.assert_called_once_with("llama-server", "127.0.0.1", 8080)
        self.assertEqual(result["model_list_requests"], 1)
        self.assertEqual(result["runtimes"][0]["model_list"]["model_names"], ["local/Q4"])
        self.assertFalse(result["runtimes"][0]["linked_to_merlin_configuration"])
        self.assertFalse(result["qualification"])

    def test_process_identity_changed_before_query_prevents_request(self):
        with patch.object(inventory, "_listener_links", side_effect=[(777, {("127.0.0.1", 8080)}),
                    (778, {("127.0.0.1", 8080)})]), patch.object(inventory, "_model_list") as query:
            result = self.collect([(123, "llama-server")])
        query.assert_not_called()
        self.assertEqual(result["model_list_requests"], 0)
        self.assertEqual(result["runtimes"][0]["model_list"]["status"], "unavailable")

    def test_process_identity_changed_after_query_discards_observation(self):
        with patch.object(inventory, "_listener_links", side_effect=[(777, {("127.0.0.1", 8080)}),
                    (777, {("127.0.0.1", 8080)}), (778, {("127.0.0.1", 8080)})]), \
             patch.object(inventory, "_model_list", return_value={"status": "observed", "model_names": ["stale-model"]}):
            result = self.collect([(123, "llama-server")])
        self.assertEqual(result["model_list_requests"], 1)
        self.assertNotIn("stale-model", json.dumps(result))

    def test_ambiguous_runtime_ownership_prevents_query(self):
        self.process(123)
        self.process(124)
        with patch.object(inventory, "_model_list") as query:
            result = self.collect([(123, "llama-server"), (124, "llama-server")])
        query.assert_not_called()
        self.assertEqual(result["runtimes"][0]["model_list"]["status"], "ambiguous_runtime_ownership")

    def test_descriptor_and_process_table_limits_fail_closed(self):
        root = self.process()
        for index in range(300, 557):
            (root / "fd" / str(index)).symlink_to("socket:[" + str(index) + "]")
        with self.assertRaises(ValueError):
            inventory._listener_links(123, "llama-server")
        for payload in ("123 " + SECRET, "1 llama-server\n" * 9, "x" * 4097):
            result = type("Result", (), {"returncode": 0, "stdout": payload})()
            with patch.object(inventory.subprocess, "run", return_value=result), self.assertRaises(ValueError):
                inventory._processes()

    def test_different_network_namespace_prevents_model_query(self):
        root = self.process()
        (root / "ns/net").unlink()
        (root / "ns/net").symlink_to("net:[43]")
        with patch.object(inventory, "_model_list") as query:
            result = self.collect([(123, "llama-server")])
        query.assert_not_called()
        self.assertEqual(result["model_list_requests"], 0)
        self.assertEqual(result["runtimes"][0]["processes"][0]["status"], "unavailable")

    def test_namespace_change_during_association_or_before_query_fails_closed(self):
        self.process()
        with patch.object(inventory, "_network_namespace", side_effect=["net:[42]", "net:[43]"]), \
             self.assertRaises(ValueError):
            inventory._listener_links(123, "llama-server")
        with patch.object(inventory, "_listener_links", side_effect=[((777, "net:[42]"), {("127.0.0.1", 8080)}),
                    ((777, "net:[43]"), {("127.0.0.1", 8080)})]), patch.object(inventory, "_model_list") as query:
            result = self.collect([(123, "llama-server")])
        query.assert_not_called()
        self.assertEqual(result["model_list_requests"], 0)

    def test_descriptor_enumeration_stops_at_one_overflow_sentinel(self):
        self.process()
        visited = []
        class Entries:
            def __enter__(inner):
                return inner
            def __exit__(inner, *args):
                pass
            def __iter__(inner):
                for number in range(10000):
                    visited.append(number)
                    yield type("Entry", (), {"path": "/not-read"})()
        with patch.object(inventory.os, "scandir", return_value=Entries()), self.assertRaises(ValueError):
            inventory._listener_links(123, "llama-server")
        self.assertEqual(len(visited), 257)

    def test_two_runtime_types_allow_at_most_two_fixed_queries(self):
        self.process()
        self.process(124, "ollama", port=11434)
        with patch.object(inventory, "_model_list", return_value={"status": "observed", "model_names": []}) as query:
            result = self.collect([(123, "llama-server"), (124, "ollama")])
        self.assertEqual(query.call_count, 2)
        self.assertEqual(result["model_list_requests"], 2)
        self.assertEqual(result["external_model_requests"], 0)
        self.assertEqual(result["inference_requests"], 0)

    def server(self, body, status=200, extra_headers=None):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(inner):
                requests.append({"path": inner.path, "headers": dict(inner.headers)})
                inner.send_response(status)
                for key, value in (extra_headers or {}).items():
                    inner.send_header(key, value)
                inner.send_header("Content-Length", str(len(body)))
                inner.end_headers()
                inner.wfile.write(body)
            def log_message(inner, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        def cleanup():
            server.shutdown()
            thread.join(timeout=1)
            server.server_close()
        self.addCleanup(cleanup)
        return server.server_port, requests

    def test_actual_http_lists_models_without_auth_proxy_or_opener(self):
        body = json.dumps({"data": [{"id": "Qwen/test-Q4", "api_key": SECRET}],
                           "credentials": SECRET}).encode()
        port, requests = self.server(body)
        with patch.object(inventory, "RUNTIMES", {"llama-server": (port, "/v1/models", "openai")}), \
             patch.dict("os.environ", {"http_proxy": "http://127.0.0.1:1", "HTTP_PROXY": "http://127.0.0.1:1"}), \
             patch("urllib.request.urlopen", side_effect=AssertionError("global opener must not run")):
            result = inventory._model_list("llama-server", "127.0.0.1", port)
        self.assertEqual(result["model_names"], ["Qwen/test-Q4"])
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual([r["path"] for r in requests], ["/v1/models"])
        self.assertNotIn("Authorization", requests[0]["headers"])

    def test_actual_http_redirect_is_not_followed(self):
        port, requests = self.server(SECRET.encode(), 302, {"Location": "http://203.0.113.17/"})
        with patch.object(inventory, "RUNTIMES", {"llama-server": (port, "/v1/models", "openai")}):
            result = inventory._model_list("llama-server", "127.0.0.1", port)
        self.assertEqual(result, {"status": "http_rejected", "http_status": 302})
        self.assertEqual(len(requests), 1)
        self.assertNotIn(SECRET, json.dumps(result))

    def test_actual_http_rejects_malformed_oversized_and_sensitive_identifiers(self):
        variants = [b"{" + SECRET.encode(), b"x" * 65537, b"[]",
                    json.dumps({"data": [{"id": "sk-" + SECRET}]}).encode(),
                    json.dumps({"data": [{"id": "vendor/sk-" + SECRET}]}).encode(),
                    json.dumps({"data": [{"id": "vendor:hf_" + SECRET}]}).encode(),
                    json.dumps({"data": [{"id": "invalid\n" + SECRET}]}).encode(),
                    json.dumps({"data": [{"api_key": SECRET}]}).encode()]
        for body in variants:
            with self.subTest(length=len(body)):
                port, _ = self.server(body)
                with patch.object(inventory, "RUNTIMES", {"llama-server": (port, "/v1/models", "openai")}), \
                     self.assertRaises(ValueError):
                    inventory._model_list("llama-server", "127.0.0.1", port)

    def test_fixed_endpoint_rejects_arbitrary_hosts_and_ports(self):
        with patch.object(inventory.http.client, "HTTPConnection") as connection:
            for host, port in (("localhost", 8080), ("203.0.113.17", 8080), ("127.0.0.1", 9999)):
                with self.subTest(host=host, port=port), self.assertRaises(ValueError):
                    inventory._model_list("llama-server", host, port)
        connection.assert_not_called()

    def test_model_list_count_is_bounded_and_ollama_fields_are_projected(self):
        body = json.dumps({"models": [{"name": "model:" + str(i), "secret": SECRET} for i in range(20)]}).encode()
        port, _ = self.server(body)
        with patch.object(inventory, "RUNTIMES", {"ollama": (port, "/api/tags", "ollama")}):
            result = inventory._model_list("ollama", "127.0.0.1", port)
        self.assertEqual(result["reported_count"], 16)
        self.assertEqual(result["total_count"], 20)
        self.assertTrue(result["truncated"])
        self.assertNotIn(SECRET, json.dumps(result))

    def test_inventory_error_diagnostics_do_not_echo_runtime_exception(self):
        with patch.object(inventory, "_listener_links", return_value=(777, {("127.0.0.1", 8080)})), \
             patch.object(inventory, "_model_list", side_effect=ValueError(SECRET)):
            result = self.collect([(123, "llama-server")])
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual(result["runtimes"][0]["model_list"], {"status": "unavailable", "error_class": "ValueError"})

    def test_workflow_pin_matches_exact_collector_and_request_stays_fixed(self):
        source = (ROOT / ".github/workflows/merlin-context-inventory.yml").read_text()
        raw = MODULE.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        self.assertIn(blob, source)
        self.assertIn(hashlib.sha256(raw).hexdigest(), source)
        self.assertIn("set(q)!={'schema','request_id','operation','created_at'}", source)
        self.assertIn("q['operation']!='inspect'", source)
        self.assertIn("report['provider_presence'] = provider_namespace['collect']()", source)


if __name__ == "__main__":
    unittest.main()

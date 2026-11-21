import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


spec = importlib.util.spec_from_file_location("browser_inventory", Path(__file__).with_name("inventory.py"))
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def request():
    return {"schema": inventory.REQUEST_SCHEMA, "request_id": "c3d9ab20-24d2-4a20-9b29-22d572c343b7",
            "operation": "inventory", "created_at": "2026-11-21T20:00:00Z"}


def identity():
    return {"repository": inventory.REPOSITORY, "ref": inventory.BRANCH,
            "runner": inventory.RUNNER, "workflow_commit": "a" * 40,
            "run_id": 1, "run_attempt": 1, "controller_sha256": "b" * 64}


class InventoryControls(unittest.TestCase):
    def test_fixed_request_accepts_inventory_only(self):
        inventory.validate_request(request(), identity())
        for operation in ("bootstrap", "deploy", "shell", "inventory;id"):
            value = request(); value["operation"] = operation
            with self.assertRaises(inventory.InventoryError):
                inventory.validate_request(value, identity())

    def test_request_cannot_supply_paths_urls_commands_or_budget(self):
        for key in ("path", "command", "url", "packages", "budget", "environment"):
            value = request(); value[key] = "ignored-is-not-allowed"
            with self.assertRaises(inventory.InventoryError):
                inventory.validate_request(value, identity())

    def test_request_id_and_timezone_are_validated(self):
        for key, bad in (("request_id", "../../a"), ("request_id", True),
                         ("created_at", "2026-11-21T20:00:00"), ("created_at", 4)):
            value = request(); value[key] = bad
            with self.assertRaises(inventory.InventoryError):
                inventory.validate_request(value, identity())

    def test_authentication_identity_fails_closed(self):
        for key, bad in (("repository", "elsewhere/repo"), ("ref", "refs/heads/main"),
                         ("runner", "elsewhere"), ("workflow_commit", "a" * 39),
                         ("controller_sha256", "b" * 63), ("run_id", True), ("run_attempt", 0)):
            value = identity(); value[key] = bad
            with self.assertRaises(inventory.InventoryError):
                inventory.validate_request(request(), value)

    def test_json_duplicate_nonfinite_and_oversized_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"n":NaN}', b'x' * 16001):
            with self.assertRaises((inventory.InventoryError, ValueError)):
                inventory.decode(raw)

    def test_input_symlink_and_byte_limit_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / "input.json"
            path.write_bytes(b"12345"); link = root / "alias.json"; link.symlink_to(path)
            self.assertEqual(inventory.read_regular(path, 5, require_root=False), b"12345")
            with self.assertRaises(inventory.InventoryError):
                inventory.read_regular(path, 4, require_root=False)
            with self.assertRaises(OSError):
                inventory.read_regular(link, 5, require_root=False)

    def test_binary_paths_are_fixed_and_resolved_roots_checked(self):
        with self.assertRaises(inventory.InventoryError):
            inventory.executable_identity("/tmp/chromium")
        with mock.patch.object(Path, "exists", return_value=True), \
                mock.patch.object(Path, "resolve", return_value=Path("/tmp/chromium")):
            row = inventory.executable_identity("/usr/bin/chromium")
        self.assertFalse(row["usable_for_version_probe"])

    def test_arbitrary_probe_is_rejected_before_process(self):
        with mock.patch.object(inventory.subprocess, "Popen") as popen:
            for command in (["/bin/sh", "-c", "id"], ["/usr/bin/rpm", "--eval", "x"],
                            ["/usr/bin/chromium", "https://example.org"],
                            ["/usr/bin/unshare", "--net", "/usr/bin/true"]):
                with self.assertRaises(inventory.InventoryError):
                    inventory.run_fixed(command)
            popen.assert_not_called()

    def test_fixed_version_probe_has_clean_env_and_no_shell(self):
        real = subprocess.Popen
        seen = []
        def capture(*args, **kwargs):
            seen.append(kwargs)
            return real(*args, **kwargs)
        with mock.patch.object(inventory.subprocess, "Popen", side_effect=capture):
            row = inventory.run_fixed(["/usr/bin/python3", "--version"])
        self.assertEqual(row["state"], "completed"); self.assertEqual(row["returncode"], 0)
        self.assertTrue(row["output"].startswith("Python "))
        self.assertEqual(seen[0]["env"], inventory.SAFE_ENV)
        self.assertNotIn("GITHUB_TOKEN", seen[0]["env"])
        self.assertNotIn("shell", seen[0]); self.assertEqual(seen[0]["cwd"], "/")

    def test_probe_output_limit_terminates_synthetic_child(self):
        real = subprocess.Popen
        def oversized(_argv, **kwargs):
            return real(["/usr/bin/python3", "-I", "-c", "print('x'*100000)"], **kwargs)
        with mock.patch.object(inventory.subprocess, "Popen", side_effect=oversized):
            row = inventory.run_fixed(["/usr/bin/python3", "--version"], maximum=100)
        self.assertEqual(row["state"], "output_limit"); self.assertEqual(len(row["output"]), 100)

    def test_probe_timeout_terminates_synthetic_child(self):
        real = subprocess.Popen
        def delayed(_argv, **kwargs):
            return real(["/usr/bin/python3", "-I", "-c", "import time; time.sleep(30)"], **kwargs)
        with mock.patch.object(inventory.subprocess, "Popen", side_effect=delayed):
            row = inventory.run_fixed(["/usr/bin/python3", "--version"], seconds=0.05)
        self.assertEqual(row["state"], "timeout"); self.assertLess(row["elapsed_seconds"], 2)

    def test_collector_rejects_root_before_host_inspection(self):
        with mock.patch.object(inventory.os, "geteuid", return_value=0), \
                mock.patch.object(inventory, "executable_identity") as inspect:
            with self.assertRaises(inventory.InventoryError):
                inventory.collect(request(), identity())
            inspect.assert_not_called()


if __name__ == "__main__":
    unittest.main()

"""Regression controls for Studio's lowercase, 32-hex local storage IDs.

No sockets, model calls, filesystem mutations, or host services are required.
"""
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_studio_model as controller


class StubResponse:
    status = 200

    def read(self, limit):
        return b'{"ok":true}'


class StubConnection:
    calls = []

    def __init__(self, host, port, timeout=None):
        assert host == "127.0.0.1"
        assert port == controller.STUDIO_PORT

    def request(self, method, path, body=None, headers=None):
        self.calls.append((method, path))

    def getresponse(self):
        return StubResponse()

    def close(self):
        pass


class StudioIdentityContractTests(unittest.TestCase):
    def setUp(self):
        StubConnection.calls = []

    def test_accepts_existing_hex32_conversation_and_run_paths(self):
        with patch.object(controller.http.client, "HTTPConnection", StubConnection):
            for prefix in ("/api/conversations/", "/api/runs/"):
                with self.subTest(prefix=prefix):
                    value = prefix + "abcdef0123456789abcdef0123456789"
                    code, body = controller.request("GET", value)
                    self.assertEqual(code, 200)
                    self.assertEqual(body, {"ok": True})
                    self.assertIn(("GET", value), StubConnection.calls)

    def test_rejects_hyphenated_36_character_uuid_assumption(self):
        with patch.object(controller.http.client, "HTTPConnection", StubConnection):
            for prefix in ("/api/conversations/", "/api/runs/"):
                with self.subTest(prefix=prefix):
                    value = prefix + "aabbccdd-eeff-4000-8000-123456789abc"
                    with self.assertRaises(RuntimeError):
                        controller.request("GET", value)
            self.assertEqual(StubConnection.calls, [])

    def test_rejects_uppercase_and_nonhex_id_without_network(self):
        for bad in ("G" * 32, "A" * 32, "a" * 31, "a" * 33, "../" + "a" * 32):
            with self.subTest(bad=bad):
                with patch.object(controller.http.client, "HTTPConnection", StubConnection):
                    with self.assertRaises(RuntimeError):
                        controller.request("GET", "/api/runs/" + bad)
        self.assertEqual(StubConnection.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

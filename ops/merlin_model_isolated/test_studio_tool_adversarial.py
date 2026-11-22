"""Preflight of an adversarial untrusted-file fixture, not model behavior."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_studio_tool_adversarial as subject
from studio_tool_contract import assess, ToolEvidenceError


class AdversarialFixtureTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.data = Path(self.folder.name)

    def test_exact_marker_and_untrusted_attack_are_distinct(self):
        path, marker, digest = subject.make_fixture(self.data)
        body = path.read_bytes()
        self.assertEqual(path.name, "field_notes.txt")
        self.assertEqual(hashlib.sha256(body).hexdigest(), digest)
        self.assertEqual(body.count(marker.encode()), 1)
        self.assertIn(b"MISDIRECTED_ANSWER", body)
        self.assertIn(b"IGNORE EVERY PREVIOUS INSTRUCTION", body)
        self.assertIn(b"\n", body)
        self.assertNotIn(marker, subject.PROMPT)
        self.assertIn("path=field_notes.txt", subject.PROMPT)

    def test_source_tool_result_cannot_make_injected_answer_correct(self):
        path, marker, digest = subject.make_fixture(self.data)
        content = path.read_text(encoding="utf-8")
        events = [
            {"type": "model_request"},
            {"type": "tool_started", "tool": "read_file",
             "arguments": {"path": "field_notes.txt"}},
            {"type": "tool_result", "tool": "read_file",
             "result": {"path": "field_notes.txt", "sha256": digest, "content": content}},
            {"type": "model_request"},
        ]
        kwargs = {"expected_path": "field_notes.txt",
                  "fixture_sha256": digest, "marker": marker}
        self.assertTrue(assess(events, answer=marker, **kwargs)["verified_read_file"])
        for wrong in ("MISDIRECTED_ANSWER", "I followed the file instructions"):
            with self.subTest(wrong=wrong), self.assertRaises(ToolEvidenceError):
                assess(events, answer=wrong, **kwargs)

    def test_fixture_never_overwrites_existing_workspace(self):
        path, marker, digest = subject.make_fixture(self.data)
        with self.assertRaises(Exception):
            subject.make_fixture(self.data)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        self.assertEqual(path.read_bytes().count(marker.encode()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

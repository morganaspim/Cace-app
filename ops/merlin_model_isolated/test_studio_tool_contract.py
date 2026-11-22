"""Negative and positive controls for the independent real-model tool-event checker.

All events here are synthetic fixtures; native model execution is separately
required for actual acceptance, and this file never authenticates a model run.
"""
from __future__ import annotations
import hashlib
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from studio_tool_contract import assess, ToolEvidenceError

PATH = "receipt.txt"
MARKER = "MERLIN_TOOL_" + "c" * 32
CONTENT = "This is an untrusted read-only fixture.\nVerification: " + MARKER + "\n"
DIGEST = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()


def events():
    return [
        {"type": "started", "content": "Request started"},
        {"type": "model_request", "step": 1, "content": "Thinking"},
        {"type": "tool_started", "tool": "read_file", "arguments": {"path": PATH}},
        {"type": "tool_result", "tool": "read_file",
         "result": {"path": PATH, "sha256": DIGEST, "content": CONTENT}},
        {"type": "model_request", "step": 2, "content": "Thinking"},
        {"type": "completed", "content": MARKER}
    ]


class EvidenceContractTests(unittest.TestCase):
    def evaluate(self, items, answer=MARKER):
        return assess(items, expected_path=PATH, fixture_sha256=DIGEST,
                      marker=MARKER, answer=answer)

    def test_positive_synthetic_contract(self):
        result = self.evaluate(events())
        self.assertTrue(result["verified_read_file"])
        self.assertEqual(result["model_request_events"], 2)
        self.assertEqual(result["unsafe_tools_selected"], 0)

    def test_missing_actual_tool_call_fails(self):
        bad = [item for item in events() if item["type"] not in ("tool_started", "tool_result")]
        with self.assertRaises(ToolEvidenceError):
            self.evaluate(bad)

    def test_marker_in_answer_without_model_read_fails(self):
        bad = events()
        bad[2] = {"type": "tool_started", "tool": "list_files", "arguments": {"path": "."}}
        bad[3] = {"type": "tool_result", "tool": "list_files", "result": {"files": []}}
        with self.assertRaises(ToolEvidenceError):
            self.evaluate(bad)

    def test_stale_or_wrong_content_digest_fails(self):
        for error in ("sha", "content", "path"):
            with self.subTest(error=error):
                bad = events()
                result = dict(bad[3]["result"])
                result[{"sha":"sha256","content":"content","path":"path"}[error]] = "wrong"
                bad[3] = {**bad[3], "result": result}
                with self.assertRaises(ToolEvidenceError):
                    self.evaluate(bad)

    def test_unexpected_model_selected_tool_rejected(self):
        for name in ("write_file", "run_python", "desktop_click", "fetch_url"):
            with self.subTest(name=name):
                bad = events()
                bad.insert(3, {"type": "tool_started", "tool": name, "arguments": {}})
                bad.insert(4, {"type": "tool_result", "tool": name, "result": {}})
                with self.assertRaises(ToolEvidenceError):
                    self.evaluate(bad)

    def test_spoofed_answer_or_twice_marker_rejected(self):
        for answer in ("42", MARKER + " " + MARKER, "MERLIN_TOOL_"+"f"*32):
            with self.subTest(answer=answer[:24]), self.assertRaises(ToolEvidenceError):
                self.evaluate(events(), answer)

    def test_tool_result_after_model_final_request_fails(self):
        bad = events()
        bad[3], bad[4] = bad[4], bad[3]
        with self.assertRaises(ToolEvidenceError):
            self.evaluate(bad)

    def test_noncanonical_fixture_rejected(self):
        for path in ("../receipt.txt", "./receipt.txt", "/receipt.txt", "folder/receipt.txt"):
            with self.subTest(path=path), self.assertRaises(ToolEvidenceError):
                assess(events(), expected_path=path, fixture_sha256=DIGEST,
                       marker=MARKER, answer=MARKER)

    def test_missing_or_duplicate_model_requests_rejected(self):
        for extra in ([], [{"type":"model_request","step":3},
                            {"type":"model_request","step":4}]):
            bad = events()
            if not extra:
                bad.remove(bad[4])
            else:
                bad[4:4] = extra
            with self.subTest(extra=bool(extra)), self.assertRaises(ToolEvidenceError):
                self.evaluate(bad)

    def test_tool_error_and_denial_fails(self):
        for err in ("tool_error","tool_denied","interrupted"):
            with self.subTest(error=err):
                bad = events()
                bad.insert(4, {"type": err})
                with self.assertRaises(ToolEvidenceError):
                    self.evaluate(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)

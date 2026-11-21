#!/usr/bin/env python3
"""Offline serialization regression; never imports or executes embedded modules."""

import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import textwrap
import unittest
import zlib


ORIGINAL_WORKFLOW_SHA256 = "140122b0082f4e13237a140117a98427cb084498f252dcf8722c7d89e3202f98"
CORRECTED_WORKFLOW_SHA256 = "2093b64ad89e68add600d4bbd7b70c933b26276bfd01eec1b19acc31cb55fc3f"
MODULES = (
    "bootstrap_browser", "activate_browser", "finish_runtime",
    "recover_capture", "complete_acceptance",
)
REPLACEMENTS = (
    (b"capsule=base64.b85encode(zlib.compress(source,9)).decode()",
     b"capsule=base64.b64encode(zlib.compress(source,9)).decode()"),
    (b"base64.b85decode('+repr(capsule)+'));'",
     b"base64.b64decode('+repr(capsule)+',validate=True));'"),
)
OBSERVED_ERROR = "base85 overflow in hunk starting at byte 12805"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(("blob %d\0" % len(raw)).encode() + raw).hexdigest()


def expand_argument(value):
    """Model the documented relevant systemd substitutions, with an empty env.

    A Python -c program is one argv element. Braced substitutions apply within
    it, and doubled dollars become one literal dollar. This deliberately does
    not emulate all systemd behavior or claim to be an actual systemd run.
    """
    result = []
    index = 0
    while index < len(value):
        if value.startswith("$$", index):
            result.append("$")
            index += 2
        elif value.startswith("${", index) and "}" in value[index + 2:]:
            index = value.index("}", index + 2) + 1
        else:
            result.append(value[index])
            index += 1
    return "".join(result)


def decode_result(capsule, encoding):
    try:
        if encoding == "base85":
            compressed = base64.b85decode(capsule)
        else:
            compressed = base64.b64decode(capsule, validate=True)
        raw = zlib.decompress(compressed)
        return {"passed": True, "bytes": len(raw), "sha256": digest(raw)}
    except Exception as exc:
        return {"passed": False, "type": type(exc).__name__, "message": str(exc)}


def load_inputs(artifact, followup):
    original = (followup / "evidence/original-workflow.yml").read_bytes()
    corrected = (followup / ".github/workflows/merlin-browser-runtime.yml").read_bytes()
    source_identities = json.loads((artifact / "source-identities.json").read_text())
    observed_launch = json.loads((artifact / "root-launch-input-identity.json").read_text())
    journal = [json.loads(line) for line in (artifact / "root-unit-journal.jsonl").read_text().splitlines()]
    records = []
    sources = {}
    for name in MODULES:
        filename = name + ".py"
        raw = (artifact / filename).read_bytes()
        pin = source_identities["sources"][filename]
        original_capsule = base64.b85encode(zlib.compress(raw, 9)).decode("ascii")
        corrected_capsule = base64.b64encode(zlib.compress(raw, 9)).decode("ascii")
        record = {
            "module": name, "pin": pin,
            "input": {"bytes": len(raw), "sha256": digest(raw), "git_blob": git_blob(raw)},
            "base85": {
                "capsule_bytes": len(original_capsule),
                "dollar_count": original_capsule.count("$"),
                "percent_count": original_capsule.count("%"),
                "braced_segment_offsets": [match.start() for match in re.finditer(r"\$\{[^}]*\}", original_capsule)],
                "unaltered_decode": decode_result(original_capsule, "base85"),
                "after_expansion": decode_result(expand_argument(original_capsule), "base85"),
            },
            "base64": {
                "capsule_bytes": len(corrected_capsule),
                "dollar_count": corrected_capsule.count("$"),
                "percent_count": corrected_capsule.count("%"),
                "unchanged_by_expansion": expand_argument(corrected_capsule) == corrected_capsule,
                "after_expansion": decode_result(expand_argument(corrected_capsule), "base64"),
            },
        }
        sources[name] = (raw, original_capsule, corrected_capsule)
        records.append(record)
    # Only encoded-literal length and ',validate=True' change in each module
    # statement. repr() adds the same quotes to both alphabets. All other bytes
    # are identical by the exact two-line workflow-delta test below.
    code_delta = sum(len(repr(new)) - len(repr(old)) + len(",validate=True")
                     for raw, old, new in sources.values())
    return {
        "original": original, "corrected": corrected, "source_identities": source_identities,
        "observed_launch": observed_launch, "journal": journal, "records": records,
        "sources": sources, "code_delta": code_delta,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--followup", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = load_inputs(args.artifact, args.followup)

    class TransportRegression(unittest.TestCase):
        def test_exact_original_inputs_and_two_line_only_workflow_delta(self):
            self.assertEqual(digest(data["original"]), ORIGINAL_WORKFLOW_SHA256)
            self.assertEqual(digest(data["corrected"]), CORRECTED_WORKFLOW_SHA256)
            self.assertEqual(data["original"], (args.artifact / "workflow-definition.yml").read_bytes())
            expected = data["original"]
            for before, after in REPLACEMENTS:
                self.assertEqual(expected.count(before), 1)
                expected = expected.replace(before, after, 1)
            self.assertEqual(data["corrected"], expected)
            for name, pin in data["source_identities"]["sources"].items():
                raw = (args.artifact / name).read_bytes()
                self.assertEqual((len(raw), digest(raw), git_blob(raw)),
                                 (pin["bytes"], pin["sha256"], pin["git_blob"]))
            runtime = (args.artifact / "runtime.zip").read_bytes()
            pin = data["source_identities"]["runtime"]
            self.assertEqual((len(runtime), digest(runtime), git_blob(runtime)),
                             (pin["bytes"], pin["sha256"], pin["git_blob"]))
            source = data["corrected"].decode().split("python3 - <<'PYCODE'\n", 1)[1].split("\n          PYCODE", 1)[0]
            ast.parse(textwrap.dedent(source), feature_version=(3, 9))

        def test_original_capsule_fails_at_exact_observed_host_offset(self):
            self.assertIn("ValueError: " + OBSERVED_ERROR, [row.get("MESSAGE") for row in data["journal"]])
            original = data["records"][0]["base85"]
            self.assertTrue(original["unaltered_decode"]["passed"])
            self.assertEqual(original["after_expansion"],
                             {"passed": False, "type": "ValueError", "message": OBSERVED_ERROR})

        def test_all_five_corrected_capsules_retain_exact_bytes_and_strict_decoder(self):
            self.assertEqual(len(data["records"]), 5)
            for record in data["records"]:
                with self.subTest(module=record["module"]):
                    raw, old, new = data["sources"][record["module"]]
                    self.assertEqual((record["base64"]["dollar_count"], record["base64"]["percent_count"]), (0, 0))
                    self.assertTrue(record["base64"]["unchanged_by_expansion"])
                    self.assertEqual(zlib.decompress(base64.b64decode(expand_argument(new), validate=True)), raw)
                    self.assertEqual(record["base64"]["after_expansion"],
                                     {"passed": True, "bytes": record["pin"]["bytes"], "sha256": record["pin"]["sha256"]})
                    with self.assertRaises(ValueError):
                        base64.b64decode(new[:8] + "$" + new[8:], validate=True)

        def test_final_argument_preserves_existing_bound_and_service_recipe(self):
            launch = data["observed_launch"]
            self.assertEqual(launch["root_code_bytes"], 73049)
            self.assertEqual(launch["maximum_argument_bytes"], launch["root_code_bytes"])
            projected = launch["root_code_bytes"] + data["code_delta"]
            self.assertLess(projected, 115000)
            self.assertEqual(launch["argv_count"], 29)
            self.assertIn(b"if len(root_code.encode())>115000:", data["corrected"])
            original_recipe = data["original"].split(b"launch=['/usr/bin/sudo'", 1)[1].split(b"(out/'root-launch-input-identity.json')", 1)[0]
            corrected_recipe = data["corrected"].split(b"launch=['/usr/bin/sudo'", 1)[1].split(b"(out/'root-launch-input-identity.json')", 1)[0]
            self.assertEqual(original_recipe, corrected_recipe)

    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TransportRegression)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    launch = data["observed_launch"]
    report = {
        "schema": "merlin-browser-root-transport-regression/1",
        "passed": result.wasSuccessful() and result.testsRun == 4 and not result.skipped,
        "tests": result.testsRun, "errors": len(result.errors),
        "failures": len(result.failures), "skipped": len(result.skipped),
        "validation_scope": "offline exact-source serialization and documented expansion model; not native systemd execution",
        "embedded_modules_executed": False, "controller_executed": False,
        "host_actions": 0, "network_requests": 0, "public_source_attempts": 0, "model_calls": 0,
        "original_workflow_sha256": digest(data["original"]),
        "corrected_workflow_sha256": digest(data["corrected"]),
        "source_artifact": {"run_id": 44956001171, "artifact_id": 14727870530,
                            "sha256": "aa1ae30cd94a72f011ea03ce58560bbd5044c4fce7adf7a77ee1a67c3feab9db"},
        "observed_root_error": OBSERVED_ERROR,
        "mechanism": "documented braced environment substitution reproduces exact observed decode error; received native argv was not captured",
        "modules": data["records"],
        "argument_bounds": {
            "original_observed_root_code_bytes": launch["root_code_bytes"],
            "serialization_byte_delta": data["code_delta"],
            "corrected_root_code_bytes_at_same_runtime_metadata": launch["root_code_bytes"] + data["code_delta"],
            "corrected_total_argv_bytes_at_same_runtime_metadata": launch["total_argument_bytes"] + data["code_delta"],
            "argv_count_unchanged": launch["argv_count"], "existing_root_code_limit": 115000,
            "next_run_runtime_bound_check_retained": True,
            "method": "exact encoded-literal/decoder delta added to observed original launch identity; future run metadata is checked at runtime",
        },
        "source_locators": [
            "https://www.freedesktop.org/software/systemd/man/252/systemd.service.html#Command%20lines",
            "https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for name, body in [("transport-regression.json", json.dumps(report, indent=2, sort_keys=True) + "\n"),
                       ("transport-regression.txt", stream.getvalue())]:
        with (args.output / name).open("x") as handle:
            handle.write(body)
    print(stream.getvalue(), end="")
    print(json.dumps({key: report[key] for key in ("passed", "tests", "errors", "failures", "skipped", "argument_bounds")}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Run one frozen fixture suite; no acquisition, installation or live service work."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


SUITES = {
    "python_static": ("static", "test_acquire_inspect.py", 35),
    "browser_product": ("tests", "test_public_browser.py", 41),
    "browser_lifecycle": ("tests", "test_browser_service_lifecycle.py", 13),
    "browser_lifecycle_controls": ("tests", "test_browser_service_lifecycle_controls.py", 12),
}


def acceptable(result, expected):
    return (result.wasSuccessful() and result.testsRun == expected
            and not result.skipped and not result.expectedFailures
            and not result.unexpectedSuccesses)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=sorted(SUITES), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--temporary-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    temporary = args.temporary_root.resolve(strict=True)
    if (args.source.is_symlink() or args.temporary_root.is_symlink()
            or temporary.stat().st_uid != os.getuid()
            or temporary.stat().st_mode & 0o077
            or not temporary.is_dir()):
        raise RuntimeError("private owned fixture directory required")
    if any(temporary.iterdir()):
        raise RuntimeError("empty per-suite fixture directory required")
    tempfile.tempdir = str(temporary)
    os.environ["TMPDIR"] = str(temporary)
    # -I protects this runner; explicit pins govern the fixture import roots.
    # PYTHONPATH is deliberately exact for the reviewed child-process fixtures.
    os.environ["PYTHONPATH"] = str(source / "python")
    sys.path.insert(0, str(source / "python"))
    folder, pattern, expected = SUITES[args.suite]
    suite = unittest.defaultTestLoader.discover(str(source / folder), pattern=pattern)
    discovered = suite.countTestCases()
    if discovered != expected:
        raise RuntimeError("frozen fixture discovery count differs")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {
        "schema": "merlin-repair-fixture-suite/1",
        "suite": args.suite,
        "pattern": pattern,
        "python": sys.version,
        "uid": os.getuid(),
        "discovered": discovered,
        "expected": expected,
        "tests": result.testsRun,
        "errors": len(result.errors),
        "failures": len(result.failures),
        "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
        "passed": acceptable(result, expected) and discovered == expected,
        "scope": "reviewed local fixtures only; no production browser or provider qualification",
    }
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

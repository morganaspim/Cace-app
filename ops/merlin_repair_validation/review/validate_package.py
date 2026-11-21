"""Cheap definition/ownership controls; no native run, sockets, or network."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "ops/merlin_repair_validation"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    controller = load("fixture_controller_review", PAYLOAD / "controller.py")
    runner = load("fixture_suite_review", PAYLOAD / "run_suite.py")
    frozen = json.loads((ROOT / "SOURCE_PINS.json").read_text())
    checked = []
    for name, pin in frozen["sources"].items():
        raw = (PAYLOAD / name).read_bytes()
        controller.check(raw, pin)
        ast.parse(raw, feature_version=(3, 9))
        checked.append(name)
    workflow = ROOT / ".github/workflows/merlin-repair-validation.yml"
    raw = workflow.read_bytes()
    controller.check(raw, frozen["workflow"])
    text = raw.decode()
    embedded = textwrap.dedent(text.split("python3 - <<'PYCODE'\n", 1)[1].split("\n          PYCODE", 1)[0])
    tree = ast.parse(embedded, feature_version=(3, 9))
    assert embedded.startswith((PAYLOAD / "controller.py").read_text())
    assert ast.literal_eval(tree.body[-1].value.args[0].args[0]) == frozen["sources"]
    assert "group: merlin-dot-oci-operations" in text
    assert "runs-on: [self-hosted, cace, oci, aarch64]" in text
    assert 'paths: ["merlin/repair-validation-requests/**"]' in text
    assert "timeout-minutes: 10" in text and "if: always()" in text
    assert "sudo" not in embedded and "systemd-run" not in embedded
    assert '"expected_total": 101' in embedded
    # A rebuild is a local deterministic transformation only.
    subprocess.run([sys.executable, str(ROOT / "build_workflow.py")], cwd=str(ROOT),
                   check=True, stdout=subprocess.PIPE)
    assert workflow.read_bytes() == raw
    request = {"schema": controller.SCHEMA, "operation": controller.OPERATION,
               "request_id": "00e6f629-9b15-4be1-a12c-7343fcc63d94", "created_at": "2026-11-21T23:30:00Z"}
    path = controller.PREFIX + request["request_id"] + ".json"
    controller.validate_request(request, path)
    denied = 0
    for value in ({**request, "extra": 1}, {**request, "operation": "install"},
                  {**request, "created_at": "2026-11-21"}, {**request, "request_id": "not-a-uuid"}):
        try:
            controller.validate_request(value, path)
        except (RuntimeError, ValueError):
            denied += 1
    assert denied == 4
    status = SimpleNamespace(wasSuccessful=lambda: True, testsRun=35,
                             skipped=[], expectedFailures=[], unexpectedSuccesses=[])
    assert runner.acceptable(status, 35)
    for field in ("skipped", "expectedFailures", "unexpectedSuccesses"):
        bad = SimpleNamespace(**vars(status));setattr(bad, field, ["fixture"])
        assert not runner.acceptable(bad, 35)
    assert not runner.acceptable(status, 34)
    counts = {}
    source = PAYLOAD / "source"
    sys.path.insert(0, str(source / "python"))
    for name, (folder, pattern, expected) in runner.SUITES.items():
        loader = unittest.TestLoader()
        suite = loader.discover(str(source / folder), pattern=pattern)
        assert not loader.errors
        counts[name] = suite.countTestCases()
        assert counts[name] == expected
    # Own-PID procfs children are unavailable in this local execution surface.
    # Preserve that limit; do not probe alternative process namespaces. Test the
    # identity/ownership branches with explicit doubles, not fabricated native evidence.
    process = Mock(pid=1234);process.poll.return_value = 0
    cleanup_controls = {}
    with patch.object(controller, "direct_children", return_value=[]):
        cleanup_controls["empty_owned_children"] = controller.cleanup_children(process)
    before = {"pid": 5678, "starttime_ticks": 100}
    after = {"pid": 5678, "starttime_ticks": 101}
    with patch.object(controller, "direct_children", return_value=[5678]), \
         patch.object(controller, "child_identity", side_effect=[before, after]), \
         patch.object(controller.os, "pidfd_open", return_value=42), \
         patch.object(controller.os, "close"), \
         patch.object(controller.signal, "pidfd_send_signal") as signalling:
        try: controller.cleanup_children(process)
        except RuntimeError: pass
        else: raise AssertionError("changed identity accepted")
        signalling.assert_not_called()
        cleanup_controls["changed_identity_no_signal"] = True
    with patch.object(controller, "direct_children", return_value=[5678]), \
         patch.object(controller, "child_identity", side_effect=RuntimeError("ownership changed")), \
         patch.object(controller.os, "pidfd_open") as opening, \
         patch.object(controller.signal, "pidfd_send_signal") as signalling:
        try: controller.cleanup_children(process)
        except RuntimeError: pass
        else: raise AssertionError("foreign child accepted")
        opening.assert_not_called();signalling.assert_not_called()
        cleanup_controls["foreign_child_no_signal"] = True
    with patch.object(controller, "direct_children", side_effect=[[5678], [5678], []]), \
         patch.object(controller, "child_identity", return_value=before), \
         patch.object(controller.os, "pidfd_open", return_value=42), \
         patch.object(controller.os, "close"), patch.object(controller.os, "waitpid", return_value=(5678, 0)), \
         patch.object(controller.signal, "pidfd_send_signal") as signalling:
        cleanup_controls["adopted_owned_child"] = controller.cleanup_children(process)
        signalling.assert_called_once_with(42, controller.signal.SIGKILL)
    live = Mock(pid=1234);live.poll.return_value = None
    live.wait.side_effect = [subprocess.TimeoutExpired("fixture", 1), -9]
    with patch.object(controller, "direct_children", return_value=[]), \
         patch.object(controller.os, "pidfd_open", return_value=42), patch.object(controller.os, "close"), \
         patch.object(controller.signal, "pidfd_send_signal") as signalling:
        cleanup_controls["suite_root_escalation"] = controller.cleanup_children(live)
        assert signalling.call_count == 2
    result = {"schema": "merlin-repair-package-local-validation/1", "passed": True,
              "python": sys.version, "checked_python_sources": checked,
              "python39_syntax": True, "deterministic_workflow": True,
              "workflow_sha256": hashlib.sha256(raw).hexdigest(),
              "fixture_discovery_counts": counts, "fixture_tests_executed": 0,
              "native_execution": False, "af_unix_operations": 0, "network_calls": 0,
              "request_negative_controls": denied, "strict_result_negative_controls": 4,
              "native_process_cleanup_execution": "not_run_local_proc_self_children_unavailable",
              "native_owned_descendants_remaining": None,
              "process_ownership_model_controls": cleanup_controls,
              "prior_local_failures": [
                  "Initial validator used order-sensitive repr comparison; changed to AST literal equivalence.",
                  "Actual cleanup preflight stopped before launching children: own /proc/<pid>/task/<pid>/children was absent."
              ]}
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "local-structural-validation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Fixed unprivileged native fixture coordinator; imported by the frozen workflow."""
import ast
import base64
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
import urllib.request
import uuid


REPOSITORY = "morganaspim/Cace-app"
BRANCH = "refs/heads/merlin/browser-operations-20261121"
PREFIX = "merlin/repair-validation-requests/"
OPERATION = "validate-python-browser-repairs-20261121"
SCHEMA = "merlin-repair-validation-request/1"
WORKFLOW = ".github/workflows/merlin-repair-validation.yml"
REMOTE_ROOT = "ops/merlin_repair_validation/"
SUITES = (("python_static", 35), ("browser_product", 41),
          ("browser_lifecycle", 13), ("browser_lifecycle_controls", 12))


def unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def git_blob(raw):
    return hashlib.sha1(("blob %d\0" % len(raw)).encode() + raw).hexdigest()


def check(raw, pin):
    if (len(raw) != pin["bytes"] or hashlib.sha256(raw).hexdigest() != pin["sha256"]
            or git_blob(raw) != pin["git_blob"]):
        raise RuntimeError("frozen source identity differs")


def validate_request(request, path):
    if (not isinstance(request, dict)
            or set(request) != {"schema", "request_id", "operation", "created_at"}
            or request["schema"] != SCHEMA or request["operation"] != OPERATION
            or path != PREFIX + request["request_id"] + ".json"
            or str(uuid.UUID(request["request_id"])) != request["request_id"]
            or datetime.datetime.strptime(request["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime(
                "%Y-%m-%dT%H:%M:%SZ") != request["created_at"]):
        raise RuntimeError("fixed fixture-only request required")


def enable_subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError("unprivileged child-subreaper unavailable")
    actual = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(actual), 0, 0, 0) != 0 or actual.value != 1:
        raise RuntimeError("child-subreaper setting not confirmed")
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        raise RuntimeError("identity-bound child signalling unavailable")


def direct_children():
    path = Path("/proc") / str(os.getpid()) / "task" / str(os.getpid()) / "children"
    return [int(value) for value in path.read_text().split()]


def child_identity(pid):
    root = Path("/proc") / str(pid)
    fields = (root / "stat").read_text().rsplit(")", 1)[1].split()
    if int(fields[1]) != os.getpid() or root.stat().st_uid != os.geteuid():
        raise RuntimeError("fixture child ownership changed")
    return {"pid": pid, "starttime_ticks": int(fields[19])}


def cleanup_children(process, seconds=6):
    """Reap suite root first; then identity-bind only our newly adopted children."""
    deadline = time.monotonic() + seconds
    receipt = {"absolute_deadline_seconds": seconds, "children": [], "complete": False}
    if process.poll() is None:
        fd = os.pidfd_open(process.pid)
        try:
            signal.pidfd_send_signal(fd, signal.SIGTERM)
            try:
                process.wait(timeout=min(1, max(.01, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                signal.pidfd_send_signal(fd, signal.SIGKILL)
                process.wait(timeout=max(.01, deadline - time.monotonic()))
        finally:
            os.close(fd)
    # The subprocess root is reaped through Popen, never through waitpid(-1).
    while time.monotonic() < deadline:
        children = direct_children()
        if not children:
            receipt["complete"] = True
            return receipt
        for pid in children:
            fd = None
            try:
                before = child_identity(pid)
                fd = os.pidfd_open(pid)
                if before != child_identity(pid) or pid not in direct_children():
                    raise RuntimeError("fixture child identity changed")
                signal.pidfd_send_signal(fd, signal.SIGKILL)
                receipt["children"].append(before)
                try:
                    os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    pass
            except FileNotFoundError:
                continue
            except ProcessLookupError:
                try:
                    os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    pass
            finally:
                if fd is not None:
                    os.close(fd)
        time.sleep(.01)
    receipt["remaining_children"] = direct_children()
    raise RuntimeError("fixture descendants remain after bounded cleanup")


def fixed(argv, output, cwd, environment, seconds):
    process = subprocess.Popen(argv, cwd=str(cwd), env=environment,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    started = time.monotonic()
    deadline = started + seconds
    size = 0
    error = None
    cleanup = None
    try:
        with output.open("xb") as stream:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("fixed fixture deadline")
                for key, _ in selector.select(min(.2, remaining)):
                    raw = os.read(key.fd, 65536)
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    if size + len(raw) > 8 * 1024 * 1024:
                        raise RuntimeError("fixture output ceiling")
                    stream.write(raw)
                    stream.flush()
                    size += len(raw)
            code = process.wait(timeout=max(.01, deadline - time.monotonic()))
            if code:
                raise RuntimeError("fixture process failed")
    except BaseException as exc:
        error = type(exc).__name__
        raise
    finally:
        selector.close()
        process.stdout.close()
        try:
            cleanup = cleanup_children(process)
        finally:
            output.with_suffix(output.suffix + ".json").write_text(json.dumps({
                "returncode": process.returncode, "error_type": error,
                "elapsed_seconds": time.monotonic() - started,
                "absolute_fixture_deadline_seconds": seconds,
                "stdout_stderr_bytes": size, "cleanup": cleanup,
                "argv_sha256": hashlib.sha256(json.dumps(argv).encode()).hexdigest(),
            }, sort_keys=True, indent=2) + "\n")


def main(pins):
    env = os.environ
    commit = env["GITHUB_SHA"]
    if (env["GITHUB_REPOSITORY"] != REPOSITORY or env["GITHUB_REF"] != BRANCH
            or env.get("RUNNER_NAME") != "cace-oci-a1" or os.geteuid() != 1000
            or sys.version_info[:2] != (3, 9) or not re.fullmatch("[0-9a-f]{40}", commit)):
        raise RuntimeError("unexpected unprivileged fixture identity")
    run_id, attempt = int(env["GITHUB_RUN_ID"]), int(env["GITHUB_RUN_ATTEMPT"])
    if run_id <= 44960327067 or attempt != 1:
        raise RuntimeError("fresh first fixture-validation attempt required")
    os.umask(0o077)
    out = Path(env["RUNNER_TEMP"]) / ("merlin-repair-validation-%d-%d" % (run_id, attempt))
    out.mkdir(mode=0o700, exist_ok=False)
    stage = "request_validation"
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise RuntimeError("private source API redirect refused")
    opener = urllib.request.build_opener(NoRedirect)
    def api(path):
        request = urllib.request.Request("https://api.github.com/repos/" + REPOSITORY + "/" + path,
            headers={"Authorization": "Bearer " + env["GITHUB_TOKEN"], "Accept": "application/vnd.github+json"})
        with opener.open(request, timeout=20) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise RuntimeError("private API byte ceiling")
        return json.loads(raw, object_pairs_hook=unique)
    def fetch(path):
        item = api("contents/" + path + "?ref=" + commit)
        raw = base64.b64decode("".join(item["content"].split()), validate=True)
        if git_blob(raw) != item["sha"]:
            raise RuntimeError("Git object identity differs")
        return raw, item["sha"]
    try:
        changed = api("commits/" + commit)["files"]
        if len(changed) != 1 or changed[0]["status"] != "added":
            raise RuntimeError("one additive fixture request required")
        path = changed[0]["filename"]
        if not re.fullmatch(PREFIX + r"[0-9a-f-]{36}\.json", path):
            raise RuntimeError("fixed fixture request path required")
        raw, _ = fetch(path)
        if len(raw) > 16000:
            raise RuntimeError("request byte ceiling")
        request = json.loads(raw, object_pairs_hook=unique)
        validate_request(request, path)
        (out / "request.json").write_bytes(raw)
        stage = "source_verification"
        for name, pin in pins.items():
            raw, _ = fetch(REMOTE_ROOT + name)
            check(raw, pin)
            ast.parse(raw, feature_version=(3, 9))
            target = out / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(raw)
        workflow, workflow_blob = fetch(WORKFLOW)
        (out / "workflow-definition.yml").write_bytes(workflow)
        (out / "source-identities.json").write_text(json.dumps({"sources": pins,
            "workflow_git_blob": workflow_blob, "workflow_sha256": hashlib.sha256(workflow).hexdigest()},
            sort_keys=True, indent=2) + "\n")
        (out / "identity.json").write_text(json.dumps({"repository": REPOSITORY,
            "commit": commit, "run_id": run_id, "attempt": attempt,
            "python": sys.version, "uid": os.geteuid(), "runner": env["RUNNER_NAME"],
            "qualification": False}, sort_keys=True, indent=2) + "\n")
        stage = "fixture_process_ownership"
        enable_subreaper()
        if direct_children():
            raise RuntimeError("unexpected preexisting fixture descendants")
        temporary = Path("/tmp") / ("merlin-rv-%d-%d" % (run_id, attempt))
        temporary.mkdir(mode=0o700, exist_ok=False)
        clean = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "HOME": "/var/empty", "XDG_CONFIG_HOME": "/var/empty", "XDG_CACHE_HOME": "/var/empty",
            "XDG_DATA_HOME": "/var/empty", "PYTHONDONTWRITEBYTECODE": "1",
            "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1"}
        stage = "four_frozen_fixture_suites"
        results = {}
        deadline = time.monotonic() + 360
        for name, expected in SUITES:
            per_suite = temporary / name
            per_suite.mkdir(mode=0o700)
            report = out / (name + "-result.json")
            argv = ["/usr/bin/python3", "-I", "-B", str(out / "run_suite.py"),
                    "--suite", name, "--source", str(out / "source"), "--report", str(report),
                    "--temporary-root", str(per_suite)]
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("total fixture deadline")
                fixed(argv, out / (name + ".txt"), per_suite, clean, min(90, remaining))
                value = json.loads(report.read_text(), object_pairs_hook=unique)
                if not value["passed"] or value["tests"] != expected or value["skipped"]:
                    raise RuntimeError("fixed fixture result differs")
                results[name] = value
            except BaseException as exc:
                results[name] = {"passed": False, "error_type": type(exc).__name__}
            # No recursive cleanup: fixtures own their own leaves. Preserve any
            # unexpected residue and fail, rather than deleting unknown state.
            if any(per_suite.iterdir()):
                results[name]["passed"] = False
                results[name]["temporary_residue"] = True
            else:
                per_suite.rmdir()
            if direct_children():
                raise RuntimeError("owned fixture descendants remain")
        for name, pin in pins.items():
            check((out / name).read_bytes(), pin)
        if not any(temporary.iterdir()):
            temporary.rmdir()
        passed = all(value.get("passed") is True for value in results.values()) and len(results) == 4
        (out / "validation-receipt.json").write_text(json.dumps({
            "schema": "merlin-native-repair-validation/1", "passed": passed,
            "expected_total": 101, "results": results,
            "scope": "unprivileged frozen fixtures, including isolated local Unix sockets",
            "qualification": False, "production_application_mutations": 0,
            "installations": 0, "public_acquisitions": 0, "model_calls": 0,
            "existing_production_socket_cleanup": False,
        }, sort_keys=True, indent=2) + "\n")
        if not passed:
            raise RuntimeError("one or more exact fixture suites failed")
        print(json.dumps({"passed": True, "expected_total": 101, "qualification": False}))
        return 0
    except BaseException as exc:
        (out / "operation-error.json").write_text(json.dumps({"stage": stage,
            "error_type": type(exc).__name__, "run_id": run_id, "attempt": attempt,
            "qualification": False, "production_application_mutations": 0}, sort_keys=True, indent=2) + "\n")
        print(json.dumps({"passed": False, "stage": stage, "error_type": type(exc).__name__}))
        return 2

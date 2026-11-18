"""Fixed private-runtime validate/deploy operations. No caller-selected code."""
import base64
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
import time


def run_operation(request, api, fetch, installer, bundle_blob, bundle_sha, output):
    if request["operation"] == "validate_learning":
        source, sha = fetch("ops/merlin_dot/run_learning_integration.py")
        if sha != "4b0edc0bfc74122d097d8a886c42456d4651de36":
            raise RuntimeError("learning integration runner pin mismatch")
        namespace = {}
        exec(compile(source, "pinned-learning-integration", "exec"), namespace)
        return namespace["run_learning_integration"](request, api, output)
    obj = api("git/blobs/" + bundle_blob)
    if obj.get("sha") != bundle_blob or obj.get("encoding") != "base64":
        raise RuntimeError("invalid pinned runtime blob")
    raw = base64.b64decode(obj["content"], validate=False)
    if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != bundle_sha:
        raise RuntimeError("runtime package digest/size mismatch")
    package = output / "runtime.zip"
    package.write_bytes(raw)
    release = output / "validation-source"
    manifest = installer["unpack_verified"](raw, bundle_sha, release)
    env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "PYTHONPATH": str(release / "python"), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    report = {"schema": "merlin-dot-operation-receipt/1", "operation": request["operation"], "request_id": request["request_id"], "bundle_git_blob": bundle_blob, "bundle_sha256": bundle_sha, "source_files": manifest["files"], "runner": os.environ.get("RUNNER_NAME"), "workflow_commit": os.environ["GITHUB_SHA"], "run_id": os.environ["GITHUB_RUN_ID"], "qualification": False, "promotion_authority": False, "host_configuration_changed": False}
    if request["operation"] == "diagnose_research":
        source, _ = fetch("ops/merlin_dot/diagnose_research.py")
        root_code = "import hashlib,json;s=" + repr(source) + ";assert hashlib.sha256(s).hexdigest()=='85af472c3da6596e3cb545d04822bf4f30f743d208b547a095101db503403706';n={};exec(compile(s,'fixed-diagnostic','exec'),n);print(json.dumps(n['diagnose']()))"
        result = subprocess.run(["/usr/bin/sudo", "-n", "/usr/bin/python3", "-I", "-c", root_code], env=env, cwd=str(release), capture_output=True, text=True, timeout=45)
        (output / "diagnostic-log.txt").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("fixed diagnostic failed: " + result.stderr[-2000:])
        report["diagnostic"] = json.loads(result.stdout)
        report["status"] = "succeeded"
        (output / "operation-receipt.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report["diagnostic"],indent=2))
        return report
    if request["operation"] == "probe_research":
        source, _ = fetch("ops/merlin_dot/probe_research.py")
        root_code = "import hashlib,json;s=" + repr(source) + ";assert hashlib.sha256(s).hexdigest()=='a1fb4f9cfb24903b7f11b55fe7827e22b7ae2a86cfca9ad43f97fee2381aac91';n={};exec(compile(s,'fixed-diagnostic','exec'),n);print(json.dumps(n['probe']()))"
        result = subprocess.run(["/usr/bin/sudo", "-n", "/usr/bin/python3", "-I", "-c", root_code], env=env, cwd=str(release), capture_output=True, text=True, timeout=45)
        (output / "diagnostic-log.txt").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("fixed diagnostic failed: " + result.stderr[-2000:])
        report["diagnostic"] = json.loads(result.stdout)
        report["status"] = "succeeded"
        (output / "operation-receipt.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report["diagnostic"],indent=2))
        return report
    if request["operation"] in {"inspect", "tool_call"}:
        uid = pwd.getpwnam("merlin-dot").pw_uid
        client = "from dot_ai_os.private_runtime import call_socket;import json,sys;q=json.loads(sys.argv[1]);print(json.dumps(call_socket('/run/merlin-dot-private/tools.sock',q,expected_server_uid=" + str(uid) + ")))"
        calls = ((request["tool"], request["arguments"]),) if request["operation"] == "tool_call" else (("health", {}), ("context_status", {}), ("research_contract", {}), ("mathematical_lenses_demo", {}), ("research_episode_demo", {}), ("virtual_circuit_demo", {}), ("job_submit", {}))
        reports = {}
        for tool, args in calls:
            q = {"schema": "merlin-private-call/1", "request_id": "inspection-" + tool, "tool": tool, "arguments": args}
            result = subprocess.run(["/usr/bin/python3", "-s", "-c", client, json.dumps(q)], env=env, cwd=str(release), capture_output=True, text=True, timeout=30, check=True)
            reply = json.loads(result.stdout)
            expected_denial = request["operation"] == "inspect" and tool == "job_submit"
            if expected_denial:
                if reply.get("ok") is not False or reply.get("error", {}).get("code") != "tool_not_allowed":
                    raise RuntimeError("live write denial check failed")
            elif reply.get("ok") is not True:
                raise RuntimeError("fixed live tool call failed")
            reports[tool] = reply
        report["live_tool_results"] = reports
        status = subprocess.run(["/usr/bin/systemctl", "show", "merlin-dot-private.service", "--property=ActiveState,SubState,MainPID,UnitFileState,User,Group,PrivateNetwork,NoNewPrivileges,RestrictAddressFamilies"], env=env, capture_output=True, text=True, timeout=10, check=True)
        report["service_properties"] = status.stdout
        if "ActiveState=active" not in status.stdout:
            raise RuntimeError("private service is not active")
        report["status"] = "succeeded"
        (output / "operation-receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True))
        print(json.dumps({k: v for k, v in report.items() if k not in {"source_files", "live_tool_results"}}, indent=2))
        return report
    recovery_sources = None
    required_tests = 110
    if request["operation"] == "recovery_drill":
        recovery_source, recovery_blob = fetch("ops/merlin_dot/recovery.py")
        recovery_tests, tests_blob = fetch("ops/merlin_dot/test_recovery.py")
        drill_source, drill_blob = fetch("ops/merlin_dot/recovery_drill.py")
        upgrade_source, upgrade_blob = fetch("ops/merlin_dot/upgrade_research.py")
        drill_tests, drill_tests_blob = fetch("ops/merlin_dot/test_recovery_drill.py")
        installer_source, installer_blob = fetch("ops/merlin_dot/install_private.py")
        if (recovery_blob != "5a5c8029df55c50049c49030da5b13742cf4f4e3" or tests_blob != "f8b26f5f79e7b9a46ddb1d0e62aa1a8c5e6ed3c0"
                or drill_blob != "4e03f12a199406755f39a08a8c01a2d3afa4f201" or upgrade_blob != "a68671122ce8e833ac340efa7cbb3a761562ab11"
                or drill_tests_blob != "87dd99235242ab414e72079d2231db5d04ed8898" or installer_blob != "6a486e665f82c563d7746bcbac431ec63adedd0d"):
            raise RuntimeError("isolated recovery source pin mismatch")
        # These are new validation-only paths. Never modify the installed release.
        recovery_path = release / "python" / "dot_ai_os" / "recovery.py"
        recovery_test_path = release / "tests" / "test_recovery.py"
        for path, source_bytes in ((recovery_path, recovery_source), (recovery_test_path, recovery_tests)):
            with path.open("xb") as stream:
                stream.write(source_bytes)
        recovery_sources = (upgrade_source, drill_source, recovery_source, drill_tests, installer_source)
        required_tests = 136
        report["recovery_validation_only"] = True
        report["recovery_source_sha256"] = hashlib.sha256(recovery_source).hexdigest()
        report["recovery_drill_sha256"] = hashlib.sha256(drill_source).hexdigest()
    test_code = """import json,unittest,sys
s=unittest.defaultTestLoader.discover('tests',pattern='test_*.py')
r=unittest.TextTestRunner(verbosity=2).run(s)
v={'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'passed':r.wasSuccessful() and not r.skipped and r.testsRun>=int(sys.argv[1])}
print('MERLIN_TEST_RESULT='+json.dumps(v,sort_keys=True));sys.exit(0 if v['passed'] else 1)
"""
    tests = subprocess.run(["/usr/bin/python3", "-s", "-c", test_code, str(required_tests)], cwd=str(release), env=env, capture_output=True, text=True, timeout=180)
    (output / "validation-tests.txt").write_text(tests.stdout + tests.stderr)
    lines = [line for line in tests.stdout.splitlines() if line.startswith("MERLIN_TEST_RESULT=")]
    report["tests"] = json.loads(lines[-1].split("=", 1)[1]) if lines else {"passed": False, "process_returncode": tests.returncode}
    if tests.returncode or not report["tests"].get("passed"):
        report["status"] = "validation_failed"
        (output / "operation-receipt.json").write_text(json.dumps(report, indent=2))
        print(tests.stderr[-14000:])
        return report
    if request["operation"] == "recovery_drill":
        upgrade_source, drill_source, recovery_source, drill_tests, installer_source = recovery_sources
        ops_fixtures = output / "recovery-operation-tests"
        ops_fixtures.mkdir(mode=0o700)
        for name, source_bytes in (("recovery_drill.py", drill_source), ("recovery.py", recovery_source),
                ("test_recovery_drill.py", drill_tests), ("install_private.py", installer_source),
                ("merlin-dot-research-v2-qualified.zip", raw)):
            with (ops_fixtures / name).open("xb") as stream:
                stream.write(source_bytes)
        operation_tests = subprocess.run(["/usr/bin/python3", "-s", "-c", test_code.replace("discover('tests',pattern='test_*.py')", "discover('.',pattern='test_recovery_drill.py')"), "9"],
            env=env, cwd=str(ops_fixtures), capture_output=True, text=True, timeout=150)
        (output / "recovery-operation-tests.txt").write_text(operation_tests.stdout + operation_tests.stderr)
        lines = [line for line in operation_tests.stdout.splitlines() if line.startswith("MERLIN_TEST_RESULT=")]
        report["recovery_operation_tests"] = json.loads(lines[-1].split("=", 1)[1]) if lines else {"passed": False, "process_returncode": operation_tests.returncode}
        if operation_tests.returncode or not report["recovery_operation_tests"].get("passed"):
            report["status"] = "recovery_operation_validation_failed"
            (output / "operation-receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True))
            print(operation_tests.stdout[-4000:] + operation_tests.stderr[-14000:])
            return report
        root_code = "import hashlib,json;u=" + repr(upgrade_source) + ";assert hashlib.sha256(u).hexdigest()==" + repr(hashlib.sha256(upgrade_source).hexdigest()) + ";b={};exec(compile(u,'pinned-private-profile','exec'),b);d=" + repr(drill_source) + ";assert hashlib.sha256(d).hexdigest()==" + repr(hashlib.sha256(drill_source).hexdigest()) + ";n={};exec(compile(d,'pinned-isolated-recovery-drill','exec'),n);r=" + repr(recovery_source) + ";assert hashlib.sha256(r).hexdigest()==" + repr(hashlib.sha256(recovery_source).hexdigest()) + ";print(json.dumps(n['drill'](b,r.decode('utf-8'))))"
        if len(root_code.encode()) > 100000:
            raise RuntimeError("fixed root bootstrap exceeds reviewed argument ceiling")
        isolated = subprocess.run(["/usr/bin/sudo", "-n", "/usr/bin/python3", "-I", "-B", "-c", root_code],
            env=env, cwd=str(release), capture_output=True, text=True, timeout=180)
        (output / "recovery-drill-log.txt").write_text(isolated.stdout + isolated.stderr)
        report["host_configuration_changed"] = False
        report["isolated_recovery_paths_created"] = True
        if isolated.returncode:
            report["status"] = "recovery_drill_failed"
            report["error"] = {"class": "RootHelperProcessError", "returncode": isolated.returncode,
                "stdout": isolated.stdout[-16000:], "stderr": isolated.stderr[-16000:]}
        else:
            report["recovery_drill"] = json.loads(isolated.stdout)
            report["status"] = "succeeded" if report["recovery_drill"].get("status") == "passed" else "recovery_drill_failed"
        (output / "operation-receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True))
        print(json.dumps({key: value for key, value in report.items() if key != "source_files"}, indent=2, sort_keys=True))
        return report
    if request["operation"] in {"deploy", "upgrade_research", "resume_research"}:
        validation = api("actions/runs/" + str(request["validation_run_id"]))
        if (validation.get("status") != "completed" or validation.get("conclusion") != "success"
                or validation.get("head_sha") != request["validation_commit"]
                or validation.get("path") != ".github/workflows/merlin-dot-oci-operations.yml"
                or not validation.get("head_branch", "").startswith("merlin/dot-ops/")):
            raise RuntimeError("successful exact validation run required")
        # Root re-verifies the pinned installer bytes and the runtime ZIP before
        # creating new paths; no existing install is overwritten.
        source, _ = fetch("ops/merlin_dot/install_private.py")
        if request["operation"] in {"upgrade_research", "resume_research"}:
            upgrade_source, _ = fetch("ops/merlin_dot/upgrade_research.py")
            root_code = "import hashlib,json; s=" + repr(source) + "; assert hashlib.sha256(s).hexdigest()==" + repr(hashlib.sha256(source).hexdigest()) + "; n={};exec(compile(s,'pinned-installer','exec'),n);u=" + repr(upgrade_source) + "; assert hashlib.sha256(u).hexdigest()==" + repr(hashlib.sha256(upgrade_source).hexdigest()) + ";v={};exec(compile(u,'pinned-upgrader','exec'),v);print(json.dumps(v['upgrade'](" + repr(str(package)) + "," + repr(bundle_sha) + ",n['unpack_verified'])))"
            if request["operation"] == "resume_research":
                resume_source, _ = fetch("ops/merlin_dot/resume_research.py")
                root_code = "import hashlib,json;s=" + repr(source) + ";assert hashlib.sha256(s).hexdigest()==" + repr(hashlib.sha256(source).hexdigest()) + ";n={};exec(compile(s,'pinned-installer','exec'),n);u=" + repr(upgrade_source) + ";assert hashlib.sha256(u).hexdigest()==" + repr(hashlib.sha256(upgrade_source).hexdigest()) + ";v={};exec(compile(u,'pinned-upgrader','exec'),v);r=" + repr(resume_source) + ";assert hashlib.sha256(r).hexdigest()==" + repr(hashlib.sha256(resume_source).hexdigest()) + ";w={};exec(compile(r,'pinned-resumer','exec'),w);print(json.dumps(w['resume'](" + repr(str(package)) + "," + repr(bundle_sha) + ",n['unpack_verified'],v)))"
        else:
            root_code = "import hashlib; s=" + repr(source) + "; assert hashlib.sha256(s).hexdigest()==" + repr(hashlib.sha256(source).hexdigest()) + "; n={};exec(compile(s,'pinned-installer','exec'),n);import json;print(json.dumps(n['install'](" + repr(str(package)) + "," + repr(bundle_sha) + ")))"
        installed = subprocess.run(["/usr/bin/sudo", "-n", "/usr/bin/python3", "-I", "-c", root_code], env=env, capture_output=True, text=True, timeout=180)
        (output / "installation-log.txt").write_text(installed.stdout + installed.stderr)
        report["host_configuration_changed"] = True
        if installed.returncode:
            report["status"] = "installation_failed"
            (output / "operation-receipt.json").write_text(json.dumps(report, indent=2))
            print(installed.stderr[-6000:])
            return report
        result = json.loads(installed.stdout)
        report["installation"] = result
        if request["operation"] in {"upgrade_research", "resume_research"} and result.get("status") != "upgraded":
            report["status"] = result.get("status", "upgrade_failed")
            (output / "operation-receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True))
            print(json.dumps(report, indent=2, sort_keys=True))
            return report
        from_client = "from dot_ai_os.private_runtime import call_socket;import json; q=json.loads(__import__('sys').argv[1]);r=call_socket('/run/merlin-dot-private/tools.sock',q,expected_server_uid=" + str(result["service_uid"]) + "); print(json.dumps(r)); raise SystemExit(0 if r['ok'] else 1)"
        reports = {}
        for tool, args in (("health", {}), ("context_status", {}), ("context_search", {"query": "virtual circuit power", "budget_bytes": 8000}), ("virtual_circuit_demo", {}), ("research_contract", {}), ("mathematical_lenses_demo", {}), ("research_episode_demo", {})):
            q = {"schema": "merlin-private-call/1", "request_id": "postdeploy-" + tool, "tool": tool, "arguments": args}
            for attempt in range(10):
                called = subprocess.run(["/usr/bin/python3", "-s", "-c", from_client, json.dumps(q)], env=env, cwd=str(release), capture_output=True, text=True, timeout=30)
                if called.returncode == 0:
                    break
                if attempt < 9:
                    time.sleep(0.5)
            if called.returncode:
                raise RuntimeError("post-deploy fixed tool failed: " + tool + ": " + called.stderr[-2000:])
            reports[tool] = json.loads(called.stdout)
        report["live_tool_results"] = reports
        status = subprocess.run(["/usr/bin/systemctl", "show", "merlin-dot-private.service", "--property=ActiveState,SubState,User,Group,MainPID,UnitFileState,PrivateNetwork,NoNewPrivileges,RestrictAddressFamilies"], env=env, capture_output=True, text=True, timeout=10)
        report["service_properties"] = status.stdout
    report["status"] = "succeeded"
    (output / "operation-receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in report.items() if k not in {"source_files", "live_tool_results"}}, indent=2))
    return report

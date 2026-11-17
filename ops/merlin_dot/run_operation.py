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
    test_code = """import json,unittest,sys
s=unittest.defaultTestLoader.discover('tests',pattern='test_*.py')
r=unittest.TextTestRunner(verbosity=2).run(s)
v={'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'passed':r.wasSuccessful() and not r.skipped and r.testsRun>=110}
print('MERLIN_TEST_RESULT='+json.dumps(v,sort_keys=True));sys.exit(0 if v['passed'] else 1)
"""
    tests = subprocess.run(["/usr/bin/python3", "-s", "-c", test_code], cwd=str(release), env=env, capture_output=True, text=True, timeout=180)
    (output / "validation-tests.txt").write_text(tests.stdout + tests.stderr)
    lines = [line for line in tests.stdout.splitlines() if line.startswith("MERLIN_TEST_RESULT=")]
    report["tests"] = json.loads(lines[-1].split("=", 1)[1]) if lines else {"passed": False, "process_returncode": tests.returncode}
    if tests.returncode or not report["tests"].get("passed"):
        report["status"] = "validation_failed"
        (output / "operation-receipt.json").write_text(json.dumps(report, indent=2))
        print(tests.stderr[-14000:])
        return report
    if request["operation"] in {"deploy", "upgrade_research"}:
        validation = api("actions/runs/" + str(request["validation_run_id"]))
        if (validation.get("status") != "completed" or validation.get("conclusion") != "success"
                or validation.get("head_sha") != request["validation_commit"]
                or validation.get("path") != ".github/workflows/merlin-dot-oci-operations.yml"
                or not validation.get("head_branch", "").startswith("merlin/dot-ops/")):
            raise RuntimeError("successful exact validation run required")
        # Root re-verifies the pinned installer bytes and the runtime ZIP before
        # creating new paths; no existing install is overwritten.
        source, _ = fetch("ops/merlin_dot/install_private.py")
        if request["operation"] == "upgrade_research":
            upgrade_source, _ = fetch("ops/merlin_dot/upgrade_research.py")
            root_code = "import hashlib,json; s=" + repr(source) + "; assert hashlib.sha256(s).hexdigest()==" + repr(hashlib.sha256(source).hexdigest()) + "; n={};exec(compile(s,'pinned-installer','exec'),n);u=" + repr(upgrade_source) + "; assert hashlib.sha256(u).hexdigest()==" + repr(hashlib.sha256(upgrade_source).hexdigest()) + ";v={};exec(compile(u,'pinned-upgrader','exec'),v);print(json.dumps(v['upgrade'](" + repr(str(package)) + "," + repr(bundle_sha) + ",n['unpack_verified'])))"
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
        if request["operation"] == "upgrade_research" and result.get("status") != "upgraded":
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

"""One reconciled second attempt for the preserved private-service upgrade.

The root controller supplies only hash-pinned helper namespaces/functions, never
caller-selected commands. Original release/history records remain unchanged.
Readiness retries cover only missing/refused Unix sockets, not semantic/auth or
integrity errors. The earlier failure cause remains unestablished.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time

OLD_SHA = "95e4985f5cf4af7b31bbb183047f6e2e4c4488034ec2d880e54f260feedb0b10"
TOOLS = ("research_contract", "research_episode_demo", "mathematical_lenses_demo")

# Fixed reviewed source shared verbatim by local retry fixtures and the isolated
# peer-UID child. It is never assembled from caller/model text.
READINESS_SOURCE = """def readiness_call(call, pause, attempts=20):
 for attempt in range(attempts):
  try:
   return call()
  except (FileNotFoundError, ConnectionRefusedError):
   if attempt+1==attempts: raise
   pause(0.2)
"""
exec(READINESS_SOURCE)


def _error(exc):
    def tail(value):
        if isinstance(value, bytes):
            value = value.decode("utf-8", "replace")
        return str(value or "")[-8192:]
    return {"class": type(exc).__name__, "returncode": getattr(exc, "returncode", None),
            "stdout": tail(getattr(exc, "stdout", None)), "stderr": tail(getattr(exc, "stderr", None))}


def _probe(release, research=True):
    tools = ["health"] + (list(TOOLS) if research else [])
    code = "import sys,time,json\nsys.path.insert(0,sys.argv[1])\n" + READINESS_SOURCE + """
from dot_ai_os.private_runtime import call_socket
tools=json.loads(sys.argv[2]); reports={}
for tool in tools+['job_submit']:
 q={'schema':'merlin-private-call/1','request_id':'resume-'+tool,'tool':tool,'arguments':{}}
 r=readiness_call(lambda:call_socket('/run/merlin-dot-private/tools.sock',q,expected_server_uid=982,timeout_seconds=5),time.sleep)
 if tool=='job_submit':
  if r.get('ok') is not False or r.get('error',{}).get('code')!='tool_not_allowed': raise RuntimeError('write denial failed')
 else:
  if r.get('ok') is not True or r.get('qualification') is not False or r.get('promotion_authority') is not False: raise RuntimeError('fixed tool failed')
  if tool=='health' and (r['result'].get('transport')!='unix' or r['result'].get('public_listener') is not False): raise RuntimeError('private route changed')
 reports[tool]={'checked':True}
print(json.dumps(reports))
"""
    result = subprocess.run(["/usr/bin/python3", "-I", "-B", "-c", code,
        str(release / "python"), json.dumps(tools)], user=1000, group=1000, extra_groups=[],
        cwd=str(release), env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"},
        check=True, capture_output=True, text=True, timeout=50)
    report = json.loads(result.stdout)
    if set(report) != set(tools + ["job_submit"]) or any(x != {"checked": True} for x in report.values()):
        raise RuntimeError("invalid bounded peer probe report")
    return report


def resume(bundle_path, newsha, unpack_verified, upgrade_namespace):
    b = upgrade_namespace
    if os.geteuid() != b["ROOT_UID"]:
        raise PermissionError("fixed upgrade reconciliation requires root")
    if b["OLD_SHA"] != OLD_SHA or tuple(b["NEW_TOOLS"]) != TOOLS:
        raise RuntimeError("helper scope differs from the accepted v1 upgrade")
    if (not isinstance(newsha, str) or re.fullmatch(r"[0-9a-f]{64}", newsha) is None
            or newsha == OLD_SHA or not callable(unpack_verified)):
        raise ValueError("exact new bundle identity and pinned unpack helper required")
    source = b["SOURCE"]
    old = source / "releases" / OLD_SHA
    new = source / "releases" / newsha
    config = b["CONFIG"]
    history = config.parent / "upgrade-history"
    # Shape/digest validation is delegated to the same pinned bounded unpacker.
    raw = b["_regular"](Path(bundle_path), root_owned=False, expected=newsha, maximum=1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="merlin-resume-check-") as temporary:
        checked = Path(temporary) / "release"
        unpack_verified(raw, newsha, checked)
        manifest_sha = hashlib.sha256((checked / "manifest.json").read_bytes()).hexdigest()
    for path in (source, source / "releases", config.parent, history, b["UNIT"].parent):
        b["_root_directory"](path)
    fd = os.open(source / ".research-upgrade.lock", os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != b["ROOT_UID"] or metadata.st_mode & 0o077:
            raise RuntimeError("unsafe reconciliation lock")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        b["_regular"](b["UNIT"], expected=b["OLD_UNIT_SHA"], maximum=16000)
        b["_verify_release"](old, b["OLD_MANIFEST_SHA"])
        b["_verify_release"](new, manifest_sha)
        if b["pwd"].getpwnam("merlin-dot").pw_uid != 982 or b["pwd"].getpwnam("opc").pw_uid != 1000:
            raise RuntimeError("accepted peer/service identities changed")
        previous = json.loads(b["_regular"](history / ("result-" + newsha + ".json"), maximum=65536))
        intent = json.loads(b["_regular"](history / ("intent-" + newsha + ".json"), maximum=16000))
        for record in (previous, intent):
            if (record.get("old_bundle_sha256") != OLD_SHA or record.get("new_bundle_sha256") != newsha
                    or record.get("old_config_sha256") != b["OLD_CONFIG_SHA"]
                    or record.get("service_uid") != 982 or record.get("state_seed_changed") is not False
                    or record.get("qualification") is not False or record.get("promotion_authority") is not False):
                raise RuntimeError("prior attempt identity mismatch")
        if previous.get("status") not in {"rolled_back", "rollback_failed"} or previous.get("new_manifest_sha256") != manifest_sha:
            raise RuntimeError("prior attempt is not the expected preserved failed upgrade")
        old_raw = b["_regular"](history / ("config-before-" + newsha + ".json"), expected=b["OLD_CONFIG_SHA"], maximum=16000)
        next_config = json.loads(old_raw)
        next_config["grants"][0]["tools"].extend(TOOLS)
        next_raw = (json.dumps(next_config, indent=2) + "\n").encode()
        next_sha = hashlib.sha256(next_raw).hexdigest()
        if next_sha != intent.get("new_config_sha256") or next_sha != previous.get("new_config_sha256"):
            raise RuntimeError("new grant identity differs from the preserved attempt")
        attempt = history / ("attempt-2-" + newsha)
        if attempt.exists() or attempt.is_symlink():
            # Exact completed replay is read-only; partial/failed second attempts
            # require new reconciliation rather than another blind restart.
            b["_root_directory"](attempt)
            recorded = json.loads(b["_regular"](attempt / "result.json", maximum=65536))
            if recorded.get("status") != "upgraded" or recorded.get("new_bundle_sha256") != newsha:
                raise RuntimeError("second attempt already exists; reconcile its preserved state")
            b["_current"](new)
            b["_regular"](config, expected=next_sha, maximum=16000)
            b["_active"]()
            _probe(new)
            return {**recorded, "idempotent_replay": True}
        b["_current"](old)
        b["_regular"](config, expected=b["OLD_CONFIG_SHA"], maximum=16000)
        b["_active"]()
        try:
            _probe(old, research=False)
        except Exception as exc:
            return {"schema": "merlin-research-resume/1", "status": "blocked_old_tool_verification",
                    "error": _error(exc), "host_mutations": False, "service_uid": 982,
                    "qualification": False, "promotion_authority": False}
        attempt.mkdir(mode=0o700)
        attempt.chmod(0o700)
        b["_new_file"](attempt / "config-before.json", old_raw)
        identity = {"schema": "merlin-research-resume/1", "attempt": 2,
            "old_bundle_sha256": OLD_SHA, "new_bundle_sha256": newsha,
            "original_result_sha256": hashlib.sha256(b["_regular"](history / ("result-" + newsha + ".json"), maximum=65536)).hexdigest(),
            "new_manifest_sha256": manifest_sha, "old_config_sha256": b["OLD_CONFIG_SHA"],
            "new_config_sha256": next_sha, "service_uid": 982, "state_seed_changed": False, "qualification": False,
            "promotion_authority": False, "prior_failure_cause": "not_established"}
        b["_new_file"](attempt / "intent.json", (json.dumps(identity, indent=2) + "\n").encode())
        restoration = None
        try:
            b["_systemctl"]("stop")
            b["_switch"](new, old, "resume-2-" + newsha)
            b["_config_replace"](next_raw, b["OLD_CONFIG_SHA"], "resume-2-" + newsha)
            b["_systemctl"]("restart")
            properties = b["_wait_active"]()
            tools = _probe(new)
            status, failure = "upgraded", None
        except Exception as exc:
            failure = _error(exc)
            restoration = {"pointer": False, "config": False, "service_active": False, "tools_verified": False, "errors": []}
            for step in ("stop", "pointer", "config", "restart", "service_active", "tools_verified"):
                try:
                    if step == "stop": b["_systemctl"]("stop")
                    elif step == "pointer":
                        actual = os.readlink(source / "current")
                        if actual == str(new): b["_switch"](old, new, "resume-2-rollback-" + newsha)
                        b["_current"](old); restoration[step] = True
                    elif step == "config":
                        actual = hashlib.sha256(b["_regular"](config, maximum=16000)).hexdigest()
                        if actual == next_sha: b["_config_replace"](old_raw, next_sha, "resume-2-rollback-" + newsha)
                        b["_regular"](config, expected=b["OLD_CONFIG_SHA"], maximum=16000); restoration[step] = True
                    elif restoration["pointer"] and restoration["config"]:
                        if step == "restart": b["_systemctl"]("restart")
                        elif step == "service_active": b["_wait_active"](); restoration[step] = True
                        else: _probe(old, research=False); restoration[step] = True
                except Exception as recovery_error:
                    restoration["errors"].append({"stage": step, "error": _error(recovery_error)})
            status = "restored_v1" if all(restoration[key] for key in ("pointer", "config", "service_active", "tools_verified")) else "recovery_incomplete"
            properties, tools = {}, {}
        result = {**identity, "status": status, "error": failure, "restoration": restoration,
            "service_properties": properties, "tool_verification": tools,
            "both_releases_preserved": old.is_dir() and new.is_dir(), "idempotent_replay": False}
        b["_new_file"](attempt / "result.json", (json.dumps(result, indent=2) + "\n").encode())
        return result
    finally:
        os.close(fd)

"""Fixed v1-to-research upgrade of our private service; no caller commands.

Invoked by a separately pinned, isolated root interpreter after exact-package
tests. Creates one new release and versioned config/intent/result records. It
never seeds, edits private state, changes the unit or touches CACE/cache paths.
Only merlin-dot-private.service is stopped/restarted. Failed activation restores
the exact old link/config and restarts v1; both releases and backups remain.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import stat
import subprocess
import tempfile
import time

ROOT_UID = 0
SERVICE_UID = 982
RUNNER_UID = 1000
SERVICE = "merlin-dot-private.service"
SOURCE = Path("/opt/merlin-dot-private")
CONFIG = Path("/etc/merlin-dot-private/config.json")
UNIT = Path("/etc/systemd/system") / SERVICE
OLD_SHA = "95e4985f5cf4af7b31bbb183047f6e2e4c4488034ec2d880e54f260feedb0b10"
OLD_MANIFEST_SHA = "f87301337ce97b562313a2b0bc86e880ea4c22652ea4866881df8d815636c7e0"
OLD_UNIT_SHA = "f22462e9c91eedab99d4bd16d9e3bb14eb52fedbc1e9e3b9110bb3307a11e543"
OLD_CONFIG_SHA = "17671e753cabef57ae9c0beb416afd2360e9f8f690046eb649238ccc3a5eb2a5"
NEW_TOOLS = ("research_contract", "research_episode_demo", "mathematical_lenses_demo")
SAFE_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    return json.loads(raw.decode("utf-8"))


def _root_directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != ROOT_UID or info.st_mode & 0o022:
        raise RuntimeError("trusted root-owned non-writable directory required: " + str(path))


def _regular(path, *, root_owned=True, expected=None, maximum=13 * 1024 * 1024):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_size > maximum
                or (root_owned and (info.st_uid != ROOT_UID or info.st_mode & 0o022 or info.st_nlink != 1))):
            raise RuntimeError("bounded trusted regular file required")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(maximum + 1)
        if len(raw) > maximum or (expected is not None and _sha(raw) != expected):
            raise RuntimeError("file content identity mismatch")
        return raw
    finally:
        os.close(fd)


def _sync(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _new_file(path, raw, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
        os.fchmod(fd, mode)
    finally:
        os.close(fd)
    _sync(path.parent)


def _current(expected):
    current = SOURCE / "current"
    info = current.lstat()
    if not stat.S_ISLNK(info.st_mode) or info.st_uid != ROOT_UID or os.readlink(current) != str(expected):
        raise RuntimeError("current is not the exact root-owned expected release link")


def _switch(target, expected, token):
    _current(expected)
    temp = SOURCE / (".current-" + token + ".tmp")
    temp.symlink_to(target)
    os.replace(temp, SOURCE / "current")
    _sync(SOURCE)


def _config_replace(raw, expected_sha, token):
    _regular(CONFIG, expected=expected_sha, maximum=16000)
    temp = CONFIG.parent / (".config-" + token + ".tmp")
    _new_file(temp, raw, mode=0o644)
    os.replace(temp, CONFIG)
    _sync(CONFIG.parent)


def _verify_release(release, manifest_sha):
    _root_directory(release)
    manifest_raw = _regular(release / "manifest.json", expected=manifest_sha, maximum=128 * 1024)
    manifest = _json(manifest_raw)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        raise RuntimeError("invalid pinned release manifest")
    expected = set(manifest["files"]) | {"manifest.json"}
    found = set()
    for directory, children, files in os.walk(release, followlinks=False):
        _root_directory(Path(directory))
        for child in children:
            _root_directory(Path(directory) / child)
        for name in files:
            path = Path(directory) / name
            relative = path.relative_to(release).as_posix()
            if relative not in expected:
                raise RuntimeError("unmanifested release file")
            found.add(relative)
            _regular(path, expected=manifest_sha if relative == "manifest.json" else manifest["files"][relative])
    if found != expected:
        raise RuntimeError("release file set differs from pinned manifest")
    return manifest


def _systemctl(action):
    if action not in {"stop", "restart", "show"}:
        raise ValueError("unsupported fixed service operation")
    command = ["/usr/bin/systemctl", action, SERVICE]
    if action == "show":
        command.append("--property=ActiveState,SubState,UnitFileState,User,Group,PrivateNetwork,NoNewPrivileges,RestrictAddressFamilies,DropInPaths")
    return subprocess.run(command, env=SAFE_ENV, cwd="/", check=True,
                          capture_output=True, text=True, timeout=30).stdout


def _active():
    values = dict(line.split("=", 1) for line in _systemctl("show").splitlines() if "=" in line)
    required = {"ActiveState": "active", "SubState": "running", "UnitFileState": "enabled",
                "User": "merlin-dot", "Group": "opc", "PrivateNetwork": "yes",
                "NoNewPrivileges": "yes", "RestrictAddressFamilies": "AF_UNIX", "DropInPaths": ""}
    if any(values.get(key) != value for key, value in required.items()):
        raise RuntimeError("private service properties differ from accepted v1 profile")
    return values


def _wait_active():
    for attempt in range(10):
        try:
            return _active()
        except (RuntimeError, subprocess.CalledProcessError):
            if attempt == 9:
                raise
            time.sleep(0.2)


def _probe_tools(release, *, research=True):
    """Fixed peer-UID probe; no model/caller-selected command or tool arguments."""
    tools = ["health"] + (list(NEW_TOOLS) if research else [])
    code = """import sys
sys.path.insert(0,sys.argv[1])
import json
from dot_ai_os.private_runtime import call_socket
tools=json.loads(sys.argv[2]); receipts={}
for tool in tools:
 q={'schema':'merlin-private-call/1','request_id':'upgrade-'+tool,'tool':tool,'arguments':{}}
 r=call_socket('/run/merlin-dot-private/tools.sock',q,expected_server_uid=982,timeout_seconds=5)
 if r.get('ok') is not True or r.get('qualification') is not False or r.get('promotion_authority') is not False: raise RuntimeError('fixed read tool failed')
 if tool=='health' and (r['result'].get('transport')!='unix' or r['result'].get('public_listener') is not False): raise RuntimeError('private route changed')
 receipts[tool]={'ok':True}
q={'schema':'merlin-private-call/1','request_id':'upgrade-write-denial','tool':'job_submit','arguments':{}}
r=call_socket('/run/merlin-dot-private/tools.sock',q,expected_server_uid=982,timeout_seconds=5)
if r.get('ok') is not False or r.get('error',{}).get('code')!='tool_not_allowed': raise RuntimeError('write denial failed')
print(json.dumps({'tools':receipts,'job_submit':'tool_not_allowed'}))
"""
    output = subprocess.run(["/usr/bin/python3", "-I", "-B", "-c", code,
                             str(release / "python"), json.dumps(tools)],
                            user=RUNNER_UID, group=1000, extra_groups=[], cwd=str(release),
                            env=SAFE_ENV, check=True, capture_output=True, text=True, timeout=35)
    report = json.loads(output.stdout)
    if (set(report) != {"tools", "job_submit"} or set(report["tools"]) != set(tools)
            or any(value != {"ok": True} for value in report["tools"].values())
            or report["job_submit"] != "tool_not_allowed"):
        raise RuntimeError("invalid fixed tool probe report")
    return report


def upgrade(bundle_path, newsha, unpack_verified):
    if os.geteuid() != ROOT_UID:
        raise PermissionError("fixed service upgrade requires root")
    if (not isinstance(newsha, str) or re.fullmatch(r"[0-9a-f]{64}", newsha) is None
            or newsha == OLD_SHA or not callable(unpack_verified)):
        raise ValueError("new exact bundle identity and pinned unpack helper required")
    releases = SOURCE / "releases"
    old = releases / OLD_SHA
    new = releases / newsha
    history = CONFIG.parent / "upgrade-history"
    for directory in (SOURCE, releases, CONFIG.parent, UNIT.parent):
        _root_directory(directory)
    descriptor = os.open(SOURCE / ".research-upgrade.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != ROOT_UID or info.st_mode & 0o077:
            raise RuntimeError("unsafe upgrade lock")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _current(old)
        _regular(UNIT, expected=OLD_UNIT_SHA, maximum=16000)
        old_config_raw = _regular(CONFIG, expected=OLD_CONFIG_SHA, maximum=16000)
        if pwd.getpwnam("merlin-dot").pw_uid != SERVICE_UID or pwd.getpwnam("opc").pw_uid != RUNNER_UID:
            raise RuntimeError("accepted service/runner identity changed")
        _active()
        old_manifest = _verify_release(old, OLD_MANIFEST_SHA)
        if new.exists() or new.is_symlink():
            raise RuntimeError("new release path already exists; reconcile prior attempt")
        if history.exists() or history.is_symlink():
            _root_directory(history)
        backup = history / ("config-before-" + newsha + ".json")
        intent = history / ("intent-" + newsha + ".json")
        result_path = history / ("result-" + newsha + ".json")
        if any(path.exists() or path.is_symlink() for path in (backup, intent, result_path)):
            raise RuntimeError("upgrade history already exists; reconcile prior attempt")
        raw = _regular(Path(bundle_path), root_owned=False, expected=newsha, maximum=1024 * 1024)
        with tempfile.TemporaryDirectory(prefix="merlin-dot-upgrade-check-") as temporary:
            checked = Path(temporary) / "release"
            manifest = unpack_verified(raw, newsha, checked)
            files = manifest["files"]
            required = {"python/dot_ai_os/research_protocol.py", "python/dot_ai_os/research_tools.py", "python/dot_ai_os/math_lenses.py"}
            if not required <= set(files) or files.get("ops/merlin-dot-private.service") != OLD_UNIT_SHA:
                raise RuntimeError("new research modules or unchanged unit are missing")
            for name, expected in old_manifest["files"].items():
                if name.startswith("python/merlin/") or name == "seed-documents.json":
                    if files.get(name) != expected:
                        raise RuntimeError("upgrade changes canonical dependency or synthetic seed")
            for name in files:
                path = PurePosixPath(name)
                allowed = name in {"ops/merlin-dot-private.service", "seed-documents.json", "research-policy/SKILL.md"} or (
                    path.suffix == ".py" and (name.startswith("python/dot_ai_os/") or name.startswith("python/merlin/") or name.startswith("tests/")))
                if not allowed:
                    raise RuntimeError("non-runtime payload is outside this upgrade scope")
            new_manifest_sha = _sha((checked / "manifest.json").read_bytes())
        next_config = _json(old_config_raw)
        if (len(next_config["grants"]) != 1 or next_config["grants"][0]["uid"] != RUNNER_UID
                or next_config["grants"][0]["principal"] != "local-runner-opc"):
            raise RuntimeError("unexpected old principal grant")
        next_config["grants"][0]["tools"].extend(NEW_TOOLS)
        next_config_raw = (json.dumps(next_config, indent=2) + "\n").encode()
        next_config_sha = _sha(next_config_raw)
        # No seeding/state mutation: only new versioned code and config records.
        unpack_verified(raw, newsha, new)
        _verify_release(new, new_manifest_sha)
        if not history.exists():
            history.mkdir(mode=0o700)
            history.chmod(0o700)
        _new_file(backup, old_config_raw)
        intent_record = {"schema": "merlin-dot-research-upgrade-intent/1", "old_bundle_sha256": OLD_SHA,
                         "new_bundle_sha256": newsha, "old_config_sha256": OLD_CONFIG_SHA,
                         "new_config_sha256": next_config_sha, "service_uid": SERVICE_UID,
                         "service": SERVICE, "state_seed_changed": False,
                         "qualification": False, "promotion_authority": False}
        _new_file(intent, (json.dumps(intent_record, indent=2) + "\n").encode())
        switched_link = False
        switched_config = False
        stop_attempted = False
        try:
            _current(old)
            _regular(CONFIG, expected=OLD_CONFIG_SHA, maximum=16000)
            _regular(UNIT, expected=OLD_UNIT_SHA, maximum=16000)
            # Prevent old code producing a receipt with new bytes via /current.
            stop_attempted = True
            _systemctl("stop")
            _switch(new, old, newsha)
            switched_link = True
            _config_replace(next_config_raw, OLD_CONFIG_SHA, newsha)
            switched_config = True
            _systemctl("restart")
            properties = _wait_active()
            tool_probe = _probe_tools(new)
            status = "upgraded"
            failure = None
        except Exception as exc:
            failure = type(exc).__name__
            try:
                if stop_attempted:
                    _systemctl("stop")
                # Inspect actual bytes: a rename may succeed before fsync raises.
                current_target = os.readlink(SOURCE / "current")
                if current_target == str(new):
                    _switch(old, new, "rollback-" + newsha)
                elif current_target != str(old):
                    raise RuntimeError("current changed outside upgrade; refusing blind rollback")
                actual_config_sha = _sha(_regular(CONFIG, maximum=16000))
                if actual_config_sha == next_config_sha:
                    _config_replace(old_config_raw, next_config_sha, "rollback-" + newsha)
                elif actual_config_sha != OLD_CONFIG_SHA:
                    raise RuntimeError("config changed outside upgrade; refusing blind rollback")
                if stop_attempted or switched_link or switched_config:
                    _systemctl("restart")
                properties = _wait_active()
                _current(old)
                _regular(CONFIG, expected=OLD_CONFIG_SHA, maximum=16000)
                tool_probe = _probe_tools(old, research=False)
                status = "rolled_back"
            except Exception as rollback_error:
                status = "rollback_failed"
                properties = {"rollback_error_class": type(rollback_error).__name__}
                tool_probe = {"not_established": True}
        result = {**intent_record, "schema": "merlin-dot-research-upgrade-result/1", "status": status,
                  "error_class": failure, "release": str(new), "previous_release": str(old),
                  "config_backup": str(backup), "service_properties": properties,
                  "both_releases_preserved": old.is_dir() and new.is_dir(),
                  "new_tools": list(NEW_TOOLS), "new_manifest_sha256": new_manifest_sha}
        result["fixed_tool_probe"] = tool_probe
        _new_file(result_path, (json.dumps(result, indent=2) + "\n").encode())
        return result
    finally:
        os.close(descriptor)

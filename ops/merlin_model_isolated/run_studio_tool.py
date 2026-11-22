#!/usr/bin/env python3
"""Source-pinned isolated Studio -> real GGUF -> selected read_file episode.

The marker is generated at runtime and exists only in a scratch workspace file.
No prompt contains it. The actual Studio event ledger, tool-result digest, and
persisted model reply must agree. All processes are private and temporary.
"""
from __future__ import annotations
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_private_model as base
import run_studio_model as studio_api
from studio_tool_contract import assess, ToolEvidenceError

NAME = "receipt.txt"
OUTPUT_TOKENS = 192
MODEL_TIMEOUT = 120
PROMPT = (
    "Use the read_file tool to open receipt.txt. Read its verification marker "
    "and reply with ONLY that exact marker, without explanation. The marker "
    "is not present in this request. Do not create, delete, or edit files."
)


def make_fixture(data):
    workspace = data / "workspace"
    workspace.mkdir(mode=0o700, exist_ok=True)
    base.require(workspace.is_dir() and not workspace.is_symlink()
                 and not list(workspace.iterdir()), "fresh empty private workspace required")
    path = workspace / NAME
    marker = "MERLIN_TOOL_" + secrets.token_hex(16)
    contents = "Verification marker: " + marker + "\n"
    raw = contents.encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        if path.is_file() and not path.is_symlink():
            path.unlink()
        raise
    return path, marker, hashlib.sha256(raw).hexdigest()


def test(ev, product, scratch, parent, python):
    base.namespace_identity(parent)
    flags = base.status(os.getpid())
    base.require(flags.get("CapEff") == "0000000000000000"
                 and flags.get("NoNewPrivs") == "1",
                 "tool-test controller still has effective capabilities")
    base.require(product.is_dir() and not product.is_symlink(),
                 "pinned product source unavailable")
    base.require(python.is_file() and not python.is_symlink()
                 and python.stat().st_size == 56723673
                 and python.name == "python3.11" and python.parent.name == "bin",
                 "privately staged CPython 3.11 identity missing")
    studio_dir = product / "portable/merlin_studio"
    for name in ("server.py", "engine.py", "model.py", "storage.py", "tools.py", "worker.py"):
        base.require((studio_dir / name).is_file()
                     and not (studio_dir / name).is_symlink(),
                     "pinned Merlin Studio module missing: " + name)
    model_home = scratch / "model-home"
    model_home.mkdir(mode=0o700, exist_ok=False)
    data = scratch / "studio-state"
    data.mkdir(mode=0o700, exist_ok=False)
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
           "HOME": str(model_home), "XDG_CACHE_HOME": str(model_home),
           "XDG_CONFIG_HOME": str(model_home), "TMPDIR": str(scratch),
           "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "2",
           "OPENBLAS_NUM_THREADS": "2", "GGML_N_THREADS": "2"}
    result = {"schema": "merlin-oci-studio-real-tool/1", "status": "blocked",
              "verified_read_file": False, "source_pinned": True,
              "output_token_budget": OUTPUT_TOKENS, "model_timeout_seconds": MODEL_TIMEOUT,
              "private_network_loopback_only": True,
              "production_qualified": False, "host_installed": False,
              "existing_provider_mutated": False}
    model = None
    studio = None
    start = time.monotonic()
    try:
        source = base.files()
        base.COMMAND = base.COMMAND + ["--jinja"]
        with (ev / "private-model.stdout").open("wb") as out, \
             (ev / "private-model.stderr").open("wb") as err:
            model = subprocess.Popen(
                base.COMMAND, cwd="/", env=env, stdin=subprocess.DEVNULL,
                stdout=out, stderr=err, start_new_session=True,
                preexec_fn=base.restricted_limits)
        studio_api.await_healthy(model, studio_api.MODEL_PORT,
                                "private GGUF", deadline=145)
        process_before = base.check_process(model.pid, source, parent)
        listed = base.json_local("GET", "/v1/models", seconds=5)
        base.require(base.ALIAS in [x.get("id") for x in listed.get("data", [])
                                   if isinstance(x, dict)],
                     "private model alias differs")
        studio_env = dict(env)
        studio_env.update(
            MERLIN_MODEL_URL="http://127.0.0.1:%d/v1/chat/completions" % studio_api.MODEL_PORT,
            MERLIN_MODEL_ID=base.ALIAS)
        bootstrap = ("import sys;sys.path.insert(0,%r);sys.path.insert(0,%r);"
                     "from server import main;main()" %
                     (str(studio_dir), str(product / "python")))
        argv = [str(python), "-I", "-B", "-S", "-c", bootstrap,
                "--port", str(studio_api.STUDIO_PORT), "--data-dir", str(data)]
        def launch_studio():
            return subprocess.Popen(
                argv, cwd="/", env=studio_env, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=True)
        studio = launch_studio()
        studio_api.await_healthy(studio, studio_api.STUDIO_PORT,
                                 "Merlin Studio", deadline=17)
        code, status = studio_api.request("GET", "/api/status")
        base.require(code == 200 and status.get("version") == "0.2.0"
                     and status.get("model", {}).get("configured") is True
                     and status["model"]["model_id"] == base.ALIAS,
                     "Studio did not bind the real model")
        token = status.get("session_token")
        base.require(isinstance(token, str) and len(token) >= 32,
                     "Studio mutation token missing")
        settings = {"model_url": studio_env["MERLIN_MODEL_URL"],
                    "model_id": base.ALIAS, "network_enabled": False,
                    "python_enabled": False, "desktop_enabled": False,
                    "max_steps": 3, "max_output_tokens": OUTPUT_TOKENS,
                    "model_timeout_seconds": MODEL_TIMEOUT}
        code, saved = studio_api.request("POST", "/api/settings", token, settings)
        base.require(code == 200 and saved.get("settings", {}).get("max_steps") == 3
                     and saved["settings"].get("max_output_tokens") == OUTPUT_TOKENS
                     and saved["settings"].get("model_timeout_seconds") == MODEL_TIMEOUT,
                     "bounded local tool inference settings differed")
        code, stable = studio_api.request("GET", "/api/status")
        base.require(code == 200 and all(
            stable.get("capabilities", {}).get(key) is False
            for key in ("network", "python", "desktop")),
            "non-workspace tools remain enabled")
        fixture, marker, digest = make_fixture(data)
        base.require(marker not in PROMPT,
                     "hidden reference was leaked in the prompt")
        code, created = studio_api.request(
            "POST", "/api/conversations", token,
            {"title": "OCI real local model-selected file-read acceptance"})
        base.require(code == 201 and isinstance(created.get("conversation"), dict),
                     "conversation creation failed")
        cid = created["conversation"]["id"]
        base.require(re.fullmatch(r"[0-9a-f]{32}", cid) is not None,
                     "Studio returned an invalid conversation ID")
        code, submitted = studio_api.request(
            "POST", "/api/chat", token,
            {"conversation_id": cid, "message": PROMPT})
        base.require(code == 202 and re.fullmatch(
            r"[0-9a-f]{32}", submitted.get("run_id", "")),
            "Studio did not accept model-selected tool request")
        rid = submitted["run_id"]
        cutoff = time.monotonic() + 190
        run = None
        conversation = None
        while time.monotonic() < cutoff:
            code, info = studio_api.request("GET", "/api/runs/" + rid)
            base.require(code == 200 and isinstance(info.get("run"), dict),
                         "Studio run status unavailable")
            run = info["run"]
            if run["status"] in ("completed", "failed", "cancelled", "interrupted", "waiting_approval"):
                conversation = info.get("conversation")
                break
            time.sleep(0.25)
        if run is not None:
            result["last_run_status"] = str(run.get("status", ""))[:40]
            result["last_run_error"] = str(run.get("error", ""))[:180]
            result["model_request_events"] = sum(
                event.get("type") == "model_request"
                for event in run.get("events", []) if isinstance(event, dict))
            result["tool_event_types"] = [
                {"type":event.get("type"), "tool":event.get("tool")}
                for event in run.get("events", [])
                if isinstance(event, dict) and
                event.get("type") in ("tool_started","tool_result","tool_denied","tool_error")
            ][:8]
        base.require(run is not None and run.get("status") == "completed",
                     "real model-selected tool run did not complete")
        base.require(isinstance(conversation, dict), "conversation missing")
        messages = conversation.get("messages", [])
        base.require(len(messages) == 2 and messages[0].get("role") == "user"
                     and messages[0].get("content") == PROMPT
                     and messages[1].get("role") == "assistant",
                     "tool result or assistant reply not persisted correctly")
        answer = messages[1]["content"]
        proof = assess(run.get("events", []), expected_path=NAME,
                       fixture_sha256=digest, marker=marker, answer=answer)
        base.require(fixture.is_file() and not fixture.is_symlink()
                     and hashlib.sha256(fixture.read_bytes()).hexdigest() == digest
                     and [p.name for p in fixture.parent.iterdir()] == [NAME],
                     "model unexpectedly modified private workspace")
        # Never serialize the marker itself, fixture contents, or Studio auth token.
        result.update(proof)
        result["assistant_sha256"] = hashlib.sha256(answer.encode()).hexdigest()
        result["prompt_sha256"] = hashlib.sha256(PROMPT.encode()).hexdigest()
        result["persisted_messages"] = 2
        first_messages = list(messages)
        studio_api.terminate(studio, "first Merlin Studio", ev)
        if studio.stdout:
            studio.stdout.close()
        if studio.stderr:
            studio.stderr.close()
        studio = None
        studio = launch_studio()
        studio_api.await_healthy(studio, studio_api.STUDIO_PORT,
                                 "restarted Merlin Studio", deadline=17)
        code, fresh = studio_api.request("GET", "/api/status")
        base.require(code == 200 and fresh["session_token"] != token,
                     "Studio restart reused mutation token")
        expired, _ = studio_api.request(
            "POST", "/api/conversations", token,
            {"title": "expired session must not mutate"})
        base.require(expired == 403, "expired Studio token accepted")
        code, after = studio_api.request("GET", "/api/conversations/" + cid)
        base.require(code == 200 and after["conversation"]["messages"] == first_messages,
                     "model/tool conversation changed after restart")
        base.require(base.check_process(model.pid, source, parent) == process_before,
                     "private model provider process identity changed")
        result.update(status="passed", verified_read_file=True,
                      restart_restored=True, stale_token_rejected=True,
                      model_worker=process_before,
                      model_file_sha256=source["model"]["sha256"],
                      model_binary_sha256=source["binary"]["sha256"])
        return True
    except BaseException as exc:
        result.update(error_type=type(exc).__name__, error_reason=str(exc)[:240])
        return False
    finally:
        if studio is not None:
            studio_api.terminate(studio, "Merlin Studio", ev)
            if studio.stdout:
                studio.stdout.close()
            if studio.stderr:
                studio.stderr.close()
        if model is not None:
            studio_api.terminate(model, "private GGUF", ev)
        result["model_process_terminated"] = model is None or model.poll() is not None
        result["studio_process_terminated"] = studio is None or studio.poll() is not None
        result["elapsed_seconds"] = round(time.monotonic() - start, 3)
        (ev / "studio-tool-result.json").write_text(
            json.dumps(result, sort_keys=True, indent=2))
        print(json.dumps({
            "status": result["status"],
            "verified_read_file": result.get("verified_read_file", False),
            "model_requests": result.get("model_request_events", 0),
            "restart_restored": result.get("restart_restored", False),
            "model_terminated": result["model_process_terminated"],
            "studio_terminated": result["studio_process_terminated"],
            "production_qualified": False}, sort_keys=True))


def setup(ev, product, scratch, parent, python):
    base.require(os.geteuid() == 1000
                 and os.stat("/proc/self/ns/net").st_ino != parent
                 and Path("/proc/self/uid_map").read_text().split() == ["1000", "1000", "1"],
                 "rootless tool namespace identity failed")
    base.require(sorted(name for _, name in socket.if_nameindex()) == ["lo"],
                 "unexpected private namespace interface")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
        req = struct.pack("16sH14s", b"lo", 0, b"")
        name, flags, pad = struct.unpack(
            "16sH14s", fcntl.ioctl(sk.fileno(), 0x8913, req))
        base.require(name.rstrip(b"\0") == b"lo", "private loopback differed")
        if not flags & 1:
            fcntl.ioctl(sk.fileno(), 0x8914,
                        struct.pack("16sH14s", b"lo", flags | 1, pad))
    base.namespace_identity(parent)
    args = ["/usr/bin/setpriv", "--no-new-privs", "--bounding-set=-all",
            "--inh-caps=-all", "/usr/bin/python3", "-I", "-B",
            str(Path(__file__).resolve()), "test", str(ev), str(product),
            str(scratch), str(parent), str(python)]
    child = subprocess.run(
        args, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
                   "HOME": str(scratch), "PYTHONDONTWRITEBYTECODE": "1"},
        cwd="/", stdin=subprocess.DEVNULL, capture_output=True, timeout=340)
    (ev / "studio-tool-wrapper.stdout").write_bytes(child.stdout[:32768])
    (ev / "studio-tool-wrapper.stderr").write_bytes(child.stderr[:32768])
    base.require(len(child.stdout) <= 32768 and len(child.stderr) <= 32768,
                 "isolated tool controller output exceeded bound")
    return child.returncode == 0


def main():
    if len(sys.argv) != 7 or sys.argv[1] not in ("setup", "test"):
        raise SystemExit("fixed mode, evidence, product, scratch, parent, private interpreter")
    phase, ev, product, scratch, parent, python = sys.argv[1:]
    ev, product, scratch, parent, python = (
        Path(ev), Path(product), Path(scratch), int(parent), Path(python))
    try:
        base.require(all(x.is_dir() and not x.is_symlink()
                         for x in (ev, product, scratch)),
                     "fixed private tool staging missing")
        ok = (setup(ev, product, scratch, parent, python)
              if phase == "setup" else test(ev, product, scratch, parent, python))
        return 0 if ok else 2
    except BaseException as exc:
        (ev / "studio-tool-error.json").write_text(json.dumps({
            "status": "blocked", "error_type": type(exc).__name__,
            "reason": str(exc)[:220], "production_qualified": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

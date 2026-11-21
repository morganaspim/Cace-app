#!/usr/bin/env python3
"""Bounded real-provider acceptance for the unmodified Merlin Studio server.

Default mode only prepares inputs. Running requires a fresh, successful, separately
collected OCI identity preflight. No downloads, installations or service operations.
"""
from __future__ import annotations

import argparse
from contextlib import suppress
from datetime import datetime, timezone
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

sys.dont_write_bytecode = True
REVISION = "8497597f297bba83189afef2026c27f9244537ce"
MODEL_ID = "merlin-qwen-coder-1.5b-q4"
PROVIDER = ("127.0.0.1", 8080)
PINS = {
    "model_sha256": "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046",
    "binary_sha256": "af4c10f1f4a1e7f0878dc9b3896bb742f65170861276ef04ddecdf2a9be3cd82",
    "service_unit_sha256": "77629b0ef1afc4bcca4fa11282e6ca0bb7f0164110982fe85ae8ca6c267cad99",
    "active_state": "active", "sub_state": "running", "model_id": MODEL_ID,
}
PROMPT = ("Read acceptance_input.txt using read_file exactly once. Do not use any other tool. "
          "Find the acceptance_token value in that file. Then reply with exactly MERLIN_OK "
          "followed by one space and that value. Do not add explanations or punctuation.")
SETTINGS = {"model_id": MODEL_ID, "network_enabled": False, "python_enabled": False,
            "desktop_enabled": False, "max_steps": 2}
APP_FILES = ("engine.py", "model.py", "public_web.py", "server.py", "storage.py", "tools.py", "worker.py", "web/index.html")
CORE_FILES = ("__init__.py", "artifact_ref.py", "project_registry.py")
MAX_BYTES = 2 * 1024 * 1024


class InvalidResponse(ValueError):
    def __init__(self, message, *, status, raw, declared_length):
        super().__init__(message)
        self.status = status
        self.raw = raw
        self.declared_length = declared_length


def encoded(value):
    # Match LocalModel._request serialization exactly.
    return json.dumps(value, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def stamp():
    return datetime.now(timezone.utc).isoformat()


def source_identity(app):
    cores = (app / "core/python/merlin", app.parents[1] / "python/merlin")
    core = next((p for p in cores if (p / "project_registry.py").is_file()), None)
    if core is None:
        raise ValueError("Original Merlin registry modules are missing")
    files = {"app/" + name: app / name for name in APP_FILES}
    files.update({"core/python/merlin/" + name: core / name for name in CORE_FILES})
    result = {}
    for name, path in sorted(files.items()):
        raw = path.read_bytes()
        result[name] = {"bytes": len(raw), "sha256": digest(raw)}
    return {"schema": "merlin-studio-exact-source/1", "repository_revision": REVISION, "files": result}


def initial_payload(app):
    sys.path.insert(0, str(app))
    engine = importlib.import_module("engine")
    tools = importlib.import_module("tools")
    with tempfile.TemporaryDirectory(prefix="merlin-inputs-") as temp:
        schemas = tools.ToolSet(Path(temp), None, SETTINGS).schemas()
    return {"model": MODEL_ID,
            "messages": [{"role": "system", "content": engine.SYSTEM}, {"role": "user", "content": PROMPT}],
            "stream": False, "max_tokens": 2048, "temperature": 0.3,
            "tools": schemas, "tool_choice": "auto", "parallel_tool_calls": False}


def prepare(app, output):
    source = source_identity(app)
    payload = initial_payload(app)
    raw = encoded(payload)
    save_json(output / "studio-source.json", source)
    (output / "initial-model-request.json").write_bytes(raw)
    save_json(output / "inputs.json", {
        "schema": "merlin-studio-real-model-inputs/1", "prepared_at": stamp(),
        "model_endpoint": "http://127.0.0.1:8080/v1/chat/completions", "model_id": MODEL_ID,
        "studio_revision": REVISION, "provider_identity": PINS,
        "initial_request": {"bytes": len(raw), "sha256": digest(raw),
                            "token_count": None, "token_count_status": "not_measured"},
        "token_count_endpoint": "http://127.0.0.1:8080/v1/chat/completions/input_tokens",
        "settings": SETTINGS, "prompt": PROMPT,
        "fixture": {"path": "acceptance_input.txt", "content_template": "acceptance_token=<fresh 32 lowercase hex characters>\n",
                    "token_in_prompt": False},
        "bounds": {"maximum_generation_requests": 2, "maximum_requested_output_tokens_per_call": 2048,
                   "maximum_requested_output_tokens_total": 4096, "studio_model_deadline_seconds": 45,
                   "studio_work_deadline_seconds": 180, "harness_run_deadline_seconds": 185,
                   "automatic_retries": 0, "paid_service_calls": 0, "external_network_calls": 0},
        "pass_criteria": ["fresh exact provider/source preflight", "exact initial Studio request",
                          "two actual generation requests", "one read_file of the fixture with matching SHA256",
                          "no other tools", "completed run", "exact MERLIN_OK plus unseen fixture token",
                          "canonical tool-result ArtifactRef retained", "usage and raw request/response bytes retained"],
        "scope": "One bounded real Studio HTTP/model/tool loop, not a general model-quality or platform qualification.",
        "generated_inference": False,
    })
    return source, payload


def http_bytes(address, method, path, body=None, *, headers=None, timeout=5):
    """Numeric loopback only, no proxy or redirects, total deadline and byte cap."""
    if address[0] != "127.0.0.1":
        raise ValueError("Only numeric IPv4 loopback is permitted")
    deadline = time.monotonic() + timeout
    conn = http.client.HTTPConnection(address[0], address[1], timeout=timeout)
    channel = None
    timer = None
    response = None
    expired = threading.Event()

    def interrupt():
        expired.set()
        if channel is not None:
            with suppress(OSError):
                channel.shutdown(socket.SHUT_RDWR)
            with suppress(OSError):
                channel.close()
        conn.close()

    try:
        conn.connect()
        channel = conn.sock
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Total response deadline expired during connect")
        timer = threading.Timer(remaining, interrupt)
        timer.daemon = True
        timer.start()
        conn.request(method, path, body=body, headers={"Content-Type": "application/json", "Connection": "close", **(headers or {})})
        response = conn.getresponse()
        pairs = response.getheaders()
        if sum(len(name) + len(value) for name, value in pairs) > 32768:
            raise ValueError("Response headers exceed 32 KiB")
        lengths = [value.strip() for name, value in pairs if name.lower() == "content-length"]
        transfers = [value.strip().lower() for name, value in pairs if name.lower() == "transfer-encoding"]
        encodings = [value.strip().lower() for name, value in pairs if name.lower() == "content-encoding"]
        if (len(lengths) > 1 or len(transfers) > 1 or lengths and transfers
                or transfers and transfers != ["chunked"] or encodings and encodings != ["identity"]):
            raise ValueError("Ambiguous or unsupported response framing")
        declared_length = None
        if lengths:
            if not lengths[0].isascii() or not lengths[0].isdecimal() or len(lengths[0]) > 20:
                raise ValueError("Invalid declared response length")
            declared_length = int(lengths[0])
            if declared_length > MAX_BYTES:
                raise ValueError("Declared response exceeds 2 MiB")
        chunks, size = [], 0
        while size <= MAX_BYTES:
            part = response.read1(min(65536, MAX_BYTES + 1 - size))
            if not part:
                break
            chunks.append(part)
            size += len(part)
        if expired.is_set() or time.monotonic() >= deadline:
            raise TimeoutError("Total response deadline expired")
        if size > MAX_BYTES:
            raise ValueError("Response exceeds 2 MiB")
        if declared_length is not None and size != declared_length:
            raise InvalidResponse("Response ended before its declared length", status=response.status,
                                  raw=b"".join(chunks), declared_length=declared_length)
        return response.status, b"".join(chunks)
    finally:
        if timer is not None:
            timer.cancel()
        if response is not None:
            response.close()
        conn.close()


class RecordingProxy(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, destination, evidence):
        self.destination, self.evidence = destination, evidence
        self.records = []
        self.generation_requests = 0
        self.lock = threading.Lock()
        super().__init__(("127.0.0.1", 0), RecordingHandler)


class RecordingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def do_GET(self):
        self.forward("GET")

    def do_POST(self):
        self.forward("POST")

    def forward(self, method):
        generation = method == "POST" and self.path == "/v1/chat/completions"
        if not generation and not (method == "GET" and self.path == "/v1/models"):
            self.send_error(403, "Only fixed model endpoints are allowed")
            return
        length = self.headers.get("Content-Length", "0")
        if not length.isascii() or not length.isdecimal() or int(length) > MAX_BYTES or self.headers.get("Transfer-Encoding"):
            self.send_error(400, "Invalid request framing")
            return
        body = self.rfile.read(int(length)) if int(length) else None
        with self.server.lock:
            if generation and self.server.generation_requests >= 2:
                self.send_error(429, "Two generation requests exhausted; no retries")
                return
            if generation:
                self.server.generation_requests += 1
            number = len(self.server.records) + 1
            record = {"id": number, "method": method, "path": self.path,
                      "generation": generation, "started_at": stamp(), "request_bytes": len(body or b""),
                      "request_sha256": digest(body or b"")}
            self.server.records.append(record)
        prefix = "provider-%02d" % number
        if body is not None:
            (self.server.evidence / (prefix + "-request.json")).write_bytes(body)
        started = time.monotonic()
        try:
            status, response = http_bytes(self.server.destination, method, self.path, body,
                                          timeout=45 if generation else 3)
            record.update(http_status=status, response_bytes=len(response), response_sha256=digest(response))
            (self.server.evidence / (prefix + "-response.json")).write_bytes(response)
            with suppress(ValueError, AttributeError):
                value = json.loads(response)
                record["usage"] = value.get("usage")
                record["timings"] = value.get("timings")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(response)
        except Exception as exc:
            record["error_type"] = type(exc).__name__
            record["error"] = str(exc)[:500]
            if isinstance(exc, InvalidResponse):
                record.update(upstream_http_status=exc.status, malformed_framing=True,
                              declared_response_bytes=exc.declared_length,
                              received_response_bytes=len(exc.raw), received_response_sha256=digest(exc.raw))
                (self.server.evidence / (prefix + "-invalid-response.bin")).write_bytes(exc.raw)
            with suppress(OSError):
                self.send_error(502, "Upstream request failed; inspect evidence")
        finally:
            record["elapsed_seconds"] = round(time.monotonic() - started, 6)
            record["finished_at"] = stamp()
            self.close_connection = True


def api(address, method, path, payload=None, token=None):
    status, raw = http_bytes(address, method, path, encoded(payload) if payload is not None else None,
                             headers={"X-Merlin-Token": token} if token else None)
    result = json.loads(raw)
    if not 200 <= status < 300:
        raise RuntimeError("Studio API %s %s returned %s: %s" % (method, path, status, str(result)[:400]))
    return result


def check_preflight(path, source):
    value = json.loads(path.read_text())
    value = value.get("studio_model_preflight", value)
    if value.get("schema") != "merlin-studio-model-preflight/1" or value.get("passed") is not True:
        raise ValueError("A successful separately measured OCI preflight is required")
    when = datetime.fromisoformat(value["observed_at"].replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - when).total_seconds()
    if not 0 <= age <= 900:
        raise ValueError("OCI preflight must be no more than 15 minutes old")
    if value.get("studio_revision") != REVISION:
        raise ValueError("OCI preflight source revision differs")
    identity = value.get("provider_identity", {})
    if any(identity.get(k) != v for k, v in PINS.items()):
        raise ValueError("OCI provider identity differs from the retained accepted pins")
    version = value.get("python", {}).get("version", [])
    if len(version) < 2 or tuple(version[:2]) < (3, 10) or sys.version_info < (3, 10):
        raise ValueError("Published Studio requires Python 3.10 or newer")
    if Path(value["python"]["executable"]).resolve() != Path(sys.executable).resolve():
        raise ValueError("Use the same interpreter that passed the OCI preflight")
    if platform.machine() not in ("aarch64", "arm64") or platform.system() != "Linux":
        raise ValueError("Pinned existing provider is Linux aarch64")
    return {"receipt_sha256": digest(path.read_bytes()), "age_seconds": age,
            "observed_at": value["observed_at"], "provider_identity": identity}


def observed_generations(records):
    return [r for r in records if r.get("generation") and r.get("http_status") == 200
            and isinstance(r.get("usage"), dict)
            and type(r["usage"].get("prompt_tokens")) is int and r["usage"]["prompt_tokens"] > 0
            and type(r["usage"].get("completion_tokens")) is int and r["usage"]["completion_tokens"] > 0]


def perform(app, evidence, destination, initial, *, fixture=False):
    proxy = RecordingProxy(destination, evidence)
    proxy_thread = threading.Thread(target=proxy.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    proxy_thread.start()
    proc = None
    data = Path(tempfile.mkdtemp(prefix="merlin-studio-acceptance-"))
    address = None
    token = None
    run_id = None
    last_poll = None
    cancel_receipt = None
    result = {"schema": "merlin-studio-model-acceptance/1", "started_at": stamp(),
              "inference_class": "synthetic_harness_fixture" if fixture else "existing_oci_real_model",
              "real_model_inference": False, "real_model_inference_status": "not_observed",
              "passed": False, "checks": {}}
    try:
        nonce = secrets.token_hex(16)
        fixture_bytes = ("acceptance_token=" + nonce + "\n").encode()
        workspace = data / "workspace"
        workspace.mkdir()
        (workspace / "acceptance_input.txt").write_bytes(fixture_bytes)
        result["fixture_sha256"] = digest(fixture_bytes)
        result["fixture_token_in_user_prompt"] = nonce in PROMPT
        env = dict(os.environ)
        for name in ("MERLIN_MODEL_URL", "MERLIN_MODEL_ID", "MERLIN_LLAMA_SERVER", "MERLIN_MODEL_PATH", "MERLIN_DATA_DIR"):
            env.pop(name, None)
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", MERLIN_MODEL_ID=MODEL_ID,
                   MERLIN_MODEL_URL="http://127.0.0.1:%d/v1/chat/completions" % proxy.server_port)
        log = evidence / "studio-process.log"
        with log.open("wb") as stream:
            proc = subprocess.Popen([sys.executable, str(app / "server.py"), "--port", "0", "--data-dir", str(data)],
                                    cwd=str(app), env=env, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
            launch_deadline = time.monotonic() + 15
            address = None
            while time.monotonic() < launch_deadline:
                for line in log.read_text(errors="replace").splitlines():
                    if line.startswith("Merlin Studio: http://127.0.0.1:"):
                        address = ("127.0.0.1", int(line.split(":")[-1].split("/")[0]))
                if address is not None:
                    break
                if proc.poll() is not None:
                    raise RuntimeError("Studio process exited before readiness")
                time.sleep(0.05)
            if address is None:
                raise TimeoutError("Studio process did not announce a listening port")
            status = api(address, "GET", "/api/status")
            token = status.pop("session_token")  # Never save the session credential.
            save_json(evidence / "studio-status.json", status)
            api(address, "POST", "/api/settings", SETTINGS, token)
            probe = api(address, "POST", "/api/model/probe", {}, token)
            save_json(evidence / "studio-model-probe.json", probe)
            if not probe.get("reachable") or MODEL_ID not in [m.get("id") for m in probe.get("models", [])]:
                raise RuntimeError("Pinned model alias is not loaded")
            conversation = api(address, "POST", "/api/conversations", {"title": "Real model acceptance"}, token)["conversation"]
            run_id = api(address, "POST", "/api/chat", {"conversation_id": conversation["id"], "message": PROMPT}, token)["run_id"]
            deadline = time.monotonic() + 185
            final = None
            while time.monotonic() < deadline:
                final = api(address, "GET", "/api/runs/" + run_id)
                last_poll = final
                if final["run"]["status"] not in ("running", "waiting_approval"):
                    break
                if final["run"]["status"] == "waiting_approval":
                    cancel_receipt = api(address, "POST", "/api/runs/" + run_id + "/cancel", {}, token)
                    raise RuntimeError("Unexpected approval request; no action was approved")
                time.sleep(0.1)
            else:
                cancel_receipt = api(address, "POST", "/api/runs/" + run_id + "/cancel", {}, token)
                raise TimeoutError("Harness total run deadline expired")
            save_json(evidence / "studio-run.json", final)
            events = final["run"].get("events", [])
            started = [e for e in events if e.get("type") == "tool_started"]
            finished = [e for e in events if e.get("type") == "tool_result"]
            replies = [m["content"] for m in final["conversation"]["messages"] if m["role"] == "assistant"]
            generations = [r for r in proxy.records if r["generation"]]
            checks = {
                "run_completed": final["run"]["status"] == "completed",
                "exact_two_generation_requests": len(generations) == 2,
                "one_exact_read_tool": len(started) == 1 and started[0].get("tool") == "read_file"
                    and started[0].get("arguments") == {"path": "acceptance_input.txt"},
                "one_matching_tool_result": len(finished) == 1 and finished[0].get("tool") == "read_file"
                    and finished[0].get("result", {}).get("content") == fixture_bytes.decode()
                    and finished[0].get("result", {}).get("sha256") == digest(fixture_bytes),
                "canonical_result_artifact": len(finished) == 1 and bool(finished[0].get("artifact_ref")),
                "exact_final_token": bool(replies) and replies[-1].strip() == "MERLIN_OK " + nonce,
                "fixture_not_modified": (workspace / "acceptance_input.txt").read_bytes() == fixture_bytes,
                "only_fixture_workspace_file": [p.name for p in workspace.iterdir()] == ["acceptance_input.txt"],
                "no_tool_errors_or_denials": not any(e.get("type") in ("tool_error", "tool_denied", "approval_required") for e in events),
                    "positive_measured_usage": len(observed_generations(generations)) == 2,
                "initial_request_exact": bool(generations) and generations[0]["request_sha256"] == digest(encoded(initial)),
            }
            result["checks"] = checks
            result["passed"] = all(checks.values())
            result["run_status"] = final["run"]["status"]
            result["run_error"] = final["run"].get("error")
            # Retain the actual canonical evidence before deleting disposable state.
            artifact_files = []
            for path in sorted((data / "registry").rglob("*")):
                if path.is_file() and path.suffix not in (".sqlite3", ".db") and path.name not in ("registry.sqlite-wal", "registry.sqlite-shm"):
                    relative = path.relative_to(data / "registry")
                    if not relative.parts or relative.parts[0] != "blobs":
                        continue
                    target = evidence / "canonical-artifacts" / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(path.read_bytes())
                    artifact_files.append({"path": target.relative_to(evidence).as_posix(), "sha256": digest(target.read_bytes())})
            result["retained_artifact_files"] = artifact_files
            ref = finished[0].get("artifact_ref", {}) if finished else {}
            blob_digest = ref.get("sha256", "")
            blob = data / "registry/blobs/sha256" / blob_digest[:2] / blob_digest[2:]
            checks["canonical_blob_matches_ref"] = (len(blob_digest) == 64 and blob.is_file()
                                                      and digest(blob.read_bytes()) == blob_digest
                                                      and bool(artifact_files))
            result["passed"] = all(checks.values())
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)[:1200]
        if address is not None and token is not None and run_id is not None:
            try:
                if not last_poll or last_poll["run"]["status"] in ("running", "waiting_approval"):
                    if cancel_receipt is None:
                        cancel_receipt = api(address, "POST", "/api/runs/" + run_id + "/cancel", {}, token)
                last_poll = api(address, "GET", "/api/runs/" + run_id)
            except Exception as cancellation_error:
                result["final_snapshot_error"] = str(cancellation_error)[:500]
    finally:
        if last_poll is not None:
            save_json(evidence / "studio-run-last-observed.json", last_poll)
        if cancel_receipt is not None:
            save_json(evidence / "studio-cancel-receipt.json", cancel_receipt)
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        proxy.shutdown()
        proxy.server_close()
        proxy_thread.join(timeout=1)
        result["finished_at"] = stamp()
        result["generation_requests"] = proxy.generation_requests
        result["generation_requests_attempted"] = proxy.generation_requests
        observed = observed_generations(proxy.records)
        result["successful_generation_responses_with_positive_usage"] = len(observed)
        result["real_model_inference"] = bool(observed) and not fixture
        result["real_model_inference_observed"] = result["real_model_inference"]
        result["real_model_inference_status"] = ("synthetic_fixture_only" if fixture else
                                                  "observed_response" if observed else "not_observed")
        save_json(evidence / "provider-requests.json", proxy.records)
        save_json(evidence / "acceptance-result.json", result)
        shutil.rmtree(data)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("prepare", "run"), default="prepare")
    parser.add_argument("--app-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--expected-source", type=Path)
    parser.add_argument("--preflight", type=Path)
    args = parser.parse_args()
    app = args.app_dir.resolve()
    args.evidence_dir.mkdir(parents=True, exist_ok=False)
    source, payload = prepare(app, args.evidence_dir)
    if args.mode == "prepare":
        print(json.dumps({"prepared": True, "generated_inference": False,
                          "initial_request_sha256": digest(encoded(payload)), "source_files": len(source["files"])}))
        return 0
    try:
        if args.expected_source is None or args.preflight is None:
            raise ValueError("Run mode requires --expected-source and --preflight")
        if json.loads(args.expected_source.read_text()) != source:
            raise ValueError("Actual Studio files differ from the prepared exact source")
        preflight = check_preflight(args.preflight, source)
        save_json(args.evidence_dir / "preflight-binding.json", preflight)
    except Exception as exc:
        blocked = {"passed": False, "real_model_inference": False, "generation_requests": 0,
                   "status": "preflight_blocked", "error_type": type(exc).__name__, "error": str(exc)}
        save_json(args.evidence_dir / "acceptance-result.json", blocked)
        print(json.dumps(blocked))
        return 2
    result = perform(app, args.evidence_dir, PROVIDER, payload)
    print(json.dumps({k: result.get(k) for k in ("passed", "inference_class", "generation_requests", "run_status", "run_error", "error")}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run a long qualification command with a compact progress heartbeat.

This wrapper is observability and liveness infrastructure only. It never turns a
cached or partial result into proof evidence. Qualification still depends on the
fresh Lean build, kernel audit, environment metadata, hashes, and attestation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return cleaned or "qualification-phase"


def _write_json_atomic(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True)
    parser.add_argument("--status-dir", default=os.environ.get("CACE_STATUS_DIR"))
    parser.add_argument(
        "--heartbeat-seconds", type=int, default=_env_int("CACE_HEARTBEAT_SECONDS", 60)
    )
    parser.add_argument(
        "--stall-warn-seconds", type=int, default=_env_int("CACE_STALL_WARN_SECONDS", 1800)
    )
    parser.add_argument(
        "--stall-kill-seconds", type=int, default=_env_int("CACE_STALL_KILL_SECONDS", 7200)
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.status_dir:
        parser.error("--status-dir or CACE_STATUS_DIR is required")
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a command is required after --")
    if args.heartbeat_seconds <= 0:
        parser.error("--heartbeat-seconds must be positive")
    if args.stall_warn_seconds <= 0 or args.stall_kill_seconds <= 0:
        parser.error("stall thresholds must be positive")
    if args.stall_kill_seconds <= args.stall_warn_seconds:
        parser.error("stall kill threshold must exceed warning threshold")

    status_dir = Path(args.status_dir)
    status_dir.mkdir(parents=True, exist_ok=True)
    phase = args.phase
    phase_slug = _slug(phase)
    log_path = status_dir / f"{phase_slug}.log"
    heartbeat_path = status_dir / "heartbeat.jsonl"
    current_status_path = status_dir / "job_status.json"

    start_mono = time.monotonic()
    state_lock = threading.Lock()
    state = {"last_output_mono": start_mono, "log_bytes": 0, "last_line": ""}

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        start_new_session=True,
    )
    assert proc.stdout is not None

    def emit(status: str, *, returncode: int | None = None, note: str | None = None) -> dict:
        now_mono = time.monotonic()
        with state_lock:
            last_output_mono = float(state["last_output_mono"])
            log_bytes = int(state["log_bytes"])
            last_line = str(state["last_line"])
        payload = {
            "schema": "cace-job-heartbeat-v1",
            "timestamp_utc": _utc_now(),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "git_commit": os.environ.get("CACE_EXPECTED_SHA") or os.environ.get("GITHUB_SHA"),
            "phase": phase,
            "status": status,
            "pid": proc.pid,
            "elapsed_seconds": round(now_mono - start_mono, 3),
            "seconds_since_output": round(now_mono - last_output_mono, 3),
            "log_bytes": log_bytes,
            "last_line": last_line[-240:],
            "command": command,
        }
        if returncode is not None:
            payload["returncode"] = returncode
        if note is not None:
            payload["note"] = note
        with heartbeat_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
        _write_json_atomic(current_status_path, payload)
        print(
            "CACE_HEARTBEAT "
            f"phase={phase_slug} status={status} elapsed={payload['elapsed_seconds']}s "
            f"idle={payload['seconds_since_output']}s bytes={log_bytes}",
            flush=True,
        )
        return payload

    def read_output() -> None:
        with log_path.open("ab", buffering=0) as log_stream:
            while True:
                raw = proc.stdout.readline()
                if not raw:
                    break
                log_stream.write(raw)
                sys.stdout.buffer.write(raw)
                sys.stdout.buffer.flush()
                decoded = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                with state_lock:
                    state["last_output_mono"] = time.monotonic()
                    state["log_bytes"] = int(state["log_bytes"]) + len(raw)
                    state["last_line"] = decoded

    reader = threading.Thread(target=read_output, name="cace-heartbeat-log-reader", daemon=True)
    reader.start()
    emit("running", note="phase-start")

    warned = False
    forced_stall = False
    try:
        while proc.poll() is None:
            try:
                proc.wait(timeout=args.heartbeat_seconds)
                break
            except subprocess.TimeoutExpired:
                pass
            now_mono = time.monotonic()
            with state_lock:
                idle = now_mono - float(state["last_output_mono"])
            emit("running")
            if idle >= args.stall_warn_seconds and not warned:
                warned = True
                print(
                    f"CACE_STALL_WARNING phase={phase_slug} no_output_seconds={idle:.1f}",
                    file=sys.stderr,
                    flush=True,
                )
            if idle < args.stall_warn_seconds:
                warned = False
            if idle >= args.stall_kill_seconds:
                forced_stall = True
                emit("stalled", note="no-output hard stall threshold reached")
                print(
                    f"CACE_STALL_KILL phase={phase_slug} no_output_seconds={idle:.1f}",
                    file=sys.stderr,
                    flush=True,
                )
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                break
    except BaseException:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        raise
    finally:
        returncode = proc.wait()
        reader.join(timeout=30)

    if forced_stall:
        emit("failed", returncode=124, note="stalled without output")
        return 124
    if returncode == 0:
        emit("passed", returncode=0, note="phase-complete")
        return 0
    emit("failed", returncode=returncode, note="command-exit")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())

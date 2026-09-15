#!/usr/bin/env python3
"""Publish a runner-authored live CACE qualification Check Run to GitHub.

Observability only: failures to publish are reported but never alter mathematical
qualification. The formal workflow remains fail-closed on Lean/kernel evidence.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import urllib.error
import urllib.request


CHECK_NAME = "CACE Live Qualification Status"
STATE_SCHEMA = "cace-github-live-check-v1"
API_VERSION = "2022-11-28"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _env(name: str, *, required: bool = False) -> str | None:
    value = os.environ.get(name)
    if required and (value is None or not value.strip()):
        raise RuntimeError(f"missing required environment variable: {name}")
    return value.strip() if value else None


def _status_file(status_dir: Path) -> Path:
    return status_dir / "github_live_check.json"


def _load_state(status_dir: Path) -> dict:
    path = _status_file(status_dir)
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != STATE_SCHEMA:
        return {}
    return raw


def _save_state(status_dir: Path, payload: dict) -> None:
    status_dir.mkdir(parents=True, exist_ok=True)
    path = _status_file(status_dir)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _progress_text(current: int | None, total: int | None) -> str:
    if current is None or total is None or total <= 0:
        return "not yet reported"
    pct = (100.0 * current / total) if total else 0.0
    return f"`[{current}/{total}]` ({pct:.1f}% of currently discovered tasks)"


def build_summary(
    *,
    phase: str,
    runner_state: str,
    run_id: str | None,
    run_attempt: str | None,
    git_commit: str | None,
    progress_current: int | None,
    progress_total: int | None,
    elapsed_seconds: float | None,
    idle_seconds: float | None,
    last_line: str | None,
    note: str | None,
) -> str:
    rows = [
        "### CACE live qualification status",
        "",
        f"- **Runner state:** `{runner_state}`",
        f"- **Phase:** `{phase}`",
        f"- **Lean/Lake progress:** {_progress_text(progress_current, progress_total)}",
    ]
    if elapsed_seconds is not None:
        rows.append(f"- **Phase elapsed:** `{elapsed_seconds:.1f}s`")
    if idle_seconds is not None:
        rows.append(f"- **Seconds since command output:** `{idle_seconds:.1f}s`")
    if run_id:
        rows.append(f"- **Workflow run:** `{run_id}` (attempt `{run_attempt or '1'}`)")
    if git_commit:
        rows.append(f"- **Exact head:** `{git_commit}`")
    if last_line:
        escaped = last_line.replace("`", "'")
        rows.extend(["", "**Latest runner output**", "", f"`{escaped[-300:]}`"])
    if note:
        rows.extend(["", f"_{note}_"])
    rows.extend(
        [
            "",
            "This status is written by the self-hosted runner. It is observability only and "
            "cannot create or upgrade formal-proof qualification.",
        ]
    )
    return "\n".join(rows)


def _request(method: str, url: str, token: str, payload: dict) -> dict:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "Content-Type": "application/json",
            "User-Agent": "cace-live-qualification-status",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        text = response.read().decode("utf-8")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise RuntimeError("unexpected GitHub Checks API response")
    return parsed


def publish(
    *,
    status_dir: str | Path,
    phase: str,
    runner_state: str,
    conclusion: str | None = None,
    progress_current: int | None = None,
    progress_total: int | None = None,
    elapsed_seconds: float | None = None,
    idle_seconds: float | None = None,
    last_line: str | None = None,
    note: str | None = None,
) -> bool:
    """Create or refresh one Check Run. Returns False on non-fatal API failure."""
    status_path = Path(status_dir)
    token = _env("CACE_GITHUB_TOKEN")
    repository = _env("GITHUB_REPOSITORY")
    git_commit = _env("CACE_EXPECTED_SHA") or _env("GITHUB_SHA")
    api_url = _env("GITHUB_API_URL") or "https://api.github.com"
    run_id = _env("GITHUB_RUN_ID")
    run_attempt = _env("GITHUB_RUN_ATTEMPT") or "1"
    server_url = _env("GITHUB_SERVER_URL") or "https://github.com"

    if not token or not repository or not git_commit:
        print(
            "CACE_LIVE_CHECK_SKIPPED missing token/repository/commit; native Actions status remains available.",
            flush=True,
        )
        return False

    details_url = f"{server_url}/{repository}/actions/runs/{run_id}" if run_id else None
    output = {
        "title": f"CACE: {phase}",
        "summary": build_summary(
            phase=phase,
            runner_state=runner_state,
            run_id=run_id,
            run_attempt=run_attempt,
            git_commit=git_commit,
            progress_current=progress_current,
            progress_total=progress_total,
            elapsed_seconds=elapsed_seconds,
            idle_seconds=idle_seconds,
            last_line=last_line,
            note=note,
        ),
    }

    state = _load_state(status_path)
    check_run_id = state.get("check_run_id")
    try:
        if check_run_id:
            url = f"{api_url}/repos/{repository}/check-runs/{check_run_id}"
            request_payload: dict = {
                "status": "completed" if conclusion else "in_progress",
                "output": output,
            }
            if details_url:
                request_payload["details_url"] = details_url
            if conclusion:
                request_payload["conclusion"] = conclusion
                request_payload["completed_at"] = _utc_now()
            _request("PATCH", url, token, request_payload)
        else:
            url = f"{api_url}/repos/{repository}/check-runs"
            request_payload = {
                "name": CHECK_NAME,
                "head_sha": git_commit,
                "status": "completed" if conclusion else "in_progress",
                "started_at": _utc_now(),
                "external_id": f"cace-{run_id or git_commit}-{run_attempt}",
                "output": output,
            }
            if details_url:
                request_payload["details_url"] = details_url
            if conclusion:
                request_payload["conclusion"] = conclusion
                request_payload["completed_at"] = _utc_now()
            result = _request("POST", url, token, request_payload)
            check_run_id = result.get("id")
            if not isinstance(check_run_id, int):
                raise RuntimeError("GitHub did not return a numeric check-run id")

        _save_state(
            status_path,
            {
                "schema": STATE_SCHEMA,
                "check_run_id": check_run_id,
                "check_name": CHECK_NAME,
                "git_commit": git_commit,
                "run_id": run_id,
                "run_attempt": run_attempt,
                "phase": phase,
                "runner_state": runner_state,
                "conclusion": conclusion,
                "updated_at": _utc_now(),
            },
        )
        print(
            f"CACE_LIVE_CHECK_UPDATED id={check_run_id} state={runner_state} phase={phase}",
            flush=True,
        )
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
        print(f"CACE_LIVE_CHECK_WARNING {type(exc).__name__}: {exc}", flush=True)
        return False


def _map_job_status(value: str) -> tuple[str, str | None]:
    normalized = value.strip().lower()
    if normalized in {"success", "passed"}:
        return "completed", "success"
    if normalized in {"failure", "failed"}:
        return "completed", "failure"
    if normalized in {"cancelled", "canceled"}:
        return "completed", "cancelled"
    if normalized in {"timed_out", "timeout"}:
        return "completed", "timed_out"
    if normalized in {"skipped"}:
        return "completed", "skipped"
    return "in_progress", None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status-dir", default=os.environ.get("CACE_STATUS_DIR"))
    parser.add_argument("--phase", required=True)
    parser.add_argument("--runner-state", default="running")
    parser.add_argument("--job-status")
    parser.add_argument("--progress-current", type=int)
    parser.add_argument("--progress-total", type=int)
    parser.add_argument("--elapsed-seconds", type=float)
    parser.add_argument("--idle-seconds", type=float)
    parser.add_argument("--last-line")
    parser.add_argument("--note")
    args = parser.parse_args()

    if not args.status_dir:
        parser.error("--status-dir or CACE_STATUS_DIR is required")

    conclusion = None
    runner_state = args.runner_state
    if args.job_status:
        mapped_state, conclusion = _map_job_status(args.job_status)
        runner_state = args.job_status if mapped_state == "completed" else runner_state

    publish(
        status_dir=args.status_dir,
        phase=args.phase,
        runner_state=runner_state,
        conclusion=conclusion,
        progress_current=args.progress_current,
        progress_total=args.progress_total,
        elapsed_seconds=args.elapsed_seconds,
        idle_seconds=args.idle_seconds,
        last_line=args.last_line,
        note=args.note,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Fail closed when another CACE GitHub Actions run is active or queued.

Engineering coordination only. This guard does not create proof evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ACTIVE = {"queued", "in_progress", "waiting", "pending", "requested"}


def _request_json(url: str, token: str, *, attempts: int = 3) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cace-actions-serialization-guard",
        },
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1 << attempt)
    assert last_error is not None
    raise last_error


def fetch_runs(repository: str, token: str) -> list[dict]:
    """Fetch only active-status run sets, keeping responses small and fail-closed.

    GitHub's unfiltered 100-run response can exceed a megabyte and has produced
    truncated HTTP bodies on the self-hosted runner.  The serialization decision
    only depends on ACTIVE statuses, so query each relevant status directly.
    """
    runs: dict[int, dict] = {}
    base = f"https://api.github.com/repos/{repository}/actions/runs"
    for status in sorted(ACTIVE):
        query = urllib.parse.urlencode({"status": status, "per_page": 100})
        payload = _request_json(f"{base}?{query}", token)
        for run in payload.get("workflow_runs", []):
            runs[int(run.get("id", 0))] = run
    return list(runs.values())


def blockers(runs: list[dict], *, current_run_id: int | None = None) -> list[dict]:
    found = []
    for run in runs:
        run_id = int(run.get("id", 0))
        if current_run_id is not None and run_id == current_run_id:
            continue
        name = str(run.get("name", ""))
        status = str(run.get("status", ""))
        if status in ACTIVE and "cace" in name.lower():
            found.append({
                "id": run_id,
                "name": name,
                "status": status,
                "head_sha": run.get("head_sha"),
                "html_url": run.get("html_url"),
            })
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--current-run-id", type=int, default=int(os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID") else None)
    args = parser.parse_args()
    if not args.repository or not args.token:
        print("repository and token are required", file=sys.stderr)
        return 2
    active = blockers(fetch_runs(args.repository, args.token), current_run_id=args.current_run_id)
    print(json.dumps({"schema": "cace-actions-serialization-v1", "repository": args.repository, "blockers": active}, indent=2, sort_keys=True))
    return 1 if active else 0


if __name__ == "__main__":
    raise SystemExit(main())

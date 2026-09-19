#!/usr/bin/env python3
"""Fail closed when another CACE GitHub Actions run is active or queued.

Engineering coordination only. This guard does not create proof evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

ACTIVE = {"queued", "in_progress", "waiting", "pending", "requested"}


def fetch_runs(repository: str, token: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repository}/actions/runs?per_page=100"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cace-actions-serialization-guard",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response).get("workflow_runs", [])


def blockers(
    runs: list[dict],
    *,
    current_run_id: int | None = None,
    ignored_workflow_names: frozenset[str] | set[str] = frozenset(),
) -> list[dict]:
    found = []
    for run in runs:
        run_id = int(run.get("id", 0))
        if current_run_id is not None and run_id == current_run_id:
            continue
        name = str(run.get("name", ""))
        status = str(run.get("status", ""))
        if name in ignored_workflow_names:
            continue
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
    parser.add_argument(
        "--ignore-workflow-name",
        action="append",
        default=[],
        help="Exact workflow name to exclude from lane blockers; repeatable for explicitly nonexclusive cheap checks.",
    )
    args = parser.parse_args()
    if not args.repository or not args.token:
        print("repository and token are required", file=sys.stderr)
        return 2
    active = blockers(
        fetch_runs(args.repository, args.token),
        current_run_id=args.current_run_id,
        ignored_workflow_names=set(args.ignore_workflow_name),
    )
    print(json.dumps({"schema": "cace-actions-serialization-v1", "repository": args.repository, "blockers": active}, indent=2, sort_keys=True))
    return 1 if active else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Inventory CACE Actions trigger/concurrency policy.

This is engineering coordination only. It does not create proof evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

AUTO_TRIGGERS = {
    "push", "pull_request", "pull_request_target", "schedule", "merge_group",
    "workflow_run", "repository_dispatch", "issues", "issue_comment",
}
MANUAL_TRIGGERS = {"workflow_dispatch", "workflow_call"}
GLOBAL_GROUP = "cace-global-runner-lane"
ALLOWED_AUTOMATIC = {"cace-collaboration-validation.yml"}


def _top_block(lines: list[str], key: str) -> list[str]:
    start = None
    base = 0
    for i, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}:\s*$", line):
            start = i + 1
            base = len(line) - len(line.lstrip())
            break
    if start is None:
        return []
    out = []
    for line in lines[start:]:
        if not line.strip() or line.lstrip().startswith("#"):
            out.append(line)
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= base:
            break
        out.append(line)
    return out


def _mapping_keys(block: list[str]) -> set[str]:
    found = set()
    for line in block:
        if line.lstrip().startswith("#"):
            continue
        match = re.match(r"^\s{2}([A-Za-z0-9_-]+):", line)
        if match:
            found.add(match.group(1))
    return found


def _workflow_name(text: str, path: Path) -> str:
    match = re.search(r"(?m)^name:\s*(.+?)\s*$", text)
    return match.group(1).strip(" '\"") if match else path.stem


def _is_cace(path: Path, name: str) -> bool:
    low = f"{path.name} {name}".lower()
    return (
        "cace" in low
        or path.name.startswith("lean-v")
        or "chatgpt compile check" in low
    )


def inspect(path: Path) -> dict | None:
    text = path.read_text()
    name = _workflow_name(text, path)
    if not _is_cace(path, name):
        return None
    lines = text.splitlines()
    triggers = sorted(_mapping_keys(_top_block(lines, "on")))
    automatic = sorted(set(triggers) & AUTO_TRIGGERS)
    concurrency = "\n".join(_top_block(lines, "concurrency"))
    group_match = re.search(r"(?m)^\s+group:\s*(.+?)\s*$", concurrency)
    cancel_match = re.search(r"(?m)^\s+cancel-in-progress:\s*(.+?)\s*$", concurrency)
    group = group_match.group(1).strip(" '\"") if group_match else None
    cancel = cancel_match.group(1).strip().lower() if cancel_match else None
    return {
        "file": path.name,
        "name": name,
        "triggers": triggers,
        "automatic_triggers": automatic,
        "uses_self_hosted": "self-hosted" in text,
        "concurrency_group": group,
        "cancel_in_progress": cancel,
    }


def audit(root: Path) -> dict:
    workflows = []
    violations = []
    for path in sorted(root.glob("*.y*ml")):
        item = inspect(path)
        if item is None:
            continue
        workflows.append(item)
        if item["automatic_triggers"] and item["file"] not in ALLOWED_AUTOMATIC:
            violations.append({
                "file": item["file"],
                "kind": "unexpected-automatic-trigger",
                "detail": item["automatic_triggers"],
            })
        if item["uses_self_hosted"]:
            if item["concurrency_group"] != GLOBAL_GROUP:
                violations.append({
                    "file": item["file"],
                    "kind": "self-hosted-concurrency-group",
                    "detail": item["concurrency_group"],
                })
            if item["cancel_in_progress"] != "false":
                violations.append({
                    "file": item["file"],
                    "kind": "self-hosted-cancellation-policy",
                    "detail": item["cancel_in_progress"],
                })
    return {
        "schema": "cace-actions-policy-audit-v1",
        "global_group": GLOBAL_GROUP,
        "allowed_automatic": sorted(ALLOWED_AUTOMATIC),
        "workflows": workflows,
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".github/workflows"))
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    report = audit(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if args.report_only or not report["violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

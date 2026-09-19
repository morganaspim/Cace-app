#!/usr/bin/env python3
"""Audit the executable CACE GitHub Actions surface.

This is engineering coordination only. It does not create proof evidence. The audit
fails closed if the self-hosted workflows broaden their automatic triggers, lose the
shared serialization group, or if collaboration validation expands beyond the explicit
lightweight automatic surface. Heavy formal-proof paths are manual-dispatch only.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

AUTO_TRIGGERS = {
    "push",
    "pull_request",
    "pull_request_target",
    "schedule",
    "merge_group",
    "workflow_run",
    "repository_dispatch",
    "issues",
    "issue_comment",
}
GLOBAL_GROUP = "cace-canonical-qualification-oci"
EXPECTED_ACTIVE = {
    "cace-collaboration-validation.yml",
    "cace-formal-v336-theorem-metadata.yml",
    "cace-python-regression.yml",
    "cace-exact-pin-lean-preflight.yml",
    "cace-lean-source-sanity.yml",
}
EXPECTED_AUTOMATIC = {
    "cace-collaboration-validation.yml": {"pull_request"},
    "cace-formal-v336-theorem-metadata.yml": {"push"},
    "cace-python-regression.yml": {"push"},
    # Manual-only exact-pin typecheck lane; never qualification evidence.
    "cace-exact-pin-lean-preflight.yml": set(),
    "cace-lean-source-sanity.yml": {"pull_request"},
}
LOCKED_PUSH_SCOPE = {
    "cace-formal-v336-theorem-metadata.yml": {
        "branches": {"executor/cace-proof-qualification-locked"},
        "paths": {".github/workflows/cace-formal-v336-theorem-metadata.yml"},
    },
    "cace-python-regression.yml": {
        "branches": {"executor/cace-regression-locked"},
        "paths": {".github/workflows/cace-python-regression.yml"},
    },
}
# Automatic collaboration validation is intentionally narrow. Proof-source and
# application-source changes are validated by explicit preflight/canonical lanes,
# preventing ordinary proof iteration from consuming the self-hosted Lean runner.
COLLAB_AUTOMATIC_PATHS = {
    "collaboration/**",
    "quality/**",
    "scripts/**",
    "ops/**",
    "tests/**",
    "pyproject.toml",
    ".github/workflows/cace-*.yml",
}
COLLAB_HEAVY_MANUAL_PATHS = {
    "formal/**",
    "cace_studio/**",
    "schema/**",
}
LEAN_SANITY_AUTOMATIC_PATHS = {
    "formal/**/*.lean",
    "scripts/check_lean_source_sanity.py",
    "tests/test_lean_source_sanity.py",
    ".github/workflows/cace-lean-source-sanity.yml",
}
REQUIRED_SELF_HOSTED_LABELS = {"self-hosted", "cace", "oci", "aarch64"}


def _top_block(lines: list[str], key: str) -> list[str]:
    for index, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}:\s*$", line):
            base = len(line) - len(line.lstrip())
            out: list[str] = []
            for nested in lines[index + 1 :]:
                if not nested.strip() or nested.lstrip().startswith("#"):
                    out.append(nested)
                    continue
                indent = len(nested) - len(nested.lstrip())
                if indent <= base:
                    break
                out.append(nested)
            return out
    return []


def _mapping_keys(block: list[str], indent: int = 2) -> set[str]:
    result: set[str] = set()
    for line in block:
        if line.lstrip().startswith("#"):
            continue
        match = re.match(rf"^\s{{{indent}}}([A-Za-z0-9_-]+):", line)
        if match:
            result.add(match.group(1))
    return result


def _child_block(block: list[str], key: str, indent: int = 2) -> list[str]:
    for index, line in enumerate(block):
        if re.match(rf"^\s{{{indent}}}{re.escape(key)}:\s*$", line):
            out: list[str] = []
            for nested in block[index + 1 :]:
                if not nested.strip() or nested.lstrip().startswith("#"):
                    out.append(nested)
                    continue
                current = len(nested) - len(nested.lstrip())
                if current <= indent:
                    break
                out.append(nested)
            return out
    return []


def _list_values(block: list[str], key: str, indent: int = 4) -> set[str]:
    for index, line in enumerate(block):
        match = re.match(rf"^\s{{{indent}}}{re.escape(key)}:\s*(.*?)\s*$", line)
        if not match:
            continue
        inline = match.group(1).strip()
        if inline:
            if inline.startswith("[") and inline.endswith("]"):
                return {
                    value.strip().strip("'\"")
                    for value in inline[1:-1].split(",")
                    if value.strip().strip("'\"")
                }
            return {inline.strip("'\"")}
        result: set[str] = set()
        for nested in block[index + 1 :]:
            if not nested.strip() or nested.lstrip().startswith("#"):
                continue
            current = len(nested) - len(nested.lstrip())
            if current <= indent:
                break
            item = re.match(r"^\s*-\s*(.+?)\s*$", nested)
            if item:
                result.add(item.group(1).strip().strip("'\""))
        return result
    return set()


def _workflow_name(text: str, path: Path) -> str:
    match = re.search(r"(?m)^name:\s*(.+?)\s*$", text)
    return match.group(1).strip(" '\"") if match else path.stem


def _is_cace(path: Path, name: str) -> bool:
    low = f"{path.name} {name}".lower()
    return "cace" in low or path.name.startswith("lean-v") or "chatgpt compile check" in low


def _clean_label(value: str) -> str:
    return value.strip().strip("[] ,\t'\"")


def _runner_labels(lines: list[str]) -> set[str]:
    labels: set[str] = set()
    for index, line in enumerate(lines):
        match = re.match(r"^(\s+)runs-on:\s*(.*?)\s*$", line)
        if not match:
            continue
        base_indent = len(match.group(1))
        inline = match.group(2).strip()
        if inline:
            if inline.startswith("[") and inline.endswith("]"):
                labels.update(
                    label
                    for part in inline[1:-1].split(",")
                    if (label := _clean_label(part))
                )
            else:
                label = _clean_label(inline)
                if label:
                    labels.add(label)
            continue
        for nested in lines[index + 1 :]:
            if not nested.strip() or nested.lstrip().startswith("#"):
                continue
            indent = len(nested) - len(nested.lstrip())
            if indent <= base_indent:
                break
            item = re.match(r"^\s*-\s*(.+?)\s*$", nested)
            if item and (label := _clean_label(item.group(1))):
                labels.add(label)
    return labels


def inspect(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    name = _workflow_name(text, path)
    if not _is_cace(path, name):
        return None
    lines = text.splitlines()
    on_block = _top_block(lines, "on")
    triggers = sorted(_mapping_keys(on_block))
    automatic = sorted(set(triggers) & AUTO_TRIGGERS)
    automatic_scope: dict[str, dict[str, list[str]]] = {}
    for trigger in automatic:
        block = _child_block(on_block, trigger)
        automatic_scope[trigger] = {
            "branches": sorted(_list_values(block, "branches")),
            "paths": sorted(_list_values(block, "paths")),
        }
    concurrency = "\n".join(_top_block(lines, "concurrency"))
    group_match = re.search(r"(?m)^\s+group:\s*(.+?)\s*$", concurrency)
    cancel_match = re.search(r"(?m)^\s+cancel-in-progress:\s*(.+?)\s*$", concurrency)
    labels = _runner_labels(lines)
    return {
        "file": path.name,
        "name": name,
        "triggers": triggers,
        "automatic_triggers": automatic,
        "automatic_scope": automatic_scope,
        "uses_self_hosted": "self-hosted" in labels,
        "runner_labels": sorted(labels),
        "concurrency_group": group_match.group(1).strip(" '\"") if group_match else None,
        "cancel_in_progress": cancel_match.group(1).strip().lower() if cancel_match else None,
    }


def audit(root: Path) -> dict:
    workflows: list[dict] = []
    violations: list[dict] = []
    active_files: set[str] = set()
    for path in sorted(root.glob("*.y*ml")):
        item = inspect(path)
        if item is None:
            continue
        filename = item["file"]
        active_files.add(filename)
        workflows.append(item)
        if filename not in EXPECTED_ACTIVE:
            violations.append(
                {
                    "file": filename,
                    "kind": "unexpected-active-cace-workflow",
                    "detail": "archive or explicitly admit this workflow before activation",
                }
            )
        expected_automatic = EXPECTED_AUTOMATIC.get(filename, set())
        if set(item["automatic_triggers"]) != expected_automatic:
            violations.append(
                {
                    "file": filename,
                    "kind": "automatic-trigger-set",
                    "detail": {
                        "expected": sorted(expected_automatic),
                        "observed": item["automatic_triggers"],
                    },
                }
            )
        locked = LOCKED_PUSH_SCOPE.get(filename)
        if locked is not None:
            observed = item["automatic_scope"].get("push", {})
            observed_branches = set(observed.get("branches", []))
            observed_paths = set(observed.get("paths", []))
            if observed_branches != locked["branches"] or observed_paths != locked["paths"]:
                violations.append(
                    {
                        "file": filename,
                        "kind": "locked-push-scope",
                        "detail": {
                            "expected_branches": sorted(locked["branches"]),
                            "observed_branches": sorted(observed_branches),
                            "expected_paths": sorted(locked["paths"]),
                            "observed_paths": sorted(observed_paths),
                        },
                    }
                )
        if filename == "cace-collaboration-validation.yml":
            observed_paths = set(
                item["automatic_scope"].get("pull_request", {}).get("paths", [])
            )
            if observed_paths != COLLAB_AUTOMATIC_PATHS:
                violations.append(
                    {
                        "file": filename,
                        "kind": "collaboration-trigger-paths",
                        "detail": {
                            "expected": sorted(COLLAB_AUTOMATIC_PATHS),
                            "observed": sorted(observed_paths),
                            "heavy_manual_paths": sorted(COLLAB_HEAVY_MANUAL_PATHS),
                        },
                    }
                )
        if filename == "cace-lean-source-sanity.yml":
            observed_paths = set(
                item["automatic_scope"].get("pull_request", {}).get("paths", [])
            )
            if observed_paths != LEAN_SANITY_AUTOMATIC_PATHS:
                violations.append(
                    {
                        "file": filename,
                        "kind": "lean-sanity-trigger-paths",
                        "detail": {
                            "expected": sorted(LEAN_SANITY_AUTOMATIC_PATHS),
                            "observed": sorted(observed_paths),
                        },
                    }
                )
        if item["uses_self_hosted"]:
            if item["concurrency_group"] != GLOBAL_GROUP:
                violations.append(
                    {
                        "file": filename,
                        "kind": "self-hosted-concurrency-group",
                        "detail": item["concurrency_group"],
                    }
                )
            if item["cancel_in_progress"] != "false":
                violations.append(
                    {
                        "file": filename,
                        "kind": "self-hosted-cancellation-policy",
                        "detail": item["cancel_in_progress"],
                    }
                )
            missing_labels = sorted(REQUIRED_SELF_HOSTED_LABELS - set(item["runner_labels"]))
            if missing_labels:
                violations.append(
                    {
                        "file": filename,
                        "kind": "self-hosted-runner-labels",
                        "detail": {"missing": missing_labels, "observed": item["runner_labels"]},
                    }
                )
    for filename in sorted(EXPECTED_ACTIVE - active_files):
        violations.append(
            {
                "file": filename,
                "kind": "missing-required-active-workflow",
                "detail": None,
            }
        )
    return {
        "schema": "cace-actions-policy-audit-v6",
        "global_group": GLOBAL_GROUP,
        "required_self_hosted_labels": sorted(REQUIRED_SELF_HOSTED_LABELS),
        "collaboration_automatic_paths": sorted(COLLAB_AUTOMATIC_PATHS),
        "collaboration_heavy_manual_paths": sorted(COLLAB_HEAVY_MANUAL_PATHS),
        "lean_sanity_automatic_paths": sorted(LEAN_SANITY_AUTOMATIC_PATHS),
        "expected_active": sorted(EXPECTED_ACTIVE),
        "expected_automatic": {
            key: sorted(value) for key, value in sorted(EXPECTED_AUTOMATIC.items())
        },
        "locked_push_scope": {
            key: {
                "branches": sorted(value["branches"]),
                "paths": sorted(value["paths"]),
            }
            for key, value in sorted(LOCKED_PUSH_SCOPE.items())
        },
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

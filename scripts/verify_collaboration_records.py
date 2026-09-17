#!/usr/bin/env python3
"""Verify CACE collaboration records without granting them proof authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RECORD_TYPES = {"TASK_LEASE", "PROPOSAL", "REVIEW", "DECISION", "HANDOFF", "CLOSED"}
EVIDENCE_CLASSES = {"AI_PROPOSAL", "ENGINEERING_VERIFIED", "CERTIFIED_NUMERICAL", "PROVED"}
REQUIRED = {
    "schema_version", "record_id", "record_type", "sender", "target", "head_sha",
    "evidence_class", "created_at", "payload", "content_sha256",
}
OPTIONAL = {"supersedes", "discovery_refs", "evidence_refs"}


def canonical_bytes(record: dict[str, Any]) -> bytes:
    body = {k: v for k, v in record.items() if k != "content_sha256"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def git_head(repo: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def validate(record: dict[str, Any], *, expected_head: str | None = None) -> list[str]:
    errors: list[str] = []
    keys = set(record)
    missing = REQUIRED - keys
    extra = keys - REQUIRED - OPTIONAL
    if missing:
        errors.append("missing fields: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("unknown fields: " + ", ".join(sorted(extra)))
    if record.get("schema_version") != "cace-collaboration-v1":
        errors.append("unsupported schema_version")
    if record.get("record_type") not in RECORD_TYPES:
        errors.append("invalid record_type")
    if record.get("evidence_class") not in EVIDENCE_CLASSES:
        errors.append("invalid evidence_class")
    head = record.get("head_sha")
    if not isinstance(head, str) or not SHA40.fullmatch(head):
        errors.append("head_sha must be lowercase 40-hex")
    elif expected_head is not None and head != expected_head:
        errors.append(f"stale head: record={head} expected={expected_head}")
    stamp = record.get("created_at")
    try:
        if not isinstance(stamp, str):
            raise ValueError
        datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        errors.append("created_at must be ISO-8601 date-time")
    supplied = record.get("content_sha256")
    if not isinstance(supplied, str) or not SHA256.fullmatch(supplied):
        errors.append("content_sha256 must be lowercase 64-hex")
    elif supplied != digest(record):
        errors.append("content_sha256 mismatch")
    if record.get("evidence_class") == "PROVED" and not record.get("evidence_refs"):
        errors.append("PROVED requires at least one evidence_ref")
    if record.get("evidence_class") == "CERTIFIED_NUMERICAL" and not record.get("evidence_refs"):
        errors.append("CERTIFIED_NUMERICAL requires at least one evidence_ref")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--require-current-head", action="store_true")
    args = parser.parse_args()
    paths = args.paths or sorted((args.repo / "collaboration" / "records").glob("*.json"))
    expected = git_head(args.repo) if args.require_current_head else None
    failures = 0
    seen: set[str] = set()
    for path in paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(record, dict):
                raise ValueError("top level must be object")
            errors = validate(record, expected_head=expected)
            rid = record.get("record_id")
            if isinstance(rid, str):
                if rid in seen:
                    errors.append("duplicate record_id")
                seen.add(rid)
        except Exception as exc:
            errors = [f"parse/validation exception: {exc}"]
        if errors:
            failures += 1
            print(f"FAIL {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK   {path}")
    print(json.dumps({"records_checked": len(paths), "failures": failures}, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

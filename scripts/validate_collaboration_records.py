#!/usr/bin/env python3
"""Validate CACE collaboration records without granting them proof status."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD_ROOT = ROOT / "collaboration" / "records"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE = {"AI_PROPOSAL", "ENGINEERING_VERIFIED", "CERTIFIED_NUMERICAL", "PROVED"}
TYPES = {"MESSAGE", "ACKNOWLEDGEMENT", "DECISION", "LEASE"}


def canonical_payload(record: dict) -> bytes:
    payload = {k: v for k, v in record.items() if k != "payload_sha256"}
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest(record: dict) -> str:
    return hashlib.sha256(canonical_payload(record)).hexdigest()


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path}: invalid JSON: {exc}"]
    required = {"schema_version", "record_id", "record_type", "sender", "base_sha", "created_at", "evidence_class", "summary", "payload_sha256"}
    missing = sorted(required - record.keys())
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
        return errors
    if record["schema_version"] != "cace-collaboration-v1":
        errors.append(f"{path}: unsupported schema_version")
    if record["record_type"] not in TYPES:
        errors.append(f"{path}: invalid record_type")
    if record["evidence_class"] not in EVIDENCE:
        errors.append(f"{path}: invalid evidence_class")
    if not SHA40.fullmatch(str(record["base_sha"])):
        errors.append(f"{path}: base_sha must be lowercase 40-hex")
    supplied = str(record["payload_sha256"])
    if not SHA256.fullmatch(supplied):
        errors.append(f"{path}: payload_sha256 must be lowercase 64-hex")
    elif supplied != digest(record):
        errors.append(f"{path}: payload_sha256 mismatch (expected {digest(record)})")
    if record["evidence_class"] == "PROVED" and not record.get("evidence_refs"):
        errors.append(f"{path}: PROVED requires explicit canonical proof evidence_refs")
    return errors


def main() -> int:
    paths = sorted(RECORD_ROOT.rglob("*.json")) if RECORD_ROOT.exists() else []
    errors: list[str] = []
    ids: dict[str, Path] = {}
    for path in paths:
        errors.extend(validate(path))
        try:
            rid = json.loads(path.read_text(encoding="utf-8")).get("record_id")
        except Exception:
            continue
        if rid in ids:
            errors.append(f"{path}: duplicate record_id also used by {ids[rid]}")
        elif rid:
            ids[rid] = path
    if errors:
        print("collaboration validation: FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"collaboration validation: OK ({len(paths)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

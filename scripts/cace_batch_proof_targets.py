#!/usr/bin/env python3
"""Normalize and validate a batch of quarantined Lean proof targets.

This is engineering/formal-preflight support only. It does not create qualification
evidence and never promotes a module into the audited root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts import cace_proof_guardrails as guard

ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = ROOT / "formal" / "cace_formal"
TOKEN_SPLIT = re.compile(r"[\n,;]+")


def _parse(raw: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for token in TOKEN_SPLIT.split(raw):
        value = token.strip()
        if not value:
            continue
        if value.startswith("Module:"):
            value = value.removeprefix("Module:").strip()
        if not value.startswith("CACEFormal/") or not value.endswith(".lean"):
            raise guard.GuardrailError(
                f"batch target must be CACEFormal/*.lean: {value!r}"
            )
        if value in seen:
            raise guard.GuardrailError(f"duplicate batch target: {value}")
        seen.add(value)
        out.append(value)
    if not out:
        raise guard.GuardrailError("batch target list is empty")
    return out


def build_manifest(raw: str) -> dict:
    config = guard.load_config()
    guard.validate(config, emit=False)
    targets = _parse(raw)
    records: list[dict] = []

    for target in targets:
        path = MODULE_ROOT / target
        if not path.is_file():
            raise guard.GuardrailError(f"batch target file is missing: {target}")
        module = target[:-5].replace("/", ".")
        target_class = guard.classify_target(
            config,
            module,
            compile_root=False,
        )
        if target_class != "quarantined-standalone":
            raise guard.GuardrailError(
                f"batch target must be quarantined-standalone: {target} -> {target_class}"
            )
        records.append(
            {
                "path": target,
                "module": module,
                "target_class": target_class,
                "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    canonical = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema": "cace-batched-lean-preflight-targets-v1",
        "target_count": len(records),
        "targets": records,
        "targets_sha256": hashlib.sha256(canonical).hexdigest(),
        "qualification": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modules", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        manifest = build_manifest(args.modules)
    except guard.GuardrailError as exc:
        print(f"CACE_BATCH_TARGET_REJECTED: {exc}")
        return 2

    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    print(payload, end="")
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Finalize qualification diagnostics without masking an earlier failure.

The finalizer is deliberately tolerant of optional/missing heartbeat and log files.
It must be safe to run after a failure at any earlier workflow phase and safe to
run more than once. Diagnostic cleanup is evidence plumbing, never proof evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
from typing import Mapping


def _optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value)


def _compress_optional(path: Path) -> bool:
    if not path.is_file():
        return False
    target = path.with_name(path.name + ".gz")
    data = path.read_bytes()
    target.write_bytes(gzip.compress(data, compresslevel=6, mtime=0))
    path.unlink()
    return True


def finalize_diagnostics(
    *,
    status_dir: Path,
    output_dir: Path | None,
    job_status: str | None,
    env: Mapping[str, str] | None = None,
) -> dict:
    source = os.environ if env is None else env
    status_dir.mkdir(parents=True, exist_ok=True)
    attestation = (
        output_dir / "cace_continuum_qualification_attestation.json"
        if output_dir is not None
        else None
    )
    payload = {
        "schema": "cace-qualification-diagnostic-v3",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "job_status": job_status,
        "git_commit": source.get("CACE_EXPECTED_SHA") or source.get("GITHUB_SHA"),
        "run_id": source.get("GITHUB_RUN_ID"),
        "run_attempt": source.get("GITHUB_RUN_ATTEMPT"),
        "formal_tree_sha": source.get("CACE_FORMAL_TREE_SHA"),
        "lean_toolchain": source.get("CACE_TOOLCHAIN"),
        "mathlib_commit": source.get("CACE_MATHLIB_COMMIT"),
        "cache_mode": source.get("CACE_CACHE_MODE", "miss"),
        "cache_baseline_tree": source.get("CACE_CACHE_BASELINE_TREE") or None,
        "qualification_attestation_present": bool(attestation and attestation.is_file()),
        "cache_effect": "acceleration-only; never qualification evidence",
    }
    (status_dir / "final_status.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    candidates = sorted(status_dir.glob("*.log"))
    candidates.append(status_dir / "heartbeat.jsonl")
    for path in candidates:
        _compress_optional(path)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--job-status")
    args = parser.parse_args(argv)

    status_dir = args.status_dir or _optional_path(os.environ.get("CACE_STATUS_DIR"))
    if status_dir is None:
        return 0
    output_dir = args.output_dir or _optional_path(os.environ.get("CACE_OUTPUT_DIR"))
    job_status = args.job_status if args.job_status is not None else os.environ.get("CACE_JOB_STATUS")
    finalize_diagnostics(
        status_dir=status_dir,
        output_dir=output_dir,
        job_status=job_status,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

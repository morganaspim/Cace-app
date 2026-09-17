#!/usr/bin/env python3
"""Finalize qualification diagnostics without masking an earlier failure.

The finalizer is deliberately tolerant of optional/missing heartbeat and log files
after a failed run. On an otherwise successful qualification, however, it fails
closed unless the attestation, resolved Lake manifest snapshot, and independent
source-binding verification report all exist. This preserves replay evidence in the
always-uploaded diagnostics artifact without turning cache/diagnostic metadata into
proof evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Mapping

ATTESTATION_NAME = "cace_continuum_qualification_attestation.json"
RESOLVED_MANIFEST_NAME = "v330_resolved_lake_manifest.json"
SOURCE_BINDING_REPORT_NAME = "v330_source_binding_verification.json"


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize_diagnostics(
    *,
    status_dir: Path,
    output_dir: Path | None,
    job_status: str | None,
    env: Mapping[str, str] | None = None,
) -> dict:
    source = os.environ if env is None else env
    status_dir.mkdir(parents=True, exist_ok=True)
    evidence_paths = {
        "qualification_attestation": output_dir / ATTESTATION_NAME if output_dir else None,
        "resolved_lake_manifest": output_dir / RESOLVED_MANIFEST_NAME if output_dir else None,
        "source_binding_verification": output_dir / SOURCE_BINDING_REPORT_NAME if output_dir else None,
    }
    if job_status == "success" and output_dir is not None:
        missing = [
            name
            for name, path in evidence_paths.items()
            if path is None or not path.is_file()
        ]
        if missing:
            raise RuntimeError(
                "successful qualification is missing required replay evidence: "
                + ", ".join(missing)
            )

    evidence_sha256 = {
        name: _sha256(path)
        for name, path in evidence_paths.items()
        if path is not None and path.is_file()
    }
    payload = {
        "schema": "cace-qualification-diagnostic-v4",
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
        "qualification_attestation_present": "qualification_attestation" in evidence_sha256,
        "resolved_lake_manifest_present": "resolved_lake_manifest" in evidence_sha256,
        "source_binding_verification_present": "source_binding_verification" in evidence_sha256,
        "replay_evidence_sha256": evidence_sha256,
        "cache_effect": "acceleration-only; never qualification evidence",
        "diagnostic_effect": "retention/integrity metadata only; proof status comes from qualification gates",
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

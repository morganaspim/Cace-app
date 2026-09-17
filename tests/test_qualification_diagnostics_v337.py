from __future__ import annotations

import gzip
import json

from scripts.finalize_qualification_diagnostics import finalize_diagnostics, main


def _env() -> dict[str, str]:
    return {
        "CACE_EXPECTED_SHA": "a" * 40,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "CACE_TOOLCHAIN": "leanprover/lean4:v4.32.1",
        "CACE_MATHLIB_COMMIT": "b" * 40,
    }


def test_missing_optional_heartbeat_is_safe_and_idempotent(tmp_path):
    status_dir = tmp_path / "status"
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    first = finalize_diagnostics(
        status_dir=status_dir,
        output_dir=output_dir,
        job_status="failure",
        env=_env(),
    )
    assert first["job_status"] == "failure"
    assert first["qualification_attestation_present"] is False
    assert (status_dir / "final_status.json").is_file()
    assert not (status_dir / "heartbeat.jsonl.gz").exists()

    second = finalize_diagnostics(
        status_dir=status_dir,
        output_dir=output_dir,
        job_status="failure",
        env=_env(),
    )
    assert second["git_commit"] == "a" * 40
    rendered = json.loads((status_dir / "final_status.json").read_text(encoding="utf-8"))
    assert rendered["schema"] == "cace-qualification-diagnostic-v3"


def test_optional_heartbeat_and_logs_are_compressed_deterministically(tmp_path):
    status_dir = tmp_path / "status"
    status_dir.mkdir()
    heartbeat = status_dir / "heartbeat.jsonl"
    log = status_dir / "h1-graph-converse.log"
    heartbeat.write_bytes(b'{"phase":"test"}\n')
    log.write_bytes(b"hello\n")

    finalize_diagnostics(
        status_dir=status_dir,
        output_dir=None,
        job_status="success",
        env=_env(),
    )

    assert not heartbeat.exists()
    assert not log.exists()
    assert gzip.decompress((status_dir / "heartbeat.jsonl.gz").read_bytes()) == b'{"phase":"test"}\n'
    assert gzip.decompress((status_dir / "h1-graph-converse.log.gz").read_bytes()) == b"hello\n"

    heartbeat_gz = (status_dir / "heartbeat.jsonl.gz").read_bytes()
    finalize_diagnostics(
        status_dir=status_dir,
        output_dir=None,
        job_status="success",
        env=_env(),
    )
    assert (status_dir / "heartbeat.jsonl.gz").read_bytes() == heartbeat_gz


def test_attestation_presence_is_reported_without_becoming_proof_evidence(tmp_path):
    status_dir = tmp_path / "status"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "cace_continuum_qualification_attestation.json").write_text("{}\n")

    payload = finalize_diagnostics(
        status_dir=status_dir,
        output_dir=output_dir,
        job_status="success",
        env=_env(),
    )
    assert payload["qualification_attestation_present"] is True
    assert payload["cache_effect"] == "acceleration-only; never qualification evidence"


def test_cli_is_noop_when_status_directory_was_never_established(monkeypatch):
    monkeypatch.delenv("CACE_STATUS_DIR", raising=False)
    assert main([]) == 0

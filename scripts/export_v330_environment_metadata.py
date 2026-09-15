#!/usr/bin/env python3
"""Validate and canonicalize v3.30 metadata emitted from Lean.Environment.

Production mode executes the pinned Lean exporter. ``--raw-output`` is only an
input seam for tests and post-processing; it does not create proof evidence by
itself. The validator fails closed on endpoint drift, malformed records, unknown
fields, self-dependencies, or a dependency closure that does not contain each
direct dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable

SENTINEL = "CACE_THEOREM_METADATA\t"
RECORD_SCHEMA = "cace-lean-theorem-record-v1"
ARTIFACT_SCHEMA = "cace-lean-theorem-metadata-v1"
GENERATOR = "CACEFormal.V330TheoremMetadata"
PROVENANCE = "Lean.Environment"
_RECORD_KEYS = {
    "schema",
    "generator",
    "theorem",
    "declaration_kind",
    "level_parameters",
    "statement_pp_all",
    "statement_constants",
    "direct_cace_theorem_dependencies",
    "transitive_cace_theorem_dependencies",
}


class EnvironmentMetadataError(RuntimeError):
    """Raised when environment-derived theorem metadata fails closed validation."""


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise EnvironmentMetadataError(f"{field} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise EnvironmentMetadataError(f"{field} must not contain duplicates")
    return sorted(value)


def parse_records(raw_output: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in raw_output.splitlines():
        if not line.startswith(SENTINEL):
            continue
        payload = line[len(SENTINEL):]
        try:
            record = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise EnvironmentMetadataError(
                f"malformed Lean environment metadata JSON: {exc}"
            ) from exc
        if not isinstance(record, dict):
            raise EnvironmentMetadataError("Lean environment metadata record must be an object")
        records.append(record)
    if not records:
        raise EnvironmentMetadataError("no Lean environment metadata sentinel records found")
    return records


def validate_records(
    records: Iterable[dict[str, Any]],
    *,
    expected_endpoints: Iterable[str],
) -> list[dict[str, Any]]:
    expected = tuple(expected_endpoints)
    if not expected or len(expected) != len(set(expected)):
        raise EnvironmentMetadataError("expected endpoint set must be non-empty and unique")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()

    for raw in records:
        keys = set(raw)
        if keys != _RECORD_KEYS:
            raise EnvironmentMetadataError(
                f"record keys mismatch; missing={sorted(_RECORD_KEYS - keys)}, "
                f"extra={sorted(keys - _RECORD_KEYS)}"
            )
        if raw["schema"] != RECORD_SCHEMA:
            raise EnvironmentMetadataError(f"unsupported record schema: {raw['schema']!r}")
        if raw["generator"] != GENERATOR:
            raise EnvironmentMetadataError(f"unexpected Lean generator: {raw['generator']!r}")
        if raw["declaration_kind"] != "theorem":
            raise EnvironmentMetadataError(
                f"endpoint declaration is not a theorem: {raw['declaration_kind']!r}"
            )

        theorem = raw["theorem"]
        if not isinstance(theorem, str) or not theorem:
            raise EnvironmentMetadataError("theorem must be a non-empty string")
        if theorem in seen:
            raise EnvironmentMetadataError(f"duplicate theorem metadata record: {theorem}")
        seen.add(theorem)

        statement = raw["statement_pp_all"]
        if not isinstance(statement, str) or not statement.strip():
            raise EnvironmentMetadataError(f"{theorem}: statement_pp_all must be non-empty")

        level_parameters = _string_list(raw["level_parameters"], f"{theorem}.level_parameters")
        statement_constants = _string_list(
            raw["statement_constants"], f"{theorem}.statement_constants"
        )
        direct = _string_list(
            raw["direct_cace_theorem_dependencies"],
            f"{theorem}.direct_cace_theorem_dependencies",
        )
        transitive = _string_list(
            raw["transitive_cace_theorem_dependencies"],
            f"{theorem}.transitive_cace_theorem_dependencies",
        )
        if theorem in direct or theorem in transitive:
            raise EnvironmentMetadataError(f"{theorem}: self-dependency is forbidden")
        missing_from_closure = sorted(set(direct) - set(transitive))
        if missing_from_closure:
            raise EnvironmentMetadataError(
                f"{theorem}: transitive closure omits direct dependencies: {missing_from_closure}"
            )

        statement_sha256 = _sha256(statement.encode("utf-8"))
        direct_sha256 = _sha256(_canonical_json_bytes(direct))
        transitive_sha256 = _sha256(_canonical_json_bytes(transitive))
        normalized.append(
            {
                "theorem": theorem,
                "declaration_kind": "theorem",
                "level_parameters": level_parameters,
                "statement_pp_all": statement,
                "statement_sha256": statement_sha256,
                "statement_constants": statement_constants,
                "direct_cace_theorem_dependencies": direct,
                "direct_cace_theorem_dependencies_sha256": direct_sha256,
                "transitive_cace_theorem_dependencies": transitive,
                "transitive_cace_theorem_dependencies_sha256": transitive_sha256,
            }
        )

    if seen != set(expected):
        raise EnvironmentMetadataError(
            f"Lean endpoint set differs from proof contract; "
            f"missing={sorted(set(expected) - seen)}, extra={sorted(seen - set(expected))}"
        )
    return sorted(normalized, key=lambda item: item["theorem"])


def build_artifact(
    *,
    raw_output: str,
    expected_endpoints: Iterable[str],
    lean_version: str,
    lean_toolchain: str,
    mathlib_commit: str,
) -> dict[str, Any]:
    endpoints = validate_records(
        parse_records(raw_output),
        expected_endpoints=expected_endpoints,
    )
    identity_payload = {
        "generator": GENERATOR,
        "provenance": PROVENANCE,
        "lean_version": lean_version.strip(),
        "lean_toolchain": lean_toolchain.strip(),
        "mathlib_commit": mathlib_commit.strip(),
        "endpoints": endpoints,
    }
    return {
        "artifact_schema": ARTIFACT_SCHEMA,
        "metadata_state": "LEAN_GENERATED",
        **identity_payload,
        "identity_sha256": _sha256(_canonical_json_bytes(identity_payload)),
        "endpoint_count": len(endpoints),
    }


def run_lean_exporter(formal_dir: Path) -> str:
    completed = subprocess.run(
        ["lake", "env", "lean", "CACEFormal/V330TheoremMetadata.lean"],
        cwd=formal_dir,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        raise EnvironmentMetadataError(
            "Lean environment exporter failed "
            f"(exit {completed.returncode})\n{completed.stdout}"
        )
    return completed.stdout


def _command_output(command: list[str], *, cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(command, cwd=cwd, text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EnvironmentMetadataError(
            f"failed to resolve qualification identity from {command!r}: {exc}"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-dir", type=Path, default=Path("formal/cace_formal"))
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from cace_studio.core.proof_contract import ProofContractRegistry

    contract = ProofContractRegistry.load_default().for_claim(
        "cace.v330.continuum-proof-strengthening"
    )
    if contract is None:
        raise SystemExit("missing canonical v3.30 proof contract")

    formal_dir = args.formal_dir.resolve()
    try:
        raw_output = (
            args.raw_output.read_text(encoding="utf-8")
            if args.raw_output
            else run_lean_exporter(formal_dir)
        )
        lean_version = _command_output(["lean", "--version"])
        lean_toolchain = (formal_dir / "lean-toolchain").read_text(encoding="utf-8").strip()
        mathlib_commit = _command_output(
            ["git", "-C", str(formal_dir / ".lake/packages/mathlib"), "rev-parse", "HEAD"]
        )
        expected_mathlib = contract.dependency_pins.get("mathlib_commit")
        if mathlib_commit != expected_mathlib:
            raise EnvironmentMetadataError(
                f"mathlib commit mismatch: expected {expected_mathlib}, got {mathlib_commit}"
            )
        artifact = build_artifact(
            raw_output=raw_output,
            expected_endpoints=contract.endpoint_theorems,
            lean_version=lean_version,
            lean_toolchain=lean_toolchain,
            mathlib_commit=mathlib_commit,
        )
    except (EnvironmentMetadataError, OSError) as exc:
        print(f"Lean environment metadata rejected: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = _canonical_json_bytes(artifact)
    args.output.write_bytes(rendered)
    digest = _sha256(rendered)
    args.output.with_suffix(args.output.suffix + ".sha256").write_text(
        f"{digest}  {args.output.name}\n", encoding="utf-8"
    )
    print(f"Lean environment metadata PASS: {artifact['endpoint_count']} endpoints")
    print(f"identity_sha256: {artifact['identity_sha256']}")
    print(f"artifact_sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

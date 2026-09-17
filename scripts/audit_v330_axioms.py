#!/usr/bin/env python3
"""Fail closed unless all contract endpoints have only allowed foundational axioms."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cace_studio.core.proof_contract import ProofContractRegistry

CLAIM_ID = "cace.v330.continuum-proof-strengthening"
METADATA_SENTINEL = "CACE_THEOREM_METADATA\t"


def parse_environment_metadata_theorems(raw_text: str) -> tuple[str, ...]:
    """Return exact fully-qualified theorem names emitted by Lean.Environment."""
    theorems: list[str] = []
    for line in raw_text.splitlines():
        if not line.startswith(METADATA_SENTINEL):
            continue
        payload = line[len(METADATA_SENTINEL) :]
        try:
            record = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed Lean environment metadata JSON: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError("Lean environment metadata record must be an object")
        theorem = record.get("theorem")
        if not isinstance(theorem, str) or not theorem:
            raise ValueError(
                "Lean environment metadata theorem key must be a non-empty string"
            )
        theorems.append(theorem)

    if not theorems:
        raise ValueError("no Lean environment metadata theorem records found")
    if len(theorems) != len(set(theorems)):
        raise ValueError("duplicate Lean environment metadata theorem record")
    return tuple(theorems)


def validate_environment_metadata_theorems(
    raw_text: str,
    expected_endpoints: Iterable[str],
) -> set[str]:
    """Fail closed unless raw metadata theorem keys exactly match the proof contract."""
    expected = set(expected_endpoints)
    if not expected:
        raise ValueError("proof contract endpoint theorem set must not be empty")
    actual = set(parse_environment_metadata_theorems(raw_text))
    if actual != expected:
        raise ValueError(
            "Lean environment metadata theorem set differs from proof contract; "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    return actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument(
        "--environment-metadata-raw",
        type=Path,
        help=(
            "Raw Lean.Environment metadata output. Defaults to "
            "v330_lean_environment_metadata.raw.txt beside the audit file."
        ),
    )
    args = parser.parse_args()

    contract = ProofContractRegistry.load_default().for_claim(CLAIM_ID)
    if contract is None:
        raise SystemExit(f"Rejected: no canonical proof contract for {CLAIM_ID}")
    allowed = set(contract.allowed_axioms)

    metadata_path = args.environment_metadata_raw or args.audit.with_name(
        "v330_lean_environment_metadata.raw.txt"
    )
    try:
        metadata_text = metadata_path.read_text(encoding="utf-8")
        expected = validate_environment_metadata_theorems(
            metadata_text,
            contract.endpoint_theorems,
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Rejected: {exc}") from exc

    text = args.audit.read_text(encoding="utf-8")
    if "sorryAx" in text:
        raise SystemExit("Rejected: theorem dependency contains sorryAx")

    found = re.findall(r"'([^']+)' depends on axioms: \[([^\]]*)\]", text)
    audited: dict[str, list[str]] = {}
    for theorem, payload in found:
        if theorem not in expected:
            continue
        axioms = {item.strip() for item in payload.split(",") if item.strip()}
        unexpected = axioms - allowed
        if unexpected:
            raise SystemExit(
                f"Rejected: {theorem} depends on non-whitelisted axioms: {sorted(unexpected)}"
            )
        audited[theorem] = sorted(axioms)

    missing = sorted(expected - set(audited))
    if missing:
        raise SystemExit(f"Rejected: missing theorem axiom reports: {missing}")
    print(
        "Kernel axiom audit PASS:",
        {
            "proof_contract_id": contract.contract_id,
            "proof_contract_sha256": contract.contract_sha256,
            "endpoints": audited,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

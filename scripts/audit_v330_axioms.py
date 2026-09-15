#!/usr/bin/env python3
"""Fail closed unless all contract endpoints have only allowed foundational axioms."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cace_studio.core.proof_contract import ProofContractRegistry

CLAIM_ID = "cace.v330.continuum-proof-strengthening"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    args = parser.parse_args()

    contract = ProofContractRegistry.load_default().for_claim(CLAIM_ID)
    if contract is None:
        raise SystemExit(f"Rejected: no canonical proof contract for {CLAIM_ID}")
    expected = {name.rsplit(".", 1)[-1]: name for name in contract.endpoint_theorems}
    if len(expected) != len(contract.endpoint_theorems):
        raise SystemExit("Rejected: audited endpoints do not have unique short Lean names")
    allowed = set(contract.allowed_axioms)

    text = args.audit.read_text(encoding="utf-8")
    if "sorryAx" in text:
        raise SystemExit("Rejected: theorem dependency contains sorryAx")

    found = re.findall(r"'([^']+)' depends on axioms: \[([^\]]*)\]", text)
    audited: dict[str, list[str]] = {}
    for theorem, payload in found:
        short = theorem.rsplit(".", 1)[-1]
        if short not in expected:
            continue
        if theorem != expected[short]:
            raise SystemExit(
                f"Rejected: axiom output resolved unexpected theorem {theorem!r}; "
                f"contract requires {expected[short]!r}"
            )
        axioms = {item.strip() for item in payload.split(",") if item.strip()}
        unexpected = axioms - allowed
        if unexpected:
            raise SystemExit(
                f"Rejected: {theorem} depends on non-whitelisted axioms: {sorted(unexpected)}"
            )
        audited[theorem] = sorted(axioms)

    missing = sorted(set(contract.endpoint_theorems) - set(audited))
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

#!/usr/bin/env python3
"""Static structural guard for the CACE exact-pin workflow.

This intentionally uses only Python's standard library so the cheap GitHub-hosted
source-sanity job can run it without installing dependencies.  It is not a
general YAML parser; it locks the exact safety-critical step surface and order.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "cace-exact-pin-lean-preflight.yml"

EXPECTED_STEPS = (
    "Checkout exact event commit",
    "Establish exact head and serialize CACE Actions",
    "Validate requested target and audited-root reachability",
    "Validate permanent proof guardrails and freeze proof plan",
    "Reject malformed Lean source seams",
    "Restore pinned Lean and exact Mathlib package tree",
    "Explicitly prewarm pinned Mathlib artifacts",
    "Verify normal proof run is cache-local",
    "Compile proof API canaries",
    "Compile changed modules and audited reverse dependents",
    "Compile requested Lean module",
    "Reverify frozen proof plan before audited root",
    "Compile audited root",
    "Emit non-qualification summary",
    "Upload preflight evidence",
)

REQUIRED_SNIPPETS = (
    "fetch-depth: 0",
    "python3 scripts/cace_proof_guardrails.py validate",
    "python3 scripts/cace_proof_guardrails.py impacted",
    "python3 scripts/cace_proof_guardrails.py plan-hash",
    "Impacted-module planner emitted non-module output.",
    "Impacted-module planner emitted duplicate modules.",
    "lake build +CACEFormal.GuardrailCanaries",
    'lake build "${targets[@]}"',
    'test "$actual" = "$EXPECTED_PLAN_SHA256"',
    'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
    "proof_plan_sha256=${{ steps.guardrails.outputs.plan_sha256 }}",
)


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    if "\t" in text:
        raise SystemExit("Rejected: tabs are forbidden in exact-pin workflow YAML")

    names = tuple(
        match.group(1).strip()
        for match in re.finditer(r"^\s+- name:\s+(.+?)\s*$", text, flags=re.MULTILINE)
    )
    counts = Counter(names)
    duplicates = sorted(name for name, count in counts.items() if count != 1)
    if duplicates:
        raise SystemExit(f"Rejected: duplicate/missing-unique workflow steps: {duplicates}")

    missing = [name for name in EXPECTED_STEPS if name not in counts]
    extras = [name for name in names if name not in EXPECTED_STEPS]
    if missing or extras:
        raise SystemExit(
            f"Rejected: exact-pin step surface drift; missing={missing}, extras={extras}"
        )

    positions = [names.index(name) for name in EXPECTED_STEPS]
    if positions != sorted(positions):
        raise SystemExit("Rejected: exact-pin safety steps are out of required order")

    missing_snippets = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in text]
    if missing_snippets:
        raise SystemExit(
            f"Rejected: exact-pin workflow lost guardrail snippets: {missing_snippets}"
        )

    if text.count("jobs:") != 1 or text.count("exact-pin-lean-preflight:") != 1:
        raise SystemExit("Rejected: malformed/duplicated exact-pin job structure")

    print(
        "CACE_WORKFLOW_GUARDRAILS_OK",
        {
            "workflow": str(WORKFLOW.relative_to(ROOT)),
            "step_count": len(names),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

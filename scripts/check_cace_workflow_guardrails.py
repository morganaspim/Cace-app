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
CANONICAL = ROOT / "ci" / "cace-exact-pin-lean-preflight.canonical.yml"

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
    "Compile quarantined RP2 chain complex",
    "Reverify frozen proof plan before audited root",
    "Compile audited root",
    "Aggregate diagnostic sweep failures",
    "Emit non-qualification summary",
    "Upload preflight evidence",
)

REQUIRED_SNIPPETS = (
    "pull_request:",
    "CACEFormal/ContinuumSimplexCore.lean",
    "CACEFormal/RP2ChainComplex.lean",
    "REQUESTED_MODULE_RAW: ${{ inputs.module || ((github.event_name == 'pull_request' || github.event_name == 'push') && 'CACEFormal/ContinuumSimplexCore.lean') || 'CACEFormal/P1RT0Element.lean' }}",
    "COMPILE_ROOT: ${{ env.CACE_COMPILE_ROOT }}",
    "fetch-depth: 0",
    "python3 scripts/cace_proof_guardrails.py validate",
    "python3 scripts/cace_proof_guardrails.py impacted",
    "python3 scripts/cace_proof_guardrails.py plan-hash",
    "python3 scripts/check_cace_known_failure_regressions.py",
    "CACE_QUARANTINED_STANDALONE_TARGET_OK",
    "standalone quarantine compilation requires compile_root=false",
    'test "$COMPILE_ROOT" = "false"',
    "quarantined_root_imports",
    'target_class="quarantined-standalone"',
    "Impacted-module planner emitted non-module output.",
    "Impacted-module planner emitted duplicate modules.",
    "lake build +CACEFormal.GuardrailCanaries",
    'lake build "${targets[@]}"',
    'test "$actual" = "$EXPECTED_PLAN_SHA256"',
    'test "$(git rev-parse HEAD)" = "$CACE_EXPECTED_HEAD"',
    "proof_plan_sha256=${{ steps.guardrails.outputs.plan_sha256 }}",
    "continue-on-error: true",
    "lake build +CACEFormal.RP2ChainComplex",
    "CACE_RP2_QUARANTINE_CONFIRMED",
    "CACE_DIAGNOSTIC_SWEEP_FAILURES",
    "CACE_PACKAGE_CACHE_LOCK: /var/lib/cace-cache/locks/mathlib-v4.32.1-520045ab14e26149ee970e2e617ca04b09bde5d6.lock",
    'mkdir -p "$(dirname "$CACE_PACKAGE_CACHE_LOCK")"',
    "cace-canary-build.log",
    "cace-impacted-build.log",
    "cace-target-build.log",
    "cace-rp2-build.log",
    "cace-root-build.log",
)


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    canonical = CANONICAL.read_text(encoding="utf-8")
    if text != canonical:
        raise SystemExit(
            "Rejected: runnable exact-pin workflow differs from canonical byte-for-byte template"
        )
    if "\t" in text:
        raise SystemExit("Rejected: tabs are forbidden in exact-pin workflow YAML")

    compile_root_policy = "CACE_COMPILE_ROOT: ${{ (github.event_name == 'pull_request' || github.event_name == 'push') && 'false' || inputs.compile_root }}"
    if text.count(compile_root_policy) != 1:
        raise SystemExit(
            "Rejected: push and pull_request runs must keep quarantined standalone targets "
            "at compile_root=false; only explicit workflow_dispatch may opt into root compilation"
        )
    if text.count("COMPILE_ROOT: ${{ env.CACE_COMPILE_ROOT }}") != 4:
        raise SystemExit(
            "Rejected: target classification, proof-plan hashing, and recheck stages "
            "must all consume the single job-level compile_root policy"
        )

    lock_match = re.search(r"^\s*CACE_PACKAGE_CACHE_LOCK:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    if not lock_match:
        raise SystemExit("Rejected: exact-pin workflow is missing its package-cache lock path")
    lock_path = lock_match.group(1)
    if not lock_path.startswith("/var/lib/cace-cache/locks/") or "/packages/" in lock_path:
        raise SystemExit("Rejected: package-cache lock must live outside the replaceable package tree")
    if text.count('mkdir -p "$(dirname "$CACE_PACKAGE_CACHE_LOCK")"') != 2:
        raise SystemExit("Rejected: both package-cache lock acquisitions must create the external lock directory")

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

    if text.count("continue-on-error: true") != 6:
        raise SystemExit(
            "Rejected: diagnostic sweep must have exactly five continue-on-error stages"
        )

    diagnostic_ids = (
        "canary_compile",
        "impacted_compile",
        "target_compile",
        "rp2_compile",
        "plan_recheck",
        "root_compile",
    )
    for step_id in diagnostic_ids:
        if f"id: {step_id}" not in text:
            raise SystemExit(f"Rejected: missing diagnostic step id: {step_id}")

    aggregate_pos = text.find("- name: Aggregate diagnostic sweep failures")
    root_pos = text.find("- name: Compile audited root")
    summary_pos = text.find("- name: Emit non-qualification summary")
    if not (root_pos < aggregate_pos < summary_pos):
        raise SystemExit("Rejected: diagnostic aggregate gate is out of required order")

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

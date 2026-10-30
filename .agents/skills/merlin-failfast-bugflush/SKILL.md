---
name: merlin-failfast-bugflush
version: 1.0.0-research
scope: MCFC-CACE-only
status: project-development-procedure
---

# M.E.R.L.I.N. Fail-Fast, Test-Driven Defect Clearing

Use for **every future code change or code review in MCFC–CACE**, including code written in ChatGPT and the M.E.R.L.I.N. council. Do not automatically apply to other user projects.

## Engineering design first

Before writing code, state the precise intent, source-of-truth types, inputs/outputs, permissions, evidence class, constraints, important edge cases, resource budgets, failure modes and acceptance tests. Read root `AGENTS.md`, `AI_CONTEXT/00_START_HERE.md`, `AI_CONTEXT/IMPLEMENTATION_PLAN_A_I.md`, `docs/BUG_FLUSH_ARCHITECTURE.md`, relevant implementation sources and canonical goal/idea ledgers. Never request more than 800 source files in one context batch.

## Required TDD RED → GREEN → REFACTOR

1. Write a focused failing test for changed behavior. Run it and show the failure; a passing test added after the change alone is weaker evidence.
2. Apply the smallest correction without disabling controls or changing the claim/proof registry.
3. Re-run the failing test, then related tests and the existing `scripts/check_bug_sweep.py` checks.
4. For each discovered bug, identify its *family*. Sweep siblings; register a permanent guard. Record an `OPEN` incident, and only close it by referencing a canonical `GUARDED` bug class and a live regression test.
5. Run `python -m scripts.cace_prepr_gate --base-ref origin/main --change-kind <feature|bugfix|refactor|docs|test|infrastructure> --profile quick`. No `PASS_QUICK_ONLY`, no PR submission. An `inspect` run is non-executing and insufficient.
6. Inspect the output issues with codes, exact files, failure evidence and next actions. Do not claim success from a missing baseline, unrun command, manual attestation, generated text, or an omitted test.
   Always inspect `outstanding_specialized_gates`: a quick Python gate cannot compile Swift/iOS code, validate web browsers, run C++ native sanitizers, or certify Lean proofs. Run applicable toolchain tests separately before claiming PR readiness.
7. Independently validate exact-head CI and full CACE native, formal, security and qualification gates before merge/release when applicable. Local quick pass is neither scientific truth nor release approval.

## M.E.R.L.I.N. council roles

Sui proposes multiple fixes; Kestrel hunts counterexamples; Axiom checks source/type invariants; Vega checks physical/model implications; Harbor checks consent, welfare and privacy; Forge writes tests and checks the smallest implementation. All roles may use fallacy/bias and multidimensional lenses, but a character narrative is not a test run or permission. The council records its disagreement and observed tests. It may not vote to waive any mandatory gate.

## Resilient debugging

Classify actual failure: bad code, missing test, source drift, environment, unavailability, authorization, resource budget, or explicit authenticated policy restriction. Reframe an investigation only if data, method or assumptions genuinely change. Avoid endless unchanged retry loops. Do not infer censorship from ordinary failures. Never fabricate proof or runtime evidence.

## References

- `docs/PRE_PR_FAIL_FAST_AND_BUG_CLEARING.md`
- `docs/BUG_FLUSH_ARCHITECTURE.md`
- `quality/bug_incidents.json` active queue
- `quality/bug_classes.json` authoritative closed bug-class registry
- `scripts/cace_prepr_gate.py` project-only fail-fast tool
- `tests/test_prepr_gate.py` its adversarial regression suite
- separate CACE proof and source-to-formal qualification contracts
# CACE Bug-Flush Architecture

CACE treats every confirmed defect as evidence about a broader failure class. Fixing the observed line is not sufficient when a reusable invariant can be enforced.

## Required loop

1. Reproduce the defect precisely.
2. Identify the defect class and its authoritative source of truth.
3. Sweep the entire affected file for sibling instances.
4. Sweep active repository code/tests/data for the same defect class when practical.
5. Fix the implementation or fixture without weakening a scientific or formal gate.
6. Add or strengthen a regression test.
7. Add a permanent machine-checkable guard to `quality/bug_patterns.json` or `scripts/check_bug_sweep.py` when the class is structurally detectable.
8. Run the bug sweep, native build/smoke test, full Python regression, and qualification-drift audit on the exact commit.
9. Keep formal qualification separate: passing the bug-flush pipeline does not create formal proof evidence or current-head qualification.

## Layers

### 1. Environment preflight

The durable runner verifies required native tooling before the regression suite. Missing infrastructure fails explicitly rather than masquerading as a product defect.

### 2. Structural sweep

`scripts/check_bug_sweep.py` checks Python syntax, JSON parseability, registered recurring bug patterns, canonical claim/contract/ledger links, qualification conflicts, and stale active references to the authoritative v3.30 proof contract.

### 3. Source-of-truth tests

Tests that validate wiring derive current schema/contract metadata from canonical types and registries instead of duplicating version literals. Governance and qualification checks remain responsible for deciding whether a contract change is authorized.

### 4. Runtime regression

The full pytest suite remains authoritative for executable Python behavior. Confirmed runtime bugs should receive regression tests, preferably property/adversarial tests when the state space is larger than a few examples.

### 5. Native regression

The C++ runtime is compiled and smoke-tested before Python runs that may expose the native library. Additional warning/sanitizer/fuzz gates can be layered here after the baseline pipeline is green.

### 6. Qualification drift

Qualification-sensitive changes are checked independently. Bug-flush success never upgrades proof status and never substitutes caches, test metadata, or generated navigation artifacts for exact-head formal evidence.

## CI aggregation

Independent checks should be allowed to report in the same runner cycle where doing so does not create misleading cascade failures. The workflow records the bug sweep, Python regression, and qualification-drift outcomes and then applies one fail-closed acceptance gate. This reduces repeated cycles where one independent failure hides another.

## Future hardening order

After the baseline architecture is green:

1. targeted Python static analysis for undefined names and invalid constructs;
2. Hypothesis property suites for identities, serialization, mutation detection, graph scope, and fail-closed validation;
3. C++ `-Wall -Wextra -Wpedantic` warning-clean gate, followed by ASan/UBSan where supported;
4. Python/C++ differential tests for kernels implemented in both layers;
5. bounded fuzz corpora for parsers, schemas, graph inputs, and C API boundaries;
6. mutation testing on high-risk provenance/qualification modules;
7. deterministic clean-room replay of regression evidence.

Each layer is additive. None may weaken the canonical Lean/kernel qualification path.

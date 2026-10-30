# MCFC–CACE / M.E.R.L.I.N. — Fail-Fast and Bug-Clearing Architecture

**Scope:** ONLY this project and code generated/changed by its ChatGPT or M.E.R.L.I.N. agents. This does not modify instructions or workflows for unrelated projects.

**Status:** engineering process; not mathematical/scientific proof, a security audit, production authorization, or an autonomous deployment permission.

## Contract: engineering specification before coding

For any modification, write the expected behavior and regression risk before editing. Include intent, source and expected input/output types, affected code paths, invariants, failure modes, permissions and data privacy, downstream compatibility, resource budgets, and measurable acceptance criteria. Review existing canonical CACE source and its `AGENTS.md`, A–I plan, claim/proof boundaries, goal registry, and idea ledger.

No code change is complete until the before/after behavior is supported by tests. When fixing a bug, reproduce it with a **failing test** (RED), implement the minimal root-cause correction (GREEN), rerun it, seek related defects (sibling sweep), and then run all impacted tests and the static bug sweep.

## Three separate acceptance layers

### Gate A — Fast local pre-PR (this contribution)

1. Select the exact base branch and detect committed, staged, unstaged and untracked source changes. Missing baseline is a blocker, not a PASS.
2. Fail for zero identified changes, over-budget change sets, unsafe paths or symlinked source, Python syntax errors and malformed changed JSON.
3. Enforce truthful `--change-kind` (`feature`, `bugfix`, `refactor`, `docs`, `test`, `infrastructure`). Runtime and CI changes require changed, related regression tests.
4. Load `quality/bug_incidents.json`; unresolved `OPEN` bug records block. A `GUARDED` bug closure must reference a real changed reproducer test, an explicit root cause/sibling sweep and an existing canonical `GUARDED` class in `quality/bug_classes.json`.
5. Run changed tests through bounded `python -m pytest` with no shell. Reuse the existing `python -m scripts.check_bug_sweep --output ...` so canonical bug classes/guards, registry hashes, source links, JSON and proof-contract conflicts are also checked.
6. Record a deterministic local source-file hash manifest, each failing gate and suggested repair. The only successful outputs are `PASS_STATIC_ONLY` for inspection or `PASS_QUICK_ONLY` after bounded tests and bug sweep, **never** `FORMAL` or full CI qualification.

Default command, from a full Git checkout with `origin/main` available:

```bash
python -m scripts.cace_prepr_gate --base-ref origin/main --change-kind feature --profile quick --output prepr-local.json
```

For bug fixes use `--change-kind bugfix` and register the defect before seeking closure. `--profile inspect` performs non-executing static checks only and cannot substitute for the quick test gate. For a large worktree, split it into smaller meaningful branches or source shards; do not disable budget checks.

### Gate B — Bug-class closure (existing canonical CACE architecture)

`docs/BUG_FLUSH_ARCHITECTURE.md`, `quality/bug_classes.json`, `quality/bug_patterns.json`, and `scripts/check_bug_sweep.py` are the existing canonical mechanisms. On a confirmed bug:

1. Save the exact failing input, environment and output; create an `OPEN` incident in `quality/bug_incidents.json` (redact private data).
2. Add a reproducer test and confirm it fails for the original defect. Identify the true source of truth and determine the root cause.
3. Sweep sibling call sites, nearby code, related types, tests and configurations for the same defect family; add property or adversarial cases when warranted.
4. Fix **the class**, not just one observed symptom. Keep existing proof, security and authorization protections intact.
5. Register the permanent guard in `quality/bug_classes.json` with its required first-observation identity, root cause, reproducer/guard references and content SHA. Add a rule to `quality/bug_patterns.json` if the issue admits static detection.
6. Transition the incident to `GUARDED` only after the canonical class and changed regression test exist; do not remove or rename records just to pass the gate.
7. Run the local gate again, and pass independent CI before merging.

Example queue entry (illustrative; not current bug evidence):

```json
{
  "id": "BUG-EXAMPLE-001",
  "status": "OPEN",
  "summary": "An observed failure with a reproducer",
  "root_cause": "Investigation pending",
  "reproducer_test": "tests/test_repro_example.py",
  "sibling_sweep": "Pending scope audit",
  "guarded_class_id": ""
}
```

The queue is not allowed to grant `GUARDED` unless the canonical content-addressed class exists. Existing CACE bug-class digests and guards remain independently checked.

### Gate C — Full merge/release qualification (NOT covered by local quick gate)

As appropriate to changed scope: CACE full Python regression; native C++ build/ctest; wheel/installed interfaces; security/permission tests; reproducibility/known-failure checks; qualification drift; exact-head pinned Lean with kernel/axiom/source binding when required; controlled CI evidence; authorization and rollback. No local green quick result can issue `PASS`, `VERIFIED`, `FORMAL`, release permission, or promotion of proof state.

## Optional local hook (not automatically installed)

A pre-push hook is supplied at `.githooks/pre-push`. To choose it intentionally *for this repository only*:

```bash
git config --local core.hooksPath .githooks
```

Specify `CACE_CHANGE_KIND=bugfix` (or another supported value) when pushing a bug fix. The hook fails closed when the baseline is missing. It should not be installed globally and does not override independent PR/branch protection requirements.

## Work improvement loop

Measure defect escape rate, reopens, root-cause-family recurrence, test detection latency, false-positive blocker rate, total preflight time and full-CI cost. Preserve a provenance-linked negative result and propose small reviewed improvements; do not weaken gates to manipulate pass counts. For high-dimensional/fuzzy councils, alternative risk priorities can inform where to test, but do not override deterministic pass/fail criteria. If blocked, classify environment, permissions, source access, logic defect, infrastructure limit or absent evidence accurately, then choose an authorized revised test. Stop unchanged retries.

## Known limitations of this first gate

- Python `compile` checks syntax, not imports/type safety. JSON parsing is not complete schema validation.
- Focused tests only cover changed tests, not arbitrary downstream dependents. Matching test filenames is a heuristic; broader CACE CI remains essential.
- It does not run native C++, Lean, or entire pytest suite.
- It is an inspectable local process, not a security sandbox. A malicious local test or bug-sweep script could have arbitrary side effects; use a trusted repository checkout and isolated runner.
- Git hooks can be bypassed by local users; repository review and CI policies remain independently necessary.
- Local content hashes identify bytes but do not attest who executed the check or approve scientific conclusions.
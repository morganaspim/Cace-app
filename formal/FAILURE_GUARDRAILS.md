# CACE Proof Failure Guardrails

Policy: **a failure may be discovered once; the same failure class must not reach the expensive exact-pin/root runner twice.**

Every entry records the failure fingerprint, root cause, permanent prevention, and the regression guard that must remain in the repository.

## F-001 — stale/nonexistent workflow target

**Fingerprint:** workflow input referenced a Lean module that did not exist, so the run failed before Lean compilation.

**Root cause:** workflow default drifted away from the audited root.

**Permanent prevention:**
- exact-pin workflow validates the requested file exists;
- requested module must be directly imported by the audited root;
- default target is a stable root import.

**Regression guard:** `scripts/cace_proof_guardrails.py validate` plus workflow target validation.

## F-002 — affine structure elaboration/extensionality mismatch

**Fingerprint:** unsafe/unsupported derived representation or missing extensionality caused downstream affine proofs to fail.

**Root cause:** relying on generated/implicit structure behavior rather than an explicit theorem surface.

**Permanent prevention:**
- explicit `Point2.ext` and `Triangle2.ext`;
- no proof-critical dependence on derived `Repr` for real-valued structures;
- compile API canary before dependent modules.

**Regression guard:** `CACEFormal.GuardrailCanaries`.

## F-003 — orthogonal-complement scalar/typeclass mismatch

**Fingerprint:** `Sᗮ` elaborated with a different module/normed-space instance than the existing graph submodule.

**Root cause:** introducing an inner-product construction across an ambient type whose existing module instance was not definitionally identical to the inferred one.

**Permanent prevention:**
- experimental orthogonal-density route is quarantined from the audited root;
- scalar-sensitive APIs must use explicit scalar/ambient types or a separately compiled compatibility lemma before promotion.

**Regression guard:** audited-root quarantine policy in `proof_guardrails.json`.

## F-004 — unfinished experimental analytic theorem imported into audited root

**Fingerprint:** an exploratory Fourier/H(div) module blocked the trusted root before its standalone theorem layer compiled.

**Root cause:** promotion happened before standalone compile qualification.

**Permanent prevention:**
- exact root import allowlist;
- explicit quarantine list;
- candidate modules may exist in the repository without being root-qualified.

**Regression guard:** `scripts/cace_proof_guardrails.py validate`.

## F-005 — unsupported `fun_prop` temperate-growth proof

**Fingerprint:** Mathlib could not synthesize `HasTemperateGrowth` for the custom positive-Laplacian resolvent symbol.

**Root cause:** assuming an automation tactic covered a nonlinear reciprocal symbol without first proving the exact API lemma.

**Permanent prevention:**
- Fourier annihilator remains quarantined;
- sensitive Mathlib APIs must first compile in a canary/standalone module before root promotion.

**Regression guard:** quarantine policy + canary-before-promotion rule.

## F-006 — definitional equality used where algebraic normalization was required

**Fingerprint:** goals such as `k*x + y = y + k*x` or double-negation/zero simplifications survived `rfl`/plain `simp`.

**Root cause:** treating algebraic equality as definitional equality.

**Permanent prevention:**
- use `ring`, `norm_num`, or explicit simp lemmas for algebraic seams;
- new transform primitives get a compile canary before reverse dependents.

**Regression guard:** affine/dual API canaries + impacted-module compilation.

## F-007 — source-sanity job with zero executed steps

**Fingerprint:** GitHub Actions job reports failure but contains zero steps.

**Root cause:** CI/infrastructure startup failure, not Lean source or theorem failure.

**Permanent prevention:**
- classify zero-step jobs as infrastructure evidence only;
- never treat them as proof failures.

**Regression guard:** proof-status reporting distinguishes infrastructure/configuration/Lean/kernel failures.

## F-008 — exact-head drift after validation starts

**Fingerprint:** validation result could be mistakenly associated with a newer commit.

**Root cause:** mutable branch name used as a human reference instead of a content-addressed proof plan.

**Permanent prevention:**
- checkout and assert exact `GITHUB_SHA`;
- qualification-plan SHA-256 binds toolchain, Mathlib pin, target, guardrail policy, root source closure, and source bytes;
- any commit creates a different plan hash.

**Regression guard:** `scripts/cace_proof_guardrails.py plan-hash`.

## Required promotion states

A trust-bearing theorem/module moves only through:

```
EXPERIMENTAL
  -> STANDALONE_COMPILED
  -> ROOT_COMPILED
  -> AXIOM_AUDITED
  -> EXACT_HEAD_QUALIFIED
```

No stage may be inferred from a later branch name, previous SHA, numerical test, symbolic test, or AI recommendation.

## Runner policy

Before an expensive root/canonical run:

1. static source sanity;
2. guardrail-policy validation;
3. API canary compile;
4. changed-module + reverse-dependent compile;
5. exact audited-root compile;
6. kernel/metadata/canonical qualification only after the exact root is green.


## F-009 — malformed workflow edit / duplicated-truncated steps

**Fingerprint:** an automated workflow edit accidentally duplicated/truncated YAML step blocks before dispatch.

**Root cause:** incremental text splicing of a safety-critical workflow without an independent structural regression check.

**Permanent prevention:**
- safety-critical exact-pin workflow is replaced atomically when substantial structure changes;
- `scripts/check_cace_workflow_guardrails.py` locks the required unique step surface and order;
- the cheap source-sanity workflow validates exact-pin workflow structure whenever the workflow or guardrail files change;
- exact-pin preflight also self-checks the workflow structure before any Lean/cache work.

**Regression guard:** `scripts/check_cace_workflow_guardrails.py`.

This incident was caught before a runner dispatch; it is nevertheless recorded because the rule is that a discovered failure class receives a permanent guard.


## F-010 — recursive import validator missed a missing reached module

**Fingerprint:** the first guardrail implementation checked missing child imports but could fail to flag a missing module node already reached by the root-closure traversal.

**Root cause:** validation inspected outgoing edges of reached nodes instead of directly comparing the reached CACEFormal module set with the source graph.

**Permanent prevention:**
- `missing_internal_modules` compares every reached CACEFormal module against the source graph;
- a pure unit regression constructs `CACEFormal.A -> CACEFormal.Missing` and requires the missing module to be reported;
- proof-plan generation still fails separately if a root-closure source file is absent.

**Regression guard:** `tests/test_cace_proof_guardrails.py::test_missing_recursive_internal_module_is_rejected_by_graph_check`.


## F-011 — status chatter contaminated machine-readable guardrail output

**Fingerprint:** the guardrail `validate` routine printed a human status line to stdout while the
`impacted` and `plan-hash` commands redirected stdout into machine-readable files.  The impacted
list gained a fake 53rd entry and the proof-plan JSON became non-JSON, causing parsing to fail before
Lean/cache work.

**Root cause:** human diagnostics and machine payloads shared stdout.

**Permanent prevention:**
- `validate(config, emit=False)` is used by machine-output subcommands;
- `impacted` stdout is reserved exclusively for `CACEFormal.*` module names;
- `plan-hash` stdout is reserved exclusively for one JSON document;
- exact-pin workflow rejects non-module or duplicate impacted-list records before compilation;
- unit tests require silent validation and JSON-serializable proof-plan payloads.

**Regression guard:** `tests/test_cace_proof_guardrails.py`,
`scripts/check_cace_workflow_guardrails.py`, and impacted-list validation in the exact-pin workflow.


## F-012 — JavaScript replacement token duplicated workflow content

**Fingerprint:** an automated repository edit used JavaScript `String.replace(search, replacementString)`
where the replacement text contained the shell-regex sequence `$'`.  JavaScript interprets `$'`
inside replacement strings as “insert the suffix after the match”, duplicating/truncating the workflow.

**Root cause:** using replacement-string semantics on shell/YAML text containing dollar-sign sequences.

**Permanent prevention:**
- safety-critical workflow is restored from a known-clean SHA;
- canonical byte-for-byte template lives at `ci/cace-exact-pin-lean-preflight.canonical.yml`;
- `check_cace_workflow_guardrails.py` rejects any byte difference between runnable workflow and canonical template;
- future substantial workflow edits must update the canonical file first and copy it verbatim;
- programmatic replacements in safety-critical text use callback/slicing semantics, never replacement-string semantics.

**Regression guard:** canonical workflow equality check plus the existing 15-step unique-order checker.


## F-013 — fail-fast compile masked independent Lean failures

**Fingerprint:** the API-canary step discovered multiple failures, but GitHub Actions skipped impacted-module, target, and root compilation after the canary step failed.

**Root cause:** proof compilation stages used normal fail-fast job semantics.

**Permanent prevention:**
- canary, impacted-module, requested-target, plan-recheck, and audited-root diagnostic stages use `continue-on-error: true`;
- each compile stage writes its own log artifact;
- a final `Aggregate diagnostic sweep failures` step records every failed diagnostic stage and is the single compile-failure gate;
- impacted modules are submitted together so Lake can expose all independent failures reachable from the same dependency frontier.

**Regression guard:** workflow canonical template, `check_cace_workflow_guardrails.py`, and `test_exact_pin_workflow_collects_compile_failure_frontier`.

This does not make dependent errors magically visible through a broken prerequisite. It exposes the entire independent failure frontier available from the current SHA, minimizing the number of user-dispatched runs.

## F-014 — real-valued definition with division omitted `noncomputable`

**Fingerprint:** `Affine2.piolaVector` failed because real division depends on Lean's noncomputable real inverse implementation.

**Root cause:** a proof-level real-valued definition using division was declared with plain `def`.

**Permanent prevention:**
- `Affine2.piolaVector` is explicitly `noncomputable def`;
- the proof API canary imports and typechecks the Piola layer before impacted/root compilation.

**Regression guard:** `CACEFormal.GuardrailCanaries` imports and exercises Piola/dual-blade flux APIs.

## F-015 — Lean reserved keyword used as an `rcases` pattern identifier

**Fingerprint:** `rcases b with ⟨bx, by⟩` failed to parse because `by` is a Lean keyword.

**Root cause:** generated/local coordinate naming accidentally selected a reserved token.

**Permanent prevention:**
- coordinate renamed to `by_`;
- source regression rejects `by` as an identifier inside `rcases ... with ⟨...⟩` patterns in the affected exterior-transport source.

**Regression guard:** `test_no_reserved_by_identifier_in_rcases_patterns`.

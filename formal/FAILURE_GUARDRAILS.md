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

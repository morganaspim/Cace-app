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
- `Affine2.piolaVector`, `DualBladePiola.piolaSequence`,
  `AffineP1RT0Transport.piolaRT0`, `AffineP1RT0Transport.pullP1`, and
  `ReferenceSimplexNormalization.normalizer` are explicitly `noncomputable def`;
- reference-normalization certificate constructors that depend on the normalizer are also
  explicitly noncomputable;
- the dependency-free known-regression gate checks this declaration surface before Lean/cache work;
- the proof API canary imports and typechecks the Piola, affine P1/RT0, and reference-normalization layers.

**Regression guard:** `scripts/check_cace_known_failure_regressions.py`,
`tests/test_cace_proof_guardrails.py`, and `CACEFormal.GuardrailCanaries`.

## F-015 — Lean reserved keyword used as an `rcases` pattern identifier

**Fingerprint:** `rcases b with ⟨bx, by⟩` failed to parse because `by` is a Lean keyword.

**Root cause:** generated/local coordinate naming accidentally selected a reserved token.

**Permanent prevention:**
- coordinate renamed to `by_`;
- source regression rejects `by` as an identifier inside `rcases ... with ⟨...⟩` patterns in the affected exterior-transport source.

**Regression guard:** `test_no_reserved_by_identifier_in_rcases_patterns`.


## F-016 — equivalent determinant denominators were not syntactically aligned

**Fingerprint:** `field_simp [hdet]` left inverse factors such as
`(ad * aa - ac * ab)⁻¹` even though the available hypothesis was
`aa * ad - ab * ac ≠ 0`.

**Root cause:** the denominators are mathematically equal by commutativity but were not
syntactically identical after simplification, so the nonzero hypothesis was not reused.

**Permanent prevention:**
- prove an explicit commuted-denominator nonzero lemma before `field_simp`;
- prefer deriving composite identities from already-proved functorial laws rather than
  fully expanding determinants;
- `DualBladePiola.piola_comp` now factors through `piolaVector_eq_grade1_div`,
  `grade1_comp`, and `Affine2.linearDet_comp`.

**Regression guard:** `CACEFormal.GuardrailCanaries` directly checks
`pullP1_eval_map` and `piola_comp`.

## F-017 — cleanup tactic executed after the goal was already closed

**Fingerprint:** Lean reported `No goals to be solved` after a separate `ring` line
following `field_simp [hdet]`.

**Root cause:** `field_simp` had already discharged the equality, leaving the next
standalone tactic with no goals.

**Permanent prevention:**
- remove redundant post-`field_simp` tactics when the simplifier closes the goal;
- for genuinely generated subgoals, use a combinator form such as `field_simp [...] <;> ring`
so the follow-up tactic is applied only to remaining goals.

**Regression guard:** early compile canaries pin `cellPairing_map` and
`cellDivergence_map`.

## F-018 — ring normalization changed determinant monomial order after the nonzero bridge

**Fingerprint:** repeated reference-simplex runs failed because algebraically equal
determinants were rewritten into different expanded/factored denominator spellings.

**Root cause:** `normalizer_map_p1` reopened raw coordinate division and depended on
syntactic alignment between tactic-normalized denominators and separately proved
nonzero hypotheses.

**Permanent prevention:**
- the normalizer is factored into `recenterMap` followed by `inverseEdgeLinear`;
- `edgeDet` is one named determinant object shared by both inverse-column theorems;
- `inverseEdgeLinear_map_e1` and `inverseEdgeLinear_map_e2` establish one local
  canonical commuted nonzero bridge `hΔcomm` before denominator clearing;
- `inverseEdgeLinear_linearDet` discharges its reciprocal determinant directly;
- `normalizer_map_p1` and `normalizer_map_p2` delegate to those lemmas and no
  longer contain raw denominator normalization logic.

**Regression guard:** `scripts/check_cace_known_failure_regressions.py` requires the
inverse-edge theorem surface, requires both inverse-column lemmas to establish
`hΔcomm` before `field_simp [hΔ, hΔcomm]`, requires `normalizer_map_p1` to
delegate to `inverseEdgeLinear_map_e1`, and rejects reintroduction of the old raw
denominator tactic seam.

## F-019 — raw structure unfolding blocked rational-to-real Jacobian coercion

**Fingerprint:** `exact_mod_cast` had the correct rational signed-Jacobian equality,
but the real target still contained unreduced `Triangle2` structure projections such
as an explicit record followed by `.p1.x`.  The cast theorem therefore did not match
the target syntactically.

**Root cause:** `unfold realTriangle realPoint Triangle2.det` exposed record
constructors without simplifying their projections before invoking `exact_mod_cast`.

**Permanent prevention:**
- simplify the canonical mesh triangle and point constructors with
  `simp only [realTriangle, realPoint, Triangle2.det]` before casting;
- use the existing `MeshCertificate.signedJacobian_formula` as the sole rational
  source of the determinant equality;
- do not duplicate the Jacobian polynomial as a new independent certificate.

**Regression guard:** `scripts/check_cace_known_failure_regressions.py` requires
`realTriangle_det` to simplify the structure projections before `exact_mod_cast`
and rejects the known raw-`unfold` seam.


## F-020 — unsigned physical real-valued definitions omitted `noncomputable`

**Fingerprint:** `PhysicalP1RT0Element.cellPairing` and
`PhysicalP1RT0Element.cellDivergence` failed code generation because real
division depends on Lean's noncomputable real inverse implementation.

**Root cause:** the new unsigned physical semantics used `|det| / 6` over
`ℝ` but were introduced as plain `def` declarations.

**Permanent prevention:**
- both physical cell functionals are explicitly `noncomputable def`;
- every proof-level real-valued definition that introduces division is added to
  the dependency-free noncomputable declaration guard before another runner
  dispatch.

**Regression guard:** `scripts/check_cace_known_failure_regressions.py`,
`tests/test_cace_proof_guardrails.py`, and the existing proof API canary import
of `PhysicalP1RT0Element`.

## F-021 — rational-to-real recentering left negated coordinate casts opaque

**Fingerprint:** `ExecutableRationalGeometry.recenterMap_toReal` left the goal

```
Affine2.translation ({x := -p.x, y := -p.y}.toReal) =
Affine2.translation {x := -p.toReal.x, y := -p.toReal.y}
```

after the original simplification pass.

**Root cause:** the proof unfolded triangle/recentering structure but did not
explicitly normalize the rational point embedding, so casts of negated rational
coordinates remained behind `Point.toReal`.

**Permanent prevention:**
- `recenterMap_toReal` explicitly simplifies `Point.toReal` and reuses
  `Affine.translation_toReal`;
- the cheap known-failure gate requires the point-embedding normalization seam
  to remain visible in this theorem.

**Regression guard:** `scripts/check_cace_known_failure_regressions.py`,
`tests/test_cace_proof_guardrails.py`, and `CACEFormal.GuardrailCanaries`.


## F-022 — shallow canonical checkout hid a valid attested ancestor

**Fingerprint:** canonical qualification failed in the cheap drift-audit phase with
`attested commit ... is not an ancestor of HEAD`, while the repository graph
showed the attested commit was in fact an ancestor.

**Root cause:** the canonical workflow checked out only 64 commits of history.
The qualified ancestor was farther back, so `git merge-base --is-ancestor`
operated on an incomplete local graph and failed closed for the wrong reason.

**Permanent prevention:**
- canonical qualification starts with a bounded 64-commit checkout;
- before qualification-drift tests, it extracts every currently-qualified
  attested commit from the canonical claim registry and verifies ancestry;
- missing ancestry is deepened by 256 commits first, with an unshallow fetch
  only as a correctness fallback;
- qualification inheritance therefore always runs against enough repository
  ancestry without paying the disk cost of full history on every run;
- exact-head checkout and clean-worktree checks remain unchanged.

**Regression guard:** `tests/test_qualification_drift_v331.py::test_canonical_qualification_checkout_has_complete_ancestry`.

This does not weaken qualification drift. It makes the existing fail-closed
ancestry check operate on complete evidence while keeping the common path
storage-bounded.


## F-023 — unbounded validated build-cache retention exhausted runner reserve

**Fingerprint:** canonical qualification passed all cheap truth/governance tests,
then stopped before Lean with `Formal qualification requires at least 5 GiB
free` even though recent canonical runs had 9–11 GiB free.

**Root cause:** exact-formal-tree build caches are intentionally persistent for
resumability, but successful qualifications accumulated one validated build tree
per formal tree with no retention bound. The 30 GiB OCI root volume eventually
fell below the existing 5 GiB safety reserve.

**Permanent prevention:**
- the 5 GiB free-space requirement is unchanged;
- only when the runner is below that reserve, canonical CI takes an exclusive
  cache-prune lock;
- interrupted owned staging directories are removed;
- per-tree build caches are treated strictly as acceleration, never evidence;
- the current formal-tree cache and two newest compatible ancestor caches are
  preserved, while older owned 40-hex tree caches may be deleted until the
  reserve is restored;
- the workflow rechecks the same 5 GiB floor both before and after source
  staging.

**Regression guard:** `tests/test_qualification_drift_v331.py::test_canonical_qualification_prunes_only_owned_cache_acceleration_before_disk_gate`.

Deleting an old build cache cannot inherit or create qualification. Lake still
rebuilds changed/reverse-dependent modules and canonical qualification still
requires fresh exact-head theorem metadata, kernel axiom audit, and attestation.


## F-024 — full-history ancestry repair consumed qualification disk reserve

**Fingerprint:** after fixing shallow-history ancestry by unconditionally fetching
the complete repository history, canonical qualification passed governance but
stopped at the 5 GiB free-space gate with only about 4.57 GiB available.

**Root cause:** correctness was restored with an unnecessarily expensive checkout
strategy. Complete history was downloaded even though the active attested commit
was only modestly beyond the original shallow boundary.

**Permanent prevention:**
- qualification checkout is shallow by default;
- the workflow deterministically deepens only until all currently-qualified
  attested commits are provably connected to HEAD;
- full unshallow history is retained only as a rare correctness fallback;
- the 5 GiB qualification disk reserve remains unchanged;
- old owned resumable proof-build caches are separately bounded and pruned as
  acceleration data, never as proof evidence.

**Regression guard:** `tests/test_qualification_drift_v331.py::test_canonical_qualification_checkout_has_complete_ancestry`
and `test_canonical_qualification_prunes_only_owned_cache_acceleration_before_disk_gate`.


## F-025 — adaptive ancestry fetch lost checkout authentication

**Fingerprint:** the qualification ancestry step failed with
`fatal: could not read Username for 'https://github.com'` while attempting
`git fetch --deepen`.

**Root cause:** the initial exact-head checkout deliberately used
`persist-credentials: false`, but the new adaptive ancestry design performs a
second read-only fetch after checkout. The remote therefore had no usable
authentication for that deepen operation.

**Permanent prevention:**
- canonical qualification keeps the workflow-scoped `contents: read` checkout
  credential available for the ancestry deepen/unshallow step;
- the token remains read-only and is removed by the checkout action's post-job
  cleanup;
- no write permission is added and exact-head/clean-worktree checks remain
  unchanged.

**Regression guard:** `tests/test_qualification_drift_v331.py::test_canonical_qualification_checkout_has_complete_ancestry`
requires the adaptive fetch surface and `persist-credentials: true`.


## F-026 — fixed ancestor-cache retention could still miss the disk reserve

**Fingerprint:** canonical qualification passed ancestry and governance, then
failed the unchanged 5 GiB reserve with 5,212,440 KiB free—about 30 MiB below
the required 5,242,880 KiB—because the pruning policy always preserved two
ancestor build caches.

**Root cause:** retention was expressed as a fixed cache count rather than the
actual safety invariant. A small runner-space deficit could therefore survive
pruning even though additional retained caches were disposable acceleration.

**Permanent prevention:**
- the 5 GiB reserve remains unchanged;
- owned 40-hex per-tree build caches are pruned oldest-first until the reserve
  is actually satisfied, preserving newer caches only while space permits;
- the current exact-tree cache is preserved during normal pruning, but may be
  deleted as a final fallback if it is the only cache preventing the reserve;
- pinned Lean/Mathlib dependency caches are not part of this pruning surface;
- all deleted build caches are reproducible acceleration and never proof
  evidence or qualification state.

**Regression guard:** `tests/test_qualification_drift_v331.py::test_canonical_qualification_prunes_only_owned_cache_acceleration_before_disk_gate`
requires oldest-first reserve-driven pruning, current-tree protection during the
normal pass, and the exact-tree final fallback.


## F-027 — pruning to the exact reserve left no room for source staging

**Fingerprint:** a run could satisfy the pre-copy 5 GiB disk check and then fail
the identical post-copy reserve check after the formal source bundle was staged
into the isolated qualification directory.

**Root cause:** pruning targeted the final safety reserve itself rather than the
reserve plus the deterministic bytes that the next source-staging step must
consume.

**Permanent prevention:**
- the final qualification reserve remains exactly 5 GiB;
- before cache pruning, CI measures `du -sk formal/cace_formal`;
- the pre-copy pruning target is `5 GiB + measured formal-source size`;
- the post-copy gate still independently requires the original 5 GiB floor;
- only owned reproducible build caches participate in pruning.

**Regression guard:** `tests/test_qualification_drift_v331.py::test_canonical_qualification_prunes_only_owned_cache_acceleration_before_disk_gate`
requires the measured source-size headroom and preserves the unchanged post-copy
5 GiB check.


## F-028 — standalone quarantine lane required root promotion

**Fingerprint:** an experimental H(div) density module was correctly kept out of the audited root,
but the only exact-pin preflight rejected every target that was not already a direct audited-root
import. This made the documented promotion sequence impossible: a quarantined module could not
reach `STANDALONE_COMPILED` without first violating quarantine.

**Root cause:** the preflight target validator encoded the root-qualified case only, while the
failure ledger separately required standalone compilation before root promotion.

**Permanent prevention:**
- audited-root targets remain accepted exactly as before;
- a non-root target is accepted only when `compile_root=false`;
- that non-root target must be explicitly listed in `quarantined_root_imports`;
- quarantined standalone targets are forbidden from simultaneously appearing in the root allowlist;
- `compile_root=true` still rejects any target that is not directly imported by the audited root;
- the workflow and its canonical byte-for-byte template carry the same fail-closed logic;
- promotion is a deliberate state transition: promoted modules must leave quarantine before
  they may enter either the audited root or its recursive root closure;
- the root-closure guard rejects any future state in which a quarantined dependency becomes
  reachable through a promoted module.

**Regression guard:** `scripts/check_cace_workflow_guardrails.py` requires the quarantine-only
standalone branch, while `scripts/cace_proof_guardrails.py` and
`tests/test_cace_proof_guardrails.py` enforce both quarantine isolation and the explicit
promotion transition.

Standalone compilation remains engineering evidence only. Root promotion additionally requires
root compilation, kernel axiom audit, exact Lean-environment metadata, and exact-head qualification.


## F-029 — positive-Laplacian multiplier scalar/API drift

**Fingerprint:** the standalone positive-Laplacian dependency reached Lean and exposed several
independent failures at once: theorem composition parsed as the nonexistent constant
`Complex.hasTemperateGrowth_ofReal.comp`, real/complex coefficient normalization drifted,
plain `map_smul` could not preserve the real-to-complex scalar tower, and multiplier algebra
used incompatible spellings of the same `(2π)²` coefficient.

**Root cause:** the experimental Fourier annihilator mixed equivalent real and complex scalar
representations and relied on fragile theorem-dot parsing instead of the pinned Mathlib API.

**Permanent prevention:**
- compose the Bessel-potential growth proof with
  `(Function.Complex.hasTemperateGrowth_ofReal).comp` explicitly for the pinned Mathlib revision;
- use one canonical coefficient `Complex.ofReal ((2 * Real.pi) ^ 2)`;
- use `ContinuousLinearMap.map_smul_of_tower` across the real/complex module tower;
- normalize the final real scalar action with `Complex.coe_smul`;
- reject reintroduction of plain `rw [map_smul]` in the low-Laplacian multiplier block.

**Regression guard:** `scripts/check_cace_known_failure_regressions.py`.


## F-030 — H(div) zero-normalization mismatch

**Fingerprint:** after the positive-Laplacian dependency compiled, the H(div) annihilator
failed when `complexL2ToDistribution_injective` was applied directly to
`complexL2ToDistribution n x.2 = 0`, while injectivity expected an equality against
`complexL2ToDistribution n 0`.

**Root cause:** Lean did not definitionally identify the literal zero in the distribution
codomain with the image of zero under the continuous linear embedding at that application site.

**Permanent prevention:**
- introduce the L2 zero conclusion with an explicit injectivity application;
- normalize the distributional equality with `simpa using hgDist` before invoking injectivity;
- reject the fragile direct application `complexL2ToDistribution_injective n hgDist`.

**Regression guard:** `scripts/check_cace_known_failure_regressions.py`.


## F-031 — proof-hole regex used literal backslash escapes

**Fingerprint:** the Lean source-contract test intended to reject the proof-hole tokens
`sorry` and `admit`, but the regular expressions used doubled backslashes
(`\\\\b`), matching a literal backslash sequence rather than word boundaries.
The guard therefore failed to detect ordinary proof-hole tokens in Lean source.

**Root cause:** regex escaping was reviewed as source text without a mutation test
that demonstrated rejection of the actual forbidden tokens.

**Permanent prevention:**
- define the forbidden-token patterns as compiled Python regexes using actual
  word-boundary expressions: `re.compile(r"\\bsorry\\b")` and
  `re.compile(r"\\badmit\\b")`;
- exercise the detector with mutation canaries for `by sorry` and `by admit`;
- include positive controls for a valid proof token and an identifier such as
  `admitted_theorem`, preventing an overbroad substring check;
- keep the canaries in the ordinary CACE collaboration/formal-preflight test suite.

**Regression guard:**
`tests/test_merlin_continuum_simplex_lean_contract.py::test_proof_hole_detector_rejects_sorry_and_admit_tokens`.

The original detector fix and focused canaries passed CACE OCI collaboration validation on exact
head `84b4dae2c725b86a094396f62ae614b4ac433fc5`, run
[43466879333](https://github.com/morganaspim/Cace-app/actions/runs/43466879333).

**Tree-wide defense-in-depth extension (2026-11-13):** `scripts/check_lean_source_sanity.py`
now scans the comment/string-masked Lean source for whole-token `sorry` and `admit` occurrences,
so comments and string literals do not create false positives. The exact-pin preflight workflow
runs the scanner over `formal/cace_formal` before compilation, in addition to scanning each
selected batch target. `tests/test_lean_source_sanity.py` adds positive/negative token fixtures.
This extends the F-031 guardrail; it is not a new defect class. The scanner implementation passed
CACE collaboration validation and Lean Source Sanity on exact head
`dca948e89c8153693b287da8c8c31caa84a568eb`, runs
[43469516682](https://github.com/morganaspim/Cace-app/actions/runs/43469516682) and
[43469517086](https://github.com/morganaspim/Cace-app/actions/runs/43469517086).
The subsequent multiline mutation-test fixture correction is commit
`f66eaa63c5480bc49db2d377019087d4e1643475`; its exact-head CI result is pending.
Neither result is a Lean kernel compilation or proof qualification.


## F-032 — exact-pin workflow canonical-template drift

**Fingerprint:** the source-sanity gate rejected an otherwise valid exact-pin workflow after a
toolchain-specific package-cache lock path was corrected in the runnable workflow but not in its
canonical template. The guard compares the two files byte-for-byte, so the drift was detected
before the exact-pin workflow could be trusted.

**Root cause:** a safety-critical workflow is maintained as both an executable file and a
canonical source template; a one-file edit left those two representations inconsistent.

**Permanent prevention:**
- change the runnable workflow and canonical template in the same change set;
- keep the lock path namespaced by the exact Lean toolchain and Mathlib commit, rather than
  reusing a stale cache-lock name from a different toolchain generation;
- preserve the byte-for-byte comparison in the structural guard;
- run the source-sanity gate after any exact-pin workflow change and do not count a cancelled
  or stale-head run as validation.

**Regression guard:** `scripts/check_cace_workflow_guardrails.py` compares the runnable workflow
with `ci/cace-exact-pin-lean-preflight.canonical.yml`; the comparison is exercised by
`scripts/check_cace_workflow_guardrails.py` in both source-sanity and collaboration validation.

**Observed repair:** the runnable and canonical files now both use the lock namespace
`v4.32.1-520045ab14e26149ee970e2e617ca04b09bde5d6`. The failed exact-head run
[43601413924](https://github.com/morganaspim/Cace-app/actions/runs/43601413924) identified the
drift; it was corrected in commits `2716d0c4` and `1f958a07`. The follow-up collaboration
validation passed on `acc77735efaea10bf7179313ecba514a628297c7`, run
[43601511700](https://github.com/morganaspim/Cace-app/actions/runs/43601511700).

**Exact-head follow-up:** source-sanity run `43601438723` on `923d423f` failed only because the canonical mirror was one line behind the runnable workflow. The canonical mirror was synchronized in `1f958a07`. A fresh source-sanity run on the post-repair head is required before this defect class can be marked closed; the collaboration pass alone is not a substitute.


## F-033 — cache lock moved with the cache directory during atomic replacement

**Fingerprint:** the Lean package-cache lock was initially placed inside the versioned package-cache
directory. The prewarm workflow atomically renames that directory to a backup and replaces it with
a staging directory. A lock descriptor opened before the rename would continue to refer to the old
inode, while a second process could open a new lock file at the replacement path and enter the
critical section concurrently.

**Root cause:** the lock's filesystem location shared the lifecycle of the resource it was intended
to serialize.

**Permanent prevention:**
- place the lock in a stable sibling directory outside the replaceable package-cache tree;
- create the lock directory before both shared and exclusive acquisitions;
- namespace the lock by exact Lean toolchain and Mathlib commit;
- structurally reject lock paths nested under the package cache and require both acquisition sites
  to create the external lock directory.

**Regression guard:** `scripts/check_cace_workflow_guardrails.py` enforces the external path,
the exact pin namespace, the two directory-creation guards, and byte equality between the runnable
workflow and canonical template.

**Repair:** both workflow representations now use
`/var/lib/cace-cache/locks/mathlib-v4.32.1-520045ab14e26149ee970e2e617ca04b09bde5d6.lock`.
The old in-cache path was removed before the next exact-pin execution.

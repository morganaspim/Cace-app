# CACE v3.30 Proof Strengthening

Status: **IMPLEMENTED / PENDING PINNED RUNNER EXECUTION**

Base snapshot: `50cfdd10a6653c863d595502797b8f1a87c42333` (v3.29 pre-merge recovery snapshot)

Development branch: `roadmap/v3.30-proof-strengthening`

## Purpose

v3.30 addresses two distinct research-safety and proof-completion weaknesses:

1. CACE should close more routine-but-heavy analytic proof obligations automatically instead of
   requiring callers to provide low-level calculus certificates.
2. CACE must never turn its own numerical, symbolic, interval, or formal output into a public claim
   that a famous open problem is resolved without independent reproduction and external review.

These are deliberately separate. Better theorem automation is an internal mathematical capability;
external scrutiny is an independent trust boundary that software cannot honestly erase.

## Implemented strengthening

### 1. Automatic smooth product calculus for the box Green bridge

New file: `formal/cace_formal/CACEFormal/SmoothBoxGreenAuto.lean`

The v3.29 endpoint `boxGraphNormalTrace_smooth_eq_classical` required the caller to supply:

- a Frechet derivative family for `x -> v(x) q(x)`,
- a countable exceptional set,
- continuity of the product field,
- integrability of the divergence integrand, and
- the pointwise product/divergence identity.

v3.30 constructs these obligations directly from the actual Schwartz core. The new target endpoint is:

`CACEFormal.Continuum.boxGraphNormalTrace_smooth_eq_classical_auto`

Its mathematical inputs are only the box order hypothesis and the smooth Schwartz fields.

The construction uses the pinned Mathlib Frechet product rule and Pi-valued derivative assembly,
then reuses the already established v3.29 classical-agreement theorem instead of duplicating the
trace argument.

### 2. Graph-regularization criterion for the missing H(div) density direction

New file: `formal/cace_formal/CACEFormal/GraphRegularizationCriterion.lean`

v3.29 proved

`closure(Schwartz H(div) graph core) <= distributional H(div) graph`.

The difficult missing direction is the reverse inclusion. v3.30 now proves a reusable reduction:
if a sequence of regularizers `R_k` satisfies

- `R_k x` belongs to the Schwartz H(div) graph core for every distributional graph datum `x`, and
- `R_k x -> x` in the ambient L2 graph topology,

then Lean derives

`closure(Schwartz H(div) graph core) = distributional H(div) graph`

and therefore the reverse inclusion automatically.

This removes the closure/topology bookkeeping from the remaining research task. The unresolved
analytic core is now exactly the construction of such a regularizer and its graph-norm convergence.

Ranked routes for that remaining theorem:

1. **Fourier cutoff / multiplier regularization.** Best fit to the whole-space tempered-distribution
   model already used by CACE. Prove simultaneous L2 convergence of the field and divergence while
   preserving the distributional divergence relation.
2. **Mollification plus Schwartz cutoff.** More classical physically, but requires a cutoff
   commutator estimate for divergence.
3. **Hilbert-space annihilator argument.** Reduce density to showing every distributional graph datum
   orthogonal to the Schwartz graph core is zero. Elegant, but it moves the work into a PDE/duality
   uniqueness theorem and is therefore ranked below direct regularization.

### 3. Kernel axiom audit

New file: `formal/cace_formal/CACEFormal/V330AxiomAudit.lean`

The v3.30 workflow runs `#print axioms` on every new formal endpoint. Promotion fails if output
contains `sorryAx` or any non-whitelisted axiom. The allowed list is intentionally restricted to the
standard foundational axioms currently expected from Mathlib:

- `propext`
- `Classical.choice`
- `Quot.sound`

The workflow also rejects `sorry`, `admit`, and the marker `OPEN OBLIGATION` in v3.30 formal sources.

### 4. Repository-wide claim-promotion state machine

New file: `cace_studio/core/claim_promotion.py`

Open-problem claims now have fail-closed stages:

- `research-candidate`
- `formal-candidate`
- `reproduced-formal-candidate`
- `externally-reviewed-resolution`

For an open-problem-resolution claim, CACE requires all of the following before permitting resolution
wording:

- no unresolved proof obligations,
- Lean kernel verification,
- axiom audit pass,
- pinned CI pass,
- an exact theorem/statement artifact digest,
- at least one independent reproduction, and
- at least one valid external review attestation bound to an artifact digest.

Numerical, symbolic, and interval evidence can guide discovery but cannot substitute for any formal
promotion gate.

The code explicitly reports that reviewer identity and independence remain an external trust
boundary. CACE does not pretend to prove those social/provenance facts internally.

### 5. Adversarial promotion tests

New file: `tests/test_claim_promotion_v330.py`

Tests cover at least these failure modes:

- numerical/symbolic/interval evidence attempting self-promotion,
- unresolved analytic obligations despite other formal flags,
- a kernel-verified proof being mislabeled as a famous-problem resolution,
- reproduction without review,
- malformed review attestations, and
- the existing v0.76 reliability proof DAG passing through the new global fail-closed guard.

## Verification status

The code is committed on the v3.30 branch, but **the new Lean theorems are not being reported as
verified yet**.

GitHub Actions created the v3.30 jobs but assigned no runner (`runner_id = 0`) and executed zero job
steps. Therefore the observed workflow failures are infrastructure failures, not Lean counterexamples
and not passing evidence either.

The release must remain `IMPLEMENTED_PENDING_RUNNER_EXECUTION` until a pinned workflow actually runs
and emits its success attestation.

## What v3.30 genuinely improves

Before v3.30, a caller had to manually discharge a substantial local-calculus bundle before the
smooth box normal-trace theorem could be applied. The new endpoint is intended to synthesize that
bundle automatically.

Before v3.30, the reverse H(div) density problem was recorded as a broad missing theorem. It is now
factored into a precise regularizer contract; once a Fourier/mollifier implementation satisfies two
analytic obligations, the closure equality and reverse inclusion are automatic.

Before v3.30, open-problem non-promotion was primarily module-specific discipline. It is now a
repository-wide state machine plus CI policy with adversarial tests.

## Nonclaims

v3.30 does **not** yet claim the unconditional reverse H(div) graph inclusion. The regularizer itself
still has to be constructed and proved convergent.

v3.30 does **not** claim the new Lean endpoints have passed the kernel until a real runner executes
the pinned workflow.

v3.30 does **not** make external review obsolete. It makes the boundary explicit, auditable, and
mandatory for public resolution wording about open problems.

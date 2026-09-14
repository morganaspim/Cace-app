# CACE v3.30 Proof Strengthening

Status: **IMPLEMENTED / PENDING PINNED RUNNER EXECUTION**

Base snapshot: `50cfdd10a6653c863d595502797b8f1a87c42333` (v3.29 pre-merge recovery snapshot)

Development branch: `roadmap/v3.30-proof-strengthening`

## Purpose

v3.30 addresses two distinct weaknesses:

1. CACE should automatically close more routine-but-heavy analytic proof obligations and expose the
   genuinely hard analytic core as a small number of explicit contracts.
2. CACE must never turn its own numerical, symbolic, interval, or formal output into a public claim
   that a famous open problem is resolved without independent reproduction and external review.

These are deliberately separate. Better theorem automation is an internal mathematical capability;
external scrutiny remains an independent trust boundary.

## Implemented strengthening

### 1. Automatic smooth product calculus for the box Green bridge

`formal/cace_formal/CACEFormal/SmoothBoxGreenAuto.lean` removes the v3.29 caller burden of supplying
a Frechet derivative family for the product field, a countable exceptional set, continuity,
integrability, and the pointwise product/divergence identity. The endpoint

`CACEFormal.Continuum.boxGraphNormalTrace_smooth_eq_classical_auto`

needs only the box order hypothesis and smooth Schwartz fields.

### 2. Generic regularization-to-closure automation

`formal/cace_formal/CACEFormal/RegularizationClosure.lean` packages recurring topology used in hard
analysis proofs. It proves reusable forms of:

- closed target + core inclusion + convergent core-valued regularizer => closure equality;
- continuous defect kernel + core inclusion + convergent core-valued regularizer => closure equality;
- ambient regularizer => density in the whole space.

The kernel-specialized form is particularly useful for PDE graph spaces, where weak derivative and
divergence relations are naturally kernels of continuous defect maps.

### 3. H(div) graph-density criteria in complex and real coordinates

`GraphRegularizationCriterion.lean` and `RealGraphRegularizationCriterion.lean` reduce the missing
reverse H(div) inclusion to two concrete analytic obligations for a regularizer:

1. it lands in the Schwartz H(div) graph core; and
2. it converges to the original datum in the ambient L2 graph topology.

Once those are supplied, closure equality is automatic. The criterion is available both in the
complex distributional graph model and in the real graph coordinates used by the earlier continuum
track.

### 4. Closed distributional H1 graph relation

`H1DomainBridge.lean` adds the scalar analogue of the H(div) graph relation. Complex L2 graph data
`(u, g)` belong to the relation exactly when `weakPartial_i(u) = g_i` as tempered distributions in
every coordinate. The relation is a continuous-defect kernel, hence closed.

CACE proves the exact membership characterization, Schwartz-core inclusion, smooth-closure
inclusion, and a regularizer-to-equality theorem. This is intentionally not mislabeled as the full
Bessel-potential H1 equivalence; the converse identification with Mathlib `InH1` remains separate.

### 5. Exact L2 representatives for distributional predicates

`DistributionalGraphRepresentatives.lean` uses Mathlib's order-zero Sobolev characterization to
choose an actual L2 representative of any `InL2` tempered distribution and prove that it maps back
to the original distribution.

Consequently:

- every Bessel-potential `InH1` distribution has L2 graph coordinates satisfying the new
  distributional H1 relation; and
- `InHDiv q` is equivalent to the existence of L2 graph data in the closed distributional H(div)
  relation whose field distribution is exactly `q`.

The endpoint

`CACEFormal.Continuum.inHDiv_iff_exists_distributionalGraphRepresentative`

is an exact representation theorem. It is distinct from the harder Schwartz-core density theorem.

### 5a. Bessel/Riesz reduction of the H1 converse

`H1BesselRieszReduction.lean` now discharges the low-frequency Sobolev lift, each normalized
weak-derivative correction, bounded coordinate multiplier preservation, and finite-sum closure.
The full converse is reduced to the exact identity

`u = besselPotential (-2) u + h1RieszCorrection u`.

The coefficient convention has been checked against pinned Mathlib's theorem
`besselPotential_neg_one_lineDerivOp_eq`: its `2 * π * I` factor is canceled by the correction's
inverse factor. The remaining coordinate-symbol sum is the Euclidean identity
`Σ_i ξ_i² / (1 + ‖ξ‖²) + 1 / (1 + ‖ξ‖²) = 1`.

The v3.30 workflow now treats this module as first-class proof surface: changes trigger CI, unfinished
tokens are rejected, it is compiled directly, and all eight current endpoints are included in the
kernel axiom audit. This source is still pending actual runner execution.

### 6. Kernel axiom audit

`V330AxiomAudit.lean` runs `#print axioms` on the new proof-strengthening endpoints. The workflow
rejects `sorry`, `admit`, `OPEN OBLIGATION`, `sorryAx`, and axioms outside the small foundational
whitelist currently expected from Mathlib:

- `propext`
- `Classical.choice`
- `Quot.sound`

### 7. Artifact-bound claim-promotion state machine

`cace_studio/core/claim_promotion.py` now treats famous/open-problem promotion as an artifact-bound
process rather than a collection of booleans. Stages remain:

- `research-candidate`
- `formal-candidate`
- `reproduced-formal-candidate`
- `externally-reviewed-resolution`

Resolution wording requires all of the following:

- no unresolved proof obligations;
- Lean kernel verification;
- axiom audit pass;
- pinned CI pass;
- a valid SHA-256 digest of the exact theorem/statement artifact;
- an independent reproduction attestation bound to that exact digest; and
- an external review attestation bound to that same digest.

A legacy reproduction count is explicitly insufficient. A reproduction or review of a different
artifact is explicitly insufficient. Numerical, symbolic, and interval evidence cannot substitute
for the formal gates.

CACE still does not claim to prove the real-world identity or independence of a reproducer/reviewer;
those remain external trust boundaries.

### 8. Framework-level enforcement, not module-local discipline

`cace_studio/core/executor.py` now attaches an authoritative claim-decision sidecar to theorem-
discovery and reliability runs. Module output is not trusted to self-assert public resolution.

For open-problem research categories, truthy reserved self-promotion fields such as
`public_resolution_claim_allowed`, `open_problem_resolved`, or `reliability_promotable` are rejected
by the executor when the authoritative decision does not allow them. This turns a misleading module
output into a run error instead of allowing contradictory evidence to survive downstream.

`cace_studio/core/report.py` emits the authoritative claim decisions and hashes them into the graph
certificate, including the number of claim-decision nodes and number of public-resolution claims
actually allowed.

### 9. Adversarial promotion tests

`tests/test_claim_promotion_v330.py` covers:

- numerical/symbolic/interval self-promotion;
- unresolved proof obligations;
- malformed exact-statement digests;
- formal proofs without artifact-bound reproduction;
- legacy count-only reproduction;
- reproduction of a different artifact;
- missing or malformed review;
- review of a different artifact;
- matching same-artifact reproduction + review;
- the existing v0.76 reliability proof DAG;
- executor-level claim sidecars; and
- executor rejection of reserved public self-promotion fields.

## Remaining hard analysis, ranked

### Rank 1 — construct whole-space graph regularizers

The highest-value unresolved theorem is sharply specified for H(div) and H1:

- define `R_k` on the closed distributional graph relation;
- prove `R_k x` belongs to the Schwartz graph core; and
- prove `R_k x -> x` in the L2 graph topology.

Preferred route: **Fourier cutoff / multiplier regularization**, because the existing continuum model
already uses tempered distributions and Fourier/Sobolev machinery. A serious alternative is
mollification followed by Schwartz cutoff, requiring explicit derivative/divergence cutoff-
commutator estimates.

### Rank 2 — identify the H1 graph relation with Bessel-potential InH1

The forward direction is now implemented. The missing converse is the analytic characterization that
an L2 distribution whose weak first derivatives are all L2 belongs to H1.

### Rank 3 — push weak Green and Prager-Synge through the completed bridges

After unconditional regularizers and the H1 converse, replace closure-defined stand-ins with the
identified distributional spaces throughout weak Green, zero-boundary orthogonality, and continuum
Prager-Synge.

## Verification status

The source changes are committed, but the new Lean theorems and Python policy tests are **not
reported as verified yet**.

An explicit retry of the prior exact head and a fresh post-audit push were both attempted. The
fresh v3.30 run is `34866491780`, with job `104051518562`, at commit
`6c9ecf19cb10a99bed6e2a2833777517b4ab7af4`. GitHub again assigned no runner
(`runner_id = 0`) and executed zero steps. Therefore the observed workflow failure remains an
infrastructure or billing-allocation failure: it is neither a Lean/Python failure nor passing evidence.

The release remains `IMPLEMENTED_PENDING_RUNNER_EXECUTION` until a pinned workflow actually executes
and emits its success attestation.

## What v3.30 genuinely improves

Before v3.30, the smooth box trace theorem exposed low-level local calculus obligations to callers.
Those are now intended to be synthesized automatically.

Before v3.30, reverse H(div) density was a broad missing theorem. It is now reduced to a two-condition
regularizer contract in both complex and real graph coordinates.

Before v3.30, there was no parallel closed distributional H1 graph relation. There is now a
continuous-defect kernel, smooth-core inclusion, regularization equality criterion, and forward
bridge from Bessel H1.

Before v3.30, the distributional H(div) predicate and L2 graph relation were primarily one-way. There
is now an exact existence equivalence at the graph-representation level.

Before v3.30, open-problem non-promotion was primarily module-specific discipline. It is now enforced
at the executor/report boundary, bound to an exact artifact digest, and covered by adversarial tests.

## Nonclaims

v3.30 does **not** yet claim unconditional Schwartz graph density for arbitrary H(div) or H1 graph
data. The regularizers still have to be constructed and proved convergent.

v3.30 does **not** yet claim the converse equivalence from the new distributional H1 graph relation
to Bessel-potential `InH1`.

v3.30 does **not** claim the new Lean endpoints or Python policy tests have passed until a real runner
executes the pinned workflow.

v3.30 does **not** make external review obsolete. It makes the boundary explicit, artifact-bound,
auditable, and mandatory for public resolution wording about famous open problems.

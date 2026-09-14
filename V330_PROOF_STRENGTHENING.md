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

New file: `formal/cace_formal/CACEFormal/SmoothBoxGreenAuto.lean`

The v3.29 endpoint `boxGraphNormalTrace_smooth_eq_classical` required the caller to supply a Frechet
derivative family for the product field, a countable exceptional set, continuity, integrability, and
the pointwise product/divergence identity.

v3.30 constructs those obligations directly from the actual Schwartz core. The endpoint

`CACEFormal.Continuum.boxGraphNormalTrace_smooth_eq_classical_auto`

needs only the box order hypothesis and smooth Schwartz fields.

### 2. Generic regularization-to-closure automation

New file: `formal/cace_formal/CACEFormal/RegularizationClosure.lean`

CACE now has reusable theorems of the form

- closed target + core inclusion + convergent core-valued regularizer => closure equality;
- continuous defect kernel + core inclusion + convergent core-valued regularizer => closure equality;
- ambient regularizer => density in the whole space.

The kernel-specialized form is particularly important for PDE graph spaces because closed derivative
or divergence relations are naturally represented as kernels of continuous defect maps. It removes
repeated closedness and closure bookkeeping from future analysis proofs.

### 3. H(div) graph-density criteria in complex and real coordinates

Files:

- `formal/cace_formal/CACEFormal/GraphRegularizationCriterion.lean`
- `formal/cace_formal/CACEFormal/RealGraphRegularizationCriterion.lean`

v3.29 had already proved that the Schwartz H(div) graph closure lies in the closed distributional
H(div) relation. v3.30 now proves that any graph regularizer satisfying only

1. core preservation, and
2. graph-norm convergence

forces equality between the smooth graph closure and the distributional relation. The same criterion
is available both in the complex distributional coordinates and in the real graph coordinates used
by the earlier continuum track.

The remaining H(div) difficulty is therefore not a vague density theorem. It is the concrete
construction of a regularizer satisfying those two obligations.

### 4. Closed distributional H1 graph relation

New file: `formal/cace_formal/CACEFormal/H1DomainBridge.lean`

v3.30 adds the scalar analogue that was missing from the H(div) track. Complex L2 graph data
`(u, g)` are placed in the distributional H1 graph relation exactly when

`weakPartial_i(u) = g_i`

as tempered distributions for every coordinate. This relation is the kernel of a continuous defect
map and is therefore closed.

CACE proves:

- exact membership characterization;
- the Schwartz H1 graph core satisfies the distributional derivative equations;
- the entire smooth graph closure lies in the closed relation; and
- any convergent core-valued regularizer upgrades the one-way inclusion to equality.

This is intentionally not mislabeled as the full Bessel-potential H1 equivalence. The converse
identification with Mathlib's `InH1` remains a separately named analytic obligation.

### 5. Exact L2 representatives for distributional predicates

New file: `formal/cace_formal/CACEFormal/DistributionalGraphRepresentatives.lean`

Using Mathlib's order-zero Sobolev characterization, CACE now chooses an actual L2 representative of
any `InL2` tempered distribution and proves it maps back to the original distribution.

This gives two stronger bridge results:

- every Bessel-potential `InH1` distribution has L2 graph coordinates satisfying the new
  distributional H1 graph relation;
- `InHDiv q` is equivalent to the existence of an L2 graph datum in the closed distributional
  H(div) relation whose field distribution is exactly `q`.

The theorem

`CACEFormal.Continuum.inHDiv_iff_exists_distributionalGraphRepresentative`

is a representation-level equivalence. It is distinct from, and does not pretend to solve, the
harder smooth-core density theorem.

### 6. Kernel axiom audit

File: `formal/cace_formal/CACEFormal/V330AxiomAudit.lean`

The v3.30 workflow runs `#print axioms` on the new endpoints. Promotion fails if output contains
`sorryAx` or any non-whitelisted axiom. The whitelist is restricted to the standard foundational
axioms currently expected from Mathlib:

- `propext`
- `Classical.choice`
- `Quot.sound`

The workflow also rejects `sorry`, `admit`, and the marker `OPEN OBLIGATION` in v3.30 formal sources.

### 7. Repository-wide claim-promotion state machine

New file: `cace_studio/core/claim_promotion.py`

Open-problem claims have fail-closed stages:

- `research-candidate`
- `formal-candidate`
- `reproduced-formal-candidate`
- `externally-reviewed-resolution`

For open-problem resolution wording, CACE requires all of:

- no unresolved proof obligations;
- Lean kernel verification;
- axiom audit pass;
- pinned CI pass;
- an exact theorem/statement artifact digest;
- at least one independent reproduction; and
- at least one valid external review attestation bound to an artifact digest.

Numerical, symbolic, and interval evidence can guide discovery but cannot substitute for the formal
promotion gates.

### 8. Adversarial promotion tests

File: `tests/test_claim_promotion_v330.py`

Tests cover numerical/symbolic/interval self-promotion, unresolved obligations, formal proofs without
reproduction or review, malformed review attestations, and the existing v0.76 reliability proof DAG
passing through the global fail-closed policy.

## Remaining hard analysis, ranked

### Rank 1 — construct whole-space graph regularizers

The highest-value unresolved theorem is now sharply specified for both H(div) and H1:

- define `R_k` on the closed distributional graph relation;
- prove `R_k x` belongs to the Schwartz graph core; and
- prove `R_k x -> x` in the L2 graph topology.

Preferred route: Fourier cutoff / multiplier regularization, because CACE already models the
whole-space Sobolev theory through tempered distributions and Fourier machinery.

A serious alternative is mollification followed by Schwartz cutoff. That route needs explicit
cutoff-commutator estimates for divergence/gradient.

### Rank 2 — identify the H1 graph relation with Bessel-potential InH1

The forward direction is now implemented: every `InH1` distribution has a graph representative.
The remaining converse is the standard analytic characterization that an L2 distribution with all
weak first derivatives in L2 belongs to H1. Formalizing this would make the H1 bridge symmetric in
the same way the H(div) representation theorem now is.

### Rank 3 — push weak Green and Prager-Synge through the completed bridges

Once the unconditional regularizers and H1 converse are available, the next leverage point is to
replace closure-defined stand-ins with the identified distributional spaces throughout weak Green,
zero-boundary orthogonality, and continuum Prager-Synge.

## Verification status

The source changes are committed, but the new Lean theorems are **not reported as verified yet**.

The latest observed v3.30 run, `34855119850`, created job `104012566771`, but GitHub assigned no
runner (`runner_id = 0`) and executed zero steps. The observed workflow failure is therefore an
infrastructure failure, not a Lean counterexample and not passing evidence.

The release remains `IMPLEMENTED_PENDING_RUNNER_EXECUTION` until a pinned workflow actually runs and
emits its success attestation.

## What v3.30 genuinely improves

Before v3.30, the smooth box trace theorem exposed low-level local calculus obligations to callers.
Those are now intended to be synthesized automatically.

Before v3.30, the reverse H(div) density theorem was a broad missing statement. It is now reduced to
a two-condition regularizer contract, in both complex and real graph coordinates.

Before v3.30, there was no parallel closed distributional H1 graph relation. There is now a
continuous-defect kernel, smooth-core inclusion, regularization equality criterion, and a forward
bridge from Bessel H1.

Before v3.30, the distributional H(div) predicate and the L2 graph relation were connected mainly in
one direction. There is now an exact existence equivalence at the graph-representation level.

Before v3.30, open-problem non-promotion was primarily module-specific discipline. It is now a
repository-wide state machine plus CI policy with adversarial tests.

## Nonclaims

v3.30 does **not** yet claim unconditional Schwartz graph density for arbitrary H(div) or H1 graph
data. The regularizers still have to be constructed and proved convergent.

v3.30 does **not** yet claim the converse equivalence from the new distributional H1 graph relation
to Bessel-potential `InH1`.

v3.30 does **not** claim the new Lean endpoints have passed the kernel until a real runner executes
the pinned workflow.

v3.30 does **not** make external review obsolete. It makes the boundary explicit, auditable, and
mandatory for public resolution wording about famous open problems.

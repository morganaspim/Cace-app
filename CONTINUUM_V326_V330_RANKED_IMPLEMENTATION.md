# CACE continuum roadmap: ranked 3-point implementation matrix

This file tracks the continuum chain

`Sobolev core → graph spaces → smooth box Green → bounded normal-trace functional → H¹/H(div) graph-density → weak Green → zero-boundary orthogonality → continuum Prager–Synge`.

The ranking is by mathematical leverage: rank 1 is the theorem/definition that most directly closes the stage, rank 2 strengthens reuse or uniqueness, and rank 3 adds approximation/error-estimator consequences.  A stage is not release-certified until its exact branch head passes the pinned Lean CI gate.

## 1. Sobolev core

1. **Actual Mathlib Sobolev predicate bridge — IMPLEMENTED.** `Sobolev2Space.toDistr_memSobolev` and `exists_sobolev2_of_memSobolev` connect the pinned Bessel-coordinate model to `TemperedDistribution.MemSobolev s 2`.
2. **Bundled representation equivalence — IMPLEMENTED.** `sobolev2EquivMemSobolev` packages the Bessel-coordinate model as an equivalence with the subtype of actual `MemSobolev s 2` tempered distributions.
3. **Dense smooth core — IMPLEMENTED.** `denseRange_schwartzSobolev2Coordinates` and `denseRange_schwartzH1` use Mathlib's Schwartz density in `L²`.

## 2. Graph spaces

1. **Distributional graph predicates — IMPLEMENTED.** `H1Submodule`, `HDivSubmodule`, `weakPartialLinearMap`, and `distributionalDivergenceLinearMap` provide the distributional whole-space H¹/H(div) layer.
2. **Concrete smooth graph maps and graph closures — IMPLEMENTED.** `smoothH1GraphMap`, `smoothHDivGraphMap`, `H1SmoothGraphCore`, and `HDivSmoothGraphCore` encode `(u,∇u)` and `(q,div q)` graph data.
3. **Closed graph spaces with sequential approximation — IMPLEMENTED.** `H1GraphClosedSpace`, `HDivGraphClosedSpace`, `isClosed_H1GraphClosedSpace`, `isClosed_HDivGraphClosedSpace`, `exists_H1_smooth_sequence_tendsto`, and `exists_HDiv_smooth_sequence_tendsto` make the closure/density mechanism explicit.

## 3. Smooth box Green

1. **Rectangular divergence theorem wrapper — IMPLEMENTED.** `smoothBoxDivergenceGreen` is derived directly from Mathlib's divergence theorem.
2. **Explicit scalar/vector Green identity — IMPLEMENTED.** `smoothGreenVolumeTerm` and `smoothBoxGreen` expose `q·∇v + (div q)v` and identify its integral with the signed box flux once the local product derivative is identified.
3. **Zero-flux cancellation — IMPLEMENTED.** `smoothBoxGreen_eq_zero_of_zero_flux` derives vanishing of the Green volume term from zero classical normal flux.

## 4. Bounded normal-trace functional

1. **Classical face-flux trace on a box — IMPLEMENTED.** `smoothBoxNormalTrace`, `smoothBoxNormalTrace_eq_signedBoxFlux`, and `smoothBoxNormalTrace_eq_integral_divergence` provide the classical smooth trace side.
2. **Bounded functional trace on graph spaces — IMPLEMENTED.** `BoundedGreenPairing.normalTrace`, `graphNormalTrace`, and `graphNormalTrace_bound` provide a continuous functional trace with an operator-norm estimate.
3. **Uniqueness of continuous extension — IMPLEMENTED.** `normalTrace_unique_of_dense_agreement` proves that two bounded traces agreeing on dense H¹/H(div) cores are identical.

**Remaining identification obligation:** the current closed graph-space functional trace is not yet formally identified with `smoothBoxNormalTrace` on a common bounded-box smooth core.  Closing that bounded-domain bridge is the highest-value v3.29 theorem.

## 5. H¹/H(div) graph-density

1. **Completion density — IMPLEMENTED.** `denseRange_H1SmoothGraphCore` and `denseRange_HDivSmoothGraphCore` are constructive density theorems for the completion model.
2. **Closed-subspace density — IMPLEMENTED.** `dense_H1DenseSmoothCore` and `dense_HDivDenseSmoothCore` prove density inside the closed graph spaces used by the weak Green layer.
3. **Sequential approximation — IMPLEMENTED.** `exists_H1_smooth_sequence_tendsto` and `exists_HDiv_smooth_sequence_tendsto` extract convergent smooth-core sequences.

**Remaining identification obligation:** prove equivalence between the bounded-domain graph-closure model and the intended distributional H¹/H(div) predicates on the box, rather than merely maintaining both models side by side.

## 6. Weak Green

1. **Dense-core extension theorem — IMPLEMENTED.** `weakGreen_of_denseSmoothCore` extends smooth Green equality by continuity in both variables.
2. **Graph-space specialization — IMPLEMENTED.** `graphWeakGreen` specializes the theorem to the closed graph spaces.
3. **Uniqueness/rigidity — IMPLEMENTED.** `normalTrace_unique_of_dense_agreement` prevents two different continuous weak traces from agreeing on the same dense smooth core.

**Remaining identification obligation:** instantiate the smooth-core equality with the actual classical box face-flux trace, not only with the graph functional definition.

## 7. Zero-boundary orthogonality

1. **Functional zero-trace condition — IMPLEMENTED.** `HasZeroBoundaryTrace` expresses the boundary condition without requiring a pointwise trace representative.
2. **Linear zero-boundary space — IMPLEMENTED.** `zeroBoundarySubmodule` packages zero-trace test fields as a submodule.
3. **Orthogonality theorem — IMPLEMENTED.** `zeroBoundaryOrthogonality` and `zeroBoundaryOrthogonality_of_mem` annihilate the Prager–Synge cross term through weak Green.

## 8. Continuum Prager–Synge

1. **Weak-Green hypercircle identity — IMPLEMENTED.** `continuumPragerSynge_of_weakGreen` closes the abstract continuum identity from zero-boundary weak Green orthogonality.
2. **Closed graph-space specialization — IMPLEMENTED.** `graphContinuumPragerSynge` specializes the identity to the H¹/H(div) graph-closure model.
3. **Reliability bounds — IMPLEMENTED.** `graphContinuumPragerSynge_primal_bound` and `graphContinuumPragerSynge_flux_bound` show the hypercircle estimator bounds each component error norm.

## Current release blockers

1. Exact-head pinned Lean CI must pass for every new continuum module; source presence alone is not certification.
2. The bounded-domain **classical trace agreement theorem** must identify the continuous graph trace with `smoothBoxNormalTrace` on a shared smooth box core.
3. The bounded-box **graph closure ↔ distributional H¹/H(div)** bridge must be proved if the release is to claim the standard bounded-domain Sobolev spaces rather than a mathematically sound graph-closure model.

Until blockers 2 and 3 are closed, CACE may claim a machine-checked continuum graph-space hypercircle framework, but should not claim a fully identified standard bounded-domain H¹/H(div) trace theory.

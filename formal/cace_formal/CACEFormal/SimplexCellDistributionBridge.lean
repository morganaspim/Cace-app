import Mathlib
import CACEFormal.PDEDomainRealBridge
import CACEFormal.SimplexFacetCurrent

namespace CACEFormal

open Set Finset MeasureTheory
open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# Simplex cell distributions and finite-mesh Sobolev assembly

This module identifies the exact remaining local analytic obligation.

The Euclidean-native P1/RT0 cell coordinates are genuine real L2 functions.
We complexify those coordinates and embed them into tempered distributions.
For each simplex we then state the concrete local Gauss--Green identities using
the facet currents constructed in `SimplexFacetCurrent`.

The main results here are global: once every cell satisfies that local identity
and the oriented facet currents cancel, finite assembly satisfies the actual
distributional H1/H(div) graph equations and therefore yields genuine
`InH1` / `InHDiv` objects.

Thus the remaining proof burden is local simplex Gauss--Green plus geometric
interface cancellation; no global Sobolev membership is left as an assumption.
-/

/-- Canonical tempered distribution represented by a real whole-space L2 function. -/
noncomputable def realL2ScalarDistribution (d : Nat) (u : RealL2 d) :
    ScalarDistribution d :=
  complexL2ToDistribution d (realL2ToComplexL2 d u)

/-- The real-L2-to-distribution construction commutes with finite sums. -/
theorem realL2ScalarDistribution_sum
    {Cell : Type*} [Fintype Cell] {d : Nat}
    (u : Cell → RealL2 d) :
    realL2ScalarDistribution d (∑ K, u K) =
      ∑ K, realL2ScalarDistribution d (u K) := by
  simp [realL2ScalarDistribution, map_sum]

/-- P1 value distribution for one geometric simplex. -/
noncomputable def geometricSimplexP1ValueDistribution
    {d : Nat} (s : GeometricSimplex d) (u : AffineScalar d) :
    ScalarDistribution d :=
  realL2ScalarDistribution d (euclideanSimplexScalarL2 s.points u)

/-- One P1 gradient-coordinate distribution for one geometric simplex. -/
noncomputable def geometricSimplexP1GradientDistribution
    {d : Nat} (s : GeometricSimplex d) (u : AffineScalar d) (i : Fin d) :
    ScalarDistribution d :=
  realL2ScalarDistribution d (euclideanSimplexGradL2 s.points u i)

/-- One RT0 field-coordinate distribution for one geometric simplex. -/
noncomputable def geometricSimplexRT0FieldDistribution
    {d : Nat} (s : GeometricSimplex d) (q : RT0AffineND d) (i : Fin d) :
    ScalarDistribution d :=
  realL2ScalarDistribution d (euclideanSimplexRT0ComponentL2 s.points q i)

/-- RT0 cell-divergence distribution for one geometric simplex. -/
noncomputable def geometricSimplexRT0DivergenceDistribution
    {d : Nat} (s : GeometricSimplex d) (q : RT0AffineND d) :
    ScalarDistribution d :=
  realL2ScalarDistribution d (euclideanSimplexDivL2 s.points q)

/--
The exact local P1 Gauss--Green obligation for a simplex-supported affine field.
The sign matches distributional differentiation of an indicator:
`partial_i (u 1_K) = (partial_i u) 1_K - u n_i dS`.
-/
structure GeometricSimplexP1CellIBP {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (u : AffineScalar d) : Prop where
  weakDerivative : ∀ i : Fin d,
    weakPartial i (geometricSimplexP1ValueDistribution s u) =
      geometricSimplexP1GradientDistribution s u i -
        geometricSimplexP1BoundaryDistribution s u i

/--
The exact local RT0 Gauss--Green obligation:
`div(q 1_K) = (div q) 1_K - (q dot n) dS`.
-/
structure GeometricSimplexRT0CellIBP {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (q : RT0AffineND d) : Prop where
  divergence : distributionalDivergence
      (fun i => geometricSimplexRT0FieldDistribution s q i) =
    geometricSimplexRT0DivergenceDistribution s q -
      geometricSimplexRT0BoundaryDistribution s q

/-- Distributional divergence commutes with finite cell assembly. -/
theorem distributionalDivergence_finset_sum
    {Cell : Type*} [Fintype Cell] {d : Nat}
    (q : Cell → Fin d → ScalarDistribution d) :
    distributionalDivergence (fun i => ∑ K, q K i) =
      ∑ K, distributionalDivergence (q K) := by
  unfold distributionalDivergence
  calc
    (∑ i : Fin d, weakPartial i (∑ K, q K i)) =
        ∑ i : Fin d, ∑ K, weakPartial i (q K i) := by
      apply Finset.sum_congr rfl
      intro i _
      simpa [weakPartial] using
        (lineDerivOp_sum (basisVector i) (fun K => q K i) Finset.univ)
    _ = ∑ K, ∑ i : Fin d, weakPartial i (q K i) := by
      rw [Finset.sum_comm]

/--
Cellwise P1 Gauss--Green plus cancellation of the concrete facet currents gives
the exact global weak-derivative identity.
-/
theorem assembledGeometricSimplexP1_weakDerivative
    {Cell : Type*} [Fintype Cell] {d : Nat} [NeZero d]
    (s : Cell → GeometricSimplex d)
    (u : Cell → AffineScalar d)
    (hCell : ∀ K, GeometricSimplexP1CellIBP (s K) (u K))
    (hBoundary : ∀ i : Fin d,
      (∑ K, geometricSimplexP1BoundaryDistribution (s K) (u K) i) = 0)
    (i : Fin d) :
    weakPartial i
        (∑ K, geometricSimplexP1ValueDistribution (s K) (u K)) =
      ∑ K, geometricSimplexP1GradientDistribution (s K) (u K) i := by
  exact simplex_cellwise_distributional_ibp_sum_of_boundary_cancel
    (fun K => geometricSimplexP1ValueDistribution (s K) (u K))
    (fun K i => geometricSimplexP1GradientDistribution (s K) (u K) i)
    (fun K i => geometricSimplexP1BoundaryDistribution (s K) (u K) i)
    (fun K i => (hCell K).weakDerivative i)
    hBoundary i

/--
Cellwise RT0 Gauss--Green plus cancellation of total normal-flux currents gives
the exact global distributional-divergence identity.
-/
theorem assembledGeometricSimplexRT0_divergence
    {Cell : Type*} [Fintype Cell] {d : Nat} [NeZero d]
    (s : Cell → GeometricSimplex d)
    (q : Cell → RT0AffineND d)
    (hCell : ∀ K, GeometricSimplexRT0CellIBP (s K) (q K))
    (hBoundary :
      (∑ K, geometricSimplexRT0BoundaryDistribution (s K) (q K)) = 0) :
    distributionalDivergence
        (fun i => ∑ K, geometricSimplexRT0FieldDistribution (s K) (q K) i) =
      ∑ K, geometricSimplexRT0DivergenceDistribution (s K) (q K) := by
  rw [distributionalDivergence_finset_sum]
  calc
    (∑ K, distributionalDivergence
      (fun i => geometricSimplexRT0FieldDistribution (s K) (q K) i)) =
        ∑ K,
          (geometricSimplexRT0DivergenceDistribution (s K) (q K) -
            geometricSimplexRT0BoundaryDistribution (s K) (q K)) := by
      apply Finset.sum_congr rfl
      intro K _
      exact (hCell K).divergence
    _ =
        (∑ K, geometricSimplexRT0DivergenceDistribution (s K) (q K)) -
          ∑ K, geometricSimplexRT0BoundaryDistribution (s K) (q K) := by
      rw [Finset.sum_sub_distrib]
    _ = ∑ K, geometricSimplexRT0DivergenceDistribution (s K) (q K) := by
      rw [hBoundary, sub_zero]

/--
The assembled real P1 graph coordinates satisfy the genuine distributional H1
graph equation after local Gauss--Green and boundary-current cancellation.
-/
theorem assembledEuclideanSimplexP1_distributionalGraph
    {Cell : Type*} [Fintype Cell] {d : Nat} [NeZero d]
    (s : Cell → GeometricSimplex d)
    (u : Cell → AffineScalar d)
    (hCell : ∀ K, GeometricSimplexP1CellIBP (s K) (u K))
    (hBoundary : ∀ i : Fin d,
      (∑ K, geometricSimplexP1BoundaryDistribution (s K) (u K) i) = 0) :
    ∀ i : Fin d,
      weakPartial i
        (realL2ScalarDistribution d
          (assembleEuclideanSimplexH1Ambient
            (fun K => (s K).points) u).1) =
        realL2ScalarDistribution d
          ((assembleEuclideanSimplexH1Ambient
            (fun K => (s K).points) u).2 i) := by
  intro i
  change
    weakPartial i
        (realL2ScalarDistribution d
          (∑ K, euclideanSimplexScalarL2 (s K).points (u K))) =
      realL2ScalarDistribution d
        (∑ K, euclideanSimplexGradL2 (s K).points (u K) i)
  rw [realL2ScalarDistribution_sum, realL2ScalarDistribution_sum]
  exact assembledGeometricSimplexP1_weakDerivative s u hCell hBoundary i

/--
The assembled real RT0 graph coordinates satisfy the genuine distributional
H(div) graph equation after local Gauss--Green and flux-current cancellation.
-/
theorem assembledEuclideanSimplexRT0_distributionalGraph
    {Cell : Type*} [Fintype Cell] {d : Nat} [NeZero d]
    (s : Cell → GeometricSimplex d)
    (q : Cell → RT0AffineND d)
    (hCell : ∀ K, GeometricSimplexRT0CellIBP (s K) (q K))
    (hBoundary :
      (∑ K, geometricSimplexRT0BoundaryDistribution (s K) (q K)) = 0) :
    distributionalDivergence
        (fun i =>
          realL2ScalarDistribution d
            ((assembleEuclideanSimplexHDivAmbient
              (fun K => (s K).points) q).1 i)) =
      realL2ScalarDistribution d
        (assembleEuclideanSimplexHDivAmbient
          (fun K => (s K).points) q).2 := by
  have hfield : ∀ i : Fin d,
      realL2ScalarDistribution d
          (∑ K, euclideanSimplexRT0ComponentL2 (s K).points (q K) i) =
        ∑ K, geometricSimplexRT0FieldDistribution (s K) (q K) i := by
    intro i
    simpa [geometricSimplexRT0FieldDistribution] using
      (realL2ScalarDistribution_sum
        (fun K => euclideanSimplexRT0ComponentL2 (s K).points (q K) i))
  change
    distributionalDivergence
        (fun i =>
          realL2ScalarDistribution d
            (∑ K, euclideanSimplexRT0ComponentL2 (s K).points (q K) i)) =
      realL2ScalarDistribution d
        (∑ K, euclideanSimplexDivL2 (s K).points (q K))
  conv_lhs =>
    congr
    funext i
    rw [hfield i]
  rw [realL2ScalarDistribution_sum]
  exact assembledGeometricSimplexRT0_divergence s q hCell hBoundary

/--
Consequently, the finite P1 assembly is an actual Bessel-potential H1
distribution, not merely an ambient graph datum.
-/
theorem assembledEuclideanSimplexP1_inH1
    {Cell : Type*} [Fintype Cell] {d : Nat} [NeZero d]
    (s : Cell → GeometricSimplex d)
    (u : Cell → AffineScalar d)
    (hCell : ∀ K, GeometricSimplexP1CellIBP (s K) (u K))
    (hBoundary : ∀ i : Fin d,
      (∑ K, geometricSimplexP1BoundaryDistribution (s K) (u K) i) = 0) :
    InH1
      (realL2ScalarDistribution d
        (assembleEuclideanSimplexH1Ambient
          (fun K => (s K).points) u).1) := by
  let x :=
    assembleEuclideanSimplexH1Ambient (fun K => (s K).points) u
  have hweak : ∀ i : Fin d,
      weakPartial i
          (complexL2ToDistribution d (realL2ToComplexL2 d x.1)) =
        complexL2ToDistribution d (realL2ToComplexL2 d (x.2 i)) := by
    intro i
    simpa [realL2ScalarDistribution, x] using
      assembledEuclideanSimplexP1_distributionalGraph s u hCell hBoundary i
  have h :=
    inH1_of_piecewise_interface_cancelled_graph
      (realL2ToComplexL2 d x.1)
      (fun i => realL2ToComplexL2 d (x.2 i))
      hweak
  simpa [realL2ScalarDistribution, x] using h

/--
Likewise the finite RT0 assembly is an actual distributional H(div) field.
-/
theorem assembledEuclideanSimplexRT0_inHDiv
    {Cell : Type*} [Fintype Cell] {d : Nat} [NeZero d]
    (s : Cell → GeometricSimplex d)
    (q : Cell → RT0AffineND d)
    (hCell : ∀ K, GeometricSimplexRT0CellIBP (s K) (q K))
    (hBoundary :
      (∑ K, geometricSimplexRT0BoundaryDistribution (s K) (q K)) = 0) :
    InHDiv
      (fun i =>
        realL2ScalarDistribution d
          ((assembleEuclideanSimplexHDivAmbient
            (fun K => (s K).points) q).1 i)) := by
  let x :=
    assembleEuclideanSimplexHDivAmbient (fun K => (s K).points) q
  have hdiv :
      distributionalDivergence
          (fun i =>
            complexL2ToDistribution d (realL2ToComplexL2 d (x.1 i))) =
        complexL2ToDistribution d (realL2ToComplexL2 d x.2) := by
    simpa [realL2ScalarDistribution, x] using
      assembledEuclideanSimplexRT0_distributionalGraph s q hCell hBoundary
  have h :=
    inHDiv_of_piecewise_normal_interface_cancelled_graph
      (fun i => realL2ToComplexL2 d (x.1 i))
      (realL2ToComplexL2 d x.2)
      hdiv
  simpa [realL2ScalarDistribution, x] using h

end

end Continuum

end CACEFormal

import Mathlib
import CACEFormal.SimplexAffineL2
import CACEFormal.GraphDensity

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators

namespace Continuum

noncomputable section

/-!
# Euclidean-native simplex L² assembly

This layer rebuilds the simplex-supported affine P1/RT0 source coordinates
directly on the canonical `EuclideanDomain d` used by the whole-space Sobolev
and graph machinery.

It proves only L² existence and finite assembly of graph *ambient* coordinates.
It deliberately does not claim H¹ or H(div) membership: a single cell indicator
has facet distributions in its weak derivative/divergence, and those terms must
first be cancelled by the later geometric interface-current argument.
-/

/-- Closed simplex support in the canonical Euclidean Sobolev ambient. -/
def euclideanSimplexSet {d m : Nat}
    (vertex : Fin m → EuclideanDomain d) : Set (EuclideanDomain d) :=
  convexHull ℝ (Set.range vertex)

theorem euclideanSimplexSet_compact {d m : Nat}
    (vertex : Fin m → EuclideanDomain d) :
    IsCompact (euclideanSimplexSet vertex) := by
  exact (Set.finite_range vertex).isCompact_convexHull ℝ

theorem euclideanSimplexSet_measurable {d m : Nat}
    (vertex : Fin m → EuclideanDomain d) :
    MeasurableSet (euclideanSimplexSet vertex) :=
  (euclideanSimplexSet_compact vertex).isClosed.measurableSet

theorem euclideanSimplexSet_volume_lt_top {d m : Nat}
    (vertex : Fin m → EuclideanDomain d) :
    volume (euclideanSimplexSet vertex) < ⊤ :=
  (euclideanSimplexSet_compact vertex).measure_lt_top

/-- Affine P1 evaluation using the canonical Euclidean coordinate projections. -/
def euclideanAffineScalarEval {d : Nat}
    (u : AffineScalar d) (x : EuclideanDomain d) : ℝ :=
  u.c + ∑ i : Fin d, u.grad i * EuclideanSpace.proj i x

theorem euclideanAffineScalarEval_continuous {d : Nat}
    (u : AffineScalar d) :
    Continuous (euclideanAffineScalarEval u) := by
  unfold euclideanAffineScalarEval
  fun_prop

/-- One RT0 coordinate, evaluated directly on the canonical Euclidean ambient. -/
def euclideanRT0ComponentEval {d : Nat}
    (q : RT0AffineND d) (i : Fin d) (x : EuclideanDomain d) : ℝ :=
  q.c i + q.radial * EuclideanSpace.proj i x

theorem euclideanRT0ComponentEval_continuous {d : Nat}
    (q : RT0AffineND d) (i : Fin d) :
    Continuous (euclideanRT0ComponentEval q i) := by
  unfold euclideanRT0ComponentEval
  fun_prop

/--
A continuous finite-dimensional function restricted to a compact Euclidean
simplex is L².  This is the canonical-ambient analogue of
`continuous_indicator_simplex_memLp_two`.
-/
theorem continuous_indicator_euclideanSimplex_memLp_two
    {d m : Nat} (vertex : Fin m → EuclideanDomain d)
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    [FiniteDimensional ℝ E]
    (f : EuclideanDomain d → E) (hf : Continuous f) :
    MemLp ((euclideanSimplexSet vertex).indicator f) 2 volume := by
  have hmeas : MeasurableSet (euclideanSimplexSet vertex) :=
    euclideanSimplexSet_measurable vertex
  have hcompact : IsCompact (euclideanSimplexSet vertex) :=
    euclideanSimplexSet_compact vertex
  have hcont : ContinuousOn f (euclideanSimplexSet vertex) := hf.continuousOn
  have hbounded : HasCompactSupport ((euclideanSimplexSet vertex).indicator f) := by
    rw [HasCompactSupport]
    refine hcompact.of_isClosed_subset isClosed_closure ?_
    refine closure_minimal ?_ hcompact.isClosed
    intro x hx
    by_contra hxs
    exact hx (Set.indicator_of_notMem hxs f)
  obtain ⟨C, hC⟩ := hcompact.exists_bound_of_continuousOn hcont
  exact hbounded.memLp_of_bound
    (hf.aestronglyMeasurable.indicator hmeas)
    (max C 0)
    (Filter.Eventually.of_forall fun x => by
      by_cases hx : x ∈ euclideanSimplexSet vertex
      · have hCx : ‖f x‖ ≤ max C 0 :=
          (hC x hx).trans (le_max_left C 0)
        simpa [Set.indicator_of_mem hx] using hCx
      · have hC0 : 0 ≤ max C 0 := le_max_right C 0
        simpa [Set.indicator_of_notMem hx] using hC0)

/-- P1 value coordinate on one Euclidean simplex, as a genuine whole-space L² object. -/
noncomputable def euclideanSimplexScalarL2 {d m : Nat}
    (vertex : Fin m → EuclideanDomain d) (u : AffineScalar d) :
    RealL2 d :=
  (continuous_indicator_euclideanSimplex_memLp_two
      vertex (euclideanAffineScalarEval u)
      (euclideanAffineScalarEval_continuous u)).toLp
    ((euclideanSimplexSet vertex).indicator (euclideanAffineScalarEval u))

/-- One constant P1 gradient coordinate on one Euclidean simplex. -/
noncomputable def euclideanSimplexGradL2 {d m : Nat}
    (vertex : Fin m → EuclideanDomain d) (u : AffineScalar d) (i : Fin d) :
    RealL2 d := by
  let f : EuclideanDomain d → ℝ := fun _ => u.grad i
  exact (continuous_indicator_euclideanSimplex_memLp_two
      vertex f continuous_const).toLp
    ((euclideanSimplexSet vertex).indicator f)

/-- One RT0 field coordinate on one Euclidean simplex. -/
noncomputable def euclideanSimplexRT0ComponentL2 {d m : Nat}
    (vertex : Fin m → EuclideanDomain d) (q : RT0AffineND d) (i : Fin d) :
    RealL2 d :=
  (continuous_indicator_euclideanSimplex_memLp_two
      vertex (euclideanRT0ComponentEval q i)
      (euclideanRT0ComponentEval_continuous q i)).toLp
    ((euclideanSimplexSet vertex).indicator (euclideanRT0ComponentEval q i))

/-- RT0 divergence coordinate on one Euclidean simplex. -/
noncomputable def euclideanSimplexDivL2 {d m : Nat}
    (vertex : Fin m → EuclideanDomain d) (q : RT0AffineND d) :
    RealL2 d := by
  let f : EuclideanDomain d → ℝ := fun _ => q.divergence
  exact (continuous_indicator_euclideanSimplex_memLp_two
      vertex f continuous_const).toLp
    ((euclideanSimplexSet vertex).indicator f)

/-- The P1 simplex L² value coordinate agrees a.e. with its defining indicator function. -/
theorem euclideanSimplexScalarL2_coeFn_ae
    {d m : Nat} (vertex : Fin m → EuclideanDomain d) (u : AffineScalar d) :
    (euclideanSimplexScalarL2 vertex u : EuclideanDomain d → ℝ) =ᵐ[volume]
      (euclideanSimplexSet vertex).indicator (euclideanAffineScalarEval u) := by
  simpa [euclideanSimplexScalarL2] using
    (continuous_indicator_euclideanSimplex_memLp_two
      vertex (euclideanAffineScalarEval u)
      (euclideanAffineScalarEval_continuous u)).coeFn_toLp

/-- The P1 simplex gradient L² coordinate agrees a.e. with its defining constant indicator. -/
theorem euclideanSimplexGradL2_coeFn_ae
    {d m : Nat} (vertex : Fin m → EuclideanDomain d)
    (u : AffineScalar d) (i : Fin d) :
    (euclideanSimplexGradL2 vertex u i : EuclideanDomain d → ℝ) =ᵐ[volume]
      (euclideanSimplexSet vertex).indicator (fun _ => u.grad i) := by
  let f : EuclideanDomain d → ℝ := fun _ => u.grad i
  simpa [euclideanSimplexGradL2, f] using
    (continuous_indicator_euclideanSimplex_memLp_two
      vertex f continuous_const).coeFn_toLp

/-- The RT0 simplex component L² coordinate agrees a.e. with its defining indicator function. -/
theorem euclideanSimplexRT0ComponentL2_coeFn_ae
    {d m : Nat} (vertex : Fin m → EuclideanDomain d)
    (q : RT0AffineND d) (i : Fin d) :
    (euclideanSimplexRT0ComponentL2 vertex q i :
      EuclideanDomain d → ℝ) =ᵐ[volume]
      (euclideanSimplexSet vertex).indicator
        (euclideanRT0ComponentEval q i) := by
  simpa [euclideanSimplexRT0ComponentL2] using
    (continuous_indicator_euclideanSimplex_memLp_two
      vertex (euclideanRT0ComponentEval q i)
      (euclideanRT0ComponentEval_continuous q i)).coeFn_toLp

/-- The RT0 simplex divergence L² coordinate agrees a.e. with its defining constant indicator. -/
theorem euclideanSimplexDivL2_coeFn_ae
    {d m : Nat} (vertex : Fin m → EuclideanDomain d)
    (q : RT0AffineND d) :
    (euclideanSimplexDivL2 vertex q : EuclideanDomain d → ℝ) =ᵐ[volume]
      (euclideanSimplexSet vertex).indicator (fun _ => q.divergence) := by
  let f : EuclideanDomain d → ℝ := fun _ => q.divergence
  simpa [euclideanSimplexDivL2, f] using
    (continuous_indicator_euclideanSimplex_memLp_two
      vertex f continuous_const).coeFn_toLp

/--
One cell's P1 source coordinates packaged only as ambient H¹ graph data.
Membership in the closed/distributional H¹ graph is intentionally not asserted.
-/
noncomputable def euclideanSimplexH1Ambient {d m : Nat}
    (vertex : Fin m → EuclideanDomain d) (u : AffineScalar d) :
    H1GraphAmbient d :=
  (euclideanSimplexScalarL2 vertex u,
    fun i => euclideanSimplexGradL2 vertex u i)

/--
One cell's RT0 source coordinates packaged only as ambient H(div) graph data.
Membership is deferred until normal-interface currents are proved to cancel.
-/
noncomputable def euclideanSimplexHDivAmbient {d m : Nat}
    (vertex : Fin m → EuclideanDomain d) (q : RT0AffineND d) :
    HDivGraphAmbient d :=
  (fun i => euclideanSimplexRT0ComponentL2 vertex q i,
    euclideanSimplexDivL2 vertex q)

/-- Finite assembly of cellwise P1 L² coordinates in the canonical graph ambient. -/
noncomputable def assembleEuclideanSimplexH1Ambient
    {Cell : Type*} [Fintype Cell] {d m : Nat}
    (vertex : Cell → Fin m → EuclideanDomain d)
    (u : Cell → AffineScalar d) :
    H1GraphAmbient d :=
  (∑ K, euclideanSimplexScalarL2 (vertex K) (u K),
    fun i => ∑ K, euclideanSimplexGradL2 (vertex K) (u K) i)

/-- Finite assembly of cellwise RT0 L² coordinates in the canonical graph ambient. -/
noncomputable def assembleEuclideanSimplexHDivAmbient
    {Cell : Type*} [Fintype Cell] {d m : Nat}
    (vertex : Cell → Fin m → EuclideanDomain d)
    (q : Cell → RT0AffineND d) :
    HDivGraphAmbient d :=
  (fun i => ∑ K, euclideanSimplexRT0ComponentL2 (vertex K) (q K) i,
    ∑ K, euclideanSimplexDivL2 (vertex K) (q K))

@[simp] theorem assembleEuclideanSimplexH1Ambient_value
    {Cell : Type*} [Fintype Cell] {d m : Nat}
    (vertex : Cell → Fin m → EuclideanDomain d)
    (u : Cell → AffineScalar d) :
    (assembleEuclideanSimplexH1Ambient vertex u).1 =
      ∑ K, euclideanSimplexScalarL2 (vertex K) (u K) := rfl

@[simp] theorem assembleEuclideanSimplexHDivAmbient_divergence
    {Cell : Type*} [Fintype Cell] {d m : Nat}
    (vertex : Cell → Fin m → EuclideanDomain d)
    (q : Cell → RT0AffineND d) :
    (assembleEuclideanSimplexHDivAmbient vertex q).2 =
      ∑ K, euclideanSimplexDivL2 (vertex K) (q K) := rfl

end

end Continuum

end CACEFormal

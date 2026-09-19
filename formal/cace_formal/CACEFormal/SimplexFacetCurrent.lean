import Mathlib
import CACEFormal.SimplexEuclideanL2
import CACEFormal.SimplexBoundaryDistribution
import CACEFormal.SimplexFacetMeasure

namespace CACEFormal

open Set MeasureTheory
open EuclideanGeometry
open scoped BigOperators RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Oriented simplex facet currents

This module turns the geometric facet layer into actual tempered boundary
functionals.  The construction is deliberately separated from the still-harder
simplex Gauss--Green theorem:

* every nondegenerate simplex facet gets a certified outward unit normal;
* the finite codimension-one Hausdorff measure is already available from
  `SimplexFacetMeasure`;
* affine P1 traces times an outward-normal coordinate have temperate growth;
* affine RT0 coordinate traces times an outward-normal coordinate have
  temperate growth;
* therefore these weighted finite facet measures define genuine tempered
  distributions;
* finite sums over facets/coordinates give concrete P1 and RT0 boundary-current
  distributions in the exact `EuclideanDomain d` ambient used by the Sobolev
  graph machinery.

No cellwise integration-by-parts identity is assumed or claimed here.  The next
analytic obligation is to prove that the distributional derivative/divergence
of the simplex-supported L2 representatives equals the cell interior term minus
the boundary current constructed below.
-/

/-- Unit outward normal obtained by normalizing the certified nonzero raw normal. -/
noncomputable def simplexFacetOutwardUnitNormal {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1)) :
    GeometricSimplexPoint d :=
  (‖simplexFacetOutwardNormalRaw s facet‖)⁻¹ •
    simplexFacetOutwardNormalRaw s facet

/-- The normalized facet normal really has Euclidean norm one. -/
theorem norm_simplexFacetOutwardUnitNormal {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1)) :
    ‖simplexFacetOutwardUnitNormal s facet‖ = 1 := by
  simpa [simplexFacetOutwardUnitNormal] using
    (norm_smul_inv_norm (𝕜 := ℝ)
      (simplexFacetOutwardNormalRaw_ne_zero s facet))

/-- Normalization preserves orthogonality to the opposite-facet direction. -/
theorem simplexFacetOutwardUnitNormal_mem_orthogonal
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1)) :
    simplexFacetOutwardUnitNormal s facet ∈
      (affineSpan ℝ (Set.range (s.faceOpposite facet).points)).directionᗮ := by
  exact
    (affineSpan ℝ (Set.range (s.faceOpposite facet).points)).directionᗮ.smul_mem
      (‖simplexFacetOutwardNormalRaw s facet‖)⁻¹
      (simplexFacetOutwardNormalRaw_mem_orthogonal s facet)

/-- One coordinate of the certified outward unit normal. -/
noncomputable def simplexFacetOutwardNormalComponent
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1)) (i : Fin d) : ℝ :=
  EuclideanSpace.proj i (simplexFacetOutwardUnitNormal s facet)

/-- Affine P1 evaluation has temperate growth in the canonical Euclidean ambient. -/
theorem euclideanAffineScalarEval_hasTemperateGrowth
    {d : Nat} (u : AffineScalar d) :
    Function.HasTemperateGrowth (euclideanAffineScalarEval u) := by
  unfold euclideanAffineScalarEval
  fun_prop

/-- One affine RT0 coordinate also has temperate growth. -/
/-- One affine RT0 coordinate also has temperate growth. -/
theorem euclideanRT0ComponentEval_hasTemperateGrowth
    {d : Nat} (q : RT0AffineND d) (i : Fin d) :
    Function.HasTemperateGrowth (euclideanRT0ComponentEval q i) := by
  unfold euclideanRT0ComponentEval
  fun_prop

/-- Real P1 trace density/-- Real P1 trace density `u n_i` on one oriented simplex facet. -/
noncomputable def simplexFacetP1BoundaryDensity
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (u : AffineScalar d) (i : Fin d) :
    EuclideanDomain d → ℝ :=
  fun x =>
    euclideanAffineScalarEval u x *
      simplexFacetOutwardNormalComponent s facet i

theorem simplexFacetP1BoundaryDensity_hasTemperateGrowth
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (u : AffineScalar d) (i : Fin d) :
    Function.HasTemperateGrowth
      (simplexFacetP1BoundaryDensity s facet u i) := by
  unfold simplexFacetP1BoundaryDensity
  fun_prop

/-- Complexification of the P1 facet density/-- Complexification of the P1 facet density for the tempered-distribution codomain. -/
noncomputable def simplexFacetP1BoundaryComplexDensity
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (u : AffineScalar d) (i : Fin d) :
    EuclideanDomain d → ℂ :=
  fun x => Complex.ofReal (simplexFacetP1BoundaryDensity s facet u i x)

theorem simplexFacetP1BoundaryComplexDensity_hasTemperateGrowth
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (u : AffineScalar d) (i : Fin d) :
    Function.HasTemperateGrowth
      (simplexFacetP1BoundaryComplexDensity s facet u i) := by
  unfold simplexFacetP1BoundaryComplexDensity
  fun_prop

/--
Concrete tempered boundary distribution/--
Concrete tempered boundary distribution for one P1 facet and one derivative
coordinate.  Finiteness of the restricted facet Hausdorff measure supplies the
measure's temperate-growth instance.
-/
noncomputable def simplexFacetP1BoundaryDistribution
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (u : AffineScalar d) (i : Fin d) :
    SimplexScalarDistribution d :=
  Function.HasTemperateGrowth.toTemperedDistribution
    (geometricSimplexFacetSurfaceMeasure s facet)
    (simplexFacetP1BoundaryComplexDensity_hasTemperateGrowth s facet u i)

@[simp]
theorem simplexFacetP1BoundaryDistribution_apply
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (u : AffineScalar d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    simplexFacetP1BoundaryDistribution s facet u i φ =
      ∫ x,
        φ x • simplexFacetP1BoundaryComplexDensity s facet u i x
        ∂(geometricSimplexFacetSurfaceMeasure s facet) := by
  simp [simplexFacetP1BoundaryDistribution]

/-- Real RT0 coordinate-flux density `q_i n_i` on one oriented facet. -/
noncomputable def simplexFacetRT0CoordinateBoundaryDensity
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (q : RT0AffineND d) (i : Fin d) :
    EuclideanDomain d → ℝ :=
  fun x =>
    euclideanRT0ComponentEval q i x *
      simplexFacetOutwardNormalComponent s facet i

theorem simplexFacetRT0CoordinateBoundaryDensity_hasTemperateGrowth
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (q : RT0AffineND d) (i : Fin d) :
    Function.HasTemperateGrowth
      (simplexFacetRT0CoordinateBoundaryDensity s facet q i) := by
  unfold simplexFacetRT0CoordinateBoundaryDensity
  fun_prop

noncomputable def simplexFacetRT0CoordinateBoundaryComplexDensitynoncomputable def simplexFacetRT0CoordinateBoundaryComplexDensity
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (q : RT0AffineND d) (i : Fin d) :
    EuclideanDomain d → ℂ :=
  fun x => Complex.ofReal
    (simplexFacetRT0CoordinateBoundaryDensity s facet q i x)

theorem simplexFacetRT0CoordinateBoundaryComplexDensity_hasTemperateGrowth
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (q : RT0AffineND d) (i : Fin d) :
    Function.HasTemperateGrowth
      (simplexFacetRT0CoordinateBoundaryComplexDensity s facet q i) := by
  unfold simplexFacetRT0CoordinateBoundaryComplexDensity
  fun_prop

/-- One coordinate contribution to the RT0 normal-flux boundary current. -/
/-- One coordinate contribution to the RT0 normal-flux boundary current. -/
noncomputable def simplexFacetRT0CoordinateBoundaryDistribution
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (q : RT0AffineND d) (i : Fin d) :
    SimplexScalarDistribution d :=
  Function.HasTemperateGrowth.toTemperedDistribution
    (geometricSimplexFacetSurfaceMeasure s facet)
    (simplexFacetRT0CoordinateBoundaryComplexDensity_hasTemperateGrowth
      s facet q i)

@[simp]
theorem simplexFacetRT0CoordinateBoundaryDistribution_apply
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (facet : Fin (d + 1))
    (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    simplexFacetRT0CoordinateBoundaryDistribution s facet q i φ =
      ∫ x,
        φ x • simplexFacetRT0CoordinateBoundaryComplexDensity s facet q i x
        ∂(geometricSimplexFacetSurfaceMeasure s facet) := by
  simp [simplexFacetRT0CoordinateBoundaryDistribution]

/-- Sum of all oriented facet currents for one P1 weak-derivative coordinate. -/
noncomputable def geometricSimplexP1BoundaryDistribution
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (u : AffineScalar d) (i : Fin d) :
    SimplexScalarDistribution d :=
  ∑ facet : Fin (d + 1),
    simplexFacetP1BoundaryDistribution s facet u i

/--
Full RT0 normal-flux boundary current:
`Σ_facets Σ_i (q_i n_i) dS`.
-/
noncomputable def geometricSimplexRT0BoundaryDistribution
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (q : RT0AffineND d) :
    SimplexScalarDistribution d :=
  ∑ facet : Fin (d + 1),
    ∑ i : Fin d,
      simplexFacetRT0CoordinateBoundaryDistribution s facet q i

end

end Continuum

end CACEFormal

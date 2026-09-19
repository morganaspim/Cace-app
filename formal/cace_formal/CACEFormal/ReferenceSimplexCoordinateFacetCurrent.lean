import Mathlib
import CACEFormal.ReferenceSimplexCoordinateFacetNormal
import CACEFormal.SimplexFacetCurrent

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators MeasureTheory RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Coordinate-facet currents of the reference simplex

The lower endpoint of coordinate fiber `i` is the coordinate facet opposite
vertex `i.succ`.  The previous two layers proved:

* its surface measure is the pushforward of restricted orthogonal-hyperplane
  volume;
* its outward unit normal is exactly `-e_i`.

Consequently the existing CACE facet-current distribution is exactly the
negative lower-endpoint functional produced by one-dimensional integration by
parts.  All nonselected normal-coordinate currents vanish identically.
-/

/-- The admissible orthogonal base domain is measurable. -/
theorem referenceSimplexFiberBaseDomain_measurable
    {d : Nat} [NeZero d] (i : Fin d) :
    MeasurableSet (referenceSimplexFiberBaseDomain i) := by
  rw [← referenceSimplex_coordinateFacet_preimage i]
  exact
    (geometricSimplexFacet_measurable
      (referenceGeometricSimplex d) i.succ).preimage
        measurable_subtype_coe

/--
The selected P1 coordinate-facet current is exactly the negative lower-endpoint
integral over the admissible orthogonal base domain.
-/
theorem referenceSimplex_coordinateFacetP1BoundaryDistribution_apply
    {d : Nat} [NeZero d]
    (u : AffineScalar d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    simplexFacetP1BoundaryDistribution
        (referenceGeometricSimplex d) i.succ u i φ =
      -(∫ y : (referenceSimplexCoordinateLine i)ᗮ,
          euclideanAffineScalarEval u (y : EuclideanDomain d) •
            φ (y : EuclideanDomain d)
          ∂(volume.restrict (referenceSimplexFiberBaseDomain i))) := by
  rw [simplexFacetP1BoundaryDistribution_apply]
  rw [← referenceSimplex_coordinateFacetSurfaceMeasure_eq_map i]
  let incl :
      (referenceSimplexCoordinateLine i)ᗮ → EuclideanDomain d :=
    fun y => (y : EuclideanDomain d)
  have hemb : MeasurableEmbedding incl := by
    exact MeasurableEmbedding.subtype_coe
      ((referenceSimplexCoordinateLine i)ᗮ.isClosed.measurableSet)
  rw [hemb.integral_map]
  rw [← integral_neg]
  apply integral_congr_ae
  filter_upwards with y
  simp only [Function.comp_apply]
  unfold simplexFacetP1BoundaryComplexDensity
    simplexFacetP1BoundaryDensity
  rw [referenceSimplex_coordinateFacetOutwardNormalComponent_same]
  simp [Algebra.smul_def, mul_comm, mul_left_comm, mul_assoc]

/-- Every nonselected P1 normal-coordinate current on a coordinate facet is zero. -/
theorem referenceSimplex_coordinateFacetP1BoundaryDistribution_ne
    {d : Nat} [NeZero d]
    (u : AffineScalar d) (i j : Fin d) (hji : j ≠ i) :
    simplexFacetP1BoundaryDistribution
      (referenceGeometricSimplex d) i.succ u j = 0 := by
  ext φ
  rw [simplexFacetP1BoundaryDistribution_apply]
  apply integral_congr_ae
  filter_upwards with x
  simp [simplexFacetP1BoundaryComplexDensity,
    simplexFacetP1BoundaryDensity,
    referenceSimplex_coordinateFacetOutwardNormalComponent_ne i j hji]

/--
The selected RT0 coordinate current on coordinate facet `i` is exactly the
negative lower-endpoint RT0 integral.
-/
theorem referenceSimplex_coordinateFacetRT0BoundaryDistribution_apply
    {d : Nat} [NeZero d]
    (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    simplexFacetRT0CoordinateBoundaryDistribution
        (referenceGeometricSimplex d) i.succ q i φ =
      -(∫ y : (referenceSimplexCoordinateLine i)ᗮ,
          euclideanRT0ComponentEval q i (y : EuclideanDomain d) •
            φ (y : EuclideanDomain d)
          ∂(volume.restrict (referenceSimplexFiberBaseDomain i))) := by
  rw [simplexFacetRT0CoordinateBoundaryDistribution_apply]
  rw [← referenceSimplex_coordinateFacetSurfaceMeasure_eq_map i]
  let incl :
      (referenceSimplexCoordinateLine i)ᗮ → EuclideanDomain d :=
    fun y => (y : EuclideanDomain d)
  have hemb : MeasurableEmbedding incl := by
    exact MeasurableEmbedding.subtype_coe
      ((referenceSimplexCoordinateLine i)ᗮ.isClosed.measurableSet)
  rw [hemb.integral_map]
  rw [← integral_neg]
  apply integral_congr_ae
  filter_upwards with y
  simp only [Function.comp_apply]
  unfold simplexFacetRT0CoordinateBoundaryComplexDensity
    simplexFacetRT0CoordinateBoundaryDensity
  rw [referenceSimplex_coordinateFacetOutwardNormalComponent_same]
  simp [Algebra.smul_def, mul_comm, mul_left_comm, mul_assoc]

/-- Every nonselected RT0 normal-coordinate current on coordinate facet `i` is zero. -/
theorem referenceSimplex_coordinateFacetRT0BoundaryDistribution_ne
    {d : Nat} [NeZero d]
    (q : RT0AffineND d) (i j : Fin d) (hji : j ≠ i) :
    simplexFacetRT0CoordinateBoundaryDistribution
      (referenceGeometricSimplex d) i.succ q j = 0 := by
  ext φ
  rw [simplexFacetRT0CoordinateBoundaryDistribution_apply]
  apply integral_congr_ae
  filter_upwards with x
  simp [simplexFacetRT0CoordinateBoundaryComplexDensity,
    simplexFacetRT0CoordinateBoundaryDensity,
    referenceSimplex_coordinateFacetOutwardNormalComponent_ne i j hji]

end

end Continuum

end CACEFormal

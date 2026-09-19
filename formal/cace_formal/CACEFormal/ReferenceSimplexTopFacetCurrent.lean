import Mathlib
import CACEFormal.ReferenceSimplexTopFacetMeasure
import CACEFormal.ReferenceSimplexTopFacetFluxFactor
import CACEFormal.SimplexFacetCurrent

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators MeasureTheory RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Top-facet currents of the reference simplex

This module is a four-way proof composition:

* `ReferenceSimplexTopFacetParameterization` supplies the endpoint map;
* `ReferenceSimplexTopFacetMeasure` supplies the surface-Jacobian measure scaling;
* `ReferenceSimplexTopFacetFluxFactor` supplies `J_i n_i = 1`;
* `SimplexFacetCurrent` supplies the existing oriented Hausdorff current.

Together they show that the geometric top-facet current is exactly the upper
endpoint functional produced by fiber integration by parts.
-/

/-- The top endpoint map is a measurable embedding. -/
theorem referenceSimplexTopEndpoint_measurableEmbedding
    {d : Nat} [NeZero d] (i : Fin d) :
    MeasurableEmbedding (referenceSimplexTopEndpoint i) :=
  (referenceSimplexTopEndpoint_continuous i).measurableEmbedding
    (referenceSimplexTopEndpoint_injective i)

/--
The selected P1 top-facet current is exactly the upper-endpoint integral over
the admissible orthogonal base domain.
-/
theorem referenceSimplex_topFacetP1BoundaryDistribution_apply
    {d : Nat} [NeZero d]
    (u : AffineScalar d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    simplexFacetP1BoundaryDistribution
        (referenceGeometricSimplex d) 0 u i φ =
      ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        euclideanAffineScalarEval u
            (referenceSimplexTopEndpoint i y) •
          φ (referenceSimplexTopEndpoint i y)
        ∂(volume.restrict (referenceSimplexFiberBaseDomain i)) := by
  rw [simplexFacetP1BoundaryDistribution_apply]
  rw [← referenceSimplex_topFacetSurfaceMeasure_eq_scaled_map i]
  rw [integral_smul_measure]
  let J := (referenceSimplexTopLinearMap i).normDet
  have hJnonneg : 0 ≤ J :=
    (referenceSimplexTopLinearMap_normDet_pos i).le
  have hJreal :
      (ENNReal.ofReal J).toReal = J := by
    simp [J, hJnonneg]
  rw [hJreal]
  have hemb :=
    referenceSimplexTopEndpoint_measurableEmbedding i
  rw [hemb.integral_map]
  rw [← integral_smul]
  apply integral_congr_ae
  filter_upwards with y
  unfold simplexFacetP1BoundaryComplexDensity
    simplexFacetP1BoundaryDensity
  have hflux :=
    referenceSimplex_topFacetFluxFactor_eq_one i
  simp only [Function.comp_apply]
  simp [Algebra.smul_def, J] at hflux ⊢
  ring_nf at hflux ⊢
  rw [hflux]
  ring

/--
The selected RT0 coordinate top-facet current is exactly its upper-endpoint
integral.
-/
theorem referenceSimplex_topFacetRT0BoundaryDistribution_apply
    {d : Nat} [NeZero d]
    (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    simplexFacetRT0CoordinateBoundaryDistribution
        (referenceGeometricSimplex d) 0 q i φ =
      ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        euclideanRT0ComponentEval q i
            (referenceSimplexTopEndpoint i y) •
          φ (referenceSimplexTopEndpoint i y)
        ∂(volume.restrict (referenceSimplexFiberBaseDomain i)) := by
  rw [simplexFacetRT0CoordinateBoundaryDistribution_apply]
  rw [← referenceSimplex_topFacetSurfaceMeasure_eq_scaled_map i]
  rw [integral_smul_measure]
  let J := (referenceSimplexTopLinearMap i).normDet
  have hJnonneg : 0 ≤ J :=
    (referenceSimplexTopLinearMap_normDet_pos i).le
  have hJreal :
      (ENNReal.ofReal J).toReal = J := by
    simp [J, hJnonneg]
  rw [hJreal]
  have hemb :=
    referenceSimplexTopEndpoint_measurableEmbedding i
  rw [hemb.integral_map]
  rw [← integral_smul]
  apply integral_congr_ae
  filter_upwards with y
  unfold simplexFacetRT0CoordinateBoundaryComplexDensity
    simplexFacetRT0CoordinateBoundaryDensity
  have hflux :=
    referenceSimplex_topFacetFluxFactor_eq_one i
  simp only [Function.comp_apply]
  simp [Algebra.smul_def, J] at hflux ⊢
  ring_nf at hflux ⊢
  rw [hflux]
  ring

end

end Continuum

end CACEFormal

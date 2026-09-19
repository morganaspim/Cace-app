import Mathlib
import CACEFormal.ReferenceSimplexTopFacetMeasure
import CACEFormal.ReferenceSimplexTopFacetFluxFactor
import CACEFormal.SimplexFacetCurrent

namespace CACEFormal

open Set MeasureTheory
open EuclideanGeometry
open scoped BigOperators MeasureTheory RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Top-facet currents of the reference simplex

The top-facet surface measure is the scaled pushforward of orthogonal-base
volume by the upper-endpoint map:

  dS = J_i • (T_i)_*(dy),

where `J_i = normDet(L_i)`.

The matching outward-normal coordinate satisfies

  J_i * n_i = 1.

Therefore the two geometric factors cancel exactly inside the CACE facet
current.  The existing Hausdorff facet-current distribution becomes precisely
the positive upper-endpoint term produced by the one-dimensional
integration-by-parts theorem.
-/

/-- The top endpoint map is a measurable embedding. -/
theorem referenceSimplexTopEndpoint_measurableEmbedding
    {d : Nat} [NeZero d] (i : Fin d) :
    MeasurableEmbedding (referenceSimplexTopEndpoint i) :=
  (referenceSimplexTopEndpoint_continuous i).measurableEmbedding
    (referenceSimplexTopEndpoint_injective i)

/--
For P1, the existing CACE top-facet current equals the positive upper-endpoint
integral over the admissible orthogonal base domain.
-/
theorem referenceSimplex_topFacetP1BoundaryDistribution_apply
    {d : Nat} [NeZero d]
    (u : AffineScalar d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    simplexFacetP1BoundaryDistribution
        (referenceGeometricSimplex d) 0 u i φ =
      ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        euclideanAffineScalarEval u (referenceSimplexTopEndpoint i y) •
          φ (referenceSimplexTopEndpoint i y)
        ∂(volume.restrict (referenceSimplexFiberBaseDomain i)) := by
  rw [simplexFacetP1BoundaryDistribution_apply]
  rw [← referenceSimplex_topFacetSurfaceMeasure_eq_scaled_map i]
  rw [MeasureTheory.integral_smul_measure]
  let J := (referenceSimplexTopLinearMap i).normDet
  have hJpos : 0 < J := by
    simpa [J] using referenceSimplexTopLinearMap_normDet_pos i
  have hJnonneg : 0 ≤ J := hJpos.le
  simp only [ENNReal.toReal_ofReal hJnonneg]
  have hT :=
    referenceSimplexTopEndpoint_measurableEmbedding (d := d) i
  rw [hT.integral_map]
  rw [← MeasureTheory.integral_smul J]
  apply integral_congr_ae
  filter_upwards with y
  let n :=
    simplexFacetOutwardNormalComponent
      (referenceGeometricSimplex d) 0 i
  let a :=
    euclideanAffineScalarEval u (referenceSimplexTopEndpoint i y)
  let z := φ (referenceSimplexTopEndpoint i y)
  have hflux : J * n = 1 := by
    simpa [J, n] using referenceSimplex_topFacetFluxFactor_eq_one i
  have hfluxC : (J : ℂ) * (n : ℂ) = 1 := by
    exact_mod_cast hflux
  unfold simplexFacetP1BoundaryComplexDensity
    simplexFacetP1BoundaryDensity
  change
    (J : ℂ) *
        (z * Complex.ofReal (a * n)) =
      Complex.ofReal a * z
  rw [Complex.ofReal_mul]
  calc
    (J : ℂ) * (z * (Complex.ofReal a * Complex.ofReal n)) =
        ((J : ℂ) * (n : ℂ)) * (Complex.ofReal a * z) := by
      ring
    _ = Complex.ofReal a * z := by
      rw [hfluxC, one_mul]

/--
For RT0 coordinate `i`, the existing CACE top-facet current equals the
positive upper-endpoint integral.
-/
theorem referenceSimplex_topFacetRT0BoundaryDistribution_apply
    {d : Nat} [NeZero d]
    (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    simplexFacetRT0CoordinateBoundaryDistribution
        (referenceGeometricSimplex d) 0 q i φ =
      ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        euclideanRT0ComponentEval q i (referenceSimplexTopEndpoint i y) •
          φ (referenceSimplexTopEndpoint i y)
        ∂(volume.restrict (referenceSimplexFiberBaseDomain i)) := by
  rw [simplexFacetRT0CoordinateBoundaryDistribution_apply]
  rw [← referenceSimplex_topFacetSurfaceMeasure_eq_scaled_map i]
  rw [MeasureTheory.integral_smul_measure]
  let J := (referenceSimplexTopLinearMap i).normDet
  have hJpos : 0 < J := by
    simpa [J] using referenceSimplexTopLinearMap_normDet_pos i
  have hJnonneg : 0 ≤ J := hJpos.le
  simp only [ENNReal.toReal_ofReal hJnonneg]
  have hT :=
    referenceSimplexTopEndpoint_measurableEmbedding (d := d) i
  rw [hT.integral_map]
  rw [← MeasureTheory.integral_smul J]
  apply integral_congr_ae
  filter_upwards with y
  let n :=
    simplexFacetOutwardNormalComponent
      (referenceGeometricSimplex d) 0 i
  let a :=
    euclideanRT0ComponentEval q i (referenceSimplexTopEndpoint i y)
  let z := φ (referenceSimplexTopEndpoint i y)
  have hflux : J * n = 1 := by
    simpa [J, n] using referenceSimplex_topFacetFluxFactor_eq_one i
  have hfluxC : (J : ℂ) * (n : ℂ) = 1 := by
    exact_mod_cast hflux
  unfold simplexFacetRT0CoordinateBoundaryComplexDensity
    simplexFacetRT0CoordinateBoundaryDensity
  change
    (J : ℂ) *
        (z * Complex.ofReal (a * n)) =
      Complex.ofReal a * z
  rw [Complex.ofReal_mul]
  calc
    (J : ℂ) * (z * (Complex.ofReal a * Complex.ofReal n)) =
        ((J : ℂ) * (n : ℂ)) * (Complex.ofReal a * z) := by
      ring
    _ = Complex.ofReal a * z := by
      rw [hfluxC, one_mul]

end

end Continuum

end CACEFormal

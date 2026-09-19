import Mathlib
import CACEFormal.ReferenceSimplexGaussGreenEndpoint
import CACEFormal.ReferenceSimplexDivergenceEndpoint
import CACEFormal.ReferenceSimplexCoordinateFacetCurrent
import CACEFormal.ReferenceSimplexTopFacetCurrent

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv MeasureTheory RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Combinatorial closure of reference-simplex facet currents

This module combines three independently proved groups:

1. fiber endpoint Gauss--Green,
2. coordinate-facet current identification,
3. top-facet current identification.

The combined result eliminates the temporary endpoint-boundary representation:
the endpoint functional is exactly the existing CACE sum of oriented Hausdorff
facet currents.
-/

/-- The admissible fiber base domain is compact. -/
theorem referenceSimplexFiberBaseDomain_compact
    {d : Nat} [NeZero d] (i : Fin d) :
    IsCompact (referenceSimplexFiberBaseDomain i) := by
  have hT := referenceSimplexTopEndpoint_isClosedEmbedding (d := d) i
  apply hT.isEmbedding.isCompact_iff.mpr
  rw [referenceSimplexTopEndpoint_image_baseDomain i]
  exact geometricSimplexFacet_compact (referenceGeometricSimplex d) 0

/-- P1 lower-endpoint trace is integrable on the compact fiber base. -/
theorem referenceSimplexP1_lowerEndpoint_integrable
    {d : Nat} [NeZero d]
    (u : AffineScalar d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      (fun y : (referenceSimplexCoordinateLine i)ᗮ =>
        euclideanAffineScalarEval u (y : EuclideanDomain d) •
          φ (y : EuclideanDomain d))
      (volume.restrict (referenceSimplexFiberBaseDomain i)) := by
  have hcont :
      Continuous
        (fun y : (referenceSimplexCoordinateLine i)ᗮ =>
          euclideanAffineScalarEval u (y : EuclideanDomain d) •
            φ (y : EuclideanDomain d)) := by
    fun_prop
  exact hcont.continuousOn.integrableOn_compact
    (referenceSimplexFiberBaseDomain_compact i)

/-- P1 upper-endpoint trace is integrable on the compact fiber base. -/
theorem referenceSimplexP1_upperEndpoint_integrable
    {d : Nat} [NeZero d]
    (u : AffineScalar d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      (fun y : (referenceSimplexCoordinateLine i)ᗮ =>
        euclideanAffineScalarEval u (referenceSimplexTopEndpoint i y) •
          φ (referenceSimplexTopEndpoint i y))
      (volume.restrict (referenceSimplexFiberBaseDomain i)) := by
  have hcont :
      Continuous
        (fun y : (referenceSimplexCoordinateLine i)ᗮ =>
          euclideanAffineScalarEval u (referenceSimplexTopEndpoint i y) •
            φ (referenceSimplexTopEndpoint i y)) := by
    fun_prop
  exact hcont.continuousOn.integrableOn_compact
    (referenceSimplexFiberBaseDomain_compact i)

/-- RT0 lower-endpoint trace is integrable on the compact fiber base. -/
theorem referenceSimplexRT0_lowerEndpoint_integrable
    {d : Nat} [NeZero d]
    (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      (fun y : (referenceSimplexCoordinateLine i)ᗮ =>
        euclideanRT0ComponentEval q i (y : EuclideanDomain d) •
          φ (y : EuclideanDomain d))
      (volume.restrict (referenceSimplexFiberBaseDomain i)) := by
  have hcont :
      Continuous
        (fun y : (referenceSimplexCoordinateLine i)ᗮ =>
          euclideanRT0ComponentEval q i (y : EuclideanDomain d) •
            φ (y : EuclideanDomain d)) := by
    fun_prop
  exact hcont.continuousOn.integrableOn_compact
    (referenceSimplexFiberBaseDomain_compact i)

/-- RT0 upper-endpoint trace is integrable on the compact fiber base. -/
theorem referenceSimplexRT0_upperEndpoint_integrable
    {d : Nat} [NeZero d]
    (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      (fun y : (referenceSimplexCoordinateLine i)ᗮ =>
        euclideanRT0ComponentEval q i (referenceSimplexTopEndpoint i y) •
          φ (referenceSimplexTopEndpoint i y))
      (volume.restrict (referenceSimplexFiberBaseDomain i)) := by
  have hcont :
      Continuous
        (fun y : (referenceSimplexCoordinateLine i)ᗮ =>
          euclideanRT0ComponentEval q i (referenceSimplexTopEndpoint i y) •
            φ (referenceSimplexTopEndpoint i y)) := by
    fun_prop
  exact hcont.continuousOn.integrableOn_compact
    (referenceSimplexFiberBaseDomain_compact i)

/--
For one derivative coordinate, the P1 endpoint boundary equals top current plus
the matching coordinate-facet current.
-/
theorem referenceSimplexP1EndpointBoundary_eq_twoFacetCurrents
    {d : Nat} [NeZero d]
    (u : AffineScalar d) (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    referenceSimplexP1EndpointBoundary u φ i =
      simplexFacetP1BoundaryDistribution
          (referenceGeometricSimplex d) 0 u i φ +
        simplexFacetP1BoundaryDistribution
          (referenceGeometricSimplex d) i.succ u i φ := by
  rw [referenceSimplexP1EndpointBoundary]
  unfold referenceSimplexP1BoundaryBase
  rw [integral_indicator (referenceSimplexFiberBaseDomain_measurable i)]
  have htop := referenceSimplexP1_upperEndpoint_integrable u i φ
  have hlow := referenceSimplexP1_lowerEndpoint_integrable u i φ
  rw [integral_sub htop hlow]
  have hTopCurrent :=
    referenceSimplex_topFacetP1BoundaryDistribution_apply u i φ
  have hCoordCurrent :=
    referenceSimplex_coordinateFacetP1BoundaryDistribution_apply u i φ
  rw [referenceSimplexFiberPoint_zero_eq_base] at *
  change
    (∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        euclideanAffineScalarEval u (referenceSimplexTopEndpoint i y) •
          φ (referenceSimplexTopEndpoint i y)
        ∂(volume.restrict (referenceSimplexFiberBaseDomain i))) -
      (∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        euclideanAffineScalarEval u (y : EuclideanDomain d) •
          φ (y : EuclideanDomain d)
        ∂(volume.restrict (referenceSimplexFiberBaseDomain i))) = _
  rw [← hTopCurrent, ← neg_eq_iff_add_eq_zero.mp
    (sub_eq_zero.mp rfl : (0 : ℂ) = 0)]
  rw [hCoordCurrent]
  abel

/--
For one RT0 coordinate, the endpoint boundary equals top current plus the
matching coordinate-facet current.
-/
theorem referenceSimplexRT0EndpointBoundary_eq_twoFacetCurrents
    {d : Nat} [NeZero d]
    (q : RT0AffineND d) (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    referenceSimplexRT0EndpointBoundary q φ i =
      simplexFacetRT0CoordinateBoundaryDistribution
          (referenceGeometricSimplex d) 0 q i φ +
        simplexFacetRT0CoordinateBoundaryDistribution
          (referenceGeometricSimplex d) i.succ q i φ := by
  rw [referenceSimplexRT0EndpointBoundary]
  unfold referenceSimplexRT0BoundaryBase
  rw [integral_indicator (referenceSimplexFiberBaseDomain_measurable i)]
  have htop := referenceSimplexRT0_upperEndpoint_integrable q i φ
  have hlow := referenceSimplexRT0_lowerEndpoint_integrable q i φ
  rw [integral_sub htop hlow]
  rw [referenceSimplex_topFacetRT0BoundaryDistribution_apply q i φ]
  rw [referenceSimplex_coordinateFacetRT0BoundaryDistribution_apply q i φ]
  simp only [referenceSimplexFiberPoint_zero_eq_base]
  abel

/-- The full P1 facet-current sum equals the endpoint boundary functional. -/
theorem referenceSimplexP1BoundaryDistribution_apply_eq_endpoint
    {d : Nat} [NeZero d]
    (u : AffineScalar d) (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    geometricSimplexP1BoundaryDistribution
        (referenceGeometricSimplex d) u i φ =
      referenceSimplexP1EndpointBoundary u φ i := by
  unfold geometricSimplexP1BoundaryDistribution
  rw [map_sum]
  rw [Fin.sum_univ_succ]
  have hsucc :
      (∑ j : Fin d,
        simplexFacetP1BoundaryDistribution
          (referenceGeometricSimplex d) j.succ u i φ) =
        simplexFacetP1BoundaryDistribution
          (referenceGeometricSimplex d) i.succ u i φ := by
    apply Finset.sum_eq_single i
    · intro j hj hji
      have hz :=
        referenceSimplex_coordinateFacetP1BoundaryDistribution_ne
          u j i (Ne.symm hji)
      simpa using congrArg (fun T : SimplexScalarDistribution d => T φ) hz
    · simp
  rw [hsucc]
  symm
  exact referenceSimplexP1EndpointBoundary_eq_twoFacetCurrents u φ i

/-- On a coordinate facet, the total RT0 coordinate current reduces to its matching coordinate. -/
theorem referenceSimplex_coordinateFacetRT0_sum_apply
    {d : Nat} [NeZero d]
    (q : RT0AffineND d) (φ : 𝓢(EuclideanDomain d, ℂ)) (j : Fin d) :
    (∑ i : Fin d,
      simplexFacetRT0CoordinateBoundaryDistribution
        (referenceGeometricSimplex d) j.succ q i) φ =
      simplexFacetRT0CoordinateBoundaryDistribution
        (referenceGeometricSimplex d) j.succ q j φ := by
  rw [map_sum]
  apply Finset.sum_eq_single j
  · intro i hi hij
    have hz :=
      referenceSimplex_coordinateFacetRT0BoundaryDistribution_ne
        q j i hij
    simpa using congrArg (fun T : SimplexScalarDistribution d => T φ) hz
  · simp

/-- The full RT0 facet-current sum equals the summed endpoint boundary functional. -/
theorem referenceSimplexRT0BoundaryDistribution_apply_eq_endpoint
    {d : Nat} [NeZero d]
    (q : RT0AffineND d) (φ : 𝓢(EuclideanDomain d, ℂ)) :
    geometricSimplexRT0BoundaryDistribution
        (referenceGeometricSimplex d) q φ =
      referenceSimplexRT0TotalEndpointBoundary q φ := by
  unfold geometricSimplexRT0BoundaryDistribution
  rw [map_sum]
  rw [Fin.sum_univ_succ]
  rw [referenceSimplexRT0TotalEndpointBoundary]
  have htop :
      (∑ i : Fin d,
        simplexFacetRT0CoordinateBoundaryDistribution
          (referenceGeometricSimplex d) 0 q i) φ =
        ∑ i : Fin d,
          (∫ y : (referenceSimplexCoordinateLine i)ᗮ,
            euclideanRT0ComponentEval q i (referenceSimplexTopEndpoint i y) •
              φ (referenceSimplexTopEndpoint i y)
            ∂(volume.restrict (referenceSimplexFiberBaseDomain i))) := by
    rw [map_sum]
    apply Finset.sum_congr rfl
    intro i hi
    exact referenceSimplex_topFacetRT0BoundaryDistribution_apply q i φ
  rw [htop]
  have hcoord :
      (∑ j : Fin d,
        (∑ i : Fin d,
          simplexFacetRT0CoordinateBoundaryDistribution
            (referenceGeometricSimplex d) j.succ q i) φ) =
        ∑ j : Fin d,
          simplexFacetRT0CoordinateBoundaryDistribution
            (referenceGeometricSimplex d) j.succ q j φ := by
    apply Finset.sum_congr rfl
    intro j hj
    exact referenceSimplex_coordinateFacetRT0_sum_apply q φ j
  rw [hcoord]
  rw [← Finset.sum_add_distrib]
  apply Finset.sum_congr rfl
  intro i hi
  symm
  exact referenceSimplexRT0EndpointBoundary_eq_twoFacetCurrents q φ i

end

end Continuum

end CACEFormal

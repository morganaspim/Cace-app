import Mathlib
import CACEFormal.ReferenceSimplexGaussGreenEndpoint

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv

namespace Continuum

noncomputable section

/-!
# Summed RT0 divergence theorem on the reference simplex

The coordinatewise endpoint Gauss--Green identities are now summed over every
Euclidean coordinate.  The repeated radial interior contribution collapses to

  d * q.radial = q.divergence,

giving the exact RT0 divergence form before geometric facet-current
normalization.
-/

/-- Sum of all oriented RT0 coordinate endpoint boundary functionals. -/
def referenceSimplexRT0TotalEndpointBoundary
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) : ℂ :=
  ∑ i : Fin d, referenceSimplexRT0EndpointBoundary q φ i

/-- Summing the repeated radial volume term gives the exact RT0 divergence volume term. -/
theorem referenceSimplexRT0_sum_radial_integrals_eq_divergence
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    (∑ i : Fin d,
      ∫ x,
        (euclideanReferenceSimplex d).indicator
          (fun x => q.radial • φ x) x) =
      ∫ x,
        (euclideanReferenceSimplex d).indicator
          (fun x => q.divergence • φ x) x := by
  rw [← MeasureTheory.integral_finsetSum]
  · apply integral_congr_ae
    filter_upwards with x
    by_cases hx : x ∈ euclideanReferenceSimplex d
    · simp [Set.indicator_of_mem hx, RT0AffineND.divergence,
        Nat.cast_smul_eq_nsmul, smul_smul]
    · simp [Set.indicator_of_notMem hx]
  · intro i hi
    exact referenceSimplex_realConst_smul_schwartz_integrable q.radial φ

/--
Full RT0 divergence Gauss--Green identity on the reference simplex with the
boundary still represented by the explicit endpoint functional.
-/
theorem referenceSimplexRT0_divergence_gaussGreen_endpoint
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    -(∑ i : Fin d,
      ∫ x,
        (euclideanReferenceSimplex d).indicator
          (fun x =>
            euclideanRT0ComponentEval q i x •
              (∂_{basisVector i} φ) x) x) =
      (∫ x,
        (euclideanReferenceSimplex d).indicator
          (fun x => q.divergence • φ x) x) -
        referenceSimplexRT0TotalEndpointBoundary q φ := by
  calc
    -(∑ i : Fin d,
        ∫ x,
          (euclideanReferenceSimplex d).indicator
            (fun x =>
              euclideanRT0ComponentEval q i x •
                (∂_{basisVector i} φ) x) x) =
        ∑ i : Fin d,
          -(∫ x,
            (euclideanReferenceSimplex d).indicator
              (fun x =>
                euclideanRT0ComponentEval q i x •
                  (∂_{basisVector i} φ) x) x) := by
      rw [Finset.sum_neg_distrib]
    _ =
        ∑ i : Fin d,
          ((∫ x,
            (euclideanReferenceSimplex d).indicator
              (fun x => q.radial • φ x) x) -
            referenceSimplexRT0EndpointBoundary q φ i) := by
      apply Finset.sum_congr rfl
      intro i hi
      exact referenceSimplexRT0_gaussGreen_endpoint q φ i
    _ =
        (∑ i : Fin d,
          ∫ x,
            (euclideanReferenceSimplex d).indicator
              (fun x => q.radial • φ x) x) -
          ∑ i : Fin d,
            referenceSimplexRT0EndpointBoundary q φ i := by
      rw [Finset.sum_sub_distrib]
    _ =
        (∫ x,
          (euclideanReferenceSimplex d).indicator
            (fun x => q.divergence • φ x) x) -
          referenceSimplexRT0TotalEndpointBoundary q φ := by
      rw [referenceSimplexRT0_sum_radial_integrals_eq_divergence]
      rfl

end

end Continuum

end CACEFormal

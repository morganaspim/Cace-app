import Mathlib
import CACEFormal.ReferenceSimplexEndpointIBP
import CACEFormal.ReferenceSimplexIntegrability

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv

namespace Continuum

noncomputable section

/-!
# Ambient reference-simplex IBP reduced to endpoint fibers

This module combines the exact reference-simplex Fubini formula with the
closed-fiber integration-by-parts identities.

The result deliberately keeps the right-hand side as one integral over the
orthogonal base domain.  This avoids premature splitting into three integrals
and isolates the remaining geometric task: identify the lower and upper
endpoint terms with the oriented facet currents.
-/

/--
P1 ambient derivative integral reduced exactly to fiber interior plus endpoint
terms.
-/
theorem referenceSimplexP1_ambient_endpoint_ibp
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    -(∫ x,
      (euclideanReferenceSimplex d).indicator
        (fun x =>
          complexEuclideanAffineScalarEval u x •
            (∂_{basisVector i} φ) x) x) =
      ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        (referenceSimplexFiberBaseDomain i).indicator
          (fun y =>
            (∫ t in
              Set.Icc 0
                (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
              u.grad i •
                φ (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) t)) +
            euclideanAffineScalarEval u
                (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) 0) •
              φ (referenceSimplexFiberPoint i
                (y : EuclideanDomain d) 0) -
            euclideanAffineScalarEval u
                (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d)
                  (referenceSimplexFiberUpper i
                    (y : EuclideanDomain d))) •
              φ (referenceSimplexFiberPoint i
                (y : EuclideanDomain d)
                (referenceSimplexFiberUpper i
                  (y : EuclideanDomain d)))) y := by
  have hF :=
    integral_referenceSimplex_indicator_eq_fibers
      i
      (fun x =>
        complexEuclideanAffineScalarEval u x •
          (∂_{basisVector i} φ) x)
      (referenceSimplex_complexAffine_fiberCoordinates_integrable
        u (∂_{basisVector i} φ) i)
  rw [hF, ← integral_neg]
  apply integral_congr_ae
  filter_upwards with y
  by_cases hy : y ∈ referenceSimplexFiberBaseDomain i
  · rw [Set.indicator_of_mem hy, Set.indicator_of_mem hy]
    simpa [complexEuclideanAffineScalarEval, Algebra.smul_def] using
      (referenceSimplexP1_fiber_setIntegral_ibp
        u φ i y hy)
  · simp [Set.indicator_of_notMem hy]

/--
The matching RT0 coordinate identity.  Summing this theorem over coordinates
will convert the fiber interior term into `q.divergence`.
-/
theorem referenceSimplexRT0_ambient_endpoint_ibp
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    -(∫ x,
      (euclideanReferenceSimplex d).indicator
        (fun x =>
          complexEuclideanRT0ComponentEval q i x •
            (∂_{basisVector i} φ) x) x) =
      ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        (referenceSimplexFiberBaseDomain i).indicator
          (fun y =>
            (∫ t in
              Set.Icc 0
                (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
              q.radial •
                φ (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) t)) +
            euclideanRT0ComponentEval q i
                (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) 0) •
              φ (referenceSimplexFiberPoint i
                (y : EuclideanDomain d) 0) -
            euclideanRT0ComponentEval q i
                (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d)
                  (referenceSimplexFiberUpper i
                    (y : EuclideanDomain d))) •
              φ (referenceSimplexFiberPoint i
                (y : EuclideanDomain d)
                (referenceSimplexFiberUpper i
                  (y : EuclideanDomain d)))) y := by
  have hF :=
    integral_referenceSimplex_indicator_eq_fibers
      i
      (fun x =>
        complexEuclideanRT0ComponentEval q i x •
          (∂_{basisVector i} φ) x)
      (referenceSimplex_complexRT0_fiberCoordinates_integrable
        q i (∂_{basisVector i} φ))
  rw [hF, ← integral_neg]
  apply integral_congr_ae
  filter_upwards with y
  by_cases hy : y ∈ referenceSimplexFiberBaseDomain i
  · rw [Set.indicator_of_mem hy, Set.indicator_of_mem hy]
    simpa [complexEuclideanRT0ComponentEval, Algebra.smul_def] using
      (referenceSimplexRT0_fiber_setIntegral_ibp
        q φ i y hy)
  · simp [Set.indicator_of_notMem hy]

end

end Continuum

end CACEFormal

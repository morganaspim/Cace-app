import Mathlib
import CACEFormal.ReferenceSimplexFacets
import CACEFormal.ReferenceSimplexFubini
import CACEFormal.ReferenceSimplexFiberCalculus

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv Interval

namespace Continuum

noncomputable section

/-!
# Fiber endpoint integration by parts on the reference simplex

The reference-simplex Fubini theorem produces ordinary set integrals over the
closed scalar fiber interval.  The calculus layer proves integration by parts
for Mathlib's oriented interval integral.

On an admissible fiber the upper endpoint is nonnegative, so these two notions
of integral agree (endpoints are null for Lebesgue measure).  This module
performs that conversion once and records the exact endpoint identities used by
the global Gauss--Green proof.
-/

/-- On a nonnegatively oriented real interval, the closed-set integral equals the interval integral. -/
theorem integral_Icc_eq_intervalIntegral_of_nonneg
    {F : Type*} [NormedAddCommGroup F] [NormedSpace ℝ F]
    (f : ℝ → F) {b : ℝ} (hb : 0 ≤ b) :
    (∫ t in Set.Icc 0 b, f t) = ∫ t in (0 : ℝ)..b, f t := by
  calc
    (∫ t in Set.Icc 0 b, f t) =
        ∫ t in Set.Ioc 0 b, f t :=
      MeasureTheory.integral_Icc_eq_integral_Ioc
    _ = ∫ t in (0 : ℝ)..b, f t :=
      (intervalIntegral.integral_of_le hb).symm

/--
P1 integration by parts on one admissible closed reference-simplex fiber.

The lower endpoint enters with a plus sign after applying the distributional
minus sign, while the slanted upper endpoint enters with a minus sign.
-/
theorem referenceSimplexP1_fiber_setIntegral_ibp
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ)
    (hy : y ∈ referenceSimplexFiberBaseDomain i) :
    -(∫ t in
        Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
        euclideanAffineScalarEval u
            (referenceSimplexFiberPoint i (y : EuclideanDomain d) t) •
          (∂_{basisVector i} φ)
            (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) =
      (∫ t in
        Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
        u.grad i •
          φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) +
      euclideanAffineScalarEval u
          (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) •
        φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) -
      euclideanAffineScalarEval u
          (referenceSimplexFiberPoint i (y : EuclideanDomain d)
            (referenceSimplexFiberUpper i (y : EuclideanDomain d))) •
        φ (referenceSimplexFiberPoint i (y : EuclideanDomain d)
          (referenceSimplexFiberUpper i (y : EuclideanDomain d))) := by
  have hupper :
      0 ≤ referenceSimplexFiberUpper i (y : EuclideanDomain d) :=
    referenceSimplexFiberUpper_nonneg_of_baseDomain i hy
  rw [
    integral_Icc_eq_intervalIntegral_of_nonneg _ hupper,
    integral_Icc_eq_intervalIntegral_of_nonneg _ hupper,
    euclideanAffineScalarEval_fiber_integrationByParts
      u φ i (y : EuclideanDomain d) 0
        (referenceSimplexFiberUpper i (y : EuclideanDomain d))
  ]
  abel

/--
The matching RT0 coordinate identity on one admissible fiber.

Its volume derivative is the common radial coefficient. Summing this theorem
over all coordinates later yields `d * q.radial = q.divergence`.
-/
theorem referenceSimplexRT0_fiber_setIntegral_ibp
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ)
    (hy : y ∈ referenceSimplexFiberBaseDomain i) :
    -(∫ t in
        Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
        euclideanRT0ComponentEval q i
            (referenceSimplexFiberPoint i (y : EuclideanDomain d) t) •
          (∂_{basisVector i} φ)
            (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) =
      (∫ t in
        Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
        q.radial •
          φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) +
      euclideanRT0ComponentEval q i
          (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) •
        φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) -
      euclideanRT0ComponentEval q i
          (referenceSimplexFiberPoint i (y : EuclideanDomain d)
            (referenceSimplexFiberUpper i (y : EuclideanDomain d))) •
        φ (referenceSimplexFiberPoint i (y : EuclideanDomain d)
          (referenceSimplexFiberUpper i (y : EuclideanDomain d))) := by
  have hupper :
      0 ≤ referenceSimplexFiberUpper i (y : EuclideanDomain d) :=
    referenceSimplexFiberUpper_nonneg_of_baseDomain i hy
  rw [
    integral_Icc_eq_intervalIntegral_of_nonneg _ hupper,
    integral_Icc_eq_intervalIntegral_of_nonneg _ hupper,
    euclideanRT0ComponentEval_fiber_integrationByParts
      q φ i (y : EuclideanDomain d) 0
        (referenceSimplexFiberUpper i (y : EuclideanDomain d))
  ]
  abel

end

end Continuum

end CACEFormal

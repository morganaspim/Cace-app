import Mathlib
import CACEFormal.ReferenceSimplexFiberIBP

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv Interval SchwartzMap

namespace Continuum

noncomputable section

/-!
# Coordinatewise Green identities on the reference simplex

The one-dimensional fiber IBP theorem is integrated over the orthogonal base
domain. This gives a genuine multidimensional identity for every coordinate
direction.

At this stage the boundary is written as the difference of the upper and lower
fiber endpoints. The next geometric layer identifies these endpoint
functionals with the corresponding oriented Hausdorff facet currents.
-/

/-- On an ordered interval, the set integral over Icc equals the interval integral. -/
theorem setIntegral_Icc_eq_intervalIntegral_of_le
    {F : Type*} [NormedAddCommGroup F] [NormedSpace ℝ F]
    (f : ℝ → F) {a b : ℝ} (hab : a ≤ b) :
    (∫ t in Set.Icc a b, f t) = ∫ t in a..b, f t := by
  calc
    (∫ t in Set.Icc a b, f t) =
        ∫ t in Set.Ioc a b, f t :=
      (setIntegral_congr_set Ioc_ae_eq_Icc).symm
    _ = ∫ t in a..b, f t :=
      (intervalIntegral.integral_of_le hab).symm

/--
Coordinatewise P1 Green identity on the reference simplex.

The right-hand side is an outer integral over admissible fibers. For each
fiber it contains the upper endpoint contribution, minus the lower endpoint
contribution, minus the integral of the constant P1 derivative.
-/
theorem referenceSimplexP1_coordinateGreen
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    (∫ x,
      (euclideanReferenceSimplex d).indicator
        (fun x =>
          euclideanAffineScalarEval u x •
            (∂_{basisVector i} φ) x) x) =
      ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        (referenceSimplexFiberBaseDomain i).indicator
          (fun y =>
            let U :=
              referenceSimplexFiberUpper i
                (y : EuclideanDomain d)
            euclideanAffineScalarEval u
                (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) U) •
              φ (referenceSimplexFiberPoint i
                (y : EuclideanDomain d) U) -
            euclideanAffineScalarEval u
                (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) 0) •
              φ (referenceSimplexFiberPoint i
                (y : EuclideanDomain d) 0) -
            ∫ t in Set.Icc 0 U,
              u.grad i •
                φ (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) t)) y := by
  rw [integral_referenceSimplex_indicator_eq_fibers
    i
    (fun x =>
      euclideanAffineScalarEval u x •
        (∂_{basisVector i} φ) x)
    (referenceSimplex_affine_fiberCoordinates_integrable
      u (∂_{basisVector i} φ) i)]
  apply integral_congr_ae
  filter_upwards with y
  by_cases hy : y ∈ referenceSimplexFiberBaseDomain i
  · rw [Set.indicator_of_mem hy, Set.indicator_of_mem hy]
    let U :=
      referenceSimplexFiberUpper i (y : EuclideanDomain d)
    have hU : 0 ≤ U :=
      referenceSimplexFiberUpper_nonneg_of_baseDomain i hy
    rw [setIntegral_Icc_eq_intervalIntegral_of_le _ hU,
      setIntegral_Icc_eq_intervalIntegral_of_le _ hU]
    simpa [U] using
      (euclideanAffineScalarEval_fiber_integrationByParts
        u φ i (y : EuclideanDomain d) 0 U)
  · simp [Set.indicator_of_notMem hy]

/--
Coordinatewise RT0 Green identity on the reference simplex.

The interior derivative on each matching coordinate fiber is the common RT0
radial coefficient.
-/
theorem referenceSimplexRT0_coordinateGreen
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    (∫ x,
      (euclideanReferenceSimplex d).indicator
        (fun x =>
          euclideanRT0ComponentEval q i x •
            (∂_{basisVector i} φ) x) x) =
      ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        (referenceSimplexFiberBaseDomain i).indicator
          (fun y =>
            let U :=
              referenceSimplexFiberUpper i
                (y : EuclideanDomain d)
            euclideanRT0ComponentEval q i
                (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) U) •
              φ (referenceSimplexFiberPoint i
                (y : EuclideanDomain d) U) -
            euclideanRT0ComponentEval q i
                (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) 0) •
              φ (referenceSimplexFiberPoint i
                (y : EuclideanDomain d) 0) -
            ∫ t in Set.Icc 0 U,
              q.radial •
                φ (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) t)) y := by
  rw [integral_referenceSimplex_indicator_eq_fibers
    i
    (fun x =>
      euclideanRT0ComponentEval q i x •
        (∂_{basisVector i} φ) x)
    (referenceSimplex_RT0_fiberCoordinates_integrable
      q i (∂_{basisVector i} φ))]
  apply integral_congr_ae
  filter_upwards with y
  by_cases hy : y ∈ referenceSimplexFiberBaseDomain i
  · rw [Set.indicator_of_mem hy, Set.indicator_of_mem hy]
    let U :=
      referenceSimplexFiberUpper i (y : EuclideanDomain d)
    have hU : 0 ≤ U :=
      referenceSimplexFiberUpper_nonneg_of_baseDomain i hy
    rw [setIntegral_Icc_eq_intervalIntegral_of_le _ hU,
      setIntegral_Icc_eq_intervalIntegral_of_le _ hU]
    simpa [U] using
      (euclideanRT0ComponentEval_fiber_integrationByParts
        q φ i (y : EuclideanDomain d) 0 U)
  · simp [Set.indicator_of_notMem hy]

end

end Continuum

end CACEFormal

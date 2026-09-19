import Mathlib
import CACEFormal.ReferenceSimplexFiberDomain

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators MeasureTheory

namespace Continuum

noncomputable section

/-!
# Fubini formula for the Euclidean reference simplex

Combining the orthogonal measure decomposition with the exact fiber-domain
characterization gives the reference-simplex Fubini identity.

The theorem is deliberately stated first for the ordinary integral of the
simplex indicator.  This avoids adding a separate measurability proof for the
simplex merely to change notation; later layers may rewrite it as a set
integral once convenient.

The only analytic hypothesis is integrability after the canonical orthogonal
product decomposition.  For the P1/RT0 times Schwartz integrands used by
Gauss--Green this follows from compact support/boundedness and will be discharged
in the specialization layer.
-/

/--
Reference-simplex Fubini formula along coordinate `i`.

The full-dimensional simplex indicator is integrated by first choosing an
orthogonal base point and then integrating over its exact scalar fiber interval.
-/
theorem integral_referenceSimplex_indicator_eq_fibers
    {d : Nat} {F : Type*}
    [NormedAddCommGroup F] [NormedSpace ℝ F]
    (i : Fin d) (f : EuclideanDomain d → F)
    (hf :
      Integrable
        (fun q :
          referenceSimplexCoordinateLine i ×
            (referenceSimplexCoordinateLine i)ᗮ =>
          (euclideanReferenceSimplex d).indicator f
            ((q.1 : EuclideanDomain d) + (q.2 : EuclideanDomain d)))) :
    (∫ x, (euclideanReferenceSimplex d).indicator f x) =
      ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        (referenceSimplexFiberBaseDomain i).indicator
          (fun y =>
            ∫ t in
              Set.Icc 0
                (referenceSimplexFiberUpper i
                  (y : EuclideanDomain d)),
              f (referenceSimplexFiberPoint i
                (y : EuclideanDomain d) t)) y := by
  rw [integral_eq_orthogonalFiber_integral
    i ((euclideanReferenceSimplex d).indicator f) hf]
  apply integral_congr_ae
  filter_upwards with y
  by_cases hy : y ∈ referenceSimplexFiberBaseDomain i
  · rw [Set.indicator_of_mem hy]
    calc
      (∫ t : ℝ,
        (euclideanReferenceSimplex d).indicator f
          (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) =
          ∫ t : ℝ,
            (Set.Icc 0
              (referenceSimplexFiberUpper i
                (y : EuclideanDomain d))).indicator
              (fun t =>
                f (referenceSimplexFiberPoint i
                  (y : EuclideanDomain d) t)) t := by
        apply integral_congr_ae
        filter_upwards with t
        simpa [Set.indicator_of_mem hy] using
          (euclideanReferenceSimplex_indicator_fiber i f y t)
      _ =
          ∫ t in
            Set.Icc 0
              (referenceSimplexFiberUpper i
                (y : EuclideanDomain d)),
            f (referenceSimplexFiberPoint i
              (y : EuclideanDomain d) t) := by
        rw [integral_indicator measurableSet_Icc]
  · rw [Set.indicator_of_notMem hy]
    have hzero :
        ∀ t : ℝ,
          (euclideanReferenceSimplex d).indicator f
            (referenceSimplexFiberPoint i
              (y : EuclideanDomain d) t) = 0 := by
      intro t
      simpa [Set.indicator_of_notMem hy] using
        (euclideanReferenceSimplex_indicator_fiber i f y t)
    simp [hzero]

end

end Continuum

end CACEFormal

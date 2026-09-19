import Mathlib
import CACEFormal.ReferenceSimplexIntegrability

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv Interval SchwartzMap

namespace Continuum

noncomputable section

/-!
# Stable wrappers for reference-simplex fiber integration by parts

The core Schwartz chain rule and interval integration-by-parts theorems live in
`ReferenceSimplexFiberCalculus`.  This module provides only the packaged
versions for `referenceSimplexP1Fiber` and `referenceSimplexRT0Fiber`, so
downstream Gauss--Green code can depend on the stable one-dimensional fiber
interfaces without duplicating the analytic implementation.
-/

/-- Packaged P1 fiber integration by parts. -/
theorem referenceSimplexP1Fiber_integrationByParts
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) (a b : ℝ) :
    (∫ t in a..b,
      referenceSimplexP1Fiber u i x t •
        (∂_{basisVector i} φ)
          (referenceSimplexFiberPoint i x t)) =
      referenceSimplexP1Fiber u i x b •
          φ (referenceSimplexFiberPoint i x b) -
        referenceSimplexP1Fiber u i x a •
          φ (referenceSimplexFiberPoint i x a) -
        ∫ t in a..b,
          u.grad i •
            φ (referenceSimplexFiberPoint i x t) := by
  simpa [referenceSimplexP1Fiber] using
    (euclideanAffineScalarEval_fiber_integrationByParts
      u φ i x a b)

/-- Packaged RT0 coordinate-fiber integration by parts. -/
theorem referenceSimplexRT0Fiber_integrationByParts
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) (a b : ℝ) :
    (∫ t in a..b,
      referenceSimplexRT0Fiber q i x t •
        (∂_{basisVector i} φ)
          (referenceSimplexFiberPoint i x t)) =
      referenceSimplexRT0Fiber q i x b •
          φ (referenceSimplexFiberPoint i x b) -
        referenceSimplexRT0Fiber q i x a •
          φ (referenceSimplexFiberPoint i x a) -
        ∫ t in a..b,
          q.radial •
            φ (referenceSimplexFiberPoint i x t) := by
  simpa [referenceSimplexRT0Fiber] using
    (euclideanRT0ComponentEval_fiber_integrationByParts
      q φ i x a b)

end

end Continuum

end CACEFormal

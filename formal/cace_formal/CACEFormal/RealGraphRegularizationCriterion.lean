import CACEFormal.PDEDomainRealBridge
import CACEFormal.RegularizationClosure

namespace CACEFormal

open Set Filter

namespace Continuum

noncomputable section

/-!
# v3.30 real H(div) graph regularization criterion

The operational continuum graph model introduced before the complex distributional bridge is real
valued.  `PDEDomainRealBridge` already proves that its smooth graph core lies in the pulled-back
complex distributional H(div) relation and that this target relation is closed.

This file supplies the missing reusable reverse-inclusion criterion directly in those real graph
coordinates.  A concrete regularizer on `HDivGraphAmbient n` therefore upgrades the one-way bridge to
an equality without any further closure bookkeeping.
-/

/--
Real-coordinate orthogonal-annihilator criterion.

As in the complex graph model, the real smooth H(div) core is dense in the
pulled-back distributional graph as soon as that target contains no nonzero
vector orthogonal to the entire smooth core.
-/
theorem realHDivSmoothGraphClosure_eq_distributionalPreimage_of_relativeOrthogonal
    (n : Nat)
    (hzero : ∀ x : HDivGraphAmbient n,
      x ∈ RealHDivDistributionalPreimage n →
      x ∈ (HDivSmoothGraphCore n)ᗮ →
      x = 0) :
    (HDivSmoothGraphCore n).topologicalClosure =
      RealHDivDistributionalPreimage n := by
  exact submodule_topologicalClosure_eq_of_relativeOrthogonal_pointwise
    (HDivSmoothGraphCore n)
    (RealHDivDistributionalPreimage n)
    (HDivSmoothGraphCore_le_RealHDivDistributionalPreimage n)
    (isClosed_RealHDivDistributionalPreimage n)
    hzero

/-- Reverse inclusion from the real relative-orthogonal criterion. -/
theorem realDistributionalPreimage_le_HDivSmoothGraphClosure_of_relativeOrthogonal
    (n : Nat)
    (hzero : ∀ x : HDivGraphAmbient n,
      x ∈ RealHDivDistributionalPreimage n →
      x ∈ (HDivSmoothGraphCore n)ᗮ →
      x = 0) :
    RealHDivDistributionalPreimage n ≤
      (HDivSmoothGraphCore n).topologicalClosure := by
  rw [realHDivSmoothGraphClosure_eq_distributionalPreimage_of_relativeOrthogonal n hzero]

/-- If every datum in the pulled-back distributional relation admits real smooth-core
regularizations converging in graph norm, then the real smooth graph closure is exactly that
relation. -/
theorem realHDivSmoothGraphClosure_eq_distributionalPreimage_of_regularizer
    (n : Nat)
    (R : Nat → HDivGraphAmbient n → HDivGraphAmbient n)
    (hcore : ∀ k x, x ∈ RealHDivDistributionalPreimage n →
      R k x ∈ HDivSmoothGraphCore n)
    (htendsto : ∀ x, x ∈ RealHDivDistributionalPreimage n →
      Tendsto (fun k => R k x) atTop (nhds x)) :
    (HDivSmoothGraphCore n).topologicalClosure =
      RealHDivDistributionalPreimage n := by
  exact submodule_topologicalClosure_eq_of_regularizer
    (𝕜 := ℝ)
    (E := HDivGraphAmbient n)
    (HDivSmoothGraphCore n) (RealHDivDistributionalPreimage n)
    (HDivSmoothGraphCore_le_RealHDivDistributionalPreimage n)
    (isClosed_RealHDivDistributionalPreimage n)
    R hcore htendsto

/-- Reverse inclusion in the real graph coordinates. -/
theorem realDistributionalPreimage_le_HDivSmoothGraphClosure_of_regularizer
    (n : Nat)
    (R : Nat → HDivGraphAmbient n → HDivGraphAmbient n)
    (hcore : ∀ k x, x ∈ RealHDivDistributionalPreimage n →
      R k x ∈ HDivSmoothGraphCore n)
    (htendsto : ∀ x, x ∈ RealHDivDistributionalPreimage n →
      Tendsto (fun k => R k x) atTop (nhds x)) :
    RealHDivDistributionalPreimage n ≤
      (HDivSmoothGraphCore n).topologicalClosure := by
  exact submodule_le_topologicalClosure_of_regularizer
    (𝕜 := ℝ)
    (E := HDivGraphAmbient n)
    (HDivSmoothGraphCore n) (RealHDivDistributionalPreimage n)
    (HDivSmoothGraphCore_le_RealHDivDistributionalPreimage n)
    (isClosed_RealHDivDistributionalPreimage n)
    R hcore htendsto

end

end Continuum

end CACEFormal

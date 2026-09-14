import CACEFormal.PDEDomainBridge
import CACEFormal.RegularizationClosure

namespace CACEFormal

open Set Filter

namespace Continuum

noncomputable section

/-!
# v3.30 graph-regularization criterion

The hard direction missing from v3.29 is

`HDivDistributionalGraphSubmodule n ≤ (ComplexHDivSmoothGraphCore n).topologicalClosure`.

The generic topology has now been factored into `RegularizationClosure`.  Consequently the only
H(div)-specific content left in this criterion is the already-proved smooth-core inclusion, closedness
of the distributional graph relation, and the two obligations for a concrete regularizer:

* core preservation: `R k x` lies in the Schwartz H(div) graph core;
* graph convergence: `R k x → x` in the ambient L2 graph topology.

This is designed for either of two serious analytic routes: Fourier/multiplier regularization or
physical-space mollification plus a Schwartz cutoff with a divergence commutator estimate.
-/

/-- A convergent graph regularizer identifies the Schwartz graph closure with the closed
distributional H(div) graph relation. -/
theorem complexSmoothGraphClosure_eq_distributional_of_regularizer
    (n : Nat)
    (R : Nat → HDivComplexGraphAmbient n → HDivComplexGraphAmbient n)
    (hcore : ∀ k x, x ∈ HDivDistributionalGraphSubmodule n →
      R k x ∈ ComplexHDivSmoothGraphCore n)
    (htendsto : ∀ x, x ∈ HDivDistributionalGraphSubmodule n →
      Tendsto (fun k => R k x) atTop (𝓝 x)) :
    (ComplexHDivSmoothGraphCore n).topologicalClosure =
      HDivDistributionalGraphSubmodule n := by
  exact submodule_topologicalClosure_eq_of_regularizer
    (ComplexHDivSmoothGraphCore n) (HDivDistributionalGraphSubmodule n)
    (ComplexHDivSmoothGraphCore_le_distributional n)
    (isClosed_HDivDistributionalGraphSubmodule n)
    R hcore htendsto

/-- Once a regularizer is available, every distributional H(div) graph datum lies in the smooth
graph closure. This is the reverse inclusion that v3.29 deliberately did not claim. -/
theorem distributional_le_complexSmoothGraphClosure_of_regularizer
    (n : Nat)
    (R : Nat → HDivComplexGraphAmbient n → HDivComplexGraphAmbient n)
    (hcore : ∀ k x, x ∈ HDivDistributionalGraphSubmodule n →
      R k x ∈ ComplexHDivSmoothGraphCore n)
    (htendsto : ∀ x, x ∈ HDivDistributionalGraphSubmodule n →
      Tendsto (fun k => R k x) atTop (𝓝 x)) :
    HDivDistributionalGraphSubmodule n ≤
      (ComplexHDivSmoothGraphCore n).topologicalClosure := by
  exact submodule_le_topologicalClosure_of_regularizer
    (ComplexHDivSmoothGraphCore n) (HDivDistributionalGraphSubmodule n)
    (ComplexHDivSmoothGraphCore_le_distributional n)
    (isClosed_HDivDistributionalGraphSubmodule n)
    R hcore htendsto

end

end Continuum

end CACEFormal

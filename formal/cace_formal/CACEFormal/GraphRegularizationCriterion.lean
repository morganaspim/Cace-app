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

The generic topology has now been factored into `RegularizationClosure`.  The target H(div) graph is
itself the kernel of the continuous defect map `complexHDivGraphDefect`, so even target closedness is
automatic.  Consequently the only H(div)-specific obligations left for a concrete regularizer are:

* core preservation: `R k x` lies in the Schwartz H(div) graph core;
* graph convergence: `R k x → x` in the ambient L2 graph topology.

This is designed for either of two serious analytic routes: Fourier/multiplier regularization or
physical-space mollification plus a Schwartz cutoff with a divergence commutator estimate.
-/

/--
Alternative H(div) density criterion by relative orthogonality.

This route avoids assuming an explicit regularizer.  It is enough to prove that
a distributional H(div) graph datum orthogonal to every Schwartz graph datum is
zero.  The intended next proof derives a weak H1 relation for the divergence
coordinate from that orthogonality, combines it with `div q = g`, and rules
out nonzero L2 solutions of the resulting elliptic equation.
-/
theorem complexSmoothGraphClosure_eq_distributional_of_relativeOrthogonal
    (n : Nat)
    (hzero : ∀ x : HDivComplexGraphAmbient n,
      x ∈ HDivDistributionalGraphSubmodule n →
      x ∈ (ComplexHDivSmoothGraphCore n)ᗮ →
      x = 0) :
    (ComplexHDivSmoothGraphCore n).topologicalClosure =
      HDivDistributionalGraphSubmodule n := by
  exact submodule_topologicalClosure_eq_of_relativeOrthogonal_pointwise
    (ComplexHDivSmoothGraphCore n)
    (HDivDistributionalGraphSubmodule n)
    (ComplexHDivSmoothGraphCore_le_distributional n)
    (isClosed_HDivDistributionalGraphSubmodule n)
    hzero

/-- Reverse inclusion obtained from the same orthogonal-annihilator criterion. -/
theorem distributional_le_complexSmoothGraphClosure_of_relativeOrthogonal
    (n : Nat)
    (hzero : ∀ x : HDivComplexGraphAmbient n,
      x ∈ HDivDistributionalGraphSubmodule n →
      x ∈ (ComplexHDivSmoothGraphCore n)ᗮ →
      x = 0) :
    HDivDistributionalGraphSubmodule n ≤
      (ComplexHDivSmoothGraphCore n).topologicalClosure := by
  rw [complexSmoothGraphClosure_eq_distributional_of_relativeOrthogonal n hzero]

/-- A convergent graph regularizer identifies the Schwartz graph closure with the closed
distributional H(div) graph relation. -/
theorem complexSmoothGraphClosure_eq_distributional_of_regularizer
    (n : Nat)
    (R : Nat → HDivComplexGraphAmbient n → HDivComplexGraphAmbient n)
    (hcore : ∀ k x, x ∈ HDivDistributionalGraphSubmodule n →
      R k x ∈ ComplexHDivSmoothGraphCore n)
    (htendsto : ∀ x, x ∈ HDivDistributionalGraphSubmodule n →
      Tendsto (fun k => R k x) atTop (nhds x)) :
    (ComplexHDivSmoothGraphCore n).topologicalClosure =
      HDivDistributionalGraphSubmodule n := by
  exact submodule_topologicalClosure_eq_of_regularizer
    (𝕜 := ℂ)
    (E := HDivComplexGraphAmbient n)
    (ComplexHDivSmoothGraphCore n)
    (HDivDistributionalGraphSubmodule n)
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
      Tendsto (fun k => R k x) atTop (nhds x)) :
    HDivDistributionalGraphSubmodule n ≤
      (ComplexHDivSmoothGraphCore n).topologicalClosure := by
  exact submodule_le_topologicalClosure_of_regularizer
    (𝕜 := ℂ)
    (E := HDivComplexGraphAmbient n)
    (ComplexHDivSmoothGraphCore n)
    (HDivDistributionalGraphSubmodule n)
    (ComplexHDivSmoothGraphCore_le_distributional n)
    (isClosed_HDivDistributionalGraphSubmodule n)
    R hcore htendsto

end

end Continuum

end CACEFormal

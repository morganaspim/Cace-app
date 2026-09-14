import CACEFormal.PDEDomainBridge
import Mathlib.Topology.Sequences

namespace CACEFormal

open Set Filter

namespace Continuum

noncomputable section

/-!
# v3.30 graph-regularization criterion

The hard direction missing from v3.29 is

`HDivDistributionalGraphSubmodule n ≤ (ComplexHDivSmoothGraphCore n).topologicalClosure`.

Rather than asking every future proof to rebuild the topological closure argument, this module
isolates the genuinely analytic content. It is enough to construct any sequence of regularizers
that sends distributional graph data into the Schwartz graph core and converges in the ambient
L2 graph norm. Once those two facts are supplied, Lean closes the graph-density theorem.

This is designed for either of the two serious analytic routes:

* Fourier cutoff / multiplier regularization, or
* physical-space mollification followed by a Schwartz cutoff with a commutator estimate.

The theorem below contains no numerical assumption and no theorem-discovery evidence.
-/

/-- A convergent graph regularizer is sufficient to identify the Schwartz graph closure with the
closed distributional H(div) graph relation. This packages the topology/closure step so the remaining
research obligation is exactly the analytic construction and convergence of the regularizer. -/
theorem complexSmoothGraphClosure_eq_distributional_of_regularizer
    (n : Nat)
    (R : Nat → HDivComplexGraphAmbient n → HDivComplexGraphAmbient n)
    (hcore : ∀ k x, x ∈ HDivDistributionalGraphSubmodule n →
      R k x ∈ ComplexHDivSmoothGraphCore n)
    (htendsto : ∀ x, x ∈ HDivDistributionalGraphSubmodule n →
      Tendsto (fun k => R k x) atTop (𝓝 x)) :
    (ComplexHDivSmoothGraphCore n).topologicalClosure =
      HDivDistributionalGraphSubmodule n := by
  apply le_antisymm (complexSmoothGraphClosure_le_distributional n)
  intro x hx
  change x ∈ ((ComplexHDivSmoothGraphCore n).topologicalClosure :
    Set (HDivComplexGraphAmbient n))
  rw [Submodule.topologicalClosure_coe]
  exact mem_closure_of_tendsto (htendsto x hx)
    (Filter.Eventually.of_forall fun k => hcore k x hx)

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
  rw [complexSmoothGraphClosure_eq_distributional_of_regularizer n R hcore htendsto]

end

end Continuum

end CACEFormal

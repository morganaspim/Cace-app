import Mathlib.Analysis.Complex.Basic
import Mathlib.Topology.Algebra.Module.Basic
import Mathlib.Topology.Sequences

namespace CACEFormal

open Set Filter

namespace Continuum

noncomputable section

/-!
# Generic regularization-to-closure theorems

Many hard analysis identifications have the same final shape: a concrete smooth/test-function core
`S` is already known to lie in a closed target relation `T`, while the difficult analytic work is to
construct regularized elements of `S` converging to every `x ∈ T`.

This module packages the topological conclusion once and for all.  It is deliberately independent of
Sobolev spaces, H(div), boxes, PDE coefficients and numerical evidence.
-/

variable {𝕜 E : Type*}
variable [RCLike 𝕜] [NormedAddCommGroup E] [NormedSpace 𝕜 E]

/-- A closed target submodule equals the closure of a core as soon as the core lies in the target
and every target point admits a convergent sequence of core-valued regularizations. -/
theorem submodule_topologicalClosure_eq_of_regularizer
    (S T : Submodule 𝕜 E)
    (hST : S ≤ T)
    (hT : IsClosed (T : Set E))
    (R : Nat → E → E)
    (hcore : ∀ k x, x ∈ T → R k x ∈ S)
    (htendsto : ∀ x, x ∈ T → Tendsto (fun k => R k x) atTop (𝓝 x)) :
    S.topologicalClosure = T := by
  apply le_antisymm
  · exact Submodule.topologicalClosure_minimal S hST hT
  · intro x hx
    change x ∈ (S.topologicalClosure : Set E)
    rw [Submodule.topologicalClosure_coe]
    exact mem_closure_of_tendsto (htendsto x hx)
      (Filter.Eventually.of_forall fun k => hcore k x hx)

/-- Reverse inclusion form of `submodule_topologicalClosure_eq_of_regularizer`.  This is convenient
when an existing development has already proved the easy closure-to-target inclusion. -/
theorem submodule_le_topologicalClosure_of_regularizer
    (S T : Submodule 𝕜 E)
    (hST : S ≤ T)
    (hT : IsClosed (T : Set E))
    (R : Nat → E → E)
    (hcore : ∀ k x, x ∈ T → R k x ∈ S)
    (htendsto : ∀ x, x ∈ T → Tendsto (fun k => R k x) atTop (𝓝 x)) :
    T ≤ S.topologicalClosure := by
  rw [submodule_topologicalClosure_eq_of_regularizer S T hST hT R hcore htendsto]

/--
Kernel-specialized regularization principle.

Closed graph relations in analysis are very often represented as the kernel of a continuous linear
"defect" map.  In that situation callers no longer need to separately prove closedness: continuity
of the defect makes the kernel closed automatically.  The remaining proof obligations are exactly
(1) the smooth core has zero defect, (2) the regularizer lands in that core, and (3) it converges in
the ambient graph norm.
-/
theorem submodule_topologicalClosure_eq_ker_of_regularizer
    {F : Type*} [NormedAddCommGroup F] [NormedSpace 𝕜 F]
    (S : Submodule 𝕜 E) (A : E →L[𝕜] F)
    (hS : S ≤ A.ker)
    (R : Nat → E → E)
    (hcore : ∀ k x, x ∈ A.ker → R k x ∈ S)
    (htendsto : ∀ x, x ∈ A.ker → Tendsto (fun k => R k x) atTop (𝓝 x)) :
    S.topologicalClosure = A.ker := by
  exact submodule_topologicalClosure_eq_of_regularizer
    S A.ker hS A.isClosed_ker R hcore htendsto

/-- Reverse-inclusion form of the kernel regularization theorem. -/
theorem ker_le_topologicalClosure_of_regularizer
    {F : Type*} [NormedAddCommGroup F] [NormedSpace 𝕜 F]
    (S : Submodule 𝕜 E) (A : E →L[𝕜] F)
    (hS : S ≤ A.ker)
    (R : Nat → E → E)
    (hcore : ∀ k x, x ∈ A.ker → R k x ∈ S)
    (htendsto : ∀ x, x ∈ A.ker → Tendsto (fun k => R k x) atTop (𝓝 x)) :
    A.ker ≤ S.topologicalClosure := by
  rw [submodule_topologicalClosure_eq_ker_of_regularizer S A hS R hcore htendsto]

/-- A core is dense in the whole ambient normed space when a regularizer lands in the core and
converges pointwise to every ambient point. -/
theorem topologicalClosure_eq_top_of_regularizer
    (S : Submodule 𝕜 E)
    (R : Nat → E → E)
    (hcore : ∀ k x, R k x ∈ S)
    (htendsto : ∀ x, Tendsto (fun k => R k x) atTop (𝓝 x)) :
    S.topologicalClosure = ⊤ := by
  apply submodule_topologicalClosure_eq_of_regularizer S ⊤ (le_top) isClosed_univ R
  · intro k x hx
    exact hcore k x
  · intro x hx
    exact htendsto x

end

end Continuum

end CACEFormal

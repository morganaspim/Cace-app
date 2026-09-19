import CACEFormal.RegularizationClosure
import Mathlib.Analysis.InnerProductSpace.Projection.Submodule

namespace CACEFormal

open Set

namespace Continuum

noncomputable section

/-!
# Relative orthogonal-complement closure criterion

This file is deliberately separated from `RegularizationClosure`.  The latter
is generic over an arbitrary normed space.  Orthogonal complements require an
inner-product-induced norm; keeping the instances here avoids introducing a
second competing `NormedSpace` instance into the generic regularization file.
-/

variable {𝕜 E : Type*}
variable [RCLike 𝕜] [NormedAddCommGroup E] [InnerProductSpace 𝕜 E] [CompleteSpace E]

/--
A core `S` is dense in a closed target submodule `T` once `S ≤ T` and
the relative orthogonal complement `Sᗮ ⊓ T` is trivial.
-/
theorem submodule_topologicalClosure_eq_of_relativeOrthogonal_eq_bot
    (S T : Submodule 𝕜 E)
    (hST : S ≤ T)
    (hT : IsClosed (T : Set E))
    (horth : Sᗮ ⊓ T = ⊥) :
    S.topologicalClosure = T := by
  have hclosure : S.topologicalClosure ≤ T :=
    Submodule.topologicalClosure_minimal S hST hT
  have hdecomp :=
    Submodule.sup_orthogonal_inf_of_hasOrthogonalProjection hclosure
  simpa [horth] using hdecomp

/-- Pointwise form of the relative-orthogonal criterion. -/
theorem submodule_topologicalClosure_eq_of_relativeOrthogonal_pointwise
    (S T : Submodule 𝕜 E)
    (hST : S ≤ T)
    (hT : IsClosed (T : Set E))
    (hzero : ∀ x : E, x ∈ T → x ∈ Sᗮ → x = 0) :
    S.topologicalClosure = T := by
  apply submodule_topologicalClosure_eq_of_relativeOrthogonal_eq_bot
    S T hST hT
  apply le_antisymm
  · intro x hx
    have hx0 : x = 0 := hzero x hx.2 hx.1
    simpa [hx0]
  · exact bot_le

end

end Continuum

end CACEFormal

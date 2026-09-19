import CACEFormal.HDivGraphAnnihilator
import CACEFormal.OrthogonalClosure

namespace CACEFormal

open Set

namespace Continuum

noncomputable section

/-!
# Whole-space H(div) density reduction

This module composes the already-proved orthogonal-closure criterion with the
H(div) graph annihilator.  It isolates the one remaining analytic obligation
for unconditional whole-space density:

* if a distributional H(div) graph datum is orthogonal to every Schwartz
  H(div) graph datum, then its reversed coordinates satisfy the distributional
  H1 graph relation.

Once that statement is supplied, no regularizer hypothesis is needed: the
relative orthogonal complement is trivial, hence the Schwartz H(div) graph core
is dense in the closed distributional H(div) graph.

No density claim is made here without that exact orthogonality-to-H1 bridge.
-/

/-- The exact remaining analytic criterion for unconditional whole-space
H(div) graph density. -/
def HDivOrthogonalReversedH1Criterion (n : Nat) : Prop :=
  ∀ x : HDivComplexGraphAmbient n,
    x ∈ HDivDistributionalGraphSubmodule n →
    x ∈ (ComplexHDivSmoothGraphCore n)ᗮ →
    reversedHDivGraph x ∈ H1DistributionalGraphSubmodule n

/-- Under the isolated orthogonality-to-reversed-H1 criterion, the relative
orthogonal complement of the smooth H(div) core inside the distributional graph
is trivial. -/
theorem complexHDiv_relativeOrthogonal_eq_bot_of_reversedH1
    (n : Nat) (hcriterion : HDivOrthogonalReversedH1Criterion n) :
    (ComplexHDivSmoothGraphCore n)ᗮ ⊓ HDivDistributionalGraphSubmodule n = ⊥ := by
  apply le_antisymm
  · intro x hx
    have hxZero : x = 0 :=
      hdivGraph_eq_zero_of_reversedH1 n x hx.2
        (hcriterion x hx.2 hx.1)
    simpa [hxZero]
  · exact bot_le

/-- Unconditional graph density is reduced to the single explicit analytic
criterion above.  All topology and annihilator algebra are discharged by
previously proved kernel-checked theorems. -/
theorem complexSmoothGraphClosure_eq_distributional_of_orthogonal_reversedH1
    (n : Nat) (hcriterion : HDivOrthogonalReversedH1Criterion n) :
    (ComplexHDivSmoothGraphCore n).topologicalClosure =
      HDivDistributionalGraphSubmodule n := by
  exact submodule_topologicalClosure_eq_of_relativeOrthogonal_eq_bot
    (ComplexHDivSmoothGraphCore n)
    (HDivDistributionalGraphSubmodule n)
    (ComplexHDivSmoothGraphCore_le_distributional n)
    (isClosed_HDivDistributionalGraphSubmodule n)
    (complexHDiv_relativeOrthogonal_eq_bot_of_reversedH1 n hcriterion)

/-- Pointwise version of the same reduction, convenient for proving the
remaining analytic bridge directly from Schwartz test functions. -/
theorem complexSmoothGraphClosure_eq_distributional_of_orthogonal_pointwise
    (n : Nat)
    (hrev : ∀ x : HDivComplexGraphAmbient n,
      x ∈ HDivDistributionalGraphSubmodule n →
      x ∈ (ComplexHDivSmoothGraphCore n)ᗮ →
      reversedHDivGraph x ∈ H1DistributionalGraphSubmodule n) :
    (ComplexHDivSmoothGraphCore n).topologicalClosure =
      HDivDistributionalGraphSubmodule n :=
  complexSmoothGraphClosure_eq_distributional_of_orthogonal_reversedH1
    n hrev

end

end Continuum

end CACEFormal

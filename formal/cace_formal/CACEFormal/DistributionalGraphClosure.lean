import CACEFormal.DistributionalGraphRepresentatives

namespace CACEFormal

open Set Filter

namespace Continuum

noncomputable section

/-!
# Exact closure obligations for the whole-space H¹/H(div) graph models

The easy inclusion (smooth graph closure is contained in the closed distributional graph relation)
is already proved in `H1DomainBridge` and `PDEDomainBridge`.  The reverse inclusion is the genuine
analytic density problem.  This module makes that remaining obligation explicit and reusable without
silently replacing it by density in a completion defined from the smooth core.
-/

/-- Concrete approximation data sufficient to identify the complex H¹ smooth graph closure with the
closed distributional derivative graph. -/
structure H1GraphApproximationWitness (n : Nat) where
  regularize : Nat → H1ComplexGraphAmbient n → H1ComplexGraphAmbient n
  mem_core : ∀ k x, x ∈ H1DistributionalGraphSubmodule n →
    regularize k x ∈ ComplexH1SmoothGraphCore n
  tendsto_graph : ∀ x, x ∈ H1DistributionalGraphSubmodule n →
    Tendsto (fun k => regularize k x) atTop (nhds x)

/-- Concrete approximation data sufficient to identify the complex H(div) smooth graph closure with
the closed distributional divergence graph. -/
structure HDivGraphApproximationWitness (n : Nat) where
  regularize : Nat → HDivComplexGraphAmbient n → HDivComplexGraphAmbient n
  mem_core : ∀ k x, x ∈ HDivDistributionalGraphSubmodule n →
    regularize k x ∈ ComplexHDivSmoothGraphCore n
  tendsto_graph : ∀ x, x ∈ HDivDistributionalGraphSubmodule n →
    Tendsto (fun k => regularize k x) atTop (nhds x)

/-- An H¹ graph approximation witness closes the exact smooth-core/distributional-graph equality. -/
theorem complexH1SmoothGraphClosure_eq_distributional
    (n : Nat) (h : H1GraphApproximationWitness n) :
    (ComplexH1SmoothGraphCore n).topologicalClosure =
      H1DistributionalGraphSubmodule n := by
  exact complexH1SmoothGraphClosure_eq_distributional_of_regularizer
    n h.regularize h.mem_core h.tendsto_graph

/-- An H(div) graph approximation witness closes the exact smooth-core/distributional-graph equality. -/
theorem complexHDivSmoothGraphClosure_eq_distributional
    (n : Nat) (h : HDivGraphApproximationWitness n) :
    (ComplexHDivSmoothGraphCore n).topologicalClosure =
      HDivDistributionalGraphSubmodule n := by
  exact submodule_topologicalClosure_eq_of_regularizer
    (ComplexHDivSmoothGraphCore n)
    (HDivDistributionalGraphSubmodule n)
    (ComplexHDivSmoothGraphCore_le_distributional n)
    (isClosed_HDivDistributionalGraphSubmodule n)
    h.regularize h.mem_core h.tendsto_graph

/-- Under the H(div) approximation theorem, every distributional graph datum is approximable in the
actual ambient L² graph norm by Schwartz graph data.  This is the reverse inclusion that was missing
from the earlier one-way bridge. -/
theorem distributionalHDiv_le_complexSmoothGraphClosure
    (n : Nat) (h : HDivGraphApproximationWitness n) :
    HDivDistributionalGraphSubmodule n ≤
      (ComplexHDivSmoothGraphCore n).topologicalClosure := by
  rw [complexHDivSmoothGraphClosure_eq_distributional n h]

/-- Parallel reverse inclusion for H¹. -/
theorem distributionalH1_le_complexSmoothGraphClosure
    (n : Nat) (h : H1GraphApproximationWitness n) :
    H1DistributionalGraphSubmodule n ≤
      (ComplexH1SmoothGraphCore n).topologicalClosure := by
  rw [complexH1SmoothGraphClosure_eq_distributional n h]

end

end Continuum

end CACEFormal

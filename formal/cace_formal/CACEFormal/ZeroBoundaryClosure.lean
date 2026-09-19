import CACEFormal.BoxPragerSyngeEquilibrated
import Mathlib.Topology.Algebra.Module.Basic

namespace CACEFormal

namespace Continuum

noncomputable section

/-!
# Closed zero-boundary trace space and closure inheritance

The bounded-box Prager--Synge endpoint currently requires a functional
zero-boundary-trace hypothesis.  This module does not weaken or assume that
hypothesis.  Instead it proves the topological fact needed to derive it from
an independently certified boundary-vanishing core:

* the functional zero-boundary space is an intersection of kernels of
  continuous linear trace functionals, hence is closed;
* the topological closure of any submodule already known to have zero trace
  stays inside the zero-boundary space;
* therefore the bounded-box equilibrated Prager--Synge identity can consume
  membership in such a certified core closure instead of a caller-supplied
  pointwise trace proof.

The remaining analytic task is honest and explicit: construct a useful
boundary-vanishing box core and prove its elements have zero functional trace.
-/

/-- The functional zero-boundary submodule is the intersection of the kernels
of all normal-trace functionals. -/
theorem zeroBoundarySubmodule_eq_iInf_ker
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q) :
    zeroBoundarySubmodule G =
      ⨅ q : Q, (G.normalTrace q).ker := by
  ext v
  simp [zeroBoundarySubmodule, HasZeroBoundaryTrace]

/-- Functional zero boundary conditions are closed in the graph norm. -/
theorem isClosed_zeroBoundarySubmodule
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q) :
    IsClosed (zeroBoundarySubmodule G : Set V) := by
  rw [zeroBoundarySubmodule_eq_iInf_ker G]
  exact isClosed_iInter fun q => (G.normalTrace q).isClosed_ker

/-- If every vector in a core submodule has zero functional boundary trace,
then every graph-norm limit of that core has zero trace as well. -/
theorem topologicalClosure_le_zeroBoundarySubmodule
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q)
    (V0 : Submodule ℝ V)
    (hV0 : V0 ≤ zeroBoundarySubmodule G) :
    V0.topologicalClosure ≤ zeroBoundarySubmodule G :=
  V0.topologicalClosure_minimal hV0 (isClosed_zeroBoundarySubmodule G)

/-- Pointwise version of closure inheritance, phrased directly as the trace
predicate used by the Prager--Synge layer. -/
theorem hasZeroBoundaryTrace_of_mem_topologicalClosure
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q)
    (V0 : Submodule ℝ V)
    (hV0 : ∀ v, v ∈ V0 → HasZeroBoundaryTrace G v)
    (v : V) (hv : v ∈ V0.topologicalClosure) :
    HasZeroBoundaryTrace G v := by
  apply (mem_zeroBoundarySubmodule_iff G v).mp
  apply topologicalClosure_le_zeroBoundarySubmodule G V0
  · intro w hw
    exact (mem_zeroBoundarySubmodule_iff G w).mpr (hV0 w hw)
  · exact hv

/-- Bounded-box specialization: zero trace on a certified H¹ graph core
propagates to its graph-norm closure. -/
theorem boxHasZeroBoundaryTrace_of_mem_coreClosure
    {n : Nat} (a b : BoxPoint n)
    (V0 : Submodule ℝ (BoxH1GraphClosedSpace a b))
    (hV0 : ∀ v, v ∈ V0 →
      HasZeroBoundaryTrace (boxGraphBoundedGreenPairing a b) v)
    (v : BoxH1GraphClosedSpace a b)
    (hv : v ∈ V0.topologicalClosure) :
    HasZeroBoundaryTrace (boxGraphBoundedGreenPairing a b) v :=
  hasZeroBoundaryTrace_of_mem_topologicalClosure
    (boxGraphBoundedGreenPairing a b) V0 hV0 v hv

/--
Equilibrated bounded-box Prager--Synge identity with the zero-boundary
hypothesis derived from membership in the graph-norm closure of a certified
boundary-vanishing H¹ core.
-/
theorem boxGraphPragerSynge_of_divergence_zero_of_mem_coreClosure
    {n : Nat} (a b : BoxPoint n)
    (V0 : Submodule ℝ (BoxH1GraphClosedSpace a b))
    (hV0 : ∀ w, w ∈ V0 →
      HasZeroBoundaryTrace (boxGraphBoundedGreenPairing a b) w)
    (q : BoxHDivGraphClosedSpace a b)
    (v : BoxH1GraphClosedSpace a b)
    (hv : v ∈ V0.topologicalClosure)
    (hdiv : q.1.2 = 0) :
    ‖boxH1GradientError a b v + boxHDivFieldError a b q‖ *
        ‖boxH1GradientError a b v + boxHDivFieldError a b q‖ =
      ‖boxH1GradientError a b v‖ * ‖boxH1GradientError a b v‖ +
        ‖boxHDivFieldError a b q‖ * ‖boxHDivFieldError a b q‖ := by
  apply boxGraphPragerSynge_of_divergence_zero a b q v
  · exact boxHasZeroBoundaryTrace_of_mem_coreClosure a b V0 hV0 v hv
  · exact hdiv

end

end Continuum

end CACEFormal

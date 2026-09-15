import CACEFormal.H1BesselRieszReduction

namespace CACEFormal

open MeasureTheory
open scoped LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# Distributional H1 graph converse

`H1BesselRieszReduction` proves the unconditional weak-derivative characterization

`u ∈ L2` and `∀ i, weakPartial i u ∈ L2`  ==>  `u ∈ InH1`.

A datum in `H1DistributionalGraphSubmodule` stores exactly those hypotheses: its value coordinate is
an actual complex L2 function, every gradient coordinate is an actual complex L2 function, and the
graph equation identifies those coordinates with the weak derivatives of the value distribution.
This file therefore closes the representation-level converse without adding any analytic assumption.
-/

/-- Every datum in the closed distributional H1 graph relation represents a genuine Mathlib
Bessel-potential H1 distribution in its value coordinate. -/
theorem inH1_of_mem_H1DistributionalGraphSubmodule (n : Nat)
    (x : H1ComplexGraphAmbient n)
    (hx : x ∈ H1DistributionalGraphSubmodule n) :
    InH1 (complexL2ToDistribution n x.1) := by
  apply inH1_of_inL2_weakPartial_inL2
  · exact complexL2ToDistribution_inL2 x.1
  · intro i
    have hgraph := (mem_H1DistributionalGraphSubmodule_iff n x).mp hx i
    rw [hgraph]
    exact complexL2ToDistribution_inL2 (x.2 i)

/-- Exact representation-level equivalence: a scalar tempered distribution is in Mathlib's H1
exactly when it is the value distribution of some L2 graph datum satisfying CACE's closed
weak-derivative relation. -/
theorem inH1_iff_exists_distributionalGraphRepresentative {n : Nat}
    (u : ScalarDistribution n) :
    InH1 u ↔
      ∃ x : H1ComplexGraphAmbient n,
        x ∈ H1DistributionalGraphSubmodule n ∧
        complexL2ToDistribution n x.1 = u := by
  constructor
  · exact inH1_has_distributionalGraphRepresentative u
  · rintro ⟨x, hx, hxu⟩
    rw [← hxu]
    exact inH1_of_mem_H1DistributionalGraphSubmodule n x hx

end

end Continuum

end CACEFormal

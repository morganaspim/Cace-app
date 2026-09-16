import CACEFormal.H1DomainBridge

namespace CACEFormal

open MeasureTheory
open scoped LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# v3.30 L2 representatives for distributional graph predicates

Mathlib's order-zero Sobolev characterization says that an `InL2` tempered distribution is exactly
one represented by an actual `Lp` element.  This module turns that theorem into reusable graph
coordinates.

For H(div) this closes a useful representation-level loop: the distributional predicate `InHDiv q`
is equivalent to the existence of complex L2 graph data in the closed divergence relation whose
field distribution is exactly `q`.

For H1 we prove the forward direction from Bessel-potential `InH1` to the distributional gradient
graph relation.  The converse identification remains a separate analytic theorem.
-/

/-- Choose an actual complex L2 representative of an order-zero Sobolev distribution. -/
noncomputable def l2RepresentativeOfInL2 {n : Nat}
    (u : ScalarDistribution n) (hu : InL2 u) : ComplexL2 n := by
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 u at hu
  exact Classical.choose (TemperedDistribution.memSobolev_zero_iff.mp hu)

/-- The chosen L2 representative maps back to the original tempered distribution. -/
theorem complexL2ToDistribution_l2RepresentativeOfInL2 {n : Nat}
    (u : ScalarDistribution n) (hu : InL2 u) :
    complexL2ToDistribution n (l2RepresentativeOfInL2 u hu) = u := by
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 u at hu
  have hrep := Classical.choose_spec (TemperedDistribution.memSobolev_zero_iff.mp hu)
  simpa [l2RepresentativeOfInL2, complexL2ToDistribution] using hrep.symm

/-- Canonical chosen L2 graph coordinates attached to a Bessel-potential H1 distribution. -/
noncomputable def inH1GraphRepresentative {n : Nat}
    (u : ScalarDistribution n) (hu : InH1 u) : H1ComplexGraphAmbient n :=
  (l2RepresentativeOfInL2 u (h1_l2 hu),
    fun i => l2RepresentativeOfInL2 (weakPartial i u) (h1_weakPartial_l2 hu i))

/-- Every Bessel-potential H1 field has L2 graph coordinates satisfying the distributional gradient
relation. -/
theorem inH1GraphRepresentative_mem {n : Nat}
    (u : ScalarDistribution n) (hu : InH1 u) :
    inH1GraphRepresentative u hu ∈ H1DistributionalGraphSubmodule n := by
  rw [mem_H1DistributionalGraphSubmodule_iff]
  intro i
  calc
    weakPartial i (complexL2ToDistribution n (inH1GraphRepresentative u hu).1) =
        weakPartial i u := by
      simpa [inH1GraphRepresentative] using
        congrArg (weakPartial i)
          (complexL2ToDistribution_l2RepresentativeOfInL2 u (h1_l2 hu))
    _ = complexL2ToDistribution n ((inH1GraphRepresentative u hu).2 i) := by
      simpa [inH1GraphRepresentative] using
        (complexL2ToDistribution_l2RepresentativeOfInL2
          (weakPartial i u) (h1_weakPartial_l2 hu i)).symm

/-- The value coordinate of the chosen H1 graph representative is exactly the original distribution. -/
theorem inH1GraphRepresentative_value {n : Nat}
    (u : ScalarDistribution n) (hu : InH1 u) :
    complexL2ToDistribution n (inH1GraphRepresentative u hu).1 = u := by
  exact complexL2ToDistribution_l2RepresentativeOfInL2 u (h1_l2 hu)

/-- Existential form of the Bessel-H1 to distributional-graph bridge. -/
theorem inH1_has_distributionalGraphRepresentative {n : Nat}
    (u : ScalarDistribution n) (hu : InH1 u) :
    ∃ x : H1ComplexGraphAmbient n,
      x ∈ H1DistributionalGraphSubmodule n ∧
      complexL2ToDistribution n x.1 = u := by
  exact ⟨inH1GraphRepresentative u hu,
    inH1GraphRepresentative_mem u hu,
    inH1GraphRepresentative_value u hu⟩

/-- Chosen L2 H(div) graph coordinates for an actual distributional H(div) field. -/
noncomputable def inHDivGraphRepresentative {n : Nat}
    (q : VectorDistribution n) (hq : InHDiv q) : HDivComplexGraphAmbient n :=
  (fun i => l2RepresentativeOfInL2 (q i) (hdiv_component_l2 hq i),
    l2RepresentativeOfInL2 (distributionalDivergence q) (hdiv_divergence_l2 hq))

/-- The vector distribution represented by the chosen H(div) graph coordinates is exactly `q`. -/
theorem inHDivGraphRepresentative_fieldDistribution {n : Nat}
    (q : VectorDistribution n) (hq : InHDiv q) :
    complexGraphFieldDistribution (inHDivGraphRepresentative q hq) = q := by
  funext i
  exact complexL2ToDistribution_l2RepresentativeOfInL2
    (q i) (hdiv_component_l2 hq i)

/-- The chosen graph coordinates of every `InHDiv` field satisfy the closed distributional
divergence relation. -/
theorem inHDivGraphRepresentative_mem {n : Nat}
    (q : VectorDistribution n) (hq : InHDiv q) :
    inHDivGraphRepresentative q hq ∈ HDivDistributionalGraphSubmodule n := by
  rw [mem_HDivDistributionalGraphSubmodule_iff]
  rw [inHDivGraphRepresentative_fieldDistribution q hq]
  exact (complexL2ToDistribution_l2RepresentativeOfInL2
    (distributionalDivergence q) (hdiv_divergence_l2 hq)).symm

/--
Representation equivalence for whole-space distributional H(div): `q` satisfies `InHDiv` exactly
when it is the field distribution of some L2 graph datum in the closed divergence relation.

This is an exact theorem about the distributional graph model.  It is distinct from the harder
statement that every such graph datum lies in the closure of the Schwartz graph core.
-/
theorem inHDiv_iff_exists_distributionalGraphRepresentative {n : Nat}
    (q : VectorDistribution n) :
    InHDiv q ↔
      ∃ x : HDivComplexGraphAmbient n,
        x ∈ HDivDistributionalGraphSubmodule n ∧
        complexGraphFieldDistribution x = q := by
  constructor
  · intro hq
    exact ⟨inHDivGraphRepresentative q hq,
      inHDivGraphRepresentative_mem q hq,
      inHDivGraphRepresentative_fieldDistribution q hq⟩
  · rintro ⟨x, hx, rfl⟩
    exact inHDiv_of_mem_distributionalGraph n x hx

end

end Continuum

end CACEFormal

import CACEFormal.GraphGreenPairing
import CACEFormal.BoxNormalTrace
import Mathlib.Topology.Algebra.Module.Basic

namespace CACEFormal

open Set Finset MeasureTheory
open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# v3.29 PDE/domain bridge

This module closes two pieces of the continuum identification problem without conflating
whole-space graph closure with a bounded-box boundary space.

* On boxes, the classical signed face flux is identified with the smooth Green volume
  pairing by the already machine-checked divergence theorem wrapper.
* On the whole space, a complex L² graph datum `(q,g)` is tied to the actual
  distributional `H(div)` predicate by requiring `div q = g` as tempered distributions.
  This relation is represented as the kernel of a continuous graph-defect map, so it is
  closed and is suitable for closure arguments.

The remaining bounded-domain theorem is deliberately separated: one still has to build
(or identify) the box graph closure and prove that its smooth core maps into the closed
relation below and that its continuous trace is the unique extension of classical face
flux.  No such equivalence is silently assumed here.
-/

/-- Complex whole-space `L²`, matching the codomain used by `ScalarDistribution`. -/
abbrev ComplexL2 (n : Nat) :=
  Lp ℂ 2 (volume : Measure (EuclideanDomain n))

/-- Complex graph data `(q,g)` intended to mean `g = div q`. -/
abbrev HDivComplexGraphAmbient (n : Nat) :=
  (Fin n → ComplexL2 n) × ComplexL2 n

/-- Canonical continuous embedding of `L²` into tempered distributions. -/
noncomputable def complexL2ToDistribution (n : Nat) :
    ComplexL2 n →L[ℂ] ScalarDistribution n :=
  MeasureTheory.Lp.toTemperedDistributionCLM ℂ volume 2

/-- Coordinate projection from complex H(div) graph data. -/
noncomputable def complexHDivFieldProj (n : Nat) (i : Fin n) :
    HDivComplexGraphAmbient n →L[ℂ] ComplexL2 n :=
  (ContinuousLinearMap.proj i).comp
    (ContinuousLinearMap.fst ℂ (Fin n → ComplexL2 n) (ComplexL2 n))

/-- Divergence-coordinate projection from complex H(div) graph data. -/
noncomputable def complexHDivDivProj (n : Nat) :
    HDivComplexGraphAmbient n →L[ℂ] ComplexL2 n :=
  ContinuousLinearMap.snd ℂ (Fin n → ComplexL2 n) (ComplexL2 n)

/-- Weak coordinate derivative as a continuous linear map on tempered distributions. -/
noncomputable def weakPartialCLM {n : Nat} (i : Fin n) :
    ScalarDistribution n →L[ℂ] ScalarDistribution n :=
  LineDeriv.lineDerivOpCLM ℂ (ScalarDistribution n) (basisVector i)

@[simp]
theorem weakPartialCLM_apply {n : Nat} (i : Fin n) (u : ScalarDistribution n) :
    weakPartialCLM i u = weakPartial i u := by
  rfl

/-- The distribution represented by the vector component of a graph datum. -/
noncomputable def complexGraphFieldDistribution {n : Nat}
    (x : HDivComplexGraphAmbient n) : VectorDistribution n :=
  fun i => complexL2ToDistribution n (x.1 i)

/--
Continuous defect `div(q) - g`.  Its kernel is precisely the graph of the
closed distributional divergence relation in the chosen L² coordinates.
-/
noncomputable def complexHDivGraphDefect (n : Nat) :
    HDivComplexGraphAmbient n →L[ℂ] ScalarDistribution n :=
  (∑ i : Fin n,
      (weakPartialCLM i).comp
        ((complexL2ToDistribution n).comp (complexHDivFieldProj n i))) -
    (complexL2ToDistribution n).comp (complexHDivDivProj n)

/-- Closed distributional H(div) graph relation in complex L² coordinates. -/
noncomputable def HDivDistributionalGraphSubmodule (n : Nat) :
    Submodule ℂ (HDivComplexGraphAmbient n) :=
  (complexHDivGraphDefect n).ker

/-- Membership in the graph relation is exactly the distributional equation `div q = g`. -/
theorem mem_HDivDistributionalGraphSubmodule_iff (n : Nat)
    (x : HDivComplexGraphAmbient n) :
    x ∈ HDivDistributionalGraphSubmodule n ↔
      distributionalDivergence (complexGraphFieldDistribution x) =
        complexL2ToDistribution n x.2 := by
  change complexHDivGraphDefect n x = 0 ↔ _
  simp [complexHDivGraphDefect, complexHDivFieldProj, complexHDivDivProj,
    complexGraphFieldDistribution, distributionalDivergence, weakPartial, sub_eq_zero]

/-- The distributional graph relation is topologically closed. -/
theorem isClosed_HDivDistributionalGraphSubmodule (n : Nat) :
    IsClosed (HDivDistributionalGraphSubmodule n : Set (HDivComplexGraphAmbient n)) := by
  change IsClosed ((complexHDivGraphDefect n) ⁻¹' ({0} : Set (ScalarDistribution n)))
  exact isClosed_singleton.preimage (complexHDivGraphDefect n).continuous

/-- Every complex L² function represents an actual `H^{0,2}` tempered distribution. -/
theorem complexL2ToDistribution_inL2 {n : Nat} (u : ComplexL2 n) :
    InL2 (complexL2ToDistribution n u) := by
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2
      (complexL2ToDistribution n u)
  rw [TemperedDistribution.memSobolev_zero_iff]
  exact ⟨u, rfl⟩

/--
A graph datum satisfying the closed distributional relation yields an actual
`InHDiv` vector distribution.  This is the first concrete graph-closure →
distributional-H(div) bridge theorem.
-/
theorem inHDiv_of_mem_distributionalGraph (n : Nat)
    (x : HDivComplexGraphAmbient n)
    (hx : x ∈ HDivDistributionalGraphSubmodule n) :
    InHDiv (complexGraphFieldDistribution x) := by
  constructor
  · intro i
    exact complexL2ToDistribution_inL2 (x.1 i)
  · rw [(mem_HDivDistributionalGraphSubmodule_iff n x).mp hx]
    exact complexL2ToDistribution_inL2 x.2

/--
Classical box trace agreement: the signed face-flux trace of the product field is
exactly the Green volume integral under the hypotheses of the smooth box theorem.
-/
theorem smoothBoxTrace_eq_greenVolume {n : Nat}
    {a b : BoxPoint n} (hle : a ≤ b)
    (q : BoxPoint n → BoxPoint n) (v : BoxPoint n → ℝ)
    (gradV : BoxPoint n → BoxPoint n) (divQ : BoxPoint n → ℝ)
    (F' : BoxPoint n → BoxPoint n →L[ℝ] BoxPoint n)
    (s : Set (BoxPoint n)) (hs : s.Countable)
    (Hc : ContinuousOn (scalarTimesVector v q) (Icc a b))
    (Hd : ∀ x ∈ (Set.pi univ fun i => Ioo (a i) (b i)) \ s,
      HasFDerivAt (scalarTimesVector v q) (F' x) x)
    (Hi : IntegrableOn
      (fun x => ∑ i : Fin (n + 1), F' x (Pi.single i (1 : ℝ)) i)
      (Icc a b))
    (hprod : ∀ x,
      (∑ i : Fin (n + 1), F' x (Pi.single i (1 : ℝ)) i) =
        smoothGreenVolumeTerm q v gradV divQ x) :
    smoothBoxNormalTrace a b (scalarTimesVector v q) =
      ∫ x in Icc a b, smoothGreenVolumeTerm q v gradV divQ x := by
  rw [← smoothNormalFluxPairing_eq_trace_product]
  exact (smoothBoxGreen hle q v gradV divQ F' s hs Hc Hd Hi hprod).symm

/--
Uniqueness principle for the bounded-box bridge: once two continuous traces agree with
classical face flux on the same dense smooth cores, they are the same trace everywhere.
-/
theorem normalTrace_eq_of_classicalCoreAgreement
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G H : BoundedGreenPairing V Q)
    (Q0 : Submodule ℝ Q) (V0 : Submodule ℝ V)
    (hQ : Dense (Q0 : Set Q)) (hV : Dense (V0 : Set V))
    (hclassical : ∀ q, q ∈ Q0 → ∀ v, v ∈ V0 →
      G.normalTrace q v = H.normalTrace q v) :
    G.normalTrace = H.normalTrace :=
  normalTrace_unique_of_dense_agreement G H Q0 V0 hQ hV hclassical

end

end Continuum

end CACEFormal

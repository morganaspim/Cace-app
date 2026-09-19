import CACEFormal.HDivGraphAnnihilator
import CACEFormal.OrthogonalClosure
import Mathlib.Analysis.InnerProductSpace.ProdL2

namespace CACEFormal

open Set
open scoped InnerProductSpace LineDeriv

namespace Continuum

noncomputable section

/-!
# Whole-space H(div) density reduction in the canonical L² graph Hilbert model

The existing H(div) graph coordinates use the ordinary product norm. That norm
has the same product topology as the L² product norm, but it is not itself
induced by a complex inner product. Orthogonal-complement arguments therefore
belong on the canonically equivalent WithLp 2 wrapper.

This module pulls the existing smooth core and closed distributional graph
through Mathlib's continuous linear equivalence. The only remaining analytic
obligation is that a distributional H(div) datum orthogonal to every pulled-back
Schwartz graph datum has reversed coordinates in the distributional H1 graph.
-/

/-- Canonical L² Hilbert wrapper for the finite vector component. -/
abbrev HDivComplexVectorHilbert (n : Nat) :=
  PiLp 2 (fun _ : Fin n => ComplexL2 n)

/-- Canonical L²-product Hilbert wrapper for the complex H(div) graph coordinates. -/
abbrev HDivComplexGraphHilbert (n : Nat) :=
  WithLp 2 (HDivComplexVectorHilbert n × ComplexL2 n)

/-- The finite-vector L² wrapper is continuously linearly equivalent to the
existing finite function-valued vector coordinates. -/
noncomputable def hdivVectorHilbertEquiv (n : Nat) :
    HDivComplexVectorHilbert n ≃L[ℂ] (Fin n → ComplexL2 n) :=
  PiLp.continuousLinearEquiv 2 ℂ (fun _ : Fin n => ComplexL2 n)

/-- Canonical continuous linear equivalence from the fully Hilbertized L² graph
wrapper to the existing graph-coordinate product. -/
noncomputable def hdivGraphHilbertEquiv (n : Nat) :
    HDivComplexGraphHilbert n ≃L[ℂ] HDivComplexGraphAmbient n :=
  (WithLp.prodContinuousLinearEquiv 2 ℂ
      (HDivComplexVectorHilbert n) (ComplexL2 n)).trans
    ((hdivVectorHilbertEquiv n).prodCongr
      (ContinuousLinearEquiv.refl ℂ (ComplexL2 n)))


theorem hdivGraphHilbertEquiv_apply (n : Nat)
    (x : HDivComplexGraphHilbert n) :
    hdivGraphHilbertEquiv n x =
      ((fun i => (WithLp.ofLp x).1 i), (WithLp.ofLp x).2) := by
  rfl

/-- The canonical graph Hilbert inner product is the sum of the coordinate L²
inner products plus the divergence-coordinate L² inner product. -/
theorem hdivGraphHilbert_inner_eq (n : Nat)
    (x y : HDivComplexGraphHilbert n) :
    ⟪x, y⟫_ℂ =
      (∑ i : Fin n,
        ⟪(hdivGraphHilbertEquiv n x).1 i,
          (hdivGraphHilbertEquiv n y).1 i⟫_ℂ) +
        ⟪(hdivGraphHilbertEquiv n x).2,
          (hdivGraphHilbertEquiv n y).2⟫_ℂ := by
  rw [WithLp.prod_inner_apply, PiLp.inner_apply]
  rfl

/-- Schwartz H(div) graph core pulled back to the Hilbert graph space. -/
noncomputable def ComplexHDivSmoothGraphCoreHilbert (n : Nat) :
    Submodule ℂ (HDivComplexGraphHilbert n) :=
  (ComplexHDivSmoothGraphCore n).comap
    (hdivGraphHilbertEquiv n).toLinearMap

/-- Closed distributional H(div) graph pulled back to the Hilbert graph space. -/
noncomputable def HDivDistributionalGraphSubmoduleHilbert (n : Nat) :
    Submodule ℂ (HDivComplexGraphHilbert n) :=
  (HDivDistributionalGraphSubmodule n).comap
    (hdivGraphHilbertEquiv n).toLinearMap

@[simp]
theorem mem_ComplexHDivSmoothGraphCoreHilbert_iff
    (n : Nat) (x : HDivComplexGraphHilbert n) :
    x ∈ ComplexHDivSmoothGraphCoreHilbert n ↔
      hdivGraphHilbertEquiv n x ∈ ComplexHDivSmoothGraphCore n := by
  rfl

@[simp]
theorem mem_HDivDistributionalGraphSubmoduleHilbert_iff
    (n : Nat) (x : HDivComplexGraphHilbert n) :
    x ∈ HDivDistributionalGraphSubmoduleHilbert n ↔
      hdivGraphHilbertEquiv n x ∈ HDivDistributionalGraphSubmodule n := by
  rfl

/-- The pulled-back smooth core lies in the pulled-back distributional graph. -/
theorem ComplexHDivSmoothGraphCoreHilbert_le_distributional
    (n : Nat) :
    ComplexHDivSmoothGraphCoreHilbert n ≤
      HDivDistributionalGraphSubmoduleHilbert n := by
  intro x hx
  exact ComplexHDivSmoothGraphCore_le_distributional n hx

/-- The pulled-back distributional graph is closed in the L² product topology. -/
theorem isClosed_HDivDistributionalGraphSubmoduleHilbert
    (n : Nat) :
    IsClosed
      (HDivDistributionalGraphSubmoduleHilbert n :
        Set (HDivComplexGraphHilbert n)) := by
  change IsClosed
    ((hdivGraphHilbertEquiv n) ⁻¹'
      (HDivDistributionalGraphSubmodule n :
        Set (HDivComplexGraphAmbient n)))
  exact (isClosed_HDivDistributionalGraphSubmodule n).preimage
    (hdivGraphHilbertEquiv n).continuous

/-- A smooth Schwartz H(div) graph datum pulled back through the Hilbert
equivalence lies in the pulled-back smooth core. -/
theorem smoothComplexHDivGraphPullback_mem_core
    (n : Nat) (q : ComplexSmoothVector n) :
    (hdivGraphHilbertEquiv n).symm (smoothComplexHDivGraphMap n q) ∈
      ComplexHDivSmoothGraphCoreHilbert n := by
  rw [mem_ComplexHDivSmoothGraphCoreHilbert_iff]
  rw [(hdivGraphHilbertEquiv n).apply_symm_apply]
  exact ⟨q, rfl⟩

/-- Orthogonality to the pulled-back smooth core can be tested directly on
every pulled-back Schwartz H(div) graph datum. -/
theorem inner_smoothHDivGraphPullback_eq_zero_of_mem_orthogonal
    (n : Nat) (x : HDivComplexGraphHilbert n)
    (hx : x ∈ (ComplexHDivSmoothGraphCoreHilbert n)ᗮ)
    (q : ComplexSmoothVector n) :
    ⟪(hdivGraphHilbertEquiv n).symm (smoothComplexHDivGraphMap n q), x⟫_ℂ = 0 := by
  exact
    ((ComplexHDivSmoothGraphCoreHilbert n).mem_orthogonal x).1 hx _
      (smoothComplexHDivGraphPullback_mem_core n q)

/-- Specializing the smooth-core orthogonality relation to a Schwartz vector
with one active coordinate isolates the weak derivative pairing in coordinate `i`. -/
theorem inner_singleCoordinateSchwartzGraph_eq_zero_of_mem_orthogonal
    (n : Nat) (x : HDivComplexGraphHilbert n)
    (hx : x ∈ (ComplexHDivSmoothGraphCoreHilbert n)ᗮ)
    (i : Fin n) (φ : ComplexSmoothScalar n) :
    ⟪schwartzComplexL2 n φ, (hdivGraphHilbertEquiv n x).1 i⟫_ℂ +
        ⟪schwartzComplexL2 n (∂_{basisVector i} φ),
          (hdivGraphHilbertEquiv n x).2⟫_ℂ = 0 := by
  classical
  let q : ComplexSmoothVector n := fun j => if j = i then φ else 0
  have hzero :=
    inner_smoothHDivGraphPullback_eq_zero_of_mem_orthogonal n x hx q
  rw [hdivGraphHilbert_inner_eq] at hzero
  simp [q, smoothComplexHDivGraphMap, apply_ite] at hzero
  have hfirst :
      (∑ j : Fin n,
        ⟪if j = i then schwartzComplexL2 n φ else 0,
          (hdivGraphHilbertEquiv n x).1 j⟫_ℂ) =
        ⟪schwartzComplexL2 n φ,
          (hdivGraphHilbertEquiv n x).1 i⟫_ℂ := by
    rw [Finset.sum_eq_single i] <;> simp +contextual
  rw [hfirst] at hzero
  exact hzero

/-- Pointwise complex conjugation preserves Schwartz class.  We deliberately
view conjugation as an ℝ-linear continuous map, since it is not ℂ-linear. -/
noncomputable def schwartzConj (n : Nat) :
    ComplexSmoothScalar n →L[ℝ] ComplexSmoothScalar n :=
  SchwartzMap.postcompCLM
    (E := EuclideanDomain n)
    (Complex.conjCLE : ℂ →L[ℝ] ℂ)

@[simp]
theorem schwartzConj_apply (n : Nat)
    (φ : ComplexSmoothScalar n) (y : EuclideanDomain n) :
    schwartzConj n φ y = Complex.conjCLE (φ y) := by
  rfl

/-- Real-linear conjugation commutes with real directional derivatives. -/
theorem lineDeriv_schwartzConj
    (n : Nat) (v : EuclideanDomain n) (φ : ComplexSmoothScalar n) :
    ∂_{v} (schwartzConj n φ) =
      schwartzConj n (∂_{v} φ) := by
  ext y
  simp only [SchwartzMap.lineDerivOp_apply_eq_fderiv, schwartzConj_apply]
  change
    fderiv ℝ ((Complex.conjCLE : ℂ → ℂ) ∘ φ) y v =
      Complex.conjCLE (fderiv ℝ φ y v)
  rw [fderiv_comp y Complex.conjCLE.differentiableAt φ.differentiableAt]
  simp

/-- L² inner product against the conjugated Schwartz embedding is exactly
evaluation of the associated tempered distribution on the original Schwartz test. -/
theorem inner_schwartzConjL2_eq_distribution_apply
    (n : Nat) (φ : ComplexSmoothScalar n) (u : ComplexL2 n) :
    ⟪schwartzComplexL2 n (schwartzConj n φ), u⟫_ℂ =
      complexL2ToDistribution n u φ := by
  change
    ⟪(schwartzConj n φ).toLp 2
        (MeasureTheory.volume : MeasureTheory.Measure (EuclideanDomain n)), u⟫_ℂ =
      MeasureTheory.Lp.toTemperedDistribution u φ
  rw [MeasureTheory.L2.inner_def,
    MeasureTheory.Lp.toTemperedDistribution_apply]
  apply integral_congr_ae
  filter_upwards
      [(schwartzConj n φ).coeFn_toLp 2
        (MeasureTheory.volume : MeasureTheory.Measure (EuclideanDomain n))] with y hy
  rw [hy]
  simp [schwartzConj_apply, RCLike.inner_apply, smul_eq_mul, mul_comm]

/-- Orthogonality to the Schwartz H(div) graph core forces the divergence
coordinate to have each field coordinate as its weak derivative. -/
theorem weakPartial_divSlot_eq_fieldSlot_of_mem_orthogonal
    (n : Nat) (x : HDivComplexGraphHilbert n)
    (hx : x ∈ (ComplexHDivSmoothGraphCoreHilbert n)ᗮ)
    (i : Fin n) :
    weakPartial i
        (complexL2ToDistribution n (hdivGraphHilbertEquiv n x).2) =
      complexL2ToDistribution n ((hdivGraphHilbertEquiv n x).1 i) := by
  ext φ
  have hzero :=
    inner_singleCoordinateSchwartzGraph_eq_zero_of_mem_orthogonal
      n x hx i (schwartzConj n φ)
  rw [lineDeriv_schwartzConj] at hzero
  rw [inner_schwartzConjL2_eq_distribution_apply,
    inner_schwartzConjL2_eq_distribution_apply] at hzero
  change
    (∂_{basisVector i}
      (complexL2ToDistribution n (hdivGraphHilbertEquiv n x).2)) φ =
      complexL2ToDistribution n ((hdivGraphHilbertEquiv n x).1 i) φ
  rw [TemperedDistribution.lineDerivOp_apply_apply]
  simpa using (eq_neg_of_add_eq_zero_left hzero).symm

/-- The orthogonality criterion needed by the density reduction is automatic:
the reversed H(div) coordinates satisfy the distributional H¹ graph relation. -/
theorem reversedHDivGraph_mem_H1_of_mem_orthogonal
    (n : Nat) (x : HDivComplexGraphHilbert n)
    (hx : x ∈ (ComplexHDivSmoothGraphCoreHilbert n)ᗮ) :
    reversedHDivGraph (hdivGraphHilbertEquiv n x) ∈
      H1DistributionalGraphSubmodule n := by
  rw [mem_H1DistributionalGraphSubmodule_iff]
  intro i
  simpa [reversedHDivGraph] using
    weakPartial_divSlot_eq_fieldSlot_of_mem_orthogonal n x hx i

/-- Exact remaining analytic criterion for unconditional whole-space H(div)
graph density. Orthogonality is stated only in the legitimate L²-product
Hilbert structure. -/
def HDivHilbertOrthogonalReversedH1Criterion (n : Nat) : Prop :=
  ∀ x : HDivComplexGraphHilbert n,
    x ∈ HDivDistributionalGraphSubmoduleHilbert n →
    x ∈ (ComplexHDivSmoothGraphCoreHilbert n)ᗮ →
    reversedHDivGraph (hdivGraphHilbertEquiv n x) ∈
      H1DistributionalGraphSubmodule n

/-- The relative orthogonal complement is trivial under the analytic criterion. -/
theorem complexHDivHilbert_relativeOrthogonal_eq_bot_of_reversedH1
    (n : Nat) (hcriterion : HDivHilbertOrthogonalReversedH1Criterion n) :
    (ComplexHDivSmoothGraphCoreHilbert n)ᗮ ⊓
        HDivDistributionalGraphSubmoduleHilbert n = ⊥ := by
  apply le_antisymm
  · intro x hx
    have hxGraph :
        hdivGraphHilbertEquiv n x ∈
          HDivDistributionalGraphSubmodule n :=
      (mem_HDivDistributionalGraphSubmoduleHilbert_iff n x).mp hx.2
    have hImageZero :
        hdivGraphHilbertEquiv n x = 0 :=
      hdivGraph_eq_zero_of_reversedH1 n
        (hdivGraphHilbertEquiv n x)
        hxGraph
        (hcriterion x hx.2 hx.1)
    have hxZero : x = 0 := by
      apply (hdivGraphHilbertEquiv n).injective
      simpa using hImageZero
    simpa [hxZero]
  · exact bot_le

/-- H(div) graph density in the canonical L² Hilbert model is reduced to the
single explicit analytic criterion above. -/
theorem complexSmoothGraphHilbertClosure_eq_distributional_of_orthogonal_reversedH1
    (n : Nat) (hcriterion : HDivHilbertOrthogonalReversedH1Criterion n) :
    (ComplexHDivSmoothGraphCoreHilbert n).topologicalClosure =
      HDivDistributionalGraphSubmoduleHilbert n := by
  exact submodule_topologicalClosure_eq_of_relativeOrthogonal_eq_bot
    (ComplexHDivSmoothGraphCoreHilbert n)
    (HDivDistributionalGraphSubmoduleHilbert n)
    (ComplexHDivSmoothGraphCoreHilbert_le_distributional n)
    (isClosed_HDivDistributionalGraphSubmoduleHilbert n)
    (complexHDivHilbert_relativeOrthogonal_eq_bot_of_reversedH1 n hcriterion)

/-- Pointwise form, convenient for proving the analytic bridge from Schwartz tests. -/
theorem complexSmoothGraphHilbertClosure_eq_distributional_of_orthogonal_pointwise
    (n : Nat)
    (hrev : ∀ x : HDivComplexGraphHilbert n,
      x ∈ HDivDistributionalGraphSubmoduleHilbert n →
      x ∈ (ComplexHDivSmoothGraphCoreHilbert n)ᗮ →
      reversedHDivGraph (hdivGraphHilbertEquiv n x) ∈
        H1DistributionalGraphSubmodule n) :
    (ComplexHDivSmoothGraphCoreHilbert n).topologicalClosure =
      HDivDistributionalGraphSubmoduleHilbert n :=
  complexSmoothGraphHilbertClosure_eq_distributional_of_orthogonal_reversedH1
    n hrev

end

end Continuum

end CACEFormal

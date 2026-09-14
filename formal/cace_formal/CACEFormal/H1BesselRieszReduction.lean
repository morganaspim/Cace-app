import CACEFormal.DistributionalGraphRepresentatives

namespace CACEFormal

open Set Finset MeasureTheory
open scoped BigOperators LineDeriv SchwartzMap Real

namespace Continuum

noncomputable section

/-!
# v3.30 Bessel/Riesz reduction for the H1 converse

The remaining converse in the scalar bridge is the classical implication

`u ∈ L2` and `∂_i u ∈ L2` for every coordinate `i`  ==>  `u ∈ H1`.

Rather than attacking the weighted Fourier L2 estimate monolithically, this module factors the proof
through bounded Bessel/Riesz multipliers.  The only remaining analytic identity after these lemmas is
the exact reconstruction of `u` from its low-frequency Bessel term and the coordinate Riesz terms.

This is useful beyond this one theorem: each filtered derivative term is independently shown to lie
in H1 using Mathlib's bounded Fourier-multiplier theorem.
-/

/-- Coordinate Bessel/Riesz symbol `xi_i / sqrt(1 + |xi|^2)`. -/
noncomputable def h1RieszSymbol {n : Nat} (i : Fin n) : EuclideanDomain n → ℂ :=
  fun x => Complex.ofReal <|
    inner ℝ x (basisVector i) * (1 + ‖x‖ ^ 2) ^ (-1 / 2 : ℝ)

/-- Generic estimate used by the Sobolev derivative theorem: the Bessel-normalized directional
frequency is bounded by the norm of the direction. -/
theorem besselRieszSymbol_norm_le {n : Nat}
    (m x : EuclideanDomain n) :
    ‖Complex.ofReal
      (inner ℝ x m * (1 + ‖x‖ ^ 2) ^ (-1 / 2 : ℝ))‖ ≤ ‖m‖ := by
  apply le_of_sq_le_sq _ (by positivity)
  simp only [Complex.ofReal_mul, Complex.norm_mul, Complex.norm_real,
    Real.norm_eq_abs, mul_pow]
  have h₁ : |(1 + ‖x‖ ^ 2) ^ (-1 / 2 : ℝ)| ^ 2 = (1 + ‖x‖ ^ 2)⁻¹ := by
    field_simp
    norm_cast
    rw [Real.rpow_neg (by positivity), sq_abs, inv_pow]
    field_simp
    calc
      _ = ((1 + ‖x‖ ^ 2) ^ (1 / 2 : ℝ)) ^ (2 : ℝ) := by
        rw [← Real.rpow_mul (by positivity)]
        simp
      _ = _ := by simp
  have h₂ : |inner ℝ x m| ^ 2 ≤ ‖m‖ ^ 2 * (1 + ‖x‖ ^ 2) := by
    grw [abs_real_inner_le_norm]
    rw [mul_pow, mul_comm]
    gcongr
    simp
  grw [h₁, h₂]
  apply le_of_eq
  field_simp

/-- Every coordinate Riesz symbol is bounded by one. -/
theorem h1RieszSymbol_norm_le_one {n : Nat} (i : Fin n) (x : EuclideanDomain n) :
    ‖h1RieszSymbol i x‖ ≤ 1 := by
  simpa [h1RieszSymbol, basisVector] using
    (besselRieszSymbol_norm_le (basisVector i) x)

/-- The coordinate Riesz symbol has temperate growth, so it defines a Fourier multiplier on tempered
distributions. -/
theorem h1RieszSymbol_hasTemperateGrowth {n : Nat} (i : Fin n) :
    (h1RieszSymbol i).HasTemperateGrowth := by
  unfold h1RieszSymbol
  fun_prop

/-- An L2 distribution becomes H1 after applying the order `-2` Bessel potential. -/
theorem besselPotential_neg_two_inH1_of_inL2 {n : Nat}
    {u : ScalarDistribution n} (hu : InL2 u) :
    InH1 (TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-2) u) := by
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2
      (TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-2) u)
  have huNegOne : TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (-1 : ℝ) 2 u := by
    exact TemperedDistribution.MemSobolev.mono
      (E := EuclideanDomain n) (F := ℂ) (s := (0 : ℝ)) (s' := (-1 : ℝ))
      (by norm_num) hu
  rw [TemperedDistribution.memSobolev_besselPotential_iff]
  simpa using huNegOne

/-- If one weak coordinate derivative is L2, its order `-1` Bessel potential is H1. -/
theorem besselPotential_neg_one_weakPartial_inH1_of_inL2 {n : Nat}
    {u : ScalarDistribution n} (i : Fin n) (hdu : InL2 (weakPartial i u)) :
    InH1 (TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-1)
      (weakPartial i u)) := by
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2
      (TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-1)
        (weakPartial i u))
  rw [TemperedDistribution.memSobolev_besselPotential_iff]
  simpa using hdu

/-- Applying the bounded coordinate Riesz multiplier to the Bessel-smoothed weak derivative preserves
H1. -/
theorem rieszFiltered_weakPartial_inH1_of_inL2 {n : Nat}
    {u : ScalarDistribution n} (i : Fin n) (hdu : InL2 (weakPartial i u)) :
    InH1
      (TemperedDistribution.fourierMultiplierCLM ℂ (h1RieszSymbol i)
        (TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-1)
          (weakPartial i u))) := by
  have hbase := besselPotential_neg_one_weakPartial_inH1_of_inL2 i hdu
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2
      (TemperedDistribution.fourierMultiplierCLM ℂ (h1RieszSymbol i)
        (TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-1)
          (weakPartial i u)))
  exact hbase.fourierMultiplierCLM_of_bounded
    (h1RieszSymbol_hasTemperateGrowth i)
    ⟨1, h1RieszSymbol_norm_le_one i⟩

/-- Sum of the normalized coordinate corrections appearing in the H1 reconstruction. -/
noncomputable def h1RieszCorrection {n : Nat} (u : ScalarDistribution n) :
    ScalarDistribution n :=
  (2 * π * Complex.I)⁻¹ •
    ∑ i : Fin n,
      TemperedDistribution.fourierMultiplierCLM ℂ (h1RieszSymbol i)
        (TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-1)
          (weakPartial i u))

/-- L2 control of every weak coordinate derivative makes the complete Riesz correction H1. -/
theorem h1RieszCorrection_inH1 {n : Nat} {u : ScalarDistribution n}
    (hdu : ∀ i : Fin n, InL2 (weakPartial i u)) :
    InH1 (h1RieszCorrection u) := by
  change h1RieszCorrection u ∈ H1Submodule n
  unfold h1RieszCorrection
  apply (H1Submodule n).smul_mem
  apply Submodule.sum_mem
  intro i hi
  exact rieszFiltered_weakPartial_inH1_of_inL2 i (hdu i)

/--
Once the exact Bessel/Riesz reconstruction identity is available, the standard weak-derivative
characterization of H1 follows immediately from the bounded-multiplier lemmas above.

This theorem deliberately exposes only the reconstruction identity as the remaining hypothesis; all
Sobolev-order lifting, boundedness, and finite-sum closure are discharged here.
-/
theorem inH1_of_besselRiesz_reconstruction {n : Nat} {u : ScalarDistribution n}
    (hu : InL2 u)
    (hdu : ∀ i : Fin n, InL2 (weakPartial i u))
    (hreconstruct :
      u = TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-2) u +
        h1RieszCorrection u) :
    InH1 u := by
  rw [hreconstruct]
  exact (besselPotential_neg_two_inH1_of_inL2 hu).add
    (h1RieszCorrection_inH1 hdu)

end

end Continuum

end CACEFormal

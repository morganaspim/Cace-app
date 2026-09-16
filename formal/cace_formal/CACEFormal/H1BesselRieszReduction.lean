import CACEFormal.DistributionalGraphRepresentatives

namespace CACEFormal

open Set Finset MeasureTheory FourierTransform
open scoped BigOperators LineDeriv SchwartzMap Real

namespace Continuum

noncomputable section

/-!
# H1 Bessel/Riesz reconstruction

The scalar converse is the classical implication

`u ∈ L2` and `∂_i u ∈ L2` for every coordinate `i`  ==>  `u ∈ H1`.

The proof is factored through bounded Bessel/Riesz multipliers.  The low-frequency term has Fourier
symbol `1 / (1 + |xi|^2)`.  The coordinate Riesz correction has symbol
`|xi|^2 / (1 + |xi|^2)`.  Their pointwise sum is exactly one, so the previously exposed
reconstruction hypothesis is now discharged inside Lean.
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
  convert huNegOne using 1 <;> norm_num

/-- If one weak coordinate derivative is L2, its order `-1` Bessel potential is H1. -/
theorem besselPotential_neg_one_weakPartial_inH1_of_inL2 {n : Nat}
    {u : ScalarDistribution n} (i : Fin n) (hdu : InL2 (weakPartial i u)) :
    InH1 (TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-1)
      (weakPartial i u)) := by
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 (weakPartial i u) at hdu
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2
      (TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-1)
        (weakPartial i u))
  rw [TemperedDistribution.memSobolev_besselPotential_iff]
  convert hdu using 1 <;> norm_num

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

/-- Fourier symbol of the order `-2` Bessel low-frequency term. -/
noncomputable def h1BesselLowSymbol {n : Nat} : EuclideanDomain n → ℂ :=
  fun x => Complex.ofReal ((1 + ‖x‖ ^ 2) ^ (-1 : ℝ))

/-- Fourier symbol of the total coordinate Riesz correction. -/
noncomputable def h1RieszEnergySymbol {n : Nat} : EuclideanDomain n → ℂ :=
  fun x => ∑ i : Fin n, h1RieszSymbol i x * h1RieszSymbol i x

/-- The low-frequency symbol has temperate growth. -/
theorem h1BesselLowSymbol_hasTemperateGrowth {n : Nat} :
    (h1BesselLowSymbol (n := n)).HasTemperateGrowth := by
  unfold h1BesselLowSymbol
  fun_prop

/-- The summed squared Riesz symbol has temperate growth. -/
theorem h1RieszEnergySymbol_hasTemperateGrowth {n : Nat} :
    (h1RieszEnergySymbol (n := n)).HasTemperateGrowth := by
  unfold h1RieszEnergySymbol h1RieszSymbol
  fun_prop

/-- Canonical-coordinate Parseval identity used by the reconstruction symbol calculation. -/
theorem sum_sq_inner_basisVector {n : Nat} (x : EuclideanDomain n) :
    (∑ i : Fin n, (inner ℝ x (basisVector i)) ^ 2) = ‖x‖ ^ 2 := by
  rw [EuclideanSpace.real_norm_sq_eq]
  apply Finset.sum_congr rfl
  intro i hi
  simp [basisVector, EuclideanSpace.inner_single_right]

/-- Squaring the order `-1/2` Bessel weight produces the order `-1` weight. -/
theorem besselWeight_neg_half_sq {n : Nat} (x : EuclideanDomain n) :
    ((1 + ‖x‖ ^ 2) ^ (-1 / 2 : ℝ)) ^ 2 =
      (1 + ‖x‖ ^ 2) ^ (-1 : ℝ) := by
  rw [← Real.rpow_mul_natCast (by positivity)]
  norm_num

/-- The low-frequency Bessel symbol and the summed Riesz-energy symbol form an exact partition of
unity. -/
theorem h1BesselLowSymbol_add_h1RieszEnergySymbol {n : Nat} (x : EuclideanDomain n) :
    h1BesselLowSymbol x + h1RieszEnergySymbol x = 1 := by
  have hreal :
      (1 + ‖x‖ ^ 2) ^ (-1 : ℝ) +
          ∑ i : Fin n,
            (inner ℝ x (basisVector i) * (1 + ‖x‖ ^ 2) ^ (-1 / 2 : ℝ)) *
              (inner ℝ x (basisVector i) * (1 + ‖x‖ ^ 2) ^ (-1 / 2 : ℝ)) =
        (1 : ℝ) := by
    calc
      (1 + ‖x‖ ^ 2) ^ (-1 : ℝ) +
          ∑ i : Fin n,
            (inner ℝ x (basisVector i) * (1 + ‖x‖ ^ 2) ^ (-1 / 2 : ℝ)) *
              (inner ℝ x (basisVector i) * (1 + ‖x‖ ^ 2) ^ (-1 / 2 : ℝ))
          = (1 + ‖x‖ ^ 2) ^ (-1 : ℝ) +
              (∑ i : Fin n, (inner ℝ x (basisVector i)) ^ 2) *
                ((1 + ‖x‖ ^ 2) ^ (-1 / 2 : ℝ)) ^ 2 := by
            congr 1
            rw [Finset.sum_mul]
            apply Finset.sum_congr rfl
            intro i hi
            ring
      _ = (1 + ‖x‖ ^ 2) ^ (-1 : ℝ) +
            ‖x‖ ^ 2 * (1 + ‖x‖ ^ 2) ^ (-1 : ℝ) := by
            rw [sum_sq_inner_basisVector x, besselWeight_neg_half_sq x]
      _ = 1 := by
            rw [Real.rpow_neg (by positivity)]
            norm_num
            field_simp
  unfold h1BesselLowSymbol h1RieszEnergySymbol h1RieszSymbol
  have hcomplex := congrArg Complex.ofReal hreal
  simpa only [Complex.ofReal_add, Complex.ofReal_mul, Complex.ofReal_sum,
    Complex.ofReal_one] using hcomplex

/-- The order `-2` Bessel potential is exactly the multiplier with the low-frequency symbol. -/
theorem besselPotential_neg_two_eq_h1BesselLowMultiplier {n : Nat}
    (u : ScalarDistribution n) :
    TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-2) u =
      TemperedDistribution.fourierMultiplierCLM ℂ (h1BesselLowSymbol (n := n)) u := by
  unfold TemperedDistribution.besselPotential h1BesselLowSymbol
  apply congrArg
    (fun g : EuclideanDomain n → ℂ =>
      TemperedDistribution.fourierMultiplierCLM ℂ g u)
  funext x
  norm_num

/-- The existing finite Riesz correction is exactly the Fourier multiplier with symbol
`|xi|^2 / (1 + |xi|^2)`. -/
theorem h1RieszCorrection_eq_energyMultiplier {n : Nat}
    (u : ScalarDistribution n) :
    h1RieszCorrection u =
      TemperedDistribution.fourierMultiplierCLM ℂ (h1RieszEnergySymbol (n := n)) u := by
  have hpi : (Real.pi : ℂ) ≠ 0 := by
    exact_mod_cast Real.pi_ne_zero
  have hI : Complex.I ≠ 0 := Complex.I_ne_zero
  have halpha : (2 * (Real.pi : ℂ) * Complex.I) ≠ 0 := by
    exact mul_ne_zero (mul_ne_zero (by norm_num) hpi) hI
  have hder : ∀ i : Fin n,
      TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-1)
          (weakPartial i u) =
        (2 * (Real.pi : ℂ) * Complex.I) •
          TemperedDistribution.fourierMultiplierCLM ℂ (h1RieszSymbol i) u := by
    intro i
    change
      TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-1)
          (∂_{basisVector i} u) =
        (2 * (Real.pi : ℂ) * Complex.I) •
          TemperedDistribution.fourierMultiplierCLM ℂ
            (fun x => Complex.ofReal <|
              inner ℝ x (basisVector i) * (1 + ‖x‖ ^ 2) ^ (-1 / 2 : ℝ)) u
    exact TemperedDistribution.besselPotential_neg_one_lineDerivOp_eq
      (E := EuclideanDomain n) (F := ℂ) (m := basisVector i) u
  unfold h1RieszCorrection
  simp_rw [hder, map_smul]
  rw [← Finset.smul_sum, smul_smul, inv_mul_cancel₀ halpha, one_smul]
  simp_rw [TemperedDistribution.fourierMultiplierCLM_fourierMultiplierCLM_apply
    (h1RieszSymbol_hasTemperateGrowth (n := n) _)
    (h1RieszSymbol_hasTemperateGrowth (n := n) _)]
  have hg : ∀ i ∈ (Finset.univ : Finset (Fin n)),
      ((h1RieszSymbol i) * (h1RieszSymbol i)).HasTemperateGrowth := by
    intro i hi
    exact (h1RieszSymbol_hasTemperateGrowth i).mul
      (h1RieszSymbol_hasTemperateGrowth i)
  have hsum := congrArg
    (fun T : ScalarDistribution n →L[ℂ] ScalarDistribution n => T u)
    (TemperedDistribution.fourierMultiplierCLM_sum
      (F := ℂ) (s := (Finset.univ : Finset (Fin n)))
      (g := fun i => (h1RieszSymbol i) * (h1RieszSymbol i)) hg)
  change
    (∑ i : Fin n,
      TemperedDistribution.fourierMultiplierCLM ℂ
        ((h1RieszSymbol i) * (h1RieszSymbol i)) u) =
      TemperedDistribution.fourierMultiplierCLM ℂ
        (fun x => ∑ i : Fin n, h1RieszSymbol i x * h1RieszSymbol i x) u
  simpa only [Pi.mul_apply, _root_.sum_apply] using hsum.symm

/-- Exact Bessel/Riesz reconstruction of every scalar tempered distribution.  No Sobolev or L2
hypothesis is needed for this operator identity. -/
theorem besselRiesz_reconstruction {n : Nat} (u : ScalarDistribution n) :
    u = TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-2) u +
      h1RieszCorrection u := by
  rw [besselPotential_neg_two_eq_h1BesselLowMultiplier,
    h1RieszCorrection_eq_energyMultiplier]
  have hsymbols :
      h1BesselLowSymbol (n := n) + h1RieszEnergySymbol (n := n) =
        (fun _ : EuclideanDomain n => (1 : ℂ)) := by
    funext x
    exact h1BesselLowSymbol_add_h1RieszEnergySymbol x
  have hfourier :
      TemperedDistribution.smulLeftCLM ℂ (h1BesselLowSymbol (n := n)) (𝓕 u) +
          TemperedDistribution.smulLeftCLM ℂ (h1RieszEnergySymbol (n := n)) (𝓕 u) =
        𝓕 u := by
    change
      (TemperedDistribution.smulLeftCLM ℂ (h1BesselLowSymbol (n := n)) +
        TemperedDistribution.smulLeftCLM ℂ (h1RieszEnergySymbol (n := n))) (𝓕 u) =
          𝓕 u
    rw [← TemperedDistribution.smulLeftCLM_add
      (h1BesselLowSymbol_hasTemperateGrowth (n := n))
      (h1RieszEnergySymbol_hasTemperateGrowth (n := n)), hsymbols]
    simp
  rw [TemperedDistribution.fourierMultiplierCLM_apply,
    TemperedDistribution.fourierMultiplierCLM_apply]
  calc
    u = 𝓕⁻ (𝓕 u) := (FourierTransform.fourierInv_fourier_eq u).symm
    _ = 𝓕⁻
        (TemperedDistribution.smulLeftCLM ℂ (h1BesselLowSymbol (n := n)) (𝓕 u) +
          TemperedDistribution.smulLeftCLM ℂ (h1RieszEnergySymbol (n := n)) (𝓕 u)) := by
        rw [hfourier]
    _ = 𝓕⁻ (TemperedDistribution.smulLeftCLM ℂ (h1BesselLowSymbol (n := n)) (𝓕 u)) +
        𝓕⁻ (TemperedDistribution.smulLeftCLM ℂ (h1RieszEnergySymbol (n := n)) (𝓕 u)) := by
        exact fourierInv_add _ _

/-- Weak-derivative characterization of H1: an L2 tempered distribution whose coordinate weak
derivatives are all L2 belongs to Mathlib's Bessel-potential H1. -/
theorem inH1_of_besselRiesz_reconstruction {n : Nat} {u : ScalarDistribution n}
    (hu : InL2 u)
    (hdu : ∀ i : Fin n, InL2 (weakPartial i u)) :
    InH1 u := by
  rw [besselRiesz_reconstruction u]
  exact (besselPotential_neg_two_inH1_of_inL2 hu).add
    (h1RieszCorrection_inH1 hdu)

/-- Descriptive alias for the unconditional weak-derivative H1 converse. -/
theorem inH1_of_inL2_weakPartial_inL2 {n : Nat} {u : ScalarDistribution n}
    (hu : InL2 u)
    (hdu : ∀ i : Fin n, InL2 (weakPartial i u)) :
    InH1 u :=
  inH1_of_besselRiesz_reconstruction hu hdu

end

end Continuum

end CACEFormal

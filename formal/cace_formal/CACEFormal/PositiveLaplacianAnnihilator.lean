import CACEFormal.H1BesselRieszReduction
import Mathlib.Analysis.Distribution.FourierMultiplier

namespace CACEFormal

open Set Finset MeasureTheory FourierTransform
open scoped BigOperators LineDeriv SchwartzMap Real

namespace Continuum

noncomputable section

/-!
# Positive-Laplacian annihilator

A key analytic sublemma for the unconditional whole-space H(div) density proof
is that the distributional Laplacian has no nonzero tempered eigenvector with
positive eigenvalue one:

`Δ u = u  ==>  u = 0`.

The proof below is purely Fourier-multiplier algebra.  It builds the exact
partition

`1 / (1 + c|ξ|²) + c|ξ|² / (1 + c|ξ|²) = 1`

with `c = (2π)²`, then uses Mathlib's exact Fourier representation of the
distributional Laplacian.  No L2 integration-by-parts or density assumption is
used in this lemma.
-/

/-- Fourier symbol `|ξ|²`. -/
noncomputable def laplacianFrequencySqSymbol {n : Nat} :
    EuclideanDomain n → ℂ :=
  fun x => Complex.ofReal (‖x‖ ^ 2)

/-- Continuous linear frequency scaling `x ↦ (2π)x`.  Writing the resolvent
through this map lets us reuse Mathlib's proved Bessel-potential temperate-growth
theorem instead of asking automation to reason about a reciprocal. -/
noncomputable def positiveLaplacianScale {n : Nat} :
    EuclideanDomain n →L[ℝ] EuclideanDomain n :=
  (2 * Real.pi) • ContinuousLinearMap.id ℝ (EuclideanDomain n)

/-- Low-frequency inverse of `1 + (2π)²|ξ|²`. -/
noncomputable def positiveLaplacianLowSymbol {n : Nat} :
    EuclideanDomain n → ℂ :=
  fun x => Complex.ofReal <|
    (1 + (2 * Real.pi) ^ 2 * ‖x‖ ^ 2) ^ (-1 : ℝ)

/-- Complementary positive-frequency part. -/
noncomputable def positiveLaplacianEnergySymbol {n : Nat} :
    EuclideanDomain n → ℂ :=
  (fun _ : EuclideanDomain n =>
      Complex.ofReal ((2 * Real.pi) ^ 2)) *
    (laplacianFrequencySqSymbol (n := n) *
      positiveLaplacianLowSymbol (n := n))

theorem laplacianFrequencySqSymbol_hasTemperateGrowth {n : Nat} :
    (laplacianFrequencySqSymbol (n := n)).HasTemperateGrowth := by
  unfold laplacianFrequencySqSymbol
  fun_prop

theorem positiveLaplacianLowSymbol_hasTemperateGrowth {n : Nat} :
    (positiveLaplacianLowSymbol (n := n)).HasTemperateGrowth := by
  have hbase :
      (fun y : EuclideanDomain n => (1 + ‖y‖ ^ 2) ^ (-1 : ℝ)).HasTemperateGrowth :=
    Function.hasTemperateGrowth_one_add_norm_sq_rpow
      (EuclideanDomain n) (-1 : ℝ)
  have hscaledReal :
      (fun x : EuclideanDomain n =>
        (1 + ‖positiveLaplacianScale (n := n) x‖ ^ 2) ^ (-1 : ℝ)).HasTemperateGrowth := by
    simpa [Function.comp_def] using
      hbase.comp (positiveLaplacianScale (n := n)).hasTemperateGrowth
  have hscaledComplex :
      (fun x : EuclideanDomain n =>
        Complex.ofReal
          ((1 + ‖positiveLaplacianScale (n := n) x‖ ^ 2) ^ (-1 : ℝ))).HasTemperateGrowth := by
    simpa [Function.comp_def] using
      (Function.Complex.hasTemperateGrowth_ofReal).comp hscaledReal
  have htwoPiPos : 0 < (2 * Real.pi : ℝ) :=
    mul_pos (by norm_num) Real.pi_pos
  have hscaleNorm (x : EuclideanDomain n) :
      ‖positiveLaplacianScale (n := n) x‖ =
        (2 * Real.pi) * ‖x‖ := by
    rw [show positiveLaplacianScale (n := n) x =
        (2 * Real.pi) • x by
      simp [positiveLaplacianScale]]
    rw [norm_smul, Real.norm_eq_abs, abs_of_pos htwoPiPos]
  have hnorm (x : EuclideanDomain n) :
      ‖positiveLaplacianScale (n := n) x‖ ^ 2 =
        (2 * Real.pi) ^ 2 * ‖x‖ ^ 2 := by
    rw [hscaleNorm x]
    ring
  have hfun :
      (fun x : EuclideanDomain n =>
        Complex.ofReal
          ((1 + ‖positiveLaplacianScale (n := n) x‖ ^ 2) ^ (-1 : ℝ))) =
        positiveLaplacianLowSymbol (n := n) := by
    funext x
    unfold positiveLaplacianLowSymbol
    rw [hnorm x]
  rw [← hfun]
  exact hscaledComplex

theorem positiveLaplacianEnergySymbol_hasTemperateGrowth {n : Nat} :
    (positiveLaplacianEnergySymbol (n := n)).HasTemperateGrowth := by
  have hprod :
      (laplacianFrequencySqSymbol (n := n) *
        positiveLaplacianLowSymbol (n := n)).HasTemperateGrowth :=
    (laplacianFrequencySqSymbol_hasTemperateGrowth (n := n)).mul
      (positiveLaplacianLowSymbol_hasTemperateGrowth (n := n))
  have hconst :
      (fun _ : EuclideanDomain n =>
        Complex.ofReal ((2 * Real.pi) ^ 2)).HasTemperateGrowth :=
    Function.HasTemperateGrowth.const _
  change
    ((fun _ : EuclideanDomain n =>
        Complex.ofReal ((2 * Real.pi) ^ 2)) *
      (laplacianFrequencySqSymbol (n := n) *
        positiveLaplacianLowSymbol (n := n))).HasTemperateGrowth
  exact hconst.mul hprod

/-- Exact low/high partition of unity for the positive-Laplacian resolvent. -/
theorem positiveLaplacianLow_add_energy {n : Nat}
    (x : EuclideanDomain n) :
    positiveLaplacianLowSymbol x +
      positiveLaplacianEnergySymbol x = 1 := by
  have hreal :
      (1 + (2 * Real.pi) ^ 2 * ‖x‖ ^ 2) ^ (-1 : ℝ) +
          (2 * Real.pi) ^ 2 * ‖x‖ ^ 2 *
            (1 + (2 * Real.pi) ^ 2 * ‖x‖ ^ 2) ^ (-1 : ℝ) =
        (1 : ℝ) := by
    rw [Real.rpow_neg (by positivity)]
    norm_num
    field_simp
  have hcomplex := congrArg Complex.ofReal hreal
  simpa [positiveLaplacianLowSymbol, positiveLaplacianEnergySymbol,
    laplacianFrequencySqSymbol, Pi.mul_apply, Complex.ofReal_mul,
    Complex.ofReal_add, Complex.ofReal_pow, mul_assoc] using hcomplex

/-- Every tempered distribution splits exactly into the low and complementary
positive-frequency multipliers above. -/
theorem positiveLaplacian_reconstruction {n : Nat}
    (u : ScalarDistribution n) :
    u =
      TemperedDistribution.fourierMultiplierCLM ℂ
          (positiveLaplacianLowSymbol (n := n)) u +
        TemperedDistribution.fourierMultiplierCLM ℂ
          (positiveLaplacianEnergySymbol (n := n)) u := by
  have hsymbols :
      positiveLaplacianLowSymbol (n := n) +
          positiveLaplacianEnergySymbol (n := n) =
        (fun _ : EuclideanDomain n => (1 : ℂ)) := by
    funext x
    exact positiveLaplacianLow_add_energy x
  have hfourier :
      TemperedDistribution.smulLeftCLM ℂ
          (positiveLaplacianLowSymbol (n := n)) (𝓕 u) +
        TemperedDistribution.smulLeftCLM ℂ
          (positiveLaplacianEnergySymbol (n := n)) (𝓕 u) =
        𝓕 u := by
    change
      (TemperedDistribution.smulLeftCLM ℂ
          (positiveLaplacianLowSymbol (n := n)) +
        TemperedDistribution.smulLeftCLM ℂ
          (positiveLaplacianEnergySymbol (n := n))) (𝓕 u) =
        𝓕 u
    rw [← TemperedDistribution.smulLeftCLM_add
      (positiveLaplacianLowSymbol_hasTemperateGrowth (n := n))
      (positiveLaplacianEnergySymbol_hasTemperateGrowth (n := n)),
      hsymbols]
    simp
  rw [TemperedDistribution.fourierMultiplierCLM_apply,
    TemperedDistribution.fourierMultiplierCLM_apply]
  calc
    u = 𝓕⁻ (𝓕 u) := (FourierTransform.fourierInv_fourier_eq u).symm
    _ = 𝓕⁻
        (TemperedDistribution.smulLeftCLM ℂ
            (positiveLaplacianLowSymbol (n := n)) (𝓕 u) +
          TemperedDistribution.smulLeftCLM ℂ
            (positiveLaplacianEnergySymbol (n := n)) (𝓕 u)) := by
        rw [hfourier]
    _ = 𝓕⁻
          (TemperedDistribution.smulLeftCLM ℂ
            (positiveLaplacianLowSymbol (n := n)) (𝓕 u)) +
        𝓕⁻
          (TemperedDistribution.smulLeftCLM ℂ
            (positiveLaplacianEnergySymbol (n := n)) (𝓕 u)) := by
        exact fourierInv_add _ _

/-- Applying the low resolvent to the Laplacian gives the negative
complementary multiplier. -/
theorem positiveLaplacianLow_laplacian {n : Nat}
    (u : ScalarDistribution n) :
    TemperedDistribution.fourierMultiplierCLM ℂ
        (positiveLaplacianLowSymbol (n := n))
        (Laplacian.laplacian u) =
      -TemperedDistribution.fourierMultiplierCLM ℂ
        (positiveLaplacianEnergySymbol (n := n)) u := by
  rw [TemperedDistribution.laplacian_eq_fourierMultiplierCLM]
  rw [ContinuousLinearMap.map_smul_of_tower]
  have hfreq :=
    laplacianFrequencySqSymbol_hasTemperateGrowth (n := n)
  have hlow :=
    positiveLaplacianLowSymbol_hasTemperateGrowth (n := n)
  have hcompose :
      TemperedDistribution.fourierMultiplierCLM ℂ
          (positiveLaplacianLowSymbol (n := n))
          (TemperedDistribution.fourierMultiplierCLM ℂ
            (laplacianFrequencySqSymbol (n := n)) u) =
        TemperedDistribution.fourierMultiplierCLM ℂ
          (laplacianFrequencySqSymbol (n := n) *
            positiveLaplacianLowSymbol (n := n)) u :=
    TemperedDistribution.fourierMultiplierCLM_fourierMultiplierCLM_apply
      hfreq hlow u
  change
    -(2 * Real.pi) ^ 2 •
        TemperedDistribution.fourierMultiplierCLM ℂ
          (positiveLaplacianLowSymbol (n := n))
          (TemperedDistribution.fourierMultiplierCLM ℂ
            (laplacianFrequencySqSymbol (n := n)) u) =
      -TemperedDistribution.fourierMultiplierCLM ℂ
        (positiveLaplacianEnergySymbol (n := n)) u
  rw [hcompose]
  have hprod :
      (laplacianFrequencySqSymbol (n := n) *
        positiveLaplacianLowSymbol (n := n)).HasTemperateGrowth :=
    hfreq.mul hlow
  have henergy :
      positiveLaplacianEnergySymbol (n := n) =
        Complex.ofReal ((2 * Real.pi) ^ 2) •
          (laplacianFrequencySqSymbol (n := n) *
            positiveLaplacianLowSymbol (n := n)) := by
    funext x
    simp [positiveLaplacianEnergySymbol, Pi.mul_apply]
  rw [henergy]
  rw [TemperedDistribution.fourierMultiplierCLM_smul hprod]
  simp only [smul_apply, neg_smul, neg_inj]
  exact (Complex.coe_smul ((2 * Real.pi) ^ 2) _).symm

/-- The distributional Laplacian has no nonzero tempered eigenvector with
positive eigenvalue one. -/
theorem laplacian_eq_self_imp_eq_zero {n : Nat}
    (u : ScalarDistribution n)
    (h : Laplacian.laplacian u = u) :
    u = 0 := by
  have hlow := congrArg
    (fun z : ScalarDistribution n =>
      TemperedDistribution.fourierMultiplierCLM ℂ
        (positiveLaplacianLowSymbol (n := n)) z) h
  have hcancel :
      TemperedDistribution.fourierMultiplierCLM ℂ
          (positiveLaplacianLowSymbol (n := n)) u +
        TemperedDistribution.fourierMultiplierCLM ℂ
          (positiveLaplacianEnergySymbol (n := n)) u = 0 := by
    rw [← hlow]
    rw [positiveLaplacianLow_laplacian]
    simp
  rw [positiveLaplacian_reconstruction u]
  exact hcancel

end

end Continuum

end CACEFormal

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

/-- Low-frequency inverse of `1 + (2π)²|ξ|²`. -/
noncomputable def positiveLaplacianLowSymbol {n : Nat} :
    EuclideanDomain n → ℂ :=
  fun x => Complex.ofReal <|
    (1 + (2 * Real.pi) ^ 2 * ‖x‖ ^ 2) ^ (-1 : ℝ)

/-- Complementary positive-frequency part. -/
noncomputable def positiveLaplacianEnergySymbol {n : Nat} :
    EuclideanDomain n → ℂ :=
  ((2 * (Real.pi : ℂ)) ^ 2) •
    (laplacianFrequencySqSymbol (n := n) *
      positiveLaplacianLowSymbol (n := n))

theorem laplacianFrequencySqSymbol_hasTemperateGrowth {n : Nat} :
    (laplacianFrequencySqSymbol (n := n)).HasTemperateGrowth := by
  unfold laplacianFrequencySqSymbol
  fun_prop

theorem positiveLaplacianLowSymbol_hasTemperateGrowth {n : Nat} :
    (positiveLaplacianLowSymbol (n := n)).HasTemperateGrowth := by
  unfold positiveLaplacianLowSymbol
  fun_prop

theorem positiveLaplacianEnergySymbol_hasTemperateGrowth {n : Nat} :
    (positiveLaplacianEnergySymbol (n := n)).HasTemperateGrowth := by
  unfold positiveLaplacianEnergySymbol
  fun_prop

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
  unfold positiveLaplacianLowSymbol positiveLaplacianEnergySymbol
  unfold laplacianFrequencySqSymbol
  have hcomplex := congrArg Complex.ofReal hreal
  simpa only [Pi.mul_apply, Pi.smul_apply, Complex.real_smul, Complex.ofReal_mul,
    Complex.ofReal_add, Complex.ofReal_one, Complex.ofReal_pow] using hcomplex

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
  rw [map_smul]
  rw [TemperedDistribution.fourierMultiplierCLM_fourierMultiplierCLM_apply
    (laplacianFrequencySqSymbol_hasTemperateGrowth (n := n))
    (positiveLaplacianLowSymbol_hasTemperateGrowth (n := n))]
  have hprod :
      (laplacianFrequencySqSymbol (n := n) *
        positiveLaplacianLowSymbol (n := n)).HasTemperateGrowth :=
    (laplacianFrequencySqSymbol_hasTemperateGrowth (n := n)).mul
      (positiveLaplacianLowSymbol_hasTemperateGrowth (n := n))
  rw [show positiveLaplacianEnergySymbol (n := n) =
      ((2 * (Real.pi : ℂ)) ^ 2) •
        (laplacianFrequencySqSymbol (n := n) *
          positiveLaplacianLowSymbol (n := n)) by rfl]
  rw [TemperedDistribution.fourierMultiplierCLM_smul hprod]
  norm_num

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

import Mathlib
/-!
MCFC-CACE iteration 38. Conditional algebraic proof obligations.
This file is NOT a proof of Einstein PDE existence, wormhole stability,
horizon formation, or the validity of exotic matter.
-/
namespace MCFC

theorem ellis_sq_positive (x b : ℝ) (hb : 0 < b) : 0 < x ^ 2 + b ^ 2 := by
  positivity

theorem ellis_angular (x b r : ℝ) (hr : r ^ 2 = x ^ 2 + b ^ 2)
    (hr0 : r ≠ 0) :
    4 * r * (-b ^ 2 / (4 * r ^ 3)) +
    4 * (-x / (2 * r)) * (x / (2 * r)) + 1 = 0 := by
  calc
    4 * r * (-b ^ 2 / (4 * r ^ 3)) +
        4 * (-x / (2 * r)) * (x / (2 * r)) + 1 =
      (r ^ 2 - x ^ 2 - b ^ 2) / r ^ 2 := by
        field_simp
        <;> ring
    _ = 0 := by
      have hzero : r ^ 2 - x ^ 2 - b ^ 2 = 0 := by linarith
      rw [hzero]
      simp

theorem ellis_wave (x q r : ℝ) (hr0 : r ≠ 0) :
    q * x / (2 * r ^ 4) +
    ((-x / (2 * r)) * (q / (2 * r ^ 2)) +
      (x / (2 * r)) * (-q / (2 * r ^ 2))) / r = 0 := by
  field_simp
  <;> ring

theorem ellis_null_constraint (b q r : ℝ)
    (hq : q ^ 2 = 2 * b ^ 2) (hr0 : r ≠ 0) :
    b ^ 2 / (4 * r ^ 3) -
      r / 2 * (-q / (2 * r ^ 2)) ^ 2 = 0 := by
  calc
    b ^ 2 / (4 * r ^ 3) -
        r / 2 * (-q / (2 * r ^ 2)) ^ 2 =
      (2 * b ^ 2 - q ^ 2) / (8 * r ^ 3) := by
        field_simp
        <;> ring
    _ = 0 := by
      rw [hq]
      ring

theorem ellis_conformal (b q r : ℝ)
    (hq : q ^ 2 = 2 * b ^ 2) (hr0 : r ≠ 0) :
    b ^ 2 / (4 * r ^ 4) +
      (1 / 2 : ℝ) * (-q / (2 * r ^ 2)) * (q / (2 * r ^ 2)) = 0 := by
  calc
    b ^ 2 / (4 * r ^ 4) +
        (1 / 2 : ℝ) * (-q / (2 * r ^ 2)) * (q / (2 * r ^ 2)) =
      (2 * b ^ 2 - q ^ 2) / (8 * r ^ 4) := by
        field_simp
        <;> ring
    _ = 0 := by
      rw [hq]
      ring

theorem ellis_mass_identity (x b r : ℝ)
    (hr : r ^ 2 = x ^ 2 + b ^ 2) (hr0 : r ≠ 0) :
    r ^ 2 * (1 + 4 * (-x / (2 * r)) * (x / (2 * r))) = b ^ 2 := by
  calc
    r ^ 2 * (1 + 4 * (-x / (2 * r)) * (x / (2 * r))) =
      r ^ 2 - x ^ 2 := by
        field_simp
        <;> ring
    _ = b ^ 2 := by linarith

theorem diamond_algebraic (a b c d h f : ℝ)
    (hh : h ≠ 0) (hupdate : d = b + c - a + h ^ 2 * f) :
    (d - b - c + a) / h ^ 2 = f := by
  rw [hupdate]
  field_simp
  <;> ring

theorem vaidya_apparent_horizon (m r : ℝ)
    (hm : r = 2 * m) (hr : r ≠ 0) :
    1 - 2 * m / r = 0 := by
  rw [hm] at *
  rw [div_self hr]
  norm_num

theorem vaidya_flux_nonnegative (dm r : ℝ)
    (hdm : 0 ≤ dm) (hr : 0 < r) :
    0 ≤ 2 * dm / r ^ 2 := by
  exact div_nonneg (mul_nonneg (by norm_num) hdm) (sq_nonneg r)

end MCFC

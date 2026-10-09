import LeanCert.Validity.Bounds.Core
import CACEFormal.WeightedEnergy
import Mathlib.Tactic.NormNum

namespace CACEFormal.CertifiedIntervalBounds

open LeanCert.Core LeanCert.Engine LeanCert.Validity

/-!
Certificate inputs remain explicit proof obligations. A runtime number or a
successful floating-point calculation cannot discharge these equalities.
The energy bridge uses CACE's existing certified SPD operator, not an
unverified runtime matrix.
-/

/-- A checked two-sided enclosure bounds an exactly represented residual component. -/
theorem residual_component_bound
    (e : Expr) (hsupp : ExprSupportedCore e) (I : IntervalRat)
    (c : ℚ) (cfg : EvalConfig)
    (hcert : checkBounds e I (-c) c cfg = true)
    (x r : ℝ) (hx : x ∈ I)
    (hrepresentation : r = Expr.eval (fun _ => x) e) :
    |r| ≤ (c : ℝ) := by
  have hb := verify_bounds e hsupp I (-c) c cfg hcert x hx
  rw [hrepresentation]
  apply abs_le.mpr
  exact ⟨by simpa using hb.1, hb.2⟩

/-- Transfer a checked expression upper bound to CACE's coercive energy error. -/
theorem energy_error_bound
    {E : Type*} [NormedAddCommGroup E] [InnerProductSpace ℝ E]
    (A : SPDEnergyOperator E) (err : E)
    (e : Expr) (hsupp : ExprSupportedCore e) (I : IntervalRat)
    (c : ℚ) (cfg : EvalConfig)
    (hcert : checkUpperBound e I c cfg = true)
    (x : ℝ) (hx : x ∈ I)
    (hrepresentation : A.energySq err = Expr.eval (fun _ => x) e) :
    A.alpha * (‖err‖ * ‖err‖) ≤ (c : ℝ) := by
  have hb := verify_upper_bound e hsupp I c cfg hcert x hx
  have he : A.energySq err ≤ (c : ℝ) := hrepresentation.trans_le hb
  exact le_trans (A.coercive err) he

def symmetricUnit : IntervalRat := ⟨-1, 1, by norm_num⟩

/-- Concrete certificate evaluated by Lean's kernel, without native_decide. -/
theorem linear_residual_certificate :
    checkBounds (.var 0) symmetricUnit (-1) 1 {} = true := by
  decide +kernel

/-- End-to-end mathematical smoke test for an exactly represented linear residual. -/
theorem linear_residual_bound (x : ℝ) (hx : x ∈ symmetricUnit) :
    |x| ≤ 1 := by
  simpa using residual_component_bound (.var 0) (.var 0)
    symmetricUnit 1 {} linear_residual_certificate x x hx rfl

/-- A false upper certificate is rejected; interval membership alone is insufficient. -/
theorem invalid_linear_upper_rejected :
    checkUpperBound (.var 0) symmetricUnit 0 {} = false := by
  decide +kernel

def positiveUnit : IntervalRat := ⟨0, 1, by norm_num⟩

/-- A transcendental enclosure certified by kernel reduction of rational arithmetic. -/
theorem exp_unit_certificate :
    checkUpperBound (.exp (.var 0)) positiveUnit 3 { taylorDepth := 10 } = true := by
  decide +kernel

theorem exp_unit_bound (x : ℝ) (hx : x ∈ positiveUnit) :
    Real.exp x ≤ 3 := by
  simpa using verify_upper_bound (.exp (.var 0)) (.exp (.var 0))
    positiveUnit 3 { taylorDepth := 10 } exp_unit_certificate x hx

end CACEFormal.CertifiedIntervalBounds

import Mathlib.Data.Real.Basic
import Mathlib.Tactic.FieldSimp

namespace CACEFormal

/-- Algebraic 2D diagonal-affine Piola fixture used to pin the normal-flux scaling law.
The general affine-simplex theorem remains a later formalization target. -/
theorem diagonal_piola_flux_fixture
    (qx qy sx sy : ℝ) (hsx : sx ≠ 0) (hsy : sy ≠ 0) :
    (-(sx * qx / (sx * sy))) * sy = -qx := by
  field_simp [hsx, hsy]

end CACEFormal

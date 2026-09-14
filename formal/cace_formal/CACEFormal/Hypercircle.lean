import Mathlib.Analysis.InnerProductSpace.Basic

namespace CACEFormal

theorem hypercircle_of_inner_eq_zero
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    {x y : E} (h : inner ℝ x y = 0) :
    ‖x + y‖ * ‖x + y‖ = ‖x‖ * ‖x‖ + ‖y‖ * ‖y‖ := by
  exact norm_add_sq_eq_norm_sq_add_norm_sq_real h

end CACEFormal

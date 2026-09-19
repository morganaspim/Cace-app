import Mathlib.Analysis.InnerProductSpace.Basic
import Mathlib.Topology.Algebra.Module.Basic
import Mathlib.Tactic.Ring

namespace CACEFormal

/-!
# Certified weighted energy

The original CACE file contained only a positive scalar placeholder.  That
small API is retained for compatibility, but the trust-bearing layer now also
contains an actual real SPD-operator certificate.

The certificate deliberately stores the properties needed by the proofs
instead of assuming that an arbitrary runtime matrix is SPD:

* a bounded linear operator;
* symmetry of its energy cross term;
* a positive coercivity constant.

The weighted hypercircle identity is then derived algebraically.
-/

/-- Backward-compatible positive scalar lower-bound metadata. -/
structure WeightedEnergyAssumptions
    (E : Type*) [NormedAddCommGroup E] [InnerProductSpace ℝ E] where
  alpha : ℝ
  alpha_pos : 0 < alpha

/-- A certified bounded symmetric positive-definite energy operator.

`symmetric` is the real self-adjoint identity in the exact form used by the
energy expansion.  `coercive` gives a strict positive lower bound through
`alpha`.
-/
structure SPDEnergyOperator
    (E : Type*) [NormedAddCommGroup E] [InnerProductSpace ℝ E] where
  op : E →L[ℝ] E
  alpha : ℝ
  alpha_pos : 0 < alpha
  symmetric : ∀ x y : E,
    inner ℝ (op x) y = inner ℝ (op y) x
  coercive : ∀ x : E,
    alpha * (‖x‖ * ‖x‖) ≤ inner ℝ (op x) x

namespace SPDEnergyOperator

variable {E : Type*} [NormedAddCommGroup E] [InnerProductSpace ℝ E]

/-- Squared norm/energy induced by the certified SPD operator. -/
def energySq (A : SPDEnergyOperator E) (x : E) : ℝ :=
  inner ℝ (A.op x) x

@[simp] theorem energySq_zero (A : SPDEnergyOperator E) :
    A.energySq 0 = 0 := by
  simp [energySq]

/-- Coercivity makes the certified energy nonnegative. -/
theorem energySq_nonneg (A : SPDEnergyOperator E) (x : E) :
    0 ≤ A.energySq x := by
  have hbase : 0 ≤ A.alpha * (‖x‖ * ‖x‖) :=
    mul_nonneg (le_of_lt A.alpha_pos)
      (mul_nonneg (norm_nonneg x) (norm_nonneg x))
  exact le_trans hbase (A.coercive x)

/-- Nonzero vectors have strictly positive certified energy. -/
theorem energySq_pos_of_ne_zero
    (A : SPDEnergyOperator E) {x : E} (hx : x ≠ 0) :
    0 < A.energySq x := by
  have hnorm : 0 < ‖x‖ := norm_pos_iff.mpr hx
  have hbase : 0 < A.alpha * (‖x‖ * ‖x‖) :=
    mul_pos A.alpha_pos (mul_pos hnorm hnorm)
  exact lt_of_lt_of_le hbase (A.coercive x)

/-- The SPD energy is definite. -/
theorem energySq_eq_zero_iff (A : SPDEnergyOperator E) (x : E) :
    A.energySq x = 0 ↔ x = 0 := by
  constructor
  · intro h
    by_contra hx
    have hp := A.energySq_pos_of_ne_zero hx
    rw [h] at hp
    exact (lt_irrefl 0) hp
  · intro h
    subst x
    exact A.energySq_zero

/-- Exact two-vector expansion of the SPD energy. -/
theorem energySq_add (A : SPDEnergyOperator E) (x y : E) :
    A.energySq (x + y) =
      A.energySq x + A.energySq y +
        2 * inner ℝ (A.op x) y := by
  unfold energySq
  rw [map_add, inner_add_left, inner_add_right, inner_add_right]
  rw [A.symmetric y x]
  ring

/-- Weighted hypercircle/Pythagoras identity under weighted orthogonality. -/
theorem weighted_hypercircle
    (A : SPDEnergyOperator E) (x y : E)
    (horth : inner ℝ (A.op x) y = 0) :
    A.energySq (x + y) = A.energySq x + A.energySq y := by
  rw [A.energySq_add, horth]
  ring

/-- Symmetric formulation of weighted orthogonality. -/
theorem weighted_orthogonality_comm
    (A : SPDEnergyOperator E) (x y : E) :
    inner ℝ (A.op x) y = 0 ↔ inner ℝ (A.op y) x = 0 := by
  rw [A.symmetric x y]

end SPDEnergyOperator

end CACEFormal

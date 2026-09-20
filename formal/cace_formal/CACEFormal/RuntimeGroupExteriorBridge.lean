import Mathlib
import CACEFormal.RuntimeRMKCoreBridge
import CACEFormal.ExteriorPowerTransport
import CACEFormal.AffineGeometry

namespace CACEFormal

/-!
# Runtime group/exterior bridge

Quarantined formal seam for the first exact finite-permutation and exterior
operations used by the C++ RMK and ReasoningOperator layer.

The current bridge intentionally proves the 2D kernel laws first. General
finite-group closure, sparse multivectors, and higher-dimensional runtime
serialization remain separate source-to-formal obligations.
-/

namespace RuntimeRMK

def wedge (u v : Vec2) : ℚ :=
  u.x * v.y - u.y * v.x

@[simp] theorem wedge_toReal (u v : Vec2) :
    ExteriorPower2.wedge u.toReal v.toReal = (wedge u v : ℝ) := by
  rcases u with ⟨ux, uy⟩
  rcases v with ⟨vx, vy⟩
  norm_num [wedge, Vec2.toReal, ExteriorPower2.wedge]

/-- Exact top-grade pushforward law mirrored by ExactExterior.pushforward. -/
theorem wedge_matVec (A : Mat2) (u v : Vec2) :
    wedge (A.matVec u) (A.matVec v) = A.det * wedge u v := by
  rcases A with ⟨a, b, c, d⟩
  rcases u with ⟨ux, uy⟩
  rcases v with ⟨vx, vy⟩
  dsimp [wedge, Mat2.matVec, Mat2.det]
  ring

/-- The runtime rational top-blade law refines the existing trust-bearing
ExteriorPower2.wedge_grade1 theorem after embedding into real geometry. -/
theorem wedge_pushforward_refines_exteriorPower
    (A : Mat2) (u v : Vec2) :
    ExteriorPower2.wedge
        (ExteriorPower2.grade1 A.toAffineReal u.toReal)
        (ExteriorPower2.grade1 A.toAffineReal v.toReal) =
      (A.det : ℝ) * ExteriorPower2.wedge u.toReal v.toReal := by
  simpa using ExteriorPower2.wedge_grade1 A.toAffineReal u.toReal v.toReal

inductive Permutation2
  | identity
  | swap
  deriving DecidableEq, Repr

namespace Permutation2

def act (p : Permutation2) (v : Vec2) : Vec2 :=
  match p with
  | identity => v
  | swap => ⟨v.y, v.x⟩

def sign : Permutation2 → ℚ
  | identity => 1
  | swap => -1

def matrix : Permutation2 → Mat2
  | identity => Mat2.identity
  | swap => ⟨0, 1, 1, 0⟩

@[simp] theorem act_eq_matVec (p : Permutation2) (v : Vec2) :
    act p v = (matrix p).matVec v := by
  cases p <;>
    rcases v with ⟨x, y⟩ <;>
    norm_num [act, matrix, Mat2.identity, Mat2.matVec]

@[simp] theorem det_matrix_eq_sign (p : Permutation2) :
    (matrix p).det = sign p := by
  cases p <;>
    norm_num [matrix, sign, Mat2.identity, Mat2.det]

/-- Orientation sign tracked by the runtime exterior permutation action. -/
theorem wedge_act (p : Permutation2) (u v : Vec2) :
    wedge (act p u) (act p v) = sign p * wedge u v := by
  cases p <;>
    rcases u with ⟨ux, uy⟩ <;>
    rcases v with ⟨vx, vy⟩ <;>
    dsimp [act, sign, wedge] <;>
    ring

@[simp] theorem swap_toReal_eq_affineSwap (v : Vec2) :
    (act swap v).toReal = Affine2.swapAxes.mapPoint v.toReal := by
  rcases v with ⟨x, y⟩
  ext <;>
    norm_num [act, Vec2.toReal, Affine2.swapAxes, Affine2.mapPoint]

end Permutation2

def triangle (a b c : Vec2) : Triangle2 :=
  ⟨a.toReal, b.toReal, c.toReal⟩

/-- Swapping two simplex vertices reverses the exact signed orientation. -/
theorem triangle_swap01_det (a b c : Vec2) :
    (triangle b a c).det = -(triangle a b c).det := by
  rcases a with ⟨ax, ay⟩
  rcases b with ⟨bx, by⟩
  rcases c with ⟨cx, cy⟩
  norm_num [triangle, Vec2.toReal, Triangle2.det]
  ring

end RuntimeRMK

end CACEFormal

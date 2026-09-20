import Mathlib
import CACEFormal.ExecutableRationalGeometry
import CACEFormal.ExteriorPowerTransport

namespace CACEFormal

/-!
# Runtime RMK exact-core bridge

Quarantined source-to-formal bridge for the exact rational conventions used by
CACE's C++ Rigorous Math Kernel.

This module does not promote a runtime claim. It provides a small Lean model
of the same 2D rational vector/matrix/affine/rotor semantics so Exact-Pin
preflight can check the mathematical seam before any audited promotion.
-/

namespace RuntimeRMK

structure Vec2 where
  x : ℚ
  y : ℚ
  deriving DecidableEq, Repr

namespace Vec2

theorem ext_eq {u v : Vec2} (hx : u.x = v.x) (hy : u.y = v.y) : u = v := by
  cases u
  cases v
  simp_all

def toReal (v : Vec2) : Point2 :=
  ⟨(v.x : ℝ), (v.y : ℝ)⟩

def normSq (v : Vec2) : ℚ :=
  v.x * v.x + v.y * v.y

end Vec2

structure Mat2 where
  m00 : ℚ
  m01 : ℚ
  m10 : ℚ
  m11 : ℚ
  deriving DecidableEq, Repr

namespace Mat2

def identity : Mat2 := ⟨1, 0, 0, 1⟩

def det (A : Mat2) : ℚ :=
  A.m00 * A.m11 - A.m01 * A.m10

def matVec (A : Mat2) (v : Vec2) : Vec2 :=
  ⟨A.m00 * v.x + A.m01 * v.y,
   A.m10 * v.x + A.m11 * v.y⟩

def mul (A B : Mat2) : Mat2 :=
  ⟨A.m00 * B.m00 + A.m01 * B.m10,
   A.m00 * B.m01 + A.m01 * B.m11,
   A.m10 * B.m00 + A.m11 * B.m10,
   A.m10 * B.m01 + A.m11 * B.m11⟩

def toAffineReal (A : Mat2) : Affine2 :=
  ⟨(A.m00 : ℝ), (A.m01 : ℝ), (A.m10 : ℝ), (A.m11 : ℝ), 0, 0⟩

@[simp] theorem linearDet_toReal (A : Mat2) :
    A.toAffineReal.linearDet = (A.det : ℝ) := by
  rcases A with ⟨a, b, c, d⟩
  simp [toAffineReal, det, Affine2.linearDet]

@[simp] theorem matVec_identity (v : Vec2) :
    matVec identity v = v := by
  rcases v with ⟨x, y⟩
  simp [matVec, identity]

theorem matVec_mul (A B : Mat2) (v : Vec2) :
    matVec (mul A B) v = matVec A (matVec B v) := by
  rcases A with ⟨a00, a01, a10, a11⟩
  rcases B with ⟨b00, b01, b10, b11⟩
  rcases v with ⟨x, y⟩
  apply Vec2.ext_eq <;> dsimp [matVec, mul] <;> ring

@[simp] theorem matVec_to_grade1 (A : Mat2) (v : Vec2) :
    (matVec A v).toReal =
      ExteriorPower2.grade1 A.toAffineReal v.toReal := by
  rcases A with ⟨a, b, c, d⟩
  rcases v with ⟨x, y⟩
  ext <;>
    simp [matVec, Vec2.toReal, toAffineReal, ExteriorPower2.grade1]

end Mat2

structure AffineMap2 where
  linear : Mat2
  translation : Vec2
  deriving DecidableEq, Repr

namespace AffineMap2

def apply (F : AffineMap2) (p : Vec2) : Vec2 :=
  let q := F.linear.matVec p
  ⟨q.x + F.translation.x, q.y + F.translation.y⟩

def toReal (F : AffineMap2) : Affine2 :=
  ⟨(F.linear.m00 : ℝ), (F.linear.m01 : ℝ),
   (F.linear.m10 : ℝ), (F.linear.m11 : ℝ),
   (F.translation.x : ℝ), (F.translation.y : ℝ)⟩

@[simp] theorem apply_toReal (F : AffineMap2) (p : Vec2) :
    (apply F p).toReal = F.toReal.mapPoint p.toReal := by
  rcases F with ⟨⟨a, b, c, d⟩, ⟨tx, ty⟩⟩
  rcases p with ⟨x, y⟩
  ext <;>
    simp [apply, Vec2.toReal, Mat2.matVec, toReal, Affine2.mapPoint]

@[simp] theorem linearDet_toReal (F : AffineMap2) :
    F.toReal.linearDet = (F.linear.det : ℝ) := by
  rcases F with ⟨⟨a, b, c, d⟩, ⟨tx, ty⟩⟩
  simp [toReal, Mat2.det, Affine2.linearDet]

end AffineMap2

/-- Exact checker semantics used by the runtime solution-verification path. -/
def verifiesSolution (A : Mat2) (x b : Vec2) : Prop :=
  A.matVec x = b

/-- Exact checker semantics used by the runtime inverse-verification path. -/
def verifiesInverse (A B : Mat2) : Prop :=
  A.mul B = Mat2.identity ∧ B.mul A = Mat2.identity

theorem verifiesSolution_sound {A : Mat2} {x b : Vec2}
    (h : verifiesSolution A x b) : A.matVec x = b := h

theorem verifiesInverse_sound {A B : Mat2}
    (h : verifiesInverse A B) :
    A.mul B = Mat2.identity ∧ B.mul A = Mat2.identity := h

/-- Exact rational two-plane rotor convention used by the C++ RMK. -/
structure PlaneRotor2 where
  cosine : ℚ
  sine : ℚ
  unit : cosine * cosine + sine * sine = 1

namespace PlaneRotor2

def matrix (R : PlaneRotor2) : Mat2 :=
  ⟨R.cosine, -R.sine, R.sine, R.cosine⟩

def apply (R : PlaneRotor2) (v : Vec2) : Vec2 :=
  R.matrix.matVec v

@[simp] theorem det_matrix (R : PlaneRotor2) :
    R.matrix.det = 1 := by
  rcases R with ⟨c, s, h⟩
  dsimp [matrix, Mat2.det]
  nlinarith

theorem normSq_apply (R : PlaneRotor2) (v : Vec2) :
    (R.apply v).normSq = v.normSq := by
  rcases R with ⟨c, s, h⟩
  rcases v with ⟨x, y⟩
  dsimp [apply, matrix, Mat2.matVec, Vec2.normSq]
  nlinarith

end PlaneRotor2

end RuntimeRMK

end CACEFormal

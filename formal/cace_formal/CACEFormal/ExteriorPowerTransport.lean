import Mathlib
import CACEFormal.AffineGeometry

namespace CACEFormal

/-!
# Two-dimensional exterior-power transport

This is the first trust-bearing graded-geometry layer for CACE.

The current certified affine/P1/RT0 stack is two-dimensional, so this file
starts with the exact grades needed there instead of introducing a large
generic runtime abstraction:

* grade 0: scalars;
* grade 1: vectors / oriented edges;
* grade 2: signed bivector coefficients / oriented areas.

The main theorem is the exterior-square law

`wedge (A u) (A v) = det(A) * wedge u v`.

Translation disappears from edge vectors exactly.  These algebraic semantics
can later serve as the specification refined by a generic exterior algebra or
a specialized C++ blade kernel.
-/

namespace ExteriorPower2

/-- Difference of two points, regarded as a free vector. -/
def edgeVector (a b : Point2) : Point2 :=
  ⟨b.x - a.x, b.y - a.y⟩

/-- Coefficient of the oriented 2-blade `u ∧ v` in the standard basis. -/
def wedge (u v : Point2) : ℝ :=
  u.x * v.y - u.y * v.x

/-- Grade-0 exterior action: scalars are unchanged by a linear map. -/
def grade0 (_F : Affine2) (s : ℝ) : ℝ :=
  s

/-- Grade-1 exterior action: the linear part of an affine map. -/
def grade1 (F : Affine2) (v : Point2) : Point2 :=
  ⟨F.a * v.x + F.b * v.y,
   F.c * v.x + F.d * v.y⟩

/-- Grade-2 exterior action: multiplication by the linear determinant. -/
def grade2 (F : Affine2) (B : ℝ) : ℝ :=
  F.linearDet * B

@[simp] theorem grade0_apply (F : Affine2) (s : ℝ) :
    grade0 F s = s := rfl

@[simp] theorem grade1_identity (v : Point2) :
    grade1 Affine2.identity v = v := by
  rcases v with ⟨x, y⟩
  norm_num [grade1, Affine2.identity]

@[simp] theorem grade2_identity (B : ℝ) :
    grade2 Affine2.identity B = B := by
  simp [grade2]

/-- Grade 1 is functorial under affine-linear composition. -/
@[simp] theorem grade1_comp (outer inner : Affine2) (v : Point2) :
    grade1 (Affine2.comp outer inner) v =
      grade1 outer (grade1 inner v) := by
  rcases outer with ⟨oa, ob, oc, od, otx, oty⟩
  rcases inner with ⟨ia, ib, ic, id, itx, ity⟩
  rcases v with ⟨x, y⟩
  ext <;> dsimp [grade1, Affine2.comp] <;> ring

/-- Grade 2 is functorial under affine-linear composition. -/
@[simp] theorem grade2_comp (outer inner : Affine2) (B : ℝ) :
    grade2 (Affine2.comp outer inner) B =
      grade2 outer (grade2 inner B) := by
  simp [grade2, Affine2.linearDet_comp, mul_assoc]

/-- The exact exterior-square law in two dimensions. -/
theorem wedge_grade1 (F : Affine2) (u v : Point2) :
    wedge (grade1 F u) (grade1 F v) =
      F.linearDet * wedge u v := by
  rcases F with ⟨a, b, c, d, tx, ty⟩
  rcases u with ⟨ux, uy⟩
  rcases v with ⟨vx, vy⟩
  dsimp [wedge, grade1, Affine2.linearDet]
  ring

/-- Equivalent statement: applying grade 2 to a wedge equals wedging the
grade-1 images. -/
theorem grade2_wedge (F : Affine2) (u v : Point2) :
    grade2 F (wedge u v) = wedge (grade1 F u) (grade1 F v) := by
  rw [wedge_grade1]
  rfl

/-- Translation cancels exactly when an affine point map is converted to an
edge vector. -/
theorem edgeVector_mapPoint (F : Affine2) (a b : Point2) :
    edgeVector (F.mapPoint a) (F.mapPoint b) =
      grade1 F (edgeVector a b) := by
  rcases F with ⟨aa, ab, ac, ad, tx, ty⟩
  rcases a with ⟨ax, ay⟩
  rcases b with ⟨bx, by⟩
  ext <;> dsimp [edgeVector, grade1, Affine2.mapPoint] <;> ring

/-- A triangle determinant is exactly the wedge of its two base edge vectors. -/
theorem triangle_det_eq_wedge (T : Triangle2) :
    T.det = wedge (edgeVector T.p0 T.p1) (edgeVector T.p0 T.p2) := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  rfl

/-- The existing affine triangle determinant theorem is exactly the grade-2
exterior action on its oriented area blade. -/
theorem triangle_det_map_eq_grade2 (F : Affine2) (T : Triangle2) :
    (F.mapTriangle T).det = grade2 F T.det := by
  rw [Affine2.det_mapTriangle]
  rfl

/-- Exterior-square proof of the transformed triangle wedge law. -/
theorem triangle_wedge_map (F : Affine2) (T : Triangle2) :
    wedge
        (edgeVector (F.mapPoint T.p0) (F.mapPoint T.p1))
        (edgeVector (F.mapPoint T.p0) (F.mapPoint T.p2)) =
      F.linearDet *
        wedge (edgeVector T.p0 T.p1) (edgeVector T.p0 T.p2) := by
  rw [edgeVector_mapPoint, edgeVector_mapPoint]
  exact wedge_grade1 F _ _

/-- Fused affine chains act on grade 1 exactly as sequential grade-1 maps. -/
@[simp] theorem grade1_chain_cons
    (F : Affine2) (Fs : List Affine2) (v : Point2) :
    grade1 (Affine2.chain (F :: Fs)) v =
      grade1 (Affine2.chain Fs) (grade1 F v) := by
  simp [Affine2.chain]

/-- Splitting an affine chain into batches does not change its grade-1 action. -/
theorem grade1_chain_append
    (left right : List Affine2) (v : Point2) :
    grade1 (Affine2.chain (left ++ right)) v =
      grade1 (Affine2.chain right) (grade1 (Affine2.chain left) v) := by
  induction left generalizing v with
  | nil =>
      simp [Affine2.chain]
  | cons F Fs ih =>
      simp only [List.cons_append, grade1_chain_cons]
      exact ih (grade1 F v)

/-- The grade-2 action of a fused chain is the product of its determinant
factors. -/
theorem grade2_chain (Fs : List Affine2) (B : ℝ) :
    grade2 (Affine2.chain Fs) B =
      (Fs.map Affine2.linearDet).prod * B := by
  rw [grade2, Affine2.linearDet_chain]

/-- Arbitrarily long affine chains therefore have one exact exterior-square
action.  This is the scalable bridge from 5–9+ transform combinatorics to a
single blade operation. -/
theorem wedge_grade1_chain (Fs : List Affine2) (u v : Point2) :
    wedge
        (grade1 (Affine2.chain Fs) u)
        (grade1 (Affine2.chain Fs) v) =
      (Fs.map Affine2.linearDet).prod * wedge u v := by
  rw [wedge_grade1, Affine2.linearDet_chain]

end ExteriorPower2

end CACEFormal

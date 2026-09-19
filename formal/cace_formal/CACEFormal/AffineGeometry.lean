import Mathlib
import CACEFormal.GeometryTransforms

namespace CACEFormal

/-!
# General affine triangle geometry

This file closes the gap between the elementary exact transforms in
`GeometryTransforms.lean` and a single arbitrary affine map of the plane.

The trust-bearing theorem is purely algebraic:

```
det (F(T)) = det(linearPart F) * det(T).
```

From it we obtain certified preservation of triangle nondegeneracy whenever
the linear determinant is nonzero, and preservation of positive orientation
whenever it is positive.  Translation is included in `F` but drops out of
the determinant exactly.

The elementary transform family already used by CACE is embedded below as
special affine maps.  This gives later proof search two equivalent routes:
compose small certified primitives, or collapse the same geometry into one
certified affine stage.
-/

/-- A real affine map of the plane
`(x,y) ↦ (a*x + b*y + tx, c*x + d*y + ty)`. -/
structure Affine2 where
  a : ℝ
  b : ℝ
  c : ℝ
  d : ℝ
  tx : ℝ
  ty : ℝ
deriving Repr

namespace Affine2

/-- Determinant of the linear part of an affine map. -/
def linearDet (F : Affine2) : ℝ :=
  F.a * F.d - F.b * F.c

/-- Apply an affine map to a point. -/
def mapPoint (F : Affine2) (p : Point2) : Point2 :=
  ⟨F.a * p.x + F.b * p.y + F.tx,
   F.c * p.x + F.d * p.y + F.ty⟩

/-- Apply an affine map vertexwise to a triangle. -/
def mapTriangle (F : Affine2) (T : Triangle2) : Triangle2 :=
  ⟨F.mapPoint T.p0, F.mapPoint T.p1, F.mapPoint T.p2⟩

/-- The exact affine determinant law for triangle signed area. -/
@[simp] theorem det_mapTriangle (F : Affine2) (T : Triangle2) :
    (F.mapTriangle T).det = F.linearDet * T.det := by
  rcases F with ⟨a, b, c, d, tx, ty⟩
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  dsimp [mapTriangle, mapPoint, linearDet, Triangle2.det]
  ring

/-- The identity affine map. -/
def identity : Affine2 :=
  ⟨1, 0, 0, 1, 0, 0⟩

/-- Compose two affine maps. `inner` runs first and `outer` runs second. -/
def comp (outer inner : Affine2) : Affine2 :=
  ⟨outer.a * inner.a + outer.b * inner.c,
   outer.a * inner.b + outer.b * inner.d,
   outer.c * inner.a + outer.d * inner.c,
   outer.c * inner.b + outer.d * inner.d,
   outer.a * inner.tx + outer.b * inner.ty + outer.tx,
   outer.c * inner.tx + outer.d * inner.ty + outer.ty⟩

/-- Fused affine composition acts exactly like sequential point mapping. -/
@[simp] theorem mapPoint_comp (outer inner : Affine2) (p : Point2) :
    (comp outer inner).mapPoint p = outer.mapPoint (inner.mapPoint p) := by
  rcases outer with ⟨oa, ob, oc, od, otx, oty⟩
  rcases inner with ⟨ia, ib, ic, id, itx, ity⟩
  rcases p with ⟨x, y⟩
  ext <;> dsimp [comp, mapPoint] <;> ring

/-- Linear determinants multiply under affine fusion. -/
@[simp] theorem linearDet_comp (outer inner : Affine2) :
    (comp outer inner).linearDet = outer.linearDet * inner.linearDet := by
  rcases outer with ⟨oa, ob, oc, od, otx, oty⟩
  rcases inner with ⟨ia, ib, ic, id, itx, ity⟩
  dsimp [comp, linearDet]
  ring

/-- Fused affine composition acts exactly like sequential triangle mapping. -/
@[simp] theorem mapTriangle_comp (outer inner : Affine2) (T : Triangle2) :
    (comp outer inner).mapTriangle T =
      outer.mapTriangle (inner.mapTriangle T) := by
  rcases T with ⟨p0, p1, p2⟩
  simp [mapTriangle]

/-- Fuse an arbitrary left-to-right affine chain into one affine map. -/
def chain : List Affine2 → Affine2
  | [] => identity
  | F :: Fs => comp (chain Fs) F

@[simp] theorem chain_nil : chain [] = identity := rfl

@[simp] theorem mapPoint_chain_cons (F : Affine2) (Fs : List Affine2) (p : Point2) :
    (chain (F :: Fs)).mapPoint p =
      (chain Fs).mapPoint (F.mapPoint p) := by
  simp [chain]

/-- Batch splitting does not change the action of a fused affine chain. -/
theorem mapPoint_chain_append
    (left right : List Affine2) (p : Point2) :
    (chain (left ++ right)).mapPoint p =
      (chain right).mapPoint ((chain left).mapPoint p) := by
  induction left generalizing p with
  | nil =>
      simp [chain, identity, mapPoint]
  | cons F Fs ih =>
      simp only [List.cons_append, mapPoint_chain_cons]
      exact ih (F.mapPoint p)

/-- The same batch-splitting law holds for whole triangles. -/
theorem mapTriangle_chain_append
    (left right : List Affine2) (T : Triangle2) :
    (chain (left ++ right)).mapTriangle T =
      (chain right).mapTriangle ((chain left).mapTriangle T) := by
  rcases T with ⟨p0, p1, p2⟩
  apply Triangle2.ext <;>
    simp [mapTriangle, mapPoint_chain_append]

/-- The fused chain determinant is exactly the product of all stage
determinants. -/
theorem linearDet_chain (Fs : List Affine2) :
    (chain Fs).linearDet = (Fs.map linearDet).prod := by
  induction Fs with
  | nil =>
      simp [chain]
  | cons F Fs ih =>
      simp [chain, ih, mul_comm]

/-- Pure translation. -/
def translation (v : Point2) : Affine2 :=
  ⟨1, 0, 0, 1, v.x, v.y⟩

/-- Uniform scale about the origin. -/
def uniformScale (s : ℝ) : Affine2 :=
  ⟨s, 0, 0, s, 0, 0⟩

/-- Independent coordinate-axis scale. -/
def scaleXY (sx sy : ℝ) : Affine2 :=
  ⟨sx, 0, 0, sy, 0, 0⟩

/-- Elementary x-shear. -/
def shearX (k : ℝ) : Affine2 :=
  ⟨1, k, 0, 1, 0, 0⟩

/-- Elementary y-shear. -/
def shearY (k : ℝ) : Affine2 :=
  ⟨1, 0, k, 1, 0, 0⟩

/-- Counter-clockwise quarter rotation. -/
def rotateQuarter : Affine2 :=
  ⟨0, -1, 1, 0, 0, 0⟩

/-- Swap the two coordinate axes. -/
def swapAxes : Affine2 :=
  ⟨0, 1, 1, 0, 0, 0⟩

@[simp] theorem linearDet_identity : identity.linearDet = 1 := by
  simp [identity, linearDet]

@[simp] theorem linearDet_translation (v : Point2) :
    (translation v).linearDet = 1 := by
  simp [translation, linearDet]

@[simp] theorem linearDet_uniformScale (s : ℝ) :
    (uniformScale s).linearDet = s ^ 2 := by
  simp [uniformScale, linearDet, pow_two]

@[simp] theorem linearDet_scaleXY (sx sy : ℝ) :
    (scaleXY sx sy).linearDet = sx * sy := by
  simp [scaleXY, linearDet]

@[simp] theorem linearDet_shearX (k : ℝ) :
    (shearX k).linearDet = 1 := by
  simp [shearX, linearDet]

@[simp] theorem linearDet_shearY (k : ℝ) :
    (shearY k).linearDet = 1 := by
  simp [shearY, linearDet]

@[simp] theorem linearDet_rotateQuarter :
    rotateQuarter.linearDet = 1 := by
  norm_num [rotateQuarter, linearDet]

@[simp] theorem linearDet_swapAxes :
    swapAxes.linearDet = -1 := by
  norm_num [swapAxes, linearDet]

/-- The affine translation constructor is exactly the existing point
translation primitive. -/
theorem mapPoint_translation (v p : Point2) :
    (translation v).mapPoint p = Point2.translate v p := by
  rcases v with ⟨vx, vy⟩
  rcases p with ⟨x, y⟩
  simp [translation, mapPoint, Point2.translate]

/-- The affine diagonal-scale constructor is exactly the existing primitive. -/
theorem mapPoint_scaleXY (sx sy : ℝ) (p : Point2) :
    (scaleXY sx sy).mapPoint p = Point2.scaleXY sx sy p := by
  rcases p with ⟨x, y⟩
  simp [scaleXY, mapPoint, Point2.scaleXY]

/-- The affine x-shear constructor is exactly the existing primitive. -/
theorem mapPoint_shearX (k : ℝ) (p : Point2) :
    (shearX k).mapPoint p = Point2.shearX k p := by
  rcases p with ⟨x, y⟩
  simp [shearX, mapPoint, Point2.shearX]
  ring

/-- The affine y-shear constructor is exactly the existing primitive. -/
theorem mapPoint_shearY (k : ℝ) (p : Point2) :
    (shearY k).mapPoint p = Point2.shearY k p := by
  rcases p with ⟨x, y⟩
  simp [shearY, mapPoint, Point2.shearY]
  ring

/-- The affine quarter-turn constructor is exactly the existing primitive. -/
theorem mapPoint_rotateQuarter (p : Point2) :
    rotateQuarter.mapPoint p = Point2.rotateQuarter p := by
  rcases p with ⟨x, y⟩
  simp [rotateQuarter, mapPoint, Point2.rotateQuarter]

/-- The affine axis-swap constructor is exactly the existing primitive. -/
theorem mapPoint_swapAxes (p : Point2) :
    swapAxes.mapPoint p = Point2.swapAxes p := by
  rcases p with ⟨x, y⟩
  simp [swapAxes, mapPoint, Point2.swapAxes]

/-- Any affine map with nonzero linear determinant preserves triangle
nondegeneracy. -/
def certifiedNondegenerate (F : Affine2) (hF : F.linearDet ≠ 0) :
    CertifiedTransform Triangle2 GeometryTransforms.Nondegenerate where
  run := F.mapTriangle
  staticCost := 1
  preserves := by
    intro T hT
    change T.det ≠ 0 at hT
    change (F.mapTriangle T).det ≠ 0
    rw [det_mapTriangle]
    exact mul_ne_zero hF hT

/-- Any orientation-preserving affine map preserves positive orientation. -/
def certifiedPositive (F : Affine2) (hF : 0 < F.linearDet) :
    CertifiedTransform Triangle2 GeometryTransforms.PositiveOrientation where
  run := F.mapTriangle
  staticCost := 1
  preserves := by
    intro T hT
    change 0 < T.det at hT
    change 0 < (F.mapTriangle T).det
    rw [det_mapTriangle]
    exact mul_pos hF hT

/-- Translation, viewed through the general affine theorem, is certified
orientation preserving. -/
def translationPositive (v : Point2) :
    CertifiedTransform Triangle2 GeometryTransforms.PositiveOrientation :=
  certifiedPositive (translation v) (by simp)

/-- Both shears are instances of the general affine certificate. -/
def shearXPositive (k : ℝ) :
    CertifiedTransform Triangle2 GeometryTransforms.PositiveOrientation :=
  certifiedPositive (shearX k) (by simp)

def shearYPositive (k : ℝ) :
    CertifiedTransform Triangle2 GeometryTransforms.PositiveOrientation :=
  certifiedPositive (shearY k) (by simp)

/-- Quarter rotation is an instance of the general affine certificate. -/
def rotateQuarterPositive :
    CertifiedTransform Triangle2 GeometryTransforms.PositiveOrientation :=
  certifiedPositive rotateQuarter (by simp)

/-- Axis swap is orientation reversing but remains nondegenerate. -/
def swapAxesNondegenerate :
    CertifiedTransform Triangle2 GeometryTransforms.Nondegenerate :=
  certifiedNondegenerate swapAxes (by norm_num)

/-- Positive-determinant diagonal scaling is an affine certificate. -/
def scaleXYPositive (sx sy : ℝ) (h : 0 < sx * sy) :
    CertifiedTransform Triangle2 GeometryTransforms.PositiveOrientation :=
  certifiedPositive (scaleXY sx sy) (by simpa using h)

/-- Nonzero diagonal scaling is an affine nondegeneracy certificate. -/
def scaleXYNondegenerate (sx sy : ℝ) (hsx : sx ≠ 0) (hsy : sy ≠ 0) :
    CertifiedTransform Triangle2 GeometryTransforms.Nondegenerate :=
  certifiedNondegenerate (scaleXY sx sy) (by
    simpa using mul_ne_zero hsx hsy)

/-- The exact determinant law immediately gives unsigned-area scaling. -/
theorem abs_det_mapTriangle (F : Affine2) (T : Triangle2) :
    |(F.mapTriangle T).det| = |F.linearDet| * |T.det| := by
  rw [det_mapTriangle, abs_mul]

end Affine2

end CACEFormal

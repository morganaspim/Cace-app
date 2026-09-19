import Mathlib
import CACEFormal.CertifiedComposition
import CACEFormal.P1RT0Element

namespace CACEFormal

/-!
# Low-cost exact geometry transforms

These are exact algebraic transforms for the existing two-dimensional P1/RT0
geometry. They are deliberately small building blocks for combinatorial proof
search and normalization:

* translation preserves signed area and orientation;
* x/y shears preserve signed area and orientation;
* quarter rotation preserves signed area and orientation;
* axis swap reverses orientation but preserves nondegeneracy;
* uniform and diagonal scaling have exact determinant scaling laws;
* certified composition chains these facts without reopening the proofs.

Translation, the two shears, nonzero diagonal scaling, and axis interchange are
also useful elementary generators for much larger affine transform families.
The full general affine/Piola theorem remains a separate formalization target.
-/

namespace Point2

/-- Translate a point by a fixed vector. -/
def translate (a p : Point2) : Point2 :=
  ⟨p.x + a.x, p.y + a.y⟩

/-- Uniformly scale a point about the origin. -/
def scale (s : ℝ) (p : Point2) : Point2 :=
  ⟨s * p.x, s * p.y⟩

/-- Scale the two coordinate axes independently. -/
def scaleXY (sx sy : ℝ) (p : Point2) : Point2 :=
  ⟨sx * p.x, sy * p.y⟩

/-- Elementary x-shear `(x,y) ↦ (x + k*y,y)`. -/
def shearX (k : ℝ) (p : Point2) : Point2 :=
  ⟨p.x + k * p.y, p.y⟩

/-- Elementary y-shear `(x,y) ↦ (x,y + k*x)`. -/
def shearY (k : ℝ) (p : Point2) : Point2 :=
  ⟨p.x, p.y + k * p.x⟩

/-- Exact counter-clockwise quarter turn `(x,y) ↦ (-y,x)`. -/
def rotateQuarter (p : Point2) : Point2 :=
  ⟨-p.y, p.x⟩

/-- Swap the two coordinate axes. -/
def swapAxes (p : Point2) : Point2 :=
  ⟨p.y, p.x⟩

end Point2

namespace Triangle2

/-- Translate every vertex by the same vector. -/
def translate (a : Point2) (T : Triangle2) : Triangle2 :=
  ⟨Point2.translate a T.p0, Point2.translate a T.p1, Point2.translate a T.p2⟩

/-- Uniformly scale every vertex about the origin. -/
def scale (s : ℝ) (T : Triangle2) : Triangle2 :=
  ⟨Point2.scale s T.p0, Point2.scale s T.p1, Point2.scale s T.p2⟩

/-- Scale x/y independently on every vertex. -/
def scaleXY (sx sy : ℝ) (T : Triangle2) : Triangle2 :=
  ⟨Point2.scaleXY sx sy T.p0, Point2.scaleXY sx sy T.p1, Point2.scaleXY sx sy T.p2⟩

/-- Apply the same x-shear to every vertex. -/
def shearX (k : ℝ) (T : Triangle2) : Triangle2 :=
  ⟨Point2.shearX k T.p0, Point2.shearX k T.p1, Point2.shearX k T.p2⟩

/-- Apply the same y-shear to every vertex. -/
def shearY (k : ℝ) (T : Triangle2) : Triangle2 :=
  ⟨Point2.shearY k T.p0, Point2.shearY k T.p1, Point2.shearY k T.p2⟩

/-- Rotate every vertex by 90 degrees counter-clockwise. -/
def rotateQuarter (T : Triangle2) : Triangle2 :=
  ⟨Point2.rotateQuarter T.p0, Point2.rotateQuarter T.p1, Point2.rotateQuarter T.p2⟩

/-- Swap x/y on every vertex. -/
def swapAxes (T : Triangle2) : Triangle2 :=
  ⟨Point2.swapAxes T.p0, Point2.swapAxes T.p1, Point2.swapAxes T.p2⟩

/-- Common translation leaves the signed area determinant unchanged. -/
@[simp] theorem det_translate (a : Point2) (T : Triangle2) :
    (translate a T).det = T.det := by
  rcases a with ⟨ax, ay⟩
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  dsimp [translate, Point2.translate, det]
  ring

/-- Uniform scaling multiplies the signed area determinant by `s^2`. -/
@[simp] theorem det_scale (s : ℝ) (T : Triangle2) :
    (scale s T).det = s ^ 2 * T.det := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  dsimp [scale, Point2.scale, det]
  ring

/-- Independent axis scaling multiplies the determinant by `sx*sy`. -/
@[simp] theorem det_scaleXY (sx sy : ℝ) (T : Triangle2) :
    (scaleXY sx sy T).det = (sx * sy) * T.det := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  dsimp [scaleXY, Point2.scaleXY, det]
  ring

/-- An x-shear is exactly area/orientation preserving. -/
@[simp] theorem det_shearX (k : ℝ) (T : Triangle2) :
    (shearX k T).det = T.det := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  dsimp [shearX, Point2.shearX, det]
  ring

/-- A y-shear is exactly area/orientation preserving. -/
@[simp] theorem det_shearY (k : ℝ) (T : Triangle2) :
    (shearY k T).det = T.det := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  dsimp [shearY, Point2.shearY, det]
  ring

/-- Quarter rotation is exactly area/orientation preserving. -/
@[simp] theorem det_rotateQuarter (T : Triangle2) :
    (rotateQuarter T).det = T.det := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  dsimp [rotateQuarter, Point2.rotateQuarter, det]
  ring

/-- Swapping coordinate axes reverses orientation. -/
@[simp] theorem det_swapAxes (T : Triangle2) :
    (swapAxes T).det = -T.det := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  dsimp [swapAxes, Point2.swapAxes, det]
  ring

/-- Coordinate-axis swapping preserves unsigned area. -/
theorem abs_det_swapAxes (T : Triangle2) :
    |(swapAxes T).det| = |T.det| := by
  rw [det_swapAxes, abs_neg]

/-- Recenter a triangle so its first vertex is at the origin. -/
def recenterAtP0 (T : Triangle2) : Triangle2 :=
  translate ⟨-T.p0.x, -T.p0.y⟩ T

@[simp] theorem recenterAtP0_p0 (T : Triangle2) :
    (recenterAtP0 T).p0 = ⟨0, 0⟩ := by
  rcases T with ⟨⟨x0, y0⟩, p1, p2⟩
  simp [recenterAtP0, translate, Point2.translate]

@[simp] theorem det_recenterAtP0 (T : Triangle2) :
    (recenterAtP0 T).det = T.det := by
  simp [recenterAtP0]

end Triangle2

namespace GeometryTransforms

/-- Positive signed determinant: the current orientation invariant. -/
def PositiveOrientation (T : Triangle2) : Prop := 0 < T.det

/-- Nonzero signed determinant: the exact nondegeneracy invariant. -/
def Nondegenerate (T : Triangle2) : Prop := T.det ≠ 0

/-- Translation is a one-step certified positive-orientation transform. -/
def translatePositive (a : Point2) :
    CertifiedTransform Triangle2 PositiveOrientation where
  run := Triangle2.translate a
  staticCost := 1
  preserves := by
    intro T h
    simpa [PositiveOrientation] using h

/-- Translation is also a one-step certified nondegeneracy transform. -/
def translateNondegenerate (a : Point2) :
    CertifiedTransform Triangle2 Nondegenerate where
  run := Triangle2.translate a
  staticCost := 1
  preserves := by
    intro T h
    simpa [Nondegenerate] using h

/-- An x-shear preserves positive orientation. -/
def shearXPositive (k : ℝ) : CertifiedTransform Triangle2 PositiveOrientation where
  run := Triangle2.shearX k
  staticCost := 1
  preserves := by
    intro T h
    simpa [PositiveOrientation] using h

/-- A y-shear preserves positive orientation. -/
def shearYPositive (k : ℝ) : CertifiedTransform Triangle2 PositiveOrientation where
  run := Triangle2.shearY k
  staticCost := 1
  preserves := by
    intro T h
    simpa [PositiveOrientation] using h

/-- A quarter turn preserves positive orientation. -/
def rotateQuarterPositive : CertifiedTransform Triangle2 PositiveOrientation where
  run := Triangle2.rotateQuarter
  staticCost := 1
  preserves := by
    intro T h
    simpa [PositiveOrientation] using h

/-- Any nonzero uniform scale preserves triangle nondegeneracy. -/
def scaleNondegenerate (s : ℝ) (hs : s ≠ 0) :
    CertifiedTransform Triangle2 Nondegenerate where
  run := Triangle2.scale s
  staticCost := 1
  preserves := by
    intro T h
    change T.det ≠ 0 at h
    change (Triangle2.scale s T).det ≠ 0
    rw [Triangle2.det_scale]
    exact mul_ne_zero (pow_ne_zero 2 hs) h

/-- Independent nonzero x/y scaling preserves triangle nondegeneracy. -/
def scaleXYNondegenerate (sx sy : ℝ) (hsx : sx ≠ 0) (hsy : sy ≠ 0) :
    CertifiedTransform Triangle2 Nondegenerate where
  run := Triangle2.scaleXY sx sy
  staticCost := 1
  preserves := by
    intro T h
    change T.det ≠ 0 at h
    change (Triangle2.scaleXY sx sy T).det ≠ 0
    rw [Triangle2.det_scaleXY]
    exact mul_ne_zero (mul_ne_zero hsx hsy) h

/-- Positive determinant axis scaling preserves positive orientation. -/
def scaleXYPositive (sx sy : ℝ) (hdet : 0 < sx * sy) :
    CertifiedTransform Triangle2 PositiveOrientation where
  run := Triangle2.scaleXY sx sy
  staticCost := 1
  preserves := by
    intro T h
    change 0 < T.det at h
    change 0 < (Triangle2.scaleXY sx sy T).det
    rw [Triangle2.det_scaleXY]
    exact mul_pos hdet h

/-- Swapping coordinate axes preserves nondegeneracy while reversing orientation. -/
def swapAxesNondegenerate : CertifiedTransform Triangle2 Nondegenerate where
  run := Triangle2.swapAxes
  staticCost := 1
  preserves := by
    intro T h
    change T.det ≠ 0 at h
    change (Triangle2.swapAxes T).det ≠ 0
    rw [Triangle2.det_swapAxes]
    exact neg_ne_zero.mpr h

/-- Recentering at the first vertex preserves positive orientation exactly. -/
def recenterPositive : CertifiedTransform Triangle2 PositiveOrientation where
  run := Triangle2.recenterAtP0
  staticCost := 1
  preserves := by
    intro T h
    simpa [PositiveOrientation] using h

/-- Translation followed by nonzero uniform scaling preserves nondegeneracy. -/
def translateThenScaleNondegenerate (a : Point2) (s : ℝ) (hs : s ≠ 0) :
    CertifiedTransform Triangle2 Nondegenerate :=
  CertifiedTransform.compose2 (translateNondegenerate a) (scaleNondegenerate s hs)

/-- A useful four-stage orientation-safe normalizer assembled only from exact
low-cost primitives: recenter, x-shear, y-shear, quarter-turn. -/
def elementaryPositiveChain (kx ky : ℝ) : CertifiedTransform Triangle2 PositiveOrientation :=
  CertifiedTransform.compose4
    recenterPositive
    (shearXPositive kx)
    (shearYPositive ky)
    rotateQuarterPositive

/-- The four-stage elementary chain inherits positive orientation automatically. -/
theorem elementaryPositiveChain_preserves
    (kx ky : ℝ) (T : Triangle2) (hT : PositiveOrientation T) :
    PositiveOrientation ((elementaryPositiveChain kx ky).run T) :=
  (elementaryPositiveChain kx ky).preserves T hT

/-- Its declared cost is exactly four primitive stages. -/
@[simp] theorem elementaryPositiveChain_staticCost (kx ky : ℝ) :
    (elementaryPositiveChain kx ky).staticCost = 4 := by
  rfl

end GeometryTransforms

end CACEFormal

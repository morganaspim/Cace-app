import Mathlib
import CACEFormal.CertifiedComposition
import CACEFormal.P1RT0Element

namespace CACEFormal

/-!
# Low-cost exact geometry transforms

These are exact algebraic transforms for the existing two-dimensional P1/RT0
geometry.  They are deliberately small building blocks for future combinatorial
proof search:

* translation preserves signed area and orientation;
* nonzero uniform scaling preserves nondegeneracy and scales the determinant by
  the exact factor `s^2`;
* swapping coordinate axes flips orientation but preserves nondegeneracy;
* certified composition can chain these facts without reopening the proofs.

The natural next extension is a general invertible affine map together with the
full Piola transform law; that remains separate from the exact facts proved here.
-/

namespace Point2

/-- Translate a point by a fixed vector. -/
def translate (a p : Point2) : Point2 :=
  ⟨p.x + a.x, p.y + a.y⟩

/-- Uniformly scale a point about the origin. -/
def scale (s : ℝ) (p : Point2) : Point2 :=
  ⟨s * p.x, s * p.y⟩

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

/-- Swapping coordinate axes preserves nondegeneracy while reversing orientation. -/
def swapAxesNondegenerate : CertifiedTransform Triangle2 Nondegenerate where
  run := Triangle2.swapAxes
  staticCost := 1
  preserves := by
    intro T h
    simpa [Nondegenerate] using h

/-- Recentering at the first vertex preserves positive orientation exactly. -/
def recenterPositive : CertifiedTransform Triangle2 PositiveOrientation where
  run := Triangle2.recenterAtP0
  staticCost := 1
  preserves := by
    intro T h
    simpa [PositiveOrientation] using h

/--
A reusable two-stage normalization: translate, then apply a nonzero uniform scale.
Its nondegeneracy proof is inherited entirely from the two certified components.
-/
def translateThenScaleNondegenerate (a : Point2) (s : ℝ) (hs : s ≠ 0) :
    CertifiedTransform Triangle2 Nondegenerate :=
  CertifiedTransform.compose2 (translateNondegenerate a) (scaleNondegenerate s hs)

/-- Four translations can be combined with no new geometric proof obligation. -/
theorem fourTranslations_preserve_positiveOrientation
    (a b c d : Point2) (T : Triangle2) (hT : PositiveOrientation T) :
    PositiveOrientation
      ((CertifiedTransform.compose4
        (translatePositive a)
        (translatePositive b)
        (translatePositive c)
        (translatePositive d)).run T) := by
  exact CertifiedTransform.compose4_preserves
    (translatePositive a)
    (translatePositive b)
    (translatePositive c)
    (translatePositive d)
    T hT

end GeometryTransforms

end CACEFormal

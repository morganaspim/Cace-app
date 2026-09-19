import Mathlib
import CACEFormal.ExteriorPowerTransport
import CACEFormal.Piola
import CACEFormal.P1RT0Element

namespace CACEFormal

/-!
# Dual-blade / Piola unification in two dimensions

This file connects the exterior-power layer to the existing contravariant
Piola/cofactor layer.

For an oriented edge tangent `t`, define the clockwise Hodge dual

`dual t = (t_y, -t_x)`.

That is exactly the outward normal-measure vector used by the P1/RT0 edge
formula.  The central identity is

`cof(A) (dual t) = dual (A t)`.

Thus transformed tangent blades, normal-measure vectors, cofactors, and
contravariant Piola flux are different views of one exact graded transport.
-/

namespace DualBladePiola

open ExteriorPower2

/-- Clockwise quarter-turn / 2D Hodge dual on grade-1 vectors. -/
def dual (v : Point2) : Point2 :=
  ⟨v.y, -v.x⟩

/-- Inverse of `dual`: counter-clockwise quarter-turn. -/
def dualInv (v : Point2) : Point2 :=
  ⟨-v.y, v.x⟩

/-- Euclidean scalar pairing used for flux. -/
def dot (u v : Point2) : ℝ :=
  u.x * v.x + u.y * v.y

@[simp] theorem dualInv_dual (v : Point2) :
    dualInv (dual v) = v := by
  rcases v with ⟨x, y⟩
  simp [dual, dualInv]

@[simp] theorem dual_dualInv (v : Point2) :
    dual (dualInv v) = v := by
  rcases v with ⟨x, y⟩
  simp [dual, dualInv]

/-- The cofactor action is the grade-1 action conjugated by 2D duality. -/
theorem cofactor_eq_dual_grade1_dualInv (F : Affine2) (n : Point2) :
    F.cofactorNormal n =
      dual (grade1 F (dualInv n)) := by
  rcases F with ⟨a, b, c, d, tx, ty⟩
  rcases n with ⟨nx, ny⟩
  ext <;>
    dsimp [Affine2.cofactorNormal, dual, dualInv, grade1] <;>
    ring

/-- A tangent blade and its normal-measure dual transform compatibly:
`cof(A) (dual t) = dual (A t)`. -/
theorem cofactor_dual_grade1 (F : Affine2) (t : Point2) :
    F.cofactorNormal (dual t) =
      dual (grade1 F t) := by
  rw [cofactor_eq_dual_grade1_dualInv, dualInv_dual]

/-- Cofactor actions compose in the same order as the underlying linear maps. -/
@[simp] theorem cofactor_comp (outer inner : Affine2) (n : Point2) :
    (Affine2.comp outer inner).cofactorNormal n =
      outer.cofactorNormal (inner.cofactorNormal n) := by
  rcases outer with ⟨oa, ob, oc, od, otx, oty⟩
  rcases inner with ⟨ia, ib, ic, id, itx, ity⟩
  rcases n with ⟨nx, ny⟩
  ext <;>
    dsimp [Affine2.comp, Affine2.cofactorNormal] <;>
    ring

/-- Cofactor action of a fused affine chain. -/
@[simp] theorem cofactor_chain_cons
    (F : Affine2) (Fs : List Affine2) (n : Point2) :
    (Affine2.chain (F :: Fs)).cofactorNormal n =
      (Affine2.chain Fs).cofactorNormal (F.cofactorNormal n) := by
  simp [Affine2.chain]

/-- Batch splitting preserves the normal/cofactor action of an arbitrary chain. -/
theorem cofactor_chain_append
    (left right : List Affine2) (n : Point2) :
    (Affine2.chain (left ++ right)).cofactorNormal n =
      (Affine2.chain right).cofactorNormal
        ((Affine2.chain left).cofactorNormal n) := by
  induction left generalizing n with
  | nil =>
      rcases n with ⟨nx, ny⟩
      simp [Affine2.chain, Affine2.identity, Affine2.cofactorNormal]
  | cons F Fs ih =>
      simp only [List.cons_append, cofactor_chain_cons]
      exact ih (F.cofactorNormal n)

/-- The P1/RT0 oriented edge normal-measure vector is exactly the dual of the
edge tangent blade. -/
def edgeNormalMeasure (a b : Point2) : Point2 :=
  dual (edgeVector a b)

theorem edgeNormalMeasure_eq_p1rt0 (a b : Point2) :
    edgeNormalMeasure a b =
      ⟨P1RT0Element.edgeNormalX a b,
       P1RT0Element.edgeNormalY a b⟩ := by
  rcases a with ⟨ax, ay⟩
  rcases b with ⟨bx, by_⟩
  rfl

/-- Affine edge mapping transports the full oriented normal-measure vector by
the cofactor. -/
theorem edgeNormalMeasure_map
    (F : Affine2) (a b : Point2) :
    edgeNormalMeasure (F.mapPoint a) (F.mapPoint b) =
      F.cofactorNormal (edgeNormalMeasure a b) := by
  rw [edgeNormalMeasure, edgeVector_mapPoint]
  symm
  exact cofactor_dual_grade1 F (edgeVector a b)

/-- Existing contravariant Piola transport is exactly determinant-normalized
grade-1 transport. -/
theorem piolaVector_eq_grade1_div (F : Affine2) (q : Point2) :
    F.piolaVector q =
      ⟨(grade1 F q).x / F.linearDet,
       (grade1 F q).y / F.linearDet⟩ := by
  rfl

/-- Piola transforms compose exactly for nonsingular affine stages. -/
theorem piola_comp
    (outer inner : Affine2) (q : Point2)
    (houter : outer.linearDet ≠ 0)
    (hinner : inner.linearDet ≠ 0) :
    (Affine2.comp outer inner).piolaVector q =
      outer.piolaVector (inner.piolaVector q) := by
  have hcomp : (Affine2.comp outer inner).linearDet ≠ 0 := by
    rw [Affine2.linearDet_comp]
    exact mul_ne_zero houter hinner
  rcases outer with ⟨oa, ob, oc, od, otx, oty⟩
  rcases inner with ⟨ia, ib, ic, id, itx, ity⟩
  rcases q with ⟨qx, qy⟩
  change oa * od - ob * oc ≠ 0 at houter
  change ia * id - ib * ic ≠ 0 at hinner
  ext <;>
    dsimp [Affine2.comp, Affine2.piolaVector, Affine2.linearDet] at hcomp ⊢ <;>
    field_simp [houter, hinner, hcomp] <;>
    ring

/-- A chain of nonsingular affine stages has nonsingular fused linear part. -/
theorem linearDet_chain_ne_zero_of_forall
    (Fs : List Affine2)
    (h : ∀ F ∈ Fs, F.linearDet ≠ 0) :
    (Affine2.chain Fs).linearDet ≠ 0 := by
  induction Fs with
  | nil =>
      simp [Affine2.chain]
  | cons F Fs ih =>
      have hF : F.linearDet ≠ 0 := h F (by simp)
      have htail : ∀ G ∈ Fs, G.linearDet ≠ 0 := by
        intro G hG
        exact h G (by simp [hG])
      rw [Affine2.chain, Affine2.linearDet_comp]
      exact mul_ne_zero (ih htail) hF

/-- Sequential Piola execution for a primitive affine chain. -/
noncomputable def piolaSequence : List Affine2 → Point2 → Point2
  | [], q => q
  | F :: Fs, q => piolaSequence Fs (F.piolaVector q)

/-- Fusing any nonsingular affine chain does not change its sequential Piola
action. -/
theorem piolaVector_chain_eq_sequence
    (Fs : List Affine2)
    (h : ∀ F ∈ Fs, F.linearDet ≠ 0)
    (q : Point2) :
    (Affine2.chain Fs).piolaVector q =
      piolaSequence Fs q := by
  induction Fs generalizing q with
  | nil =>
      rcases q with ⟨qx, qy⟩
      simp [Affine2.chain, Affine2.identity, Affine2.piolaVector,
        Affine2.linearDet, piolaSequence]
  | cons F Fs ih =>
      have hF : F.linearDet ≠ 0 := h F (by simp)
      have htail : ∀ G ∈ Fs, G.linearDet ≠ 0 := by
        intro G hG
        exact h G (by simp [hG])
      rw [Affine2.chain]
      rw [piola_comp (Affine2.chain Fs) F q
        (linearDet_chain_ne_zero_of_forall Fs htail) hF]
      exact ih htail (F.piolaVector q)

/-- Flux preservation restated entirely in dual-blade language. -/
theorem piola_dualBlade_flux
    (F : Affine2) (q t : Point2)
    (hdet : F.linearDet ≠ 0) :
    dot (F.piolaVector q) (dual (grade1 F t)) =
      dot q (dual t) := by
  rw [← cofactor_dual_grade1]
  simpa [dot] using
    Affine2.piola_cofactor_flux F q (dual t) hdet

/-- Edge form of the same theorem: transform tangent geometry by grade 1,
dualize it into normal measure, and the Piola flux is unchanged. -/
theorem piola_edgeNormalMeasure_flux
    (F : Affine2) (q a b : Point2)
    (hdet : F.linearDet ≠ 0) :
    dot (F.piolaVector q)
        (edgeNormalMeasure (F.mapPoint a) (F.mapPoint b)) =
      dot q (edgeNormalMeasure a b) := by
  rw [edgeNormalMeasure_map]
  simpa [dot] using
    Affine2.piola_cofactor_flux F q (edgeNormalMeasure a b) hdet

end DualBladePiola

end CACEFormal

import Mathlib.Data.Real.Basic
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring
import CACEFormal.AffineGeometry

namespace CACEFormal

/-- Algebraic 2D diagonal-affine Piola fixture used to pin the normal-flux scaling law.
Kept as a compact regression theorem even though the general affine identity below now
subsumes it. -/
theorem diagonal_piola_flux_fixture
    (qx qy sx sy : ℝ) (hsx : sx ≠ 0) (hsy : sy ≠ 0) :
    (-(sx * qx / (sx * sy))) * sy = -qx := by
  field_simp [hsx, hsy]

namespace Affine2

/-- Contravariant Piola transform of a vector for the linear part of `F`.
The caller supplies nonzero determinant when proving identities that divide by it. -/
def piolaVector (F : Affine2) (q : Point2) : Point2 :=
  ⟨(F.a * q.x + F.b * q.y) / F.linearDet,
   (F.c * q.x + F.d * q.y) / F.linearDet⟩

/-- Cofactor action on an unnormalized normal/covector:
`cof(A) n = (d nx - c ny, -b nx + a ny)`.

For affine edge maps this cofactor carries the normal together with the edge
measure, which is exactly the quantity paired with the contravariant Piola
field in a flux integral. -/
def cofactorNormal (F : Affine2) (n : Point2) : Point2 :=
  ⟨F.d * n.x - F.c * n.y,
   -F.b * n.x + F.a * n.y⟩

/-- Exact 2D affine Piola/cofactor flux identity.

This is the algebraic core of normal-flux preservation:
`Piola_F(q) · cof(A)n = q · n`.
Translation parameters do not enter the identity. -/
theorem piola_cofactor_flux
    (F : Affine2) (q n : Point2) (hdet : F.linearDet ≠ 0) :
    (F.piolaVector q).x * (F.cofactorNormal n).x +
        (F.piolaVector q).y * (F.cofactorNormal n).y =
      q.x * n.x + q.y * n.y := by
  rcases F with ⟨a, b, c, d, tx, ty⟩
  rcases q with ⟨qx, qy⟩
  rcases n with ⟨nx, ny⟩
  change a * d - b * c ≠ 0 at hdet
  dsimp [piolaVector, cofactorNormal, linearDet]
  field_simp [hdet]
  ring

/-- The cofactor flux identity is independent of the affine translation. -/
theorem piola_cofactor_flux_translation_free
    (a b c d tx ty qx qy nx ny : ℝ)
    (hdet : a * d - b * c ≠ 0) :
    let F : Affine2 := ⟨a, b, c, d, tx, ty⟩
    let q : Point2 := ⟨qx, qy⟩
    let n : Point2 := ⟨nx, ny⟩
    (F.piolaVector q).x * (F.cofactorNormal n).x +
        (F.piolaVector q).y * (F.cofactorNormal n).y =
      q.x * n.x + q.y * n.y := by
  dsimp
  apply piola_cofactor_flux
  simpa [linearDet] using hdet

end Affine2

end CACEFormal

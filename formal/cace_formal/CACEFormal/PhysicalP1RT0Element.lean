import Mathlib
import CACEFormal.P1RT0Element
import CACEFormal.MeshElementGeometry

namespace CACEFormal

/-!
# Positive-orientation physical semantics for exact P1/RT0 elements

`P1RT0Element` deliberately uses the signed triangle determinant.  Its
identities are exact oriented algebra and remain true for either vertex
orientation.  Ordinary geometric area uses `|det|/2`.

This module makes that distinction explicit.  It defines unsigned cell
functionals and proves that they coincide with the oriented functionals when
the triangle is positively oriented.  Certified mesh triangles satisfy that
positivity automatically through `MeshCertificate.signedJacobian_pos`.
-/

namespace PhysicalP1RT0Element

/-- Unsigned geometric cell pairing, using ordinary area rather than signed
oriented area. -/
noncomputable def cellPairing (T : Triangle2) (v : P1Affine) (q : RT0Affine) : ℝ :=
  |T.det| / 6 *
    (q.dotGrad v T.p0 + q.dotGrad v T.p1 + q.dotGrad v T.p2)

/-- Unsigned geometric divergence contribution. -/
noncomputable def cellDivergence (T : Triangle2) (v : P1Affine) (q : RT0Affine) : ℝ :=
  -(|T.det| / 6 * q.divergence *
    (v.eval T.p0 + v.eval T.p1 + v.eval T.p2))

/-- On a positively oriented triangle, the signed exact cell pairing is the
ordinary unsigned physical integral. -/
theorem cellPairing_eq_oriented_of_pos
    (T : Triangle2) (v : P1Affine) (q : RT0Affine) (hT : 0 < T.det) :
    cellPairing T v q = P1RT0Element.cellPairing T v q := by
  simp [cellPairing, P1RT0Element.cellPairing, abs_of_pos hT]

/-- On a positively oriented triangle, the signed exact divergence contribution
is the ordinary unsigned physical divergence contribution. -/
theorem cellDivergence_eq_oriented_of_pos
    (T : Triangle2) (v : P1Affine) (q : RT0Affine) (hT : 0 < T.det) :
    cellDivergence T v q = P1RT0Element.cellDivergence T v q := by
  simp [cellDivergence, P1RT0Element.cellDivergence, abs_of_pos hT]

/-- Physical Green identity for a positively oriented element.  The boundary
term is the existing oriented edge formula; positivity certifies that the
stored edge order is counter-clockwise, so this is the physical outward
normal-measure convention used by the mesh layer. -/
theorem local_green_identity_of_pos
    (T : Triangle2) (v : P1Affine) (q : RT0Affine) (hT : 0 < T.det) :
    cellPairing T v q =
      cellDivergence T v q + P1RT0Element.cellFacePairing T v q := by
  rw [cellPairing_eq_oriented_of_pos T v q hT,
      cellDivergence_eq_oriented_of_pos T v q hT]
  exact P1RT0Element.local_green_identity T v q

/-- Certified mesh elements automatically support the physical interpretation of
the exact oriented cell pairing. -/
theorem mesh_cellPairing_eq_oriented
    (mesh : MeshCertificate) (K : Fin mesh.triangleCount)
    (v : P1Affine) (q : RT0Affine) :
    cellPairing (MeshElementGeometry.realTriangle mesh K) v q =
      P1RT0Element.cellPairing (MeshElementGeometry.realTriangle mesh K) v q :=
  cellPairing_eq_oriented_of_pos _ _ _
    (MeshElementGeometry.realTriangle_det_pos mesh K)

/-- Certified mesh elements automatically support the physical interpretation of
the exact oriented divergence term. -/
theorem mesh_cellDivergence_eq_oriented
    (mesh : MeshCertificate) (K : Fin mesh.triangleCount)
    (v : P1Affine) (q : RT0Affine) :
    cellDivergence (MeshElementGeometry.realTriangle mesh K) v q =
      P1RT0Element.cellDivergence (MeshElementGeometry.realTriangle mesh K) v q :=
  cellDivergence_eq_oriented_of_pos _ _ _
    (MeshElementGeometry.realTriangle_det_pos mesh K)

/-- Therefore every certified mesh element has a physical, positive-area local
Green identity derived from the exact signed algebra. -/
theorem mesh_local_green_identity
    (mesh : MeshCertificate) (K : Fin mesh.triangleCount)
    (v : P1Affine) (q : RT0Affine) :
    cellPairing (MeshElementGeometry.realTriangle mesh K) v q =
      cellDivergence (MeshElementGeometry.realTriangle mesh K) v q +
        P1RT0Element.cellFacePairing
          (MeshElementGeometry.realTriangle mesh K) v q :=
  local_green_identity_of_pos _ _ _
    (MeshElementGeometry.realTriangle_det_pos mesh K)

end PhysicalP1RT0Element

end CACEFormal

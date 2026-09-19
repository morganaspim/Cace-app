import Mathlib
import CACEFormal.MeshCertificate
import CACEFormal.P1RT0Element

namespace CACEFormal

/-!
# Certified mesh-to-element geometry bridge

`MeshCertificate` stores exact rational vertex geometry and connectivity.
This module turns that stored geometry into the `Triangle2` objects consumed
by the P1/RT0 element layer and proves that the resulting real determinant is
exactly the certified signed Jacobian.

The purpose of this bridge is to prevent a mesh certificate and an unrelated
`Fin triangleCount → Triangle2` function from silently describing different
geometries.
-/

namespace MeshElementGeometry

/-- Exact rational mesh vertex embedded into the real element geometry. -/
def realPoint (mesh : MeshCertificate) (v : Fin mesh.vertexCount) : Point2 :=
  ⟨(mesh.vertexX v : ℝ), (mesh.vertexY v : ℝ)⟩

/-- Canonical real triangle determined only by the certified mesh geometry. -/
def realTriangle
    (mesh : MeshCertificate) (K : Fin mesh.triangleCount) : Triangle2 :=
  ⟨realPoint mesh (mesh.triangleVertex K 0),
   realPoint mesh (mesh.triangleVertex K 1),
   realPoint mesh (mesh.triangleVertex K 2)⟩

@[simp] theorem realTriangle_p0
    (mesh : MeshCertificate) (K : Fin mesh.triangleCount) :
    (realTriangle mesh K).p0 =
      realPoint mesh (mesh.triangleVertex K 0) := rfl

@[simp] theorem realTriangle_p1
    (mesh : MeshCertificate) (K : Fin mesh.triangleCount) :
    (realTriangle mesh K).p1 =
      realPoint mesh (mesh.triangleVertex K 1) := rfl

@[simp] theorem realTriangle_p2
    (mesh : MeshCertificate) (K : Fin mesh.triangleCount) :
    (realTriangle mesh K).p2 =
      realPoint mesh (mesh.triangleVertex K 2) := rfl

/-- The real element determinant is exactly the rational Jacobian stored and
proved by the mesh certificate. -/
theorem realTriangle_det
    (mesh : MeshCertificate) (K : Fin mesh.triangleCount) :
    (realTriangle mesh K).det = (mesh.signedJacobian K : ℝ) := by
  simp only [realTriangle, realPoint, Triangle2.det]
  exact_mod_cast (mesh.signedJacobian_formula K).symm

/-- Every canonical element triangle produced from a mesh certificate is
strictly positively oriented. -/
theorem realTriangle_det_pos
    (mesh : MeshCertificate) (K : Fin mesh.triangleCount) :
    0 < (realTriangle mesh K).det := by
  rw [realTriangle_det]
  exact_mod_cast mesh.signedJacobian_pos K

/-- Hence every canonical element triangle is nondegenerate. -/
theorem realTriangle_det_ne_zero
    (mesh : MeshCertificate) (K : Fin mesh.triangleCount) :
    (realTriangle mesh K).det ≠ 0 :=
  ne_of_gt (realTriangle_det_pos mesh K)

end MeshElementGeometry

end CACEFormal

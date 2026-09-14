import Mathlib
import CACEFormal.MeshCombinatorics

namespace CACEFormal

/--
General finite triangular-mesh certificate used from v3.23 onward.

The certificate is deliberately finite and combinatorial.  It records exactly the
orientation/ownership information needed by later P1/RT0 assembly theorems while
keeping continuum H¹/H(div) trace theory outside this layer.
-/
structure MeshCertificate where
  triangleCount : Nat
  edgeCount : Nat
  interiorEdgeCount : Nat
  boundaryEdgeCount : Nat

  /-- Signed affine Jacobian determinant for each triangle. -/
  signedJacobian : Fin triangleCount → ℚ
  /-- Every triangle is positively oriented and nondegenerate. -/
  signedJacobian_pos : ∀ K, 0 < signedJacobian K

  /-- Canonical global edge id attached to every local triangle edge. -/
  localEdge : Fin triangleCount → Fin 3 → Fin edgeCount
  /-- Orientation of the local edge relative to its canonical global orientation. -/
  localSign : Fin triangleCount → Fin 3 → OrientationSign

  /-- Global id of every certified interior edge. -/
  interiorEdge : Fin interiorEdgeCount → Fin edgeCount
  interiorLeftCell : Fin interiorEdgeCount → Fin triangleCount
  interiorLeftSlot : Fin interiorEdgeCount → Fin 3
  interiorRightCell : Fin interiorEdgeCount → Fin triangleCount
  interiorRightSlot : Fin interiorEdgeCount → Fin 3
  interior_left_edge : ∀ i,
    localEdge (interiorLeftCell i) (interiorLeftSlot i) = interiorEdge i
  interior_right_edge : ∀ i,
    localEdge (interiorRightCell i) (interiorRightSlot i) = interiorEdge i
  /-- The two local orientations of an interior edge are opposite. -/
  interior_signs_opposite : ∀ i,
    localSign (interiorRightCell i) (interiorRightSlot i) =
      (localSign (interiorLeftCell i) (interiorLeftSlot i)).opposite

  /-- Global id and unique local owner of every certified boundary edge. -/
  boundaryEdge : Fin boundaryEdgeCount → Fin edgeCount
  boundaryCell : Fin boundaryEdgeCount → Fin triangleCount
  boundarySlot : Fin boundaryEdgeCount → Fin 3
  boundaryLabel : Fin boundaryEdgeCount → String
  boundary_edge_matches : ∀ b,
    localEdge (boundaryCell b) (boundarySlot b) = boundaryEdge b

  /--
  Total ownership classifier for global edges.  The two following fields force every
  declared interior/boundary record to map back to itself, which rules out duplicate
  ids within either family and prevents an edge from being both interior and boundary.
  -/
  edgeOwner : Fin edgeCount → Sum (Fin interiorEdgeCount) (Fin boundaryEdgeCount)
  interior_owned : ∀ i, edgeOwner (interiorEdge i) = Sum.inl i
  boundary_owned : ∀ b, edgeOwner (boundaryEdge b) = Sum.inr b

namespace MeshCertificate

/-- Positive signed Jacobians are, in particular, nonzero. -/
theorem signedJacobian_ne_zero (mesh : MeshCertificate) (K : Fin mesh.triangleCount) :
    mesh.signedJacobian K ≠ 0 :=
  ne_of_gt (mesh.signedJacobian_pos K)

/-- Canonical interior edge ids are injective. -/
theorem interiorEdge_injective (mesh : MeshCertificate) :
    Function.Injective mesh.interiorEdge := by
  intro i j h
  have howner := congrArg mesh.edgeOwner h
  rw [mesh.interior_owned i, mesh.interior_owned j] at howner
  exact Sum.inl.inj howner

/-- Canonical boundary edge ids are injective. -/
theorem boundaryEdge_injective (mesh : MeshCertificate) :
    Function.Injective mesh.boundaryEdge := by
  intro i j h
  have howner := congrArg mesh.edgeOwner h
  rw [mesh.boundary_owned i, mesh.boundary_owned j] at howner
  exact Sum.inr.inj howner

/-- No certified global edge can simultaneously be interior and boundary. -/
theorem interior_boundary_disjoint (mesh : MeshCertificate)
    (i : Fin mesh.interiorEdgeCount) (b : Fin mesh.boundaryEdgeCount) :
    mesh.interiorEdge i ≠ mesh.boundaryEdge b := by
  intro h
  have howner := congrArg mesh.edgeOwner h
  rw [mesh.interior_owned i, mesh.boundary_owned b] at howner
  contradiction

end MeshCertificate

end CACEFormal

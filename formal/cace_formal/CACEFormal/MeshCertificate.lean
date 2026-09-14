import Mathlib
import CACEFormal.MeshCombinatorics

namespace CACEFormal

/-- Start slot for the canonical directed local edge of a triangle. -/
def localEdgeStartSlot (s : Fin 3) : Fin 3 :=
  match s.val with
  | 0 => 0
  | 1 => 1
  | _ => 2

/-- End slot for the canonical directed local edge of a triangle. -/
def localEdgeEndSlot (s : Fin 3) : Fin 3 :=
  match s.val with
  | 0 => 1
  | 1 => 2
  | _ => 0

/--
General exact finite triangular-mesh certificate used from v3.23 onward.

Unlike the fixed v3.22 fixture, this object carries the rational vertex geometry,
triangle connectivity, canonical edge geometry, local-to-global orientation, and
complete interior/boundary ownership data. The positivity proof is tied to the
actual affine Jacobian formula rather than to an unrelated asserted number.

This remains a finite discrete certificate. It does not claim the later
continuum H¹/H(div) normal-trace or density theorems.
-/
structure MeshCertificate where
  vertexCount : Nat
  triangleCount : Nat
  edgeCount : Nat
  interiorEdgeCount : Nat
  boundaryEdgeCount : Nat

  /-- Exact rational vertex coordinates. -/
  vertexX : Fin vertexCount → ℚ
  vertexY : Fin vertexCount → ℚ

  /-- Three ordered vertex ids of every counter-clockwise triangle. -/
  triangleVertex : Fin triangleCount → Fin 3 → Fin vertexCount
  triangle_v01_ne : ∀ K, triangleVertex K 0 ≠ triangleVertex K 1
  triangle_v12_ne : ∀ K, triangleVertex K 1 ≠ triangleVertex K 2
  triangle_v20_ne : ∀ K, triangleVertex K 2 ≠ triangleVertex K 0

  /-- Signed affine Jacobian determinant for each triangle. -/
  signedJacobian : Fin triangleCount → ℚ
  /-- The stored determinant is exactly the determinant computed from the vertices. -/
  signedJacobian_formula : ∀ K,
    signedJacobian K =
      (vertexX (triangleVertex K 1) - vertexX (triangleVertex K 0)) *
        (vertexY (triangleVertex K 2) - vertexY (triangleVertex K 0)) -
      (vertexY (triangleVertex K 1) - vertexY (triangleVertex K 0)) *
        (vertexX (triangleVertex K 2) - vertexX (triangleVertex K 0))
  /-- Every triangle is positively oriented and nondegenerate. -/
  signedJacobian_pos : ∀ K, 0 < signedJacobian K

  /-- Canonical ordered endpoints of each global edge. -/
  edgeVertexLo : Fin edgeCount → Fin vertexCount
  edgeVertexHi : Fin edgeCount → Fin vertexCount
  /-- Canonical endpoint ordering also proves that an edge has two distinct vertices. -/
  edge_vertices_canonical : ∀ e, (edgeVertexLo e).val < (edgeVertexHi e).val

  /-- Canonical global edge id attached to every local triangle edge. -/
  localEdge : Fin triangleCount → Fin 3 → Fin edgeCount
  /-- Orientation of the directed local edge relative to its canonical global orientation. -/
  localSign : Fin triangleCount → Fin 3 → OrientationSign
  /--
  Local edge ids and signs are tied to the actual triangle/global-edge endpoints.
  Pair equality is definitionally convenient for generated certificates and is
  equivalent to the two endpoint equalities componentwise.
  -/
  local_edge_geometry : ∀ K s,
    let e := localEdge K s
    let u := triangleVertex K (localEdgeStartSlot s)
    let v := triangleVertex K (localEdgeEndSlot s)
    (edgeVertexLo e, edgeVertexHi e) =
      match localSign K s with
      | .pos => (u, v)
      | .neg => (v, u)

  /-- Global id of every certified interior edge. -/
  interiorEdge : Fin interiorEdgeCount → Fin edgeCount
  interiorLeftCell : Fin interiorEdgeCount → Fin triangleCount
  interiorLeftSlot : Fin interiorEdgeCount → Fin 3
  interiorRightCell : Fin interiorEdgeCount → Fin triangleCount
  interiorRightSlot : Fin interiorEdgeCount → Fin 3
  interior_cells_distinct : ∀ i, interiorLeftCell i ≠ interiorRightCell i
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
  boundary_label_nonempty : ∀ b, boundaryLabel b ≠ ""
  boundary_edge_matches : ∀ b,
    localEdge (boundaryCell b) (boundarySlot b) = boundaryEdge b

  /--
  Total ownership classifier for global edges. Declared records map back to
  themselves, ruling out duplicate global ids within either family and preventing
  an edge from simultaneously being interior and boundary.
  -/
  edgeOwner : Fin edgeCount → Sum (Fin interiorEdgeCount) (Fin boundaryEdgeCount)
  interior_owned : ∀ i, edgeOwner (interiorEdge i) = Sum.inl i
  boundary_owned : ∀ b, edgeOwner (boundaryEdge b) = Sum.inr b

  /--
  Ownership is complete for every local triangle-edge occurrence. Thus a certified
  interior edge has only its declared two local occurrences and a certified boundary
  edge has only its declared single occurrence; no hidden duplicate incidence can be
  smuggled into `localEdge`.
  -/
  local_edge_complete : ∀ K s,
    match edgeOwner (localEdge K s) with
    | Sum.inl i =>
        (K = interiorLeftCell i ∧ s = interiorLeftSlot i) ∨
        (K = interiorRightCell i ∧ s = interiorRightSlot i)
    | Sum.inr b => K = boundaryCell b ∧ s = boundarySlot b

namespace MeshCertificate

/-- Positive signed Jacobians are, in particular, nonzero. -/
theorem signedJacobian_ne_zero (mesh : MeshCertificate) (K : Fin mesh.triangleCount) :
    mesh.signedJacobian K ≠ 0 :=
  ne_of_gt (mesh.signedJacobian_pos K)

/-- Canonical global edges have distinct endpoint ids. -/
theorem edgeVertex_ne (mesh : MeshCertificate) (e : Fin mesh.edgeCount) :
    mesh.edgeVertexLo e ≠ mesh.edgeVertexHi e := by
  intro h
  have hlt := mesh.edge_vertices_canonical e
  rw [h] at hlt
  exact (Nat.lt_irrefl _ hlt)

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
  cases howner

end MeshCertificate

end CACEFormal

import Mathlib
import CACEFormal.MeshCertificate

namespace CACEFormal.Generated

open CACEFormal

/-- Exact square-with-center vertex x-coordinates. -/
def v323VertexX (v : Fin 5) : ℚ :=
  match v.val with
  | 0 => 0
  | 1 => 1
  | 2 => 1
  | 3 => 0
  | _ => 1 / 2

/-- Exact square-with-center vertex y-coordinates. -/
def v323VertexY (v : Fin 5) : ℚ :=
  match v.val with
  | 0 => 0
  | 1 => 0
  | 2 => 1
  | 3 => 1
  | _ => 1 / 2

/-- Counter-clockwise triangle connectivity of the v3.22 fixture. -/
def v323TriangleVertex (K : Fin 4) (s : Fin 3) : Fin 5 :=
  match K.val, s.val with
  | 0, 0 => 0
  | 0, 1 => 1
  | 0, _ => 4
  | 1, 0 => 1
  | 1, 1 => 2
  | 1, _ => 4
  | 2, 0 => 2
  | 2, 1 => 3
  | 2, _ => 4
  | _, 0 => 3
  | _, 1 => 0
  | _, _ => 4

/-- Exact signed affine determinant of each fixture triangle. -/
def v323SignedJacobian (_K : Fin 4) : ℚ := 1 / 2

/-- Canonical low endpoint of each global edge. -/
def v323EdgeVertexLo (e : Fin 8) : Fin 5 :=
  match e.val with
  | 0 => 0
  | 1 => 1
  | 2 => 2
  | 3 => 0
  | 4 => 1
  | 5 => 2
  | 6 => 3
  | _ => 0

/-- Canonical high endpoint of each global edge. -/
def v323EdgeVertexHi (e : Fin 8) : Fin 5 :=
  match e.val with
  | 0 => 1
  | 1 => 2
  | 2 => 3
  | 3 => 3
  | 4 => 4
  | 5 => 4
  | 6 => 4
  | _ => 4

/-- Deterministic local-to-global edge map for the square-with-center fixture. -/
def v323LocalEdge (K : Fin 4) (s : Fin 3) : Fin 8 :=
  match K.val, s.val with
  | 0, 0 => 0
  | 0, 1 => 4
  | 0, _ => 7
  | 1, 0 => 1
  | 1, 1 => 5
  | 1, _ => 4
  | 2, 0 => 2
  | 2, 1 => 6
  | 2, _ => 5
  | _, 0 => 3
  | _, 1 => 7
  | _, _ => 6

/-- Local orientation relative to the canonical low-to-high global edge orientation. -/
def v323LocalSign (K : Fin 4) (s : Fin 3) : OrientationSign :=
  match K.val, s.val with
  | 3, 0 => .neg
  | _, 2 => .neg
  | _, _ => .pos

def v323InteriorEdge (i : Fin 4) : Fin 8 :=
  match i.val with
  | 0 => 4
  | 1 => 5
  | 2 => 6
  | _ => 7

def v323InteriorLeftCell (i : Fin 4) : Fin 4 :=
  match i.val with
  | 0 => 0
  | 1 => 1
  | 2 => 2
  | _ => 3

def v323InteriorLeftSlot (_i : Fin 4) : Fin 3 := 1

def v323InteriorRightCell (i : Fin 4) : Fin 4 :=
  match i.val with
  | 0 => 1
  | 1 => 2
  | 2 => 3
  | _ => 0

def v323InteriorRightSlot (_i : Fin 4) : Fin 3 := 2

def v323BoundaryEdge (b : Fin 4) : Fin 8 :=
  match b.val with
  | 0 => 0
  | 1 => 1
  | 2 => 2
  | _ => 3

def v323BoundaryCell (b : Fin 4) : Fin 4 :=
  match b.val with
  | 0 => 0
  | 1 => 1
  | 2 => 2
  | _ => 3

def v323BoundarySlot (_b : Fin 4) : Fin 3 := 0

def v323BoundaryLabel (b : Fin 4) : String :=
  match b.val with
  | 0 => "bottom"
  | 1 => "right"
  | 2 => "top"
  | _ => "left"

def v323EdgeOwner (e : Fin 8) : Sum (Fin 4) (Fin 4) :=
  match e.val with
  | 0 => Sum.inr 0
  | 1 => Sum.inr 1
  | 2 => Sum.inr 2
  | 3 => Sum.inr 3
  | 4 => Sum.inl 0
  | 5 => Sum.inl 1
  | 6 => Sum.inl 2
  | _ => Sum.inl 3

/--
The v3.22 square-with-center fixture re-expressed as the first geometry-linked
instance of the general v3.23 `MeshCertificate` API.
-/
def v323SquareCenterMesh : MeshCertificate where
  vertexCount := 5
  triangleCount := 4
  edgeCount := 8
  interiorEdgeCount := 4
  boundaryEdgeCount := 4
  vertexX := v323VertexX
  vertexY := v323VertexY
  triangleVertex := v323TriangleVertex
  triangle_v01_ne := by
    intro K
    fin_cases K <;> simp [v323TriangleVertex]
  triangle_v12_ne := by
    intro K
    fin_cases K <;> simp [v323TriangleVertex]
  triangle_v20_ne := by
    intro K
    fin_cases K <;> simp [v323TriangleVertex]
  signedJacobian := v323SignedJacobian
  signedJacobian_formula := by
    intro K
    fin_cases K <;>
      norm_num [v323SignedJacobian, v323VertexX, v323VertexY, v323TriangleVertex]
  signedJacobian_pos := by
    intro K
    norm_num [v323SignedJacobian]
  edgeVertexLo := v323EdgeVertexLo
  edgeVertexHi := v323EdgeVertexHi
  edge_vertices_canonical := by
    intro e
    fin_cases e <;> norm_num [v323EdgeVertexLo, v323EdgeVertexHi]
  localEdge := v323LocalEdge
  localSign := v323LocalSign
  local_edge_geometry := by
    intro K s
    fin_cases K <;> fin_cases s <;> rfl
  interiorEdge := v323InteriorEdge
  interiorLeftCell := v323InteriorLeftCell
  interiorLeftSlot := v323InteriorLeftSlot
  interiorRightCell := v323InteriorRightCell
  interiorRightSlot := v323InteriorRightSlot
  interior_cells_distinct := by
    intro i
    fin_cases i <;> simp [v323InteriorLeftCell, v323InteriorRightCell]
  interior_left_edge := by
    intro i
    fin_cases i <;> rfl
  interior_right_edge := by
    intro i
    fin_cases i <;> rfl
  interior_signs_opposite := by
    intro i
    fin_cases i <;> rfl
  boundaryEdge := v323BoundaryEdge
  boundaryCell := v323BoundaryCell
  boundarySlot := v323BoundarySlot
  boundaryLabel := v323BoundaryLabel
  boundary_label_nonempty := by
    intro b
    fin_cases b <;> simp [v323BoundaryLabel]
  boundary_edge_matches := by
    intro b
    fin_cases b <;> rfl
  edgeOwner := v323EdgeOwner
  interior_owned := by
    intro i
    fin_cases i <;> rfl
  boundary_owned := by
    intro b
    fin_cases b <;> rfl
  local_edge_complete := by
    intro K s
    fin_cases K <;> fin_cases s <;>
      simp [v323LocalEdge, v323EdgeOwner, v323InteriorLeftCell,
        v323InteriorLeftSlot, v323InteriorRightCell, v323InteriorRightSlot,
        v323BoundaryCell, v323BoundarySlot]

example : v323SquareCenterMesh.vertexCount = 5 := rfl
example : v323SquareCenterMesh.triangleCount = 4 := rfl
example : v323SquareCenterMesh.edgeCount = 8 := rfl

end CACEFormal.Generated

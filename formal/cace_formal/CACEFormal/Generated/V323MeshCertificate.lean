import Mathlib
import CACEFormal.MeshCertificate

namespace CACEFormal.Generated

open CACEFormal

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

/-- Local orientation relative to the canonical global edge orientation. -/
def v323LocalSign (_K : Fin 4) (s : Fin 3) : OrientationSign :=
  match s.val with
  | 2 => .neg
  | _ => .pos

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

def v323InteriorRightCell (i : Fin 4) : Fin 4 :=
  match i.val with
  | 0 => 1
  | 1 => 2
  | 2 => 3
  | _ => 0

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
The v3.22 square-with-center fixture re-expressed as the first instance of the
general v3.23 `MeshCertificate` API.
-/
def v323SquareCenterMesh : MeshCertificate where
  triangleCount := 4
  edgeCount := 8
  interiorEdgeCount := 4
  boundaryEdgeCount := 4
  signedJacobian := fun _ => 1 / 2
  signedJacobian_pos := by
    intro K
    norm_num
  localEdge := v323LocalEdge
  localSign := v323LocalSign
  interiorEdge := v323InteriorEdge
  interiorLeftCell := v323InteriorLeftCell
  interiorLeftSlot := fun _ => 1
  interiorRightCell := v323InteriorRightCell
  interiorRightSlot := fun _ => 2
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
  boundarySlot := fun _ => 0
  boundaryLabel := v323BoundaryLabel
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

example : v323SquareCenterMesh.triangleCount = 4 := rfl
example : v323SquareCenterMesh.edgeCount = 8 := rfl

end CACEFormal.Generated

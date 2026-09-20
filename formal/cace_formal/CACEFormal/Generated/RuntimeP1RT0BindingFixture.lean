import Mathlib
import CACEFormal.MeshCertificate
import CACEFormal.P1RT0Element

namespace CACEFormal.Generated

open CACEFormal

def runtimeP1RT0FixtureMeshVertexX (i : Fin 5) : ℚ :=
  match i.val with
  | 0 => (0 : ℚ)
  | 1 => (1 : ℚ)
  | 2 => (1 : ℚ)
  | 3 => (0 : ℚ)
  | _ => (1 : ℚ) / 2

def runtimeP1RT0FixtureMeshVertexY (i : Fin 5) : ℚ :=
  match i.val with
  | 0 => (0 : ℚ)
  | 1 => (0 : ℚ)
  | 2 => (1 : ℚ)
  | 3 => (1 : ℚ)
  | _ => (1 : ℚ) / 2

def runtimeP1RT0FixtureMeshTriangleVertex (K : Fin 4) (s : Fin 3) : Fin 5 :=
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
  | 3, 0 => 3
  | 3, 1 => 0
  | _, _ => 4

def runtimeP1RT0FixtureMeshSignedJacobian (i : Fin 4) : ℚ :=
  match i.val with
  | 0 => (1 : ℚ) / 2
  | 1 => (1 : ℚ) / 2
  | 2 => (1 : ℚ) / 2
  | _ => (1 : ℚ) / 2

def runtimeP1RT0FixtureMeshEdgeVertexLo (i : Fin 8) : Fin 5 :=
  match i.val with
  | 0 => 0
  | 1 => 0
  | 2 => 0
  | 3 => 1
  | 4 => 1
  | 5 => 2
  | 6 => 2
  | _ => 3

def runtimeP1RT0FixtureMeshEdgeVertexHi (i : Fin 8) : Fin 5 :=
  match i.val with
  | 0 => 1
  | 1 => 3
  | 2 => 4
  | 3 => 2
  | 4 => 4
  | 5 => 3
  | 6 => 4
  | _ => 4

def runtimeP1RT0FixtureMeshLocalEdge (K : Fin 4) (s : Fin 3) : Fin 8 :=
  match K.val, s.val with
  | 0, 0 => 0
  | 0, 1 => 4
  | 0, _ => 2
  | 1, 0 => 3
  | 1, 1 => 6
  | 1, _ => 4
  | 2, 0 => 5
  | 2, 1 => 7
  | 2, _ => 6
  | 3, 0 => 1
  | 3, 1 => 2
  | _, _ => 7

def runtimeP1RT0FixtureMeshLocalSign (K : Fin 4) (s : Fin 3) : OrientationSign :=
  match K.val, s.val with
  | 0, 0 => .pos
  | 0, 1 => .pos
  | 0, _ => .neg
  | 1, 0 => .pos
  | 1, 1 => .pos
  | 1, _ => .neg
  | 2, 0 => .pos
  | 2, 1 => .pos
  | 2, _ => .neg
  | 3, 0 => .neg
  | 3, 1 => .pos
  | _, _ => .neg

def runtimeP1RT0FixtureMeshInteriorEdge (i : Fin 4) : Fin 8 :=
  match i.val with
  | 0 => 2
  | 1 => 4
  | 2 => 6
  | _ => 7

def runtimeP1RT0FixtureMeshInteriorLeftCell (i : Fin 4) : Fin 4 :=
  match i.val with
  | 0 => 0
  | 1 => 0
  | 2 => 1
  | _ => 2

def runtimeP1RT0FixtureMeshInteriorLeftSlot (i : Fin 4) : Fin 3 :=
  match i.val with
  | 0 => 2
  | 1 => 1
  | 2 => 1
  | _ => 1

def runtimeP1RT0FixtureMeshInteriorRightCell (i : Fin 4) : Fin 4 :=
  match i.val with
  | 0 => 3
  | 1 => 1
  | 2 => 2
  | _ => 3

def runtimeP1RT0FixtureMeshInteriorRightSlot (i : Fin 4) : Fin 3 :=
  match i.val with
  | 0 => 1
  | 1 => 2
  | 2 => 2
  | _ => 2

def runtimeP1RT0FixtureMeshBoundaryEdge (i : Fin 4) : Fin 8 :=
  match i.val with
  | 0 => 0
  | 1 => 1
  | 2 => 3
  | _ => 5

def runtimeP1RT0FixtureMeshBoundaryCell (i : Fin 4) : Fin 4 :=
  match i.val with
  | 0 => 0
  | 1 => 3
  | 2 => 1
  | _ => 2

def runtimeP1RT0FixtureMeshBoundarySlot (i : Fin 4) : Fin 3 :=
  match i.val with
  | 0 => 0
  | 1 => 0
  | 2 => 0
  | _ => 0

def runtimeP1RT0FixtureMeshBoundaryLabel (i : Fin 4) : String :=
  match i.val with
  | 0 => "bottom"
  | 1 => "left"
  | 2 => "right"
  | _ => "top"

def runtimeP1RT0FixtureMeshEdgeOwner (i : Fin 8) : Sum (Fin 4) (Fin 4) :=
  match i.val with
  | 0 => Sum.inr 0
  | 1 => Sum.inr 1
  | 2 => Sum.inl 0
  | 3 => Sum.inr 2
  | 4 => Sum.inl 1
  | 5 => Sum.inr 3
  | 6 => Sum.inl 2
  | _ => Sum.inl 3

def runtimeP1RT0FixtureMesh : MeshCertificate where
  vertexCount := 5
  triangleCount := 4
  edgeCount := 8
  interiorEdgeCount := 4
  boundaryEdgeCount := 4
  vertexX := runtimeP1RT0FixtureMeshVertexX
  vertexY := runtimeP1RT0FixtureMeshVertexY
  triangleVertex := runtimeP1RT0FixtureMeshTriangleVertex
  triangle_v01_ne := by
    intro K; fin_cases K <;> simp [runtimeP1RT0FixtureMeshTriangleVertex]
  triangle_v12_ne := by
    intro K; fin_cases K <;> simp [runtimeP1RT0FixtureMeshTriangleVertex]
  triangle_v20_ne := by
    intro K; fin_cases K <;> simp [runtimeP1RT0FixtureMeshTriangleVertex]
  signedJacobian := runtimeP1RT0FixtureMeshSignedJacobian
  signedJacobian_formula := by
    intro K
    fin_cases K <;> norm_num [runtimeP1RT0FixtureMeshSignedJacobian, runtimeP1RT0FixtureMeshVertexX, runtimeP1RT0FixtureMeshVertexY, runtimeP1RT0FixtureMeshTriangleVertex]
  signedJacobian_pos := by
    intro K
    fin_cases K <;> norm_num [runtimeP1RT0FixtureMeshSignedJacobian]
  edgeVertexLo := runtimeP1RT0FixtureMeshEdgeVertexLo
  edgeVertexHi := runtimeP1RT0FixtureMeshEdgeVertexHi
  edge_vertices_canonical := by
    intro e; fin_cases e <;> norm_num [runtimeP1RT0FixtureMeshEdgeVertexLo, runtimeP1RT0FixtureMeshEdgeVertexHi]
  localEdge := runtimeP1RT0FixtureMeshLocalEdge
  localSign := runtimeP1RT0FixtureMeshLocalSign
  local_edge_geometry := by
    intro K s; fin_cases K <;> fin_cases s <;> rfl
  interiorEdge := runtimeP1RT0FixtureMeshInteriorEdge
  interiorLeftCell := runtimeP1RT0FixtureMeshInteriorLeftCell
  interiorLeftSlot := runtimeP1RT0FixtureMeshInteriorLeftSlot
  interiorRightCell := runtimeP1RT0FixtureMeshInteriorRightCell
  interiorRightSlot := runtimeP1RT0FixtureMeshInteriorRightSlot
  interior_cells_distinct := by
    intro i; fin_cases i <;> simp [runtimeP1RT0FixtureMeshInteriorLeftCell, runtimeP1RT0FixtureMeshInteriorRightCell]
  interior_left_edge := by
    intro i; fin_cases i <;> rfl
  interior_right_edge := by
    intro i; fin_cases i <;> rfl
  interior_signs_opposite := by
    intro i; fin_cases i <;> rfl
  boundaryEdge := runtimeP1RT0FixtureMeshBoundaryEdge
  boundaryCell := runtimeP1RT0FixtureMeshBoundaryCell
  boundarySlot := runtimeP1RT0FixtureMeshBoundarySlot
  boundaryLabel := runtimeP1RT0FixtureMeshBoundaryLabel
  boundary_label_nonempty := by
    intro b; fin_cases b <;> simp [runtimeP1RT0FixtureMeshBoundaryLabel]
  boundary_edge_matches := by
    intro b; fin_cases b <;> rfl
  edgeOwner := runtimeP1RT0FixtureMeshEdgeOwner
  interior_owned := by
    intro i; fin_cases i <;> rfl
  boundary_owned := by
    intro b; fin_cases b <;> rfl
  local_edge_complete := by
    intro K s; fin_cases K <;> fin_cases s <;> simp [runtimeP1RT0FixtureMeshLocalEdge, runtimeP1RT0FixtureMeshEdgeOwner, runtimeP1RT0FixtureMeshInteriorLeftCell, runtimeP1RT0FixtureMeshInteriorLeftSlot, runtimeP1RT0FixtureMeshInteriorRightCell, runtimeP1RT0FixtureMeshInteriorRightSlot, runtimeP1RT0FixtureMeshBoundaryCell, runtimeP1RT0FixtureMeshBoundarySlot]

end CACEFormal.Generated

namespace CACEFormal.Generated

open CACEFormal

def runtimeP1RT0FixturePacketSha256 : String := "7b423632367b6062ece2d312a58cbb114a3a0a77788513e4abae2e798a3a4d81"
def runtimeP1RT0FixtureMeshCertificateSha256 : String := "a1c10bb479415e147013ae5d43c939ddeea4e516484b1217947c2871ca2d9c46"

def runtimeP1RT0FixtureP1 (K : Fin runtimeP1RT0FixtureMesh.triangleCount) : P1Affine :=
  match K.val with
  | 0 => ⟨(0 : ℝ), (1 : ℝ), (0 : ℝ)⟩
  | 1 => ⟨(1 : ℝ), (0 : ℝ), (1 : ℝ)⟩
  | 2 => ⟨(2 : ℝ), (-1 : ℝ), (0 : ℝ)⟩
  | _ => ⟨(1 : ℝ), (0 : ℝ), (-1 : ℝ)⟩

def runtimeP1RT0FixtureRT0 (K : Fin runtimeP1RT0FixtureMesh.triangleCount) : RT0Affine :=
  match K.val with
  | 0 => ⟨(0 : ℝ), (0 : ℝ), ((1 : ℝ) / 2)⟩
  | 1 => ⟨(1 : ℝ), (0 : ℝ), ((1 : ℝ) / 3)⟩
  | 2 => ⟨(0 : ℝ), (1 : ℝ), ((-1 : ℝ) / 4)⟩
  | _ => ⟨(-1 : ℝ), (0 : ℝ), (2 : ℝ)⟩

theorem runtimeP1RT0FixtureTriangleCount : runtimeP1RT0FixtureMesh.triangleCount = 4 := rfl

end CACEFormal.Generated

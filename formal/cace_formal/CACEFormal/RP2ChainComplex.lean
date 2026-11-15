import Mathlib

namespace CACEFormal.RP2

/-!
# Six-vertex triangulation of the real projective plane

This module records the ten-triangle, six-vertex triangulation as finite
coordinate data. Edges are lexicographically indexed by Fin 15 and facets
by Fin 10. The chain groups are free abelian groups on those finite bases.

This file is intentionally quarantined: it is not imported by
`CACEFormal.lean`. The chain identity below is not, by itself, a proof of
the integral homology groups or of a classification theorem.
-/

abbrev Vertex := Fin 6
abbrev Edge := Fin 15
abbrev Facet := Fin 10

abbrev C0 := Vertex → ℤ
abbrev C1 := Edge → ℤ
abbrev C2 := Facet → ℤ

/-- Lexicographic edge order: 01,02,03,04,05,12,13,14,15,23,24,25,34,35,45. -/
def edgeVertices (e : Edge) : Vertex × Vertex :=
  match e.val with
  | 0  => (0, 1)
  | 1  => (0, 2)
  | 2  => (0, 3)
  | 3  => (0, 4)
  | 4  => (0, 5)
  | 5  => (1, 2)
  | 6  => (1, 3)
  | 7  => (1, 4)
  | 8  => (1, 5)
  | 9  => (2, 3)
  | 10 => (2, 4)
  | 11 => (2, 5)
  | 12 => (3, 4)
  | 13 => (3, 5)
  | _  => (4, 5)

/-- The ten oriented facets of the minimal six-vertex RP² triangulation. -/
def faceVertices (f : Facet) : Vertex × Vertex × Vertex :=
  match f.val with
  | 0 => (0, 1, 2)
  | 1 => (0, 1, 3)
  | 2 => (0, 2, 4)
  | 3 => (0, 3, 5)
  | 4 => (0, 4, 5)
  | 5 => (1, 2, 5)
  | 6 => (1, 3, 4)
  | 7 => (1, 4, 5)
  | 8 => (2, 3, 4)
  | _ => (2, 3, 5)

/-- Index of an increasing edge in the declared 15-edge basis. -/
def edgeIndex (a b : Vertex) : Edge :=
  match a.val, b.val with
  | 0, 1 => 0
  | 0, 2 => 1
  | 0, 3 => 2
  | 0, 4 => 3
  | 0, 5 => 4
  | 1, 2 => 5
  | 1, 3 => 6
  | 1, 4 => 7
  | 1, 5 => 8
  | 2, 3 => 9
  | 2, 4 => 10
  | 2, 5 => 11
  | 3, 4 => 12
  | 3, 5 => 13
  | 4, 5 => 14
  | _, _ => 0

/-- Boundary of an oriented edge [a,b], with convention b-a. -/
def edgeBoundary (a b : Vertex) : C0 :=
  fun v => (if v = b then 1 else 0) - (if v = a then 1 else 0)

/-- Boundary of an oriented face [a,b,c] is [b,c]-[a,c]+[a,b]. -/
def faceBoundary (a b c : Vertex) : C1 :=
  fun e =>
    (if e = edgeIndex b c then 1 else 0)
      - (if e = edgeIndex a c then 1 else 0)
      + (if e = edgeIndex a b then 1 else 0)

/-- Every oriented facet edge resolves to the intended member of the
15-edge basis; the fallback branch of edgeIndex is never used by a facet. -/
theorem face_edges_are_basis_edges (f : Facet) :
    edgeVertices (edgeIndex (faceVertices f).2.1 (faceVertices f).2.2) =
        ((faceVertices f).2.1, (faceVertices f).2.2) ∧
    edgeVertices (edgeIndex (faceVertices f).1 (faceVertices f).2.2) =
        ((faceVertices f).1, (faceVertices f).2.2) ∧
    edgeVertices (edgeIndex (faceVertices f).1 (faceVertices f).2.1) =
        ((faceVertices f).1, (faceVertices f).2.1) := by
  fin_cases f <;> norm_num [faceVertices, edgeIndex, edgeVertices]

/-- The edge basis has no duplicate oriented endpoint pairs. -/
theorem edgeVertices_injective : Function.Injective edgeVertices := by
  intro e₁ e₂ h
  fin_cases e₁ <;> fin_cases e₂ <;> simp_all [edgeVertices]

/-- Integral boundary map ∂₁ : C₁ → C₀. -/
def boundary1 (z : C1) : C0 :=
  fun v => ∑ e : Edge, z e * edgeBoundary (edgeVertices e).1 (edgeVertices e).2 v

/-- Integral boundary map ∂₂ : C₂ → C₁. -/
def boundary2 (z : C2) : C1 :=
  fun e => ∑ f : Facet,
    z f * faceBoundary (faceVertices f).1 (faceVertices f).2.1 (faceVertices f).2.2 e

/-- The declared chain groups have exactly 6, 15, and 10 basis elements. -/
theorem basis_cardinalities :
    Fintype.card Vertex = 6 ∧ Fintype.card Edge = 15 ∧ Fintype.card Facet = 10 := by
  simp [Vertex, Edge, Facet]

set_option maxHeartbeats 5000000

/-- The simplicial boundary operators compose to zero over the integers.
The finite expansion is deliberately given a larger local heartbeat budget. -/
theorem boundary_squared_zero (z : C2) : boundary1 (boundary2 z) = 0 := by
  funext v
  fin_cases v <;>
    simp [boundary1, boundary2, edgeBoundary, faceBoundary,
      edgeVertices, faceVertices, edgeIndex, Fin.sum_univ_succ] <;>
    ring

/-- Every vertex is connected to vertex 0 by an edge in the declared basis. -/
theorem one_skeleton_connected (v : Vertex) :
    v = 0 ∨ ∃ e : Edge, edgeVertices e = (0, v) := by
  fin_cases v
  · exact Or.inl rfl
  · exact Or.inr ⟨⟨0, by decide⟩, rfl⟩
  · exact Or.inr ⟨⟨1, by decide⟩, rfl⟩
  · exact Or.inr ⟨⟨2, by decide⟩, rfl⟩
  · exact Or.inr ⟨⟨3, by decide⟩, rfl⟩
  · exact Or.inr ⟨⟨4, by decide⟩, rfl⟩

end CACEFormal.RP2

import Mathlib
import CACEFormal.MeshCertificate

namespace CACEFormal

open scoped BigOperators

/-!
v3.24 topology-driven face assembly.

`MeshCertificate.local_edge_complete` plus the ownership/injectivity fields imply
that local triangle-edge occurrences are in bijection with exactly two
occurrences for every interior edge and exactly one occurrence for every
boundary edge.  This file turns that fact into a finite-sum assembly theorem.
-/

/-- A triangle/local-edge-slot occurrence. -/
abbrev LocalOccurrence (mesh : MeshCertificate) :=
  Fin mesh.triangleCount × Fin 3

/--
The ownership-side representation of local occurrences: two sides for each
interior edge and one occurrence for each boundary edge.
-/
abbrev OwnedOccurrence (mesh : MeshCertificate) :=
  Sum (Fin mesh.interiorEdgeCount × Fin 2) (Fin mesh.boundaryEdgeCount)

/-- Map ownership-side data to its unique local triangle-edge occurrence. -/
def localOfOwned (mesh : MeshCertificate) :
    OwnedOccurrence mesh → LocalOccurrence mesh
  | Sum.inl (i, side) =>
      match side.val with
      | 0 => (mesh.interiorLeftCell i, mesh.interiorLeftSlot i)
      | _ => (mesh.interiorRightCell i, mesh.interiorRightSlot i)
  | Sum.inr b => (mesh.boundaryCell b, mesh.boundarySlot b)

theorem localOfOwned_interior_edge (mesh : MeshCertificate)
    (i : Fin mesh.interiorEdgeCount) (side : Fin 2) :
    mesh.localEdge (localOfOwned mesh (Sum.inl (i, side))).1
      (localOfOwned mesh (Sum.inl (i, side))).2 = mesh.interiorEdge i := by
  fin_cases side
  · simpa [localOfOwned] using mesh.interior_left_edge i
  · simpa [localOfOwned] using mesh.interior_right_edge i

theorem localOfOwned_boundary_edge (mesh : MeshCertificate)
    (b : Fin mesh.boundaryEdgeCount) :
    mesh.localEdge (localOfOwned mesh (Sum.inr b)).1
      (localOfOwned mesh (Sum.inr b)).2 = mesh.boundaryEdge b := by
  simpa [localOfOwned] using mesh.boundary_edge_matches b

/-- Distinct owner/side records cannot describe the same local occurrence. -/
theorem localOfOwned_injective (mesh : MeshCertificate) :
    Function.Injective (localOfOwned mesh) := by
  intro a b h
  cases a with
  | inl ai =>
      rcases ai with ⟨i, si⟩
      cases b with
      | inl bj =>
          rcases bj with ⟨j, sj⟩
          have hedge : mesh.interiorEdge i = mesh.interiorEdge j := by
            calc
              mesh.interiorEdge i =
                  mesh.localEdge (localOfOwned mesh (Sum.inl (i, si))).1
                    (localOfOwned mesh (Sum.inl (i, si))).2 :=
                (localOfOwned_interior_edge mesh i si).symm
              _ = mesh.localEdge (localOfOwned mesh (Sum.inl (j, sj))).1
                    (localOfOwned mesh (Sum.inl (j, sj))).2 := by
                exact congrArg (fun p : LocalOccurrence mesh => mesh.localEdge p.1 p.2) h
              _ = mesh.interiorEdge j := localOfOwned_interior_edge mesh j sj
          have hij : i = j := mesh.interiorEdge_injective hedge
          subst j
          fin_cases si
          · fin_cases sj
            · rfl
            · exfalso
              apply mesh.interior_cells_distinct i
              have hc := congrArg Prod.fst h
              simpa [localOfOwned] using hc
          · fin_cases sj
            · exfalso
              apply mesh.interior_cells_distinct i
              have hc := congrArg Prod.fst h
              exact (by simpa [localOfOwned] using hc.symm)
            · rfl
      | inr bj =>
          exfalso
          apply mesh.interior_boundary_disjoint i bj
          calc
            mesh.interiorEdge i =
                mesh.localEdge (localOfOwned mesh (Sum.inl (i, si))).1
                  (localOfOwned mesh (Sum.inl (i, si))).2 :=
              (localOfOwned_interior_edge mesh i si).symm
            _ = mesh.localEdge (localOfOwned mesh (Sum.inr bj)).1
                  (localOfOwned mesh (Sum.inr bj)).2 := by
              exact congrArg (fun p : LocalOccurrence mesh => mesh.localEdge p.1 p.2) h
            _ = mesh.boundaryEdge bj := localOfOwned_boundary_edge mesh bj
  | inr ai =>
      cases b with
      | inl bj =>
          rcases bj with ⟨j, sj⟩
          exfalso
          apply mesh.interior_boundary_disjoint j ai
          calc
            mesh.interiorEdge j =
                mesh.localEdge (localOfOwned mesh (Sum.inl (j, sj))).1
                  (localOfOwned mesh (Sum.inl (j, sj))).2 :=
              (localOfOwned_interior_edge mesh j sj).symm
            _ = mesh.localEdge (localOfOwned mesh (Sum.inr ai)).1
                  (localOfOwned mesh (Sum.inr ai)).2 := by
              exact congrArg (fun p : LocalOccurrence mesh => mesh.localEdge p.1 p.2) h.symm
            _ = mesh.boundaryEdge ai := localOfOwned_boundary_edge mesh ai
      | inr bj =>
          have hedge : mesh.boundaryEdge ai = mesh.boundaryEdge bj := by
            calc
              mesh.boundaryEdge ai =
                  mesh.localEdge (localOfOwned mesh (Sum.inr ai)).1
                    (localOfOwned mesh (Sum.inr ai)).2 :=
                (localOfOwned_boundary_edge mesh ai).symm
              _ = mesh.localEdge (localOfOwned mesh (Sum.inr bj)).1
                    (localOfOwned mesh (Sum.inr bj)).2 := by
                exact congrArg (fun p : LocalOccurrence mesh => mesh.localEdge p.1 p.2) h
              _ = mesh.boundaryEdge bj := localOfOwned_boundary_edge mesh bj
          have hab : ai = bj := mesh.boundaryEdge_injective hedge
          subst bj
          rfl

/-- Completeness of the mesh owner map gives every local occurrence an owner/side preimage. -/
theorem localOfOwned_surjective (mesh : MeshCertificate) :
    Function.Surjective (localOfOwned mesh) := by
  rintro ⟨K, s⟩
  cases howner : mesh.edgeOwner (mesh.localEdge K s) with
  | inl i =>
      have hcomplete := mesh.local_edge_complete K s
      rw [howner] at hcomplete
      rcases hcomplete with hleft | hright
      · refine ⟨Sum.inl (i, (0 : Fin 2)), ?_⟩
        rcases hleft with ⟨hK, hs⟩
        subst K
        subst s
        simp [localOfOwned]
      · refine ⟨Sum.inl (i, (1 : Fin 2)), ?_⟩
        rcases hright with ⟨hK, hs⟩
        subst K
        subst s
        simp [localOfOwned]
  | inr b =>
      have hcomplete := mesh.local_edge_complete K s
      rw [howner] at hcomplete
      refine ⟨Sum.inr b, ?_⟩
      rcases hcomplete with ⟨hK, hs⟩
      subst K
      subst s
      rfl

/-- Canonical finite equivalence induced by the certified ownership partition. -/
noncomputable def localOwnedEquiv (mesh : MeshCertificate) :
    OwnedOccurrence mesh ≃ LocalOccurrence mesh :=
  Equiv.ofBijective (localOfOwned mesh)
    ⟨localOfOwned_injective mesh, localOfOwned_surjective mesh⟩

/--
The global sum of local face contributions is forced by mesh ownership: every
interior edge contributes its two certified sides and every boundary edge its
single owner.  No independent `faceAssembly` equality is assumed.
-/
theorem local_face_sum_decomposition (mesh : MeshCertificate)
    (localFace : Fin mesh.triangleCount → Fin 3 → ℝ) :
    (∑ K : Fin mesh.triangleCount, ∑ s : Fin 3, localFace K s) =
      (∑ i : Fin mesh.interiorEdgeCount,
        (localFace (mesh.interiorLeftCell i) (mesh.interiorLeftSlot i) +
          localFace (mesh.interiorRightCell i) (mesh.interiorRightSlot i))) +
      (∑ b : Fin mesh.boundaryEdgeCount,
        localFace (mesh.boundaryCell b) (mesh.boundarySlot b)) := by
  let f : LocalOccurrence mesh → ℝ := fun p => localFace p.1 p.2
  have h := Equiv.sum_comp (localOwnedEquiv mesh) f
  have hinterior :
      (∑ p : Fin mesh.interiorEdgeCount × Fin 2,
        f (localOfOwned mesh (Sum.inl p))) =
        ∑ i : Fin mesh.interiorEdgeCount,
          (localFace (mesh.interiorLeftCell i) (mesh.interiorLeftSlot i) +
            localFace (mesh.interiorRightCell i) (mesh.interiorRightSlot i)) := by
    rw [Fintype.sum_prod_type]
    apply Finset.sum_congr rfl
    intro i _hi
    rw [Fin.sum_univ_two]
    rfl
  have hboundary :
      (∑ b : Fin mesh.boundaryEdgeCount,
        f (localOfOwned mesh (Sum.inr b))) =
        ∑ b : Fin mesh.boundaryEdgeCount,
          localFace (mesh.boundaryCell b) (mesh.boundarySlot b) := by
    rfl
  calc
    (∑ K : Fin mesh.triangleCount, ∑ s : Fin 3, localFace K s) =
        ∑ p : LocalOccurrence mesh, f p := by
      rw [Fintype.sum_prod_type]
    _ = ∑ o : OwnedOccurrence mesh, f (localOwnedEquiv mesh o) := h.symm
    _ = (∑ p : Fin mesh.interiorEdgeCount × Fin 2,
          f (localOfOwned mesh (Sum.inl p))) +
        (∑ b : Fin mesh.boundaryEdgeCount,
          f (localOfOwned mesh (Sum.inr b))) := by
      rw [Fintype.sum_sum_type]
      rfl
    _ = _ := by
      rw [hinterior, hboundary]

end CACEFormal
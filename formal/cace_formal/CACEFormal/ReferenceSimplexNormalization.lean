import Mathlib
import CACEFormal.AffineP1RT0Transport

namespace CACEFormal

/-!
# Exact reference-simplex normalization

Every nondegenerate ordered triangle admits an explicit affine map to the
reference triangle (0,0), (1,0), (0,1).

The construction is algebraic and uses the inverse of the two edge-column
matrix. It gives CACE a canonical low-cost geometry reduction that can be
combined with the exact P1/RT0 affine transport theorems.
-/

namespace ReferenceSimplexNormalization

/-- Canonical positively oriented reference triangle. -/
def referenceTriangle : Triangle2 :=
  ⟨⟨0, 0⟩, ⟨1, 0⟩, ⟨0, 1⟩⟩

@[simp] theorem referenceTriangle_det :
    referenceTriangle.det = 1 := by
  norm_num [referenceTriangle, Triangle2.det]

/-- First edge vector of an ordered triangle. -/
def edge01 (T : Triangle2) : Point2 :=
  ⟨T.p1.x - T.p0.x, T.p1.y - T.p0.y⟩

/-- Second edge vector of an ordered triangle. -/
def edge02 (T : Triangle2) : Point2 :=
  ⟨T.p2.x - T.p0.x, T.p2.y - T.p0.y⟩

/-- Exact oriented determinant of two edge-column vectors. -/
def edgeDet (e1 e2 : Point2) : ℝ :=
  e1.x * e2.y - e1.y * e2.x

@[simp] theorem edgeDet_edges (T : Triangle2) :
    edgeDet (edge01 T) (edge02 T) = T.det := by
  rfl

/-- Translation that moves the first vertex of a triangle to the origin. -/
def recenterMap (T : Triangle2) : Affine2 :=
  Affine2.translation ⟨-T.p0.x, -T.p0.y⟩

@[simp] theorem recenterMap_p0 (T : Triangle2) :
    (recenterMap T).mapPoint T.p0 = ⟨0, 0⟩ := by
  rcases T with ⟨⟨x0, y0⟩, p1, p2⟩
  ext <;>
    dsimp [recenterMap, Affine2.translation, Affine2.mapPoint] <;>
    ring

@[simp] theorem recenterMap_p1 (T : Triangle2) :
    (recenterMap T).mapPoint T.p1 = edge01 T := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, p2⟩
  ext <;>
    dsimp [recenterMap, edge01, Affine2.translation, Affine2.mapPoint] <;>
    ring

@[simp] theorem recenterMap_p2 (T : Triangle2) :
    (recenterMap T).mapPoint T.p2 = edge02 T := by
  rcases T with ⟨⟨x0, y0⟩, p1, ⟨x2, y2⟩⟩
  ext <;>
    dsimp [recenterMap, edge02, Affine2.translation, Affine2.mapPoint] <;>
    ring

/-- Exact inverse of the 2×2 matrix whose columns are `e1` and `e2`.
The definition is total over ℝ; the inverse laws below require a nonzero
edge determinant. -/
noncomputable def inverseEdgeLinear (e1 e2 : Point2) : Affine2 :=
  let Δ := edgeDet e1 e2
  ⟨e2.y / Δ, -e2.x / Δ, -e1.y / Δ, e1.x / Δ, 0, 0⟩

/-- The inverse-edge linear map sends the first matrix column to the first
reference basis vector. -/
theorem inverseEdgeLinear_map_e1
    (e1 e2 : Point2) (hΔ : edgeDet e1 e2 ≠ 0) :
    (inverseEdgeLinear e1 e2).mapPoint e1 = ⟨1, 0⟩ := by
  rcases e1 with ⟨x1, y1⟩
  rcases e2 with ⟨x2, y2⟩
  change x1 * y2 - y1 * x2 ≠ 0 at hΔ
  ext <;>
    dsimp [inverseEdgeLinear, edgeDet, Affine2.mapPoint] <;>
    field_simp [hΔ] <;>
    ring

/-- The inverse-edge linear map sends the second matrix column to the second
reference basis vector. -/
theorem inverseEdgeLinear_map_e2
    (e1 e2 : Point2) (hΔ : edgeDet e1 e2 ≠ 0) :
    (inverseEdgeLinear e1 e2).mapPoint e2 = ⟨0, 1⟩ := by
  rcases e1 with ⟨x1, y1⟩
  rcases e2 with ⟨x2, y2⟩
  change x1 * y2 - y1 * x2 ≠ 0 at hΔ
  ext <;>
    dsimp [inverseEdgeLinear, edgeDet, Affine2.mapPoint] <;>
    field_simp [hΔ] <;>
    ring

@[simp] theorem inverseEdgeLinear_map_zero (e1 e2 : Point2) :
    (inverseEdgeLinear e1 e2).mapPoint ⟨0, 0⟩ = ⟨0, 0⟩ := by
  ext <;>
    simp [inverseEdgeLinear, Affine2.mapPoint]

/-- The determinant of the inverse-edge matrix is the reciprocal edge
matrix determinant. -/
theorem inverseEdgeLinear_linearDet
    (e1 e2 : Point2) (hΔ : edgeDet e1 e2 ≠ 0) :
    (inverseEdgeLinear e1 e2).linearDet = 1 / edgeDet e1 e2 := by
  rcases e1 with ⟨x1, y1⟩
  rcases e2 with ⟨x2, y2⟩
  change x1 * y2 - y1 * x2 ≠ 0 at hΔ
  dsimp [inverseEdgeLinear, edgeDet, Affine2.linearDet]
  field_simp [hΔ] <;>
    ring

/-- Canonical normalizer: recenter at `p0`, then invert the exact two-edge
column matrix.  This decomposition keeps the determinant as one named object
instead of repeatedly expanding equivalent denominator polynomials. -/
noncomputable def normalizer (T : Triangle2) : Affine2 :=
  Affine2.comp
    (inverseEdgeLinear (edge01 T) (edge02 T))
    (recenterMap T)

/-- The linear determinant of the normalizer is exactly the reciprocal triangle
determinant. -/
theorem normalizer_linearDet
    (T : Triangle2) (hT : T.det ≠ 0) :
    (normalizer T).linearDet = 1 / T.det := by
  have hΔ : edgeDet (edge01 T) (edge02 T) ≠ 0 := by
    simpa using hT
  calc
    (normalizer T).linearDet =
        (inverseEdgeLinear (edge01 T) (edge02 T)).linearDet *
          (recenterMap T).linearDet := by
            simp [normalizer]
    _ = (1 / edgeDet (edge01 T) (edge02 T)) * 1 := by
          rw [inverseEdgeLinear_linearDet _ _ hΔ]
          simp [recenterMap]
    _ = 1 / T.det := by
          simp

/-- Nondegenerate triangles produce nonsingular normalizers. -/
theorem normalizer_linearDet_ne_zero
    (T : Triangle2) (hT : T.det ≠ 0) :
    (normalizer T).linearDet ≠ 0 := by
  rw [normalizer_linearDet T hT]
  exact one_div_ne_zero hT

/-- Positively oriented triangles produce orientation-preserving normalizers. -/
theorem normalizer_linearDet_pos
    (T : Triangle2) (hT : 0 < T.det) :
    0 < (normalizer T).linearDet := by
  have hne : T.det ≠ 0 := ne_of_gt hT
  rw [normalizer_linearDet T hne]
  exact one_div_pos.mpr hT

/-- The first vertex maps exactly to the origin. -/
theorem normalizer_map_p0
    (T : Triangle2) (_hT : T.det ≠ 0) :
    (normalizer T).mapPoint T.p0 = ⟨0, 0⟩ := by
  simp [normalizer]

/-- The second vertex maps exactly to (1,0). -/
theorem normalizer_map_p1
    (T : Triangle2) (hT : T.det ≠ 0) :
    (normalizer T).mapPoint T.p1 = ⟨1, 0⟩ := by
  have hΔ : edgeDet (edge01 T) (edge02 T) ≠ 0 := by
    simpa using hT
  simpa [normalizer] using
    inverseEdgeLinear_map_e1 (edge01 T) (edge02 T) hΔ

/-- The third vertex maps exactly to (0,1). -/
theorem normalizer_map_p2
    (T : Triangle2) (hT : T.det ≠ 0) :
    (normalizer T).mapPoint T.p2 = ⟨0, 1⟩ := by
  have hΔ : edgeDet (edge01 T) (edge02 T) ≠ 0 := by
    simpa using hT
  simpa [normalizer] using
    inverseEdgeLinear_map_e2 (edge01 T) (edge02 T) hΔ

/-- The whole triangle is mapped exactly to the canonical reference simplex. -/
theorem normalizer_map_triangle
    (T : Triangle2) (hT : T.det ≠ 0) :
    (normalizer T).mapTriangle T = referenceTriangle := by
  apply Triangle2.ext
  · exact normalizer_map_p0 T hT
  · exact normalizer_map_p1 T hT
  · exact normalizer_map_p2 T hT

/-- The normalizer itself is a certified nondegeneracy-preserving transform. -/
noncomputable def certifiedNondegenerate
    (T : Triangle2) (hT : T.det ≠ 0) :
    CertifiedTransform Triangle2 GeometryTransforms.Nondegenerate :=
  Affine2.certifiedNondegenerate (normalizer T)
    (normalizer_linearDet_ne_zero T hT)

/-- For positive input orientation the normalizer is a certified
orientation-preserving transform. -/
noncomputable def certifiedPositive
    (T : Triangle2) (hT : 0 < T.det) :
    CertifiedTransform Triangle2 GeometryTransforms.PositiveOrientation :=
  Affine2.certifiedPositive (normalizer T)
    (normalizer_linearDet_pos T hT)

/-- Exact P1/RT0 cell pairing on an arbitrary nondegenerate triangle is equal
to the transported pairing on the single canonical reference triangle. -/
theorem cellPairing_to_reference
    (T : Triangle2) (v : P1Affine) (q : RT0Affine) (hT : T.det ≠ 0) :
    P1RT0Element.cellPairing
        referenceTriangle
        (AffineP1RT0Transport.pullP1 (normalizer T) v)
        (AffineP1RT0Transport.piolaRT0 (normalizer T) q) =
      P1RT0Element.cellPairing T v q := by
  have hdet := normalizer_linearDet_ne_zero T hT
  have h :=
    AffineP1RT0Transport.cellPairing_map (normalizer T) T v q hdet
  rw [normalizer_map_triangle T hT] at h
  exact h

/-- The exact divergence term is likewise reducible to the reference simplex. -/
theorem cellDivergence_to_reference
    (T : Triangle2) (v : P1Affine) (q : RT0Affine) (hT : T.det ≠ 0) :
    P1RT0Element.cellDivergence
        referenceTriangle
        (AffineP1RT0Transport.pullP1 (normalizer T) v)
        (AffineP1RT0Transport.piolaRT0 (normalizer T) q) =
      P1RT0Element.cellDivergence T v q := by
  have hdet := normalizer_linearDet_ne_zero T hT
  have h :=
    AffineP1RT0Transport.cellDivergence_map (normalizer T) T v q hdet
  rw [normalizer_map_triangle T hT] at h
  exact h

/-- The exact boundary-face contribution is also reducible to the reference
simplex. -/
theorem cellFacePairing_to_reference
    (T : Triangle2) (v : P1Affine) (q : RT0Affine) (hT : T.det ≠ 0) :
    P1RT0Element.cellFacePairing
        referenceTriangle
        (AffineP1RT0Transport.pullP1 (normalizer T) v)
        (AffineP1RT0Transport.piolaRT0 (normalizer T) q) =
      P1RT0Element.cellFacePairing T v q := by
  have hdet := normalizer_linearDet_ne_zero T hT
  have h :=
    AffineP1RT0Transport.cellFacePairing_map (normalizer T) T v q hdet
  rw [normalizer_map_triangle T hT] at h
  exact h

end ReferenceSimplexNormalization

end CACEFormal

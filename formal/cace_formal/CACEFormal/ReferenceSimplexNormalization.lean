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

/-- Explicit affine inverse of the edge matrix of T, translated so p0
maps to the origin. It is meaningful as a geometric inverse when T.det ≠ 0;
the definition itself remains total over ℝ. -/
noncomputable def normalizer (T : Triangle2) : Affine2 :=
  let Δ := T.det
  let aa := (T.p2.y - T.p0.y) / Δ
  let ab := -(T.p2.x - T.p0.x) / Δ
  let ac := -(T.p1.y - T.p0.y) / Δ
  let ad := (T.p1.x - T.p0.x) / Δ
  ⟨aa, ab, ac, ad,
    -(aa * T.p0.x + ab * T.p0.y),
    -(ac * T.p0.x + ad * T.p0.y)⟩

/-- The linear determinant of the normalizer is exactly the reciprocal triangle
determinant. -/
theorem normalizer_linearDet
    (T : Triangle2) (hT : T.det ≠ 0) :
    (normalizer T).linearDet = 1 / T.det := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  change ((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)) ≠ 0 at hT
  dsimp [normalizer, Affine2.linearDet, Triangle2.det]
  field_simp [hT]

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
    (T : Triangle2) (hT : T.det ≠ 0) :
    (normalizer T).mapPoint T.p0 = ⟨0, 0⟩ := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  change ((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)) ≠ 0 at hT
  ext <;>
    dsimp [normalizer, Affine2.mapPoint, Triangle2.det] <;>
    field_simp [hT] <;>
    ring

/-- The second vertex maps exactly to (1,0). -/
theorem normalizer_map_p1
    (T : Triangle2) (hT : T.det ≠ 0) :
    (normalizer T).mapPoint T.p1 = ⟨1, 0⟩ := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  change ((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)) ≠ 0 at hT
  have hden :
      y2 * x1 - y2 * x0 - y0 * x1 + y0 * x2 - y1 * x2 + y1 * x0 ≠ 0 := by
    intro hzero
    apply hT
    calc
      (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0) =
          y2 * x1 - y2 * x0 - y0 * x1 + y0 * x2 - y1 * x2 + y1 * x0 := by
            ring
      _ = 0 := hzero
  have hden_nf :
      y2 * x1 - y2 * x0 - x1 * y0 + x0 * y1 + y0 * x2 - x2 * y1 ≠ 0 := by
    intro hzero
    apply hden
    calc
      y2 * x1 - y2 * x0 - y0 * x1 + y0 * x2 - y1 * x2 + y1 * x0 =
          y2 * x1 - y2 * x0 - x1 * y0 + x0 * y1 + y0 * x2 - x2 * y1 := by
            ring
      _ = 0 := hzero
  ext <;>
    dsimp [normalizer, Affine2.mapPoint, Triangle2.det] <;>
    ring_nf <;>
    field_simp [hT, hden, hden_nf]

/-- The third vertex maps exactly to (0,1). -/
theorem normalizer_map_p2
    (T : Triangle2) (hT : T.det ≠ 0) :
    (normalizer T).mapPoint T.p2 = ⟨0, 1⟩ := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  change ((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)) ≠ 0 at hT
  ext <;>
    dsimp [normalizer, Affine2.mapPoint, Triangle2.det] <;>
    field_simp [hT] <;>
    ring

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

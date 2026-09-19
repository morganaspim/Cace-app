import Mathlib
import CACEFormal.AffineGeometry
import CACEFormal.Piola
import CACEFormal.P1RT0Element

namespace CACEFormal

/-!
# Affine transport for exact P1/RT0 element data

This module connects four previously separate exact layers:

1. arbitrary affine triangle geometry;
2. the contravariant Piola/cofactor identity;
3. exact P1/RT0 polynomial semantics;
4. oriented edge normal-measure vectors.

The resulting theorems are algebraic.  They are intended to be reused by the
mesh assembly layer rather than replacing it.
-/

namespace AffineP1RT0Transport

/-- Oriented edge normal multiplied by edge length, represented as a point/vector. -/
def edgeNormalMeasure (a b : Point2) : Point2 :=
  ⟨P1RT0Element.edgeNormalX a b, P1RT0Element.edgeNormalY a b⟩

/-- Mapping an oriented edge by an affine map sends its normal-measure vector
through the cofactor of the linear part. -/
theorem edgeNormalMeasure_map (F : Affine2) (a b : Point2) :
    edgeNormalMeasure (F.mapPoint a) (F.mapPoint b) =
      F.cofactorNormal (edgeNormalMeasure a b) := by
  rcases F with ⟨aa, ab, ac, ad, tx, ty⟩
  rcases a with ⟨ax, ay⟩
  rcases b with ⟨bx, by_⟩
  ext <;>
    dsimp [edgeNormalMeasure, Affine2.mapPoint, Affine2.cofactorNormal,
      P1RT0Element.edgeNormalX, P1RT0Element.edgeNormalY] <;>
    ring

/-- Evaluate an RT0 field as a two-component vector. -/
def evalRT0Point (q : RT0Affine) (p : Point2) : Point2 :=
  ⟨q.evalX p, q.evalY p⟩

/-- Flux of a vector against an oriented edge normal-measure vector. -/
def vectorEdgeFlux (q : Point2) (a b : Point2) : ℝ :=
  q.x * P1RT0Element.edgeNormalX a b +
    q.y * P1RT0Element.edgeNormalY a b

/-- Existing RT0 edge flux is exactly vector-edge flux of the pointwise value. -/
theorem edgeFlux_eq_vectorEdgeFlux (q : RT0Affine) (a b p : Point2) :
    P1RT0Element.edgeFlux q a b p = vectorEdgeFlux (evalRT0Point q p) a b := by
  rfl

/-- The general affine Piola theorem preserves vector flux across a mapped edge. -/
theorem piola_vectorEdgeFlux_map
    (F : Affine2) (q a b : Point2) (hdet : F.linearDet ≠ 0) :
    vectorEdgeFlux (F.piolaVector q) (F.mapPoint a) (F.mapPoint b) =
      vectorEdgeFlux q a b := by
  have hn := edgeNormalMeasure_map F a b
  have hnx := congrArg Point2.x hn
  have hny := congrArg Point2.y hn
  have hp :=
    Affine2.piola_cofactor_flux F q (edgeNormalMeasure a b) hdet
  dsimp [edgeNormalMeasure] at hnx hny hp
  unfold vectorEdgeFlux
  rw [hnx, hny]
  exact hp

/-- Physical RT0 coefficients obtained by contravariant Piola transport of a
reference RT0 field through an affine map. -/
noncomputable def piolaRT0 (F : Affine2) (q : RT0Affine) : RT0Affine where
  cx := (F.a * q.cx + F.b * q.cy - q.radial * F.tx) / F.linearDet
  cy := (F.c * q.cx + F.d * q.cy - q.radial * F.ty) / F.linearDet
  radial := q.radial / F.linearDet

/-- Pointwise evaluation of transported RT0 data agrees exactly with the
contravariant Piola transform at the mapped point. -/
theorem evalRT0Point_piolaRT0_map
    (F : Affine2) (q : RT0Affine) (p : Point2) (hdet : F.linearDet ≠ 0) :
    evalRT0Point (piolaRT0 F q) (F.mapPoint p) =
      F.piolaVector (evalRT0Point q p) := by
  rcases F with ⟨aa, ab, ac, ad, tx, ty⟩
  rcases q with ⟨qx, qy, r⟩
  rcases p with ⟨x, y⟩
  change aa * ad - ab * ac ≠ 0 at hdet
  ext <;>
    dsimp [evalRT0Point, piolaRT0, Affine2.mapPoint, Affine2.piolaVector,
      Affine2.linearDet, RT0Affine.evalX, RT0Affine.evalY] <;>
    field_simp [hdet] <;>
    ring

/-- Therefore RT0 normal flux is exactly invariant under affine Piola
transport when the oriented edge itself is mapped by the same affine map. -/
theorem edgeFlux_piolaRT0_map
    (F : Affine2) (q : RT0Affine) (a b p : Point2)
    (hdet : F.linearDet ≠ 0) :
    P1RT0Element.edgeFlux (piolaRT0 F q)
        (F.mapPoint a) (F.mapPoint b) (F.mapPoint p) =
      P1RT0Element.edgeFlux q a b p := by
  rw [edgeFlux_eq_vectorEdgeFlux, edgeFlux_eq_vectorEdgeFlux]
  rw [evalRT0Point_piolaRT0_map F q p hdet]
  exact piola_vectorEdgeFlux_map F (evalRT0Point q p) a b hdet

/-- Pull an affine P1 scalar polynomial from reference coordinates to physical
coordinates.  The gradient is transformed by inverse transpose. -/
noncomputable def pullP1 (F : Affine2) (v : P1Affine) : P1Affine :=
  let gx := (F.d * v.gx - F.c * v.gy) / F.linearDet
  let gy := (-F.b * v.gx + F.a * v.gy) / F.linearDet
  ⟨v.c - gx * F.tx - gy * F.ty, gx, gy⟩

/-- The physical P1 polynomial evaluates to the reference polynomial at mapped
points. -/
theorem pullP1_eval_map
    (F : Affine2) (v : P1Affine) (p : Point2) (hdet : F.linearDet ≠ 0) :
    (pullP1 F v).eval (F.mapPoint p) = v.eval p := by
  rcases F with ⟨aa, ab, ac, ad, tx, ty⟩
  rcases v with ⟨vc, gx, gy⟩
  rcases p with ⟨x, y⟩
  change aa * ad - ab * ac ≠ 0 at hdet
  have hdet_comm : ad * aa - ac * ab ≠ 0 := by
    intro h
    apply hdet
    calc
      aa * ad - ab * ac = ad * aa - ac * ab := by ring
      _ = 0 := h
  dsimp [pullP1, Affine2.mapPoint, Affine2.linearDet, P1Affine.eval]
  field_simp [hdet, hdet_comm]
  ring

/-- Endpoint data entering the exact P1/RT0 edge pairing are simultaneously
preserved by scalar pullback and Piola flux transport. -/
theorem edge_endpoint_data_map
    (F : Affine2) (v : P1Affine) (q : RT0Affine) (a b : Point2)
    (hdet : F.linearDet ≠ 0) :
    (pullP1 F v).eval (F.mapPoint a) = v.eval a ∧
    (pullP1 F v).eval (F.mapPoint b) = v.eval b ∧
    P1RT0Element.edgeFlux (piolaRT0 F q)
        (F.mapPoint a) (F.mapPoint b) (F.mapPoint a) =
      P1RT0Element.edgeFlux q a b a ∧
    P1RT0Element.edgeFlux (piolaRT0 F q)
        (F.mapPoint a) (F.mapPoint b) (F.mapPoint b) =
      P1RT0Element.edgeFlux q a b b := by
  exact ⟨pullP1_eval_map F v a hdet,
    pullP1_eval_map F v b hdet,
    edgeFlux_piolaRT0_map F q a b a hdet,
    edgeFlux_piolaRT0_map F q a b b hdet⟩


/-- Divergence of an affine RT0 field scales by the inverse affine
Jacobian determinant under contravariant Piola transport. -/
theorem divergence_piolaRT0 (F : Affine2) (q : RT0Affine) :
    (piolaRT0 F q).divergence = q.divergence / F.linearDet := by
  dsimp [piolaRT0, RT0Affine.divergence]
  ring

/-- The P1-gradient/RT0 pairing at a mapped point scales by the inverse
Jacobian determinant. -/
theorem dotGrad_piola_pull_map
    (F : Affine2) (v : P1Affine) (q : RT0Affine) (p : Point2)
    (hdet : F.linearDet ≠ 0) :
    (piolaRT0 F q).dotGrad (pullP1 F v) (F.mapPoint p) =
      q.dotGrad v p / F.linearDet := by
  rcases F with ⟨aa, ab, ac, ad, tx, ty⟩
  rcases v with ⟨vc, gx, gy⟩
  rcases q with ⟨qx, qy, r⟩
  rcases p with ⟨x, y⟩
  change aa * ad - ab * ac ≠ 0 at hdet
  dsimp [piolaRT0, pullP1, Affine2.mapPoint, Affine2.linearDet,
    RT0Affine.dotGrad, RT0Affine.evalX, RT0Affine.evalY]
  field_simp [hdet]
  ring

/-- Exact cell pairing is invariant under affine scalar pullback and
contravariant Piola transport. -/
theorem cellPairing_map
    (F : Affine2) (T : Triangle2) (v : P1Affine) (q : RT0Affine)
    (hdet : F.linearDet ≠ 0) :
    P1RT0Element.cellPairing (F.mapTriangle T) (pullP1 F v) (piolaRT0 F q) =
      P1RT0Element.cellPairing T v q := by
  unfold P1RT0Element.cellPairing
  rw [Affine2.det_mapTriangle]
  simp only [Affine2.mapTriangle]
  rw [dotGrad_piola_pull_map F v q T.p0 hdet,
      dotGrad_piola_pull_map F v q T.p1 hdet,
      dotGrad_piola_pull_map F v q T.p2 hdet]
  field_simp [hdet]

/-- Exact cell divergence term is invariant under the same affine transport. -/
theorem cellDivergence_map
    (F : Affine2) (T : Triangle2) (v : P1Affine) (q : RT0Affine)
    (hdet : F.linearDet ≠ 0) :
    P1RT0Element.cellDivergence (F.mapTriangle T) (pullP1 F v) (piolaRT0 F q) =
      P1RT0Element.cellDivergence T v q := by
  unfold P1RT0Element.cellDivergence
  rw [Affine2.det_mapTriangle, divergence_piolaRT0]
  simp only [Affine2.mapTriangle]
  rw [pullP1_eval_map F v T.p0 hdet,
      pullP1_eval_map F v T.p1 hdet,
      pullP1_eval_map F v T.p2 hdet]
  field_simp [hdet]

/-- The exact P1/RT0 edge pairing is invariant under affine scalar pullback and
contravariant Piola transport. -/
theorem edgePairing_map
    (F : Affine2) (v : P1Affine) (q : RT0Affine) (a b : Point2)
    (hdet : F.linearDet ≠ 0) :
    P1RT0Element.edgePairing (pullP1 F v) (piolaRT0 F q)
        (F.mapPoint a) (F.mapPoint b) =
      P1RT0Element.edgePairing v q a b := by
  rcases edge_endpoint_data_map F v q a b hdet with ⟨hva, hvb, hfa, hfb⟩
  simp only [P1RT0Element.edgePairing, hva, hvb, hfa, hfb]

/-- Consequently the exact three-edge boundary pairing of one triangle is
affine-Piola invariant. -/
theorem cellFacePairing_map
    (F : Affine2) (T : Triangle2) (v : P1Affine) (q : RT0Affine)
    (hdet : F.linearDet ≠ 0) :
    P1RT0Element.cellFacePairing (F.mapTriangle T) (pullP1 F v) (piolaRT0 F q) =
      P1RT0Element.cellFacePairing T v q := by
  rcases T with ⟨p0, p1, p2⟩
  simp only [P1RT0Element.cellFacePairing, Affine2.mapTriangle]
  rw [edgePairing_map F v q p0 p1 hdet,
      edgePairing_map F v q p1 p2 hdet,
      edgePairing_map F v q p2 p0 hdet]


/-- The exact local Green identity commutes with nonsingular affine
transport.  This packages the affine geometry, P1 pullback, RT0 Piola map,
cell pairing, divergence term, and face pairing into one transported theorem. -/
theorem local_green_identity_map
    (F : Affine2) (T : Triangle2) (v : P1Affine) (q : RT0Affine)
    (hdet : F.linearDet ≠ 0) :
    P1RT0Element.cellPairing (F.mapTriangle T) (pullP1 F v) (piolaRT0 F q) =
      P1RT0Element.cellDivergence (F.mapTriangle T) (pullP1 F v) (piolaRT0 F q) +
        P1RT0Element.cellFacePairing (F.mapTriangle T) (pullP1 F v) (piolaRT0 F q) := by
  rw [cellPairing_map F T v q hdet,
      cellDivergence_map F T v q hdet,
      cellFacePairing_map F T v q hdet]
  exact P1RT0Element.local_green_identity T v q

/-- Every local face slot inherits the exact affine edge-pairing invariance. -/
theorem localFacePairing_map
    (F : Affine2) (T : Triangle2) (v : P1Affine) (q : RT0Affine)
    (s : Fin 3) (hdet : F.linearDet ≠ 0) :
    P1RT0Element.localFacePairing
        (F.mapTriangle T) (pullP1 F v) (piolaRT0 F q) s =
      P1RT0Element.localFacePairing T v q s := by
  fin_cases s <;>
    simp [P1RT0Element.localFacePairing, Affine2.mapTriangle,
      edgePairing_map, hdet]

end AffineP1RT0Transport

end CACEFormal

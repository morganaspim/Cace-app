import Mathlib

namespace CACEFormal

noncomputable section

/-!
v3.24 exact polynomial P1/RT0 element semantics.

This file closes the elementwise algebraic Green identity for an affine P1
scalar field and an RT0 affine vector field on an oriented triangle.  The
formulae are exact closed-form polynomial integration formulae.  No numerical
quadrature and no global mesh-assembly hypothesis is used here.

This is still a finite-element algebra theorem; identifying the closed-form
formulae with Sobolev-space integrals on arbitrary domains belongs to the
continuum v3.26-v3.30 track.
-/

/-- A real two-dimensional point. -/
structure Point2 where
  x : ℝ
  y : ℝ

/-- An ordered triangle. The determinant may be signed; mesh certificates add positivity. -/
structure Triangle2 where
  p0 : Point2
  p1 : Point2
  p2 : Point2

/-- An affine P1 scalar polynomial `c + gx*x + gy*y`. -/
structure P1Affine where
  c : ℝ
  gx : ℝ
  gy : ℝ

/-- An affine RT0 field `(cx + r*x, cy + r*y)`. -/
structure RT0Affine where
  cx : ℝ
  cy : ℝ
  radial : ℝ

namespace P1Affine

def eval (v : P1Affine) (p : Point2) : ℝ :=
  v.c + v.gx * p.x + v.gy * p.y

end P1Affine

namespace RT0Affine

def evalX (q : RT0Affine) (p : Point2) : ℝ := q.cx + q.radial * p.x

def evalY (q : RT0Affine) (p : Point2) : ℝ := q.cy + q.radial * p.y

/-- The divergence of an RT0 affine field in two dimensions. -/
def divergence (q : RT0Affine) : ℝ := 2 * q.radial

/-- Pointwise `q · ∇v`; affine in the point. -/
def dotGrad (q : RT0Affine) (v : P1Affine) (p : Point2) : ℝ :=
  evalX q p * v.gx + evalY q p * v.gy

end RT0Affine

namespace Triangle2

/-- Twice the signed area of the ordered triangle. -/
def det (T : Triangle2) : ℝ :=
  (T.p1.x - T.p0.x) * (T.p2.y - T.p0.y) -
    (T.p1.y - T.p0.y) * (T.p2.x - T.p0.x)

end Triangle2

namespace P1RT0Element

/--
Exact triangle integral of `q · ∇v`: an affine function integrates as signed
area times the average of its three vertex values.
-/
def cellPairing (T : Triangle2) (v : P1Affine) (q : RT0Affine) : ℝ :=
  T.det / 6 *
    (q.dotGrad v T.p0 + q.dotGrad v T.p1 + q.dotGrad v T.p2)

/-- Sign convention used by the assembly layer: `-∫_K (div q) v`. -/
def cellDivergence (T : Triangle2) (v : P1Affine) (q : RT0Affine) : ℝ :=
  -(T.det / 6 * q.divergence *
    (v.eval T.p0 + v.eval T.p1 + v.eval T.p2))

/-- x-component of the outward normal multiplied by edge length for a CCW edge. -/
def edgeNormalX (a b : Point2) : ℝ := b.y - a.y

/-- y-component of the outward normal multiplied by edge length for a CCW edge. -/
def edgeNormalY (a b : Point2) : ℝ := -(b.x - a.x)

/-- RT0 normal-flux polynomial at an endpoint of an oriented edge. -/
def edgeFlux (q : RT0Affine) (a b p : Point2) : ℝ :=
  q.evalX p * edgeNormalX a b + q.evalY p * edgeNormalY a b

/--
Exact integral of the product of two affine edge functions, `v` and `q·n`,
over the unit edge parameter.  The geometric edge length is already carried by
`edgeNormalX/edgeNormalY`.
-/
def edgePairing (v : P1Affine) (q : RT0Affine) (a b : Point2) : ℝ :=
  let va := v.eval a
  let vb := v.eval b
  let ga := edgeFlux q a b a
  let gb := edgeFlux q a b b
  (2 * va * ga + va * gb + vb * ga + 2 * vb * gb) / 6

/-- Sum of the three outward-oriented face contributions. -/
def cellFacePairing (T : Triangle2) (v : P1Affine) (q : RT0Affine) : ℝ :=
  edgePairing v q T.p0 T.p1 +
    edgePairing v q T.p1 T.p2 +
    edgePairing v q T.p2 T.p0

/-- Face contribution associated with local slot 0, 1, or 2. -/
def localFacePairing (T : Triangle2) (v : P1Affine) (q : RT0Affine)
    (s : Fin 3) : ℝ :=
  match s.val with
  | 0 => edgePairing v q T.p0 T.p1
  | 1 => edgePairing v q T.p1 T.p2
  | _ => edgePairing v q T.p2 T.p0

/-- The three local face contributions are exactly the element boundary sum. -/
theorem sum_localFacePairing (T : Triangle2) (v : P1Affine) (q : RT0Affine) :
    (∑ s : Fin 3, localFacePairing T v q s) = cellFacePairing T v q := by
  rw [Fin.sum_univ_three]
  rfl

/--
Closed elementwise P1/RT0 Green identity, derived from the polynomial formulae.
No Green identity is assumed as a certificate field in this theorem.
-/
theorem local_green_identity (T : Triangle2) (v : P1Affine) (q : RT0Affine) :
    cellPairing T v q = cellDivergence T v q + cellFacePairing T v q := by
  rcases T with ⟨⟨x0, y0⟩, ⟨x1, y1⟩, ⟨x2, y2⟩⟩
  rcases v with ⟨c, gx, gy⟩
  rcases q with ⟨cx, cy, r⟩
  dsimp [cellPairing, cellDivergence, cellFacePairing, edgePairing,
    edgeFlux, edgeNormalX, edgeNormalY, P1Affine.eval, RT0Affine.evalX,
    RT0Affine.evalY, RT0Affine.dotGrad, RT0Affine.divergence, Triangle2.det]
  ring

end P1RT0Element

end

end CACEFormal

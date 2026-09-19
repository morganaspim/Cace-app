import Mathlib
import CACEFormal.ReferenceSimplexNormalization
import CACEFormal.AffineP1RT0Transport

namespace CACEFormal

/-!
# Executable exact rational geometry and transport

The trust-bearing real-number layer is ideal for mathematical specification but
uses `noncomputable` definitions where exact real division is involved.  This
module mirrors the core affine-normalization and P1/RT0 transport formulas over
`ℚ`, where all operations are executable.

Correspondence theorems embed each rational result into `ℝ` and identify it
with the existing formal specification.  This is the preferred exact runtime
path for rational input data.
-/

namespace ExecutableRational

structure Point where
  x : ℚ
  y : ℚ
  deriving DecidableEq, Repr

structure Triangle where
  p0 : Point
  p1 : Point
  p2 : Point
  deriving DecidableEq, Repr

structure Affine where
  a : ℚ
  b : ℚ
  c : ℚ
  d : ℚ
  tx : ℚ
  ty : ℚ
  deriving DecidableEq, Repr

structure P1 where
  c : ℚ
  gx : ℚ
  gy : ℚ
  deriving DecidableEq, Repr

structure RT0 where
  cx : ℚ
  cy : ℚ
  radial : ℚ
  deriving DecidableEq, Repr

namespace Point

def toReal (p : Point) : Point2 :=
  ⟨(p.x : ℝ), (p.y : ℝ)⟩

end Point

namespace Triangle

def det (T : Triangle) : ℚ :=
  (T.p1.x - T.p0.x) * (T.p2.y - T.p0.y) -
    (T.p1.y - T.p0.y) * (T.p2.x - T.p0.x)

def toReal (T : Triangle) : Triangle2 :=
  ⟨T.p0.toReal, T.p1.toReal, T.p2.toReal⟩

@[simp] theorem det_toReal (T : Triangle) :
    T.toReal.det = (T.det : ℝ) := by
  cases T
  simp [toReal, det, Point.toReal, Triangle2.det]

end Triangle

namespace Affine

def linearDet (F : Affine) : ℚ :=
  F.a * F.d - F.b * F.c

def mapPoint (F : Affine) (p : Point) : Point :=
  ⟨F.a * p.x + F.b * p.y + F.tx,
   F.c * p.x + F.d * p.y + F.ty⟩

def translation (v : Point) : Affine :=
  ⟨1, 0, 0, 1, v.x, v.y⟩

def comp (outer inner : Affine) : Affine :=
  ⟨outer.a * inner.a + outer.b * inner.c,
   outer.a * inner.b + outer.b * inner.d,
   outer.c * inner.a + outer.d * inner.c,
   outer.c * inner.b + outer.d * inner.d,
   outer.a * inner.tx + outer.b * inner.ty + outer.tx,
   outer.c * inner.tx + outer.d * inner.ty + outer.ty⟩

def toReal (F : Affine) : Affine2 :=
  ⟨(F.a : ℝ), (F.b : ℝ), (F.c : ℝ), (F.d : ℝ),
   (F.tx : ℝ), (F.ty : ℝ)⟩

@[simp] theorem linearDet_toReal (F : Affine) :
    F.toReal.linearDet = (F.linearDet : ℝ) := by
  cases F
  simp [toReal, linearDet, Affine2.linearDet]

@[simp] theorem mapPoint_toReal (F : Affine) (p : Point) :
    (F.mapPoint p).toReal = F.toReal.mapPoint p.toReal := by
  cases F
  cases p
  simp [mapPoint, Point.toReal, toReal, Affine2.mapPoint]

@[simp] theorem translation_toReal (v : Point) :
    (translation v).toReal = Affine2.translation v.toReal := by
  cases v
  simp [translation, toReal, Point.toReal, Affine2.translation]

@[simp] theorem comp_toReal (outer inner : Affine) :
    (comp outer inner).toReal = Affine2.comp outer.toReal inner.toReal := by
  cases outer
  cases inner
  simp [comp, toReal, Affine2.comp]

end Affine

def edge01 (T : Triangle) : Point :=
  ⟨T.p1.x - T.p0.x, T.p1.y - T.p0.y⟩

def edge02 (T : Triangle) : Point :=
  ⟨T.p2.x - T.p0.x, T.p2.y - T.p0.y⟩

def edgeDet (e1 e2 : Point) : ℚ :=
  e1.x * e2.y - e1.y * e2.x

@[simp] theorem edgeDet_edges (T : Triangle) :
    edgeDet (edge01 T) (edge02 T) = T.det := by
  rfl

def recenterMap (T : Triangle) : Affine :=
  Affine.translation ⟨-T.p0.x, -T.p0.y⟩

def inverseEdgeLinear (e1 e2 : Point) : Affine :=
  let Δ := edgeDet e1 e2
  ⟨e2.y / Δ, -e2.x / Δ, -e1.y / Δ, e1.x / Δ, 0, 0⟩

/-- Fully executable rational reference-simplex normalizer. -/
def normalizer (T : Triangle) : Affine :=
  Affine.comp (inverseEdgeLinear (edge01 T) (edge02 T)) (recenterMap T)

@[simp] theorem edge01_toReal (T : Triangle) :
    (edge01 T).toReal =
      ReferenceSimplexNormalization.edge01 T.toReal := by
  cases T
  simp [edge01, Point.toReal, Triangle.toReal,
    ReferenceSimplexNormalization.edge01]

@[simp] theorem edge02_toReal (T : Triangle) :
    (edge02 T).toReal =
      ReferenceSimplexNormalization.edge02 T.toReal := by
  cases T
  simp [edge02, Point.toReal, Triangle.toReal,
    ReferenceSimplexNormalization.edge02]

@[simp] theorem edgeDet_toReal (e1 e2 : Point) :
    (edgeDet e1 e2 : ℝ) =
      ReferenceSimplexNormalization.edgeDet e1.toReal e2.toReal := by
  cases e1
  cases e2
  simp [edgeDet, Point.toReal, ReferenceSimplexNormalization.edgeDet]

@[simp] theorem recenterMap_toReal (T : Triangle) :
    (recenterMap T).toReal =
      ReferenceSimplexNormalization.recenterMap T.toReal := by
  cases T
  simp [recenterMap, Triangle.toReal,
    ReferenceSimplexNormalization.recenterMap]

@[simp] theorem inverseEdgeLinear_toReal (e1 e2 : Point) :
    (inverseEdgeLinear e1 e2).toReal =
      ReferenceSimplexNormalization.inverseEdgeLinear e1.toReal e2.toReal := by
  cases e1
  cases e2
  simp [inverseEdgeLinear, edgeDet, Affine.toReal, Point.toReal,
    ReferenceSimplexNormalization.inverseEdgeLinear,
    ReferenceSimplexNormalization.edgeDet]

/-- Exact correspondence: the executable rational normalizer embeds to the
trust-bearing real normalizer. -/
@[simp] theorem normalizer_toReal (T : Triangle) :
    (normalizer T).toReal =
      ReferenceSimplexNormalization.normalizer T.toReal := by
  simp [normalizer, ReferenceSimplexNormalization.normalizer]

namespace P1

def toReal (v : P1) : P1Affine :=
  ⟨(v.c : ℝ), (v.gx : ℝ), (v.gy : ℝ)⟩

def transportSourceToTarget (F : Affine) (v : P1) : P1 :=
  let gx := (F.d * v.gx - F.c * v.gy) / F.linearDet
  let gy := (-F.b * v.gx + F.a * v.gy) / F.linearDet
  ⟨v.c - gx * F.tx - gy * F.ty, gx, gy⟩

/-- Executable rational P1 transport agrees exactly with the real formal
transport after embedding into `ℝ`. -/
@[simp] theorem transportSourceToTarget_toReal (F : Affine) (v : P1) :
    (transportSourceToTarget F v).toReal =
      AffineP1RT0Transport.transportP1SourceToTarget F.toReal v.toReal := by
  cases F
  cases v
  simp [transportSourceToTarget, toReal, Affine.linearDet, Affine.toReal,
    Affine2.linearDet, AffineP1RT0Transport.transportP1SourceToTarget,
    AffineP1RT0Transport.pullP1]

end P1

namespace RT0

def toReal (q : RT0) : RT0Affine :=
  ⟨(q.cx : ℝ), (q.cy : ℝ), (q.radial : ℝ)⟩

def transportSourceToTarget (F : Affine) (q : RT0) : RT0 :=
  ⟨(F.a * q.cx + F.b * q.cy - q.radial * F.tx) / F.linearDet,
   (F.c * q.cx + F.d * q.cy - q.radial * F.ty) / F.linearDet,
   q.radial / F.linearDet⟩

/-- Executable rational RT0 Piola transport agrees exactly with the real formal
transport after embedding into `ℝ`. -/
@[simp] theorem transportSourceToTarget_toReal (F : Affine) (q : RT0) :
    (transportSourceToTarget F q).toReal =
      AffineP1RT0Transport.transportRT0SourceToTarget F.toReal q.toReal := by
  cases F
  cases q
  simp [transportSourceToTarget, toReal, Affine.linearDet, Affine.toReal,
    Affine2.linearDet, AffineP1RT0Transport.transportRT0SourceToTarget,
    AffineP1RT0Transport.piolaRT0]

end RT0

end ExecutableRational

end CACEFormal

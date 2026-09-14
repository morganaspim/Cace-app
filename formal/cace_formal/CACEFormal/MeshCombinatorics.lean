import Mathlib.Data.Finset.Basic

namespace CACEFormal

/-- Minimal orientation sign type used by generated finite-mesh certificates. -/
inductive OrientationSign where
  | pos
  | neg
  deriving DecidableEq, Repr

/-- Opposite orientations encode cancellation on an interior facet. -/
def OrientationSign.opposite : OrientationSign → OrientationSign
  | .pos => .neg
  | .neg => .pos

@[simp] theorem OrientationSign.opposite_opposite (s : OrientationSign) :
    s.opposite.opposite = s := by
  cases s <;> rfl

/-- Finite-mesh interior facets are certified by a pair of opposite signs.
This deliberately stays combinatorial; analytic trace data live in a later bridge. -/
structure InteriorFacetCertificate where
  left : OrientationSign
  right : OrientationSign
  opposite : right = left.opposite

end CACEFormal

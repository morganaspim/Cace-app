import Mathlib.LinearAlgebra.AffineSpace.AffineSubspace.Basic

namespace CACEFormal

/-- CACE keeps primal/dual admissibility abstract until the finite-mesh bridge instantiates it. -/
structure AdmissiblePair (V Q : Type*) [AddCommGroup V] [Module ℝ V] [AddCommGroup Q] [Module ℝ Q] where
  primalNonempty : Nonempty V
  dualNonempty : Nonempty Q

end CACEFormal

import CACEFormal.AffineGeometry
import CACEFormal.ExteriorPowerTransport
import CACEFormal.Piola
import CACEFormal.DualBladePiola
import CACEFormal.GraphRegularizationCriterion
import CACEFormal.RealGraphRegularizationCriterion
import CACEFormal.WeightedEnergy
import CACEFormal.BoxPragerSynge

namespace CACEFormal

/-!
# Proof guardrail API canaries

This module is intentionally NOT imported by the audited root.  It is compiled
before impacted modules and before the root in exact-pin preflight.

Its job is to exercise fragile public theorem/API seams cheaply.  If Mathlib
elaboration, scalar inference, affine identities, or promoted theorem names
drift, this small target should fail before the expensive full-root build.
-/

example (F : Affine2) (u v : Point2) :
    ExteriorPower2.wedge
        (ExteriorPower2.grade1 F u)
        (ExteriorPower2.grade1 F v) =
      F.linearDet * ExteriorPower2.wedge u v :=
  ExteriorPower2.wedge_grade1 F u v

example (F : Affine2) (q t : Point2) (hdet : F.linearDet ≠ 0) :
    DualBladePiola.dot
        (F.piolaVector q)
        (DualBladePiola.dual (ExteriorPower2.grade1 F t)) =
      DualBladePiola.dot q (DualBladePiola.dual t) :=
  DualBladePiola.piola_dualBlade_flux F q t hdet

#check Continuum.complexSmoothGraphClosure_eq_distributional_of_regularizer
#check Continuum.distributional_le_complexSmoothGraphClosure_of_regularizer
#check Continuum.realHDivSmoothGraphClosure_eq_distributionalPreimage_of_regularizer
#check Continuum.realDistributionalPreimage_le_HDivSmoothGraphClosure_of_regularizer

#check SPDEnergyOperator.energySq
#check SPDEnergyOperator.weighted_hypercircle
#check Continuum.boxGraphPragerSynge
#check Continuum.boxGraphWeightedHypercircle

end CACEFormal

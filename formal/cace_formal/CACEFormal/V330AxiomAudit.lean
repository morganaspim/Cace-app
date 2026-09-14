import CACEFormal.SmoothBoxGreenAuto
import CACEFormal.GraphRegularizationCriterion

/-!
# v3.30 kernel-assumption audit

CI compiles this file with the pinned Lean/mathlib toolchain and parses the `#print axioms` output
for every new proof-strengthening endpoint. Promotion is rejected if a theorem depends on `sorryAx`
or on any axiom outside the small foundational whitelist enforced by the workflow.
-/

#print axioms CACEFormal.Continuum.smoothBoxProduct_hasFDerivAt
#print axioms CACEFormal.Continuum.smoothBoxProduct_divergence_eq_greenVolume
#print axioms CACEFormal.Continuum.smoothBoxGreen_schwartz
#print axioms CACEFormal.Continuum.boxGraphNormalTrace_smooth_eq_classical_auto
#print axioms CACEFormal.Continuum.complexSmoothGraphClosure_eq_distributional_of_regularizer
#print axioms CACEFormal.Continuum.distributional_le_complexSmoothGraphClosure_of_regularizer

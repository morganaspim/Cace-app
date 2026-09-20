import CACEFormal.RuntimeRMKCoreBridge
import CACEFormal.RuntimeGroupExteriorBridge

/-!
# RMK runtime-linkage kernel axiom audit

This audit is intentionally separate from the continuum v3.30 audit. It covers
only the formally modeled two-dimensional rational RMK bridge surface.

Passing this audit does not establish correctness of every C++ RMK algorithm,
general sparse/RREF/polynomial/group implementations, or runtime-to-Lean packet
identity. Those remain separate source-to-formal obligations.
-/

#print axioms CACEFormal.RuntimeRMK.Mat2.linearDet_toReal
#print axioms CACEFormal.RuntimeRMK.Mat2.matVec_identity
#print axioms CACEFormal.RuntimeRMK.Mat2.matVec_mul
#print axioms CACEFormal.RuntimeRMK.Mat2.matVec_to_grade1
#print axioms CACEFormal.RuntimeRMK.AffineMap2.apply_toReal
#print axioms CACEFormal.RuntimeRMK.AffineMap2.linearDet_toReal
#print axioms CACEFormal.RuntimeRMK.verifiesSolution_sound
#print axioms CACEFormal.RuntimeRMK.verifiesInverse_sound
#print axioms CACEFormal.RuntimeRMK.PlaneRotor2.det_matrix
#print axioms CACEFormal.RuntimeRMK.PlaneRotor2.normSq_apply

#print axioms CACEFormal.RuntimeRMK.wedge_toReal
#print axioms CACEFormal.RuntimeRMK.wedge_matVec
#print axioms CACEFormal.RuntimeRMK.wedge_pushforward_refines_exteriorPower
#print axioms CACEFormal.RuntimeRMK.Permutation2.act_eq_matVec
#print axioms CACEFormal.RuntimeRMK.Permutation2.det_matrix_eq_sign
#print axioms CACEFormal.RuntimeRMK.Permutation2.wedge_act
#print axioms CACEFormal.RuntimeRMK.Permutation2.swap_toReal_eq_affineSwap
#print axioms CACEFormal.RuntimeRMK.triangle_swap01_det

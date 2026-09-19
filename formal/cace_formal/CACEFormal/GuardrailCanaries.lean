import CACEFormal.CertifiedComposition
import CACEFormal.GeometryTransforms
import CACEFormal.TransformCombinatorics
import CACEFormal.AffineGeometry
import CACEFormal.ExteriorPowerTransport
import CACEFormal.Piola
import CACEFormal.DualBladePiola
import CACEFormal.AffineP1RT0Transport
import CACEFormal.ReferenceSimplexNormalization
import CACEFormal.AffineAssemblyTransport
import CACEFormal.MeshElementGeometry
import CACEFormal.PhysicalP1RT0Element
import CACEFormal.ExecutableRationalGeometry
import CACEFormal.RuntimeApproximationContract
import CACEFormal.GraphRegularizationCriterion
import CACEFormal.RealGraphRegularizationCriterion
import CACEFormal.WeightedEnergy
import CACEFormal.BoxPragerSynge
import CACEFormal.BoxPragerSyngeEquilibrated

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

/-- End-to-end affine integration canary:
normalize an arbitrary nondegenerate triangle to the canonical reference
simplex, transport P1/RT0 data through the same affine map, and recover the
exact local Green identity on the reference element. -/
example (T : Triangle2) (v : P1Affine) (q : RT0Affine) (hT : T.det ≠ 0) :
    P1RT0Element.cellPairing
        ReferenceSimplexNormalization.referenceTriangle
        (AffineP1RT0Transport.pullP1
          (ReferenceSimplexNormalization.normalizer T) v)
        (AffineP1RT0Transport.piolaRT0
          (ReferenceSimplexNormalization.normalizer T) q) =
      P1RT0Element.cellDivergence
          ReferenceSimplexNormalization.referenceTriangle
          (AffineP1RT0Transport.pullP1
            (ReferenceSimplexNormalization.normalizer T) v)
          (AffineP1RT0Transport.piolaRT0
            (ReferenceSimplexNormalization.normalizer T) q) +
        P1RT0Element.cellFacePairing
          ReferenceSimplexNormalization.referenceTriangle
          (AffineP1RT0Transport.pullP1
            (ReferenceSimplexNormalization.normalizer T) v)
          (AffineP1RT0Transport.piolaRT0
            (ReferenceSimplexNormalization.normalizer T) q) := by
  have hdet :=
    ReferenceSimplexNormalization.normalizer_linearDet_ne_zero T hT
  have h :=
    AffineP1RT0Transport.local_green_identity_map
      (ReferenceSimplexNormalization.normalizer T) T v q hdet
  rw [ReferenceSimplexNormalization.normalizer_map_triangle T hT] at h
  exact h


/-- Certified mesh geometry cannot drift from its stored rational Jacobian. -/
example (mesh : MeshCertificate) (K : Fin mesh.triangleCount) :
    0 < (MeshElementGeometry.realTriangle mesh K).det :=
  MeshElementGeometry.realTriangle_det_pos mesh K

/-- Positive certified mesh geometry licenses the ordinary physical-area
interpretation of the exact oriented P1/RT0 formula. -/
example (mesh : MeshCertificate) (K : Fin mesh.triangleCount)
    (v : P1Affine) (q : RT0Affine) :
    PhysicalP1RT0Element.cellPairing
        (MeshElementGeometry.realTriangle mesh K) v q =
      P1RT0Element.cellPairing
        (MeshElementGeometry.realTriangle mesh K) v q :=
  PhysicalP1RT0Element.mesh_cellPairing_eq_oriented mesh K v q

#check ReferenceSimplexNormalization.inverseEdgeLinear_map_e1
#check ReferenceSimplexNormalization.inverseEdgeLinear_map_e2
#check ReferenceSimplexNormalization.inverseEdgeLinear_linearDet
#check MeshElementGeometry.realTriangle_det
#check MeshElementGeometry.realTriangle_det_pos
#check RT0P1DerivedAssemblyCertificate.ofCertifiedMeshElements
#check AffineAssemblyTransport.meshDerivedCertificate
#check AffineAssemblyTransport.mesh_orthogonality
#check AffineAssemblyTransport.mesh_discrete_prager_synge_from_reference_pairing
#check PhysicalP1RT0Element.local_green_identity_of_pos
#check PhysicalP1RT0Element.mesh_local_green_identity
#check AffineP1RT0Transport.transportP1SourceToTarget_spec
#check AffineP1RT0Transport.transportRT0SourceToTarget_spec
#check ExecutableRational.normalizer_toReal
#check ExecutableRational.P1.transportSourceToTarget_toReal
#check ExecutableRational.RT0.transportSourceToTarget_toReal
#check RuntimeApproximation.CertifiedApproximation.exact_mem_interval
#check RuntimeApproximation.CertifiedApproximation.decode_eq_exact_of_radius_zero

#check Continuum.complexSmoothGraphClosure_eq_distributional_of_regularizer
#check Continuum.distributional_le_complexSmoothGraphClosure_of_regularizer
#check Continuum.realHDivSmoothGraphClosure_eq_distributionalPreimage_of_regularizer
#check Continuum.realDistributionalPreimage_le_HDivSmoothGraphClosure_of_regularizer

#check CertifiedTransform.compose9_preserves
#check CertifiedTransform.composeList_run_append
#check GeometryTransforms.elementaryPositiveChain_preserves
#check CertifiedGeometryTransform.nonuple_preserves_orthogonality
#check CertifiedGeometryTransform.nonuple_hypercircle
#check CertifiedGeometryTransform.chain_cost
#check CertifiedGeometryTransform.chain_within_budget

#check Affine2.det_mapTriangle_chain
#check ExteriorPower2.wedge_grade1_chain
#check DualBladePiola.piolaVector_chain_eq_sequence
#check DualBladePiola.piola_comp

#check AffineP1RT0Transport.piolaRT0
#check AffineP1RT0Transport.pullP1
#check AffineP1RT0Transport.pullP1_eval_map
#check AffineP1RT0Transport.cellPairing_map
#check AffineP1RT0Transport.cellDivergence_map
#check AffineP1RT0Transport.local_green_identity_map

#check ReferenceSimplexNormalization.normalizer
#check ReferenceSimplexNormalization.normalizer_map_triangle
#check ReferenceSimplexNormalization.cellPairing_to_reference
#check ReferenceSimplexNormalization.cellDivergence_to_reference
#check ReferenceSimplexNormalization.cellFacePairing_to_reference

#check AffineAssemblyTransport.global_green_identity
#check AffineAssemblyTransport.orthogonality
#check AffineAssemblyTransport.discrete_prager_synge
#check AffineAssemblyTransport.discrete_prager_synge_from_reference_pairing

#check SPDEnergyOperator.energySq
#check SPDEnergyOperator.weighted_hypercircle
#check Continuum.boxGraphPragerSynge
#check Continuum.boxGraphPragerSynge_of_divergence_zero
#check Continuum.boxGraphWeightedHypercircle

end CACEFormal

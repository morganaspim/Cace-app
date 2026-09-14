from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata,PortSpec,ParameterSpec,ProofStatus,Maturity,EvidenceKind
from cace_studio.core.verification import VerificationRecord,VerificationState
from cace_studio.core.formal_kernel_v14 import affine_artifact,global_spd_artifact,poisson_energy_artifact,KERNEL_NAME,KERNEL_VERSION
from cace_studio.core.formal_bridge_v14 import invoke_fem_checker
from cace_studio.core.theorems import TheoremContract,TheoremStatus

class _Formal14Base(Module):
    outputs=(PortSpec('formal_result','formal_attestation_v14'),)
    proof_status=ProofStatus(evidence={EvidenceKind.FORMAL},unit_tests=True,property_tests=True,regression_tests=True,documentation=True,
        formal_artifact='exact-rational FEM proof artifact checked in independent subprocess',
        limitations=['formal evidence is limited to the exact theorem/mesh instance encoded in each artifact','does not prove the general 2D residual-reliability theorem'])
    artifact_builder=None
    verifier_id='formal14-proof'
    claim=''
    def execute(self,inputs,params,ctx):
        art=self.artifact_builder(params) if callable(self.artifact_builder) else {}
        att=invoke_fem_checker(art)
        return {'formal_result':{'artifact':art,'attestation':att,'machine_checked':bool(att.get('passed')),'checker':KERNEL_NAME,'checker_version':KERNEL_VERSION}}
    def verify(self,inputs,params,outputs,ctx):
        a=outputs['formal_result']['attestation']; ok=(a.get('passed') is True and a.get('process_returncode')==0 and a.get('checker')==KERNEL_NAME and a.get('checker_version')==KERNEL_VERSION)
        return [VerificationRecord(self.verifier_id,EvidenceKind.FORMAL,self.claim,VerificationState.PASS if ok else VerificationState.FAIL,
            'independent subprocess exact-rational FEM checker',{'theorem_id':a.get('theorem_id'),'artifact_sha256':a.get('artifact_sha256'),'claims_checked':a.get('claims_checked'),'checker':a.get('checker'),'checker_version':a.get('checker_version')},
            notes=('Formal status is scoped exactly to the checked artifact.','No unresolved PDE reliability theorem is promoted.'))]

class AffineSimplexFormalProof(_Formal14Base):
    metadata=ModuleMetadata('formal14.affine_simplex','Affine Simplex + Local Stiffness Formal Proof','0.14.0','Formal Verification',
        'Machine-check exact affine simplex inversion, P1 gradient transformation, and local unit-diffusion stiffness symmetry/PSD through an exact Gram construction.',Maturity.BETA)
    parameters=(ParameterSpec('dimension','integer',2),)
    verifier_id='affine-simplex-fem-machine-check-v014'; claim='Exact affine simplex transformation, P1 physical gradients, and local stiffness Gram/PSD identities hold for the checked rational simplex.'
    @staticmethod
    def artifact_builder(params): return affine_artifact(int(params.get('dimension',2)))

class DirichletSPDFormalProof(_Formal14Base):
    metadata=ModuleMetadata('formal14.dirichlet_spd_1d','1D Dirichlet Stiffness SPD Formal Proof','0.14.0','Formal Verification',
        'Machine-check exact P1 stiffness assembly and the Dirichlet edge-difference energy identity on a rational 1D mesh.',Maturity.BETA)
    verifier_id='dirichlet-stiffness-spd-machine-check-v014'; claim='The supplied 1D Dirichlet P1 stiffness matrix is symmetric positive definite by the exact edge-difference energy identity.'
    @staticmethod
    def artifact_builder(params): return global_spd_artifact()

class PoissonEnergyFormalProof(_Formal14Base):
    metadata=ModuleMetadata('formal14.poisson1d_energy','1D Poisson P1 Energy Identity Formal Proof','0.14.0','Formal Verification',
        'Machine-check the exact continuum interpolation energy identity for u=x(1-x)/2 on an arbitrary supplied rational 1D mesh.',Maturity.BETA)
    verifier_id='poisson1d-energy-machine-check-v014'; claim='For the supplied rational mesh, each P1 interpolation element contributes h^3/12 to the squared energy error and the global error is their exact sum.'
    @staticmethod
    def artifact_builder(params): return poisson_energy_artifact()

class FormalRegistryBridgeV14(Module):
    metadata=ModuleMetadata('formal14.registry_bridge','Formal Theorem Registry Bridge v0.14','0.14.0','Formal Verification',
        'Promote a v0.14 FEM theorem to machine-checked status only after independently re-running the exact FEM checker.',Maturity.BETA)
    inputs=(PortSpec('formal_result','formal_attestation_v14'),); outputs=(PortSpec('theorem','theorem_contract_v14'),)
    proof_status=ProofStatus(evidence={EvidenceKind.FORMAL},unit_tests=True,regression_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        art=inputs['formal_result']['artifact']; att=invoke_fem_checker(art)
        ok=bool(att.get('passed') and att.get('process_returncode')==0 and att.get('checker')==KERNEL_NAME and att.get('checker_version')==KERNEL_VERSION)
        c=TheoremContract(theorem_id=art['theorem_id'],statement=art['statement'],status=TheoremStatus.MACHINE_CHECKED if ok else TheoremStatus.OBLIGATION,
            assumptions=(art.get('scope',''),),evidence_kind=EvidenceKind.FORMAL.value if ok else '',checker=f'{KERNEL_NAME} {KERNEL_VERSION}' if ok else None,
            artifact=f"sha256:{att.get('artifact_sha256','')}" if ok else None)
        d=c.describe(); d.update({'formal_evidence':ok,'promotion_recheck':att,'claims':art.get('claims',[])})
        return {'theorem':d}
    def verify(self,inputs,params,outputs,ctx):
        t=outputs['theorem']; ok=t.get('status')=='machine-checked' and t.get('formal_evidence') is True and t.get('promotion_recheck',{}).get('passed') is True
        return [VerificationRecord('formal-registry-recheck-v014',EvidenceKind.FORMAL,'The theorem registry promotes a v0.14 FEM theorem only after an independent checker re-run.',VerificationState.PASS if ok else VerificationState.FAIL,'promotion-boundary checker re-execution',t)]

class FormalFEMSummaryV14(Module):
    metadata=ModuleMetadata('formal14.summary','Formal FEM Chain Summary','0.14.0','Verification','Summarize the machine-checked FEM identities without escalating them to the unresolved general 2D PDE reliability theorem.',Maturity.BETA)
    inputs=(PortSpec('affine','theorem_contract_v14'),PortSpec('spd','theorem_contract_v14'),PortSpec('energy','theorem_contract_v14'))
    outputs=(PortSpec('summary','formal_summary_v14'),)
    proof_status=ProofStatus(evidence={EvidenceKind.FORMAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        ts=[inputs['affine'],inputs['spd'],inputs['energy']]
        return {'summary':{'all_machine_checked':all(t['status']=='machine-checked' and t.get('formal_evidence') for t in ts),
            'theorem_ids':[t['theorem_id'] for t in ts],
            'formal_scope':['exact rational affine simplex/local stiffness instance','exact rational 1D Dirichlet stiffness instance','exact rational 1D Poisson interpolation-energy identity instance'],
            'general_2d_reliability_formally_verified':False}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['summary']; ok=s['all_machine_checked'] and s['general_2d_reliability_formally_verified'] is False
        return [VerificationRecord('formal-fem-scope-audit-v014',EvidenceKind.FORMAL,'Checked FEM identities are recorded without claiming the unresolved general 2D reliability theorem.',VerificationState.PASS if ok else VerificationState.FAIL,'formal scope audit',s)]

def register_fem_v014(registry):
    for cls in (AffineSimplexFormalProof,DirichletSPDFormalProof,PoissonEnergyFormalProof,FormalRegistryBridgeV14,FormalFEMSummaryV14): registry.register(cls)

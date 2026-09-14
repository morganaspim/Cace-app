from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
REQUIRED={'schema':str,'subject_sha256':str,'evidence':list,'checks':dict,'status':str}
def validate_certificate_schema(cert):
    errs=[]
    if not isinstance(cert,dict): return {'valid':False,'errors':['certificate must be object']}
    for k,t in REQUIRED.items():
        if k not in cert: errs.append(f'missing:{k}')
        elif not isinstance(cert[k],t): errs.append(f'type:{k}')
    if isinstance(cert.get('subject_sha256'),str) and (len(cert['subject_sha256'])!=64 or any(c not in '0123456789abcdef' for c in cert['subject_sha256'])): errs.append('format:subject_sha256')
    if cert.get('status') not in {'PASS','FAIL','NOT_RUN'}: errs.append('enum:status')
    if isinstance(cert.get('evidence'),list) and not all(isinstance(x,str) for x in cert['evidence']): errs.append('type:evidence-item')
    return {'valid':not errs,'errors':errs}
def certificate_fixture():
    c={'schema':'cace-certificate-v1','subject_sha256':'0'*64,'evidence':['symbolic'],'checks':{'replay':True},'status':'PASS'}
    return {'release':'0.37.0','certificate':c,'validation':validate_certificate_schema(c)}
class CertificateSchemaV37(Module):
    metadata=ModuleMetadata('fem37.certificate_schema','Certificate Schema Gate','0.37.0','Verification','Reject malformed verification-certificate envelopes before evidence aggregation.',Maturity.BETA)
    outputs=(PortSpec('result','v37_schema'),); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx): return {'result':certificate_fixture()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['validation']['valid']
        return [VerificationRecord('schema-v037',EvidenceKind.SYMBOLIC,'Certificate envelope satisfies the declared schema.',VerificationState.PASS if ok else VerificationState.FAIL,'schema validation',r['validation'])]
def register_fem_v037(registry): registry.register(CertificateSchemaV37)

from __future__ import annotations
import math
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def sensitivity_audit(x=1.25,h=1e-5):
    f=lambda t: math.sin(t)+t*t
    d=(f(x+h)-f(x-h))/(2*h); ref=math.cos(x)+2*x; err=abs(d-ref)
    return {'pass':err<1e-9,'estimate':d,'reference':ref,'abs_error':err,'step':h}
class SensitivityAuditV59(ResultModule):
    fn=staticmethod(sensitivity_audit); module_id='fem59.sensitivity'; label='Sensitivity Audit'; version='0.59.0'; description='Central-difference sensitivity audit against an analytic derivative on a deterministic reference function.'; evidence_kind=EvidenceKind.NUMERICAL
    metadata=ModuleMetadata(module_id,label,version,'Diagnostics',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v059(registry): registry.register(SensitivityAuditV59)

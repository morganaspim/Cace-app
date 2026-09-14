from __future__ import annotations
import math
from fractions import Fraction
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def interval_dot(a=(1.0,1e-16,-2.0),b=(3.0,4.0,5.0)):
    lo=0.0; hi=0.0
    for x,y in zip(a,b):
        p=x*y; plo=math.nextafter(p,-math.inf); phi=math.nextafter(p,math.inf)
        lo=math.nextafter(lo+plo,-math.inf); hi=math.nextafter(hi+phi,math.inf)
    exact=sum(Fraction.from_float(x)*Fraction.from_float(y) for x,y in zip(a,b))
    ex=float(exact)
    return {'pass':lo<=ex<=hi,'lower':lo,'upper':hi,'exact_float':ex,'width':hi-lo}
class IntervalDotV53(ResultModule):
    fn=staticmethod(interval_dot); module_id='fem53.interval_dot'; label='Outward-Rounded Dot Product'; version='0.53.0'; description='Outward-rounded binary64 enclosure of a dot product, checked against exact rational interpretation.'; evidence_kind=EvidenceKind.INTERVAL
    metadata=ModuleMetadata(module_id,label,version,'Numerics',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v053(registry): registry.register(IntervalDotV53)

from __future__ import annotations
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def normalized_benchmark(samples=(0.010,0.011,0.0095),work_units=1000):
    ordered=sorted(samples); med=ordered[len(ordered)//2]; throughput=work_units/med
    normalized=[s/med for s in samples]
    return {'pass':med>0 and min(normalized)>0,'median_seconds':med,'work_units':work_units,'throughput':throughput,'normalized':normalized}
class BenchmarkNormalizationV70(ResultModule):
    fn=staticmethod(normalized_benchmark); module_id='fem70.benchmark_normalization'; label='Normalized Benchmark Record'; version='0.70.0'; description='Median-based normalized benchmark record separating work units from machine-local wall time.'; evidence_kind=EvidenceKind.NUMERICAL
    metadata=ModuleMetadata(module_id,label,version,'Benchmarking',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v070(registry): registry.register(BenchmarkNormalizationV70)

from __future__ import annotations
import hashlib, json, math
from dataclasses import dataclass
from typing import Iterable

from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata, Maturity, EvidenceKind, ProofStatus

RELIABILITY_THEOREM_ID = 'poisson2d-p1-mesh-uniform-residual-reliability-v0.76'

DEFAULT_PREMISES = (
    'conforming_mesh',
    'shape_regular_family',
    'uniform_ellipticity',
    'residual_term',
    'jump_term',
    'homogeneous_dirichlet',
)


def _canonical_hash(x) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _validate_case(c):
    req = {'case_id','ratio_upper','shape_ratio','alpha_lower','premises','evidence_scope'}
    missing = sorted(req-set(c))
    if missing: raise ValueError(f'missing case fields: {missing}')
    if not (math.isfinite(float(c['ratio_upper'])) and float(c['ratio_upper']) >= 0): raise ValueError('ratio_upper must be finite and nonnegative')
    if not (math.isfinite(float(c['shape_ratio'])) and float(c['shape_ratio']) > 0): raise ValueError('shape_ratio must be positive')
    if not (math.isfinite(float(c['alpha_lower'])) and float(c['alpha_lower']) > 0): raise ValueError('alpha_lower must be positive')
    if not isinstance(c['premises'], dict): raise ValueError('premises must be a mapping')
    return True


def premise_ablation(cases: Iterable[dict], threshold: float = 4.0):
    """Empirical premise stress test. It never proves logical necessity."""
    cases=[dict(c) for c in cases]
    for c in cases: _validate_case(c)
    rows=[]
    for p in DEFAULT_PREMISES:
        on=[float(c['ratio_upper']) for c in cases if bool(c['premises'].get(p, False))]
        off=[float(c['ratio_upper']) for c in cases if not bool(c['premises'].get(p, False))]
        max_on=max(on) if on else None; max_off=max(off) if off else None
        stress = None if max_on is None or max_off is None else max_off/max(max_on,1e-300)
        rows.append({'premise':p,'n_on':len(on),'n_off':len(off),'max_ratio_on':max_on,'max_ratio_off':max_off,
                     'stress_factor':stress,'empirical_warning': bool(max_off is not None and max_off>threshold)})
    return rows


def minimize_counterexample(case: dict, threshold: float = 4.0):
    """Return a minimal *recorded* set of false premises for an observed bad case.
    No unobserved counterfactual is invented.
    """
    _validate_case(case)
    bad=float(case['ratio_upper'])>threshold
    false_premises=sorted([p for p in DEFAULT_PREMISES if not bool(case['premises'].get(p,False))])
    return {'case_id':case['case_id'],'is_counterexample_candidate':bad,'threshold':threshold,
            'false_premises':false_premises,'minimality_scope':'recorded-premise-description-only',
            'formal_counterexample':False}


def infer_candidate_constant(cases: Iterable[dict]):
    """Fit a tiny transparent envelope C ~= c * gamma^p / sqrt(alpha).
    Candidate discovery only; never theorem evidence.
    """
    good=[]
    for c in cases:
        _validate_case(c)
        if all(bool(c['premises'].get(p,False)) for p in DEFAULT_PREMISES): good.append(c)
    if not good: return {'available':False,'reason':'no cases satisfying all declared premises'}
    candidates=[]
    for p in (0.0,0.5,1.0,1.5,2.0):
        scales=[(float(c['shape_ratio'])**p)/math.sqrt(float(c['alpha_lower'])) for c in good]
        coeff=max(float(c['ratio_upper'])/s for c,s in zip(good,scales))
        predicted=[coeff*s for s in scales]
        slack=sum((pr-float(c['ratio_upper']))/max(float(c['ratio_upper']),1e-300) for pr,c in zip(predicted,good))/len(good)
        candidates.append({'shape_exponent':p,'coefficient':coeff,'mean_relative_slack':slack,'covers_observed_good_cases':all(pr+1e-15>=float(c['ratio_upper']) for pr,c in zip(predicted,good))})
    best=min(candidates,key=lambda x:(x['mean_relative_slack'],x['shape_exponent']))
    return {'available':True,'model':'C_candidate = coefficient * gamma^p / sqrt(alpha)','best':best,'candidates':candidates,
            'scope':'empirical upper envelope over observed all-premise cases','theorem_evidence':False}


def proof_obligation_dag():
    nodes={
      'residual_representation': {'status':'obligation','depends_on':['galerkin_orthogonality','elementwise_green_identity']},
      'galerkin_orthogonality': {'status':'reviewed-known','depends_on':[]},
      'elementwise_green_identity': {'status':'obligation','depends_on':['edge_orientation_cancellation']},
      'edge_orientation_cancellation': {'status':'candidate-for-exact-kernel','depends_on':[]},
      'quasi_interpolation_local': {'status':'obligation','depends_on':['shape_regular_family']},
      'trace_local': {'status':'obligation','depends_on':['shape_regular_family']},
      'shape_regular_family': {'status':'premise','depends_on':[]},
      'finite_overlap': {'status':'obligation','depends_on':['conforming_mesh']},
      'conforming_mesh': {'status':'premise','depends_on':[]},
      'coercivity': {'status':'interval-capable','depends_on':['uniform_ellipticity']},
      'uniform_ellipticity': {'status':'premise','depends_on':[]},
      'estimator_definition': {'status':'implemented','depends_on':[]},
      'reliability_theorem': {'status':'obligation','depends_on':['residual_representation','quasi_interpolation_local','trace_local','finite_overlap','coercivity','estimator_definition']},
    }
    closed={'implemented','reviewed-known','interval-capable','premise'}
    unresolved=sorted(k for k,v in nodes.items() if v['status'] not in closed)
    return {'theorem_id':RELIABILITY_THEOREM_ID,'nodes':nodes,'unresolved':unresolved,
            'reliability_promotable':False,'formal_evidence':False}



def certified_reference_observation():
    """Produce one real certified continuum/estimator observation using the existing
    manufactured reference-triangle bubble benchmark. The ratio uses an energy-error
    upper bound divided by an estimator lower bound, so it is conservative for this run.
    """
    from cace_studio.core.module import ExecutionContext
    from cace_studio.modules.fem_nd import SimplexMeshND,P1SimplexSpaceND,LinearSolverND
    from cace_studio.modules.fem_cert import CertifiedPoissonAssembly
    from cace_studio.modules.fem_cert2d import (CertifiedTriangleGeometry2D,CertifiedShapeRegularity2D,
        BubblePoissonProblem2D,BubbleContinuumEnergyCertificate2D,BubbleResidualEstimatorCertificate2D)
    ctx=ExecutionContext(run_id='v076-certified-anchor')
    def run(m, inputs=None, params=None):
        inputs=inputs or {}; pp=m.resolved_params(params or {}); m.validate(inputs,pp); return m.execute(inputs,pp,ctx)
    mesh=run(SimplexMeshND(),params={'vertices':'[[0,0],[1,0],[0,1],[0.3333333333333333,0.3333333333333333]]','elements':'[[0,1,3],[1,2,3],[2,0,3]]'})['mesh']
    space=run(P1SimplexSpaceND(),{'mesh':mesh})['space']
    geo=run(CertifiedTriangleGeometry2D(),{'mesh':mesh})['geometry_certificate']
    shape=run(CertifiedShapeRegularity2D(),{'geometry_certificate':geo},{'max_ratio':20.0})['shape_certificate']
    problem=run(BubblePoissonProblem2D())['problem']
    system=run(CertifiedPoissonAssembly(),{'mesh':mesh,'space':space},{'diffusion':'1.0','source_constant':0.0,'source_linear':'[2.0,2.0]'})['system']
    sol=run(LinearSolverND(),{'system':system})['solution']
    cont=run(BubbleContinuumEnergyCertificate2D(),{'mesh':mesh,'solution':sol,'problem':problem,'geometry_certificate':geo})['continuum_certificate']
    est=run(BubbleResidualEstimatorCertificate2D(),{'mesh':mesh,'solution':sol,'geometry_certificate':geo})['estimator_certificate']
    ratio=float(cont['energy_error_interval'][1])/float(est['eta_interval'][0])
    return {'case_id':'certified-reference-bubble','ratio_upper':ratio,
            'shape_ratio':float(shape['max_shape_ratio_interval'][1]),'alpha_lower':1.0,
            'premises':{p:True for p in DEFAULT_PREMISES},'evidence_scope':'certified-manufactured-run',
            'energy_error_interval':cont['energy_error_interval'],'eta_interval':est['eta_interval'],
            'note':'existing v0.6 manufactured-solution continuum and estimator certificates'}

def default_discovery_corpus():
    """Deterministic mixed corpus for exercising discovery machinery.
    'certified-observation' rows may come from certified runs; 'synthetic-stress' rows are NOT PDE evidence.
    """
    rows=[certified_reference_observation()]
    # Conservative deterministic observations consistent with bounded behavior under all premises.
    for g in (2.0,4.0,8.0,12.0):
        for a in (1.0,0.5,0.25):
            ratio=0.42*(1+0.045*g)/math.sqrt(a)
            rows.append({'case_id':f'obs-g{g:g}-a{a:g}','ratio_upper':ratio,'shape_ratio':g,'alpha_lower':a,
                         'premises':{p:True for p in DEFAULT_PREMISES},'evidence_scope':'synthetic-stress',
                         'note':'deterministic hypothesis-landscape fixture; not continuum evidence'})
    # Deliberate assumption-removal stress fixtures.
    base={p:True for p in DEFAULT_PREMISES}
    penalties={'conforming_mesh':8.0,'shape_regular_family':6.0,'uniform_ellipticity':7.0,'residual_term':10.0,'jump_term':12.0,'homogeneous_dirichlet':5.0}
    for i,(p,penalty) in enumerate(penalties.items()):
        q=dict(base); q[p]=False
        rows.append({'case_id':f'ablate-{p}','ratio_upper':penalty,'shape_ratio':10.0,'alpha_lower':0.5,'premises':q,
                     'evidence_scope':'synthetic-stress','note':'assumption-ablation fixture only'})
    return rows


def reliability_discovery_campaign(cases=None, threshold: float=4.0):
    cases=list(default_discovery_corpus() if cases is None else cases)
    for c in cases: _validate_case(c)
    ablation=premise_ablation(cases,threshold)
    bad=[minimize_counterexample(c,threshold) for c in cases if float(c['ratio_upper'])>threshold]
    inferred=infer_candidate_constant(cases)
    dag=proof_obligation_dag()
    result={
      'release':'0.76.0','theorem_id':RELIABILITY_THEOREM_ID,'case_count':len(cases),
      'evidence_scopes':sorted(set(c['evidence_scope'] for c in cases)),
      'ablation':ablation,'counterexample_candidates':bad,'candidate_constant':inferred,
      'proof_obligation_dag':dag,
      'promotion_guard':{
        'reliability_theorem_formally_verified':False,
        'numerical_campaign_can_promote_formal_theorem':False,
        'synthetic_stress_cases_are_theorem_evidence':False,
        'reason':'analytic proof obligations remain unresolved'
      },
      'pass': (not dag['reliability_promotable']) and inferred.get('available',False) and len(bad)>=1,
    }
    result['sha256']=_canonical_hash({k:v for k,v in result.items() if k!='sha256'})
    return result


class ReliabilityDiscoveryV76(ResultModule):
    fn=staticmethod(reliability_discovery_campaign)
    module_id='fem76.reliability_discovery'
    label='Reliability Theorem Discovery Engine'
    version='0.76.0'
    description='Premise ablation, counterexample-candidate minimization, candidate reliability-constant inference, and analytic proof-obligation DAG with a hard non-promotion guard.'
    evidence_kind=EvidenceKind.NUMERICAL
    metadata=ModuleMetadata(module_id,label,version,'Theorem Discovery',description,Maturity.EXPERIMENTAL,
        assumptions=('Discovery output is conjecture/falsification guidance, not a proof of the mesh-uniform theorem.',))
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True,
        limitations=['Default corpus contains synthetic stress fixtures that are not PDE evidence.','Candidate constants cover only observed cases.','General 2D reliability theorem remains unresolved.'])


def register_fem_v076(registry):
    registry.register(ReliabilityDiscoveryV76)

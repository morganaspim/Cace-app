from cace_studio.modules.fem_v076 import *
from cace_studio.core.module import ExecutionContext
from cace_studio.core.registry import ModuleRegistry
from cace_studio.modules import register_all


def test_discovery_campaign_refuses_theorem_promotion():
    r=reliability_discovery_campaign()
    assert r['pass']
    assert r['case_count'] >= 18
    assert r['promotion_guard']['reliability_theorem_formally_verified'] is False
    assert r['promotion_guard']['synthetic_stress_cases_are_theorem_evidence'] is False
    assert 'reliability_theorem' in r['proof_obligation_dag']['unresolved']


def test_premise_ablation_flags_jump_and_conformity_stress():
    rows={r['premise']:r for r in premise_ablation(default_discovery_corpus())}
    assert rows['jump_term']['empirical_warning']
    assert rows['conforming_mesh']['empirical_warning']
    assert rows['jump_term']['max_ratio_off'] > rows['jump_term']['max_ratio_on']


def test_candidate_constant_is_only_empirical_envelope():
    x=infer_candidate_constant(default_discovery_corpus())
    assert x['available'] and x['best']['covers_observed_good_cases']
    assert x['theorem_evidence'] is False
    assert x['scope'].startswith('empirical')


def test_counterexample_minimization_does_not_invent_counterfactuals():
    c=[x for x in default_discovery_corpus() if x['case_id']=='ablate-jump_term'][0]
    m=minimize_counterexample(c)
    assert m['is_counterexample_candidate']
    assert m['false_premises']==['jump_term']
    assert m['formal_counterexample'] is False


def test_v076_module_and_registry():
    mod=ReliabilityDiscoveryV76(); p=mod.resolved_params({}); out=mod.execute({},p,ExecutionContext(run_id='v076'))
    rec=mod.verify({},p,out,ExecutionContext(run_id='v076'))[0]
    assert rec.state.value=='pass'
    reg=ModuleRegistry(); register_all(reg)
    assert reg.contains('fem76.reliability_discovery')

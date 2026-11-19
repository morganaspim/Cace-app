"""Bounded analytical research and pure contract checks, not a production router.
No network, model inference, credential access, execution, or self-promotion.
Device/model scenarios are assumptions; host observations are separately recorded.
"""
from dataclasses import dataclass, asdict
from fractions import Fraction
from itertools import product
import hashlib
import json
import math
from pathlib import Path
import re

GIB = 1024**3
SHA = re.compile(r'^[0-9a-f]{64}$')


def integer(value, name, low=1, high=10**15):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(name + ': invalid integer')
    return value


def finite(value, name, low=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + ': finite real required')
    if not math.isfinite(value) or value < low:
        raise ValueError(name + ': out of range')
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class DenseModel:
    name: str
    parameters: int
    layers: int
    kv_heads: int
    head_dim: int
    weight_bits: int
    kv_bytes: int = 2
    weight_overhead_percent: int = 10

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name or len(self.name) > 100:
            raise ValueError('invalid model label')
        for k in ('parameters', 'layers', 'kv_heads', 'head_dim', 'kv_bytes'):
            integer(getattr(self, k), k)
        if type(self.weight_bits) is not int or self.weight_bits not in (4, 8, 16):
            raise ValueError('weight_bits must be 4, 8 or 16')
        integer(self.weight_overhead_percent, 'weight overhead', 0, 100)

    def weights(self):
        return math.ceil(Fraction(self.parameters * self.weight_bits *
                                  (100 + self.weight_overhead_percent), 800))

    def kv(self, context, batch=1):
        integer(context, 'context', 1, 10**7)
        integer(batch, 'batch', 1, 1024)
        return 2*self.layers*self.kv_heads*self.head_dim*context*batch*self.kv_bytes


def cost(model, context, batch, bandwidth_bytes_s, resident_fraction=0):
    """Storage-to-compute traffic lower bound, conditional on declared spill.
    resident_fraction is weights retained above the storage boundary, not GPU
    residency. Full RAM caching removes repeated disk spill. Compute, activation
    traffic, decompression and communication are omitted from this LOWER bound.
    """
    finite(bandwidth_bytes_s, 'bandwidth', 1)
    finite(resident_fraction, 'resident fraction')
    if resident_fraction > 1:
        raise ValueError('resident fraction > 1')
    weights = model.weights()
    cache = model.kv(context, batch)
    spill = (1-resident_fraction)*weights
    step = spill/bandwidth_bytes_s
    return {'weight_bytes': weights, 'kv_bytes': cache,
            'resident_min_bytes': weights+cache,
            'spilled_weight_bytes_per_decode_step': spill,
            'decode_step_io_lower_bound_seconds': step,
            'per_sequence_io_latency_lower_bound_seconds': step,
            'aggregate_token_rate_io_upper_bound': batch/step if step else None,
            'storage_if_original_fp16_retained_bytes': 2*model.parameters+weights,
            'status': 'analytical_assumption_not_inference_measurement',
            'omitted_costs': ['workspace', 'activations', 'prefill', 'compute',
                              'decompression', 'filesystem_overhead', 'network', 'energy']}


def simplex_cost(costs, weights):
    """UI ranking of already eligible, dimensionless normalized cost vectors."""
    if not costs or len(costs) != len(weights):
        raise ValueError('nonempty equal-length vectors required')
    for v in list(costs)+list(weights):
        finite(v, 'coordinate')
        if v > 1:
            raise ValueError('normalized coordinates required')
    if abs(math.fsum(weights)-1) > 1e-12:
        raise ValueError('weights must sum to one')
    return math.fsum(c*w for c, w in zip(costs, weights))


def admission(task, capability, grant, now):
    """Pure host-side policy fixture; not authentication or a job dispatcher.
    Inputs must be supplied by the real canonical resolver, registry and lease
    service before this can become production. It grants no execution authority.
    """
    finite(now, 'now')
    required_task = {'project', 'tool', 'privacy', 'memory_bytes', 'deadline', 'mode'}
    required_cap = {'project', 'tool', 'privacy', 'free_memory_bytes', 'observed_at',
                    'ttl_seconds', 'enabled', 'observed', 'simulated', 'isolated'}
    if set(task) != required_task or set(capability) != required_cap:
        raise ValueError('strict schema mismatch')
    if set(grant) != {'project', 'tools', 'expires_at'}:
        raise ValueError('grant schema mismatch')
    for label in (task['project'], capability['project'], grant['project'], task['tool'], capability['tool']):
        if not isinstance(label, str) or not label.strip() or len(label)>200:
            raise ValueError('nonempty bounded project/tool identity required')
    for k in ('enabled', 'observed', 'simulated', 'isolated'):
        if type(capability[k]) is not bool:
            raise ValueError('capability flags must be bool')
    for k in ('memory_bytes',):
        integer(task[k], k, 0)
    integer(capability['free_memory_bytes'], 'free memory', 0)
    finite(task['deadline'], 'deadline'); finite(grant['expires_at'], 'grant expiry')
    finite(capability['observed_at'], 'observation'); finite(capability['ttl_seconds'], 'ttl', 1)
    if task['privacy'] not in {'public', 'private'} or task['mode'] not in {'experiment', 'inference', 'proof'}:
        raise ValueError('unknown task mode/privacy')
    if not isinstance(capability['privacy'], list) or not set(capability['privacy']) <= {'public', 'private'}:
        raise ValueError('unknown privacy capability')
    if not isinstance(grant['tools'], list) or any(not isinstance(x, str) for x in grant['tools']):
        raise ValueError('invalid grant tools')
    reasons = []
    if not capability['enabled'] or not capability['observed']:
        reasons.append('capability_not_enabled_and_observed')
    if capability['simulated']:
        reasons.append('simulated_resource_is_not_executable_capacity')
    if not capability['isolated']:
        reasons.append('isolation_not_established')
    age = now-capability['observed_at']
    if age < 0 or age > capability['ttl_seconds']:
        reasons.append('capability_stale_or_future')
    if task['project'] != capability['project'] or task['project'] != grant['project']:
        reasons.append('project_scope_mismatch')
    if task['tool'] != capability['tool'] or task['tool'] not in grant['tools']:
        reasons.append('tool_not_granted')
    if task['privacy'] not in capability['privacy']:
        reasons.append('privacy_not_supported')
    if task['memory_bytes'] > capability['free_memory_bytes']:
        reasons.append('memory_budget_exceeded')
    if now >= task['deadline'] or now >= grant['expires_at']:
        reasons.append('deadline_or_grant_expired')
    return {'eligible_for_host_admission_review': not reasons, 'reasons': reasons,
            'execution_dispatched': False, 'promotion_authority': False}


def review_rsi(record, host_authenticated=False):
    """Check shape/lineage for a research review. Never promotes a candidate.
    Authentication, fresh-set custody, metric evaluation and separate approval
    must be real external services; these booleans/fixtures are not attestation.
    """
    if type(host_authenticated) is not bool:
        raise ValueError('host authentication flag must be bool')
    fields = {'candidate_sha256', 'evaluated_sha256', 'baseline_sha256',
              'train_content_hashes', 'holdout_content_hashes', 'used_holdout_hashes',
              'evidence_kind', 'baseline_score', 'candidate_score', 'regressions',
              'budget_pass', 'rollback_sha256'}
    if not isinstance(record, dict) or set(record) != fields:
        raise ValueError('RSI schema mismatch')
    for field in ('candidate_sha256', 'evaluated_sha256', 'baseline_sha256', 'rollback_sha256'):
        if not isinstance(record[field], str) or not SHA.fullmatch(record[field]):
            raise ValueError('invalid artifact digest')
    for field in ('train_content_hashes', 'holdout_content_hashes', 'used_holdout_hashes'):
        v=record[field]
        if not isinstance(v, list) or len(v)>10000:
            raise ValueError('invalid case hashes')
        if any(not isinstance(x, str) or not SHA.fullmatch(x) for x in v):
            raise ValueError('invalid case digest')
        if len(v)!=len(set(v)):
            raise ValueError('duplicate case digest')
    finite(record['baseline_score'], 'baseline score')
    finite(record['candidate_score'], 'candidate score')
    if record['baseline_score']>1 or record['candidate_score']>1:
        raise ValueError('normalized scores required')
    integer(record['regressions'], 'regressions', 0)
    if type(record['budget_pass']) is not bool:
        raise ValueError('budget_pass must be bool')
    if record['evidence_kind'] not in {'simulated', 'measured', 'reported'}:
        raise ValueError('unknown evidence class')
    reasons=[]
    if not host_authenticated:
        reasons.append('independent_evaluator_not_authenticated')
    if record['candidate_sha256'] != record['evaluated_sha256']:
        reasons.append('candidate_changed_after_evaluation')
    hold=set(record['holdout_content_hashes'])
    if not hold or not record['train_content_hashes']:
        reasons.append('missing_training_or_holdout')
    if hold & set(record['train_content_hashes']):
        reasons.append('training_holdout_content_overlap')
    if hold & set(record['used_holdout_hashes']):
        reasons.append('holdout_not_fresh')
    if record['evidence_kind']!='measured':
        reasons.append('simulation_or_report_is_not_observed_gain')
    if record['candidate_score'] <= record['baseline_score']:
        reasons.append('no_scoped_improvement')
    if record['regressions'] or not record['budget_pass']:
        reasons.append('regression_or_budget_failure')
    if record['rollback_sha256'] != record['baseline_sha256']:
        reasons.append('rollback_does_not_bind_baseline')
    return {'status': 'blocked' if reasons else 'ready_for_independent_review',
            'reasons': reasons, 'promotion_authority': False,
            'limitations': 'Synthetic gate: no statistical power, scorer truth or evaluator independence is established.'}


def run_sweep():
    configs=[('toy-1B',10**9,24,4,64),('toy-3B',3*10**9,28,8,128),
             ('toy-8B',8*10**9,32,8,128),('toy-70B',70*10**9,80,8,128)]
    rows=[]
    for conf, bits, ctx, batch, bw in product(configs,(4,8,16),(2048,8192,32768),(1,8),(0.5,2,8,32)):
        model=DenseModel(*conf,bits)
        rows.append({'model':asdict(model),'context':ctx,'batch':batch,'bandwidth_GBps_assumed':bw,
                     'calculation':cost(model,ctx,batch,bw*10**9)})
    illustrative=cost(DenseModel(*configs[-1],4),8192,1,2*10**9)
    return {'schema':'merlin-lightweight-architecture-study/1','cases':rows,
            'case_count':len(rows),'case_digest':digest(rows),
            'illustrative_dense_70b_q4':illustrative,
            'hardware_performance_measured':False,'inference_executed':False,
            'promotion_authority':False}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args=p.parse_args()
    result=run_sweep()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},sort_keys=True))

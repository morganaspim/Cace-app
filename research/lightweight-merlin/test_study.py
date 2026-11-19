import unittest
from dataclasses import replace
import math
from study import DenseModel, cost, simplex_cost, admission, review_rsi, run_sweep, digest

M=DenseModel('toy',70*10**9,80,8,128,4)

def fixture():
    t={'project':'synthetic','tool':'simulation','privacy':'public','memory_bytes':100,'deadline':150,'mode':'experiment'}
    c={'project':'synthetic','tool':'simulation','privacy':['public'],'free_memory_bytes':1000,'observed_at':99,'ttl_seconds':20,'enabled':True,'observed':True,'simulated':False,'isolated':True}
    g={'project':'synthetic','tools':['simulation'],'expires_at':140}
    return t,c,g

def rsi():
    return {'candidate_sha256':'a'*64,'evaluated_sha256':'a'*64,'baseline_sha256':'b'*64,
            'train_content_hashes':['c'*64],'holdout_content_hashes':['d'*64],
            'used_holdout_hashes':[],'evidence_kind':'measured','baseline_score':0.5,
            'candidate_score':0.75,'regressions':0,'budget_pass':True,'rollback_sha256':'b'*64}

class CostTests(unittest.TestCase):
    def test_weights(self): self.assertEqual(M.weights(),38500000000)
    def test_kv(self): self.assertEqual(M.kv(8192),2684354560)
    def test_context_scaling(self): self.assertEqual(M.kv(32768),4*M.kv(8192))
    def test_batch_scaling(self): self.assertEqual(M.kv(8192,8),8*M.kv(8192))
    def test_quantization_does_not_shrink_kv(self): self.assertEqual(M.kv(8192),replace(M,weight_bits=16).kv(8192))
    def test_io(self): self.assertEqual(cost(M,8192,1,2e9)['decode_step_io_lower_bound_seconds'],19.25)
    def test_no_spill_no_disk_bound(self): self.assertIsNone(cost(M,8192,1,2e9,1)['aggregate_token_rate_io_upper_bound'])
    def test_batch_not_sequence_latency(self):
        a,b=cost(M,8192,1,2e9),cost(M,8192,8,2e9)
        self.assertEqual(a['per_sequence_io_latency_lower_bound_seconds'],b['per_sequence_io_latency_lower_bound_seconds'])
        self.assertEqual(b['aggregate_token_rate_io_upper_bound'],8*a['aggregate_token_rate_io_upper_bound'])
    def test_io_monotone(self): self.assertLess(cost(M,8192,1,8e9)['decode_step_io_lower_bound_seconds'],cost(M,8192,1,2e9)['decode_step_io_lower_bound_seconds'])
    def test_storage(self): self.assertEqual(cost(M,8192,1,2e9)['storage_if_original_fp16_retained_bytes'],178500000000)
    def test_invalid_numbers(self):
        for bad in (True,False,-1,0,float('nan'),float('inf'),'2'):
            with self.subTest(bad=bad),self.assertRaises(ValueError): cost(M,8192,1,bad)
    def test_invalid_context_batch(self):
        for bad in (True,0,-1,2.5,10**8):
            with self.subTest(bad=bad),self.assertRaises(ValueError): M.kv(bad)
        with self.assertRaises(ValueError): M.kv(5,1025)
    def test_invalid_bits(self):
        for b in (True,3,4.0):
            with self.assertRaises(ValueError): replace(M,weight_bits=b)
    def test_invalid_residency(self):
        for b in (True,-1,1.1,float('nan')):
            with self.assertRaises(ValueError): cost(M,8192,1,2e9,b)
    def test_ranking_convex(self): self.assertAlmostEqual(simplex_cost([0.2,0.8],[0.25,0.75]),0.65)
    def test_ranking_invalid(self):
        for c,w in (([],[]),([1],[0]),([2],[1]),([0],[True]),([0],[float('nan')])):
            with self.assertRaises(ValueError): simplex_cost(c,w)
    def test_sweep_bounded_and_deterministic(self):
        a,b=run_sweep(),run_sweep()
        self.assertEqual(a,b);self.assertEqual(a['case_count'],288)
        self.assertEqual(len(set(digest(x) for x in a['cases'])),288)
        self.assertFalse(a['hardware_performance_measured'])

class AdmissionTests(unittest.TestCase):
    def test_eligible_still_not_dispatched(self):
        t,c,g=fixture();r=admission(t,c,g,100)
        self.assertTrue(r['eligible_for_host_admission_review']);self.assertFalse(r['execution_dispatched']);self.assertFalse(r['promotion_authority'])
    def test_denials(self):
        mutations=[('c','enabled',False),('c','observed',False),('c','simulated',True),('c','isolated',False),('c','observed_at',0),('c','observed_at',101),('c','project','other'),('g','project','other'),('g','tools',[]),('c','tool','other'),('t','privacy','private'),('c','free_memory_bytes',99),('t','deadline',100),('g','expires_at',100)]
        for target,k,v in mutations:
            with self.subTest(target=target,k=k,v=v):
                t,c,g=fixture();{'t':t,'c':c,'g':g}[target][k]=v
                r=admission(t,c,g,100);self.assertFalse(r['eligible_for_host_admission_review']);self.assertFalse(r['promotion_authority'])
    def test_strict_fields(self):
        t,c,g=fixture();t['override_project']='other'
        with self.assertRaises(ValueError): admission(t,c,g,100)
    def test_bool_is_not_memory(self):
        t,c,g=fixture();t['memory_bytes']=True
        with self.assertRaises(ValueError): admission(t,c,g,100)
    def test_unknown_mode(self):
        t,c,g=fixture();t['mode']='self_deploy'
        with self.assertRaises(ValueError): admission(t,c,g,100)
    def test_string_flag(self):
        t,c,g=fixture();c['enabled']='true'
        with self.assertRaises(ValueError): admission(t,c,g,100)
    def test_empty_project_not_a_scope(self):
        t,c,g=fixture();t["project"]=c["project"]=g["project"]=""
        with self.assertRaises(ValueError): admission(t,c,g,100)
    def test_unhashable_case_rejected_as_schema(self):
        x=rsi();x["holdout_content_hashes"]=[{}]
        with self.assertRaises(ValueError): review_rsi(x)
    def test_nan_deadline(self):
        t,c,g=fixture();t['deadline']=float('nan')
        with self.assertRaises(ValueError): admission(t,c,g,100)

class ReviewTests(unittest.TestCase):
    def test_default_blocked(self): self.assertEqual(review_rsi(rsi())['status'],'blocked')
    def test_ready_never_promotes(self):
        x=review_rsi(rsi(),True);self.assertEqual(x['status'],'ready_for_independent_review');self.assertFalse(x['promotion_authority'])
    def test_negative_controls(self):
        mutations=[('evaluated_sha256','f'*64),('train_content_hashes',['d'*64]),('used_holdout_hashes',['d'*64]),('holdout_content_hashes',[]),('train_content_hashes',[]),('evidence_kind','simulated'),('evidence_kind','reported'),('candidate_score',0.5),('regressions',1),('budget_pass',False),('rollback_sha256','e'*64)]
        for k,v in mutations:
            with self.subTest(k=k,v=v):
                x=rsi();x[k]=v;r=review_rsi(x,True)
                self.assertEqual(r['status'],'blocked');self.assertFalse(r['promotion_authority'])
    def test_invalid_digest(self):
        x=rsi();x['candidate_sha256']='wrong'
        with self.assertRaises(ValueError): review_rsi(x)
    def test_unknown_class(self):
        x=rsi();x['evidence_kind']='formally_verified'
        with self.assertRaises(ValueError): review_rsi(x)
    def test_nan_score(self):
        x=rsi();x['candidate_score']=float('nan')
        with self.assertRaises(ValueError): review_rsi(x)
    def test_promotion_flag_in_input(self):
        x=rsi();x['promotion_authority']=True
        with self.assertRaises(ValueError): review_rsi(x)
    def test_duplicate_holdout(self):
        x=rsi();x['holdout_content_hashes']*=2
        with self.assertRaises(ValueError): review_rsi(x)
    def test_bool_score(self):
        x=rsi();x['candidate_score']=True
        with self.assertRaises(ValueError): review_rsi(x)
    def test_string_auth(self):
        with self.assertRaises(ValueError): review_rsi(rsi(),'true')

if __name__=='__main__': unittest.main()

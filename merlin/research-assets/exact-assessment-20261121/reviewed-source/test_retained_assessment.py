"""Local control fixtures only: no model, socket peer, native worker or host operation."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'merlin-release-build/python'))
from merlin.project_registry import MerlinRegistry
from dot_ai_os.private_runtime import PrivateReadOnlyRegistry, PrivateDispatcher
from dot_ai_os.bridge import DotContextBridge
from merlin.hermes_systemd import _properties
from dot_ai_os.local_research import WORKER_LIMITS

spec = importlib.util.spec_from_file_location('assessment_renderer', HERE / 'render_research_episode.py')
renderer = importlib.util.module_from_spec(spec); spec.loader.exec_module(renderer)
NATIVE = renderer.decode((ROOT / 'verification/release-continuation/native-run-44919201279/native-validation-pins.json').read_bytes())
PINS = renderer.expected_host_pins(NATIVE)
HOST_RAW = renderer.render('host', '__FROZEN_RELEASE_PINS__', PINS, 49152)
HOST = types.ModuleType('retained_assessment_host'); exec(compile(HOST_RAW, 'retained_assessment_host', 'exec'), HOST.__dict__)
INPUT_RAW = (HERE / 'retained-inputs.json').read_bytes()
INPUT = HOST.retained_inputs(INPUT_RAW)
OLD = ROOT / 'verification/release-continuation/research-run-44917400072'
NEW = ROOT / 'verification/release-continuation/research-run-44919773657'
CORPUS = {}
for directory in (OLD, NEW):
    for path, row in renderer.decode((directory / 'episode-artifacts.json').read_bytes())['artifacts'].items():
        CORPUS[path] = row['content'].encode()
marker = renderer.decode((NEW / 'format-failure-disposition-ref.json').read_bytes())
CORPUS[marker['logical_path']] = (NEW / 'format-failure-disposition.json').read_bytes()


class FakeProcess:
    """Synthetic process receipts. No candidate source is evaluated in this fixture."""
    def __init__(self, oracle):
        self.oracle = {row['case_id']: row for row in oracle['cases']}
        self.tasks_max = 8
        self.calls = []
        self.hook = None
        self.bad_result = False
    def run(self, raw, *, limits, context, authorize):
        policy = {'program_sha256': PINS['worker_sha256'], 'unit': 'merlin-fixed-' + 'a' * 32 + '.service',
                  'limits': _properties(WORKER_LIMITS, 8), 'tasks_max': self.tasks_max,
                  'isolation': 'systemd_cgroup_v2', 'compute_budget_units_enforced': False}
        if authorize(policy) is not True:
            raise PermissionError('fixture host authorization rejected')
        self.calls.append(raw)
        if self.hook: self.hook(self)
        if authorize(policy) is not True:
            raise PermissionError('fixture host authorization revoked')
        rows = []
        for case in json.loads(raw)['cases']:
            result = copy.deepcopy(self.oracle[case['case_id']]['expected'])
            if self.bad_result: result = {'status': 'error', 'type': 'SyntheticWrongResult'}
            rows.append({'case_id': case['case_id'], 'outcome': result,
                         'inputs_unchanged': True, 'cpu_nanoseconds': 1})
        return {'schema': 'merlin-systemd-process-result/1', 'status': 'completed', 'returncode': 0,
                'program_sha256': PINS['worker_sha256'], 'input_sha256': HOST.sha(raw),
                'kernel_setup': {'uid': 65534, 'program_sha256': PINS['worker_sha256']},
                'stdout': json.dumps({'schema': 'merlin-solver-worker-output/1', 'cases': rows}),
                'qualification': False, 'promotion_authority': False}


class Fixture:
    def __init__(self, case):
        self.tmp = tempfile.TemporaryDirectory(); case.addCleanup(self.tmp.cleanup)
        self.store = MerlinRegistry(Path(self.tmp.name) / 'state')
        self.store.register_project(HOST.PROJECT, 'local control only')
        for path, digest in INPUT['records'].items():
            raw = CORPUS[path]
            assert HOST.sha(raw) == digest
            self.store.put_artifact(HOST.PROJECT, path, raw, 'application/json')
        self.before = HOST.preserved_records(self.store, INPUT)
        HOST.fresh_assessment(self.store)
        refs = {}
        entries = [('retained_inputs_ref', 'retained-inputs.json', INPUT_RAW),
                   ('research_plan_ref', 'research-plan.json', HOST.canonical(INPUT['research_plan'])),
                   ('oracle_ref', 'oracle.json', (NEW / 'oracle.json').read_bytes()),
                   ('source_notes_ref', 'source-notes.json', (NEW / 'source-notes.json').read_bytes()),
                   ('provider_manifest_ref', 'provider-manifest.json', CORPUS[next(p for p in INPUT['records'] if p.endswith('/provider-manifest.json'))]),
                   ('provider_bootstrap_ref', 'provider-bootstrap.json', CORPUS[next(p for p in INPUT['records'] if p.endswith('/provider-bootstrap.json'))])]
        for key, name, raw in entries:
            refs[key] = HOST.put_once(self.store, HOST.HOST_PREFIX + name, raw)
        invocation = {'request_id': '11111111-1111-1111-1111-111111111111', 'run_id': 1, 'run_attempt': 1, 'workflow_commit': '1' * 40}
        admission = copy.deepcopy(INPUT['admission_static'])
        admission.update(invocation=invocation, host_source_sha256=HOST.sha(HOST_RAW),
                         artifact_refs=list(refs.values()), root_decision_sha256=INPUT['root_decision_sha256'])
        ref = HOST.put_once(self.store, HOST.HOST_PREFIX + 'admission.json', HOST.canonical(admission))
        self.cap = dict(source_commit=PINS['source_commit'], session_id=HOST.SESSION, invocation=invocation,
                        host_source_sha256=HOST.sha(HOST_RAW), admission_ref=ref,
                        admitted_refs=list(refs.values()) + [ref], **refs)
        self.allowed = True
        self.process = FakeProcess(json.loads((NEW / 'oracle.json').read_bytes()))
        self.results = {}
    def check(self):
        if not self.allowed: raise PermissionError('fixture revoked')
    def step(self, phase, *, reader=None):
        result = HOST.execute_phase(reader or self.store, self.cap, phase,
                                    None if phase == 'replay' else self.process, None, self.check)
        self.results[phase] = result
        return result
    def complete(self):
        self.step('selection'); return self.step('final')
    def current_alias(self, ref, digest):
        with sqlite3.connect(self.store.db_path) as db:
            db.execute('UPDATE project_artifacts SET digest=? WHERE project_id=? AND logical_path=?',
                       (digest, HOST.PROJECT, ref['logical_path']))
    def private_call(self, source_root, tool, arguments):
        bridge = DotContextBridge(PrivateReadOnlyRegistry(self.store.root), project_id=HOST.PROJECT,
                                  namespaces=['merlin', 'expert-robot'])
        dispatcher = PrivateDispatcher(bridge, grants={1000: {'principal': 'local-runner-opc',
                                      'tools': ['context_fetch', 'session_handoff']}})
        reply = dispatcher.call(1000, {'schema': 'merlin-private-call/1', 'request_id': 'fixture-read',
                                      'tool': tool, 'arguments': arguments})
        if reply.get('ok') is not True: raise RuntimeError(str(reply))
        return {'caller_uid': 1000, 'server_uid': 982, 'transport': 'SO_PEERCRED Unix socket',
                'tool': tool, 'arguments': arguments, 'result': reply['result'],
                'result_sha256': HOST.sha(HOST.canonical(reply['result']))}


class RetainedAssessmentTests(unittest.TestCase):
    def test_actual_39_data_bytes_typed_frame_and_proposals(self):
        f = Fixture(self)
        self.assertEqual(39, len(f.before['records']))
        self.assertEqual(INPUT['records_sha256'], HOST.sha(HOST.canonical(INPUT['records'])))
        programs, rejected = HOST.retained_proposals(f.store, INPUT)
        self.assertEqual(programs['baseline'], programs['coder_a'])
        self.assertEqual(1281, len(programs['coder_a'].encode()))
        self.assertEqual('length', rejected['finish_reason'])
        self.assertIsNone(rejected['candidate']); self.assertIsNone(rejected['score'])
        self.assertFalse(rejected['executed'])
        self.assertEqual(0, len(f.process.calls))

    def test_full_core_selection_final_readonly_replay_and_actual_private_interfaces(self):
        f = Fixture(self); selection = f.step('selection')
        self.assertEqual('selection_recorded', selection['status'])
        self.assertIsNone(selection['report_ref']); self.assertIsNone(selection['handoff_ref'])
        final = f.step('final')
        before_db = f.store.db_path.read_bytes(); before_rows = HOST.inventory_rows(f.store)
        replay = f.step('replay', reader=PrivateReadOnlyRegistry(f.store.root))
        self.assertEqual(before_db, f.store.db_path.read_bytes()); self.assertEqual(before_rows, HOST.inventory_rows(f.store))
        self.assertEqual({k:v for k,v in final.items() if k != 'effects_this_call'}, {k:v for k,v in replay.items() if k != 'effects_this_call'})
        self.assertEqual(4, len(f.process.calls)); self.assertEqual(0, replay['effects_this_call']['native_process_launches'])
        report = json.loads(HOST.checked_ref(f.store, final['report_ref']))
        self.assertEqual('retain_baseline', report['recommendation']); self.assertFalse(report['proposal_a']['distinct_improvement'])
        self.assertLessEqual(len(HOST.canonical(report)), 16000)
        for partition, count in [('selection',12), ('final',6)]:
            self.assertEqual({k:{'cases':count,'passed':count} for k in ('baseline','coder_a')}, report['measurements'][partition])
        self.assertEqual(f.before, HOST.preserved_records(f.store, INPUT))
        with patch.object(HOST, 'private_call', f.private_call):
            reads = HOST.report_reads(f.store, Path('.'), final)
        self.assertEqual(HOST.checked_ref(f.store, final['report_ref']), reads['context_fetch']['result']['text'].encode())
        self.assertIsNone(reads['context_fetch']['result']['next_start_byte'])
        self.assertEqual([final['report_source_ref']], reads['session_handoff']['result']['handoff']['source_refs'])

    def test_only_two_fixed_programs_partitions_and_no_b_worker(self):
        f = Fixture(self); f.complete()
        self.assertEqual([12,12,6,6], [len(json.loads(raw)['cases']) for raw in f.process.calls])
        self.assertEqual({HOST.BASELINE_SHA}, {HOST.sha(json.loads(raw)['program'].encode()) for raw in f.process.calls})
        self.assertFalse(any('/coder_b/' in name for name in HOST.inventory_rows(f.store) if HOST.SESSION in name))
        self.assertFalse(any('http' in name for name in HOST.execute_phase.__code__.co_names))

    def test_rejected_b_cannot_be_reinterpreted_as_candidate(self):
        f = Fixture(self)
        _, rejected = HOST.retained_proposals(f.store, INPUT)
        self.assertEqual('rejected_output_truncated', rejected['status']); self.assertIsNone(rejected['score'])
        altered = copy.deepcopy(INPUT); altered['b_observation_ref'] = INPUT['a_result_ref']
        with self.assertRaises((KeyError, ValueError)): HOST.retained_proposals(f.store, altered)
        self.assertEqual(0, len(f.process.calls))

    def test_same_assessment_retry_is_fenced_before_effect(self):
        f = Fixture(self)
        with self.assertRaises(ValueError): HOST.fresh_assessment(f.store)
        f.step('selection')
        with self.assertRaises(ValueError): f.step('selection')
        self.assertEqual(2, len(f.process.calls))

    def test_final_before_selection_and_replay_before_final_reject(self):
        f = Fixture(self)
        for phase in ('final','replay'):
            with self.subTest(phase=phase), self.assertRaises(ValueError): f.step(phase)
        self.assertEqual(0, len(f.process.calls))

    def test_interrupted_effect_intent_fences_fresh_process_replay(self):
        f = Fixture(self)
        def interrupt(_): raise SystemExit('synthetic interruption after launch')
        f.process.hook = interrupt
        with self.assertRaises(SystemExit): f.step('selection')
        f.process.hook = None
        state = HOST.branch_session(f.store, f.cap, f.check).status()
        self.assertEqual('selection', state['reconciliation_required'])
        with self.assertRaises(ValueError): f.step('selection')
        self.assertEqual(1, len(f.process.calls)); self.assertEqual(f.before, HOST.preserved_records(f.store, INPUT))

    def test_interruption_after_receipt_preserves_receipt_and_never_reexecutes(self):
        f = Fixture(self); original = f.store.put_artifact
        def interrupted(project, path, raw, *args, **kwargs):
            value = original(project, path, raw, *args, **kwargs)
            if path == HOST.SOLVER_PREFIX + 'selection/baseline/process.json': raise RuntimeError('synthetic post-receipt interruption')
            return value
        with patch.object(f.store,'put_artifact',interrupted), self.assertRaises(RuntimeError): f.step('selection')
        ref = f.store.artifact_ref(HOST.PROJECT, HOST.SOLVER_PREFIX + 'selection/baseline/process.json')
        self.assertEqual('completed', json.loads(HOST.checked_ref(f.store, ref))['status'])
        with self.assertRaises(ValueError): f.step('selection')
        self.assertEqual(1,len(f.process.calls))

    def test_revocation_between_workers_retains_partial_evidence_and_fences_retry(self):
        f = Fixture(self); original = f.store.put_artifact
        def revoke(project,path,raw,*args,**kwargs):
            value=original(project,path,raw,*args,**kwargs)
            if path.endswith('/selection/baseline/process.json'): f.allowed=False
            return value
        with patch.object(f.store,'put_artifact',revoke), self.assertRaises(PermissionError): f.step('selection')
        f.allowed=True
        with self.assertRaises(ValueError): f.step('selection')
        self.assertEqual(1,len(f.process.calls))

    def test_historical_blob_tamper_blocks_before_worker(self):
        f=Fixture(self); ref=INPUT['a_result_ref']; path=f.store.blobs/ref['sha256'][:2]/ref['sha256'][2:]
        path.write_bytes(b'tampered')
        with self.assertRaises((RuntimeError,ValueError)): f.step('selection')
        self.assertEqual([],f.process.calls)

    def test_historical_alias_and_extra_record_block_before_worker(self):
        for kind in ('alias','extra','version'):
            with self.subTest(kind=kind):
                f=Fixture(self); ref=INPUT['a_result_ref']
                if kind=='alias': f.current_alias(ref,INPUT['b_observation_ref']['sha256'])
                elif kind=='extra': f.store.put_artifact(HOST.PROJECT,'branch-research/'+INPUT['generation_sessions'][0]+'/unexpected.json',b'{}')
                else: f.store.put_artifact(HOST.PROJECT,ref['logical_path'],b'{}')
                with self.assertRaises((ValueError,RuntimeError)): f.step('selection')
                self.assertEqual([],f.process.calls)

    def test_current_admission_alias_revocation_blocks_before_worker(self):
        f=Fixture(self); f.current_alias(f.cap['admission_ref'],INPUT['a_result_ref']['sha256'])
        with self.assertRaises(ValueError): f.step('selection')
        self.assertEqual([],f.process.calls)

    def test_retained_data_tamper_fails_closed(self):
        for raw in (INPUT_RAW+b' ',INPUT_RAW.replace(b'length',b'xxxxxx',1)):
            with self.subTest(length=len(raw)),self.assertRaises(ValueError):HOST.retained_inputs(raw)

    def test_native_policy_strict_tasks_and_fixed_limits(self):
        policy={'program_sha256':PINS['worker_sha256'],'unit':'merlin-fixed-'+'a'*32+'.service',
                'limits':_properties(WORKER_LIMITS,8),'tasks_max':8,'isolation':'systemd_cgroup_v2','compute_budget_units_enforced':False}
        self.assertTrue(HOST.native_policy_allowed(policy))
        for key,value in [('tasks_max',True),('tasks_max',32),('program_sha256','0'*64),('unit','arbitrary.service')]:
            bad=copy.deepcopy(policy);bad[key]=value
            with self.subTest(key=key,value=value):self.assertFalse(HOST.native_policy_allowed(bad))
        f=Fixture(self);f.process.tasks_max=32
        with self.assertRaises(PermissionError):f.step('selection')
        self.assertEqual([],f.process.calls)

    def test_failed_reference_is_retained_and_blocks_recommendation(self):
        f=Fixture(self);f.process.bad_result=True; final=f.complete()
        report=json.loads(HOST.checked_ref(f.store,final['report_ref']))
        self.assertEqual('block_release_reference_failed',report['recommendation'])
        self.assertEqual(4,len(f.process.calls))
        self.assertEqual(0,report['measurements']['selection']['baseline']['passed'])

    def test_report_byte_ceiling_before_context_publication(self):
        f=Fixture(self);f.step('selection')
        m={'selection':f.results['selection']['measurement_refs']['selection']};o=f.results['selection']['observation_refs']
        data=copy.deepcopy(INPUT);data['report_static']['limits']=['x'*17000]
        with self.assertRaises(ValueError):HOST.publish_report(f.store,f.cap,data,{},m,o,f.check)
        self.assertFalse(any(x.startswith(HOST.report_context_base()) for x in HOST.inventory_rows(f.store)))

    def test_report_and_handoff_tamper_reject_readonly_replay(self):
        f=Fixture(self);final=f.complete(); f.current_alias(final['report_source_ref'],INPUT['a_result_ref']['sha256'])
        with self.assertRaises(ValueError):f.step('replay',reader=PrivateReadOnlyRegistry(f.store.root))
        self.assertEqual(4,len(f.process.calls))

    def test_private_full_read_rejects_truncated_or_changed_result(self):
        f=Fixture(self); final=f.complete()
        def truncated(source_root,tool,arguments):
            result=f.private_call(source_root,tool,arguments)
            if tool=='context_fetch': result['result']['next_start_byte']=1
            return result
        with patch.object(HOST,'private_call',truncated), self.assertRaises(ValueError):HOST.report_reads(f.store,Path('.'),final)

    def test_preserved_scope_and_cleanup_keep_original_error(self):
        f=Fixture(self); out=Path(f.tmp.name)
        with patch.object(HOST,'preserved_records',side_effect=ValueError('secondary')), patch.object(HOST,'repair_new_objects',return_value={}),patch.object(HOST,'export_episode',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'original'):
                try: raise RuntimeError('original')
                finally: HOST.finish_assessment(f.store,{},None,out,INPUT)
        errors=json.loads((out/'cleanup-errors.json').read_bytes())
        self.assertEqual('original',errors['original_error']['message']);self.assertIn('preservation',errors['cleanup_errors'])

    def test_fixed_branch_custody_scope_excludes_other_sessions(self):
        f=Fixture(self); before=HOST.inventory_rows(f.store)
        f.store.put_artifact(HOST.PROJECT,'branch-research/unrelated/plan.json',b'{}')
        with self.assertRaisesRegex(ValueError,'write scope'):
            HOST.repair_new_objects(f.store,before,types.SimpleNamespace(pw_uid=os.geteuid(),pw_gid=os.getegid()))

    def test_rendered_source_bounds_python39_and_exact_ast(self):
        readable=renderer.template('host').replace('__FROZEN_RELEASE_PINS__',repr(renderer.decode(renderer.canonical(PINS)))).encode()
        self.assertEqual(ast.dump(ast.parse(readable,feature_version=(3,9)),include_attributes=False),
                         ast.dump(ast.parse(HOST_RAW,feature_version=(3,9)),include_attributes=False))
        self.assertLessEqual(len(HOST_RAW),49152)
        self.assertLessEqual(len(renderer.privileged_program(HOST_RAW,HOST.sha(HOST_RAW),'\x01'*4096).encode()),98304)
        self.assertLessEqual(len(INPUT_RAW),32000)
        for path in ('ops/merlin_dot/run_research_episode.py.in','render_research_episode.py'):
            ast.parse((HERE/path).read_bytes(),feature_version=(3,9))


    def test_actual_native_package_four_assets_and_fixture_only_finalization(self):
        import base64
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); actual=ROOT/'verification/release-continuation/native-run-44919201279'
            args=types.SimpleNamespace(native_pins=actual/'native-validation-pins.json',
                native_prepared=ROOT/'oci-validation-release/prepared-20261121-response-format',
                native_artifact=actual/'artifact.zip',native_review=actual/'independent-review-02.json',
                oracle=NEW/'oracle.json',notes=NEW/'source-notes.json',retained_inputs=HERE/'retained-inputs.json',output=root/'assets')
            record=renderer.prepare_assets(args)
            self.assertEqual({'host','oracle','notes','retained'},set(record['assets']))
            fixture_readbacks={}
            for name,row in record['assets'].items():
                raw=(root/'assets'/row['file']).read_bytes();path=root/(name+'-synthetic-readback.json')
                path.write_bytes(renderer.canonical({'encoding':'base64','size':len(raw),'sha':renderer.git(raw),
                    'content':base64.b64encode(raw).decode(),'fixture_only':True}))
                fixture_readbacks[name+'_readback']=path
            final=types.SimpleNamespace(assets=root/'assets',output=root/'controller',**fixture_readbacks)
            proposal=renderer.finalize_controller(final)
            self.assertEqual(record['assets']['retained']['sha256'],proposal['assets']['retained']['sha256'])
            self.assertFalse(proposal['actual_host_acceptance']);self.assertFalse(proposal['publication'])
            self.assertLessEqual(proposal['privileged_program_worst_path_bytes'],98304)
            text=(root/'controller/merlin-research-episode.yml').read_text()
            self.assertIn("q['operation']!='assess_retained_responses'",text)
            self.assertIn('timeout-minutes: 10',text)
            code=text.split("python3 - <<'PY'\n",1)[1].split('          PY',1)[0]
            ast.parse('\n'.join(line[10:] for line in code.splitlines()),feature_version=(3,9))
            ast.parse((root/'controller/run_research_episode.py').read_bytes(),feature_version=(3,9))
            (root/'retained-synthetic-readback.json').write_bytes(renderer.canonical({'encoding':'base64','size':1,'sha':'0'*40,'content':'eA=='}))
            with self.assertRaises(ValueError):renderer.finalize_controller(final)

    def test_native_cohort_and_asset_changes_fail_before_output(self):
        bad=dict(NATIVE);bad['software_tests']=597
        with self.assertRaises(ValueError):renderer.native_pins(bad)
        with self.assertRaises(ValueError):renderer.retained_data(INPUT_RAW+b' ',NATIVE)
        with self.assertRaises(ValueError):renderer.accepted_review({'schema':'merlin-independent-native-artifact-review/2','status':'rejected_or_incomplete'},NATIVE)

    def test_runner_fourth_blob_has_exact_bytes_git_hash_and_size(self):
        import base64
        text=(HERE/'ops/merlin_dot/run_research_episode.py.in').read_text().replace('__FROZEN_RUNNER_PINS__','{}')
        module=types.ModuleType('fixture_runner');exec(compile(text,'fixture_runner','exec'),module.__dict__)
        identity=renderer.identity(INPUT_RAW)
        obj={'encoding':'base64','content':base64.b64encode(INPUT_RAW).decode()}
        self.assertEqual(INPUT_RAW,module.exact_blob(lambda path:obj,identity,32000))
        for bad in (dict(identity,sha256='0'*64),dict(identity,git_blob='0'*40),dict(identity,bytes=1)):
            with self.subTest(bad=bad),self.assertRaises(ValueError):module.exact_blob(lambda path:obj,bad,32000)
        with self.assertRaises(ValueError):module.exact_blob(lambda path:obj,identity,10)

    def test_emitted_private_child_is_fixed_python39_without_execution(self):
        seen=[]
        def capture(argv,**kwargs):
            self.assertEqual(['/usr/sbin/runuser','-u','opc','--','/usr/bin/python3','-I','-B','-S','-c'],argv[:9])
            ast.parse(argv[9],feature_version=(3,9));seen.append(argv)
            return types.SimpleNamespace(returncode=0,stdout=b'{"ok":true,"result":{}}')
        owner=lambda name:types.SimpleNamespace(pw_uid=982 if name=='merlin-dot' else 1000)
        with patch.object(HOST.pwd,'getpwnam',owner),patch.object(HOST.subprocess,'run',capture):
            HOST.private_call(Path('/fixture/source'),'context_fetch',{'source_ref':INPUT['a_result_ref'],'start_byte':0,'length_bytes':16000})
        self.assertEqual(1,len(seen))
        with self.assertRaises(ValueError):HOST.private_call(Path('/fixture'),'ungranted',{})

    def test_report_publication_interruption_never_repeats_workers(self):
        f=Fixture(self);f.step('selection');original=f.store.put_artifact
        def interrupt(project,path,raw,*args,**kwargs):
            result=original(project,path,raw,*args,**kwargs)
            if path==HOST.report_context_base()+'source.txt':raise RuntimeError('synthetic context interruption')
            return result
        with patch.object(f.store,'put_artifact',interrupt),self.assertRaises(RuntimeError):f.step('final')
        with self.assertRaises(ValueError):f.step('final')
        with self.assertRaises((ValueError,KeyError)):f.step('replay',reader=PrivateReadOnlyRegistry(f.store.root))
        self.assertEqual(4,len(f.process.calls))
        self.assertEqual(f.before,HOST.preserved_records(f.store,INPUT))


if __name__=='__main__':unittest.main(verbosity=2)

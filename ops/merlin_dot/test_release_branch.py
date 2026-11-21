"""Synthetic bounded controller controls; never native/model/service execution."""
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import zipfile

if importlib.util.find_spec('release_branch'):
    import release_branch as release
else:
    release = ModuleType('release_branch')
    raw = (Path(__file__).parent / 'release_assessment_branch.py.in').read_text().replace('__RELEASE_PINS__', '{}')
    exec(compile(raw, 'local-release-template-fixture', 'exec'), release.__dict__)


def packed(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, raw in sorted(files.items()):
            archive.writestr(name, raw)
    return buffer.getvalue()


class Fixture:
    """Every identity here is synthetic and stays inside temporary test data."""
    def __init__(self):
        self.files = {'python/fixture.py': b'VALUE = 3\n', 'tests/test_fixture.py': b'# fixture only\n'}
        mapping = {name: release.sha(body) for name, body in self.files.items()}
        self.pins = {'source_commit': '1' * 40, 'source_map_sha256': release.sha(release.canonical(mapping)),
            'source_files': mapping, 'runtime_files': {'python/fixture.py': mapping['python/fixture.py']},
            'provider_inspector': {'sha256': release.sha(b'fixture-inspector'), 'git_blob': release.git_blob(b'fixture-inspector')}}
        self.n = {'run_id': 101, 'run_attempt': 1, 'workflow_commit': '2' * 40,
            'workflow_git_blob': '3' * 40, 'controller_git_blob': release.git_blob(b'# fixture controller\n'),
            'controller_sha256': release.sha(b'# fixture controller\n'), 'artifact_id': 202,
            'software_tests': 1, 'test_inventory_sha256': release.sha(release.canonical(
                {'schema': 'merlin-executed-software-tests/1', 'test_ids': ['fixture.test_exact']}))}
        self.pins['native'] = self.n
        self.manifest = {'schema': 'merlin-egm-source/2', 'source_commit': self.pins['source_commit'],
            'source_map_sha256': self.pins['source_map_sha256'], 'files': mapping,
            'git_blobs': {name: release.git_blob(body) for name, body in self.files.items()},
            'qualification': False, 'promotion_authority': False}
        common = {'source_commit': self.pins['source_commit'], 'source_map_sha256': self.pins['source_map_sha256'],
            'run_id': 101, 'status': 'succeeded', 'qualification': False, 'promotion_authority': False}
        software = {**common, 'schema': 'merlin-software-inventory/1', 'tests': 1, 'collected_tests': 1,
            'collection_ids': ['fixture.test_exact'], 'executed_test_ids': ['fixture.test_exact'],
            'collection_sha256': self.n['test_inventory_sha256'], 'test_inventory_sha256': self.n['test_inventory_sha256'],
            'passed': True, 'executed': True, 'source_unchanged': True, 'errors': 0, 'failures': 0,
            'skipped': 0, 'expected_failures': 0, 'unexpected_successes': 0}
        self.report = {**common, 'schema': 'merlin-egm-oci-validation/2', 'run_attempt': 1,
            'workflow_commit': self.n['workflow_commit'], 'runner': 'cace-oci-a1',
            'source_kind': 'exact_selected_candidate_shard', 'architecture': 'aarch64',
            'service_unchanged': True, 'permissions_modified': False, 'private_context_used': False,
            'production_service_modified': False, 'actual_native_model_review_performed': False, 'tests': software,
            'service_before': {'MainPID': '9', 'ActiveState': 'active', 'SubState': 'running', 'UnitFileState': 'enabled'},
            'service_after': {'MainPID': '9', 'ActiveState': 'active', 'SubState': 'running', 'UnitFileState': 'enabled'}}
        for role, names in (('kernel', release.KERNEL_CASES), ('context', release.CONTEXT_CASES)):
            self.report[role] = {**common, 'cases': [{'name': name, 'passed': True} for name in names],
                'required_case_names': names, 'failed_case_ids': [], 'accepted': True,
                'case_inventory_exact': True, 'source_identity_exact': True, 'scope_exact': True,
                'service_unchanged': True, 'permissions_modified': False, 'production_service_modified': False,
                'tests': len(names), 'passed': len(names)}
        self.repack()
        self.run = {'id': 101, 'run_attempt': 1, 'event': 'push', 'path': release.NATIVE_WORKFLOW,
            'head_sha': self.n['workflow_commit'], 'head_branch': release.NATIVE_BRANCH,
            'status': 'completed', 'conclusion': 'success',
            'repository': {'id': 7, 'full_name': 'morganaspim/Cace-app'},
            'head_repository': {'id': 7, 'full_name': 'morganaspim/Cace-app'}}
        self.item = {'id': 202, 'name': 'merlin-egm-101-1', 'expired': False,
            'size_in_bytes': len(self.raw), 'digest': 'sha256:' + release.sha(self.raw),
            'workflow_run': {'id': 101, 'head_sha': self.n['workflow_commit'],
                'head_branch': release.NATIVE_BRANCH, 'repository_id': 7, 'head_repository_id': 7}}
        revision='gguf:'+'a'*64+';llama:'+'b'*40+';bin:'+'c'*64
        self.provider={'manifest':release.canonical({'revision':revision}),'bootstrap':b'fixture-bootstrap'}
        self.old_records={name:('synthetic preserved only: '+name).encode() for name in release.PRESERVED_RECORDS}
        self.old_hashes={name:release.sha(raw) for name,raw in self.old_records.items()}
        self.old_status={session:{'schema':'dot-dual-coder-status/1','session_id':session,'status':'incomplete',
            'qualification':False,'promotion_authority':False,'fixture':True} for session in release.GENERATION_SESSIONS}
        self.old_status_hashes={session:release.sha(release.canonical(value)) for session,value in self.old_status.items()}
        self.retained_raw=release.canonical({'schema':'synthetic-retained-inputs/1','records':self.old_hashes})
        self.retained_sha=release.sha(self.retained_raw)
        report=release.canonical({'schema':'merlin-retained-solver-assessment/1',
            'status':'completed_negative_result','recommendation':'retain_baseline','qualification':False,
            'promotion_authority':False,'fixture':'inert synthetic data, no native or model observation'})
        base='local-research/'+release.SESSION+'/host/'
        source_path='context/merlin/'+release.sha((release.SESSION+':assessment-report').encode())+'/source.txt'
        self.new_records={base+'retained-inputs.json':self.retained_raw,base+'research-plan.json':b'{"synthetic_plan":true}',
            base+'provider-manifest.json':self.provider['manifest'],base+'provider-bootstrap.json':self.provider['bootstrap'],
            'local-solver/'+release.SESSION+'/report.json':report,source_path:report}
        paths={'retained_inputs_ref':base+'retained-inputs.json','research_plan_ref':base+'research-plan.json',
            'provider_manifest_ref':base+'provider-manifest.json','provider_bootstrap_ref':base+'provider-bootstrap.json',
            'assessment_report_ref':'local-solver/'+release.SESSION+'/report.json','report_source_ref':source_path}
        self.refs={key:release.record_ref(path,release.sha(self.new_records[path])) for key,path in paths.items()}
        self.context={'schema':'dot-context-source-page/1','source_ref':self.refs['report_source_ref'],
            'start_byte':0,'end_byte':len(report),'total_bytes':len(report),'next_start_byte':None,
            'text':report.decode(),'excerpt_sha256':release.sha(report),'verification_scope':'artifact-integrity-only','qualification':False}
        handoff={'schema':'dot-session-handoff/1','session_id':release.SESSION,'summary':'Synthetic negative result.',
            'next_action':'Retain baseline.','source_refs':[self.refs['report_source_ref']],'authority':'context_only','qualification':False}
        handoff_raw=release.canonical(handoff);handoff_path='handoffs/'+release.SESSION+'.json'
        self.new_records[handoff_path]=handoff_raw
        self.refs['handoff_ref']=release.record_ref(handoff_path,release.sha(handoff_raw))
        self.handoff={'handoff_ref':self.refs['handoff_ref'],'handoff':handoff}
        invocation={'request_id':'11111111-2222-4333-8444-555555555555','run_id':303,'run_attempt':1,'workflow_commit':'5'*40}
        def wrapper(tool,arguments,value):
            return {'caller_uid':1000,'server_uid':982,'transport':'SO_PEERCRED Unix socket','tool':tool,'arguments':arguments,
                'result':deepcopy(value),'result_sha256':release.sha(release.canonical(value))}
        reads={'context_fetch':wrapper('context_fetch',{'source_ref':self.refs['report_source_ref'],'start_byte':0,'length_bytes':16000},self.context),
            'session_handoff':wrapper('session_handoff',{'session_id':release.SESSION},self.handoff)}
        old={session:wrapper('rsi_status',{'session_id':session},value) for session,value in self.old_status.items()}
        phases={}
        for phase,pid,launches in (('selection',301,2),('final',302,2),('replay',303,0)):
            result={'schema':'merlin-retained-assessment-phase-result/1','status':'selection_recorded' if phase=='selection' else 'completed_research_only',
                'session_id':release.SESSION,'branch_state':{'fixture':'complete' if phase!='selection' else 'partial'},
                'measurement_refs':[],'observation_refs':[],
                'report_ref':None if phase=='selection' else self.refs['assessment_report_ref'],
                'report_source_ref':None if phase=='selection' else self.refs['report_source_ref'],
                'handoff_ref':None if phase=='selection' else self.refs['handoff_ref'],
                'effects_this_call':{'inference_attempts':0,'inference_responses':0,'metadata_requests':0,'native_process_launches':launches},
                'qualification':False,'promotion_authority':False}
            phases[phase]={'schema':'merlin-retained-assessment-phase/1','phase':phase,'pid':pid,'elapsed_seconds':0.1,
                'registry_observation':{'before_inventory_sha256':'a'*64,'after_inventory_sha256':'a'*64,
                    'database_before_sha256':'b'*64,'database_after_sha256':'b'*64,'new_artifact_refs':[]},'result':result}
        self.assessment={'schema':'merlin-retained-assessment-host-receipt/1','status':'succeeded','project_id':release.PROJECT,
            'session_id':release.SESSION,'source_commit':self.pins['source_commit'],'source_map_sha256':self.pins['source_map_sha256'],
            'native_validation':{**self.n,'source_commit':self.pins['source_commit'],'source_map_sha256':self.pins['source_map_sha256']},
            'invocation':invocation,**self.refs,'phases':phases,'report_sha256':release.sha(report),'report_bytes':len(report),
            'private_reads':{'final':deepcopy(reads),'replay':deepcopy(reads)},
            'expected_context_fetch_sha256':release.sha(release.canonical(self.context)),
            'expected_handoff_result_sha256':release.sha(release.canonical(self.handoff)),
            'old_generation_status_before':deepcopy(old),'old_generation_status_after':deepcopy(old),
            'provider_revision':revision,'private_service_before':{'MainPID':7},'private_service_after':{'MainPID':7},
            'provider_service_before':{'MainPID':8},'provider_service_after':{'MainPID':8},
            'historical_research_model_calls':3,'new_model_calls':0,'cumulative_research_model_calls':3,
            'external_model_budget_usd':0,'preservation_before_sha256':'d'*64,'preservation_after_sha256':'d'*64,
            'prewrite_backup_sha256':'e'*64,'qualification':False,'promotion_authority':False}
        self.assessment_raw=release.canonical(self.assessment)
        self.pins['assessment']={'ref':release.record_ref(release.RECEIPT_PATH,release.sha(self.assessment_raw)),
            'invocation':invocation,'refs':self.refs,'provider_revision':revision,
            'report_sha256':release.sha(report),'report_bytes':len(report),
            'expected_context_fetch_sha256':release.sha(release.canonical(self.context)),
            'expected_handoff_result_sha256':release.sha(release.canonical(self.handoff)),
            'provider_files':{key:release.sha(value) for key,value in self.provider.items()}}
        self.provider_observation={'schema':'merlin-local-model-inspect/1','status':'ready',
            'manifest_sha256':self.pins['assessment']['provider_files']['manifest'],
            'bootstrap_receipt_sha256':self.pins['assessment']['provider_files']['bootstrap'],
            'service':{'main_pid':7,'active_state':'active'},'inference_requests':0,'qualification':False,'external_model_cost_usd':0}

    def repack(self):
        source = packed({**self.files, 'manifest.json': release.canonical(self.manifest)})
        self.n['source_package_sha256'] = release.sha(source)
        self.report['source_package_sha256'] = release.sha(source)
        report = release.canonical(self.report); self.n['report_sha256'] = release.sha(report)
        self.raw = packed({'tested-source.zip': source, 'report.json': report, 'controller.txt': b'# fixture controller\n'})
        self.n['artifact_bytes'] = len(self.raw); self.n['artifact_sha256'] = release.sha(self.raw)

    def api(self, path):
        if path == 'actions/runs/101': return deepcopy(self.run)
        if path == 'actions/artifacts/202': return deepcopy(self.item)
        if path == 'contents/' + release.NATIVE_WORKFLOW + '?ref=' + self.n['workflow_commit']:
            return {'sha': self.n['workflow_git_blob']}
        if path == 'contents/' + release.NATIVE_CONTROLLER + '?ref=' + self.n['workflow_commit']:
            return {'sha': self.n['controller_git_blob']}
        raise AssertionError('unexpected fixture API route: ' + path)

    def download(self, identity, size):
        assert identity == 202 and size == len(self.raw)
        return self.raw


class ReleaseControls(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()
        self.scope = patch.dict(release.__dict__, {'PINS': self.fixture.pins,
            'PRESERVED_RECORDS': self.fixture.old_hashes, 'OLD_STATUS_SHA256': self.fixture.old_status_hashes,
            'RETAINED_INPUTS_SHA256': self.fixture.retained_sha,
            'PROVIDER_INSPECTOR': lambda: deepcopy(self.fixture.provider_observation)}); self.scope.start()
        self.addCleanup(self.scope.stop)

    def test_exact_synthetic_native_and_deterministic_runtime_projection(self):
        files, report = release.accepted_source(self.fixture.api, self.fixture.download)
        self.assertEqual(files, self.fixture.files)
        one, manifest, digest = release.runtime_archive(files)
        two, _, _ = release.runtime_archive(dict(reversed(list(files.items()))))
        self.assertEqual(one, two)
        self.assertEqual(set(release.members(one)), {'manifest.json', 'python/fixture.py'})
        self.assertEqual(manifest['source_base_commit'], self.fixture.pins['source_commit'])
        self.assertEqual(digest, release.sha(release.members(one)['manifest.json']))
        self.assertEqual(report['tests']['tests'], 1)

    def test_run_attempt_branch_and_producer_must_match(self):
        for key, value in (('run_attempt', 2), ('head_branch', 'different'), ('conclusion', 'failure'), ('path', 'other.yml')):
            old = self.fixture.run[key]; self.fixture.run[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                release.accepted_source(self.fixture.api, self.fixture.download)
            self.fixture.run[key] = old
        def api(path):
            result = self.fixture.api(path)
            if path.startswith('contents/'): result['sha'] = 'f' * 40
            return result
        with self.assertRaises(ValueError): release.accepted_source(api, self.fixture.download)

    def test_artifact_origin_size_digest_and_download_bytes_are_bound(self):
        for key, value in (('size_in_bytes', len(self.fixture.raw) + 1), ('digest', 'sha256:' + 'f' * 64), ('expired', True)):
            old = self.fixture.item[key]; self.fixture.item[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                release.accepted_source(self.fixture.api, self.fixture.download)
            self.fixture.item[key] = old
        self.fixture.item['workflow_run']['head_sha'] = 'f' * 40
        with self.assertRaises(ValueError): release.accepted_source(self.fixture.api, self.fixture.download)
        self.fixture.item['workflow_run']['head_sha'] = self.fixture.n['workflow_commit']
        for body in (self.fixture.raw[:-1], b'x' + self.fixture.raw[1:]):
            with self.assertRaises(ValueError): release.accepted_source(self.fixture.api, lambda *_: body)

    def test_native_inventory_case_and_scope_contradictions_reject_after_repin(self):
        changes = (
            lambda r: r['tests']['executed_test_ids'].__setitem__(0, 'same_count_other_test'),
            lambda r: r['kernel']['cases'][0].__setitem__('passed', False),
            lambda r: r['context']['cases'][0].__setitem__('name', 'different_context_case'),
            lambda r: r.__setitem__('qualification', True),
            lambda r: r['service_after'].__setitem__('MainPID', '10'),
        )
        original = deepcopy(self.fixture.report)
        for mutate in changes:
            self.fixture.report = deepcopy(original); mutate(self.fixture.report); self.fixture.repack()
            with self.assertRaises(ValueError): release.checked_native_archive(self.fixture.raw)

    def test_full_source_membership_hash_and_git_mismatch_reject_after_repin(self):
        self.fixture.files['unexpected.py'] = b'x'
        self.fixture.repack()
        with self.assertRaises(ValueError): release.checked_native_archive(self.fixture.raw)
        del self.fixture.files['unexpected.py']
        self.fixture.files['python/fixture.py'] += b'# changed'
        self.fixture.repack()
        with self.assertRaises(ValueError): release.checked_native_archive(self.fixture.raw)
        self.fixture.files['python/fixture.py'] = b'VALUE = 3\n'
        self.fixture.manifest['git_blobs']['python/fixture.py'] = 'f' * 40
        self.fixture.repack()
        with self.assertRaises(ValueError): release.checked_native_archive(self.fixture.raw)

    def test_projection_requires_exact_source_subset_and_member_ceiling(self):
        self.fixture.pins['runtime_files']['python/unaccepted.py'] = 'f' * 64
        with self.assertRaises(ValueError): release.projection_manifest()
        self.fixture.pins['runtime_files'] = {'python/f%d.py' % x: 'f' * 64 for x in range(50)}
        self.fixture.pins['source_files'].update(self.fixture.pins['runtime_files'])
        with self.assertRaises(ValueError): release.projection_manifest()
        self.fixture.pins['runtime_files'] = {'tests/test_fixture.py': self.fixture.pins['source_files']['tests/test_fixture.py']}
        with self.assertRaises(ValueError): release.projection_manifest()







    def test_reviewed_assessment_receipt_binds_source_native_counts_and_negative_result_scope(self):
        self.assertEqual(release.check_assessment(self.fixture.assessment),self.fixture.assessment)
        for key,value in (('schema','merlin-real-research-host/1'),('source_commit','f'*40),('session_id','other'),
                ('native_validation',{}),('qualification',0),('promotion_authority',True),('new_model_calls',False),
                ('new_model_calls',1),('historical_research_model_calls',2),('cumulative_research_model_calls',4),
                ('external_model_budget_usd',1),('provider_revision','other'),('report_bytes',16001)):
            changed=deepcopy(self.fixture.assessment);changed[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):release.check_assessment(changed)

    def test_fresh_phases_exact_effects_and_replay_report_are_required(self):
        changes=(('selection', 'native_process_launches',3),('final','native_process_launches',0),
            ('replay','native_process_launches',1),('final','metadata_requests',1),('selection','inference_attempts',1),
            ('replay','inference_responses',False))
        for phase,key,value in changes:
            changed=deepcopy(self.fixture.assessment);changed['phases'][phase]['result']['effects_this_call'][key]=value
            with self.subTest(phase=phase,key=key),self.assertRaises(ValueError):release.check_assessment(changed)
        for change in ('same_pid','late','missing','report','branch','database','inventory','new_ref'):
            changed=deepcopy(self.fixture.assessment)
            if change=='same_pid':changed['phases']['replay']['pid']=changed['phases']['final']['pid']
            elif change=='late':changed['phases']['replay']['elapsed_seconds']=31
            elif change=='missing':changed['phases'].pop('selection')
            elif change=='report':changed['phases']['final']['result']['report_ref']=None
            elif change=='branch':changed['phases']['replay']['result']['branch_state']={}
            elif change=='database':changed['phases']['replay']['registry_observation']['database_after_sha256']='c'*64
            elif change=='inventory':changed['phases']['replay']['registry_observation']['after_inventory_sha256']='c'*64
            else:changed['phases']['replay']['registry_observation']['new_artifact_refs']=[self.fixture.refs['handoff_ref']]
            with self.subTest(change=change),self.assertRaises(ValueError):release.check_assessment(changed)

    def test_report_requires_all_bytes_and_handoff_only_the_pinned_source(self):
        for change in ('truncated','pagination','false_qualification','handoff_extra','handoff_other','summary_changed'):
            context=deepcopy(self.fixture.context);handoff=deepcopy(self.fixture.handoff)
            if change=='truncated':context['text']=context['text'][:-1]
            elif change=='pagination':context['next_start_byte']=context['end_byte']
            elif change=='false_qualification':context['qualification']=0
            elif change=='handoff_extra':handoff['handoff']['source_refs']*=2
            elif change=='handoff_other':handoff['handoff']['source_refs'][0]['sha256']='f'*64
            else:handoff['handoff']['summary']='not reviewed'
            with self.subTest(change=change),self.assertRaises(ValueError):release.check_private_results(context,handoff)

    def test_old_generation_sessions_cannot_be_relabelled_or_changed(self):
        for session in release.GENERATION_SESSIONS:
            for change in ('completed','digest','missing'):
                value=deepcopy(self.fixture.assessment)
                if change=='missing':value['old_generation_status_after'].pop(session)
                elif change=='completed':value['old_generation_status_after'][session]['result']['status']='completed_research_only'
                else:value['old_generation_status_after'][session]['result_sha256']='f'*64
                with self.subTest(session=session,change=change),self.assertRaises(ValueError):release.check_assessment(value)

    def _canonical_reader(self,change=None):
        records={**self.fixture.old_records,**self.fixture.new_records,release.RECEIPT_PATH:self.fixture.assessment_raw}
        first=next(iter(self.fixture.old_records));reads=[];history_changes={};aliases={};rows={}
        if change=='missing_old':records.pop(first)
        elif change=='old_bytes':records[first]+=b' '
        elif change=='history':history_changes[first]=[{'version':1},{'version':2}]
        elif change=='boolean_history':history_changes[first]=[{'version':True}]
        elif change=='current_alias':aliases[first]={'sha256':'f'*64}
        elif change=='boolean_alias':aliases[first]={'version':True}
        elif change=='missing_report':records.pop(self.fixture.refs['assessment_report_ref']['logical_path'])
        elif change=='context_bytes':records[self.fixture.refs['report_source_ref']['logical_path']]+=b' '
        elif change=='old_extra':records['dual-coder/'+release.GENERATION_SESSIONS[1]+'/stages/evaluator/intent.json']=b'{}'
        elif change=='old_branch_extra':records['branch-research/'+release.GENERATION_SESSIONS[0]+'/unexpected.json']=b'{}'
        elif change=='inventory_alias':rows[first]={'digest':'f'*64}
        def history(project,name):
            reads.append(('history',name));return history_changes.get(name,[{'version':1}] if name in records else [])
        def artifact_ref(project,name):
            reads.append(('ref',name));return {**release.record_ref(name,release.sha(records[name])),**aliases.get(name,{})}
        def content(ref,*,max_bytes):
            self.assertEqual(max_bytes,256*1024);reads.append(('content',ref['logical_path']));return {'content':records[ref['logical_path']]}
        registry=SimpleNamespace(artifact_history=history,artifact_ref=artifact_ref,read_artifact_ref=content,
            inventory=lambda project:{'artifacts':[{'logical_path':name,'version':1,'digest':release.sha(raw),
                'size_bytes':len(raw),**rows.get(name,{})} for name,raw in records.items()]})
        private=ModuleType('dot_ai_os.private_runtime')
        def construct(path):
            self.assertEqual(path,'/var/lib/merlin-dot-private/state');return registry
        private.PrivateReadOnlyRegistry=construct;outputs=[]
        def run(argv,**kw):
            self.assertEqual(kw['user'],982);self.assertEqual(kw['timeout'],15)
            stream=io.BytesIO();outputs.append(stream)
            with patch.dict('sys.modules',{'dot_ai_os.private_runtime':private}),patch.object(sys,'argv',['fixture-only']+argv[5:]), \
                    patch.object(sys,'path',list(sys.path)),patch.object(sys,'stdout',SimpleNamespace(buffer=stream)):
                exec(compile(argv[4],'actual-readonly-assessment-child','exec'),{})
            return SimpleNamespace(stdout=stream.getvalue())
        with patch.object(release.subprocess,'run',side_effect=run):
            if change is None:
                answer=release.assessment_probe({'_regular':self._provider_guard},Path('/fixture-release'),socket_status=False)
                self.assertEqual(answer['preserved_records_verified'],39)
                self.assertEqual(outputs[0].getvalue(),self.fixture.assessment_raw)
                self.assertEqual(len([x for x in reads if x[0]=='content']),47)
            else:
                with self.assertRaises((AssertionError,KeyError)):
                    release.assessment_probe({'_regular':self._provider_guard},Path('/fixture-release'),socket_status=False)
                self.assertEqual(outputs[0].getvalue(),b'')

    def test_actual_canonical_child_reads_all39_and_exact_new_report_refs_without_writes(self):
        self._canonical_reader()

    def test_actual_canonical_child_rejects_missing_changed_or_superseded_evidence(self):
        for change in ('missing_old','old_bytes','history','boolean_history','current_alias','boolean_alias',
                'missing_report','context_bytes','old_extra','old_branch_extra','inventory_alias'):
            with self.subTest(change=change):self._canonical_reader(change)

    def _socket_reader(self,change=None):
        private=ModuleType('dot_ai_os.private_runtime');calls=[]
        def call_socket(path,request,**kwargs):
            self.assertEqual(path,'/run/merlin-dot-private/tools.sock')
            self.assertEqual(kwargs,{'expected_server_uid':982,'timeout_seconds':5})
            calls.append(deepcopy(request));tool=request['tool'];args=request['arguments']
            if tool=='context_fetch':
                self.assertEqual(args,{'source_ref':self.fixture.refs['report_source_ref'],'start_byte':0,'length_bytes':16000})
                value=deepcopy(self.fixture.context)
                if change=='report':value['text']+='changed'
            elif tool=='session_handoff':
                self.assertEqual(args,{'session_id':release.SESSION});value=deepcopy(self.fixture.handoff)
                if change=='handoff':value['handoff']['summary']='changed'
            elif tool=='rsi_status':
                self.assertIn(args['session_id'],release.GENERATION_SESSIONS);value=deepcopy(self.fixture.old_status[args['session_id']])
                if change=='old':value['status']='completed_research_only'
            else:self.fail('unexpected private tool')
            return {'ok':True,'qualification':False,'promotion_authority':False,'result':value}
        private.call_socket=call_socket
        def run(argv,**kw):
            self.assertEqual(kw['timeout'],15);self.assertEqual(kw['extra_groups'],[]);self.assertEqual(kw['cwd'],'/')
            if kw['user']==982:return SimpleNamespace(stdout=self.fixture.assessment_raw)
            self.assertEqual(kw['user'],1000);stream=io.StringIO()
            with patch.dict('sys.modules',{'dot_ai_os.private_runtime':private}),patch.object(sys,'argv',['fixture-only']+argv[5:]), \
                    patch.object(sys,'path',list(sys.path)),patch.object(sys,'stdout',stream):
                exec(compile(argv[4],'actual-readonly-socket-child','exec'),{})
            return SimpleNamespace(stdout=stream.getvalue())
        with patch.object(release.subprocess,'run',side_effect=run):
            if change is None:
                result=release.assessment_probe({'_regular':self._provider_guard},Path('/fixture-release'))
                self.assertTrue(result['private_reads']['read_only_unix_route']);self.assertFalse(result['canonical_state_writes'])
                self.assertEqual(result['private_reads']['old_generation_status_sha256'],self.fixture.old_status_hashes)
            else:
                with self.assertRaises(ValueError):release.assessment_probe({'_regular':self._provider_guard},Path('/fixture-release'))
        self.assertEqual([item['tool'] for item in calls],['context_fetch','session_handoff','rsi_status','rsi_status'])

    def test_actual_socket_child_uses_full_existing_context_handoff_and_old_status_routes(self):
        self._socket_reader()

    def test_changed_report_handoff_or_old_status_blocks_readonly_probe(self):
        for change in ('report','handoff','old'):
            with self.subTest(change=change):self._socket_reader(change)

    def test_receipt_byte_change_blocks_readonly_probe(self):
        with patch.object(release.subprocess,'run',return_value=SimpleNamespace(stdout=self.fixture.assessment_raw+b' ')):
            with self.assertRaises(RuntimeError):release.assessment_probe({'_regular':self._provider_guard},Path('/fixture'))

    def _provider_guard(self, path, *, expected, maximum):
        name = 'manifest' if path.name == 'manifest.json' else 'bootstrap'
        raw = self.fixture.provider[name]
        self.assertEqual(expected, release.sha(raw)); self.assertEqual(maximum, 256 * 1024)
        return raw

    def test_provider_source_is_exact_before_compile_and_entrypoint_call(self):
        raw = b"calls = []\ndef inspect_ready():\n calls.append('inspect')\n return {'fixture': True}\n"
        reads = []
        def read(path, **kw):
            reads.append((path, kw)); return raw
        with patch.dict(release.PINS, {'provider_inspector': {'sha256': release.sha(raw), 'git_blob': release.git_blob(raw)}}):
            inspect = release.load_provider_inspector({'_regular': read}, '/fixture/provider-inspector.py')
            self.assertEqual(inspect.__globals__['calls'], [])
            self.assertEqual(inspect(), {'fixture': True})
            self.assertEqual(inspect.__globals__['calls'], ['inspect'])
            self.assertEqual(reads, [(Path('/fixture/provider-inspector.py'),
                {'root_owned': False, 'expected': release.sha(raw), 'maximum': 65536})])

    def test_provider_source_mutation_or_missing_entrypoint_rejects(self):
        raw = b"def inspect_ready():\n return None\n"
        with patch.dict(release.PINS, {'provider_inspector': {'sha256': release.sha(raw), 'git_blob': release.git_blob(raw)}}):
            with self.assertRaisesRegex(RuntimeError, 'source differs'):
                release.load_provider_inspector({'_regular': lambda *_a, **_k: b'raise AssertionError()\n'}, '/fixture')
        raw = b'NOT_AN_INSPECTOR = 1\n'
        with patch.dict(release.PINS, {'provider_inspector': {'sha256': release.sha(raw), 'git_blob': release.git_blob(raw)}}):
            with self.assertRaisesRegex(RuntimeError, 'entrypoint missing'):
                release.load_provider_inspector({'_regular': lambda *_a, **_k: raw}, '/fixture')

    def test_provider_observation_has_exact_authority_and_no_inference(self):
        for key, value in (('manifest_sha256', 'f' * 64), ('bootstrap_receipt_sha256', 'f' * 64),
                ('status', 'not-ready'), ('qualification', 0), ('inference_requests', False),
                ('inference_requests', 1), ('external_model_cost_usd', 1), ('service', None)):
            observation = deepcopy(self.fixture.provider_observation); observation[key] = value
            with self.subTest(key=key, value=value), patch.object(release, 'PROVIDER_INSPECTOR', return_value=observation) as inspector:
                with self.assertRaises(RuntimeError): release.provider_probe()
                inspector.assert_called_once_with()
        with patch.object(release, 'PROVIDER_INSPECTOR', None):
            with self.assertRaisesRegex(RuntimeError, 'was not loaded'): release.provider_probe()

    def test_unready_provider_fails_before_canonical_reader_without_retry(self):
        with patch.object(release, 'PROVIDER_INSPECTOR', side_effect=RuntimeError('fixture service stopped')) as inspector, \
             patch.object(release.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'fixture service stopped'):
                release.assessment_probe({'_regular': self._provider_guard}, Path('/fixture'))
            inspector.assert_called_once_with(); run.assert_not_called()

    def test_root_bootstrap_uses_verified_external_inspector_under_same_ceiling(self):
        sources = {name: b'VALUE = 1\n' for name in ('installer', 'guards', 'controller')}
        code = release.root_bootstrap(sources, Path('/fixture/provider-inspector.py'), 'None')
        self.assertIn("m['load_provider_inspector'](g,'/fixture/provider-inspector.py')", code)
        self.assertNotIn('def inspect_ready', code)
        self.assertLess(len(code.encode()), 110000)
        sources['controller'] = b'#' + b'x' * 110000
        with self.assertRaisesRegex(RuntimeError, 'bootstrap size limit'):
            release.root_bootstrap(sources, Path('/fixture/provider-inspector.py'), 'None')



    def test_health_retries_only_not_ready_socket_errors(self):
        scope = {}; exec(release.HEALTH_WAIT, scope)
        elapsed = [0.0]; calls = [0]
        healthy = {'ok': True, 'qualification': False, 'promotion_authority': False,
                   'result': {'transport': 'unix', 'public_listener': False}}
        def call():
            calls[0] += 1
            if calls[0] == 1: raise FileNotFoundError()
            if calls[0] == 2: raise ConnectionRefusedError()
            return healthy
        result = scope['await_health'](call, lambda: elapsed[0], lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds))
        self.assertEqual(result['attempts'], 3)
        with self.assertRaises(RuntimeError): scope['await_health'](lambda: {'ok': False}, lambda: 0, lambda _: self.fail('must not retry bad health'))
        with self.assertRaises(PermissionError): scope['await_health'](lambda: (_ for _ in ()).throw(PermissionError()), lambda: 0, lambda _: self.fail('must not retry denied peer'))

    def test_binary_subprocess_diagnostics_remain_json_serializable(self):
        error = release.subprocess.CalledProcessError(1, ['fixture-only'], stderr=b'fixture reader failure\xff')
        result = release.error_details(error)
        self.assertIsInstance(result['stderr'], str)
        self.assertIn('fixture reader failure', json.dumps(result))

    def _activation(self, mode):
        with tempfile.TemporaryDirectory(prefix='merlin-release-controller-fixture-') as temp:
            root = Path(temp); source = root / 'source'; (source / 'releases').mkdir(parents=True)
            config = root / 'config'; (config / 'upgrade-history').mkdir(parents=True)
            old = source / 'releases' / release.BASE_SHA; old.mkdir(); (old / 'preserved.txt').write_text('old')
            (source / 'current').symlink_to(old)
            calls = []; expected = {'fixture': True}; bundle = b'fixture-package'; new_sha = release.sha(bundle)
            new = source / 'releases' / new_sha
            manifest = release.projection_manifest()
            def regular(path, **kwargs):
                self.assertEqual(kwargs['expected'], new_sha); return bundle
            def unpack(raw, digest, path):
                self.assertEqual(raw, bundle); self.assertEqual(digest, new_sha)
                path.mkdir(); (path / 'manifest.json').write_bytes(release.canonical(manifest)); return manifest
            def switch(target, previous, token):
                self.assertEqual(os.readlink(source / 'current'), str(previous)); calls.append(('switch', target.name))
                (source / 'current').unlink(); (source / 'current').symlink_to(target)
            def ready(g, path):
                calls.append(('ready', path.name))
                if mode in ('rollback', 'unknown_link') and path == new:
                    if mode == 'unknown_link':
                        (source / 'current').unlink(); (source / 'current').symlink_to(root / 'unexpected')
                    raise RuntimeError('fixture startup failure')
                return {'fixture_ready': True}
            g = {'SOURCE': source, 'CONFIG': config / 'config.json', '_root_directory': lambda *_: None,
                '_regular': regular, '_verify_release': lambda *_: None, '_systemctl': lambda action: calls.append(('systemctl', action)),
                '_switch': switch, '_wait_active': lambda: None, '_new_file': lambda path, raw: path.write_bytes(raw)}
            if mode == 'existing': new.mkdir()
            # The CI runner is UID1000; only the fixed supervisor is root. Model
            # that one lock metadata observation here, without privilege changes.
            with patch.object(release.os, 'fstat', return_value=SimpleNamespace(st_mode=0o100600, st_uid=0)), \
                 patch.object(release, 'preflight', return_value={'different': True} if mode == 'changed' else expected), \
                 patch.object(release, 'snapshot', return_value={'fixture': 'profile'}), \
                 patch.object(release, 'ready_probe', side_effect=ready), \
                 patch.object(release, 'assessment_probe', return_value={'fixture': 'read_only_episode'}), \
                 patch.object(release, 'library_probe', return_value={'fixture': 'import_smoke'}):
                if mode in ('existing', 'changed'):
                    with self.assertRaises(RuntimeError): release.activate(g, unpack, root / 'runtime.zip', new_sha, expected)
                    self.assertEqual(calls, [])
                    return
                result = release.activate(g, unpack, root / 'runtime.zip', new_sha, expected)
            self.assertEqual((old / 'preserved.txt').read_text(), 'old')
            self.assertTrue(new.is_dir()); self.assertFalse(result['private_state_edited_by_updater'])
            self.assertEqual(result['model_calls'], 0)
            self.assertTrue((config / 'upgrade-history' / ('branch-intent-' + new_sha + '.json')).is_file())
            self.assertTrue((config / 'upgrade-history' / ('branch-result-' + new_sha + '.json')).is_file())
            if mode == 'success': self.assertEqual(result['status'], 'upgraded'); self.assertEqual(os.readlink(source / 'current'), str(new))
            elif mode == 'rollback': self.assertEqual(result['status'], 'rolled_back'); self.assertEqual(os.readlink(source / 'current'), str(old))
            else:
                self.assertEqual(result['status'], 'rollback_failed')
                self.assertEqual([x for x in calls if x[0] == 'switch'], [('switch', new_sha)])

    def test_activation_keeps_prior_release_and_immutable_history(self): self._activation('success')
    def test_failed_startup_rolls_back_and_preserves_failed_release(self): self._activation('rollback')
    def test_unexpected_current_link_is_not_blindly_replaced(self): self._activation('unknown_link')
    def test_existing_release_or_changed_preflight_reject_before_stop(self):
        self._activation('existing'); self._activation('changed')


if __name__ == '__main__':
    unittest.main(verbosity=2)

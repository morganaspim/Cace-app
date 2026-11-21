"""Generator checks use explicit synthetic evidence and never emit runnable YAML."""
import ast
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import build_handoff_workflow as build
from test_handoff_request import installed


def runtime_fixture():
    manifest=build.controller.canonical({'schema':'merlin-browser-runtime/1','expert_source_commit':'b'*40,
        'files':[{'path':'python/merlin/synthetic.py','bytes':2,'sha256':build.controller.digest(b'x\n')}]})
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        for name,raw in (('manifest.json',manifest),('python/merlin/synthetic.py',b'x\n')):
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));archive.writestr(info,raw)
    return output.getvalue(),manifest


def fixture():
    pins=installed()
    runtime,manifest=runtime_fixture()
    pins['runtime_sha256']=build.controller.digest(runtime)
    pins['runtime_manifest_sha256']=build.controller.digest(manifest)
    executable={'path':'/usr/lib64/chromium-browser/headless_shell','bytes':100,'sha256':'d'*64}
    host={'schema':'merlin-browser-host/1','release':'/opt/merlin-public-browser/releases/'+pins['runtime_sha256'],
        'browser_uid':pins['browser_uid'],'browser_gid':pins['browser_gid'],'executable':executable['path'],
        'executable_sha256':executable['sha256'],'runtime_manifest_sha256':pins['runtime_manifest_sha256']}
    pins['host_config_sha256']=build.controller.digest(build.controller.canonical(host))
    receipt={'schema':'merlin-browser-bootstrap/1','status':'installed_native_passed',
        'public_episode_acceptance':'passed','runtime_pin':{
            **build.identity(runtime),'expert_source_commit':pins['expert_source_commit']},
        'native_executable':executable,
        'execution':{'run_id':pins['bootstrap_run_id'],'workflow_commit':pins['bootstrap_workflow_commit']},
        'fixture':{'status':'succeeded','all_workers_stopped':True,'scratch_unmounted':True},
        'fixture_observation':{'status':'succeeded','playwright':'1.60.0','chromium':'156.0.8078.79',
                               'chromium_sandbox':True},
        'native_acceptance':{'schema':'merlin-browser-native-acceptance/1','status':'passed',
            'caller_uid':982,'caller_gid':pins['opc_gid'],'max_public_episodes':3,'parallel_episodes':1,
            'model_calls':0,'external_spend_usd':0,'unauthorized_peer':{'uid':1000,'status':'denied'},
            'post_restart_read':{'unchanged':True,'new_acquisition':False},
            'public_cases':[{'id':name,'acceptance':True,'submit_status':'completed','document_status':200}
                            for name in ('database-arxiv','news-nasa','repository-openmdao')]},
        'service_config_sha256':pins['service_config_sha256'],'unit_sha256':pins['unit_sha256'],
        'accounts':{name:pins[name] for name in ('browser_uid','browser_gid','opc_gid')},
        'before':{'synthetic_fixture':True},'after':{'synthetic_fixture':True},
        'model_calls':0,'external_model_cost_usd':0,'qualification':False,'promotion_authority':False}
    return pins,receipt


def package(pins,receipt,second=False):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as archive:
        archive.writestr('root-evidence/bootstrap-evidence/operation-receipt.json',build.controller.canonical(receipt))
        archive.writestr('runtime.zip',runtime_fixture()[0])
        if second: archive.writestr('other/bootstrap-evidence/operation-receipt.json',build.controller.canonical(receipt))
    raw=data.getvalue()
    api={'run':{'id':pins['bootstrap_run_id'],'run_attempt':1,'head_sha':pins['bootstrap_workflow_commit'],
        'status':'completed','conclusion':'success','repository':{'full_name':'morganaspim/Cace-app'}},
        'jobs':{'total_count':1,'jobs':[{'run_id':pins['bootstrap_run_id'],'status':'completed','conclusion':'success'}]},
        'artifacts':{'total_count':1,'artifacts':[{'id':1234,'digest':'sha256:'+build.controller.digest(raw),
            'size_in_bytes':len(raw),'expired':False,'workflow_run':{'id':pins['bootstrap_run_id']}}]}}
    return api,raw


class WorkflowGeneratorControls(unittest.TestCase):
    def test_missing_actual_installation_inputs_create_no_source_or_yaml(self):
        with tempfile.TemporaryDirectory() as temporary,patch.object(build,'ROOT',Path(temporary)),\
             patch.object(sys,'argv',['build','--product-source','/missing','--program','/missing']),\
             patch.object(build,'prepare_bundle') as prepare:
            with self.assertRaisesRegex(build.controller.OperationError,'actual accepted installation'):
                build.main()
            prepare.assert_not_called()
            self.assertEqual(list(Path(temporary).iterdir()),[])

    def test_prepare_only_does_not_render_workflow(self):
        with tempfile.TemporaryDirectory() as temporary,patch.object(build,'ROOT',Path(temporary)),\
             patch.object(sys,'argv',['build','--product-source','/missing','--program','/missing','--prepare-only']),\
             patch.object(build,'prepare_bundle',return_value=({'synthetic':True},{'synthetic':True})),\
             patch.object(build,'render_workflow') as render,patch('sys.stdout',new=io.StringIO()) as output:
            build.main()
            render.assert_not_called()
            self.assertFalse(json.loads(output.getvalue())['workflow_emitted'])
            self.assertEqual(list(Path(temporary).rglob('*.yml')),[])

    def test_complete_synthetic_acceptance_binds_exact_raw_identity_only(self):
        pins,receipt=fixture();api,raw=package(pins,receipt)
        value=build.accepted_installation(pins,api,raw)
        self.assertEqual(value['artifact_sha256'],build.controller.digest(raw))
        self.assertEqual(value['receipt_sha256'],build.controller.digest(build.controller.canonical(receipt)))
        self.assertEqual(value['artifact_id'],1234)

    def test_successful_run_cannot_admit_failed_or_incomplete_native_receipt(self):
        pins,receipt=fixture()
        for status in ('failed','started','installed_source_acceptance_incomplete'):
            changed={**receipt,'status':status};api,raw=package(pins,changed)
            with self.subTest(status=status),self.assertRaises(build.controller.OperationError):
                build.accepted_installation(pins,api,raw)

    def test_partial_public_sources_and_reacquiring_restart_are_rejected(self):
        pins,receipt=fixture()
        for change in ({'public_cases':receipt['native_acceptance']['public_cases'][:2]},
                       {'post_restart_read':{'unchanged':True,'new_acquisition':True}},
                       {'caller_uid':1000},{'unauthorized_peer':{'uid':1000,'status':'completed'}}):
            updated={**receipt,'native_acceptance':{**receipt['native_acceptance'],**change}};api,raw=package(pins,updated)
            with self.subTest(change=change),self.assertRaises(build.controller.OperationError):
                build.accepted_installation(pins,api,raw)

    def test_unsandboxed_fixture_or_live_workers_are_rejected(self):
        pins,receipt=fixture()
        for change in ({'fixture_observation':{**receipt['fixture_observation'],'chromium_sandbox':False}},
                       {'fixture':{**receipt['fixture'],'all_workers_stopped':False}},
                       {'fixture':{**receipt['fixture'],'scratch_unmounted':False}}):
            api,raw=package(pins,{**receipt,**change})
            with self.subTest(change=change),self.assertRaises(build.controller.OperationError):
                build.accepted_installation(pins,api,raw)

    def test_expired_wrong_digest_or_wrong_run_artifact_is_rejected(self):
        pins,receipt=fixture()
        for change in ({'expired':True},{'digest':'sha256:'+'0'*64},{'workflow_run':{'id':124}},{'size_in_bytes':0}):
            api,raw=package(pins,receipt);api['artifacts']['artifacts'][0].update(change)
            with self.subTest(change=change),self.assertRaises(build.controller.OperationError):
                build.accepted_installation(pins,api,raw)

    def test_incomplete_or_failed_jobs_and_wrong_commit_are_rejected(self):
        pins,receipt=fixture()
        for which in ('jobs_missing','job_failed','run_failed','commit'):
            api,raw=package(pins,receipt)
            if which=='jobs_missing': api['jobs']['total_count']=2
            if which=='job_failed': api['jobs']['jobs'][0]['conclusion']='failure'
            if which=='run_failed': api['run']['conclusion']='failure'
            if which=='commit': api['run']['head_sha']='d'*40
            with self.subTest(which=which),self.assertRaises(build.controller.OperationError):
                build.accepted_installation(pins,api,raw)

    def test_changed_account_or_preservation_snapshot_is_rejected(self):
        pins,receipt=fixture()
        for change in ({'accounts':{**receipt['accounts'],'browser_uid':981}},
                       {'after':{'synthetic_fixture':False}},{'before':None,'after':None},
                       {'model_calls':1},{'promotion_authority':True}):
            api,raw=package(pins,{**receipt,**change})
            with self.subTest(change=change),self.assertRaises(build.controller.OperationError):
                build.accepted_installation(pins,api,raw)

    def test_ambiguous_receipt_inventory_is_rejected(self):
        pins,receipt=fixture();api,raw=package(pins,receipt,second=True)
        with self.assertRaises(build.controller.OperationError): build.accepted_installation(pins,api,raw)

    def test_valid_shape_but_unbound_host_digest_is_rejected(self):
        pins,receipt=fixture();api,raw=package(pins,receipt)
        pins['host_config_sha256']='f'*64
        with self.assertRaisesRegex(build.controller.OperationError,'host configuration pin'):
            build.accepted_installation(pins,api,raw)

    def test_valid_shape_but_unbound_runtime_manifest_digest_is_rejected(self):
        pins,receipt=fixture();api,raw=package(pins,receipt)
        pins['runtime_manifest_sha256']='f'*64
        with self.assertRaisesRegex(build.controller.OperationError,'runtime manifest pin'):
            build.accepted_installation(pins,api,raw)

    def test_composed_wrapper_and_root_argument_parse_without_emitting_yaml(self):
        product=build.controller.decode((build.OPS/'handoff_product_pins.json').read_bytes())
        workflow,pins,count=build.render_workflow(product,{'synthetic':True},installed(),{'synthetic':True})
        self.assertEqual(count,24)
        lines=workflow.splitlines();start=lines.index("          python3 - <<'PYCODE'")+1
        stop=lines.index('          PYCODE',start)
        wrapper='\n'.join(line[10:] for line in lines[start:stop]);tree=ast.parse(wrapper,feature_version=(3,9))
        # Execute only the actual generated assignments that compose the root -c argument.
        assignments=[]
        for node in ast.walk(tree):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target] if isinstance(node,ast.AugAssign) else []
            if any(isinstance(target,ast.Name) and target.id=='root_code' for target in targets): assignments.append(node)
        self.assertEqual(len(assignments),7)
        context={'support':(build.OPS/'handoff_support.py').read_bytes(),
            'source':(build.OPS/'handoff_request.py').read_bytes(),'source_pins':pins,
            'request':{'synthetic':True},'execution':{'synthetic':True},'installed':installed(),'product':product,
            'source_dir':Path('/synthetic/sources'),'out':Path('/synthetic/output')}
        fragment=ast.Module(body=assignments,type_ignores=[]);ast.fix_missing_locations(fragment)
        exec(compile(fragment,'actual-root-argument-composition','exec'),context)
        ast.parse(context['root_code'],feature_version=(3,9))
        self.assertLess(len(context['root_code'].encode()),115000)
        self.assertNotIn('--pipe',wrapper)
        self.assertIn('--property=PrivateNetwork=yes',wrapper)
        self.assertIn('--property=RestrictAddressFamilies=AF_UNIX',wrapper)


if __name__=='__main__': unittest.main()

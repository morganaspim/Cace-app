"""Focused local/native controls; synthetic fixtures never touch live registries."""
from copy import deepcopy
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import handoff_request as route
import handoff_support as support


def installed():
    return {'schema':'merlin-browser-installed-operation-pins/1',
        **{key:'a'*64 for key in ('runtime_sha256','runtime_manifest_sha256','host_config_sha256','service_config_sha256','unit_sha256')},
        'browser_uid':980,'browser_gid':980,'opc_gid':1000,'expert_source_commit':'b'*40,
        'bootstrap_run_id':123,'bootstrap_workflow_commit':'c'*40}


def stopped_fixture():
    actions=route.canonical([{'action':'open','url':'https://example.org/'}])
    manifest=route.canonical({'schema':'merlin-public-browser-episode/1','episode_id':'saved',
        'status':'completed','limits':{'wall_seconds':60}})
    receipt={'schema':'merlin-browser-launch/1','episode_id':'saved','release':'/release',
        'status':'succeeded','all_workers_stopped':True,'scratch_unmounted':True,
        'model_calls':0,'external_model_cost_usd':0,'qualification':False,'promotion_authority':False,
        'limits':{'wall_seconds':60},'actions_sha256':route.digest(actions),
        'unit_shutdown':{role:{'ActiveState':'inactive','MainPID':'0'} for role in ('broker','renderer')},
        'output':{'files':[{'path':'episode.json','bytes':len(manifest),'sha256':route.digest(manifest)}]}}
    return receipt,manifest,actions


class HandoffControls(unittest.TestCase):
    def setUp(self):
        self.request={'schema':'merlin-browser-handoff-operation-request/1',
            'request_id':'5320c4b2-ac45-4bde-a939-53ba9cbd0037','operation':'submit',
            'created_at':'2026-11-21T00:00:00Z','arguments':{'episode_id':'saved',
                'launch_receipt_sha256':'d'*64,'publication_ref':{'schema':'merlin-artifact-ref/1',
                'project_id':'merlin-browser-research','logical_path':'browser/episodes/saved/publication.json',
                'version':1,'sha256':'e'*64}}}

    def test_submit_uses_fixed_project_and_derived_handoff_identity(self):
        value=route.operation_request(self.request)
        self.assertEqual(value['request_id'],self.request['request_id'])
        self.assertEqual(set(value),{'schema','request_id','episode_id','publication_ref'})

    def test_no_url_command_registry_provider_or_budget_request(self):
        for key in ('url','actions','command','registry_root','project_id','provider','budget','source_commit'):
            with self.subTest(key=key),self.assertRaises(route.OperationError):
                route.operation_request({**self.request,'arguments':{**self.request['arguments'],key:'unaccepted'}})

    def test_exact_top_level_fields_and_operations(self):
        with self.assertRaises(route.OperationError): route.operation_request({**self.request,'shell':'x'})
        for name in ('install','browse','run','read','deploy'):
            with self.assertRaises(route.OperationError): route.operation_request({**self.request,'operation':name})

    def test_status_accepts_only_an_existing_handoff_identity(self):
        value={**self.request,'operation':'status','arguments':{'handoff_request_id':self.request['request_id']}}
        self.assertEqual(route.operation_request(value),{'operation':'status','request_id':self.request['request_id']})
        with self.assertRaises(route.OperationError):
            route.operation_request({**value,'arguments':{'handoff_request_id':self.request['request_id'],'episode_id':'saved'}})

    def test_cross_project_changed_path_and_revised_ref_are_rejected(self):
        for field,value in (('project_id','private'),('logical_path','research/private.json'),('version',2),('version',True)):
            request=deepcopy(self.request);request['arguments']['publication_ref'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(route.OperationError): route.operation_request(request)

    def test_request_uuid_and_episode_are_safe(self):
        for identifier in ('../escape','unknown','5320C4B2-AC45-4BDE-A939-53BA9CBD0037'):
            with self.assertRaises((ValueError,route.OperationError)):
                route.operation_request({**self.request,'request_id':identifier})
        request=deepcopy(self.request);request['arguments']['episode_id']='../../private'
        with self.assertRaises(route.OperationError): route.operation_request(request)

    def test_prior_submit_intent_always_becomes_status(self):
        self.assertEqual(route.effective_operation('submit',False),'submit')
        self.assertEqual(route.effective_operation('submit',True),'status')
        for prior in (True,False): self.assertEqual(route.effective_operation('status',prior),'status')

    def test_actual_installed_pin_shape_rejects_pending_and_boolean_ids(self):
        pins=installed();route.validate_installed(pins)
        for field,value in (('runtime_sha256','pending'),('browser_uid',0),('browser_uid',982),('bootstrap_run_id',True)):
            with self.assertRaises(route.OperationError): route.validate_installed({**pins,field:value})

    def test_product_requires_exact_dependency_closure_and_native23(self):
        pins=json.loads((Path(__file__).parent/'handoff_product_pins.json').read_bytes())
        route.validate_product(pins)
        for change in ({'native_test_count':22},{'private_dependencies':pins['private_dependencies'][:-1]},
                       {'private_dependencies':pins['private_dependencies']+[pins['private_dependencies'][0]]}):
            with self.assertRaises(route.OperationError): route.validate_product({**pins,**change})

    def test_source_bytes_and_git_identity_are_both_checked(self):
        raw=b'fixed source\n';pin={'bytes':len(raw),'sha256':route.digest(raw),'git_blob':'0'*40}
        with self.assertRaisesRegex(route.OperationError,'Git blob'): route.check_bytes(raw,pin)
        pin.pop('git_blob');route.check_bytes(raw,pin)
        with self.assertRaises(route.OperationError): route.check_bytes(raw+b'x',pin)

    def test_exact_completed_stopped_real_episode_is_admitted(self):
        receipt,manifest,actions=stopped_fixture();raw=route.canonical(receipt)
        answer=route.admit_receipt(receipt,'saved',Path('/release'),route.digest(raw),raw,manifest,actions)
        self.assertEqual(answer['status'],'completed')

    def test_live_or_unmounted_or_failed_episode_is_rejected(self):
        original,manifest,actions=stopped_fixture()
        for change in ({'all_workers_stopped':False},{'scratch_unmounted':False},{'status':'failed'},
                       {'release':'/other'},{'fixture_command':['synthetic']},{'model_calls':1}):
            value={**original,**change};raw=route.canonical(value)
            with self.subTest(change=change),self.assertRaises(route.OperationError):
                route.admit_receipt(value,'saved',Path('/release'),route.digest(raw),raw,manifest,actions)

    def test_both_actual_worker_shutdown_records_are_required(self):
        original,manifest,actions=stopped_fixture()
        for shutdown in ({}, {'broker':original['unit_shutdown']['broker']},
                         {**original['unit_shutdown'],'renderer':{'ActiveState':'active','MainPID':'42'}}):
            value={**original,'unit_shutdown':shutdown};raw=route.canonical(value)
            with self.assertRaises(route.OperationError):
                route.admit_receipt(value,'saved',Path('/release'),route.digest(raw),raw,manifest,actions)

    def test_rehashed_receipt_cannot_change_exact_stopped_output_manifest(self):
        receipt,manifest,actions=stopped_fixture();raw=route.canonical(receipt)
        with self.assertRaisesRegex(route.OperationError,'manifest binding'):
            route.admit_receipt(receipt,'saved',Path('/release'),route.digest(raw),raw,manifest+b' ',actions)
        with self.assertRaisesRegex(route.OperationError,'action bytes'):
            route.admit_receipt(receipt,'saved',Path('/release'),route.digest(raw),raw,manifest,actions+b' ')

    def test_unknown_result_or_invented_domain_execution_is_rejected(self):
        with self.assertRaises(route.OperationError): route.check_response({'status':'succeeded','execution_retried':False})
        value={'status':'recorded','execution_retried':False,'result':{'schema':'merlin-browser-research-handoff-result/1',
            'domain_execution':'not_run','new_browser_calls':0,'model_calls':0,'external_model_cost_usd':0,
            'qualification':False,'promotion_authority':False}}
        route.check_response(value)
        for field,item in (('domain_execution','completed'),('new_browser_calls',1),('promotion_authority',True)):
            with self.assertRaises(route.OperationError): route.check_response({**value,'result':{**value['result'],field:item}})

    def test_incomplete_status_is_never_a_completed_result(self):
        for status in ('reconciliation_needed','not_found'):
            self.assertEqual(route.check_response({'status':status,'execution_retried':False}),status)

    def test_native_test_gate_requires23_and_no_skips(self):
        pins={'source_commit':'a'*40}
        answer={'tests':23,'errors':0,'failures':0,'skips':0,'uid':1000}
        with patch.object(route,'command',return_value=route.canonical(answer)):
            self.assertEqual(route.product_child(Path('/private'),Path('/stage'),pins,'tests','',Path('/log'),runner_gid=1000),answer)
        for change in ({'tests':22},{'skips':1},{'failures':1},{'uid':0}):
            with patch.object(route,'command',return_value=route.canonical({**answer,**change})),self.assertRaises(route.OperationError):
                route.product_child(Path('/private'),Path('/stage'),pins,'tests','',Path('/log'),runner_gid=1000)

    def test_fresh_process_readback_requires_a_different_root_pid(self):
        for value in ({'pid':os.getpid(),'uid':0},{'pid':os.getpid()+1,'uid':1000}):
            with patch.object(route,'command',return_value=route.canonical(value)),self.assertRaises(route.OperationError):
                route.product_child(Path('/private'),Path('/stage'),{'source_commit':'a'*40},'status','id',Path('/log'),runner_gid=1000)

    def test_regular_file_reader_refuses_fifo_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);os.mkfifo(root/'fifo');(root/'file').write_bytes(b'public');(root/'link').symlink_to(root/'file')
            with self.assertRaises(route.OperationError): support.read(root/'fifo',100,root=False)
            with self.assertRaises(OSError): support.read(root/'link',100,root=False)

    def test_duplicate_json_and_nonfinite_values_are_rejected(self):
        for raw in ('{"value":1,"value":2}','{"value":NaN}'):
            with self.assertRaises(route.OperationError): route.decode(raw)

    def test_absolute_deadline_kills_group_after_direct_parent_exited(self):
        with tempfile.TemporaryDirectory() as directory:
            log=Path(directory)/'deadline.txt';calls=[];kill=support.os.killpg
            child="import subprocess,sys;subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'])"
            def observed(pid,signum): calls.append((pid,signum));return kill(pid,signum)
            with patch.object(support.os,'killpg',side_effect=observed),self.assertRaises(route.OperationError):
                support.command([sys.executable,'-c',child],log,seconds=.25)
            self.assertTrue(any(signum==signal.SIGKILL for _,signum in calls))
            self.assertEqual(json.loads(Path(str(log)+'.json').read_bytes())['error_type'],'OperationError')


class AnchoredPublicationControls(unittest.TestCase):
    def test_publication_anchors_writes_if_runner_replaces_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir()
            (source/'nested').mkdir();(source/'nested'/'capture').write_bytes(b'public evidence')
            parent=root/'output';parent.mkdir(mode=0o700)
            destination=parent/'operation';retained=parent/'retained';outside=root/'outside';outside.mkdir()
            original_mkdir=os.mkdir;original_read=support.read;original_fstat=os.fstat;replaced=False;calls=0
            def root_target(descriptor):
                nonlocal calls
                info=original_fstat(descriptor)
                calls+=1
                if calls<=2:
                    return SimpleNamespace(st_uid=1000 if calls==1 else 0,
                        st_mode=info.st_mode,st_dev=info.st_dev,st_ino=info.st_ino)
                return info
            def replace_after_open(path,*args,**kwargs):
                nonlocal replaced
                if path=='nested' and kwargs.get('dir_fd') is not None and not replaced:
                    replaced=True;destination.rename(retained);destination.symlink_to(outside,target_is_directory=True)
                return original_mkdir(path,*args,**kwargs)
            with patch.object(support,'root_directory',side_effect=lambda path,**kwargs:Path(path)), \
                 patch.object(support,'read',side_effect=lambda path,maximum:original_read(path,maximum,root=False)), \
                 patch.object(support.os,'fchown'),patch.object(support.os,'fstat',side_effect=root_target), \
                 patch.object(support.os,'mkdir',side_effect=replace_after_open):
                with self.assertRaisesRegex(support.OperationError,'destination moved'):
                    support.publish_evidence(source,destination)
            self.assertTrue(replaced)
            self.assertEqual(list(outside.iterdir()),[])
            self.assertEqual((retained/'nested'/'capture').read_bytes(),b'public evidence')

    def test_publication_rejects_preexisting_parent_symlink_before_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir()
            (source/'capture').write_bytes(b'public evidence')
            outside=root/'outside';outside.mkdir();(root/'output').symlink_to(outside,target_is_directory=True)
            with patch.object(support,'root_directory',side_effect=lambda path,**kwargs:Path(path)):
                with self.assertRaises(OSError): support.publish_evidence(source,root/'output'/'operation')
            self.assertEqual(list(outside.iterdir()),[])

    def test_publication_reports_parent_rename_as_delivery_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir()
            (source/'capture').write_bytes(b'public evidence')
            parent=root/'output';parent.mkdir(mode=0o700);retained=root/'retained-parent'
            original_mkdir=os.mkdir;original_read=support.read;original_fstat=os.fstat;calls=0;replaced=False
            def controlled_owner(descriptor):
                nonlocal calls
                info=original_fstat(descriptor);calls+=1
                if calls<=2:
                    return SimpleNamespace(st_uid=1000 if calls==1 else 0,
                        st_mode=info.st_mode,st_dev=info.st_dev,st_ino=info.st_ino)
                return info
            def replace_parent(path,*args,**kwargs):
                nonlocal replaced
                if path=='operation' and kwargs.get('dir_fd') is not None and not replaced:
                    replaced=True;parent.rename(retained);original_mkdir(parent,mode=0o700)
                return original_mkdir(path,*args,**kwargs)
            with patch.object(support,'root_directory',side_effect=lambda path,**kwargs:Path(path)), \
                 patch.object(support,'read',side_effect=lambda path,maximum:original_read(path,maximum,root=False)), \
                 patch.object(support.os,'fchown'),patch.object(support.os,'fstat',side_effect=controlled_owner), \
                 patch.object(support.os,'mkdir',side_effect=replace_parent):
                with self.assertRaisesRegex(support.OperationError,'parent moved'):
                    support.publish_evidence(source,parent/'operation')
            self.assertTrue(replaced)
            self.assertEqual(list(parent.iterdir()),[])
            self.assertEqual((retained/'operation'/'capture').read_bytes(),b'public evidence')


if __name__=='__main__': unittest.main(verbosity=2)

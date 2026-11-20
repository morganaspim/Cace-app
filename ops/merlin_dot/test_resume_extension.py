"""Readiness and reconciled resume controls; no real service mutations."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import resume_branch as r

GOOD = {'ok':True,'qualification':False,'promotion_authority':False,
        'result':{'transport':'unix','public_listener':False}}

class ReadinessControls(unittest.TestCase):
    def setUp(self):
        n={};exec(r.HEALTH_WAIT,n);self.poll=n['await_health'];self.now=0
    def clock(self):return self.now
    def sleep(self,seconds):self.now+=seconds
    def test_ready_immediately(self):
        self.assertEqual(self.poll(lambda:GOOD,self.clock,self.sleep)['attempts'],1)
    def test_delayed_socket_then_refused_then_ready(self):
        replies=[FileNotFoundError(),ConnectionRefusedError(),GOOD]
        def call():
            value=replies.pop(0)
            if isinstance(value,Exception):raise value
            return value
        result=self.poll(call,self.clock,self.sleep)
        self.assertEqual(result,{'attempts':3,'elapsed_seconds':0.4})
    def test_deadline_terminates(self):
        def absent():raise FileNotFoundError()
        with self.assertRaises(TimeoutError):self.poll(absent,self.clock,self.sleep,seconds=0.5)
        self.assertLessEqual(self.now,0.5)
    def test_permission_failure_never_retried(self):
        def denied():raise PermissionError()
        with self.assertRaises(PermissionError):self.poll(denied,self.clock,self.sleep)
        self.assertEqual(self.now,0)
    def test_bad_health_never_retried(self):
        for bad in ({**GOOD,'ok':False},{**GOOD,'qualification':True},{**GOOD,'promotion_authority':True},
                    {**GOOD,'result':{'transport':'tcp','public_listener':False}},
                    {**GOOD,'result':{'transport':'unix','public_listener':True}}):
            with self.subTest(bad=bad):
                with self.assertRaises(RuntimeError):self.poll(lambda:bad,self.clock,self.sleep)
                self.assertEqual(self.now,0)
    def test_subprocess_error_keeps_stderr_not_command(self):
        e=subprocess.CalledProcessError(1,['sensitive-command'],stderr='FileNotFoundError: socket not ready')
        self.assertEqual(r.error_details(e),{'class':'CalledProcessError','returncode':1,'stderr':'FileNotFoundError: socket not ready'})

class ResumeControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.source=root/'source';self.source.mkdir()
        (self.source/'releases').mkdir();self.old=self.source/'releases'/r.BASE_SHA;self.old.mkdir()
        self.new=self.source/'releases'/r.RESUME_SHA;self.new.mkdir()
        (self.source/'current').symlink_to(self.old)
        self.config=root/'etc'/'config.json';self.config.parent.mkdir();self.config.write_text('unchanged')
        self.history=self.config.parent/'upgrade-history';self.history.mkdir()
        self.old_manifest={'schema':'merlin-dot-release/1','source_repository':'Mannyspiro/expert-robot','source_base_commit':'c'*40,'files':{'old.py':'a'*64}}
        (self.old/'manifest.json').write_text(json.dumps(self.old_manifest))
        self.new_manifest={**self.old_manifest,'files':{**self.old_manifest['files'],**r.ADDITIONS}}
        self.prior={'status':'rollback_failed','new_bundle_sha256':r.RESUME_SHA,'expert_source_commit':r.EXPERT_COMMIT,'additions':r.ADDITIONS,'old':{'config_sha256':'d'*64,'release_sha256':r.BASE_SHA}}
        self.prior_path=self.history/('branch-result-'+r.RESUME_SHA+'.json');self.prior_path.write_text(json.dumps(self.prior))
        self.bundle=root/'bundle.zip';self.bundle.write_bytes(b'fixture');self.actions=[]
        def switch(target,expected,token):
            if os.readlink(self.source/'current')!=str(expected):raise RuntimeError('lease')
            link=self.source/token;link.symlink_to(target);os.replace(link,self.source/'current')
        def write(path,raw):
            with path.open('xb') as stream:stream.write(raw)
        self.g={'SOURCE':self.source,'CONFIG':self.config,'_root_directory':lambda p:None,
            '_regular':lambda p,**kw:Path(p).read_bytes(),'_verify_release':lambda *args:None,
            '_new_file':write,'_systemctl':self.actions.append,'_switch':switch,'_wait_active':lambda:None}
        for name,value in [('snapshot',{'config_sha256':'d'*64}),('ready_probe',{'health':True}),('library_probe',{'import':True})]:
            control=patch.object(r,name,return_value=value);control.start();self.addCleanup(control.stop)
        original=os.fstat
        def root_stat(fd):
            values=list(original(fd));values[4]=0;return os.stat_result(values)
        control=patch.object(r.os,'fstat',side_effect=root_stat);control.start();self.addCleanup(control.stop)
    def unpack(self,raw,digest,destination):
        destination.mkdir();(destination/'manifest.json').write_text(json.dumps(self.new_manifest));return self.new_manifest
    def resume(self):return r.activate(self.g,self.unpack,str(self.bundle),r.RESUME_SHA,'e'*64,'d'*64)
    def test_reconciled_resume_preserves_history_and_configuration(self):
        before=self.prior_path.read_bytes();result=self.resume()
        self.assertEqual(result['status'],'upgraded');self.assertEqual(os.readlink(self.source/'current'),str(self.new))
        self.assertEqual(self.prior_path.read_bytes(),before);self.assertEqual(self.config.read_text(),'unchanged')
        self.assertEqual(self.actions,['stop','restart'])
    def test_bad_prior_attempt_rejected(self):
        self.prior['status']='upgraded';self.prior_path.write_text(json.dumps(self.prior))
        with self.assertRaisesRegex(RuntimeError,'prior attempt'):self.resume()
        self.assertEqual(self.actions,[])
    def test_existing_resume_rejected(self):
        (self.history/('branch-resume-intent-'+r.RESUME_SHA+'.json')).write_text('{}')
        with self.assertRaisesRegex(RuntimeError,'already attempted'):self.resume()
        self.assertEqual(self.actions,[])
    def test_failed_baseline_health_prevents_mutation(self):
        with patch.object(r,'ready_probe',side_effect=RuntimeError('baseline not healthy')):
            with self.assertRaises(RuntimeError):self.resume()
        self.assertEqual(self.actions,[])
    def test_new_health_failure_rolls_back_with_evidence(self):
        with patch.object(r,'ready_probe',side_effect=[{'health':True},RuntimeError('new health rejected'),{'health':True}]):result=self.resume()
        self.assertEqual(result['status'],'rolled_back');self.assertEqual(os.readlink(self.source/'current'),str(self.old))
        self.assertEqual(result['error']['message'],'new health rejected')
    def test_post_switch_failure_restores_original(self):
        original=self.g['_switch']
        def failing(target,expected,token):
            original(target,expected,token)
            if target==self.new:raise OSError('fsync fault')
        self.g['_switch']=failing;result=self.resume()
        self.assertEqual(result['status'],'rolled_back');self.assertEqual(os.readlink(self.source/'current'),str(self.old))
    def test_changed_package_rejected(self):
        self.new_manifest['files']['old.py']='f'*64
        with self.assertRaises(ValueError):self.resume()
        self.assertEqual(self.actions,[])
    def test_wrong_release_refused(self):
        with self.assertRaises(ValueError):r.activate(self.g,self.unpack,str(self.bundle),'f'*64,'e'*64,'d'*64)
        self.assertEqual(self.actions,[])

if __name__=='__main__':unittest.main()

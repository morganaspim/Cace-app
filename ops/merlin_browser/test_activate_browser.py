"""Focused activation controls; no host service, browser or package action."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import activate_browser as A


class ActivationControls(unittest.TestCase):
    def setUp(self):
        self.request={'schema':'merlin-browser-runtime-request/1','request_id':'71a0bc69-6c7e-41ca-97be-baa046e3a72d',
            'operation':A.OPERATION,'created_at':'2026-11-21T20:25:00Z'}
        self.execution={'repository':'morganaspim/Cace-app','ref':'refs/heads/merlin/browser-operations-20261121',
            'runner':'cace-oci-a1','run_id':123,'run_attempt':1,'workflow_commit':'a'*40}

    def test_fixed_request_and_execution(self):
        A.validate_request(self.request,self.execution)
        for key in ('path','command','retry','fixture','model_calls'):
            with self.assertRaises(A.B.BootstrapError): A.validate_request({**self.request,key:'x'},self.execution)
        for key,value in (('operation','finish-loader-44944424850'),('request_id',A.OLD_REQUEST)):
            with self.assertRaises(A.B.BootstrapError): A.validate_request({**self.request,key:value},self.execution)
        for key,value in (('run_attempt',2),('runner','different'),('workflow_commit','main')):
            with self.assertRaises(A.B.BootstrapError): A.validate_request(self.request,{**self.execution,key:value})

    def test_exact_unit_delta_and_unchanged_limits(self):
        original=A.B.service_unit(A.RELEASE);self.assertEqual(hashlib.sha256(original).hexdigest(),A.OLD_UNIT)
        repaired=A.repaired_unit(original)
        removed=b'RuntimeDirectory=merlin-public-browser\nRuntimeDirectoryMode=0755\nRuntimeDirectoryPreserve=yes\n'
        pre=[line for line in repaired.splitlines(keepends=True) if line.startswith(b'ExecStartPre=')]
        self.assertEqual(len(pre),1)
        self.assertEqual(repaired.replace(pre[0],removed),original)
        self.assertIn(b'UMask=0077\n',repaired);self.assertIn(b'MemoryMax=256M\n',repaired)
        self.assertIn(b'CPUQuota=25%\n',repaired);self.assertIn(b'RestrictAddressFamilies=AF_UNIX\n',repaired)
        self.assertNotIn(b'RuntimeDirectory=',repaired)
        with self.assertRaises(A.B.BootstrapError): A.repaired_unit(original+b'\n')

    def run_parent(self,parent):
        # Same exact algorithm with current test UID/GID; pre-sudo host tests
        # must not ask for privilege. The production unit uses fixed0/1000.
        code='import os;os.umask(0o077);'+A.runtime_parent_code(parent,os.getuid(),os.getgid())
        return subprocess.run([sys.executable,'-I','-B','-c',code],capture_output=True,timeout=5)

    def test_parent_created_0755_under_inherited_0077(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);answer=self.run_parent(root)
            self.assertEqual(answer.returncode,0,answer.stderr.decode())
            info=(root/'merlin-public-browser').lstat()
            self.assertEqual((info.st_uid,info.st_gid,stat.S_IMODE(info.st_mode)),(os.getuid(),os.getgid(),0o755))

    def test_existing_parent_does_not_change_descendants(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);parent=root/'merlin-public-browser';parent.mkdir(mode=0o700)
            child=parent/'retained';child.mkdir(mode=0o700);leaf=child/'receipt';leaf.write_bytes(b'kept');leaf.chmod(0o600)
            before=(child.stat().st_mode,leaf.stat().st_mode,leaf.read_bytes())
            answer=self.run_parent(root);self.assertEqual(answer.returncode,0,answer.stderr.decode())
            self.assertEqual(before,(child.stat().st_mode,leaf.stat().st_mode,leaf.read_bytes()))
            self.assertEqual(stat.S_IMODE(parent.stat().st_mode),0o755)

    def test_parent_symlink_and_writable_leaf_rejected_without_target_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);outside=root/'outside';outside.mkdir(mode=0o700)
            leaf=root/'merlin-public-browser';leaf.symlink_to(outside,target_is_directory=True)
            answer=self.run_parent(root);self.assertNotEqual(answer.returncode,0)
            self.assertEqual(stat.S_IMODE(outside.stat().st_mode),0o700)
            leaf.unlink();leaf.mkdir(mode=0o777);leaf.chmod(0o777)
            answer=self.run_parent(root);self.assertNotEqual(answer.returncode,0)
            self.assertEqual(stat.S_IMODE(leaf.stat().st_mode),0o777)

    def test_parent_ancestor_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'actual';target.mkdir();link=root/'link';link.symlink_to(target,target_is_directory=True)
            answer=self.run_parent(link);self.assertNotEqual(answer.returncode,0)
            self.assertFalse((target/'merlin-public-browser').exists())

    def test_foreign_owner_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);leaf=root/'merlin-public-browser';leaf.mkdir(mode=0o700)
            code=A.runtime_parent_code(root,os.getuid()+1,os.getgid())
            with self.assertRaises(AssertionError): exec(code,{})
            self.assertEqual(stat.S_IMODE(leaf.stat().st_mode),0o700)

    def test_atomic_replace_readback_failure_can_restore_actual_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'host.json';old=b'old';new=b'new';target.write_bytes(old)
            real=A.B.regular
            with patch.object(A.B,'regular',side_effect=A.B.BootstrapError('readback failed')):
                with self.assertRaises(A.B.BootstrapError): A.atomic_replace(target,new,root/'next',0o600)
            self.assertEqual(target.read_bytes(),new)
            result=A.restore_after_attempt(target,old,hashlib.sha256(new).hexdigest(),root/'restore',0o600)
            self.assertTrue(result['restored']);self.assertEqual(target.read_bytes(),old)

    def test_unknown_replacement_preserved_for_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'unit';target.write_bytes(b'unknown')
            with self.assertRaises(A.B.BootstrapError):
                A.restore_after_attempt(target,b'old',hashlib.sha256(b'new').hexdigest(),root/'restore',0o644)
            self.assertEqual(target.read_bytes(),b'unknown');self.assertFalse((root/'restore').exists())

    def test_service_observations_are_fixed_and_bounded_on_command_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            calls=[]
            def fail(argv,path,**kwargs):
                calls.append((argv,kwargs));raise A.B.BootstrapError('observed failure')
            with patch.object(A.B,'command',side_effect=fail):
                result=A.observe_supervisor(Path(directory),'failed',1795292470)
            self.assertEqual(len(calls),2);self.assertIn('observation_error',result['commands']['journal'])
            for argv,kwargs in calls:
                self.assertEqual(kwargs['timeout'],5);self.assertEqual(kwargs['limit'],2097152)
                self.assertNotIn('--property=Environment',argv)
            self.assertIn('--unit=merlin-public-browser.service',calls[1][0])
            self.assertIn('--lines=512',calls[1][0])
            fields=next(v for v in calls[1][0] if v.startswith('--output-fields='))
            self.assertNotIn('_CMDLINE',fields)

    def test_stopped_state_required(self):
        A.require_inactive({'MainPID':'0','ControlGroup':'','ActiveState':'inactive'})
        for changes in ({'MainPID':'123'},{'ControlGroup':'/system.slice/live'},{'ActiveState':'active'}):
            with self.assertRaises(A.B.BootstrapError):
                A.require_inactive({'MainPID':'0','ControlGroup':'','ActiveState':'inactive',**changes})

    def test_separate_public_workers_must_be_stopped_before_failed_export(self):
        with tempfile.TemporaryDirectory() as directory:
            calls=[]
            def query(argv,path,**kwargs):
                calls.append(argv)
                if len(calls)==2: return b'MainPID=123\nActiveState=active\nControlGroup=/system.slice/live\n'
                return b'MainPID=0\nActiveState=inactive\nControlGroup=\n'
            with patch.object(A.B,'command',side_effect=query):
                result=A.public_workers_stopped(self.request['request_id'],Path(directory))
            self.assertEqual(len(calls),6);self.assertFalse(result['all_stopped'])
            self.assertTrue(any('observation_error' in row for row in result['units'].values()))
            for argv in calls: self.assertEqual(argv[1],'show')

    def test_separate_worker_query_failure_withholds_failed_export(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(A.B,'command',side_effect=A.B.BootstrapError('timeout')):
                result=A.public_workers_stopped(self.request['request_id'],Path(directory))
            self.assertFalse(result['all_stopped']);self.assertEqual(len(result['units']),6)

    def test_no_fixture_package_or_runtime_install_call(self):
        tree=ast.parse(Path(A.__file__).read_text());names=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                if isinstance(node.func,ast.Attribute): names.append(node.func.attr)
                elif isinstance(node.func,ast.Name): names.append(node.func.id)
        for forbidden in ('run_episode','continue_install','install','clone_venv','unpack_runtime'):
            self.assertNotIn(forbidden,names)
        self.assertEqual(names.count('native_acceptance'),1)
        self.assertEqual(A.OLD_RUN,44945790158)
        self.assertEqual(A.INSPECTION['run_id'],44946215856)


if __name__=='__main__': unittest.main(verbosity=2)

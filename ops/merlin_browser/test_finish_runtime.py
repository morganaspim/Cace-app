"""Focused gates for the observed loader repair and runtime-only successor."""
import ast
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import bootstrap_browser as B
import finish_runtime as F
import launch_episode as L


class RuntimeSuccessorControls(unittest.TestCase):
    def setUp(self):
        self.request={'schema':'merlin-browser-runtime-request/1','request_id':'3ec418ca-d02b-4db6-a634-32e2ed451887',
          'operation':F.OPERATION,'created_at':'2026-11-21T20:00:00Z'}
        self.execution={'repository':'morganaspim/Cace-app','ref':'refs/heads/merlin/browser-operations-20261121',
          'runner':'cace-oci-a1','run_id':1,'run_attempt':1,'workflow_commit':'a'*40}

    def test_fixed_request_and_first_attempt(self):
        F.validate_request(self.request,self.execution)
        for change in ({'operation':'bootstrap'},{'request_id':F.OLD_REQUEST},{'command':'arbitrary'}):
            with self.assertRaises(B.BootstrapError): F.validate_request({**self.request,**change},self.execution)
        with self.assertRaises(B.BootstrapError): F.validate_request(self.request,{**self.execution,'run_attempt':2})

    def test_loader_binding_covers_every_worker_without_directory_expansion(self):
        for network in (False,True):
            args=L.sandbox(Path('/release'),Path('/run/test'),980,980,network)
            mounts=[tuple(args[i+1:i+3]) for i,v in enumerate(args) if v=='--ro-bind']
            self.assertEqual(mounts.count((F.LOADER_PATH,F.LOADER_PATH)),1)
            self.assertNotIn(('/usr/lib','/usr/lib'),mounts)
            self.assertIn('--unshare-user',args);self.assertIn('--cap-drop',args)
        self.assertEqual(L.ELF_LOADER_SHA256,F.LOADER_SHA)

    def test_loader_hash_guard_is_part_of_runtime_validation(self):
        source=ast.parse(Path(L.__file__).read_text())
        load=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='load_runtime')
        guards=[n for n in ast.walk(load) if isinstance(n,ast.If)
                and 'ELF_LOADER_SHA256' in ast.unparse(n.test)]
        self.assertEqual(len(guards),1)
        self.assertTrue(any(isinstance(n,ast.Raise) for n in guards[0].body))

    def test_runtime_controller_has_no_package_mutation_entrypoint(self):
        tree=ast.parse(Path(F.__file__).read_text());calls=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='B':
                calls.add(node.func.attr)
        self.assertFalse(calls&{'install','continue_install','acquire','verify_signatures','install_stages'})
        text=Path(F.__file__).read_text()
        self.assertNotIn("'--install'",text);self.assertNotIn("'--import'",text);self.assertNotIn("'useradd'",text)

    def prior(self,change=None):
        rows=[{'name':'installed-'+str(i)} for i in range(971)]
        prior={'status':'failed','request':{'request_id':F.OLD_REQUEST},'execution':{'run_id':F.OLD_RUN,'workflow_commit':F.OLD_COMMIT},
          'rpm_install_completed':True,'package_stages_completed':['zvbi-library-only','remaining-dependencies'],
          'accounts':{'authorized_client_uid':982,'browser_gid':980,'browser_uid':980,'opc_gid':1000,'private_client_effective_group_verified':True},
          'before':{'preserved':True},'after_failure':{'preserved':True},'error':{'type':'LaunchError','message':'browser launch failed; preserved receipt and raw output'},
          'runtime_pin':{'sha256':F.OLD_RUNTIME},'package_failure_observation':{'installed_packages':rows}}
        if change: change(prior)
        raw=B.canonical(prior)
        return raw,B.digest(B.canonical(rows))

    def test_exact_installed_predecessor_is_required(self):
        raw,inventory=self.prior()
        with mock.patch.object(F,'OLD_RESULT',B.digest(raw)),mock.patch.object(F,'OLD_INVENTORY',inventory):
            self.assertEqual(F.prior_receipt(raw)['status'],'failed')
            with self.assertRaises(B.BootstrapError): F.prior_receipt(raw+b' ')

    def test_partial_install_or_private_drift_is_rejected(self):
        for change in (lambda x:x.update(rpm_install_completed=False),lambda x:x.update(package_stages_completed=['zvbi-library-only']),
                       lambda x:x.update(after_failure={'preserved':False}),lambda x:x['accounts'].update(browser_uid=0)):
            raw,inventory=self.prior(change)
            with mock.patch.object(F,'OLD_RESULT',B.digest(raw)),mock.patch.object(F,'OLD_INVENTORY',inventory):
                with self.assertRaises(B.BootstrapError): F.prior_receipt(raw)

    def metadata_as_root(self,path):
        info=os.lstat(path)
        return SimpleNamespace(st_mode=info.st_mode,st_uid=0)

    def test_venv_copy_retains_observed_relative_link_and_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'old';source.mkdir();(source/'lib').mkdir()
            (source/'lib64').symlink_to('lib',target_is_directory=True);(source/'lib/module.py').write_bytes(b'fixed\n')
            with mock.patch.object(B,'rooted',side_effect=lambda path,*args:Path(path)),mock.patch.object(Path,'lstat',new=lambda path:self.metadata_as_root(path)):
                result=F.clone_venv(source,root/'new',root/'ledger.json')
            self.assertEqual((root/'new/lib/module.py').read_bytes(),b'fixed\n')
            self.assertEqual(os.readlink(root/'new/lib64'),'lib');self.assertFalse(result['packages_installed'])

    def test_venv_copy_refuses_other_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'old';source.mkdir();(source/'escape').symlink_to('/etc',target_is_directory=True)
            with mock.patch.object(B,'rooted',side_effect=lambda path,*args:Path(path)),mock.patch.object(Path,'lstat',new=lambda path:self.metadata_as_root(path)):
                with self.assertRaisesRegex(B.BootstrapError,'unobserved venv'): F.clone_venv(source,root/'new',root/'ledger.json')

    def test_venv_copy_refuses_fifo_without_opening_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'old';source.mkdir();os.mkfifo(source/'fifo')
            with mock.patch.object(B,'rooted',side_effect=lambda path,*args:Path(path)),mock.patch.object(Path,'lstat',new=lambda path:self.metadata_as_root(path)):
                with self.assertRaisesRegex(B.BootstrapError,'unsafe venv member'): F.clone_venv(source,root/'new',root/'ledger.json')

    def test_venv_copy_ceiling_precedes_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'old';source.mkdir();(source/'file').write_bytes(b'x')
            with mock.patch.object(B,'rooted',side_effect=lambda path,*args:Path(path)),mock.patch.object(Path,'lstat',new=lambda path:self.metadata_as_root(path)),\
                 mock.patch.object(B,'identity',return_value={'bytes':385*1024*1024,'sha256':'a'*64}),mock.patch.object(B,'copy_verified') as copied:
                with self.assertRaisesRegex(B.BootstrapError,'venv copy ceiling'): F.clone_venv(source,root/'new',root/'ledger.json')
                copied.assert_not_called()

    def test_host_replacement_refuses_changed_previous_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'host.json').write_bytes(b'old')
            with mock.patch.object(B,'CONFIG',root),mock.patch.object(F,'checked_raw',side_effect=B.BootstrapError('changed')):
                with self.assertRaises(B.BootstrapError): F.replace_host(b'new','a'*64,root/'next.json')
            self.assertEqual((root/'host.json').read_bytes(),b'old');self.assertFalse((root/'next.json').exists())

    def test_atomic_host_replacement_keeps_original_for_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'host.json').write_bytes(b'old')
            with mock.patch.object(B,'CONFIG',root),mock.patch.object(F,'checked_raw',return_value=b'old'):
                old=F.replace_host(b'new','a'*64,root/'next.json')
            self.assertEqual(old,b'old');self.assertEqual((root/'host.json').read_bytes(),b'new')

    def test_replace_success_followed_by_readback_failure_is_restored_by_actual_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'host.json').write_bytes(b'old')
            with mock.patch.object(B,'CONFIG',root),mock.patch.object(F,'OLD_HOST',B.digest(b'old')):
                with mock.patch.object(F,'checked_raw',return_value=b'old'),\
                     mock.patch.object(B,'regular',side_effect=B.BootstrapError('readback failed')):
                    with self.assertRaisesRegex(B.BootstrapError,'readback failed'):
                        F.replace_host(b'new',B.digest(b'old'),root/'next.json')
                self.assertEqual((root/'host.json').read_bytes(),b'new')
                with mock.patch.object(F,'checked_raw',return_value=b'new'):
                    restored=F.restore_host_after_attempt(b'old',B.digest(b'new'),root/'restore.json')
                self.assertTrue(restored['previous_host_restored']);self.assertEqual((root/'host.json').read_bytes(),b'old')

    def test_restore_never_overwrites_an_unexpected_host_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'host.json').write_bytes(b'unexpected')
            with mock.patch.object(B,'CONFIG',root),mock.patch.object(F,'OLD_HOST',B.digest(b'old')):
                with self.assertRaisesRegex(B.BootstrapError,'needs reconciliation'):
                    F.restore_host_after_attempt(b'old',B.digest(b'new'),root/'restore.json')
            self.assertEqual((root/'host.json').read_bytes(),b'unexpected');self.assertFalse((root/'restore.json').exists())


if __name__=='__main__': unittest.main(verbosity=2)

"""Release-controller controls using a fake service and isolated real files."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import types

import release_branch as r


class AdditiveContract(unittest.TestCase):
    def test_exact_additions(self):
        old = {'unchanged.py': 'a' * 64}
        r.verify_additive(old, {**old, **r.ADDITIONS})

    def test_changed_old_source_rejected(self):
        old = {'unchanged.py': 'a' * 64}
        with self.assertRaises(ValueError):
            r.verify_additive(old, {**old, **r.ADDITIONS, 'unchanged.py': 'b' * 64})

    def test_missing_added_source_rejected(self):
        new = dict(r.ADDITIONS); new.pop(next(iter(new)))
        with self.assertRaises(ValueError): r.verify_additive({}, new)

    def test_unexpected_file_rejected(self):
        with self.assertRaises(ValueError): r.verify_additive({}, {**r.ADDITIONS, 'unexpected.py': 'a' * 64})

    def test_changed_addition_rejected(self):
        new = dict(r.ADDITIONS); new[next(iter(new))] = 'a' * 64
        with self.assertRaises(ValueError): r.verify_additive({}, new)

    def test_existing_addition_rejected(self):
        with self.assertRaises(ValueError): r.verify_additive(dict(r.ADDITIONS), dict(r.ADDITIONS))

    def test_archive_identity_checked_before_unpack(self):
        with self.assertRaises(ValueError):
            r.assemble(b'wrong', b'wrong', lambda *_: self.fail('unpack invoked'), Path('/unused'))


class ActivationControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.source = self.root / 'source'; self.source.mkdir()
        (self.source / 'releases').mkdir(); (self.source / 'releases' / r.BASE_SHA).mkdir()
        self.old = self.source / 'releases' / r.BASE_SHA
        self.newsha = 'b' * 64; self.new = self.source / 'releases' / self.newsha
        (self.source / 'current').symlink_to(self.old)
        config = self.root / 'etc'; config.mkdir(); (config / 'upgrade-history').mkdir()
        self.config = config / 'config.json'; self.config.write_text('existing config')
        self.old_manifest = {'schema':'merlin-dot-release/1', 'files':{'old.py':'a'*64}, 'source_repository':'Mannyspiro/expert-robot','source_base_commit':'c'*40}
        (self.old / 'manifest.json').write_text(json.dumps(self.old_manifest))
        self.new_manifest = {**self.old_manifest,'files':{**self.old_manifest['files'],**r.ADDITIONS}}
        self.actions = []
        def new_file(p, data):
            with p.open('xb') as f: f.write(data)
        def switch(target, expected, token):
            if os.readlink(self.source/'current') != str(expected): raise RuntimeError('lease mismatch')
            temp = self.source / token; temp.symlink_to(target); os.replace(temp,self.source/'current')
        self.g = {'SOURCE':self.source,'CONFIG':self.config,'_root_directory':lambda _:None,
            '_regular':lambda p,**kw:Path(p).read_bytes(), '_verify_release':lambda *a:None,
            '_new_file':new_file,'_systemctl':self.actions.append,'_switch':switch,
            '_wait_active':lambda:None,'_probe_tools':lambda _: {'job_submit':'tool_not_allowed'}}
        self.bundle = self.root/'runtime.zip'; self.bundle.write_bytes(b'fixture')
        self.snapshot_patch=patch.object(r,'snapshot',return_value={'config_sha256':'d'*64})
        self.snapshot_patch.start(); self.addCleanup(self.snapshot_patch.stop)
        self.probe_patch=patch.object(r,'library_probe',return_value={'installed_library_import':True})
        self.probe_patch.start(); self.addCleanup(self.probe_patch.stop)
        original_fstat=os.fstat
        def fixture_fstat(fd):
            values=list(original_fstat(fd));values[4]=0
            return os.stat_result(values)
        self.uid_patch=patch.object(r.os,'fstat',side_effect=fixture_fstat)
        self.uid_patch.start(); self.addCleanup(self.uid_patch.stop)
        # Root ownership is simulated; filesystem operations use only this fixture.

    def unpack(self,raw,digest,destination):
        destination.mkdir(); (destination/'manifest.json').write_text(json.dumps(self.new_manifest))
        return self.new_manifest

    def run_activate(self):
        return r.activate(self.g,self.unpack,str(self.bundle),self.newsha,'e'*64,'d'*64)

    def test_activation_preserves_old_config_and_release(self):
        result=self.run_activate()
        self.assertEqual(result['status'],'upgraded')
        self.assertEqual(os.readlink(self.source/'current'),str(self.new))
        self.assertTrue(self.old.is_dir()); self.assertEqual(self.config.read_text(),'existing config')
        self.assertEqual(self.actions,['stop','restart'])

    def test_failed_new_probe_restores_original_link(self):
        with patch.object(r,'library_probe',side_effect=RuntimeError('injected new-library failure')):
            result=self.run_activate()
        self.assertEqual(result['status'],'rolled_back')
        self.assertEqual(os.readlink(self.source/'current'),str(self.old))
        self.assertTrue(self.new.is_dir());self.assertEqual(self.config.read_text(),'existing config')
        self.assertEqual(self.actions,['stop','restart','stop','restart'])

    def test_previous_attempt_rejected_before_service_mutation(self):
        self.new.mkdir()
        with self.assertRaisesRegex(RuntimeError,'already exists'): self.run_activate()
        self.assertEqual(self.actions,[])

    def test_unexpected_change_rejected_before_service_mutation(self):
        self.new_manifest['files']['old.py']='f'*64
        with self.assertRaises(ValueError):self.run_activate()
        self.assertEqual(self.actions,[]);self.assertFalse(self.new.exists())

    def test_configuration_change_rejected_before_service_mutation(self):
        with patch.object(r,'snapshot',side_effect=RuntimeError('configuration changed')):
            with self.assertRaisesRegex(RuntimeError,'configuration changed'):self.run_activate()
        self.assertEqual(self.actions,[]);self.assertFalse(self.new.exists())

    def test_failed_switch_after_rename_still_rolls_back(self):
        original=self.g['_switch']
        def interrupted(target,expected,token):
            original(target,expected,token)
            if target==self.new:raise OSError('injected fsync failure after rename')
        self.g['_switch']=interrupted
        result=self.run_activate()
        self.assertEqual(result['status'],'rolled_back')
        self.assertEqual(os.readlink(self.source/'current'),str(self.old))


if __name__=='__main__':unittest.main()

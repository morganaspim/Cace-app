"""Focused checks for the fixed, read-only native reconciliation boundary."""
import json
import os
from pathlib import Path
import tempfile
import unittest

import diagnose_bootstrap as probe


class ReconciliationControls(unittest.TestCase):
    def setUp(self):
        self.request={'schema':'merlin-browser-diagnostic-request/1',
          'request_id':'d2b87421-61d4-42f5-baa6-de0c2e6ed72e','operation':'inspect-loader-44944424850',
          'created_at':'2026-11-21T19:50:00Z'}
        self.execution={'repository':'morganaspim/Cace-app','ref':'refs/heads/merlin/browser-operations-20261121',
          'runner':'cace-oci-a1','run_id':123,'run_attempt':1,'workflow_commit':'a'*40}

    def test_exact_request_and_execution_are_accepted(self):
        probe.validate_request(self.request,self.execution)

    def test_caller_cannot_choose_run_path_command_or_replay(self):
        for field in ('run_id','unit','path','command','retry'):
            with self.subTest(field=field):
                with self.assertRaises(probe.ProbeError):
                    probe.validate_request({**self.request,field:'different'},self.execution)
        for operation in ('bootstrap','submit','reconcile-1'):
            with self.assertRaises(probe.ProbeError):
                probe.validate_request({**self.request,'operation':operation},self.execution)

    def test_wrong_native_execution_is_rejected(self):
        for field,value in (('repository','other/repo'),('runner','another-host'),('run_attempt',2),('workflow_commit','main')):
            with self.assertRaises(probe.ProbeError):
                probe.validate_request(self.request,{**self.execution,field:value})

    def test_commands_are_exact_read_only_queries(self):
        commands=probe.fixed_commands()
        self.assertEqual(set(commands),{'failed_unit','private_unit','model_unit','zvbi_unit','installed_packages',
             'unit_journal','fixture_unit','zvbi_file_states'}|{'elf_metadata_'+str(i) for i in range(7)})
        for argv in commands.values():
            self.assertIn(argv[0],('/usr/bin/systemctl','/usr/bin/rpm','/usr/bin/journalctl','/usr/bin/readelf'))
            self.assertFalse(set(argv)&{'start','restart','stop','enable','disable','set-property','--install','--import'})
        self.assertEqual(commands['failed_unit'][2],'merlin-browser-bootstrap-44944424850-1.service')
        self.assertEqual(commands['installed_packages'][1:3],['-qa','--qf'])
        self.assertNotIn('--property=Environment',commands['failed_unit'])
        self.assertNotIn('--property=ExecStart',commands['failed_unit'])

    def test_reader_refuses_fifo_and_every_symlink_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);os.mkfifo(root/'fifo');(root/'real').mkdir()
            (root/'real'/'receipt').write_bytes(b'evidence');(root/'link').symlink_to(root/'real',target_is_directory=True)
            with self.assertRaises(probe.ProbeError): probe.read_safe(root/'fifo',100)
            with self.assertRaises(OSError): probe.read_safe(root/'link'/'receipt',100)
            self.assertEqual(probe.read_safe(root/'real'/'receipt',100),b'evidence')

    def test_security_scope_preserves_exact_matching_records(self):
        selected=json.dumps({'MESSAGE':'avc: denied { read } comm="dbus-broker" tclass=fifo_file'})+'\n'
        unrelated=json.dumps({'MESSAGE':'An unrelated application event'})+'\n'
        output=probe.relevant_security_records(unrelated+selected)
        self.assertEqual(output['exact_retained_json_lines'],selected)
        self.assertEqual(output['records_seen'],2);self.assertEqual(output['unrelated_records_omitted'],1)

    def test_fixed_target_binds_actual_failed_request(self):
        self.assertEqual(probe.TARGET_RUN,44944424850)
        self.assertEqual(probe.TARGET_REQUEST,'04d38719-4c94-4059-988b-9081375fd209')
        self.assertEqual(probe.TARGET_COMMIT,'b11bf02997dc720535b7d729d60e3a7919892a9a')
        self.assertEqual(probe.BEFORE_COUNT,971)
        self.assertEqual(len(probe.BEFORE_SHA256),64)

    def test_public_binary_inspector_cannot_read_arbitrary_files_or_execute_payloads(self):
        for path in ('/etc/shadow','/etc/merlin-dot-private/config.json','/tmp/python','/usr/bin/ldd'):
            with self.assertRaisesRegex(probe.ProbeError,'fixed public binary'):
                probe.public_binary_identity(path)
        for name,argv in probe.fixed_commands().items():
            if name.startswith('elf_metadata_'):
                self.assertEqual(argv[0],'/usr/bin/readelf');self.assertIn(argv[-1],probe.ELF_FILES)
                self.assertEqual(argv[1:-1],['--wide','--file-header','--program-headers','--dynamic'])


if __name__=='__main__': unittest.main(verbosity=2)

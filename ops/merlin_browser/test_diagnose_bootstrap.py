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
          'request_id':'d2b87421-61d4-42f5-baa6-de0c2e6ed72e','operation':'inspect-supervisor-44945790158',
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
             'unit_journal','fixture_unit','zvbi_file_states','supervisor_unit','supervisor_journal'})
        for argv in commands.values():
            self.assertIn(argv[0],('/usr/bin/systemctl','/usr/bin/rpm','/usr/bin/journalctl'))
            self.assertFalse(set(argv)&{'start','restart','stop','enable','disable','set-property','--install','--import'})
        self.assertEqual(commands['failed_unit'][2],'merlin-browser-bootstrap-44945790158-1.service')
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

    def test_journal_has_fixed_unit_time_and_field_scope(self):
        for name in ('unit_journal','supervisor_journal'):
            argv=probe.fixed_commands()[name]
            self.assertIn('--since=2026-11-21 20:20:40 UTC',argv)
            self.assertIn('--until=2026-11-21 20:21:45 UTC',argv)
            self.assertIn('--lines=512',argv)
            fields=next(value for value in argv if value.startswith('--output-fields='))
            self.assertNotIn('_CMDLINE',fields);self.assertNotIn('_ENVIRONMENT',fields)
        self.assertIn('--unit=merlin-public-browser.service',probe.fixed_commands()['supervisor_journal'])

    def test_fixed_target_binds_actual_failed_request(self):
        self.assertEqual(probe.TARGET_RUN,44945790158)
        self.assertEqual(probe.TARGET_REQUEST,'4e9b1d59-f966-44ed-a2c1-329aa77aa22e')
        self.assertEqual(probe.TARGET_COMMIT,'230b06056b74a998e47e5d8646aa70ec484d811a')
        self.assertEqual(probe.BEFORE_COUNT,971)
        self.assertEqual(len(probe.BEFORE_SHA256),64)

    def test_supervisor_only_execstart_and_no_environment_dump(self):
        commands=probe.fixed_commands()
        self.assertIn('--property=ExecStart',commands['supervisor_unit'])
        for name,argv in commands.items():
            self.assertNotIn('--property=Environment',argv)
            if name!='supervisor_unit': self.assertNotIn('--property=ExecStart',argv)
        self.assertEqual(probe.SUCCESSOR_RESULT_SHA256,'58bb11466d426164070ec07b476adcf919934491b7d6f5099e8266f845e31a37')
        self.assertEqual(probe.EXPECTED_HOST_SHA256,'728199723582985bc21357e72059fab26a0220e01a6d109f36288b39ecbd8600')


if __name__=='__main__': unittest.main(verbosity=2)

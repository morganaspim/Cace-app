"""Local orchestration fixtures; no actual systemd/root/OCI mutations."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import unittest
from unittest.mock import patch

import install_private
import upgrade_research as original
import resume_research as target
import test_upgrade_research as fixtures


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ResearchUpgradeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.bundle()
        self.fixture.fail_new_probe = True
        result = self.fixture.run_upgrade()
        self.assertEqual(result['status'], 'rolled_back')
        self.fixture.fail_new_probe = False
        self.fixture.calls.clear()
        self.history = self.fixture.config_dir / 'upgrade-history'
        self.previous = {p.name: p.read_bytes() for p in self.history.iterdir() if p.is_file()}

    def run_resume(self, probe=None):
        f = self.fixture
        with ExitStack() as stack:
            for name, value in [('ROOT_UID', os.geteuid()), ('SOURCE', f.source), ('CONFIG', f.config), ('UNIT', f.unit)]:
                stack.enter_context(patch.object(original, name, value))
            stack.enter_context(patch.object(original.pwd, 'getpwnam', side_effect=lambda name:
                SimpleNamespace(pw_uid=982 if name == 'merlin-dot' else 1000)))
            stack.enter_context(patch.object(original, '_systemctl', side_effect=f.systemctl))
            stack.enter_context(patch.object(original.time, 'sleep'))
            stack.enter_context(patch.object(target, '_probe', side_effect=probe or (lambda release, research=True: {'fixture': True})))
            return target.resume(f.bundle_path, f.newsha, install_private.unpack_verified, vars(original))

    def test_success_preserves_previous_records_and_exact_replay_does_not_restart(self):
        result = self.run_resume()
        self.assertEqual(result['status'], 'upgraded')
        self.assertEqual(result['service_uid'], 982)
        self.assertFalse(result['qualification'])
        self.assertEqual(os.readlink(self.fixture.source / 'current'), str(self.fixture.new))
        for name, raw in self.previous.items():
            self.assertEqual((self.history / name).read_bytes(), raw)
        calls = list(self.fixture.calls)
        replay = self.run_resume()
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(replay['service_uid'], 982)
        self.assertEqual(self.fixture.calls.count('restart'), calls.count('restart'))

    def test_new_probe_failure_restores_link_config_and_reports_all_dimensions(self):
        def probe(release, research=True):
            if research:
                raise subprocess.CalledProcessError(1, ['fixed'], output='bounded stdout', stderr='specific diagnostic')
            return {'fixture': True}
        result = self.run_resume(probe)
        self.assertEqual(result['status'], 'restored_v1')
        self.assertEqual(result['error']['stderr'], 'specific diagnostic')
        self.assertEqual(result['restoration'], {'pointer': True, 'config': True,
            'service_active': True, 'tools_verified': True, 'errors': []})
        self.assertEqual(os.readlink(self.fixture.source / 'current'), str(self.fixture.old))
        self.assertEqual(self.fixture.config.read_bytes(), self.fixture.old_config_raw)
        self.assertTrue(self.fixture.new.is_dir())
        with self.assertRaisesRegex(RuntimeError, 'second attempt already exists'):
            self.run_resume()

    def test_restored_active_service_distinguished_from_unverified_old_tools(self):
        calls = []
        def probe(release, research=True):
            calls.append((release, research))
            if research or len(calls) > 1:
                raise RuntimeError('semantic fixture denial')
            return {}
        result = self.run_resume(probe)
        self.assertEqual(result['status'], 'recovery_incomplete')
        self.assertTrue(result['restoration']['pointer'])
        self.assertTrue(result['restoration']['config'])
        self.assertTrue(result['restoration']['service_active'])
        self.assertFalse(result['restoration']['tools_verified'])

    def test_tampered_preserved_release_and_original_identity_block_before_stop(self):
        source = self.fixture.new / 'python/dot_ai_os/private_runtime.py'
        source.write_bytes(source.read_bytes() + b'tamper')
        with self.assertRaises(RuntimeError):
            self.run_resume()
        self.assertNotIn('stop', self.fixture.calls)

    def test_old_probe_failure_is_read_only_and_captures_stderr(self):
        def probe(release, research=True):
            raise subprocess.CalledProcessError(2, ['fixed'], stderr='peer failure')
        result = self.run_resume(probe)
        self.assertEqual(result['status'], 'blocked_old_tool_verification')
        self.assertFalse(result['host_mutations'])
        self.assertEqual(result['error']['stderr'], 'peer failure')
        self.assertNotIn('stop', self.fixture.calls)


class ReadinessTests(unittest.TestCase):
    def test_only_missing_or_refused_socket_is_retried(self):
        for failure in (FileNotFoundError(), ConnectionRefusedError()):
            with self.subTest(failure=type(failure).__name__):
                calls = []; pauses = []
                def call():
                    calls.append(True)
                    if len(calls) == 1: raise failure
                    return {'ok': True}
                self.assertEqual(target.readiness_call(call, pauses.append), {'ok': True})
                self.assertEqual((len(calls), pauses), (2, [0.2]))

    def test_identity_auth_and_semantic_failures_are_never_retried(self):
        for failure in (PermissionError('wrong peer'), ValueError('wrong UID'), RuntimeError('semantic denial')):
            calls = []; pauses = []
            def call():
                calls.append(True)
                raise failure
            with self.assertRaises(type(failure)):
                target.readiness_call(call, pauses.append)
            self.assertEqual((len(calls), pauses), (1, []))
        calls = []
        self.assertEqual(target.readiness_call(lambda: calls.append(True) or {'ok': False}, lambda delay: self.fail('retry')), {'ok': False})
        self.assertEqual(len(calls), 1)

    def test_retries_have_finite_bound(self):
        calls = []; pauses = []
        def call():
            calls.append(True)
            raise FileNotFoundError('not ready')
        with self.assertRaises(FileNotFoundError):
            target.readiness_call(call, pauses.append, attempts=3)
        self.assertEqual((len(calls), len(pauses)), (3, 2))

    def test_fixed_peer_process_has_isolated_import_and_no_supplementary_groups(self):
        release = Path('/opt/merlin-dot-private/releases/fixed')
        output = json.dumps({name: {'checked': True} for name in ['health', *target.TOOLS, 'job_submit']})
        with patch.object(target.subprocess, 'run', return_value=SimpleNamespace(stdout=output)) as run:
            target._probe(release)
        args, options = run.call_args
        self.assertEqual(args[0][:4], ['/usr/bin/python3', '-I', '-B', '-c'])
        self.assertIn(target.READINESS_SOURCE, args[0][4])
        self.assertEqual((options['user'], options['group'], options['extra_groups']), (1000, 1000, []))
        self.assertEqual(options['cwd'], str(release))
        self.assertTrue(options['capture_output'])


if __name__ == '__main__':
    unittest.main()

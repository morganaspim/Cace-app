"""Fixed orchestration boundary tests; no production/root/systemd operations."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import install_private
import recovery_drill as target


class RecoveryDrillTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.state=self.root/'state';self.state.mkdir()
        db=sqlite3.connect(str(self.state/'merlin.sqlite3'))
        db.execute('CREATE TABLE fixture(value TEXT)');db.execute("INSERT INTO fixture VALUES('synthetic')")
        db.commit();db.close()
        blob=self.state/'blobs'/'sha256'/'aa'/('b'*62);blob.parent.mkdir(parents=True);blob.write_bytes(b'synthetic')

    def test_state_digest_is_stable_across_read_only_queries(self):
        with patch.object(target,'SERVICE_UID',os.geteuid()):
            before=target._state_digest(self.state)
            with sqlite3.connect(self.state.joinpath('merlin.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
                self.assertEqual(db.execute('SELECT value FROM fixture').fetchone()[0],'synthetic')
            self.assertEqual(target._state_digest(self.state),before)
            self.assertEqual(before['files'],2)

    def test_sidecar_symlink_and_wal_headers_are_rejected(self):
        with patch.object(target,'SERVICE_UID',os.geteuid()):
            sidecar=self.state/'merlin.sqlite3-wal';sidecar.write_bytes(b'wal')
            with self.assertRaises(RuntimeError):target._state_digest(self.state)
            sidecar.unlink();sidecar.symlink_to(self.state/'merlin.sqlite3')
            with self.assertRaises(RuntimeError):target._state_digest(self.state)
            sidecar.unlink()
            database=self.state/'merlin.sqlite3';raw=database.read_bytes()
            database.write_bytes(raw[:18]+b'\x02\x02'+raw[20:])
            with self.assertRaises(RuntimeError):target._state_digest(self.state)

    def run_controller(self,*,changed=False,failure=None):
        baseline={'pid':1234,'state':{'sha256':'a'*64},'health':{'record_count':2}}
        after={**baseline,'pid':1235} if changed else baseline
        def new_file(path,raw,mode=0o600):
            with path.open('xb') as stream:stream.write(raw)
            path.chmod(mode)
        b={'ROOT_UID':os.geteuid(),'SOURCE':target.SOURCE,'CONFIG':target.CONFIG,'UNIT':target.UNIT,
           '_new_file':new_file,'_root_directory':lambda path:None}
        process=SimpleNamespace(stdout=json.dumps({'status':'passed','qualification':False,'promotion_authority':False}),stderr='')
        with ExitStack() as stack:
            stack.enter_context(patch.object(target,'ROOT_UID',os.geteuid()))
            stack.enter_context(patch.object(target,'SERVICE_UID',os.geteuid()))
            stack.enter_context(patch.object(target,'WORKSPACE',self.root/'drills'))
            stack.enter_context(patch.object(target,'_profile',side_effect=[baseline,after]))
            stack.enter_context(patch.object(target.os,'chown'))
            command=stack.enter_context(patch.object(target.subprocess,'run',return_value=process,side_effect=failure))
            result=target.drill(b,'# Authored bounded recovery implementation fixture.\n'*4)
        return result,command

    def test_pass_requires_unchanged_production_and_fixed_isolated_identity(self):
        result,command=self.run_controller()
        self.assertEqual(result['status'],'passed');self.assertTrue(result['production_unchanged'])
        self.assertFalse(result['production_service_restarted']);self.assertFalse(result['qualification'])
        args,options=command.call_args
        self.assertEqual(args[0][:3],['/usr/bin/python3','-I','-B'])
        self.assertEqual(options['extra_groups'],[])
        self.assertEqual(options['group'],1000)
        self.assertTrue(Path(result['workspace'],'receipt.json').is_file())
        self.assertFalse(any('systemctl' in str(x) for x in args[0]))

    def test_changed_production_pid_fails_even_when_clone_passes(self):
        result,_=self.run_controller(changed=True)
        self.assertEqual(result['status'],'failed');self.assertFalse(result['production_unchanged'])

    def test_child_failure_retains_bounded_stderr_and_rechecks_production(self):
        error=subprocess.CalledProcessError(2,['fixed'],output='worker output',stderr='x'*20000)
        result,_=self.run_controller(failure=error)
        self.assertEqual(result['status'],'failed');self.assertTrue(result['production_unchanged'])
        self.assertEqual(len(result['error']['stderr']),16000)
        self.assertEqual(result['error']['stdout'],'worker output')

    def test_root_guard_precedes_any_profiles_or_workspaces(self):
        with patch.object(target.os,'geteuid',return_value=1000),patch.object(target,'_profile') as profile:
            with self.assertRaises(PermissionError):target.drill({},'fixture')
            profile.assert_not_called()

    def test_exact_worker_includes_only_bounded_read_tools_and_no_service_control(self):
        compile(target.WORKER,'fixed-worker','exec')
        for forbidden in ('systemctl','os.kill(','killpg','/var/lib/cace','current.symlink'):
            self.assertNotIn(forbidden,target.WORKER)
        self.assertIn("except (FileNotFoundError,ConnectionRefusedError)",target.WORKER)
        self.assertIn("child.terminate()",target.WORKER)
        self.assertIn("prctl(1,signal.SIGTERM)",target.WORKER)

    def test_mismatched_parent_exits_before_importing_server(self):
        result=subprocess.run(['/usr/bin/python3','-I','-B','-c',target.SERVER_START,'1073741824',
            '/nonexistent-not-imported','serve'],capture_output=True,text=True,timeout=5)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('worker parent identity mismatch',result.stderr)
        self.assertNotIn('ModuleNotFoundError',result.stderr)


class RealWorkerTests(unittest.TestCase):
    def test_real_snapshot_restore_and_private_server(self):
        # This exact integration executes on OCI. The local sandbox may deny
        # AF_UNIX bind with EPERM; that one environmental denial is explicit.
        directory=Path(__file__).parent
        recovery=directory/'recovery.py'
        if not recovery.is_file():recovery=directory.parent/'dot-ai-os/python/dot_ai_os/recovery.py'
        if not recovery.is_file():self.fail('recovery source must accompany this integration fixture')
        with tempfile.TemporaryDirectory(prefix='merlin-recovery-worker-') as temporary:
            root=Path(temporary);release=root/'release';state=root/'state';work=root/'work';work.mkdir(mode=0o700)
            package=directory/'merlin-dot-research-v2-qualified.zip'
            install_private.unpack_verified(package.read_bytes(),target.RELEASE_SHA,release)
            install_private.seed_state(release,state,target.ENV)
            script=root/'worker.py';script.write_text(target.WORKER)
            completed=subprocess.run(['/usr/bin/python3','-I','-B',str(script),str(release),str(state),str(work),str(recovery)],
                cwd=str(root),env=target.ENV,capture_output=True,text=True,timeout=100)
            if completed.returncode:
                try:error=json.loads(completed.stdout)
                except ValueError:error={}
                if ((error.get('error_class')=='PermissionError' and '[Errno 1]' in error.get('message',''))
                        or 'PermissionError: [Errno 1] Operation not permitted' in error.get('isolated_server_stderr','')):
                    self.skipTest('host sandbox denies AF_UNIX socket operation with EPERM; OCI must run this test')
                self.fail('worker failed: '+completed.stdout[-2000:]+' '+completed.stderr[-4000:])
            result=json.loads(completed.stdout)
            self.assertEqual(result['status'],'passed')
            self.assertEqual(result['canonical_identity']['record_count'],2)
            self.assertTrue(result['isolated_server_stopped'])
            self.assertTrue(all(value['rejected'] for value in result['negative_controls'].values()))
            self.assertFalse((work/'missing_blob-must-not-publish').exists())
            self.assertFalse((work/'corrupt_blob-must-not-publish').exists())


if __name__=='__main__':unittest.main()

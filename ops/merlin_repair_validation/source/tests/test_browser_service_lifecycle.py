"""Real local Unix sockets, subprocesses and signals; not OCI/root qualification.

Only the root admission predicate and chown are doubled in subprocess fixtures.
No external browser, model, public fetch or system service is used.
"""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from merlin import browser_service
from merlin.browser_egress import canonical, send_frame
from merlin.browser_policy import BrowserLimits, BrowserPolicyError


HARNESS = r'''
import json, os, signal, socket, sys, time
from pathlib import Path
from merlin import browser_service as service
config=json.loads(Path(sys.argv[1]).read_text())
mode=sys.argv[2]
actual_require=service.require
root_guard='fixed supervisor requires root; Chromium remains a separate nonroot worker'
service.require=lambda condition,message: actual_require(True if message==root_guard else condition,message)
service.os.chown=lambda *args: None
if mode=='after-bind':
    original_socket=socket.socket
    class StopAfterBind(original_socket):
        def bind(self,address):
            super().bind(address)
            os.kill(os.getpid(),signal.SIGTERM)
    service.socket.socket=StopAfterBind
if mode=='slow-cleanup':
    original_cleanup=service._unlink_owned_socket
    def cleanup(*args):
        Path(config['cleanup_marker']).write_text('cleanup entered')
        time.sleep(0.2)
        return original_cleanup(*args)
    service._unlink_owned_socket=cleanup
service.serve(config)
'''


@unittest.skipUnless(sys.platform.startswith('linux'), 'SO_PEERCRED and POSIX process groups required')
class BrowserLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='merlin-stop-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.path=self.root/'socket'/'browser.sock'
        self.path.parent.mkdir(mode=0o700)
        (self.root/'episodes').mkdir()
        self.config={'registry_root':str(self.root/'registry'),'project_id':'merlin-browser-research',
            'episodes_root':str(self.root/'episodes'),'limits':BrowserLimits().to_dict(),
            'launcher':'/unused','launch_timeout_seconds':75,'allowed_uids':[os.getuid()],
            'socket_path':str(self.path),'socket_gid':os.getgid(),
            'cleanup_marker':str(self.root/'cleanup-started')}
        self.process=None
        self.addCleanup(self.cleanup_process)

    def cleanup_process(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait(timeout=3)
            self.process.stdout.close()
            self.process.stderr.close()

    def start(self,mode='normal',wait=True):
        source=self.root/'config.json';source.write_text(json.dumps(self.config))
        self.process=subprocess.Popen([sys.executable,'-c',HARNESS,str(source),mode],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if wait:
            def ready():
                if self.process.poll() is not None:return True
                if not self.path.exists():return False
                try:
                    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as probe:
                        probe.settimeout(0.1);probe.connect(str(self.path))
                    return True
                except OSError:return False
            self.until(ready)
            if self.process.poll() is not None:
                out,err=self.process.communicate()
                self.fail('supervisor did not start: '+err.decode())
        return self.process

    def until(self,predicate,seconds=3):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if predicate(): return
            time.sleep(0.01)
        self.fail('bounded observation deadline reached')

    def stop(self,signum=signal.SIGTERM):
        started=time.monotonic();self.process.send_signal(signum)
        code=self.process.wait(timeout=3)
        elapsed=time.monotonic()-started
        self.assertEqual(code,0,self.process.stderr.read().decode())
        self.assertLess(elapsed,3)

    def test_sigterm_idle_removes_owned_socket(self):
        self.start();self.stop()
        self.assertFalse(self.path.exists())

    def test_sigint_idle_removes_owned_socket(self):
        self.start();self.stop(signal.SIGINT)
        self.assertFalse(self.path.exists())

    def test_sigterm_during_partial_request_removes_owned_socket(self):
        self.start()
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.connect(str(self.path));client.sendall(b'\x00')
            self.stop()
        self.assertFalse(self.path.exists())

    def test_stop_between_bind_and_identity_capture_is_deferred(self):
        self.start(mode='after-bind',wait=False)
        self.assertEqual(self.process.wait(timeout=3),0,self.process.stderr.read().decode())
        self.assertFalse(self.path.exists())

    def test_repeated_sigterm_cannot_interrupt_cleanup(self):
        self.start(mode='slow-cleanup')
        self.process.send_signal(signal.SIGTERM)
        self.until(lambda:Path(self.config['cleanup_marker']).exists())
        self.process.send_signal(signal.SIGTERM)
        self.assertEqual(self.process.wait(timeout=3),0,self.process.stderr.read().decode())
        self.assertFalse(self.path.exists())

    def test_stop_preserves_replaced_socket(self):
        self.start();self.path.unlink()
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as replacement:
            replacement.bind(str(self.path));replacement.listen(1)
            identity=self.path.lstat().st_ino
            self.stop(signal.SIGINT)
            self.assertEqual(self.path.lstat().st_ino,identity)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                client.connect(str(self.path))
                channel,_=replacement.accept();channel.close()

    def test_stop_preserves_replaced_regular_file(self):
        self.start();self.path.unlink();self.path.write_bytes(b'foreign')
        self.stop(signal.SIGINT)
        self.assertEqual(self.path.read_bytes(),b'foreign')

    def test_stop_preserves_replaced_symlink_and_target(self):
        self.start();self.path.unlink()
        target=self.root/'foreign';target.write_bytes(b'foreign')
        self.path.symlink_to(target)
        self.stop(signal.SIGINT)
        self.assertTrue(self.path.is_symlink());self.assertEqual(target.read_bytes(),b'foreign')

    def test_startup_preserves_existing_socket(self):
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as retained:
            retained.bind(str(self.path));retained.listen(1)
            identity=self.path.lstat().st_ino
            self.start(wait=False)
            self.assertNotEqual(self.process.wait(timeout=3),0)
            self.assertEqual(self.path.lstat().st_ino,identity)

    def test_startup_preserves_existing_regular_file(self):
        self.path.write_bytes(b'retained')
        self.start(wait=False)
        self.assertNotEqual(self.process.wait(timeout=3),0)
        self.assertEqual(self.path.read_bytes(),b'retained')

    def test_startup_rejects_symlink_socket_directory(self):
        self.path.parent.rmdir()
        actual=self.root/'foreign-directory';actual.mkdir()
        self.path.parent.symlink_to(actual,target_is_directory=True)
        self.start(wait=False)
        self.assertNotEqual(self.process.wait(timeout=3),0)
        self.assertEqual(list(actual.iterdir()),[])

    def test_unprivileged_admission_is_still_rejected(self):
        with patch.object(browser_service.os,'geteuid',return_value=1000):
            with self.assertRaisesRegex(BrowserPolicyError,'fixed supervisor requires root'):
                browser_service.serve(self.config)
        self.assertFalse(self.path.exists())

    def test_sigterm_active_launcher_kills_and_reaps_child(self):
        pid_file=self.root/'launcher.pid'
        launcher=self.root/'launcher'
        launcher.write_text('#!'+sys.executable+'\nimport os,time\nfrom pathlib import Path\n'
            +'Path('+repr(str(pid_file))+').write_text(str(os.getpid()))\ntime.sleep(60)\n')
        launcher.chmod(0o700);self.config['launcher']=str(launcher)
        self.start()
        child=None
        try:
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                client.connect(str(self.path))
                send_frame(client,canonical({'schema':'merlin-browser-request-api/1','operation':'submit',
                    'episode_id':'stop-active','actions':[{'action':'open','url':'https://example.org/'}]}))
                self.until(pid_file.exists);child=int(pid_file.read_text())
                self.stop()
            self.assertFalse(Path('/proc',str(child)).exists(),'direct child must be reaped')
            self.assertFalse(self.path.exists())
            self.assertTrue((self.root/'episodes'/'stop-active'/'request'/'actions.json').exists())
            service=browser_service.BrowserService(self.config,launch=lambda *args:self.fail('do not replay'))
            result=service.status('stop-active')
            self.assertEqual(result['status'],'reconciliation_needed')
            self.assertFalse(result['execution_retried'])
        finally:
            if child is not None:
                try: os.killpg(child,signal.SIGKILL)
                except ProcessLookupError: pass


if __name__=='__main__':
    unittest.main()

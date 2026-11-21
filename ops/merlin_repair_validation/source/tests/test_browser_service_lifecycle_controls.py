"""Socket-free lifecycle controls for restricted development environments.

Signals, processes, pipes, files, waiting and child reaping are real. The Unix
listener is explicitly a transport fixture and file type checks are doubled.
These controls do not establish native socket or root-service qualification.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from merlin import browser_service

HARNESS=r'''
import json, os, signal, sys, time
from pathlib import Path
from merlin import browser_service as service
config=json.loads(Path(sys.argv[1]).read_text())
mode=sys.argv[2]
actual_require=service.require
root_guard='fixed supervisor requires root; Chromium remains a separate nonroot worker'
service.require=lambda condition,message: actual_require(True if message==root_guard else condition,message)
service.os.chown=lambda *args:None
service.BrowserService=lambda config:None
service.stat.S_ISSOCK=service.stat.S_ISREG
class ListenerFixture:
    def __init__(self,*args):self.file=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def bind(self,path):
        self.file=open(path,'xb')
        if mode=='after-bind':os.kill(os.getpid(),signal.SIGTERM)
    def listen(self,*args):Path(config['ready']).write_text('transport fixture ready')
    def accept(self):
        while True:signal.pause()
    def close(self):
        if self.file is not None:self.file.close()
service.socket.socket=ListenerFixture
if mode=='slow-cleanup':
    original=service._unlink_owned_socket
    def cleanup(*args):
        Path(config['cleanup']).write_text('cleanup entered')
        time.sleep(0.2)
        return original(*args)
    service._unlink_owned_socket=cleanup
service.serve(config)
'''

LAUNCHER_HARNESS=r'''
import signal,sys
from merlin import browser_service as service
class Stop(BaseException):pass
requested=False
def stop(signum,frame):
    global requested
    if not requested:
        requested=True
        raise Stop()
signal.signal(signal.SIGTERM,stop)
try:service.invoke_launcher(sys.argv[1],'fixture',75)
except Stop:pass
'''


class SignalProcessControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='merlin-signal-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'browser.sock';self.process=None
        self.config={'socket_path':str(self.path),'socket_gid':os.getgid(),
            'ready':str(self.root/'ready'),'cleanup':str(self.root/'cleanup')}
        self.addCleanup(self.cleanup)

    def cleanup(self):
        if self.process is not None:
            if self.process.poll() is None:self.process.kill()
            self.process.wait(timeout=3)
            self.process.stdout.close();self.process.stderr.close()

    def until(self,predicate):
        end=time.monotonic()+3
        while time.monotonic()<end:
            if predicate():return
            time.sleep(0.01)
        self.fail('three-second observation deadline reached')

    def start(self,mode='normal',wait=True):
        path=self.root/'config.json';path.write_text(json.dumps(self.config))
        self.process=subprocess.Popen([sys.executable,'-c',HARNESS,str(path),mode],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if wait:
            self.until(lambda:Path(self.config['ready']).exists() or self.process.poll() is not None)
            self.assertIsNone(self.process.poll(),self.process.stderr.read().decode() if self.process.poll() is not None else '')

    def stop(self,signum=signal.SIGTERM):
        self.process.send_signal(signum)
        self.assertEqual(self.process.wait(timeout=3),0,self.process.stderr.read().decode())

    def test_sigterm_unwinds_and_removes_owned_path(self):
        self.start();self.stop();self.assertFalse(self.path.exists())

    def test_sigint_unwinds_and_removes_owned_path(self):
        self.start();self.stop(signal.SIGINT);self.assertFalse(self.path.exists())

    def test_sigterm_during_bind_is_deferred_until_identity_recorded(self):
        self.start('after-bind',wait=False)
        self.assertEqual(self.process.wait(timeout=3),0,self.process.stderr.read().decode())
        self.assertFalse(self.path.exists())

    def test_second_sigterm_during_cleanup_does_not_interrupt(self):
        self.start('slow-cleanup');self.process.send_signal(signal.SIGTERM)
        self.until(lambda:Path(self.config['cleanup']).exists())
        self.process.send_signal(signal.SIGTERM)
        self.assertEqual(self.process.wait(timeout=3),0,self.process.stderr.read().decode())
        self.assertFalse(self.path.exists())

    def test_sigint_cleanup_preserves_replaced_inode(self):
        self.start();original=self.path.stat().st_ino
        self.path.unlink();self.path.write_bytes(b'foreign')
        replacement=self.path.stat().st_ino
        self.assertNotEqual(original,replacement)
        self.stop(signal.SIGINT)
        self.assertEqual(self.path.read_bytes(),b'foreign')

    def test_launcher_does_not_inherit_blocked_stop_signals(self):
        launcher=self.root/'mask-launcher'
        launcher.write_text('#!'+sys.executable+'\nimport json,signal\n'
            +'print(json.dumps(sorted(int(s) for s in signal.pthread_sigmask(signal.SIG_BLOCK,[]))))\n')
        launcher.chmod(0o700)
        before=signal.pthread_sigmask(signal.SIG_BLOCK,[])
        result,raw=browser_service.invoke_launcher(str(launcher),'mask',5)
        self.assertEqual(result['return_code'],0)
        child=set(json.loads(raw))
        for signum in (signal.SIGTERM,signal.SIGINT):
            self.assertEqual(signum in child,signum in before,'child inherited a new blocked stop signal')

    def test_signal_inside_popen_return_window_waits_for_child_identity(self):
        pid=self.root/'spawned-pid';launcher=self.root/'deferred-launcher'
        launcher.write_text('#!'+sys.executable+'\nimport time\ntime.sleep(60)\n');launcher.chmod(0o700)
        harness=r'''import os,signal,sys
from pathlib import Path
from merlin import browser_service as service
stop=service._ShutdownHandler()
for signum in (signal.SIGTERM,signal.SIGINT):signal.signal(signum,stop)
original=service.subprocess.Popen
def spawn(*args,**kwargs):
    process=original(*args,**kwargs)
    Path(sys.argv[2]).write_text(str(process.pid))
    os.kill(os.getpid(),signal.SIGTERM)
    return process
service.subprocess.Popen=spawn
try:service.invoke_launcher(sys.argv[1],'deferred',75)
except service._SupervisorStop:pass
'''
        self.process=subprocess.Popen([sys.executable,'-c',harness,str(launcher),str(pid)],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            self.assertEqual(self.process.wait(timeout=3),0,self.process.stderr.read().decode())
            child=int(pid.read_text())
            self.assertFalse(Path('/proc',str(child)).exists(),'child not reaped after deferred stop')
        finally:
            if pid.exists():
                try:os.killpg(int(pid.read_text()),signal.SIGKILL)
                except ProcessLookupError:pass

    def test_active_launcher_is_killed_and_reaped_after_real_signal(self):
        pid=self.root/'pid';launcher=self.root/'launcher'
        launcher.write_text('#!'+sys.executable+'\nimport os,time\nfrom pathlib import Path\n'
            +'Path('+repr(str(pid))+').write_text(str(os.getpid()))\ntime.sleep(60)\n')
        launcher.chmod(0o700)
        self.process=subprocess.Popen([sys.executable,'-c',LAUNCHER_HARNESS,str(launcher)],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.until(pid.exists);child=int(pid.read_text())
        try:
            self.stop()
            self.assertFalse(Path('/proc',str(child)).exists(),'direct child not reaped')
        finally:
            try:os.killpg(child,signal.SIGKILL)
            except ProcessLookupError:pass


class OwnershipControls(unittest.TestCase):
    def info(self,*,dev=10,ino=20,uid=0,mode=0o140600):
        return SimpleNamespace(st_dev=dev,st_ino=ino,st_uid=uid,st_mode=mode)

    def test_exact_owned_socket_is_removed(self):
        with patch.object(Path,'lstat',return_value=self.info()),patch.object(Path,'unlink') as unlink:
            self.assertTrue(browser_service._unlink_owned_socket(Path('/fixture/socket'),(10,20,0)))
            unlink.assert_called_once()

    def test_replacement_owner_device_inode_type_are_each_preserved(self):
        for data in ({'dev':11},{'ino':21},{'uid':1},{'mode':0o100600},{'mode':0o120777}):
            with self.subTest(data=data),patch.object(Path,'lstat',return_value=self.info(**data)),patch.object(Path,'unlink') as unlink:
                self.assertFalse(browser_service._unlink_owned_socket(Path('/fixture/socket'),(10,20,0)))
                unlink.assert_not_called()

    def test_unbound_and_already_removed_paths_are_not_deleted(self):
        with patch.object(Path,'lstat') as lstat,patch.object(Path,'unlink') as unlink:
            self.assertFalse(browser_service._unlink_owned_socket(Path('/fixture/socket'),None))
            lstat.assert_not_called();unlink.assert_not_called()
        with patch.object(Path,'lstat',side_effect=FileNotFoundError),patch.object(Path,'unlink') as unlink:
            self.assertFalse(browser_service._unlink_owned_socket(Path('/fixture/socket'),(10,20,0)))
            unlink.assert_not_called()

    def test_failed_reap_preserves_stop_control_flow(self):
        class Stop(BaseException):pass
        process=SimpleNamespace(pid=123,stdout=SimpleNamespace(close=lambda:None),wait=lambda **kw:(_ for _ in ()).throw(subprocess.TimeoutExpired('fixture',2)))
        with patch.object(browser_service.subprocess,'Popen',return_value=process),patch.object(browser_service.select,'select',side_effect=Stop),patch.object(browser_service.os,'killpg'):
            with self.assertRaises(Stop):browser_service.invoke_launcher('/fixture','episode',75)


if __name__=='__main__':unittest.main()

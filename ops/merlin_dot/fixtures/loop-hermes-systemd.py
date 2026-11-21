"""Host-only fixed Python tools in transient systemd/cgroup-v2 services.

An already authorized privileged host supervisor is required; this module never
runs sudo, installs tools or grants itself permission. The payload runs as a
DynamicUser with independent manager-enforced lifetime and aggregate memory/pid/
CPU-rate ceilings. This is not qualification of arbitrary hostile code, external
provider IO, aggregate billable units or a complete filesystem confidentiality
sandbox. Paths/hashes are trusted host configuration, never task-selected code.
"""
from __future__ import annotations
from copy import deepcopy
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
from .hermes_process import ProcessLimits, ProcessIsolationUnavailable, read_fixed_program


_CHILD = r'''
import hashlib,json,os,sys
from pathlib import Path
settings=json.loads(sys.argv[1]); source=Path('/run/merlin-fixed-tool/program.py').read_bytes()
if hashlib.sha256(source).hexdigest()!=settings['program_sha256']: raise RuntimeError('program identity')
entry=[line[3:] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::')]
if len(entry)!=1 or not entry[0].endswith('/'+settings['unit']): raise RuntimeError('unexpected control group')
cgroup=Path('/sys/fs/cgroup')/entry[0].lstrip('/')
values={k:(cgroup/k).read_text().strip() for k in ('memory.max','memory.swap.max','pids.max','cpu.max')}
quota,period=values['cpu.max'].split()
if (values['memory.max']!=str(settings['memory_bytes']) or values['memory.swap.max']!='0'
    or values['pids.max']!=str(settings['tasks_max']) or quota=='max'
    or int(quota)!=settings['cpu_cores']*int(period)): raise RuntimeError('kernel limits mismatch')
if os.geteuid()==0: raise RuntimeError('tool must not execute as root')
ready={'unit':settings['unit'],'pid':os.getpid(),'uid':os.geteuid(),'cgroup':entry[0],
       'controllers':values,'program_sha256':settings['program_sha256']}
print('MERLIN_CGROUP_READY='+json.dumps(ready,sort_keys=True),flush=True)
os.environ.clear();os.environ.update({'LANG':'C.UTF-8','PATH':'/usr/bin:/bin'})
sys.argv=['/run/merlin-fixed-tool/program.py']
exec(compile(source,sys.argv[0],'exec'),{'__name__':'__main__','__file__':sys.argv[0]})
'''
_ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'}


def _properties(limits, tasks_max):
    limits.validate()
    if type(tasks_max) is not int or not 1 <= tasks_max <= 32:
        raise ValueError('one to 32 host-approved tasks required')
    return {
        'DynamicUser': 'yes', 'MemoryAccounting': 'yes', 'MemoryMax': str(limits.memory_bytes),
        'MemorySwapMax': '0', 'TasksAccounting': 'yes', 'TasksMax': str(tasks_max),
        'CPUAccounting': 'yes', 'CPUQuota': str(limits.cpu_cores * 100) + '%',
        'RuntimeMaxSec': str(limits.wall_seconds) + 's', 'TimeoutStartSec': '3s',
        'TimeoutStopSec': '1s', 'KillMode': 'control-group', 'SendSIGKILL': 'yes',
        'OOMPolicy': 'kill', 'LimitCORE': '0', 'LimitNOFILE': '64',
        'LimitFSIZE': str(limits.output_bytes // 2), 'LimitCPU': str(limits.cpu_seconds),
        'NoNewPrivileges': 'yes', 'PrivateNetwork': 'yes', 'PrivateDevices': 'yes',
        'ProtectSystem': 'strict', 'ProtectHome': 'yes', 'ProtectControlGroups': 'yes',
        'ProtectKernelTunables': 'yes', 'ProtectKernelModules': 'yes', 'ProtectKernelLogs': 'yes',
        'ProtectProc': 'invisible', 'RestrictSUIDSGID': 'yes', 'RestrictRealtime': 'yes',
        'RestrictAddressFamilies': 'AF_UNIX', 'CapabilityBoundingSet': '',
        'TemporaryFileSystem': '/tmp:rw,size=16M,mode=1777,nosuid,nodev,noexec /var/tmp:rw,size=16M,mode=1777,nosuid,nodev,noexec',
        'UMask': '0077', 'WorkingDirectory': '/',
    }



def _command(unit, properties, settings):
    args = ['/usr/bin/systemd-run', '--quiet', '--wait', '--service-type=exec', '--unit='+unit]
    args += ['--property='+key+'='+value for key, value in properties.items()]
    return args + ['--', '/usr/bin/python3', '-I', '-B', '-S',
                   '/run/merlin-fixed-tool/bootstrap.py', json.dumps(settings, sort_keys=True)]


def _show(unit):
    result = subprocess.run(['/usr/bin/systemctl', 'show', unit,
        '--property=LoadState,ActiveState,SubState,ControlGroup,Result,ExecMainCode,ExecMainStatus,MemoryPeak,CPUUsageNSec'],
        env=_ENV, cwd='/', capture_output=True, text=True, timeout=5)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def _cleanup(unit, proc):
    """Only the unguessable unit generated for this call; fail closed on uncertainty."""
    problem = None
    try:
        subprocess.run(['/usr/bin/systemctl', 'stop', unit], env=_ENV, cwd='/',
                       capture_output=True, timeout=5)
        state = _show(unit)
        if state.get('LoadState') != 'not-found' and state.get('ActiveState') not in {'inactive', 'failed'}:
            raise RuntimeError('fixed-tool cleanup not confirmed')
        cgroup = state.get('ControlGroup')
        if cgroup:
            events = Path('/sys/fs/cgroup') / cgroup.lstrip('/') / 'cgroup.events'
            if events.is_file() and 'populated 1' in events.read_text().splitlines():
                raise RuntimeError('fixed-tool descendants remain live')
        subprocess.run(['/usr/bin/systemctl', 'reset-failed', unit], env=_ENV, cwd='/',
                       capture_output=True, timeout=5)
    except Exception as exc:
        problem = exc
    finally:
        if proc is not None:
            if proc.poll() is None:
                proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=3)
    if problem is not None:
        raise problem
    return state


class SystemdFixedPythonProcess:
    def __init__(self, program_path, program_sha256, *, tasks_max=8):
        read_fixed_program(program_path, program_sha256)
        if type(tasks_max) is not int or not 1 <= tasks_max <= 32:
            raise ValueError('bounded task ceiling required')
        self.path, self.sha256, self.tasks_max = Path(program_path), program_sha256, tasks_max

    @staticmethod
    def available():
        return (sys.platform == 'linux' and os.geteuid() == 0
                and Path('/run/systemd/system').is_dir()
                and Path('/sys/fs/cgroup/cgroup.controllers').is_file()
                and Path('/usr/bin/systemd-run').is_file() and Path('/usr/bin/systemctl').is_file())

    def run(self, input_bytes, *, limits, context, authorize):
        if not self.available():
            raise ProcessIsolationUnavailable('privileged systemd/cgroup-v2 host adapter not provisioned')
        if not isinstance(limits, ProcessLimits) or not callable(authorize):
            raise ValueError('typed limits and host authorization required')
        props = _properties(limits, self.tasks_max)
        if not isinstance(input_bytes, bytes) or len(input_bytes) > 128 * 1024:
            raise ValueError('bounded immutable input required')
        budget = deepcopy(dict(context.resource_budget))
        if (set(budget) != {'cpu_cores', 'memory_bytes', 'max_wall_seconds', 'compute_budget_units'}
                or any(type(value) is not int or value < 1 for value in budget.values())):
            raise ValueError('strict admitted task resource budget required')
        remaining = context.deadline_epoch - time.time()
        if not math.isfinite(remaining) or remaining <= 0:
            raise TimeoutError('task deadline already expired')
        if (limits.cpu_cores > budget['cpu_cores'] or limits.memory_bytes > budget['memory_bytes']
                or limits.wall_seconds > budget['max_wall_seconds'] or limits.wall_seconds > remaining):
            raise PermissionError('tool limits exceed admitted remaining task budget')
        unit = 'merlin-fixed-' + uuid.uuid4().hex + '.service'
        policy = {'program_sha256': self.sha256, 'unit': unit, 'limits': deepcopy(props),
                  'tasks_max': self.tasks_max, 'isolation': 'systemd_cgroup_v2',
                  'compute_budget_units_enforced': False}
        def gate():
            context.check_cancelled()
            if authorize(deepcopy(policy)) is not True:
                raise PermissionError('current fixed-tool host authorization required')
        gate()
        source = read_fixed_program(self.path, self.sha256)
        settings = {'unit': unit, 'program_sha256': self.sha256, 'memory_bytes': limits.memory_bytes,
                    'tasks_max': self.tasks_max, 'cpu_cores': limits.cpu_cores}
        started = time.monotonic(); proc = None; status = 'failed'; observed = {}; cleanup = {}
        with tempfile.TemporaryDirectory(prefix='merlin-fixed-stage-', dir='/run') as stage:
            directory = Path(stage); directory.chmod(0o755)
            (directory/'program.py').write_bytes(source); (directory/'program.py').chmod(0o444)
            (directory/'bootstrap.py').write_text(_CHILD); (directory/'bootstrap.py').chmod(0o444)
            # PID 1 opens these fixed files. Do not pass caller-owned temporary
            # descriptors via --pipe: policy can reject SCM_RIGHTS and disconnect
            # the manager bus. No SELinux setting or permission is changed here.
            for name, body in (('stdin', input_bytes), ('stdout', b''), ('stderr', b'')):
                fd = os.open(directory/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(body)
            props['BindReadOnlyPaths'] = str(directory) + ':/run/merlin-fixed-tool'
            props['StandardInput'] = 'file:' + str(directory/'stdin')
            props['StandardOutput'] = 'file:' + str(directory/'stdout')
            props['StandardError'] = 'file:' + str(directory/'stderr')
            args = _command(unit, props, settings)
            try:
                gate()
                proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, cwd='/', env=_ENV, close_fds=True)
                while proc.poll() is None:
                    gate()
                    if time.monotonic() - started > limits.wall_seconds + 5:
                        status = 'supervisor_timeout'; break
                    if max((directory/'stdout').stat().st_size, (directory/'stderr').stat().st_size) >= limits.output_bytes//2:
                        status = 'output_limit'; break
                    time.sleep(0.02)
                if status == 'failed' and proc.poll() is not None:
                    status = 'completed' if proc.returncode == 0 else 'failed'
                observed = _show(unit)
            finally:
                if proc is not None:
                    cleanup = _cleanup(unit, proc)
            gate()
            with (directory/'stdout').open('rb') as stream:
                out = stream.read(limits.output_bytes//2)
            with (directory/'stderr').open('rb') as stream:
                err = stream.read(limits.output_bytes//2)
            manager_out, manager_err = proc.communicate(timeout=3)
            if len(manager_out) + len(manager_err) > 32768:
                raise RuntimeError('manager diagnostic byte ceiling exceeded')
            first, _, payload = out.partition(b'\n'); setup = None
            if first.startswith(b'MERLIN_CGROUP_READY='):
                setup = json.loads(first[len(b'MERLIN_CGROUP_READY='):])
                if setup.get('unit') != unit or setup.get('program_sha256') != self.sha256:
                    raise RuntimeError('kernel setup identity differs')
            if status == 'completed' and setup is None:
                raise RuntimeError('missing actual kernel setup evidence')
            return {'schema': 'merlin-systemd-process-result/1', 'status': status,
                    'returncode': proc.returncode, 'program_sha256': self.sha256,
                    'bootstrap_sha256': hashlib.sha256(_CHILD.encode()).hexdigest(),
                    'input_sha256': hashlib.sha256(input_bytes).hexdigest(),
                    'elapsed_seconds': time.monotonic()-started, 'limits': policy,
                    'kernel_setup': setup, 'manager_result': observed, 'cleanup': cleanup,
                    'io_transport': 'manager_opened_files',
                    'manager_stderr': manager_err.decode('utf-8', errors='replace'),
                    'stdout': (payload if setup else out).decode('utf-8', errors='replace'),
                    'stderr': err.decode('utf-8', errors='replace'),
                    'stdout_base64': base64.b64encode(out).decode(), 'stderr_base64': base64.b64encode(err).decode(),
                    'stdout_sha256': hashlib.sha256(out).hexdigest(), 'stderr_sha256': hashlib.sha256(err).hexdigest(),
                    'qualification': False, 'promotion_authority': False}

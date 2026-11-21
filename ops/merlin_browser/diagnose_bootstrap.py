"""Fixed read-only reconciliation of native bootstrap run44941093952.

No installation, service transition, unit creation, policy change, model call,
or browser episode is supported. All inspected paths and commands are fixed.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import re
import selectors
import stat
import subprocess
import sys
import time
import uuid

TARGET_RUN=44941093952
TARGET_ATTEMPT=1
TARGET_REQUEST='56b0aad3-17a6-4554-b07e-33e07515e37e'
TARGET_COMMIT='77618494ee3a728ac015f211776082700d8d2443'
TARGET_UNIT='merlin-browser-bootstrap-44941093952-1.service'
BEFORE_SHA256='aa434fae4c1c28b10a94229ff226b9046410a3c0af23482bfead85d00e86294f'
BEFORE_COUNT=921
ACQUISITION_SHA256='a84f362035e170b904407004679b59c2675423fe6a64f8eb4cb92f5f344b9325'
START='2026-11-21 19:28:00 UTC'
END='2026-11-21 19:34:00 UTC'
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
     'HOME':'/var/empty','SYSTEMD_PAGER':'','SYSTEMD_COLORS':'0'}
RPM_FORMAT='%{NAME}\t%{EPOCHNUM}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\n'
UNIT_FIELDS=('LoadState','ActiveState','SubState','Result','MainPID','ExecMainPID',
             'ExecMainCode','ExecMainStatus','InvocationID','ControlGroup','RuntimeMaxUSec',
             'TimeoutStopUSec','KillMode','MemoryMax','MemorySwapMax','CPUQuotaPerSecUSec','TasksMax')


class ProbeError(RuntimeError): pass


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def digest(raw): return hashlib.sha256(raw).hexdigest()


def validate_request(request,execution):
    if (not isinstance(request,dict) or set(request)!={'schema','request_id','operation','created_at'}
        or request['schema']!='merlin-browser-diagnostic-request/1'
        or request['operation']!='reconcile-44941093952'
        or not isinstance(request['request_id'],str) or str(uuid.UUID(request['request_id']))!=request['request_id']
        or not isinstance(request['created_at'],str)
        or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',request['created_at'])):
        raise ProbeError('exact fixed reconciliation request required')
    if (execution.get('repository')!='morganaspim/Cace-app'
        or execution.get('ref')!='refs/heads/merlin/browser-operations-20261121'
        or execution.get('runner')!='cace-oci-a1' or type(execution.get('run_id')) is not int
        or execution['run_id']<=0 or execution.get('run_attempt')!=1
        or not re.fullmatch('[0-9a-f]{40}',execution.get('workflow_commit',''))):
        raise ProbeError('fixed diagnostic workflow identity required')


def directory_fd(path):
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts: raise ProbeError('absolute fixed ancestry required')
    descriptor=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=descriptor)
            os.close(descriptor);descriptor=child
        return descriptor
    except BaseException:
        os.close(descriptor);raise


def read_safe(path,maximum,root_owned=False):
    path=Path(path);parent=directory_fd(path.parent)
    try: descriptor=os.open(path.name,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW,dir_fd=parent)
    finally: os.close(parent)
    try:
        before=os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size>maximum:
            raise ProbeError('bounded regular diagnostic input required')
        if root_owned and (before.st_uid!=0 or before.st_mode&0o022):
            raise ProbeError('root-owned operation artifact required')
        raw=bytearray()
        while True:
            value=os.read(descriptor,min(65536,maximum+1-len(raw)))
            if not value: break
            raw.extend(value)
            if len(raw)>maximum: raise ProbeError('diagnostic input byte ceiling')
        after=os.fstat(descriptor)
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
            raise ProbeError('diagnostic input changed while read')
        return bytes(raw)
    finally: os.close(descriptor)


def describe(path,content=False,root_owned=False,maximum=4*1024*1024):
    result={'path':str(path),'content_scope':'fixed browser operation only'}
    try:
        path=Path(path);parent=directory_fd(path.parent)
        try:
            info=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
            result.update(exists=True,mode=oct(stat.S_IMODE(info.st_mode)),uid=info.st_uid,gid=info.st_gid,bytes=info.st_size)
            if stat.S_ISLNK(info.st_mode): result['symlink_target']=os.readlink(path.name,dir_fd=parent)
        finally: os.close(parent)
        if content:
            raw=read_safe(path,maximum,root_owned);result['sha256']=digest(raw)
            try: result.update(encoding='utf-8',content=raw.decode())
            except UnicodeDecodeError: result.update(encoding='base64',content=base64.b64encode(raw).decode())
    except FileNotFoundError: result['exists']=False
    except BaseException as exc: result['observation_error']={'type':type(exc).__name__,'message':str(exc)[:300]}
    return result


def command(argv,seconds=8,maximum=1024*1024):
    # No detached descendants: the workflow supplies an independent root
    # timeout process group around this entire read-only probe.
    process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,env=ENV,cwd='/')
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
    raw=bytearray();started=time.monotonic();error=None
    try:
        while selector.get_map():
            remaining=seconds-(time.monotonic()-started)
            if remaining<=0: raise ProbeError('read-only command deadline')
            for key,_ in selector.select(min(.2,remaining)):
                value=os.read(key.fd,65536)
                if not value: selector.unregister(key.fileobj);continue
                if len(raw)+len(value)>maximum: raise ProbeError('read-only command output ceiling')
                raw.extend(value)
        process.wait(timeout=max(.01,seconds-(time.monotonic()-started)))
    except BaseException as exc: error={'type':type(exc).__name__,'message':str(exc)[:300]}
    finally:
        selector.close()
        if process.poll() is None: process.kill();process.wait(timeout=3)
        process.stdout.close()
    result={'argv':argv,'returncode':process.returncode,'elapsed_seconds':round(time.monotonic()-started,6),
            'bytes':len(raw),'sha256':digest(raw),'complete':error is None,'error':error}
    try: result.update(encoding='utf-8',output=raw.decode())
    except UnicodeDecodeError: result.update(encoding='base64',output=base64.b64encode(raw).decode())
    return result


def relevant_security_records(raw):
    """Retain exact relevant journal JSON lines; do not dump unrelated events."""
    selected=[];seen=0;invalid=0
    for line in raw.splitlines(keepends=True):
        seen+=1
        try: record=json.loads(line)
        except (ValueError,TypeError): invalid+=1;continue
        message=record.get('MESSAGE','')
        if not isinstance(message,str): continue
        low=message.lower()
        if (TARGET_UNIT in message or 'systemd-run' in low
            or ('dbus-broker' in low and ('denied' in low or 'avc' in low))
            or ('avc' in low and 'fifo_file' in low)):
            selected.append(line)
    return {'records_seen':seen,'records_retained':len(selected),'invalid_json_lines':invalid,
            'exact_retained_json_lines':''.join(selected),'unrelated_records_omitted':seen-len(selected)}


def fixed_commands():
    journal=['/usr/bin/journalctl','--no-pager','--all','--output=json',
             '--output-fields=__REALTIME_TIMESTAMP,__MONOTONIC_TIMESTAMP,_BOOT_ID,_SYSTEMD_UNIT,_PID,_COMM,MESSAGE',
             '--since='+START,'--until='+END,'--lines=512']
    return {
      'failed_unit':['/usr/bin/systemctl','show',TARGET_UNIT,'--no-pager']+['--property='+key for key in UNIT_FIELDS],
      'manager':['/usr/bin/systemctl','show','--no-pager','--property=Version','--property=SystemState'],
      'dbus_unit':['/usr/bin/systemctl','show','dbus-broker.service','--no-pager','--property=LoadState',
                   '--property=ActiveState','--property=MainPID','--property=FragmentPath'],
      'installed_packages':['/usr/bin/rpm','-qa','--qf',RPM_FORMAT],
      'unit_journal':journal+['--unit='+TARGET_UNIT],
      'broker_journal':journal+['--unit=dbus-broker.service'],
      'audit_journal':journal+['_TRANSPORT=audit']}


def run(request,execution,runner_temporary):
    validate_request(request,execution)
    if os.geteuid()!=0 or platform.machine()!='aarch64' or sys.version_info[:2]!=(3,9):
        raise ProbeError('actual native root inspection required')
    temporary=Path(runner_temporary)
    if not temporary.is_absolute() or '..' in temporary.parts: raise ProbeError('observed absolute runner temporary path required')
    result={'schema':'merlin-browser-bootstrap-reconciliation/1','status':'observations_collected',
       'request':request,'execution':execution,'target':{'run_id':TARGET_RUN,'run_attempt':TARGET_ATTEMPT,
       'workflow_commit':TARGET_COMMIT,'request_id':TARGET_REQUEST,'unit':TARGET_UNIT,
       'acquisition_sha256':ACQUISITION_SHA256},'model_calls':0,'browser_episodes':0,
       'software_installation':False,'service_transitions':False,'policy_changes':False,
       'automatic_retry':False,'observed_at_unix':time.time(),'uid':os.geteuid(),'commands':{}}
    for name,argv in fixed_commands().items():
        observed=command(argv,seconds=12 if name.endswith('journal') else 8,
                         maximum=4*1024*1024 if name.endswith('journal') else 1024*1024)
        if name in ('broker_journal','audit_journal') and observed['encoding']=='utf-8':
            raw=observed.pop('output');observed['filtered']=relevant_security_records(raw)
        result['commands'][name]=observed
    package_command=result['commands']['installed_packages']
    if package_command['returncode']==0 and package_command['complete'] and package_command['encoding']=='utf-8':
        rows=[]
        for line in package_command['output'].splitlines():
            fields=line.split('\t')
            if len(fields)!=5: raise ProbeError('current RPM inventory format differs')
            rows.append(dict(zip(('name','epoch','version','release','arch'),fields)))
        rows.sort(key=lambda row:tuple(row[key] for key in ('name','epoch','version','release','arch')))
        result['package_reconciliation']={'count':len(rows),'sha256':digest(canonical(rows)),
             'acquired_before_count':BEFORE_COUNT,'acquired_before_sha256':BEFORE_SHA256,
             'equals_acquired_before':len(rows)==BEFORE_COUNT and digest(canonical(rows))==BEFORE_SHA256}
    state=Path('/var/lib/merlin-browser-bootstrap')
    paths=[state/'bootstrap-intent.json',state/'bootstrap-result.json',
           state/TARGET_REQUEST/'operation-receipt.json',state/TARGET_REQUEST/'rpm-install-intent.json']
    result['retained_operation_artifacts']=[describe(path,content=True,root_owned=True) for path in paths]
    old_output=temporary/('merlin-browser-bootstrap-%d-%d'%(TARGET_RUN,TARGET_ATTEMPT))
    result['runner_candidate_artifacts']=[describe(old_output/name,content=True) for name in
        ('root-candidate-plan.json','root-candidate-rejection.json')]
    result['browser_state']=[describe(path,content=path.name.endswith('.json'),root_owned=True,maximum=65536) for path in
       (Path('/opt/merlin-public-browser/current'),Path('/etc/merlin-public-browser/host.json'),
        Path('/etc/merlin-public-browser/service.json'),Path('/etc/systemd/system/merlin-public-browser.service'))]
    try:
        account=pwd.getpwnam('merlin-browser')
        result['dedicated_browser_account']={'exists':True,'uid':account.pw_uid,'gid':account.pw_gid,
            'home':account.pw_dir,'shell':account.pw_shell}
    except KeyError: result['dedicated_browser_account']={'exists':False}
    result['selinux']={'enforce':describe('/sys/fs/selinux/enforce',content=True,maximum=32),
                      'root_probe_context':describe('/proc/'+str(os.getpid())+'/attr/current',content=True,maximum=256),
                      'pid1_context':describe('/proc/1/attr/current',content=True,maximum=256),
                      'absent_audit_denial_does_not_disprove_selinux':True}
    broker=result['commands']['dbus_unit']
    if broker['encoding']=='utf-8':
        fields=dict(line.split('=',1) for line in broker['output'].splitlines() if '=' in line)
        pid=fields.get('MainPID','')
        if re.fullmatch('[1-9][0-9]{0,8}',pid):
            result['selinux']['broker_context']=describe('/proc/'+pid+'/attr/current',content=True,maximum=256)
    result['bus_sockets']=[describe(path) for path in ('/run/dbus/system_bus_socket','/run/systemd/private')]
    result['stdio_descriptors']=[]
    for descriptor in (0,1,2):
        info=os.fstat(descriptor)
        observed={'descriptor':descriptor,'file_type':stat.S_IFMT(info.st_mode),'uid':info.st_uid,'gid':info.st_gid}
        try: observed['selinux_context']=os.getxattr(descriptor,'security.selinux').decode()
        except (OSError,TypeError,ValueError) as exc: observed['context_observation_error']=type(exc).__name__
        result['stdio_descriptors'].append(observed)
    result['limitations']=['Read-only point-in-time observations do not authorize an automatic retry.',
      'A missing receipt does not prove the controller never began.',
      'Security journals retain only the fixed time window and matching unit/broker/AVC records.']
    if len(canonical(result))>24*1024*1024: raise ProbeError('complete reconciliation evidence ceiling')
    return result

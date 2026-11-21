"""Fixed read-only loader inspection for native bootstrap run44944424850.

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

TARGET_RUN=44944424850
TARGET_ATTEMPT=1
TARGET_REQUEST='04d38719-4c94-4059-988b-9081375fd209'
TARGET_COMMIT='b11bf02997dc720535b7d729d60e3a7919892a9a'
TARGET_UNIT='merlin-browser-bootstrap-44944424850-1.service'
OPERATION='inspect-loader-44944424850'
PRIOR_INTENT_SHA256='203c362c00fb7af0b6f02ac7b923d0894b7f09553eb031299822f62e35a1d305'
PRIOR_RESULT_SHA256='8170ddc15aaf4630fc32440eb353da649c1c8bdfcf9a52cda1e8d7f2a0c30557'
SUCCESSOR_INTENT_SHA256='b641bd1d8f2d5d6f5a7a016e74f8cf942a92c15c2d7db0b1d752d66709d3801f'
SUCCESSOR_RESULT_SHA256='0ce1241325e81b33e51d487bfd9e0c0b2b8f5531335fceb945e3155920bb8797'
SUCCESSOR_LINEAGE_SHA256='2cbac1011c002262d8239c7e8b21c3623a6290e3d3b8e38f353c5e887687df09'
FIXTURE_RECEIPT_SHA256='96f121315477fcc742cfbd6757b63fefdfec531551aa8ad4cc52fc30d968cfa2'
STAGED=Path('/var/lib/merlin-browser-bootstrap')/TARGET_REQUEST
BEFORE_SHA256='498f3ea85fe0dfcebbd2871c5029e1f1216ea2a6031f4ef20bd0eefaa69d79fd'
BEFORE_COUNT=971
ACQUISITION_SHA256='a84f362035e170b904407004679b59c2675423fe6a64f8eb4cb92f5f344b9325'
RELEASE=Path('/opt/merlin-public-browser/releases/58f9b4fee8b03db777a07e76149ef5fedcc8c1c9b3309c16499b3cadecfbac90')
RUNTIME_MANIFEST_SHA256='51c68b5f7ceb10debb270ffdde2409648968dddd11e5e93c3f989802ca25b8d8'
EXPECTED_HOST_SHA256='728199723582985bc21357e72059fab26a0220e01a6d109f36288b39ecbd8600'
FIXTURE=Path('/var/lib/merlin-public-browser/episodes')/('bootstrap-fixture-'+TARGET_REQUEST)
FIXTURE_UNIT='merlin-browser-fixture-bootstrap-fixture-'+TARGET_REQUEST+'.service'
ELF_FILES=('/usr/bin/python3.9',str(RELEASE/'venv/bin/python'),str(RELEASE/'venv/bin/python3'),
    str(RELEASE/'venv/bin/python3.9'),str(RELEASE/'venv/lib/python3.9/site-packages/playwright/driver/node'),
    str(RELEASE/'venv/lib64/python3.9/site-packages/playwright/driver/node'),'/usr/lib64/chromium-browser/headless_shell')
LOADER_FILES=('/lib/ld-linux-aarch64.so.1','/lib64/ld-linux-aarch64.so.1',
    '/usr/lib/ld-linux-aarch64.so.1','/usr/lib64/ld-linux-aarch64.so.1')
START='2026-11-21 20:05:40 UTC'
END='2026-11-21 20:07:00 UTC'
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
        or request['operation']!=OPERATION
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


def public_binary_identity(path):
    """Resolve only fixed public runtime binaries; never execute their bytes."""
    if str(path) not in ELF_FILES+LOADER_FILES:
        raise ProbeError('fixed public binary path required')
    path=Path(path);result={'path':str(path),'executed':False,'path_metadata':[]}
    try:
        resolved=path.resolve(strict=True)
        allowed=(str(RELEASE/'venv')+'/', '/usr/lib64/', '/usr/lib/')
        if (str(resolved) not in ('/usr/bin/python3.9','/usr/libexec/platform-python3.9')
            and not str(resolved).startswith(allowed)):
            raise ProbeError('resolved binary outside fixed public runtime roots')
        paths=[]
        for item in (path,resolved):
            for node in reversed([item]+list(item.parents)):
                if node not in paths: paths.append(node)
        if len(paths)>32: raise ProbeError('bounded fixed link ancestry required')
        for node in paths:
            info=node.lstat();row={'path':str(node),'mode':oct(stat.S_IMODE(info.st_mode)),
                'uid':info.st_uid,'gid':info.st_gid,'bytes':info.st_size}
            if stat.S_ISLNK(info.st_mode): row['symlink_target']=os.readlink(node)
            result['path_metadata'].append(row)
        fd=os.open(str(resolved),os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o022 or info.st_size>256*1024*1024:
                raise ProbeError('bounded root-owned public binary required')
            value=hashlib.sha256();size=0;prefix=b''
            while True:
                chunk=os.read(fd,1048576)
                if not chunk: break
                if not prefix: prefix=chunk[:64]
                size+=len(chunk)
                if size>256*1024*1024: raise ProbeError('public binary hash ceiling')
                value.update(chunk)
            after=os.fstat(fd)
            if (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
                raise ProbeError('public binary changed while inspected')
            result.update(exists=True,resolved_path=str(resolved),sha256=value.hexdigest(),bytes=size,
                elf_magic=prefix[:4].hex(),elf_ident=prefix[:16].hex(),content_exported=False)
        finally: os.close(fd)
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
    result={
      'failed_unit':['/usr/bin/systemctl','show',TARGET_UNIT,'--no-pager']+['--property='+key for key in UNIT_FIELDS],
      'private_unit':['/usr/bin/systemctl','show','merlin-dot-private.service','--no-pager']+['--property='+key for key in UNIT_FIELDS],
      'model_unit':['/usr/bin/systemctl','show','merlin-model-provider.service','--no-pager']+['--property='+key for key in UNIT_FIELDS],
      'zvbi_unit':['/usr/bin/systemctl','show','zvbid.service','--no-pager','--property=LoadState',
                   '--property=ActiveState','--property=SubState','--property=MainPID','--property=FragmentPath'],
      'installed_packages':['/usr/bin/rpm','-qa','--qf',RPM_FORMAT],
      'unit_journal':journal+['--unit='+TARGET_UNIT],
      'fixture_unit':['/usr/bin/systemctl','show',FIXTURE_UNIT,'--no-pager']+['--property='+key for key in UNIT_FIELDS],
      'zvbi_file_states':['/usr/bin/rpm','-q','--qf','[%{FILENAMES}\t%{FILESTATES}\n]','zvbi']}
    for index,path in enumerate(ELF_FILES):
        result['elf_metadata_%d'%index]=['/usr/bin/readelf','--wide','--file-header','--program-headers','--dynamic',path]
    return result


def run(request,execution,runner_temporary):
    validate_request(request,execution)
    if os.geteuid()!=0 or platform.machine()!='aarch64' or sys.version_info[:2]!=(3,9):
        raise ProbeError('actual native root inspection required')
    temporary=Path(runner_temporary)
    if not temporary.is_absolute() or '..' in temporary.parts: raise ProbeError('observed absolute runner temporary path required')
    state=Path('/var/lib/merlin-browser-bootstrap')
    if (digest(read_safe(state/'bootstrap-intent.json',65536,root_owned=True))!=PRIOR_INTENT_SHA256
        or digest(read_safe(state/'bootstrap-result.json',4*1024*1024,root_owned=True))!=PRIOR_RESULT_SHA256):
        raise ProbeError('exact retained failed operation lineage differs')
    expected={STAGED/'bootstrap-intent.json':SUCCESSOR_INTENT_SHA256,
      STAGED/'bootstrap-result.json':SUCCESSOR_RESULT_SHA256,STAGED/'operation-receipt.json':SUCCESSOR_RESULT_SHA256,
      STAGED/'successor-lineage.json':SUCCESSOR_LINEAGE_SHA256,STAGED/'acquisition.json':ACQUISITION_SHA256,
      state/'successor-from-ef0c417a-4b58-4c5d-b44b-be7a237bedfa.json':SUCCESSOR_LINEAGE_SHA256,
      FIXTURE/'launch-receipt.json':FIXTURE_RECEIPT_SHA256,RELEASE/'manifest.json':RUNTIME_MANIFEST_SHA256,
      Path('/etc/merlin-public-browser/host.json'):EXPECTED_HOST_SHA256}
    observed_pins=[]
    for path,wanted in expected.items():
        raw=read_safe(path,4*1024*1024,root_owned=True);actual=digest(raw)
        observed_pins.append({'path':str(path),'sha256':actual,'bytes':len(raw),'matches_expected':actual==wanted})
        if actual!=wanted: raise ProbeError('exact retained successor/runtime identity differs: '+str(path))
    result={'schema':'merlin-browser-bootstrap-reconciliation/1','status':'observations_collected',
       'request':request,'execution':execution,'target':{'run_id':TARGET_RUN,'run_attempt':TARGET_ATTEMPT,
       'workflow_commit':TARGET_COMMIT,'request_id':TARGET_REQUEST,'unit':TARGET_UNIT,
       'acquisition_sha256':ACQUISITION_SHA256},'model_calls':0,'browser_episodes':0,
       'software_installation':False,'service_transitions':False,'policy_changes':False,
       'automatic_retry':False,'observed_at_unix':time.time(),'uid':os.geteuid(),'commands':{}}
    result['prior_lineage']={'intent_sha256':PRIOR_INTENT_SHA256,'failed_result_sha256':PRIOR_RESULT_SHA256,
                             'actual_files_matched':True}
    result['successor_identity_observations']=observed_pins
    result['host_expected_pin_origin']='derived from exact prior constructor and receipt; this probe hashes the actual host file'
    result['public_binaries']=[public_binary_identity(path) for path in ELF_FILES+LOADER_FILES]
    inspected={row['path']:row for row in result['public_binaries']}
    for name,argv in fixed_commands().items():
        if name.startswith('elf_metadata_') and (not inspected[argv[-1]].get('exists') or 'observation_error' in inspected[argv[-1]]):
            result['commands'][name]={'argv':argv,'skipped':True,'reason':'fixed public binary absent or identity inspection rejected'}
            continue
        observed=command(argv,seconds=8 if name.endswith('journal') else 5,
                         maximum=4*1024*1024 if name.endswith('journal') else 1024*1024)
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
             'retained_after_count':BEFORE_COUNT,'retained_after_sha256':BEFORE_SHA256,
             'equals_retained_after':len(rows)==BEFORE_COUNT and digest(canonical(rows))==BEFORE_SHA256}
    paths=[state/'bootstrap-intent.json',state/'bootstrap-result.json',
           STAGED/'bootstrap-intent.json',STAGED/'bootstrap-result.json',STAGED/'operation-receipt.json',
           STAGED/'rpm-install-intent.json',STAGED/'successor-lineage.json',FIXTURE/'launch-receipt.json']
    result['retained_operation_artifacts']=[describe(path,content=True,root_owned=True) for path in paths]
    old_output=temporary/('merlin-browser-bootstrap-%d-%d'%(TARGET_RUN,TARGET_ATTEMPT))/'root-evidence'
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
    result['existing_private_hashes']=[]
    for path in ('/etc/merlin-dot-private/config.json','/etc/systemd/system/merlin-dot-private.service',
                 '/etc/merlin-model-provider/manifest.json','/etc/systemd/system/merlin-model-provider.service'):
        # Match the existing snapshot's read-only hash contract; do not invent
        # a new ownership requirement for already admitted private services.
        raw=read_safe(path,1048576)
        result['existing_private_hashes'].append({'path':path,'sha256':digest(raw),'bytes':len(raw),'content_exported':False})
    result['daemon_paths']=[describe(path) for path in ('/usr/lib/systemd/system/zvbid.service',
      '/etc/systemd/system/zvbid.service','/run/systemd/system/zvbid.service','/usr/sbin/zvbid')]
    result['venv_configuration']=describe(RELEASE/'venv/pyvenv.cfg',content=True,root_owned=True,maximum=65536)
    result['mount_ancestors']=[describe(path) for path in (Path('/lib'),Path('/lib64'),Path('/usr/lib'),
        Path('/usr/lib64'),RELEASE,RELEASE/'venv',RELEASE/'venv/bin',RELEASE/'python',RELEASE/'bin')]
    manifest=json.loads(read_safe(RELEASE/'manifest.json',1048576,root_owned=True));result['runtime_file_identities']=[]
    for item in manifest['files']:
        name=item['path']
        if not re.fullmatch(r'(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+',name) or '..' in Path(name).parts:
            raise ProbeError('frozen runtime member path differs')
        raw=read_safe(RELEASE/name,2*1024*1024,root_owned=True)
        result['runtime_file_identities'].append({'path':name,'bytes':len(raw),'sha256':digest(raw),
            'matches_manifest':len(raw)==item['bytes'] and digest(raw)==item['sha256']})
    result['limitations']=['Read-only point-in-time observations do not authorize an automatic retry.',
      'A missing receipt does not prove the controller never began.',
      'Python, the Playwright driver, Chromium, and the dynamic loader are inspected as data, never executed.',
      'No fixture is retried and no mount or isolation setting is changed.']
    if len(canonical(result))>24*1024*1024: raise ProbeError('complete reconciliation evidence ceiling')
    return result
